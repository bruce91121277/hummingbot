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
 assert r[0]['exit_reason']=='DATA_GAP' and r[0]['net'] is None and r[0]['right_censored']
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
 assert rows[0]['exit_reason']=='DATA_GAP' and rows[0]['exit_ns'] is None
 assert [x['event'] for x in events][-2:]==['DATA_GAP','POSITION_CENSORED']