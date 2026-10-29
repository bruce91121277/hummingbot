# Hypothetical convergence with missing-data recovery

Timestamps are normalized from per-venue units; Lighter source microseconds and synchronization are assumptions; Arcus book snapshot semantics and contract economics UNVERIFIED. Decision interval is configurable; 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.

{
  "freshness_ms": 1000,
  "exit_mode": "percent",
  "left_fee_bps": "2",
  "signals": 11,
  "trades": 11,
  "closed": 4,
  "censored": 7,
  "gap_episodes": 15,
  "gap_recoveries": 8,
  "gap_reasons": {
    "left:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 11,
      "episode_duration_upper_bound_seconds": 264.4476864519999
    },
    "left:SOURCE_TIMESTAMP_STALE": {
      "episodes": 12,
      "episode_duration_upper_bound_seconds": 265.4476864519999
    },
    "pair:RECEIVE_SKEW_EXCEEDED": {
      "episodes": 4,
      "episode_duration_upper_bound_seconds": 256.768855907
    },
    "pair:SOURCE_SKEW_EXCEEDED": {
      "episodes": 4,
      "episode_duration_upper_bound_seconds": 256.768855907
    },
    "right:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 6,
      "episode_duration_upper_bound_seconds": 6.678830545
    },
    "right:SOURCE_TIMESTAMP_STALE": {
      "episodes": 6,
      "episode_duration_upper_bound_seconds": 6.678830545
    },
    "right:SOURCE_TIMESTAMP_IN_FUTURE": {
      "episodes": 3,
      "episode_duration_upper_bound_seconds": 4.0
    }
  }
}
