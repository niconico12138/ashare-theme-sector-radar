"""
Phase 38 低区分度 Agent 校准测试

测试 RiskControlAgent、MarketContextAgent、DataQualityAgent、NarrativeAgent 的 vote 校准。
"""

import pytest

from theme_sector_radar.agents.sector_research.risk_control_agent import RiskControlAgent
from theme_sector_radar.agents.sector_research.market_context_agent import MarketContextAgent
from theme_sector_radar.agents.sector_research.data_quality_agent import DataQualityAgent
from theme_sector_radar.agents.sector_research.narrative_agent import NarrativeAgent


class TestRiskControlAgentCalibration:
    """测试 RiskControlAgent 校准"""

    def test_low_risk_positive(self):
        """低风险时 positive"""
        agent = RiskControlAgent()
        result = agent.analyze("测试", "industry", {
            "risk_penalty": 2.0,
            "trend_window_status": "ok",
            "data_warnings": [],
        })
        assert result["vote"] == "positive"

    def test_high_risk_negative(self):
        """高风险时 negative"""
        agent = RiskControlAgent()
        result = agent.analyze("测试", "industry", {
            "risk_penalty": 12.0,
            "trend_window_status": "ok",
            "data_warnings": [],
        })
        assert result["vote"] == "negative"

    def test_veto_negative(self):
        """veto 触发时 negative"""
        agent = RiskControlAgent()
        result = agent.analyze("测试", "industry", {
            "risk_penalty": 2.0,
            "trend_window_status": "ok",
            "data_warnings": [],
            "veto_triggered": True,
        })
        assert result["vote"] == "negative"

    def test_conflict_negative(self):
        """conflict 高时 negative"""
        agent = RiskControlAgent()
        result = agent.analyze("测试", "industry", {
            "risk_penalty": 2.0,
            "trend_window_status": "ok",
            "data_warnings": [],
            "conflict_level": "high",
        })
        assert result["vote"] == "negative"

    def test_data_warning_negative(self):
        """有风险标志时 negative"""
        agent = RiskControlAgent()
        result = agent.analyze("测试", "industry", {
            "risk_penalty": 2.0,
            "trend_window_status": "abnormal",
            "data_warnings": ["test warning"],
        })
        assert result["vote"] == "negative"

    def test_moderate_risk_neutral(self):
        """中等风险时 neutral"""
        agent = RiskControlAgent()
        result = agent.analyze("测试", "industry", {
            "risk_penalty": 5.0,
            "trend_window_status": "ok",
            "data_warnings": [],
        })
        assert result["vote"] == "neutral"


class TestMarketContextAgentCalibration:
    """测试 MarketContextAgent 校准"""

    def test_risk_on_positive(self):
        """risk_on 时 positive"""
        agent = MarketContextAgent()
        result = agent.analyze("测试", "industry", {
            "relative_strength_component": 5.0,
        }, {
            "benchmark_status": "ok",
            "regime_composite_label": "risk_on",
        })
        assert result["vote"] == "positive"

    def test_risk_off_negative(self):
        """risk_off 时 negative"""
        agent = MarketContextAgent()
        result = agent.analyze("测试", "industry", {
            "relative_strength_component": 5.0,
        }, {
            "benchmark_status": "ok",
            "regime_composite_label": "risk_off",
        })
        assert result["vote"] == "negative"

    def test_choppy_neutral(self):
        """choppy_market 时 neutral"""
        agent = MarketContextAgent()
        # relative_strength_component=9.0 → neutral_vs_benchmark
        result = agent.analyze("测试", "industry", {
            "relative_strength_component": 9.0,
        }, {
            "benchmark_status": "ok",
            "regime_composite_label": "choppy_market",
            "breadth_regime": "mixed_breadth",
        })
        assert result["vote"] == "neutral"

    def test_broad_falling_negative(self):
        """broad_falling 时 negative"""
        agent = MarketContextAgent()
        result = agent.analyze("测试", "industry", {
            "relative_strength_component": 5.0,
        }, {
            "benchmark_status": "ok",
            "regime_composite_label": "choppy_market",
            "breadth_regime": "broad_falling",
        })
        assert result["vote"] == "negative"

    def test_outperforming_positive(self):
        """outperforming 时 positive"""
        agent = MarketContextAgent()
        result = agent.analyze("测试", "industry", {
            "relative_strength_component": 13.0,
        }, {
            "benchmark_status": "ok",
        })
        assert result["vote"] == "positive"

    def test_unknown_regime_neutral(self):
        """unknown_regime 时 neutral"""
        agent = MarketContextAgent()
        result = agent.analyze("测试", "industry", {
            "relative_strength_component": 5.0,
        }, {
            "benchmark_status": "ok",
            "regime_composite_label": "unknown_regime",
        })
        assert result["vote"] == "neutral"


class TestDataQualityAgentCalibration:
    """测试 DataQualityAgent 校准"""

    def test_reliable_high_coverage_positive(self):
        """可靠且高覆盖时 positive"""
        agent = DataQualityAgent()
        result = agent.analyze("测试", "industry", {
            "history_coverage_ratio": 1.0,
            "trend_window_status": "ok",
            "actual_history_days": 20,
        })
        assert result["vote"] == "positive"

    def test_usable_neutral(self):
        """可用时 neutral"""
        agent = DataQualityAgent()
        result = agent.analyze("测试", "industry", {
            "history_coverage_ratio": 0.75,
            "trend_window_status": "ok",
            "actual_history_days": 15,
        })
        assert result["vote"] == "neutral"

    def test_unreliable_negative(self):
        """不可靠时 negative"""
        agent = DataQualityAgent()
        result = agent.analyze("测试", "industry", {
            "history_coverage_ratio": 0.3,
            "trend_window_status": "abnormal",
            "actual_history_days": 5,
        })
        assert result["vote"] == "negative"

    def test_low_coverage_negative(self):
        """低覆盖时 negative"""
        agent = DataQualityAgent()
        result = agent.analyze("测试", "industry", {
            "history_coverage_ratio": 0.4,
            "trend_window_status": "ok",
            "actual_history_days": 8,
        })
        assert result["vote"] == "negative"

    def test_limited_neutral(self):
        """有限时 neutral"""
        agent = DataQualityAgent()
        result = agent.analyze("测试", "industry", {
            "history_coverage_ratio": 0.6,
            "trend_window_status": "ok",
            "actual_history_days": 12,
        })
        assert result["vote"] == "neutral"


class TestNarrativeAgentCalibration:
    """测试 NarrativeAgent 校准"""

    def test_neutral_vote(self):
        """无外部事件数据时 neutral"""
        agent = NarrativeAgent()
        result = agent.analyze("半导体", "industry")
        assert result["vote"] == "neutral"

    def test_low_information_flag(self):
        """标记 low_information_agent"""
        agent = NarrativeAgent()
        result = agent.analyze("半导体", "industry")
        assert result.get("low_information_agent") is True

    def test_narrative_label_exists(self):
        """叙事标签存在"""
        agent = NarrativeAgent()
        result = agent.analyze("半导体", "industry")
        assert "narrative_label" in result
        assert result["narrative_label"] != ""

    def test_all_fields_complete(self):
        """所有字段完整"""
        agent = NarrativeAgent()
        result = agent.analyze("半导体", "industry")
        assert "narrative_label" in result
        assert "narrative_summary" in result
        assert "narrative_watch_points" in result
        assert "vote" in result
        assert "low_information_agent" in result

    def test_no_trade_advice_words(self):
        """不包含交易建议词"""
        agent = NarrativeAgent()
        result = agent.analyze("半导体", "industry")
        all_text = result.get("narrative_summary", "")
        trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
        for word in trade_words:
            assert word not in all_text.lower(), f"包含交易建议词: {word}"
