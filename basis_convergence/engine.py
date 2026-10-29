"""Deterministic, read-only convergence replay with explicit missing-data intervals."""
import bisect,math
from decimal import Decimal as D
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_row import OrderBookRow
NS=1000000000

def latest(quotes,t):
 i=bisect.bisect_right(quotes,t,key=lambda q:q.mono)-1
 return quotes[i] if i>=0 else None

def diagnose(a,b,t,limit_ms):
 reasons=[];limit=limit_ms*1000000
 for name,q in (('left',a),('right',b)):
  if q is None:reasons.append((name,'ORDERBOOK_INVALID'));continue
  if not q.bids or not q.asks:reasons.append((name,getattr(q,'invalid_reason','ORDERBOOK_INVALID')));continue
  if t<q.mono or t-q.mono>limit:reasons.append((name,'RECEIVE_TIMESTAMP_STALE'))
  if not q.source:reasons.append((name,'ORDERBOOK_INVALID'))
 if a and b and a.bids and b.bids and a.source and b.source:
  now=a.utc+(t-a.mono)
  for name,q in (('left',a),('right',b)):
   age=now-q.source*1000
   if age<0:reasons.append((name,'SOURCE_TIMESTAMP_IN_FUTURE'))
   elif age>limit:reasons.append((name,'SOURCE_TIMESTAMP_STALE'))
  if abs(a.source-b.source)*1000>limit:reasons.append(('pair','SOURCE_SKEW_EXCEEDED'))
  if abs(a.utc-b.utc)>limit:reasons.append(('pair','RECEIVE_SKEW_EXCEEDED'))
 return reasons

def fresh(a,b,t,limit_ms):return not diagnose(a,b,t,limit_ms)

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

def replay(capture,market,left,right,limit_ms=500,entry_bps=10,delay_ms=100,exit_fraction=D('.25'),max_hold_s=120,*,gap_grace_s=None,exit_mode='percent',fee_left=D('2.25'),fee_right=D(0),stop_bps=D('10'),capture_end_ns=None,decision_ms=1000):
 if not left or not right:return [],[],[]
 start=max(left[0].mono,right[0].mono);end=capture_end_ns if capture_end_ns is not None else min(left[-1].mono,right[-1].mono);t=start;rows=[];events=[];signals=[]
 if end<start:return [],[],[]
 if gap_grace_s is not None and gap_grace_s<0:raise ValueError('invalid gap grace')
 if exit_mode not in ('percent','basis','net','combined','stop'):raise ValueError('invalid exit mode')
 fee_left=D(str(fee_left));fee_right=D(str(fee_right));step=decision_ms*1000000
 if decision_ms not in (100,250,1000):raise ValueError('invalid decision interval')
 def event(kind,t,venue,order,trade,details=None):events.append({'id':capture+':'+market+':'+str(len(events)),'capture':capture,'trade_id':trade,'time_mono_ns':t,'venue':venue,'market':market,'order_id':order,'event':kind,'details':details})
 while t<end:
  a=latest(left,t);b=latest(right,t)
  if not fresh(a,b,t,limit_ms):t+=step;continue
  sell=(a.bids[0][0]-b.asks[0][0])/b.asks[0][0]*10000;buy=(b.bids[0][0]-a.asks[0][0])/a.asks[0][0]*10000
  edge,side=(sell,'sell') if sell>=buy else (buy,'buy')
  if edge<D(entry_bps):t+=step;continue
  trade=capture+':'+market+':'+str(t);signals.append({'capture':capture,'market':market,'time_mono_ns':t,'edge_bps':str(edge),'side_left':side});ledger=Ledger();opp='buy' if side=='sell' else 'sell'
  event('SIGNAL_DETECTED',t,a.venue,'',trade);event('ENTRY_ATTEMPTED',t,a.venue,trade+':a',trade)
  qty=D(100)/(a.asks[0][0] if side=='buy' else a.bids[0][0]);q,p=walk(a,side,qty)
  if not q:t+=step;continue
  ledger.fill(trade+':a',a.venue,side,q,p,fee_left);entry_fee=ledger.fees;event('ENTRY_FILLED',t,a.venue,trade+':a',trade)
  ht=t+delay_ms*1000000;aa=latest(left,ht);bb=latest(right,ht)
  if ht<=end:event('HEDGE_ATTEMPTED',ht,b.venue,trade+':b',trade)
  h=D(0);reason='HEDGE_FAILURE';exit_t=None;gross=None;net=None;last=None;last_t=None;censor_t=min(end,ht);gaps=[];opps=[];first={'25':None,'50':None,'net_positive':None};maximum=None;minimum=None;gap_start=None;gap_reason=set();recovered=0;simulation_enabled=True
  if ht<=end and fresh(aa,bb,ht,limit_ms) and aa.segment==a.segment and bb.segment==b.segment:
   h,hp=walk(bb,opp,q)
   if h:ledger.fill(trade+':b',b.venue,opp,h,hp,fee_right);event('HEDGE_FILLED',ht,b.venue,trade+':b',trade)
   if h==q:
    event('POSITION_OPEN',ht,'PAIR','',trade);reason='END_OF_CAPTURE';mid_a=(a.bids[0][0]+a.asks[0][0])/2;mid_b=(b.bids[0][0]+b.asks[0][0])/2;initial=(mid_a-mid_b)*(1 if side=='sell' else -1);tick=ht+step;segments=(a.segment,b.segment)
    while tick<=end:
     x=latest(left,tick);y=latest(right,tick);why=diagnose(x,y,tick,limit_ms)
     if x and y and (x.segment,y.segment)!=segments:
      why.append(('pair','CONNECTION_SEGMENT_CHANGED'));segments=(x.segment,y.segment)
     close_a=close_b=D(0);px=py=None
     if not why:
      close_a,px=walk(x,opp,q);close_b,py=walk(y,side,h)
      if close_a<q:why.append(('left','INSUFFICIENT_EXIT_DEPTH'))
      if close_b<h:why.append(('right','INSUFFICIENT_EXIT_DEPTH'))
     if why:
      if gap_start is None:gap_start=tick;gap_reason=set();event('DATA_GAP_STARTED',tick,'PAIR','',trade)
      gap_reason.update(why);event('DATA_GAP_ACTIVE',tick,'PAIR','',trade,why)
      if gap_grace_s is not None and tick-gap_start>=gap_grace_s*NS:simulation_enabled=False
      tick+=step;continue
     if gap_start is not None:
      if gap_grace_s is not None and tick-gap_start>=gap_grace_s*NS:simulation_enabled=False
      recovered+=1;gaps.append({'capture':capture,'market':market,'trade_id':trade,'start_ns':gap_start,'end_ns':tick,'duration_seconds':str(D(tick-gap_start)/NS),'reasons':sorted([list(z) for z in gap_reason]),'recovered':True});event('DATA_GAP_RECOVERED',tick,'PAIR','',trade);gap_start=None
     event('QUOTE_VALID',tick,'PAIR','',trade)
     potential=ledger.cash-(D(1) if opp=='buy' else D(-1))*q*px-(D(1) if side=='buy' else D(-1))*h*py-ledger.fees-q*px*fee_left/10000-h*py*fee_right/10000
     last=str(potential);last_t=tick;current=((x.bids[0][0]+x.asks[0][0])-(y.bids[0][0]+y.asks[0][0]))/2*(1 if side=='sell' else -1);maximum=current if maximum is None else max(maximum,current);minimum=current if minimum is None else min(minimum,current)
     for label,fraction in (('25',D('.25')),('50',D('.5'))):
      if initial>0 and current<=initial*(1-fraction) and first[label] is None:first[label]=str(D(tick-ht)/NS)
     if potential>0 and first['net_positive'] is None:first['net_positive']=str(D(tick-ht)/NS)
     mid=(x.bids[0][0]+x.asks[0][0]+y.bids[0][0]+y.asks[0][0])/4;basis_bps=current/mid*10000
     converged=initial>0 and current<=initial*(1-exit_fraction)
     if exit_mode=='basis':target=basis_bps<=2
     elif exit_mode=='net':target=potential>0
     elif exit_mode=='combined':target=converged and potential>0
     else:target=converged
     stop=exit_mode=='stop' and potential<=-D(100)*stop_bps/10000
     action='STOP_LOSS' if stop else ('NET_PROFIT_TARGET' if target and exit_mode=='net' else ('BASIS_CONVERGED' if target else ('MAX_HOLD_TIMEOUT' if tick-ht>=max_hold_s*NS else None)))
     if action:opps.append({'capture':capture,'market':market,'trade_id':trade,'time_ns':tick,'trigger':action,'potential_net':str(potential),'basis_bps':str(basis_bps),'simulation_enabled':simulation_enabled})
     if action and simulation_enabled:
      reason=action;event('EXIT_ELIGIBLE',tick,'PAIR','',trade,action)
      if action=='BASIS_CONVERGED':event('CONVERGENCE_DETECTED',tick,'PAIR','',trade)
      for venue,s,amount,price,fee in ((a.venue,opp,q,px,fee_left),(b.venue,side,h,py,fee_right)):
       oid=trade+':exit:'+venue;event('EXIT_ATTEMPTED',tick,venue,oid,trade);ledger.fill(oid,venue,s,amount,price,fee);event('EXIT_FILLED',tick,venue,oid,trade)
      if all(v==0 for v in ledger.inventory.values()):exit_t=tick;gross=ledger.cash;net=gross-ledger.fees;event('POSITION_CLOSED',tick,'PAIR','',trade)
      break
     tick+=step
    if exit_t is None:
     censor_t=end
     if gap_start is not None:gaps.append({'capture':capture,'market':market,'trade_id':trade,'start_ns':gap_start,'end_ns':None,'duration_seconds':str(D(end-gap_start)/NS),'reasons':sorted([list(z) for z in gap_reason]),'recovered':False})
     reason='CAPTURE_END'
  emergency=None;exposure=None;single_leg_observations=[]
  if reason=='HEDGE_FAILURE':
   exposure=str(abs(q-h) * p) if 'h' in locals() else str(q*p)
   # Emergency liquidation is a separate hypothetical counterfactual, not an automatic fill.
   for et in range(min(end,ht)+step,end+1,step):
    x=latest(left,et);y=latest(right,et)
    if not fresh(x,x,et,limit_ms):continue
    closeq,closepx=walk(x,opp,q)
    if closeq<q:continue
    est=(p-closepx if side=='sell' else closepx-p)*q-entry_fee-q*closepx*fee_left/10000
    single_leg_observations.append({'time_ns':et,'first_leg_liquidation_net':str(est)})
    if emergency is None:emergency={'time_ns':et,'quantity':str(q),'price':str(closepx),'fee':str(q*closepx*fee_left/10000),'remaining_hedge_qty':str(h),'first_leg_net':str(est),'classification':'HYPOTHETICAL_COUNTERFACTUAL'}
   censor_t=end
  if exit_t is None:event('POSITION_CENSORED',censor_t,'PAIR','',trade,'CAPTURE_END' if censor_t==end else reason)
  rows.append({'capture':capture,'market':market,'trade_id':trade,'entry_ns':t,'entry_spread_bps':str(edge),'entry_fees':str(entry_fee),'hedge_ns':ht,'exit_ns':exit_t,'exit_reason':reason,'gross':str(gross) if gross is not None else None,'net':str(net) if net is not None else None,'fees':str(ledger.fees),'funding_assumption':'0','last_liquidation_estimate':last,'valuation_ns':last_t,'valuation_stale_at_capture_end':last_t is None or end-last_t>limit_ms*1000000,'inventory':{k:str(v) for k,v in ledger.inventory.items()},'fills':ledger.fills,'classification':'HYPOTHETICAL','right_censored':exit_t is None,'first_gap_ns':gaps[0]['start_ns'] if gaps else None,'gap_recoveries':recovered,'gaps':gaps,'exit_opportunities':opps,'maximum_observed_basis':str(maximum) if maximum is not None else None,'minimum_observed_basis':str(minimum) if minimum is not None else None,'first_25_seconds':first['25'],'first_50_seconds':first['50'],'first_positive_seconds':first['net_positive'],'source_clock_status':'ASSUMED_UNVERIFIED','capture_end_ns':end,'unhedged_notional_assumed':exposure,'emergency_close_scenario':emergency,'single_leg_risk_observations':single_leg_observations})
  if exit_t is None:break
  t=exit_t+step
 return signals,rows,events