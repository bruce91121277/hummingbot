"""Public capture replay; all executions are explicitly hypothetical."""
import argparse,csv,json
from collections import Counter
from datetime import datetime
from pathlib import Path
from decimal import Decimal as D
from basis_convergence.capture import read_capture
from basis_convergence.engine import replay,latest,fresh,diagnose,NS

def main():
 p=argparse.ArgumentParser();p.add_argument('--capture-root',type=Path,required=True);p.add_argument('--route',choices=['arcus_lighter_rh'],required=True);p.add_argument('--mode',choices=['hypothetical'],required=True);p.add_argument('--freshness-ms',type=int,choices=[100,250,500,1000],default=500);p.add_argument('--gap-grace-s',type=float,default=None);p.add_argument('--exit-mode',choices=['percent','basis','net','combined','stop'],default='percent');p.add_argument('--exit-fraction',type=D,choices=[D('.25'),D('.5')],default=D('.25'));p.add_argument('--left-fee-bps',type=D,choices=[D(0),D('2.25')],default=D('2.25'));p.add_argument('--max-hold-s',type=int,default=120);p.add_argument('--stop-bps',type=D,default=D('10'));p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 if args.output.exists() and any(args.output.iterdir()):raise ValueError('output directory must be empty')
 args.output.mkdir(parents=True,exist_ok=True);paths=sorted(x for x in args.capture_root.rglob('capture_*') if x.is_dir() and not x.is_symlink()) if args.capture_root.is_dir() else []
 if (args.capture_root/'manifest.json').is_file():paths=[args.capture_root]
 captures=[];excluded=[];trades=[];events=[];signals=[];gaps=[];opps=[];entry_quality=Counter();stats={str(n):{'samples':0,'positive':0,'edge_ge_10':0} for n in (100,250,500,1000)}
 for path in paths:
  try:manifest,books,quality=read_capture(path)
  except (ValueError,OSError,KeyError,TypeError) as exc:excluded.append({'capture':path.name,'reason':str(exc)});continue
  captures.append({'capture':path.name,'events':manifest.get('events'),'quality':quality})
  for market in ('SPY','QQQ','NVDA','SNDK'):
   left=books.get(('arcus',market),[]);right=books.get(('lighter_rh',market),[])
   if not left or not right:continue
   anchor=left[-1];capture_end=max(left[-1].mono,right[-1].mono)
   if manifest.get('end_utc'):
    end_utc=int(datetime.fromisoformat(manifest['end_utc']).timestamp()*NS);capture_end=max(capture_end,anchor.mono+end_utc-anchor.utc)
   for t in range(max(left[0].mono,right[0].mono),min(left[-1].mono,right[-1].mono),NS):
    a=latest(left,t);b=latest(right,t)
    for venue,reason in diagnose(a,b,t,args.freshness_ms):entry_quality[venue+':'+reason]+=1
    if not a or not b or not a.bids or not b.bids:continue
    edge=max((a.bids[0][0]-b.asks[0][0])/b.asks[0][0]*10000,(b.bids[0][0]-a.asks[0][0])/a.asks[0][0]*10000)
    for n in (100,250,500,1000):
     if fresh(a,b,t,n):stats[str(n)]['samples']+=1;stats[str(n)]['positive']+=edge>0;stats[str(n)]['edge_ge_10']+=edge>=10
   s,r,e=replay(path.name,market,left,right,args.freshness_ms,exit_fraction=args.exit_fraction,max_hold_s=args.max_hold_s,gap_grace_s=args.gap_grace_s,exit_mode=args.exit_mode,fee_left=args.left_fee_bps,stop_bps=args.stop_bps,capture_end_ns=capture_end);signals.extend(s);trades.extend(r);events.extend(e)
   for row in r:gaps.extend(row['gaps']);opps.extend(row['exit_opportunities'])
 def write(name,rows):
  fields=list(dict.fromkeys(k for row in rows for k in row))
  with (args.output/name).open('w',newline='') as f:
   if fields:
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in rows)
 write('spread_signals.csv',signals);write('convergence_trades.csv',trades);write('execution_events.csv',events);write('fee_attribution.csv',trades);write('residual_positions.csv',[x for x in trades if x['right_censored']]);write('data_gaps.csv',gaps);write('gap_recovery.csv',[g for g in gaps if g['recovered']]);write('exit_opportunities.csv',opps)
 gap_quality={}
 for gap in gaps:
  for venue,reason in gap['reasons']:
   k=venue+':'+reason;v=gap_quality.setdefault(k,{'episodes':0,'episode_duration_upper_bound_seconds':0});v['episodes']+=1;v['episode_duration_upper_bound_seconds']+=float(gap['duration_seconds'])
 result={'classification':'HYPOTHETICAL','captures':captures,'excluded':excluded,'freshness_ms':args.freshness_ms,'gap_grace_s':args.gap_grace_s,'exit_mode':args.exit_mode,'exit_fraction':str(args.exit_fraction),'left_fee_bps':str(args.left_fee_bps),'freshness_sensitivity':stats,'entry_rejection_sample_reasons':dict(entry_quality),'gap_reasons':gap_quality,'signals':len(signals),'trades':len(trades),'closed':sum(not x['right_censored'] for x in trades),'censored':sum(x['right_censored'] for x in trades),'gap_episodes':len(gaps),'gap_recoveries':sum(g['recovered'] for g in gaps),'limitations':'Source timestamps assumed microseconds and synchronized clocks; Arcus book snapshot semantics and contract economics UNVERIFIED. One-second decisions, 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.'}
 (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(args.output/'report.md').write_text('# Hypothetical convergence with missing-data recovery\n\n'+result['limitations']+'\n\n'+json.dumps({k:result[k] for k in ('freshness_ms','exit_mode','left_fee_bps','signals','trades','closed','censored','gap_episodes','gap_recoveries','gap_reasons')},indent=2)+'\n');print(json.dumps({k:result[k] for k in ('freshness_ms','signals','trades','closed','censored','gap_episodes','gap_recoveries')}))
if __name__=='__main__':main()