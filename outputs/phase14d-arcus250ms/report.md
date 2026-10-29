# Hypothetical convergence with missing-data recovery

Timestamps are normalized from per-venue units; Lighter source microseconds and synchronization are assumptions; Arcus book snapshot semantics and contract economics UNVERIFIED. Decision interval is configurable; 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.

{
  "freshness_ms": 500,
  "exit_mode": "percent",
  "left_fee_bps": "2.25",
  "signals": 12,
  "trades": 12,
  "closed": 6,
  "censored": 6,
  "gap_episodes": 182,
  "gap_recoveries": 176,
  "gap_reasons": {
    "left:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 128,
      "episode_duration_upper_bound_seconds": 141.55707715
    },
    "left:SOURCE_TIMESTAMP_STALE": {
      "episodes": 128,
      "episode_duration_upper_bound_seconds": 141.55707715
    },
    "pair:RECEIVE_SKEW_EXCEEDED": {
      "episodes": 155,
      "episode_duration_upper_bound_seconds": 143.75
    },
    "pair:SOURCE_SKEW_EXCEEDED": {
      "episodes": 151,
      "episode_duration_upper_bound_seconds": 142.75
    },
    "right:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 77,
      "episode_duration_upper_bound_seconds": 63.05707715
    },
    "right:SOURCE_TIMESTAMP_STALE": {
      "episodes": 84,
      "episode_duration_upper_bound_seconds": 65.55707715
    }
  }
}
