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