"""
板块诊断 Agent

根据评分 breakdown 生成:
- strength_reasons
- risk_reasons
- watch_points
- data_warnings
"""

from .sector_diagnosis_agent import diagnose_sector

__all__ = ["diagnose_sector"]
