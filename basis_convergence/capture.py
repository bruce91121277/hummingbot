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
 venue:str;market:str;mono:int;utc:int;source:int;segment:int;sequence:int;bids:tuple;asks:tuple;invalid_reason:str="ORDERBOOK_INVALID"

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
    except (ValueError,KeyError,TypeError,ArithmeticError) as exc:
     states.pop(sym,None);reason='SEQUENCE_GAP' if 'continuity' in str(exc) else 'ORDERBOOK_INVALID';results[(venue,sym)].append(Quote(venue,sym,t,int(row['received_utc_ns']),0,seg,0,(),(),reason));quality[venue+':rejected']+=1
 return manifest,dict(results),dict(quality)

def read_extended_core(path):
 """Replay only manifest-verified BTC books; source clocks remain research assumptions."""
 path=Path(path); manifest=verify(path); meta=json.loads((path/'discovery.json').read_text())['markets']; out=defaultdict(list); quality=Counter()
 btc=meta.get('lighter_core',{}).get('BTC',{}); market_id=str(btc.get('market_id',''))
 if not market_id or meta.get('extended',{}).get('BTC',{}).get('name')!='BTC-USD': return manifest,{}, {'route_market_missing':1}
 for venue in ('extended','lighter_core'):
  file=path/(venue+'.jsonl'); state=None; last_segment=None; last_time=-1
  if not file.exists():continue
  for line in file.open():
   row=json.loads(line); msg=row.get('message',{}); body=msg.get('data',{}) if venue=='extended' else msg.get('order_book',{})
   if venue=='extended':
    if row.get('market_id')!='BTC-USD' or not str(row.get('stream','')).startswith('orderbooks/'):continue
    if body.get('m')!='BTC-USD':quality[venue+':identity_rejected']+=1;continue
    kind=msg.get('type'); snap=kind=='SNAPSHOT'; delta=kind=='DELTA'; seq=msg.get('seq'); timestamp=msg.get('ts'); unit='ms_system_generated'
   else:
    if str(row.get('market_id'))!=market_id or msg.get('channel')!='order_book:'+market_id:continue
    kind=msg.get('type'); snap=kind=='subscribed/order_book'; delta=kind=='update/order_book'; seq=body.get('nonce'); timestamp=body.get('last_updated_at',msg.get('last_updated_at')); unit='us_UNVERIFIED'
   if not (snap or delta):continue
   t=int(row['received_mono_ns']); seg=int(row['segment_id']); reason='ORDERBOOK_INVALID'
   try:
    if row.get('source_timestamp_unit')!=unit or timestamp is None or row.get('source_timestamp')!=timestamp:raise ValueError('timestamp mismatch')
    if seq is None or int(seq)<0 or row.get('sequence')!=seq:raise ValueError('sequence mismatch')
    seq=int(seq)
    if last_segment is not None and seg!=last_segment:state=None
    last_segment=seg
    if not snap:
     if state is None or state[0]!=seg:raise ValueError('snapshot required')
     reason='SEQUENCE_GAP'
     if seq<=state[1]:raise ValueError('sequence order')
     if venue=='lighter_core' and int(body['begin_nonce'])!=state[1]:raise ValueError('nonce gap')
     # shortcut: missing Extended sequence steps invalidate a book until a snapshot, pending protocol proof that skipped steps are harmless.
     if venue=='extended' and seq!=state[1]+1:raise ValueError('sequence step unverified')
    if venue=='extended':
     def convert(k):
      raw=body.get(k)
      if not isinstance(raw,list):raise ValueError('missing depth')
      return levels([(x['p'],x['q'] if snap else x['c']) for x in raw],seq)
     bids,asks=convert('b'),convert('a')
    else:bids,asks=levels(body.get('bids'),seq),levels(body.get('asks'),seq)
    if snap:ob=OrderBook();ob.apply_snapshot(bids,asks,seq)
    else:ob=state[2];ob.apply_diffs(bids,asks,seq)
    b=tuple((Decimal(str(x.price)),Decimal(str(x.amount))) for x in list(ob.bid_entries())[:20]); a=tuple((Decimal(str(x.price)),Decimal(str(x.amount))) for x in list(ob.ask_entries())[:20])
    if not b or not a or b[0][0]>=a[0][0]:raise ValueError('invalid book')
    state=(seg,seq,ob);quality[venue+':accepted']+=1
    if t-last_time>=100000000:
     source=int(timestamp)*1000 if venue=='extended' else int(timestamp)
     out[(venue,'BTC')].append(Quote(venue,'BTC',t,int(row['received_utc_ns']),source,seg,seq,b,a));last_time=t
   except (ValueError,KeyError,TypeError,ArithmeticError):
    state=None;quality[venue+':rejected']+=1;out[(venue,'BTC')].append(Quote(venue,'BTC',t,int(row['received_utc_ns']),0,seg,0,(),(),reason))
 return manifest,dict(out),dict(quality)
