"""
评分模块

实现行业板块、概念板块、风险评分和关注等级计算。
"""

from .concept_score import calculate_concept_score, calculate_concept_score_breakdown
from .focus_level import calculate_focus_level, generate_watch_points
from .industry_score import calculate_industry_score, calculate_industry_score_breakdown
from .risk_score import calculate_risk_penalty, calculate_risk_breakdown

__all__ = [
    "calculate_industry_score",
    "calculate_industry_score_breakdown",
    "calculate_concept_score",
    "calculate_concept_score_breakdown",
    "calculate_risk_penalty",
    "calculate_risk_breakdown",
    "calculate_focus_level",
    "generate_watch_points",
]
