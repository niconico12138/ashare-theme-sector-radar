"""
评分模块

实现行业板块、概念板块、风险评分和关注等级计算。
"""

from .concept_score import calculate_concept_score, calculate_concept_score_breakdown
from .focus_level import calculate_focus_level, generate_watch_points
from .industry_score import calculate_industry_score, calculate_industry_score_breakdown
from .risk_score import calculate_risk_penalty, calculate_risk_breakdown
from .short_term_burst_score import (
    apply_burst_insufficient_history_cap,
    calculate_short_term_burst_score,
    get_burst_level,
    interpret_dual_scores,
)

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
]
