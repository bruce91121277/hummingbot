"""Read manifest-verified public captures with Hummingbot books; no account access."""
import hashlib,json
from collections import Counter,defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_row import OrderBookRow

@dataclass(frozen=True)
class Quote:
 venue:str;market:str;mono:int;utc:int;source:int;segment:int;sequence:int;bids:tuple;asks:tuple

def verify(path):
 path=Path(path);manifest=json.loads((path/'manifest.json').read_text());files=manifest.get('files')
 if not isinstance(files,dict) or not files:raise ValueError('missing manifest files')
 children=list(path.iterdir())
 if any(x.is_symlink() or not x.is_file() for x in children):raise ValueError('unsafe capture path')
 if {x.name for x in children if x.name!='manifest.json'}!=set(files):raise ValueError('manifest file set mismatch')
 for name,entry in files.items():
  if Path(name).name!=name or not isinstance(entry,dict):raise ValueError('invalid manifest entry')
  h=hashlib.sha256();size=0
  with (path/name).open('rb') as f:
   while chunk:=f.read(1024*1024):h.update(chunk);size+=len(chunk)
  if h.hexdigest()!=entry.get('sha256') or size!=entry.get('bytes'):raise ValueError('manifest hash mismatch')
 return manifest

def levels(raw,uid):
 out=[]
 for item in raw or []:
  p,q=(item.get('price'),item.get('size')) if isinstance(item,dict) else item[:2]
  p=Decimal(str(p));q=Decimal(str(q))
  if not p.is_finite() or not q.is_finite() or p<=0 or q<0:raise ValueError('invalid level')
  out.append(OrderBookRow(float(p),float(q),uid))
 return out

def read_capture(path):
 path=Path(path);manifest=verify(path);meta=json.loads((path/'discovery.json').read_text())['markets'];ids={str(v['market_id']):k for k,v in meta.get('lighter_rh',{}).items()};results=defaultdict(list);quality=Counter()
 for venue in ('arcus','lighter_rh'):
  file=path/(venue+'.jsonl')
  if not file.exists():continue
  states={};last={}
  with file.open() as f:
   for line in f:
    row=json.loads(line);msg=row['message'];typ=msg.get('type');body=None
    if venue=='arcus' and msg.get('channel')=='l2Orderbook' and typ in ('subscribed','channel_data'):
     sym=str(msg.get('id','')).removesuffix('-USD');body=msg.get('contents');snapshot=True
    elif venue=='lighter_rh' and typ in ('subscribed/order_book','update/order_book'):
     sym=ids.get(str(row.get('market_id')));body=msg.get('order_book');snapshot=typ=='subscribed/order_book'
    else:continue
    if not sym or sym not in meta.get('arcus',{}) or sym not in meta.get('lighter_rh',{}) or not isinstance(body,dict):quality['unknown_market_or_body']+=1;continue
    t=int(row['received_mono_ns']);seg=int(row['segment_id']);state=states.get(sym)
    try:
     if venue=='arcus':seq=body.get('lastSequenceId');seq=int(seq) if seq is not None else None
     else:seq=int(body['nonce'])
     if seq is None or row.get('source_timestamp') is None:raise ValueError('missing sequence or source time')
     if snapshot:
      ob=OrderBook();ob.apply_snapshot(levels(body.get('bids'),seq),levels(body.get('asks'),seq),seq);states[sym]=(seg,seq,ob)
     else:
      if not state or state[0]!=seg or int(body['begin_nonce'])!=state[1] or seq<=state[1]:raise ValueError('invalid lighter continuity')
      ob=state[2];ob.apply_diffs(levels(body.get('bids'),seq),levels(body.get('asks'),seq),seq);states[sym]=(seg,seq,ob)
     bids=tuple((Decimal(str(x.price)),Decimal(str(x.amount))) for x in list(ob.bid_entries())[:20]);asks=tuple((Decimal(str(x.price)),Decimal(str(x.amount))) for x in list(ob.ask_entries())[:20])
     if not bids or not asks or bids[0][0]>=asks[0][0]:raise ValueError('empty or crossed book')
     quality[venue+':accepted']+=1
     if t-last.get(sym,0)>=100000000:
      results[(venue,sym)].append(Quote(venue,sym,t,int(row['received_utc_ns']),int(row['source_timestamp']),seg,seq,bids,asks));last[sym]=t
    except (ValueError,KeyError,TypeError,ArithmeticError):
     states.pop(sym,None);results[(venue,sym)].append(Quote(venue,sym,t,int(row['received_utc_ns']),0,seg,0,(),()));quality[venue+':rejected']+=1
 return manifest,dict(results),dict(quality)