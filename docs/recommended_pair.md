# TxFlow x Lighter Core: Phase 14E capture review

Reviewed 2026-10-29 UTC. This is public-data, hypothetical research. The three manifest-verified captures cover about 660 seconds in separate, non-contiguous sessions and contain 11,811 events: 535 TxFlow and 11,276 Lighter Core. That is about 0.81 and 17.08 events per recorded second, respectively. No prices are joined across capture boundaries.

TxFlow documents its BTC-USDC linear perpetual, one underlying unit, hourly funding default and full-snapshot l2Book feed with millisecond timestamps. Its published VIP0 taker rate is 4.5 bps per fill. Lighter Core's timestamp conversion to microseconds, clock alignment, economic multiplier, settlement conversion and actual fee remain unverified. Thus the 500/1000 ms gates are sensitivity assumptions, not verified cross-venue clocks. [TxFlow contract specification](https://docs.txflow.com/trade/contract-specifications), [TxFlow book feed](https://docs.txflow.com/api/websocket/l2Book), [TxFlow fees](https://docs.txflow.com/trade/fees).

At the engine's 1-second decision interval, the 500 ms diagnostic recorded 200 unique synchronized quote pairs, all with a sampled edge of at least 10 bps under the engine's BBO formula. The 1000 ms sensitivity recorded 360 windows, 359 with sampled edge at least 10 bps. These are correlated windows, not independent trade opportunities or proof that the contracts are economically interchangeable. Entry-rejection reason counts are repeated decision-sample observations and may overlap: TxFlow receive stale 428, source stale 455, source skew 396, and receive skew 401.

| Scenario | Signals | Closed | Exit result | Closed gross | Closed fees | Closed net |
|---|---:|---:|---|---:|---:|---:|
| 500 ms, TxFlow taker 4.5 bps, Lighter 0 assumed | 7 | 4 | 4 timeouts; 0 convergence; 3 censored | -0.016382 | 0.359954 | -0.376335 |
| 500 ms, both fees 0 assumed | 7 | 4 | 4 timeouts; 0 convergence; 3 censored | -0.016382 | 0 | -0.016382 |
| 1000 ms, TxFlow taker 4.5 bps, Lighter 0 assumed | 7 | 4 | 4 timeouts; 0 convergence; 3 censored | -0.009149 | 0.359954 | -0.369102 |

All PnL values above are hypothetical quote units. The nonzero-fee run incurred 0.135 quote units of entry fees across the three censored positions, so total recorded fees including open entries were 0.494954. Two censored positions held paired inventory at capture end; their last liquidation estimates were stale at the end under the 500 ms valuation rule. The third was a one-leg hedge failure with approximately 100 assumed notional exposed. A later hypothetical emergency close estimated -0.076107 quote units at the 4.5 bps fee assumption (or +0.013899 at zero fees); neither is an actual fill or realized PnL.

The four closed trades all exited by MAX_HOLD_TIMEOUT. No trade exited because basis convergence was detected. Even with zero fees, their aggregate gross result was negative. At 1000 ms, trade counts did not improve; the net difference came from sampling different exit quotes. Gap counts rose from 137 episodes / 135 recoveries at 500 ms to 158 / 157 at 1000 ms. Greater tolerance admits more sampled quote windows but does not resolve source clock uncertainty.

Decision: keep TxFlow x Lighter Core as a capture-validation route, not as a strategy with demonstrated edge. TxFlow averaged about 0.81 book events/s over these captures, while most sampled entry checks failed freshness or skew reasons. Add longer captures across independent sessions and verify Lighter timestamps, contract units, fee schedule and settlement before evaluating convergence profitability. The paired BTC labels alone do not prove hedge compatibility. The zero-fee and actual-fee-schedule scenarios do not establish positive net returns.

Reproduction:

    cd ~/perp-arbitrage-hb
    .venv-research/bin/python -m basis_convergence.research       --capture-root ~/perp-arbitrage/data/phase14e       --route txflow_lighter_core --mode hypothetical       --freshness-ms 500 --output outputs/phase14e-replay-rerun
