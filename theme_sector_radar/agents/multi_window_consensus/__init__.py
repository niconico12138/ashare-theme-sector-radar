"""
多窗口趋势共识 Agent

合并同一板块在 5日、10日、20日窗口下的趋势评分，输出多窗口趋势共识结果。
"""

from .multi_window_consensus_agent import MultiWindowConsensusAgent

__all__ = ["MultiWindowConsensusAgent"]
