"""Read-only, standalone hypothetical Arcus/Lighter RH replay."""
import argparse,csv,json
from pathlib import Path
from decimal import Decimal as D
from basis_convergence.capture import read_capture
from basis_convergence.engine import replay,latest,fresh,NS

def main():
 p=argparse.ArgumentParser();p.add_argument('--capture-root',type=Path,required=True);p.add_argument('--route',choices=['arcus_lighter_rh'],required=True);p.add_argument('--mode',choices=['hypothetical'],required=True);p.add_argument('--freshness-ms',type=int,choices=[100,250,500,1000],default=500);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 if args.output.exists() and any(args.output.iterdir()):raise ValueError('output directory must be empty')
 args.output.mkdir(parents=True,exist_ok=True);paths=sorted(x for x in args.capture_root.rglob('capture_*') if x.is_dir() and not x.is_symlink()) if args.capture_root.is_dir() else []
 if (args.capture_root/'manifest.json').is_file():paths=[args.capture_root]
 captures=[];excluded=[];trades=[];events=[];signals=[];stats={str(n):{'samples':0,'positive':0,'edge_ge_10':0} for n in (100,250,500,1000)}
 for path in paths:
  try:manifest,books,quality=read_capture(path)
  except (ValueError,OSError,KeyError,TypeError) as exc:excluded.append({'capture':path.name,'reason':str(exc)});continue
  captures.append({'capture':path.name,'events':manifest.get('events'),'quality':quality})
  for market in ('SPY','QQQ','NVDA','SNDK'):
   left=books.get(('arcus',market),[]);right=books.get(('lighter_rh',market),[])
   if not left or not right:continue
   for t in range(max(left[0].mono,right[0].mono),min(left[-1].mono,right[-1].mono),NS):
    a=latest(left,t);b=latest(right,t)
    if not a or not b or not a.bids or not b.bids:continue
    edge=max((a.bids[0][0]-b.asks[0][0])/b.asks[0][0]*10000,(b.bids[0][0]-a.asks[0][0])/a.asks[0][0]*10000)
    for n in (100,250,500,1000):
     if fresh(a,b,t,n):stats[str(n)]['samples']+=1;stats[str(n)]['positive']+=edge>0;stats[str(n)]['edge_ge_10']+=edge>=10
   s,r,e=replay(path.name,market,left,right,args.freshness_ms);signals.extend(s);trades.extend(r);events.extend(e)
 def write(name,rows):
  fields=list(dict.fromkeys(k for row in rows for k in row))
  with (args.output/name).open('w',newline='') as f:
   if fields:
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in rows)
 write('spread_signals.csv',signals);write('convergence_trades.csv',trades);write('execution_events.csv',events);write('fee_attribution.csv',trades);write('residual_positions.csv',[x for x in trades if x['right_censored']])
 result={'classification':'HYPOTHETICAL','captures':captures,'excluded':excluded,'freshness_ms':args.freshness_ms,'freshness_sensitivity':stats,'signals':len(signals),'trades':len(trades),'closed':sum(not x['right_censored'] for x in trades),'censored':sum(x['right_censored'] for x in trades),'limitations':'Source timestamps assumed microseconds and synchronized clocks; Arcus book snapshot semantics and contract economics UNVERIFIED. One-second decisions, 100ms book sampling. Position accounting is isolated hypothetical ledger; all legs taker; funding assumed zero. Formal eligibility unchanged. No private APIs or live orders.'}
 (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(args.output/'report.md').write_text('# Standalone hypothetical research\n\n'+result['limitations']+'\n\n'+json.dumps({k:result[k] for k in ('freshness_ms','freshness_sensitivity','signals','trades','closed','censored')},indent=2)+'\n');print(json.dumps({k:result[k] for k in ('freshness_ms','signals','trades','closed','censored')}))
if __name__=='__main__':main()