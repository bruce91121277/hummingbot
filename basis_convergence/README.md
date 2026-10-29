# Phase 14: Hummingbot core research bridge (partial)

Upstream: https://github.com/hummingbot/hummingbot, commit 9af100d6822da7d2d0291a906c730ef172284ee2. LICENSE is retained unchanged. Research branch is local; no personal fork has been established. No private credentials, live service or orders were used.

Oracle is aarch64, Python 3.10.12, GCC and G++ available; Rust/Cargo and Conda not found. Full Hummingbot is not installed or validated. The isolated `.venv-research` includes pandas, Cython, sortedcontainers, hexbytes, cachetools and ujson; it uses system site packages including numpy, pytest, aiohttp and websockets. Compile only Hummingbot's event listener, PubSub, order book query and C++ order book:

```sh
cd ~/perp-arbitrage-hb
python3 -m venv --system-site-packages .venv-research
.venv-research/bin/python -m pip install pandas cython sortedcontainers hexbytes cachetools ujson
.venv-research/bin/python basis_convergence/build_core.py build_ext --inplace
.venv-research/bin/python -m pytest -q basis_convergence/tests test/hummingbot/core/data_type/test_order_book.py
.venv-research/bin/python -m basis_convergence.research --capture-root ~/perp-arbitrage/data/phase13-6a8-public --route arcus_lighter_rh --mode hypothetical --output outputs/phase14-repeat
```

This depends on the unchanged legacy checkout at `~/perp-arbitrage`. Outputs must be new/empty directories. The program only loads manifest-verified data and uses the old loader, old state machine, order tracking, fee and journal. It replaces the legacy depth walk with the compiled Hummingbot OrderBook and get_vwap_for_volume. This is a hybrid comparison, not an independent Hummingbot strategy or Hummingbot execution/fee framework. Lighter Core connector exists and points to mainnet.zklighter.elliot.ai; it is not a Lighter RH adapter. Arcus and RH are imported through the legacy offline loader; no public Hummingbot connectors were created.

The 302-second capture produced 0 eligible 10-bps windows under assumed 100, 250 and 500 ms source-age and source-skew limits; at 1000 ms it produced 1. These thresholds are diagnostic only and are not applied to trade generation. Source timestamp unit is assumed microseconds; clock alignment, source semantics, Arcus book semantics, contract multipliers, fee rates and 1:1 conversion remain unverified.

Without the source-age filter, the 25%-convergence scenario generated one SNDK entry/exit at 1 s. Gross +0.0294604715, hypothetical fees 0.0450029367, net -0.0155424652 assumed quote units, zero open positions. Legacy net -0.0155424652374698 versus HB VWAP -0.0155424652374251; difference approximately 4.48e-14, consistent with HB float conversion. This is one unfiltered model example, not validated economic profit. No maker orders or settlement funding are modeled. Files labeled attribution reproduce the full trade rows; they do not provide separate economic cost decomposition.

Source timestamps are preserved for sampled candidate signals, not for every converted or rejected event. The loader verifies original manifest and uses reconstructed top-20 sampled snapshots. No full JSONL converter, HB-native event execution, HB-native account ledger, standalone convergence controller, public connectors, source-time-gated execution, independent four-leg funding/partial hedge/cancellation model, full upstream test suite or live deployment is supplied. Those remain required before claiming Phase 14 is complete.
## Existing 14-capture comparison

The historical root produced 14 manifest-verified captures and 2 exclusions. The 25% legacy-state-machine/Hummingbot-VWAP scenario generated 8 entries: 3 closed and 5 censored. Signal times and exit reasons matched in all 8 paired rows. The three closed nets totaled -0.0642099856254282 in assumed quote units and completed-leg fees totaled 0.135034080503494. One trade differed by about 2.39e-13 from the legacy Decimal result; the other two matched at the shown precision. Full fills and raw inventories are in the comparison CSV. These trades did not pass a source-age execution gate.

Diagnostic source age and cross-venue source skew limits yielded the following total one-second observations across the four symbols: 100 ms: 40 windows, 5 at least 10 bps; 250 ms: 948 windows, 67 at least 10 bps; 500 ms: 2,172 windows, 104 at least 10 bps; 1000 ms: 2,749 windows, 133 at least 10 bps. These are overlapping windows, not independent trades. Timestamp units and cross-venue clock synchronization are assumptions. They do not demonstrate executable arbitrage or positive net returns.