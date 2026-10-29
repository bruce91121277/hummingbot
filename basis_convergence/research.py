"""Offline comparison: Hummingbot L2 VWAP and the legacy hypothetical state machine."""
import argparse,csv,json,sys,statistics
from decimal import Decimal as D
from pathlib import Path
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_row import OrderBookRow
from hummingbot.core.data_type.order_book_message import OrderBookMessage,OrderBookMessageType

OLD=Path.home()/'perp-arbitrage'
sys.path.insert(0,str(OLD/'src'));sys.path.insert(0,str(OLD))
from perp_arb.phase13_hedge_replay import load_books,walk as old_walk
from perp_arb.phase13_research_cli import latest,edge
import perp_arb.phase13_convergence_research as strategy
from scripts.phase13_6a_offline_validation import _capture_dirs,_integrity_and_event_count

NS=1000000000

def hb_walk(book,side,quantity):
    if side not in ('buy','sell') or quantity<0:raise ValueError('invalid order')
    ob=OrderBook(); uid=1
    msg=OrderBookMessage(OrderBookMessageType.SNAPSHOT,{'trading_pair':'RESEARCH','update_id':uid,'bids':[[str(p),str(q)] for p,q in book.bids],'asks':[[str(p),str(q)] for p,q in book.asks]},timestamp=book.time_ns/NS)
    ob.apply_snapshot(msg.bids,msg.asks,uid)
    levels=book.asks if side=='buy' else book.bids
    filled=min(quantity,sum((q for _,q in levels),D(0)))
    if not filled:return {'side':side,'quantity':D(0),'notional':D(0),'vwap':None,'unfilled':quantity}
    res=ob.get_vwap_for_volume(side=='buy',float(filled))
    import math
    if not math.isfinite(res.result_price):raise ValueError('Hummingbot VWAP unavailable')
    price=D(str(res.result_price));return {'side':side,'quantity':filled,'notional':filled*price,'vwap':price,'unfilled':quantity-filled}

def main():
    p=argparse.ArgumentParser();p.add_argument('--capture-root',type=Path,required=True);p.add_argument('--route',choices=['arcus_lighter_rh'],required=True);p.add_argument('--mode',choices=['hypothetical'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):raise ValueError('output must be empty')
    a.output.mkdir(parents=True,exist_ok=True);signals=[];trades=[];comparisons=[];excluded=[];caps=[];counts={str(n):{'samples':0,'positive':0,'edge_ge_10':0} for n in (100,250,500,1000)}
    for path in _capture_dirs(a.capture_root):
      integ=_integrity_and_event_count(path)
      if not integ['integrity_verified']:excluded.append({'capture':path.name,'reason':'INTEGRITY_UNVERIFIED'});continue
      try:books,quality=load_books(path);meta=json.loads((path/'discovery.json').read_text())['markets']
      except (ValueError,OSError,KeyError) as ex:excluded.append({'capture':path.name,'reason':str(ex)});continue
      caps.append({'capture':path.name,'manifest_verified':True,'events':integ['market_events'],'quality':quality})
      ids={str(v['market_id']):k for k,v in meta.get('lighter_rh',{}).items()};source={}
      for venue in ('arcus','lighter_rh'):
       f=path/(venue+'.jsonl')
       if not f.exists():continue
       for line in f.open():
        r=json.loads(line);m=r['message'];sym=str(m.get('id','')).removesuffix('-USD') if venue=='arcus' else ids.get(str(r['market_id']))
        if sym and r.get('source_timestamp') is not None:source[(venue,sym,r['received_mono_ns'])]=r
      for sym in ('SPY','QQQ','NVDA','SNDK'):
       if sym not in meta.get('arcus',{}) or sym not in meta.get('lighter_rh',{}):continue
       left=books.get(('arcus',sym),[]);right=books.get(('lighter_rh',sym),[])
       if not left or not right:continue
       lt=[b.time_ns for b in left];rt=[b.time_ns for b in right];
       for t in range(max(lt[0],rt[0]),min(lt[-1],rt[-1]),NS):
        x=latest(left,lt,t);y=latest(right,rt,t)
        if not x or not y:continue
        rx=source.get(('arcus',sym,x.time_ns));ry=source.get(('lighter_rh',sym,y.time_ns))
        if not rx or not ry:continue
        now=rx['received_utc_ns']+(t-x.time_ns);aa=(now-int(rx['source_timestamp'])*1000)/1e6;bb=(now-int(ry['source_timestamp'])*1000)/1e6;spread,side=edge(x,y);skew=abs(int(rx['source_timestamp'])-int(ry['source_timestamp']))/1000
        for limit in (100,250,500,1000):
         if 0<=aa<=limit and 0<=bb<=limit and skew<=limit:
          z=counts[str(limit)];z['samples']+=1;z['positive']+=spread>0;z['edge_ge_10']+=spread>=10
        if spread>=10:signals.append({'capture':path.name,'market':sym,'receive_mono_ns':t,'arcus_source_timestamp_raw':rx['source_timestamp'],'lighter_source_timestamp_raw':ry['source_timestamp'],'arcus_source_age_ms_assumed':aa,'lighter_source_age_ms_assumed':bb,'source_skew_ms_assumed':skew,'edge_bps':str(spread),'side_left':side,'segment_left':x.segment,'segment_right':y.segment})
       cfg={'entry':10,'kind':'percent','fraction':'0.25','exit_basis':2,'max_hold':120,'fee':0,'left_venue':'arcus','right_venue':'lighter_rh','left_taker_fee_bps':'2.25','right_taker_fee_bps':'0','delay_ms':100,'markets':{'arcus':sym+'-USD','lighter_rh':sym}}
       strategy.walk=old_walk;old=strategy.run(path.name,{'arcus':left,'lighter_rh':right},cfg)
       strategy.walk=hb_walk
       try:new=strategy.run(path.name,{'arcus':left,'lighter_rh':right},cfg)
       finally:strategy.walk=old_walk
       for i in range(max(len(old),len(new))):
        x=old[i] if i<len(old) else {};y=new[i] if i<len(new) else {}; comparisons.append({'capture':path.name,'market':sym,'index':i,'old_signal_ns':x.get('signal_ns'),'hb_signal_ns':y.get('signal_ns'),'old_exit_reason':x.get('exit_reason'),'hb_exit_reason':y.get('exit_reason'),'old_net':x.get('net'),'hb_net':y.get('net'),'old_fills':x.get('fills'),'hb_fills':y.get('fills'),'old_inventory':x.get('open_inventory'),'hb_inventory':y.get('open_inventory')})
       for row in new:row.update(market=sym,classification='HYPOTHETICAL');trades.append(row)
    def write(name,rows):
     fields=list(dict.fromkeys(k for r in rows for k in r))
     with (a.output/name).open('w',newline='') as f:
      if fields:w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
    write('spread_signals.csv',signals);write('convergence_trades.csv',trades);write('execution_comparison.csv',comparisons);write('fee_attribution.csv',trades);write('residual_positions.csv',[r for r in trades if r['right_censored']])
    result={'classification':'HYPOTHETICAL','captures':caps,'excluded':excluded,'freshness_ms_assumed':counts,'signals':len(signals),'trades':len(trades),'closed':sum(r['net'] is not None for r in trades),'censored':sum(r['right_censored'] for r in trades),'limitations':'Legacy capture loader and state machine/ledger reused. Only order book VWAP runs in Hummingbot; this is not a Hummingbot execution engine. Freshness is a diagnostic, not applied to strategy. Source microseconds, independent clocks, units, fees and 1:1 conversion assumed. No private trading, maker fills or qualified PnL.'}
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(a.output/'report.md').write_text('# Hummingbot core / legacy research bridge\n\n'+result['limitations']+'\n\n'+json.dumps({'freshness':counts,'signals':len(signals),'trades':len(trades),'closed':result['closed'],'censored':result['censored']},indent=2)+'\n')
    print(json.dumps({'captures':len(caps),'excluded':len(excluded),'freshness':counts,'trades':len(trades),'closed':result['closed'],'censored':result['censored']}))
if __name__=='__main__':main()