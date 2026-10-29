# Hypothetical convergence with missing-data recovery

Timestamps are normalized from per-venue units; Lighter source microseconds and synchronization are assumptions; Arcus book snapshot semantics and contract economics UNVERIFIED. Decision interval is configurable; 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.

{
  "freshness_ms": 500,
  "exit_mode": "percent",
  "left_fee_bps": "2.25",
  "signals": 13,
  "trades": 13,
  "closed": 7,
  "censored": 6,
  "gap_episodes": 210,
  "gap_recoveries": 204,
  "gap_reasons": {
    "left:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 129,
      "episode_duration_upper_bound_seconds": 139.5570771499999
    },
    "left:SOURCE_TIMESTAMP_STALE": {
      "episodes": 129,
      "episode_duration_upper_bound_seconds": 139.5570771499999
    },
    "pair:RECEIVE_SKEW_EXCEEDED": {
      "episodes": 172,
      "episode_duration_upper_bound_seconds": 146.89999999999992
    },
    "pair:SOURCE_SKEW_EXCEEDED": {
      "episodes": 162,
      "episode_duration_upper_bound_seconds": 144.99999999999991
    },
    "right:SOURCE_TIMESTAMP_STALE": {
      "episodes": 119,
      "episode_duration_upper_bound_seconds": 73.85707715000002
    },
    "right:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 103,
      "episode_duration_upper_bound_seconds": 67.45707715000002
    }
  }
}
