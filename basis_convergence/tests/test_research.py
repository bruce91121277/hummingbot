from decimal import Decimal as D
from basis_convergence.capture import Quote
from basis_convergence.engine import Ledger,fresh,latest,replay,walk,NS

def quote(venue,t,bid='102',ask='103',source=None,utc=None,qty='10'):
 return Quote(venue,'SPY',t,utc if utc is not None else t,source if source is not None else t//1000,1,1,((D(bid),D(qty)),),((D(ask),D(qty)),))

def test_hummingbot_depth_and_partial_fill():
 a=quote('arcus',NS,qty='1');assert walk(a,'buy',D('2'))==(D('1'),D('103.0'))

def test_freshness_and_no_future():
 a=quote('arcus',NS);b=quote('lighter_rh',NS);assert fresh(a,b,NS,500)
 assert not fresh(a,b,NS+501000000,500)
 assert not fresh(a,b,NS-1,500)
 assert latest([a],NS-1) is None

def test_source_skew_and_receive_skew():
 a=quote('arcus',NS);b=quote('lighter_rh',NS,source=(NS-600000000)//1000)
 assert not fresh(a,b,NS,500)
 b=quote('lighter_rh',NS,utc=NS+600000000)
 assert not fresh(a,b,NS,500)

def test_duplicate_fill_and_ledger():
 l=Ledger();assert l.fill('1','a','buy',D(2),D(3),D(10));assert not l.fill('1','a','buy',D(2),D(3),D(10))
 assert l.inventory['a']==2 and l.fees==D('.006') and l.cash==-6

def test_gap_censors_and_preserves_position():
 left=[quote('arcus',i*NS,'102','103') for i in (1,2,5,6)]
 right=[quote('lighter_rh',i*NS,'99','100') for i in (1,2,5,6)]
 s,r,e=replay('capture','SPY',left,right,1000,10,0)
 assert r[0]['exit_reason']=='CAPTURE_END' and r[0]['net'] is None and r[0]['right_censored']
 assert r[0]['inventory']['arcus']!='0' and any(x['event']=='POSITION_CENSORED' for x in e)
 assert [x['time_mono_ns'] for x in e]==sorted(x['time_mono_ns'] for x in e)

def test_hedge_failure_preserves_inventory():
 left=[quote('arcus',i*NS,'102','103') for i in (1,2,3)]
 right=[quote('lighter_rh',i*NS,'99','100',qty='.1') for i in (1,2,3)]
 s,r,e=replay('capture','SPY',left,right,1000,10,0)
 assert r[0]['exit_reason']=='HEDGE_FAILURE' and r[0]['net'] is None
 assert len(r[0]['fills'])==2 and r[0]['right_censored']

def test_replay_determinism_and_capture_isolation():
 left=[quote('arcus',i*NS,'102','103') for i in (1,2,3)]
 right=[quote('lighter_rh',i*NS,'99','100') for i in (1,2,3)]
 a=replay('one','SPY',left,right,1000,10,0);assert a==replay('one','SPY',left,right,1000,10,0)
 assert replay('two','SPY',left,right,1000,10,0)[1][0]['trade_id']!=a[1][0]['trade_id']
def test_convergence_closes_four_legs():
 left=[quote('arcus',NS,'102','103'),quote('arcus',2*NS,'100','101'),quote('arcus',3*NS,'100','101')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',2*NS,'100','101'),quote('lighter_rh',3*NS,'100','101')]
 s,r,e=replay('capture','SPY',left,right,1000,10,0)
 assert r[0]['exit_reason']=='BASIS_CONVERGED' and not r[0]['right_censored']
 assert [f['side'] for f in r[0]['fills']]==['sell','buy','buy','sell']
 assert all(D(x)==0 for x in r[0]['inventory'].values())
 assert D(r[0]['fees'])>0 and r[0]['net'] is not None

def test_stale_entry_is_rejected():
 left=[quote('arcus',NS,'102','103'),quote('arcus',3*NS,'102','103')]
 right=[quote('lighter_rh',NS,'99','100',source=(NS-600000000)//1000),quote('lighter_rh',3*NS,'99','100',source=(3*NS-600000000)//1000)]
 assert replay('capture','SPY',left,right,500,10,0)==([],[],[])

def test_delayed_hedge_does_not_cross_capture_end():
 left=[quote('arcus',NS,'102','103'),quote('arcus',NS+1000000,'102','103')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',NS+1000000,'99','100')]
 _,rows,events=replay('capture','SPY',left,right,500,10,100)
 assert rows[0]['right_censored'] and rows[0]['exit_reason']=='HEDGE_FAILURE'
 assert max(x['time_mono_ns'] for x in events)<=NS+1000000
def test_manifest_integrity_rejects_tampering(tmp_path):
 import json,hashlib,pytest
 from basis_convergence.capture import verify
 content=b'original';(tmp_path/'events.jsonl').write_bytes(content)
 (tmp_path/'manifest.json').write_text(json.dumps({'files':{'events.jsonl':{'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}}}))
 assert verify(tmp_path)['files']
 (tmp_path/'events.jsonl').write_bytes(b'tampered')
 with pytest.raises(ValueError,match='hash mismatch'):verify(tmp_path)

def test_stale_exit_censors_at_gap():
 left=[quote('arcus',NS,'102','103'),quote('arcus',2*NS,'100','101'),quote('arcus',3*NS,'100','101')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',2*NS,'100','101',source=(2*NS-700000000)//1000),quote('lighter_rh',3*NS,'100','101')]
 _,rows,events=replay('capture','SPY',left,right,500,10,0)
 assert rows[0]['exit_reason']=='BASIS_CONVERGED' and rows[0]['exit_ns']==3*NS
 assert any(x['event']=='DATA_GAP_STARTED' for x in events)
 assert any(x['event']=='DATA_GAP_RECOVERED' for x in events)
 assert not any(x['event']=='EXIT_FILLED' and x['time_mono_ns']<=2*NS for x in events)
def test_multilevel_vwap_matches_reference_for_both_sides():
 q=Quote('arcus','SPY',NS,NS,NS//1000,1,1,((D('99'),D('1')),(D('98'),D('2'))),((D('101'),D('1')),(D('102'),D('2'))))
 for side,expected in [('buy',D('101.5')),('sell',D('98.5'))]:
  amount,price=walk(q,side,D('2'))
  assert amount==2 and price==expected
  amount,price=walk(q,side,D('4'))
  assert amount==3 and abs(price-(D('305')/3 if side=='buy' else D('295')/3))<D('1e-10')
def test_gap_recovery_and_successful_exit_after_gap():
 left=[quote('arcus',NS,'102','103'),quote('arcus',4*NS,'100','101'),quote('arcus',5*NS,'100','101')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',4*NS,'100','101'),quote('lighter_rh',5*NS,'100','101')]
 _,rows,events=replay('g','SPY',left,right,500,10,0)
 r=rows[0];assert r['gap_recoveries']==1 and r['exit_reason']=='BASIS_CONVERGED' and r['exit_ns']==4*NS
 assert r['gaps'][0]['start_ns']==2*NS and r['gaps'][0]['end_ns']==4*NS
 assert not any(x['event']=='EXIT_FILLED' and 2*NS<=x['time_mono_ns']<4*NS for x in events)
 assert sum(x['event']=='DATA_GAP_ACTIVE' for x in events)==2

def test_grace_window_stops_execution_but_keeps_observation():
 left=[quote('arcus',NS,'102','103'),quote('arcus',4*NS,'100','101'),quote('arcus',5*NS,'100','101')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',4*NS,'100','101'),quote('lighter_rh',5*NS,'100','101')]
 _,rows,events=replay('g','SPY',left,right,500,10,0,gap_grace_s=1)
 assert rows[0]['right_censored'] and rows[0]['gap_recoveries']==1 and rows[0]['exit_opportunities']
 assert not any(x['event']=='EXIT_FILLED' for x in events)

def test_recovery_requires_full_depth():
 left=[quote('arcus',NS,'102','103'),quote('arcus',3*NS,'100','101',qty='.01'),quote('arcus',4*NS,'100','101')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',3*NS,'100','101'),quote('lighter_rh',4*NS,'100','101')]
 _,rows,_=replay('g','SPY',left,right,500,10,0)
 assert rows[0]['exit_ns']==4*NS and ['left','INSUFFICIENT_EXIT_DEPTH'] in rows[0]['gaps'][0]['reasons']

def test_multiple_separate_gaps_and_open_inventory():
 left=[quote('arcus',i*NS,'102','103') for i in (1,3,5,6)]
 right=[quote('lighter_rh',i*NS,'99','100') for i in (1,3,5,6)]
 _,rows,_=replay('g','SPY',left,right,500,10,0,max_hold_s=100)
 assert rows[0]['right_censored'] and rows[0]['gap_recoveries']==2 and len(rows[0]['gaps'])==2
 assert D(rows[0]['inventory']['arcus'])!=0

def test_stop_is_distinct_from_convergence_and_timeout():
 left=[quote('arcus',NS,'102','103'),quote('arcus',2*NS,'110','111'),quote('arcus',3*NS,'110','111')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',2*NS,'99','100'),quote('lighter_rh',3*NS,'99','100')]
 _,rows,_=replay('g','SPY',left,right,1000,10,0,exit_mode='stop')
 assert rows[0]['exit_reason']=='STOP_LOSS' and D(rows[0]['net'])<0

def test_zero_and_nonzero_fees_keep_gross_consistent():
 left=[quote('arcus',NS,'102','103'),quote('arcus',2*NS,'100','101'),quote('arcus',3*NS,'100','101')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',2*NS,'100','101'),quote('lighter_rh',3*NS,'100','101')]
 a=replay('g','SPY',left,right,1000,10,0,fee_left=D(0))[1][0];b=replay('g','SPY',left,right,1000,10,0,fee_left=D('2.25'))[1][0]
 assert a['gross']==b['gross'] and abs(D(a['net'])-D(b['net'])-D(b['fees']))<D('1e-26')

def test_diagnostic_reports_source_and_receive_reasons():
 from basis_convergence.engine import diagnose
 a=quote('arcus',NS);b=quote('lighter_rh',NS,source=(NS-600000000)//1000)
 assert ('right','SOURCE_TIMESTAMP_STALE') in diagnose(a,b,NS,500)
 assert ('pair','SOURCE_SKEW_EXCEEDED') in diagnose(a,b,NS,500)
 assert ('left','RECEIVE_TIMESTAMP_STALE') in diagnose(a,b,2*NS,500)

def test_capture_end_retains_unpriced_inventory():
 left=[quote('arcus',NS,'102','103'),quote('arcus',2*NS,'102','103')]
 right=[quote('lighter_rh',NS,'99','100'),quote('lighter_rh',2*NS,'99','100')]
 _,rows,_=replay('g','SPY',left,right,500,10,0,capture_end_ns=4*NS)
 assert rows[0]['right_censored'] and rows[0]['valuation_stale_at_capture_end']
 assert rows[0]['gaps'][-1]['recovered'] is False and rows[0]['net'] is None

def test_hedge_failure_emergency_is_counterfactual_and_preserves_inventory():
 left=[quote('arcus',i*NS,'102','103') for i in (1,2,3,4)]
 right=[quote('lighter_rh',i*NS,'99','100',qty='.1') for i in (1,2,3,4)]
 _,rows,events=replay('g','SPY',left,right,1000,10,0)
 r=rows[0];assert D(r['unhedged_notional_assumed'])>0
 assert r['emergency_close_scenario']['classification']=='HYPOTHETICAL_COUNTERFACTUAL'
 assert D(r['emergency_close_scenario']['remaining_hedge_qty'])==D('.1')
 assert len(r['fills'])==2 and not any(e['event']=='EXIT_FILLED' for e in events)

def test_extended_and_core_market_timestamps_and_deltas(tmp_path):
 import json,hashlib
 from basis_convergence.capture import read_extended_core
 meta={'markets':{'extended':{'BTC':{'name':'BTC-USD'}},'lighter_core':{'BTC':{'market_id':1}}}}
 (tmp_path/'discovery.json').write_text(json.dumps(meta))
 def row(v,seq,src,kind,body):
  msg=({'type':kind,'seq':seq,'ts':src,'data':body} if v=='extended' else {'type':kind,'channel':'order_book:1','order_book':body})
  return {'venue':v,'stream':'orderbooks/BTC' if v=='extended' else 'multiplex','market_id':'BTC-USD' if v=='extended' else '1','segment_id':1,'received_mono_ns':seq*NS,'received_utc_ns':seq*NS,'source_timestamp':src,'source_timestamp_unit':'ms_system_generated' if v=='extended' else 'us_UNVERIFIED','sequence':seq,'message':msg}
 ext=[row('extended',1,1000,'SNAPSHOT',{'m':'BTC-USD','b':[{'p':'100','q':'2'}],'a':[{'p':'101','q':'2'}]}),row('extended',2,2000,'DELTA',{'m':'BTC-USD','b':[{'p':'100','c':'1'}],'a':[]})]
 core=[row('lighter_core',1,1000000,'subscribed/order_book',{'nonce':1,'last_updated_at':1000000,'bids':[['100','2']],'asks':[['101','2']]}),row('lighter_core',2,2000000,'update/order_book',{'nonce':2,'begin_nonce':1,'last_updated_at':2000000,'bids':[['100','1']],'asks':[]})]
 for name,rows in [('extended',ext),('lighter_core',core)]: (tmp_path/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
 files={}
 for f in tmp_path.iterdir():
  data=f.read_bytes();files[f.name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
 (tmp_path/'manifest.json').write_text(json.dumps({'files':files}))
 _,books,quality=read_extended_core(tmp_path)
 assert books[('extended','BTC')][0].source==books[('lighter_core','BTC')][0].source==1000000
 assert books[('extended','BTC')][-1].bids[0][1]==books[('lighter_core','BTC')][-1].bids[0][1]==D('1.0')
 assert quality['extended:accepted']==quality['lighter_core:accepted']==2


def test_txflow_full_snapshot_has_no_invented_sequence_and_keeps_both_venues(tmp_path):
 import hashlib,json
 from basis_convergence.capture import read_extended_core
 meta={'markets':{'txflow':{'BTC':{'name':'BTC-USDC','index':1}},'lighter_core':{'BTC':{'market_id':1}}}}
 (tmp_path/'discovery.json').write_text(json.dumps(meta))
 mono=10*NS
 tx={'venue':'txflow','stream':'orderbook','market_id':'1','segment_id':1,'received_mono_ns':mono,'received_utc_ns':mono,'source_timestamp':1000,'source_timestamp_unit':'ms_documented','sequence':None,'message':{'channel':'l2Book','type':'l2Book','data':{'coin':'BTC-USDC','time':1000,'levels':[[{'px':'100','sz':'2'}],[{'px':'101','sz':'3'}]]}}}
 core={'venue':'lighter_core','stream':'orderbook','market_id':'1','segment_id':1,'received_mono_ns':mono,'received_utc_ns':mono,'source_timestamp':1000000,'source_timestamp_unit':'us_UNVERIFIED','sequence':1,'message':{'channel':'order_book:1','type':'subscribed/order_book','order_book':{'nonce':1,'last_updated_at':1000000,'bids':[['100','2']],'asks':[['101','3']]}}}
 for name,row in [('txflow',tx),('lighter_core',core)]: (tmp_path/(name+'.jsonl')).write_text(json.dumps(row)+'\n')
 files={}
 for f in tmp_path.iterdir():
  content=f.read_bytes();files[f.name]={'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}
 (tmp_path/'manifest.json').write_text(json.dumps({'files':files}))
 _,books,quality=read_extended_core(tmp_path,'txflow')
 left=books[('txflow','BTC')][0];right=books[('lighter_core','BTC')][0]
 assert left.source==1000000 and left.sequence is None
 assert left.bids[0][1]==D('2.0') and left.asks[0][1]==D('3.0')
 assert right.sequence==1 and right.source==1000000
 assert quality['txflow:accepted']==quality['lighter_core:accepted']==1
