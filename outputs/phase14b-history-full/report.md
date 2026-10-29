# Standalone hypothetical research

Source timestamps assumed microseconds and synchronized clocks; Arcus book snapshot semantics and contract economics UNVERIFIED. One-second decisions, 100ms book sampling. Position accounting is isolated hypothetical ledger; all legs taker; funding assumed zero. Formal eligibility unchanged. No private APIs or live orders.

{
  "freshness_ms": 500,
  "freshness_sensitivity": {
    "100": {
      "samples": 39,
      "positive": 39,
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
  "signals": 5,
  "trades": 5,
  "closed": 0,
  "censored": 5
}
