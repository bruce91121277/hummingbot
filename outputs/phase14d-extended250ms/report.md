# Hypothetical convergence with missing-data recovery

Timestamps are normalized from per-venue units; Lighter source microseconds and synchronization are assumptions; Arcus book snapshot semantics and contract economics UNVERIFIED. Decision interval is configurable; 100ms book sampling; Gap durations are sampled; each reason duration is an episode upper bound because reasons may overlap or change within an episode. Unknown intra-gap path. Position accounting hypothetical, all legs taker, funding assumed zero. No private API or live orders.

{
  "freshness_ms": 500,
  "exit_mode": "percent",
  "left_fee_bps": "2",
  "signals": 11,
  "trades": 11,
  "closed": 4,
  "censored": 7,
  "gap_episodes": 134,
  "gap_recoveries": 127,
  "gap_reasons": {
    "left:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 82,
      "episode_duration_upper_bound_seconds": 296.6976864519999
    },
    "left:SOURCE_TIMESTAMP_STALE": {
      "episodes": 121,
      "episode_duration_upper_bound_seconds": 308.1976864519999
    },
    "pair:RECEIVE_SKEW_EXCEEDED": {
      "episodes": 50,
      "episode_duration_upper_bound_seconds": 278.018855907
    },
    "pair:SOURCE_SKEW_EXCEEDED": {
      "episodes": 55,
      "episode_duration_upper_bound_seconds": 281.018855907
    },
    "right:RECEIVE_TIMESTAMP_STALE": {
      "episodes": 6,
      "episode_duration_upper_bound_seconds": 11.678830545000002
    },
    "right:SOURCE_TIMESTAMP_STALE": {
      "episodes": 7,
      "episode_duration_upper_bound_seconds": 11.928830545000002
    },
    "right:SOURCE_TIMESTAMP_IN_FUTURE": {
      "episodes": 14,
      "episode_duration_upper_bound_seconds": 4.5
    }
  }
}
