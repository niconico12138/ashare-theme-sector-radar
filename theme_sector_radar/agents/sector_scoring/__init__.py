"""
板块综合评分 Agent

提供板块综合评分能力，用于盘后复盘筛选重点观察板块。
"""

from .sector_scoring_agent import calculate_sector_scores

__all__ = ["calculate_sector_scores"]
