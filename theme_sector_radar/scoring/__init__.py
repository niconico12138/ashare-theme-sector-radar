"""
评分模块

实现行业板块、概念板块、风险评分、个股短线/趋势评分、板块龙头识别、交易风险和决策分计算。
"""

from .concept_score import calculate_concept_score, calculate_concept_score_breakdown
from .decision_score import compute_decision_score
from .focus_level import calculate_focus_level, generate_watch_points
from .industry_score import calculate_industry_score, calculate_industry_score_breakdown
from .risk_score import calculate_risk_penalty, calculate_risk_breakdown
from .sector_leader_score import compute_sector_leader_scores
from .short_term_burst_score import (
    apply_burst_insufficient_history_cap,
    calculate_short_term_burst_score,
    get_burst_level,
    interpret_dual_scores,
)
from .stock_short_score import compute_stock_short_score
from .stock_trend_score import compute_stock_trend_score
from .trade_risk import compute_trade_risk

__all__ = [
    "calculate_industry_score",
    "calculate_industry_score_breakdown",
    "calculate_concept_score",
    "calculate_concept_score_breakdown",
    "calculate_risk_penalty",
    "calculate_risk_breakdown",
    "calculate_focus_level",
    "generate_watch_points",
    "calculate_short_term_burst_score",
    "get_burst_level",
    "interpret_dual_scores",
    "apply_burst_insufficient_history_cap",
    "compute_stock_short_score",
    "compute_stock_trend_score",
    "compute_sector_leader_scores",
    "compute_trade_risk",
    "compute_decision_score",
]
