"""
鍥犲瓙鍏冩暟鎹敞鍐岃〃

瀹氫箟棣栨壒 13 涓洜瀛愮殑鍏冩暟鎹俊鎭€?姣忎釜鍥犲瓙鍖呭惈锛歠actor_id, display_name, category, source_project, direction, lookback_days, enabled, description
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FactorMetadata:
    """鍥犲瓙鍏冩暟鎹畾涔夈€?
    Attributes:
        factor_id: 鍥犲瓙鍞竴鏍囪瘑绗?        display_name: 涓枃鏄剧ず鍚?        category: 鍥犲瓙绫诲埆
        source_project: 鏉ユ簮椤圭洰/妯″潡
        direction: 璇勫垎鏂瑰悜
        lookback_days: 鍥炴函澶╂暟
        enabled: 鏄惁鍚敤
        description: 鍥犲瓙鎻忚堪
        tags: 鏍囩鍒楄〃
    """

    factor_id: str
    display_name: str
    category: str  # trend/momentum/volatility/volume/risk/reversal/sector/agent/composite
    source_project: str
    direction: str  # higher_is_better/lower_is_better/neutral/already_scored
    lookback_days: int | None
    enabled: bool
    description: str
    tags: list[str] = field(default_factory=list)


# 鎵归噺瀹氫箟鍥犲瓙鍏冩暟鎹?FACTOR_REGISTRY: dict[str, FactorMetadata] = {}
FACTOR_REGISTRY: dict[str, FactorMetadata] = {}


def _register(factor: FactorMetadata) -> None:
    """Register one factor."""
    FACTOR_REGISTRY[factor.factor_id] = factor

# ============================================================
# 瓒嬪娍绫诲洜瀛?(trend)
# ============================================================

_register(FactorMetadata(
    factor_id="ma20_slope_5",
    display_name="ma20_slope_5",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=5,
    enabled=True,
    description="Metadata for ma20_slope_5.",
))

_register(FactorMetadata(
    factor_id="stock_trend_score",
    display_name="stock_trend_score",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for stock_trend_score.",
))

# ============================================================
# 鍔ㄩ噺绫诲洜瀛?(momentum)
# ============================================================

_register(FactorMetadata(
    factor_id="stock_short_score",
    display_name="stock_short_score",
    category="momentum",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="Metadata for stock_short_score.",
))

_register(FactorMetadata(
    factor_id="stock_short_score_v2",
    display_name="stock_short_score_v2",
    category="momentum",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="Metadata for stock_short_score_v2.",
))

# ============================================================
# 椋庨櫓绫诲洜瀛?(risk)
# ============================================================

_register(FactorMetadata(
    factor_id="drawdown_risk_score",
    display_name="drawdown_risk_score",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="lower_is_better",
    lookback_days=10,
    enabled=True,
    description="Metadata for drawdown_risk_score.",
))

_register(FactorMetadata(
    factor_id="risk_penalty_score",
    display_name="risk_penalty_score",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="lower_is_better",
    lookback_days=None,
    enabled=True,
    description="Metadata for risk_penalty_score.",
))

# ============================================================
# 褰卞瓙璇勫垎鍥犲瓙 (agent)
# ============================================================

_register(FactorMetadata(
    factor_id="regime_router_shadow_score_v5",
    display_name="regime_router_shadow_score_v5",
    category="agent",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="Metadata for regime_router_shadow_score_v5.",
))

# ============================================================
# 鏉垮潡绫诲洜瀛?(sector)
# ============================================================

_register(FactorMetadata(
    factor_id="sector_trend_score",
    display_name="sector_trend_score",
    category="sector",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for sector_trend_score.",
))

_register(FactorMetadata(
    factor_id="sector_burst_score",
    display_name="sector_burst_score",
    category="sector",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="Metadata for sector_burst_score.",
))

# ============================================================
# 缁煎悎璇勫垎鍥犲瓙 (composite)
# ============================================================

_register(FactorMetadata(
    factor_id="final_score",
    display_name="final_score",
    category="composite",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="Metadata for final_score.",
))

# ============================================================
# Agent 璇勫垎鍥犲瓙 (agent)
# ============================================================

_register(FactorMetadata(
    factor_id="agent_score",
    display_name="agent_score",
    category="agent",
    source_project="ai-hedge-fund",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="Metadata for agent_score.",
))

_register(FactorMetadata(
    factor_id="trend_agent_score",
    display_name="trend_agent_score",
    category="agent",
    source_project="ai-hedge-fund",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="Metadata for trend_agent_score.",
))

_register(FactorMetadata(
    factor_id="short_agent_score",
    display_name="short_agent_score",
    category="agent",
    source_project="ai-hedge-fund",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="Metadata for short_agent_score.",
))

# ============================================================
# Bars 鍥犲瓙 (trend/volatility/volume) - 绗簩闃舵鏂板
# ============================================================

_register(FactorMetadata(
    factor_id="near_high_250",
    display_name="near_high_250",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=250,
    enabled=True,
    description="Metadata for near_high_250.",
))

_register(FactorMetadata(
    factor_id="contraction_score",
    display_name="contraction_score",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="Metadata for contraction_score.",
))

_register(FactorMetadata(
    factor_id="atr10_atr50",
    display_name="atr10_atr50",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="neutral",
    lookback_days=50,
    enabled=True,
    description="Metadata for atr10_atr50.",
))

_register(FactorMetadata(
    factor_id="range10_range20",
    display_name="range10_range20",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="neutral",
    lookback_days=20,
    enabled=True,
    description="Metadata for range10_range20.",
))

_register(FactorMetadata(
    factor_id="range20_range60",
    display_name="range20_range60",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="neutral",
    lookback_days=60,
    enabled=True,
    description="Metadata for range20_range60.",
))

_register(FactorMetadata(
    factor_id="amount_ratio_20",
    display_name="amount_ratio_20",
    category="volume",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="Metadata for amount_ratio_20.",
))

# ============================================================
# 涓偂澧炲己鍥犲瓙 (stock_quality) - 绗簩鍗佷竴闃舵-B 鏂板
# ============================================================

_register(FactorMetadata(
    factor_id="liquidity_score",
    display_name="liquidity_score",
    category="liquidity",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="Metadata for liquidity_score.",
    tags=["profile_only", "liquidity_context"],
))

_register(FactorMetadata(
    factor_id="chasing_risk_score",
    display_name="chasing_risk_score",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=10,
    enabled=True,
    description="Metadata for chasing_risk_score.",
    tags=["overheat_risk", "shadow_warning", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="drawdown_depth_20",
    display_name="drawdown_depth_20",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for drawdown_depth_20.",
    tags=["overlaps_with_breakout_distance_20", "pullback_repair_context", "shadow_only", "not_hard_blocker"],
))

_register(FactorMetadata(
    factor_id="breakout_distance_20",
    display_name="breakout_distance_20",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for breakout_distance_20.",
    tags=["structure_position", "shadow_only", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="relative_strength_20",
    display_name="relative_strength_20",
    category="momentum",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for relative_strength_20.",
    tags=["shadow_v2", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="relative_strength_60",
    display_name="relative_strength_60",
    category="momentum",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=60,
    enabled=True,
    description="Metadata for relative_strength_60.",
    tags=["shadow_v2", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="risk_adjusted_return_20",
    display_name="risk_adjusted_return_20",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for risk_adjusted_return_20.",
    tags=["shadow_v2", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="volume_stability_score",
    display_name="volume_stability_score",
    category="volume",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for volume_stability_score.",
    tags=["shadow_v2", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="trend_persistence_score",
    display_name="trend_persistence_score",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=40,
    enabled=True,
    description="Metadata for trend_persistence_score.",
    tags=["shadow_v2", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="sector_peer_rank_score",
    display_name="sector_peer_rank_score",
    category="sector",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="Metadata for sector_peer_rank_score.",
    tags=["shadow_v2", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="short_emotion_heat_score",
    display_name="short_emotion_heat_score",
    category="short_emotion",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="Metadata for short_emotion_heat_score.",
    tags=["short_burst_shadow", "research_only", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="sector_burst_breadth_score",
    display_name="sector_burst_breadth_score",
    category="short_emotion",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="Metadata for sector_burst_breadth_score.",
    tags=["short_burst_shadow", "research_only", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="limit_attention_score",
    display_name="limit_attention_score",
    category="short_emotion",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for limit_attention_score.",
    tags=["short_burst_shadow", "research_only", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="intraday_reversal_risk_score",
    display_name="intraday_reversal_risk_score",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for intraday_reversal_risk_score.",
    tags=["short_burst_shadow", "research_only", "risk_review"],
))

_register(FactorMetadata(
    factor_id="close_strength_score",
    display_name="close_strength_score",
    category="short_emotion",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for close_strength_score.",
    tags=["short_burst_shadow", "research_only", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="volume_burst_quality_score",
    display_name="volume_burst_quality_score",
    category="volume",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for volume_burst_quality_score.",
    tags=["short_burst_shadow", "research_only", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="single_name_overheat_score",
    display_name="single_name_overheat_score",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for single_name_overheat_score.",
    tags=["short_burst_shadow", "research_only", "risk_review"],
))

_register(FactorMetadata(
    factor_id="next_day_cashout_risk_score",
    display_name="next_day_cashout_risk_score",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for next_day_cashout_risk_score.",
    tags=["short_burst_shadow", "research_only", "risk_review"],
))

_register(FactorMetadata(
    factor_id="short_burst_emotion_score_v1",
    display_name="short_burst_emotion_score_v1",
    category="short_emotion",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for short_burst_emotion_score_v1.",
    tags=["short_burst_shadow", "research_only", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="short_burst_emotion_score_v2",
    display_name="short_burst_emotion_score_v2",
    category="short_emotion",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="Metadata for short_burst_emotion_score_v2.",
    tags=["short_burst_shadow", "research_only", "watch_ranking_only"],
))

_register(FactorMetadata(
    factor_id="intraday_close_position_score",
    display_name="intraday_close_position_score",
    category="intraday",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for intraday_close_position_score.",
    tags=["intraday_shadow", "short_burst_shadow", "research_only", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="intraday_high_pullback_risk_score",
    display_name="intraday_high_pullback_risk_score",
    category="intraday",
    source_project="theme-sector-radar-dev",
    direction="lower_is_better",
    lookback_days=1,
    enabled=True,
    description="Metadata for intraday_high_pullback_risk_score.",
    tags=["intraday_shadow", "short_burst_shadow", "research_only", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="intraday_volume_price_confirm_score",
    display_name="intraday_volume_price_confirm_score",
    category="intraday",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for intraday_volume_price_confirm_score.",
    tags=["intraday_shadow", "short_burst_shadow", "research_only", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="intraday_sector_breadth_score",
    display_name="intraday_sector_breadth_score",
    category="intraday",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for intraday_sector_breadth_score.",
    tags=["intraday_shadow", "short_burst_shadow", "research_only", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="intraday_late_strength_score",
    display_name="intraday_late_strength_score",
    category="intraday",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for intraday_late_strength_score.",
    tags=["intraday_shadow", "short_burst_shadow", "research_only", "no_execution_signal"],
))

_register(FactorMetadata(
    factor_id="short_burst_intraday_emotion_score_shadow",
    display_name="short_burst_intraday_emotion_score_shadow",
    category="intraday",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=1,
    enabled=True,
    description="Metadata for short_burst_intraday_emotion_score_shadow.",
    tags=["intraday_shadow", "short_burst_shadow", "research_only", "watch_ranking_only", "no_execution_signal"],
))

_INTRADAY_ATOMIC_FACTOR_DIRECTIONS = {
    "late_return_30m_score": "already_scored",
    "late_vwap_support_score": "already_scored",
    "late_volume_share_score": "already_scored",
    "late_high_near_close_score": "already_scored",
    "high_to_close_drawdown_score": "lower_is_better",
    "morning_spike_fade_score": "lower_is_better",
    "afternoon_fade_score": "lower_is_better",
    "max_gain_giveback_ratio": "lower_is_better",
    "close_vs_vwap_score": "already_scored",
    "late_price_above_vwap_ratio": "already_scored",
    "vwap_slope_score": "already_scored",
    "vwap_reclaim_score": "already_scored",
    "volume_without_price_progress_risk": "lower_is_better",
    "late_volume_efficiency_score": "already_scored",
    "amount_acceleration_score": "already_scored",
    "volume_spike_exhaustion_score": "lower_is_better",
    "opening_drive_score": "already_scored",
    "morning_strength_persist_score": "already_scored",
    "morning_pullback_repair_score": "already_scored",
    "open_to_midday_resilience_score": "already_scored",
    "sector_intraday_breadth_change": "already_scored",
    "sector_late_breadth_score": "already_scored",
    "leader_follower_sync_score": "already_scored",
    "stock_vs_sector_intraday_alpha": "already_scored",
}

for _factor_id, _direction in _INTRADAY_ATOMIC_FACTOR_DIRECTIONS.items():
    _register(FactorMetadata(
        factor_id=_factor_id,
        display_name=_factor_id,
        category="intraday",
        source_project="theme-sector-radar-dev",
        direction=_direction,
        lookback_days=1,
        enabled=True,
        description=f"Metadata for {_factor_id}.",
        tags=["intraday_shadow", "short_burst_shadow", "research_only", "no_execution_signal"],
    ))

_SHORT_BURST_NEWS_EMOTION_FACTOR_SPECS = {
    "market_short_emotion_score": ("market_emotion", "already_scored"),
    "limit_up_breadth_score": ("market_emotion", "already_scored"),
    "limit_up_failure_risk": ("market_emotion", "lower_is_better"),
    "leader_continuation_score": ("market_emotion", "already_scored"),
    "short_burst_environment_score": ("market_emotion", "already_scored"),
    "crowding_heat_score": ("market_emotion", "lower_is_better"),
    "news_heat_score": ("catalyst", "already_scored"),
    "policy_catalyst_score": ("catalyst", "already_scored"),
    "earnings_catalyst_score": ("catalyst", "already_scored"),
    "event_freshness_score": ("catalyst", "already_scored"),
    "event_continuation_score": ("catalyst", "already_scored"),
    "negative_news_risk_score": ("catalyst", "lower_is_better"),
    "rumor_hype_risk_score": ("catalyst", "lower_is_better"),
    "short_burst_news_emotion_score_shadow": ("short_emotion", "already_scored"),
}

for _factor_id, (_category, _direction) in _SHORT_BURST_NEWS_EMOTION_FACTOR_SPECS.items():
    _register(FactorMetadata(
        factor_id=_factor_id,
        display_name=_factor_id,
        category=_category,
        source_project="theme-sector-radar-dev",
        direction=_direction,
        lookback_days=3,
        enabled=True,
        description=f"Metadata for {_factor_id}.",
        tags=["short_burst_shadow", "research_only", "watch_ranking_only", "no_execution_signal"],
    ))

_register(FactorMetadata(
    factor_id="sector_support_score",
    display_name="sector_support_score",
    category="sector",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="Metadata for sector_support_score.",
))


def get_factor_metadata(factor_id: str) -> FactorMetadata | None:
    """Return metadata for a registered factor."""
    return FACTOR_REGISTRY.get(factor_id)


def list_enabled_factors() -> list[FactorMetadata]:
    """Return all enabled factors."""
    return [f for f in FACTOR_REGISTRY.values() if f.enabled]
