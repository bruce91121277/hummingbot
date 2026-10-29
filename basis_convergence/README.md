# Phase 14B — isolated hypothetical convergence replay

Fork: https://github.com/bruce91121277/hummingbot, branch `research/basis-convergence`. Upstream baseline `9af100d6822da7d2d0291a906c730ef172284ee2`. Hummingbot LICENSE remains unchanged.

This program reads public captures directly and verifies each manifest file set, SHA256 and size. It does not import or execute the legacy `perp-arbitrage` code. Data may reside anywhere; the command below points at historical Oracle captures. It reconstructs Arcus snapshot messages and Lighter RH snapshot/delta messages using Hummingbot `OrderBook`, then runs an isolated deterministic hypothetical ledger and event state machine. Unknown sequence continuity invalidates the book until the next snapshot. Books are sampled at 100 ms; decisions are taken every second.

```sh
cd ~/perp-arbitrage-hb
python3 -m venv --system-site-packages .venv-research
.venv-research/bin/python -m pip install pandas cython sortedcontainers hexbytes cachetools ujson
.venv-research/bin/python basis_convergence/build_core.py build_ext --inplace
.venv-research/bin/python -m pytest -q basis_convergence/tests test/hummingbot/core/data_type/test_order_book.py
.venv-research/bin/python -m basis_convergence.research \
  --capture-root ~/perp-arbitrage/data/phase13-6a8-public \
  --route arcus_lighter_rh --mode hypothetical --freshness-ms 500 \
  --output outputs/phase14b-repeat
```

Output directories must be empty. `--freshness-ms` accepts 100, 250, 500 or 1000 and applies the same bound to each source age, each receive age, inter-venue source skew and inter-venue receive skew at entry, delayed hedge and exit. Missing, future or stale quotes cannot fill; positions remain censored after gaps or hedge failure. Event identifiers, timestamps, venues, markets, fills, fees and inventory are retained. No position crosses a capture. A hypothetical ledger deduplicates fill IDs. The 25% contraction exit and 120 s timeout are separate. Funding is assumed zero; 1:1 economic quantity and quote conversion are assumed, not verified. All legs are taker: Arcus 2.25 bps, Lighter RH zero; rates are scenario inputs and not account-verified. Unknown current quotes or depth means liquidation estimate is unknown rather than zero.

Source timestamps are interpreted as microseconds, and the two source clocks and Oracle clock are assumed synchronized. These assumptions, Arcus snapshot semantics and economic contract equivalence remain UNVERIFIED; no result is a qualified Paper or verified USD result. There is no private API, order connector, wallet access or live execution.

For the 302-second sample, 500 ms resulted in zero entries. Sensitivity (100/250/500/1000 ms) produced 0/0/0/1 one-second windows at least 10 bps. At 1000 ms one SNDK scenario opened and closed, gross 0.0294604715, fees 0.0450029367, net -0.0155424652 in hypothetical quote units. This one unverified outcome does not establish profitability.

Legacy Phase 14 used receive-time gates but only diagnosed source freshness. Its one unfiltered trade is not a valid matched-condition 500 ms parity comparison. Both its diagnostic and the new 500 ms gate report zero >=10 bps opportunities for this sample; this is signal-count agreement, not trade-by-trade execution parity.

Limitations: only Arcus × Lighter RH and 25% contraction are implemented; Extended × Lighter Core, Maker execution, configurable stop loss/net target/funding schedule, fee currency conversions, portfolio capital and verified liquidation estimates remain incomplete. The old Phase 14 bridge and its results remain in Git history; it is not a runtime dependency. Full upstream suite and full Hummingbot installation have not been validated. Source-clock validation and independent long captures are needed before strategy conclusions.
## Historical root, 500 ms

Fourteen manifests verified and two captures were excluded. The four-symbol diagnostic counted 2,172 accepted one-second windows, 104 of which reached 10 bps; windows are not independent trades. The state machine opened five hypothetical trades, all right-censored on data gaps, with no completed PnL. Entry fees total approximately 0.11250008 assumed quote units, excluding unknown future exit costs. Signed venue inventories and any last available liquidation estimate are in `outputs/phase14b-history-full/residual_positions.csv`; a past estimate is not a current close price.

The earlier Phase 14 freshness diagnostic also counted 104 windows at 500 ms, but its trading run did not apply that gate. This is not matched-condition trade parity; a gated legacy comparison remains outstanding. The isolated ledger and new tests do not replace a complete upstream test suite.

## Phase 14C

See `outputs/phase14c/report.md` for gap recovery results, research limits and reproduction. The 500 ms and 1000 ms runs are separate. No private exchange API or live trading is used.

## Phase 14E - venue screening and TxFlow public capture

The public-only TxFlow reader is `basis_convergence.txflow_capture`. It discovers BTC-USDC and Lighter Core BTC from public metadata, records bounded L2 snapshots with receive/source timestamps and segment IDs, and hashes every capture file in a manifest. It never loads wallet credentials or trading endpoints. TxFlow documents linear perpetuals with one underlying unit and describes each `l2Book` push as a full snapshot with millisecond source time; the capture itself retains no sequence for TxFlow. Lighter source-time units and cross-venue clock alignment remain assumptions.

Capture at most five minutes per run:

```sh
cd ~/perp-arbitrage-hb
.venv-research/bin/python -m basis_convergence.txflow_capture \
  --output-root ~/perp-arbitrage/data/phase14e \
  --seconds 300
```

Replay the retained capture with the same 500 ms gate and explicit hypothetical fees:

```sh
.venv-research/bin/python -m basis_convergence.research \
  --capture-root ~/perp-arbitrage/data/phase14e \
  --route txflow_lighter_core --mode hypothetical \
  --freshness-ms 500 --output outputs/phase14e-replay-500
```

The Oct 29, 2026 review found 2 manifest-valid captures (6,557 events total: TxFlow 298, Lighter Core 6,259). At 500 ms the replay produced 4 hypothetical entries, 2 timeouts and 2 capture-end censored positions; no trade exited for convergence. With the documented TxFlow VIP0 taker rate of 4.5 bps and a zero-fee Lighter scenario, both timeout PnLs were negative (combined net -0.186234 quote units). The zero-fee scenario still had a combined gross result of -0.006274 quote units. These are tiny-sample hypothetical units, not verified USD PnL; no profitability claim follows.

See `docs/reward_eligibility.md`, `docs/recommended_pair.md`, and `outputs/phase14e-screening/` for current venue evidence and limitations.
