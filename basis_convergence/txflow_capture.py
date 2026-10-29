"""Bounded unauthenticated public market capture on Oracle."""
import argparse, asyncio, hashlib, json, time, uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
import websockets

def query(url,payload=None):
 headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json','x-api-version':'2026-08-16'}
 with urlopen(Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers=headers),timeout=15) as r:return json.load(r)
def now():return datetime.now(timezone.utc).isoformat()
async def main(root,seconds):
 if not 1<=seconds<=300:raise ValueError('duration must be between 1 and 300 seconds')
 tx=query('https://rpc.txflow.com/info',{'type':'perpMeta','includeDelisted':False})
 lighter=query('https://mainnet.zklighter.elliot.ai/api/v1/orderBooks')
 txbtc=[x for x in tx['data']['universe'] if x.get('baseCurrency')=='BTC' and x.get('quoteCurrency')=='USDC' and not x.get('delisted') and not x.get('haltTrading')]
 core=[x for x in lighter['order_books'] if x.get('symbol')=='BTC' and x.get('market_type')=='perp' and x.get('status')=='active' and x.get('market_deployer')=='lighter']
 if len(txbtc)!=1 or len(core)!=1:raise ValueError('market discovery is ambiguous')
 txbtc=txbtc[0];core=core[0];ident=str(txbtc['index']);lid=str(core['market_id'])
 root.mkdir(parents=True,exist_ok=True);d=root/('capture_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]);d.mkdir()
 discovery={'retrieved_utc':now(),'sources':{'txflow':tx,'lighter_core':lighter},'markets':{'txflow':{'BTC':txbtc},'lighter_core':{'BTC':core}}}
 (d/'discovery.json').write_text(json.dumps(discovery,separators=(',',':')))
 start=now();deadline=time.monotonic()+seconds;counts={};errors={}
 async def stream(venue,url,subscription):
  count=0;f=(d/(venue+'.jsonl')).open('x');next_ping=time.monotonic()+10
  try:
   async with websockets.connect(url,additional_headers={'User-Agent':'Mozilla/5.0'},open_timeout=12,close_timeout=2,max_size=8*1024*1024) as ws:
    await ws.send(json.dumps(subscription))
    while time.monotonic()<deadline and count<20000:
     if venue=='txflow' and time.monotonic()>=next_ping:await ws.send('{"method":"ping"}');next_ping=time.monotonic()+10
     try:raw=await asyncio.wait_for(ws.recv(),min(1,max(.01,deadline-time.monotonic())))
     except asyncio.TimeoutError:continue
     received=time.time_ns();mono=time.monotonic_ns();msg=json.loads(raw)
     if venue=='txflow':
      if msg.get('channel')!='l2Book':continue
      body=msg.get('data',{});source=body.get('time');seq=None;market=ident;unit='ms_documented'
     else:
      if not str(msg.get('channel','')).startswith('order_book:'):continue
      body=msg.get('order_book',{});source=body.get('last_updated_at',msg.get('last_updated_at'));seq=body.get('nonce');market=lid;unit='us_UNVERIFIED'
     row={'venue':venue,'stream':'orderbook','market_id':market,'segment_id':1,'received_utc_ns':received,'received_mono_ns':mono,'source_timestamp':source,'source_timestamp_unit':unit,'sequence':seq,'message':msg}
     f.write(json.dumps(row,separators=(',',':'))+'\n');count+=1
  except Exception as exc:errors[venue]=type(exc).__name__+': '+str(exc)[:200]
  finally:f.close();counts[venue]=count
 await asyncio.gather(stream('txflow','wss://rpc.txflow.com/ws',{'method':'subscribe','type':'l2Book','subscription':{'type':'l2Book','coin':ident}}),stream('lighter_core','wss://mainnet.zklighter.elliot.ai/stream?readonly=true',{'type':'subscribe','channel':'order_book/'+lid}))
 files={}
 for f in d.iterdir():
  raw=f.read_bytes();files[f.name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 manifest={'start_utc':start,'end_utc':now(),'events':counts,'errors':errors,'files':files,'source':'PUBLIC_ONLY','max_seconds':seconds,'event_cap_per_venue':20000}
 (d/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'path':str(d),'events':counts,'errors':errors}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--seconds',type=int,default=60);a=p.parse_args();asyncio.run(main(a.output_root,a.seconds))
