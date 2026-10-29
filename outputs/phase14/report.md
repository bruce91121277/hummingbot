# Hummingbot core / legacy research bridge

Legacy capture loader and state machine/ledger reused. Only order book VWAP runs in Hummingbot; this is not a Hummingbot execution engine. Freshness is a diagnostic, not applied to strategy. Source microseconds, independent clocks, units, fees and 1:1 conversion assumed. No private trading, maker fills or qualified PnL.

{
  "freshness": {
    "100": {
      "samples": 0,
      "positive": 0,
      "edge_ge_10": 0
    },
    "250": {
      "samples": 243,
      "positive": 243,
      "edge_ge_10": 0
    },
    "500": {
      "samples": 882,
      "positive": 882,
      "edge_ge_10": 0
    },
    "1000": {
      "samples": 1048,
      "positive": 1048,
      "edge_ge_10": 1
    }
  },
  "signals": 1,
  "trades": 1,
  "closed": 1,
  "censored": 0
}
