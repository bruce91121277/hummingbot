# Standalone hypothetical research

Source timestamps assumed microseconds and synchronized clocks; Arcus book snapshot semantics and contract economics UNVERIFIED. One-second decisions, 100ms book sampling. Position accounting is isolated hypothetical ledger; all legs taker; funding assumed zero. Formal eligibility unchanged. No private APIs or live orders.

{
  "freshness_ms": 500,
  "freshness_sensitivity": {
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
  "signals": 0,
  "trades": 0,
  "closed": 0,
  "censored": 0
}
