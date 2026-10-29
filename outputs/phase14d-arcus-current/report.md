# Hypothetical convergence with missing-data recovery

Timestamps are normalized from per-venue units; Lighter source microseconds and synchronization are assumptions; Arcus book snapshot semantics and contract economics UNVERIFIED. Decision interval is configurable; 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.

{
  "freshness_ms": 500,
  "exit_mode": "percent",
  "left_fee_bps": "2.25",
  "signals": 8,
  "trades": 8,
  "closed": 3,
  "censored": 5,
  "gap_episodes": 97,
  "gap_recoveries": 93,
  "gap_reasons": {
    "left:SOURCE_TIMESTAMP_STALE": {
      "episodes": 88,
      "episode_duration_upper_bound_seconds": 101.71326660800001
    },
    "pair:SOURCE_SKEW_EXCEEDED": {
      "episodes": 73,
      "episode_duration_upper_bound_seconds": 84.850121563
    },
    "left:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 75,
      "episode_duration_upper_bound_seconds": 86.71326660800001
    },
    "right:SOURCE_TIMESTAMP_STALE": {
      "episodes": 22,
      "episode_duration_upper_bound_seconds": 37.713266608000005
    },
    "pair:RECEIVE_SKEW_EXCEEDED": {
      "episodes": 67,
      "episode_duration_upper_bound_seconds": 78.850121563
    },
    "right:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 19,
      "episode_duration_upper_bound_seconds": 34.713266608000005
    }
  }
}
