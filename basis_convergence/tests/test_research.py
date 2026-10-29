from decimal import Decimal as D
from basis_convergence.research import hb_walk
from perp_arb.phase13_hedge_replay import Book,walk

def test_hummingbot_depth_and_partial_fill():
 b=Book(1,((D('99'),D('1')),(D('98'),D('2'))),((D('101'),D('1')),(D('102'),D('2'))),1)
 for side in ('buy','sell'):
  for q in (D('0.5'),D('2'),D('4')):
   old=walk(b,side,q);new=hb_walk(b,side,q)
   assert old['quantity']==new['quantity'] and old['unfilled']==new['unfilled']
   assert abs(old['vwap']-new['vwap'])<D('0.000000001')