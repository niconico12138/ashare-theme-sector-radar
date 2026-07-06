"""
CapitalVolumeAgent 测试

测试资金量能分析 Agent。
"""

import pytest

from theme_sector_radar.agents.sector_research.capital_volume_agent import CapitalVolumeAgent
from theme_sector_radar.agents.sector_research.opinion import LAYER_SPECIALIZED, VOTE_POSITIVE, VOTE_NEUTRAL, VOTE_NEGATIVE


class TestCapitalVolumeAgent:
    """测试 CapitalVolumeAgent"""

    def test_analyze_positive(self):
        """测试正向资金流"""
        agent = CapitalVolumeAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={
                "main_net_inflow": 1_000_000_000,  # 10亿
                "turnover": 10_000_000_000,
            },
        )

        assert result.agent_id == "capital_volume"
        assert result.layer == LAYER_SPECIALIZED
        assert result.label == "capital_volume_positive"
        assert result.vote == VOTE_POSITIVE

    def test_analyze_neutral(self):
        """测试中性资金流"""
        agent = CapitalVolumeAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={
                "main_net_inflow": 100_000_000,  # 1亿
                "turnover": 5_000_000_000,
            },
        )

        assert result.label == "capital_volume_neutral"
        assert result.vote == VOTE_NEUTRAL

    def test_analyze_weak(self):
        """测试弱势资金流"""
        agent = CapitalVolumeAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={
                "main_net_inflow": -1_000_000_000,  # -10亿
                "turnover": 5_000_000_000,
            },
        )

        assert result.label == "capital_volume_weak"
        assert result.vote == VOTE_NEGATIVE

    def test_analyze_unknown(self):
        """测试未知资金流"""
        agent = CapitalVolumeAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={
                "main_net_inflow": 0.0,
                "turnover": 0.0,
            },
        )

        assert result.label == "capital_volume_unknown"
        assert result.vote == VOTE_NEUTRAL
        assert len(result.warnings) > 0
