"""Deterministic hypothetical execution; timestamps are assumed comparable."""
import bisect,math
from decimal import Decimal as D
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_row import OrderBookRow
NS=1000000000

def latest(quotes,t):
 i=bisect.bisect_right([q.mono for q in quotes],t)-1
 return quotes[i] if i>=0 else None

def fresh(a,b,t,limit_ms):
 if not a or not b or not a.bids or not b.bids or not a.source or not b.source:return False
 if a.mono>t or b.mono>t:return False
 limit=limit_ms*1000000
 now=a.utc+(t-a.mono)
 return (0<=t-a.mono<=limit and 0<=t-b.mono<=limit and
         0<=now-a.source*1000<=limit and 0<=now-b.source*1000<=limit and
         abs(a.source-b.source)*1000<=limit and abs(a.utc-b.utc)<=limit)

def walk(q,side,qty):
 book=OrderBook();uid=1
 book.apply_snapshot([OrderBookRow(float(p),float(s),uid) for p,s in q.bids],[OrderBookRow(float(p),float(s),uid) for p,s in q.asks],uid)
 available=sum((x[1] for x in (q.asks if side=='buy' else q.bids)),D(0));filled=min(qty,available)
 if filled<=0:return D(0),None
 result=book.get_vwap_for_volume(side=='buy',float(filled))
 if not math.isfinite(result.result_price):return D(0),None
 return filled,D(str(result.result_price))

class Ledger:
 def __init__(self):self.ids=set();self.inventory={};self.cash=D(0);self.fees=D(0);self.fills=[]
 def fill(self,fill_id,venue,side,qty,price,fee_bps):
  if fill_id in self.ids:return False
  if qty<=0 or price<=0:raise ValueError('invalid fill')
  self.ids.add(fill_id);sign=D(1) if side=='buy' else D(-1);notional=qty*price;fee=notional*fee_bps/D(10000)
  self.inventory[venue]=self.inventory.get(venue,D(0))+sign*qty;self.cash-=sign*notional;self.fees+=fee
  self.fills.append({'id':fill_id,'venue':venue,'side':side,'qty':str(qty),'vwap':str(price),'notional':str(notional),'fee':str(fee),'role':'TAKER'});return True

def replay(capture,market,left,right,limit_ms=500,entry_bps=10,delay_ms=100,exit_fraction=D('.25'),max_hold_s=120):
 if not left or not right:return [],[],[]
 start=max(left[0].mono,right[0].mono);end=min(left[-1].mono,right[-1].mono);t=start;rows=[];events=[];signals=[]
 def event(kind,t,venue,order,trade):events.append({'id':capture+':'+market+':'+str(len(events)),'capture':capture,'trade_id':trade,'time_mono_ns':t,'venue':venue,'market':market,'order_id':order,'event':kind})
 while t<end:
  a=latest(left,t);b=latest(right,t)
  if not fresh(a,b,t,limit_ms):t+=NS;continue
  sell=(a.bids[0][0]-b.asks[0][0])/b.asks[0][0]*10000;buy=(b.bids[0][0]-a.asks[0][0])/a.asks[0][0]*10000
  edge,side=(sell,'sell') if sell>=buy else (buy,'buy')
  if edge<D(entry_bps):t+=NS;continue
  trade=capture+':'+market+':'+str(t);signals.append({'capture':capture,'market':market,'time_mono_ns':t,'edge_bps':str(edge),'side_left':side});ledger=Ledger();opp='buy' if side=='sell' else 'sell'
  event('SIGNAL_DETECTED',t,a.venue,'',trade);event('ENTRY_ATTEMPTED',t,a.venue,trade+':a',trade)
  qty=D(100)/(a.asks[0][0] if side=='buy' else a.bids[0][0]);q,p=walk(a,side,qty)
  if not q:t+=NS;continue
  ledger.fill(trade+':a',a.venue,side,q,p,D('2.25'));event('ENTRY_FILLED',t,a.venue,trade+':a',trade)
  ht=t+delay_ms*1000000;aa=latest(left,ht);bb=latest(right,ht)
  if ht<=end:event('HEDGE_ATTEMPTED',ht,b.venue,trade+':b',trade)
  reason='HEDGE_FAILURE';exit_t=None;gross=None;net=None;last=None;censor_t=min(end,ht)
  if ht<=end and fresh(aa,bb,ht,limit_ms) and aa.segment==a.segment and bb.segment==b.segment:
   h,hp=walk(bb,opp,q)
   if h:
    ledger.fill(trade+':b',b.venue,opp,h,hp,D(0));event('HEDGE_FILLED',ht,b.venue,trade+':b',trade)
   if h==q:
    event('POSITION_OPEN',ht,'PAIR','',trade);reason='END_OF_CAPTURE';mid_a=(a.bids[0][0]+a.asks[0][0])/2;mid_b=(b.bids[0][0]+b.asks[0][0])/2;initial=(mid_a-mid_b)*(1 if side=='sell' else -1);tick=ht+NS
    while tick<=end:
     x=latest(left,tick);y=latest(right,tick)
     if not fresh(x,y,tick,limit_ms) or x.segment!=a.segment or y.segment!=b.segment:reason='DATA_GAP';censor_t=tick;event('DATA_GAP',tick,'PAIR','',trade);break
     close_a,px=walk(x,opp,q);close_b,py=walk(y,side,h)
     if close_a<q or close_b<h:reason='DATA_GAP';censor_t=tick;event('DATA_GAP',tick,'PAIR','',trade);break
     potential=ledger.cash-(D(1) if opp=='buy' else D(-1))*q*px-(D(1) if side=='buy' else D(-1))*h*py-ledger.fees-q*px*D('2.25')/10000
     last=str(potential);current=((x.bids[0][0]+x.asks[0][0])-(y.bids[0][0]+y.asks[0][0]))/2*(1 if side=='sell' else -1)
     converged=initial>0 and current<=initial*(1-exit_fraction)
     if converged or tick-ht>=max_hold_s*NS:
      reason='BASIS_CONVERGED' if converged else 'MAX_HOLD_TIMEOUT'
      if converged:event('CONVERGENCE_DETECTED',tick,'PAIR','',trade)
      for venue,s,amount,price,fee in ((a.venue,opp,q,px,D('2.25')),(b.venue,side,h,py,D(0))):
       oid=trade+':exit:'+venue;event('EXIT_ATTEMPTED',tick,venue,oid,trade);ledger.fill(oid,venue,s,amount,price,fee);event('EXIT_FILLED',tick,venue,oid,trade)
      if all(v==0 for v in ledger.inventory.values()):exit_t=tick;gross=ledger.cash;net=gross-ledger.fees;event('POSITION_CLOSED',tick,'PAIR','',trade)
      break
     tick+=NS
    if reason=='END_OF_CAPTURE':censor_t=end
  if exit_t is None:event('POSITION_CENSORED',censor_t,'PAIR','',trade)
  rows.append({'capture':capture,'market':market,'trade_id':trade,'entry_ns':t,'hedge_ns':ht,'exit_ns':exit_t,'exit_reason':reason,'gross':str(gross) if gross is not None else None,'net':str(net) if net is not None else None,'fees':str(ledger.fees),'funding_assumption':'0','last_liquidation_estimate':last,'inventory':{k:str(v) for k,v in ledger.inventory.items()},'fills':ledger.fills,'classification':'HYPOTHETICAL','right_censored':exit_t is None})
  if exit_t is None:break
  t=exit_t+NS
 return signals,rows,events