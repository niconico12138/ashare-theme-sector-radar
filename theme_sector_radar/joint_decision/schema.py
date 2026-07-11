"""Schema constants for joint decision outputs."""

SCHEMA_VERSION = "1.0"
DECISION_MODE = "watch_only"

OFFICIAL_SCORE_FACTORS = ["final_score"]
SHADOW_FACTORS = [
    "factor_composite_shadow_score_v2",
    "factor_composite_shadow_score",
    "display_score_shadow_90_10",
    "display_score_shadow_80_20",
    "display_score_shadow_70_30",
]
PROFILE_ONLY_FACTORS = [
    "sector_support_score",
    "liquidity_score",
    "breakout_distance_20",
    "drawdown_depth_20",
    "chasing_risk_score",
]

STOCK_BUCKETS = [
    "core_watch",
    "v2_opportunity",
    "short_burst",
    "divergence_review",
    "blocked",
]

SECTOR_BUCKETS = [
    "primary_watch",
    "short_burst_watch",
    "review",
    "avoid",
]
