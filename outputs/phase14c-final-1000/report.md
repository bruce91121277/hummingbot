# Hypothetical convergence with missing-data recovery

Source timestamps assumed microseconds and synchronized clocks; Arcus book snapshot semantics and contract economics UNVERIFIED. One-second decisions, 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.

{
  "freshness_ms": 1000,
  "exit_mode": "percent",
  "left_fee_bps": "2.25",
  "signals": 9,
  "trades": 9,
  "closed": 3,
  "censored": 6,
  "gap_episodes": 36,
  "gap_recoveries": 32,
  "gap_reasons": {
    "left:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 31,
      "episode_duration_upper_bound_seconds": 32.762265108
    },
    "left:SOURCE_TIMESTAMP_STALE": {
      "episodes": 35,
      "episode_duration_upper_bound_seconds": 36.762265108
    },
    "pair:RECEIVE_SKEW_EXCEEDED": {
      "episodes": 11,
      "episode_duration_upper_bound_seconds": 12.0
    },
    "pair:SOURCE_SKEW_EXCEEDED": {
      "episodes": 20,
      "episode_duration_upper_bound_seconds": 21.0
    },
    "right:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 6,
      "episode_duration_upper_bound_seconds": 7.762265108
    },
    "right:SOURCE_TIMESTAMP_STALE": {
      "episodes": 6,
      "episode_duration_upper_bound_seconds": 7.762265108
    }
  }
}
