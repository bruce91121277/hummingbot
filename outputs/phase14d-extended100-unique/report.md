# Hypothetical convergence with missing-data recovery

Timestamps are normalized from per-venue units; Lighter source microseconds and synchronization are assumptions; Arcus book snapshot semantics and contract economics UNVERIFIED. Decision interval is configurable; 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.

{
  "freshness_ms": 500,
  "exit_mode": "percent",
  "left_fee_bps": "2",
  "signals": 12,
  "trades": 12,
  "closed": 5,
  "censored": 7,
  "gap_episodes": 193,
  "gap_recoveries": 186,
  "gap_reasons": {
    "left:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 113,
      "episode_duration_upper_bound_seconds": 301.04768645199994
    },
    "left:SOURCE_TIMESTAMP_STALE": {
      "episodes": 161,
      "episode_duration_upper_bound_seconds": 306.24768645200066
    },
    "pair:RECEIVE_SKEW_EXCEEDED": {
      "episodes": 78,
      "episode_duration_upper_bound_seconds": 283.56885590700006
    },
    "pair:SOURCE_SKEW_EXCEEDED": {
      "episodes": 84,
      "episode_duration_upper_bound_seconds": 285.06885590700006
    },
    "right:SOURCE_TIMESTAMP_IN_FUTURE": {
      "episodes": 34,
      "episode_duration_upper_bound_seconds": 3.700000000000002
    },
    "right:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 6,
      "episode_duration_upper_bound_seconds": 12.278830545000002
    },
    "right:SOURCE_TIMESTAMP_STALE": {
      "episodes": 6,
      "episode_duration_upper_bound_seconds": 12.278830545000002
    }
  }
}
