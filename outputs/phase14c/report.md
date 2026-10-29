# Phase 14C — hypothetical gap recovery research

All executions, economics, 1:1 inventory and fees are hypothetical. This replay uses 14 integrity-eligible captures, excluding 2. The received timestamps are monotonic; source timestamps are assumed microseconds, with source clock synchronization and Arcus book semantics unverified. Decisions are sampled each second and hedge execution uses a 100 ms delay. A gap makes prices and stop states unknown, and recoveries do not imply that no convergence happened inside the gap. Capture-end estimates may be stale. Funding assumed zero. Independent captures are never joined.

## Baseline five previously censored positions

| Capture / market | Quote recoveries | Result under 500 ms, 25% convergence, 120 s maximum | Four-leg net or last liquidation estimate |
|---|---:|---|---:|
| 20261027T090443 d2bc56 / QQQ | 9 | Capture ended open | -0.050970 (stale estimate) |
| 20261027T090549 fad661 / SPY | 23 | Timeout exit | -0.046314 net |
| 20261027T090549 fad661 / QQQ | 27 | Timeout exit | -0.053432 net |
| 20261028T020128 5dec44 / QQQ | 0 | Capture ended open | -0.050536 (stale estimate) |
| 20261028T020246 b2bcbd / QQQ | 2 | Capture ended open | -0.045003 (stale estimate) |

Four positions recovered quotes; none triggered 25% convergence before modeled exit or capture end. This does not rule out an unobserved crossing during a gap. All three open estimates above use the last eligible book, which was stale at capture end. No completed convergence trade exists for the baseline five, so a four-leg convergence PnL cannot be calculated.

## Whole-sample scenarios

| Scenario | Entries | Completed | Open | Exit causes | Completed net |
|---|---:|---:|---:|---|---:|
| 500 ms; Arcus 2.25 bps, RH 0 | 8 | 3 | 5 | 3 timeout, 4 capture end, 1 hedge failure | -0.158785 |
| 500 ms; zero fees | 8 | 3 | 5 | 3 timeout, 4 capture end, 1 hedge failure | -0.023769 |
| 1000 ms; Arcus 2.25 bps, RH 0 | 9 | 3 | 6 | 2 timeout, 1 convergence, 4 capture end, 2 hedge failures | -0.121500 |

The 1000 ms converged trade net was -0.027734; it is not part of the 500 ms main result. Sum of closed positions excludes unresolved inventory and therefore is not total strategy PnL. With the specified 2.25 bps fee scenario, 25%, 50%, 2 bps, net-positive, combined, and stop-mode runs each produced 3 timeouts and 5 censored positions at default thresholds; same totals do not establish profitability. Fixed per-leg assumed starting size is approximately 100 quote units.

Among position gaps at 500 ms, Arcus (left) source staleness occurred in 88 of 97 gap episodes versus 22 involving Lighter RH (right). Reasons overlap, source clocks are unverified, and these counts identify observed timestamps rather than proving the responsible system. Entry rejection diagnostics are sampled independently and must not be added as mutually exclusive counts. Per-reason episode durations are upper bounds because reasons can change or overlap in an episode.

The sample does not demonstrate a reliable profitable Arcus/RH convergence strategy. Collect longer, clock-verified public data and validate book semantics; compare Extended/Core with the same engine after implementing its adapter. Extended/Core was not replayed in Phase 14C and no parity result is claimed. One-leg hedge failures retain inventory but do not yet receive later gap recovery or liquidation valuation. The stop-loss condition and price path are unknown inside gaps. Funding is an explicit zero scenario, not an observed settlement.

## Reproduce

```bash
cd ~/perp-arbitrage-hb
.venv-research/bin/python -m pytest -q basis_convergence/tests test/hummingbot/core/data_type/test_order_book.py
.venv-research/bin/python -m basis_convergence.research --capture-root ~/perp-arbitrage/data/phase13 --route arcus_lighter_rh --mode hypothetical --freshness-ms 500 --output outputs/phase14c-new
```

Use a new empty output directory. Compare 1000 ms with `--freshness-ms 1000`, zero Arcus fee with `--left-fee-bps 0`, other exits with `--exit-mode basis|net|combined|stop`, 50% with `--exit-fraction .5`, and stop threshold with `--stop-bps`. `--gap-grace-s` disables subsequent simulated exits after the grace window while preserving later valid-quote diagnostics. CSV timestamps remain original monotonic nanoseconds.
