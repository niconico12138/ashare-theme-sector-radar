"""
Agent 投票校准测试

验证各 L2 Agent 的投票逻辑正确。
"""

import pytest

from theme_sector_radar.agents.sector_research.technical_trend_agent import TechnicalTrendAgent
from theme_sector_radar.agents.sector_research.short_term_heat_agent import ShortTermHeatAgent
from theme_sector_radar.agents.sector_research.rotation_analysis_agent import RotationAnalysisAgent
from theme_sector_radar.agents.sector_research.risk_control_agent import RiskControlAgent
from theme_sector_radar.agents.sector_research.data_quality_agent import DataQualityAgent
from theme_sector_radar.agents.sector_research.market_context_agent import MarketContextAgent


class TestTechnicalTrendAgentVote:
    """测试 TechnicalTrendAgent 投票"""

    def test_trend_confirmed_positive(self):
        """趋势确认应投 positive"""
        agent = TechnicalTrendAgent()
        result = agent.analyze("test", "industry", {}, {
            "multi_window_label": "multi_window_confirmed",
            "consensus_score": 60.0,
            "window_scores": {},
        })
        assert result["vote"] == "positive"

    def test_trend_weak_negative(self):
        """趋势弱应投 negative"""
        agent = TechnicalTrendAgent()
        result = agent.analyze("test", "industry", {}, {
            "multi_window_label": "weak_all_windows",
            "consensus_score": 20.0,
            "window_scores": {},
        })
        assert result["vote"] == "negative"

    def test_trend_neutral(self):
        """趋势中性应投 neutral"""
        agent = TechnicalTrendAgent()
        result = agent.analyze("test", "industry", {}, {
            "multi_window_label": "conflicted_windows",
            "consensus_score": 45.0,
            "window_scores": {},
        })
        assert result["vote"] == "neutral"


class TestShortTermHeatAgentVote:
    """测试 ShortTermHeatAgent 投票"""

    def test_heat_active_positive(self):
        """热度活跃应投 positive"""
        agent = ShortTermHeatAgent()
        result = agent.analyze("test", "industry", {
            "short_term_burst_score": 70.0,
        })
        assert result["vote"] == "positive"

    def test_heat_weak_negative(self):
        """热度弱应投 negative"""
        agent = ShortTermHeatAgent()
        result = agent.analyze("test", "industry", {
            "short_term_burst_score": 20.0,
        })
        assert result["vote"] == "negative"

    def test_heat_moderate_neutral(self):
        """热度适中应投 neutral"""
        agent = ShortTermHeatAgent()
        result = agent.analyze("test", "industry", {
            "short_term_burst_score": 55.0,
        })
        assert result["vote"] == "neutral"


class TestRotationAnalysisAgentVote:
    """测试 RotationAnalysisAgent 投票"""

    def test_rotation_rising_positive(self):
        """轮动上升应投 positive"""
        agent = RotationAnalysisAgent()
        result = agent.analyze("test", "industry", {
            "rotation_phase": "leading",
        }, {
            "multi_window_label": "multi_window_confirmed",
        })
        assert result["vote"] == "positive"

    def test_rotation_lagging_negative(self):
        """轮动落后应投 negative"""
        agent = RotationAnalysisAgent()
        result = agent.analyze("test", "industry", {
            "rotation_phase": "lagging",
        }, {
            "multi_window_label": "weak_all_windows",
        })
        assert result["vote"] == "negative"


class TestRiskControlAgentVote:
    """测试 RiskControlAgent 投票"""

    def test_risk_low_positive(self):
        """低风险应投 positive"""
        agent = RiskControlAgent()
        result = agent.analyze("test", "industry", {
            "risk_penalty": 2.0,
        })
        assert result["vote"] == "positive"

    def test_risk_high_negative(self):
        """高风险应投 negative"""
        agent = RiskControlAgent()
        result = agent.analyze("test", "industry", {
            "risk_penalty": 12.0,
        })
        assert result["vote"] == "negative"


class TestDataQualityAgentVote:
    """测试 DataQualityAgent 投票"""

    def test_data_reliable_positive(self):
        """数据可靠应投 positive"""
        agent = DataQualityAgent()
        result = agent.analyze("test", "industry", {
            "history_coverage_ratio": 1.0,
            "trend_window_status": "ok",
            "actual_history_days": 20,
        })
        assert result["vote"] == "positive"

    def test_data_limited_negative(self):
        """数据有限应投 neutral（不再默认 negative）"""
        agent = DataQualityAgent()
        result = agent.analyze("test", "industry", {
            "history_coverage_ratio": 0.5,
            "trend_window_status": "ok",
            "actual_history_days": 5,
        })
        assert result["vote"] == "neutral"


class TestMarketContextAgentVote:
    """测试 MarketContextAgent 投票"""

    def test_outperforming_positive(self):
        """跑赢基准应投 positive"""
        agent = MarketContextAgent()
        result = agent.analyze("test", "industry", {
            "relative_strength_component": 12.0,
        }, {
            "benchmark_status": "ok",
        })
        assert result["vote"] == "positive"

    def test_underperforming_negative(self):
        """跑输基准在 risk_off 时应投 negative"""
        agent = MarketContextAgent()
        result = agent.analyze("test", "industry", {
            "relative_strength_component": 5.0,
        }, {
            "benchmark_status": "ok",
            "regime_composite_label": "risk_off",
        })
        assert result["vote"] == "negative"
