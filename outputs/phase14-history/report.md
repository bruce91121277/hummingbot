# Hummingbot core / legacy research bridge

Legacy capture loader and state machine/ledger reused. Only order book VWAP runs in Hummingbot; this is not a Hummingbot execution engine. Freshness is a diagnostic, not applied to strategy. Source microseconds, independent clocks, units, fees and 1:1 conversion assumed. No private trading, maker fills or qualified PnL.

{
  "freshness": {
    "100": {
      "samples": 40,
      "positive": 40,
      "edge_ge_10": 5
    },
    "250": {
      "samples": 948,
      "positive": 948,
      "edge_ge_10": 67
    },
    "500": {
      "samples": 2172,
      "positive": 2172,
      "edge_ge_10": 104
    },
    "1000": {
      "samples": 2749,
      "positive": 2749,
      "edge_ge_10": 133
    }
  },
  "signals": 137,
  "trades": 8,
  "closed": 3,
  "censored": 5
}
