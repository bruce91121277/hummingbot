# Phase 14F — TxFlow x Lighter Core convergence

All executions are hypothetical. No rewards are counted as income.

## Data and interpretation

Manifest-verified captures: 5; event-pair rows: 84663; valid synchronized 500ms rows: 40337; 10bps BBO candidates: 38198.
The Lighter source clock is assumed to be microseconds and clock synchronization is unverified. TxFlow documents full l2Book snapshots with millisecond source time. Lighter market multiplier metadata is not enough to establish contract units or settlement conversion.
Persistent raw spread is therefore only a directional basis candidate. TxFlow publishes full l2Book snapshots on a documented millisecond clock; Lighter snapshot/delta nonce continuity is checked by the reader, while its source clock unit and cross-venue clock synchronization remain unverified. The capture summary retains each venue's update interval, error list, and connection segments. A contract-symbol match does not prove matching index or settlement economics.

## Costs

At the assumed TxFlow taker fee of 4.5bps and Lighter 0bps, fee-only round-trip break-even is 9bps before L2 spread and depth impact. Each trade's same-basis executable four-leg L2 cost is listed in breakeven_requirements.csv.

## Reproducibility

Replay historical, exploration and holdout captures as separate capture roots. Positions never carry across capture boundaries.


## Event-driven, 600-second strategy comparison

These counts aggregate independent captures; positions never cross capture boundaries. Fees are hypothetical and rewards are excluded.

| Group | Strategy | Fee | Signals | Paired | Closed (conv/net/stop/timeout) | Censored | Hedge failures | Closed net quote |
|---|---|---|---:|---:|---:|---:|---:|---:|
| exploration | basis_le_2bps | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1701744728788677181664047764 |
| exploration | basis_le_2bps | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | 0.00975925764075149036710764 |
| exploration | convergence_25 | txflow_4_5bps | 4 | 4 | 3 (1/0/0/2) | 1 | 0 | -0.2357101269643320831559454435 |
| exploration | convergence_25 | zero | 4 | 4 | 3 (1/0/0/2) | 1 | 0 | 0.03435016822321467594139264 |
| exploration | convergence_50 | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1701744728788677181664047764 |
| exploration | convergence_50 | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | 0.00975925764075149036710764 |
| exploration | convergence_and_net_positive | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1701744728788677181664047764 |
| exploration | convergence_and_net_positive | zero | 4 | 4 | 3 (1/0/0/2) | 1 | 0 | 0.03435016822321467594139264 |
| exploration | net_profit_positive | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1701744728788677181664047764 |
| exploration | net_profit_positive | zero | 8 | 7 | 7 (0/7/0/0) | 1 | 1 | 0.01395221728677813040780230 |
| exploration | stop_loss_10bps | txflow_4_5bps | 23 | 22 | 22 (4/0/18/0) | 1 | 1 | -2.039653730539677502772908629 |
| exploration | stop_loss_10bps | zero | 4 | 4 | 3 (1/0/0/2) | 1 | 0 | 0.03435016822321467594139264 |
| exploration | timeout | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1701744728788677181664047764 |
| exploration | timeout | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | 0.00975925764075149036710764 |
| historical | basis_le_2bps | txflow_4_5bps | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | basis_le_2bps | zero | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | convergence_25 | txflow_4_5bps | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | convergence_25 | zero | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | convergence_50 | txflow_4_5bps | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | convergence_50 | zero | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | convergence_and_net_positive | txflow_4_5bps | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | convergence_and_net_positive | zero | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | net_profit_positive | txflow_4_5bps | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | net_profit_positive | zero | 13 | 12 | 10 (0/10/0/0) | 3 | 1 | 0.01256500096661630877313240 |
| historical | stop_loss_10bps | txflow_4_5bps | 6 | 6 | 3 (0/0/3/0) | 3 | 0 | -0.3020389147903447021938974070 |
| historical | stop_loss_10bps | zero | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | timeout | txflow_4_5bps | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| historical | timeout | zero | 3 | 3 | 0 (0/0/0/0) | 3 | 0 | 0 |
| holdout | basis_le_2bps | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1940454772183007070346361763 |
| holdout | basis_le_2bps | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.01395852268437228855883980 |
| holdout | convergence_25 | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1940454772183007070346361763 |
| holdout | convergence_25 | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.01395852268437228855883980 |
| holdout | convergence_50 | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1940454772183007070346361763 |
| holdout | convergence_50 | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.01395852268437228855883980 |
| holdout | convergence_and_net_positive | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1940454772183007070346361763 |
| holdout | convergence_and_net_positive | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.01395852268437228855883980 |
| holdout | net_profit_positive | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1940454772183007070346361763 |
| holdout | net_profit_positive | zero | 7 | 6 | 6 (0/6/0/0) | 1 | 1 | 0.00730071564794045955479690 |
| holdout | stop_loss_10bps | txflow_4_5bps | 12 | 11 | 11 (0/0/11/0) | 1 | 1 | -1.142927655375572026062031513 |
| holdout | stop_loss_10bps | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.01395852268437228855883980 |
| holdout | timeout | txflow_4_5bps | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.1940454772183007070346361763 |
| holdout | timeout | zero | 3 | 3 | 2 (0/0/0/2) | 1 | 0 | -0.01395852268437228855883980 |