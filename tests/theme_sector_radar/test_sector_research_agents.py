"""
板块综合研判 Agent 测试

测试 Sector Research Agent Group 的各项功能。
"""

import pytest

from theme_sector_radar.agents.sector_research import (
    TechnicalTrendAgent,
    ShortTermHeatAgent,
    RotationAnalysisAgent,
    RiskControlAgent,
    DataQualityAgent,
    MarketContextAgent,
    NarrativeAgent,
    ConsensusDecisionAgent,
)


class TestTechnicalTrendAgent:
    """测试技术面趋势智能体"""

    def test_multi_window_confirmed(self):
        """测试 multi_window_confirmed -> trend_confirmed"""
        agent = TechnicalTrendAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={},
            consensus_data={
                "multi_window_label": "multi_window_confirmed",
                "consensus_score": 55.0,
                "window_scores": {"5": 55.0, "10": 55.0, "20": 55.0},
            },
        )
        assert result["technical_label"] == "trend_confirmed"
        assert result["technical_score"] > 0.5

    def test_conflicted_windows(self):
        """测试 conflicted_windows -> trend_conflicted"""
        agent = TechnicalTrendAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={},
            consensus_data={
                "multi_window_label": "conflicted_windows",
                "consensus_score": 45.0,
                "window_scores": {"5": 60.0, "10": 40.0, "20": 30.0},
            },
        )
        assert result["technical_label"] == "trend_conflicted"
        assert len(result["technical_conflicts"]) > 0

    def test_weak_all_windows(self):
        """测试 weak_all_windows -> trend_weak"""
        agent = TechnicalTrendAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={},
            consensus_data={
                "multi_window_label": "weak_all_windows",
                "consensus_score": 30.0,
                "window_scores": {"5": 30.0, "10": 30.0, "20": 30.0},
            },
        )
        assert result["technical_label"] == "trend_weak"
        assert result["technical_score"] < 0.3

    def test_insufficient_history(self):
        """测试 insufficient_history -> trend_unreliable"""
        agent = TechnicalTrendAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={},
            consensus_data={
                "multi_window_label": "insufficient_history",
                "consensus_score": 50.0,
                "window_scores": {"5": 50.0, "10": 50.0, "20": 50.0},
            },
        )
        assert result["technical_label"] == "trend_unreliable"
        assert result["technical_score"] <= 0.3


class TestShortTermHeatAgent:
    """测试短线热度智能体"""

    def test_heat_active(self):
        """测试 burst >= 65 -> heat_active"""
        agent = ShortTermHeatAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"short_term_burst_score": 70.0, "trend_continuation_score": 50.0},
        )
        assert result["heat_label"] == "heat_active"
        assert result["heat_score"] == 0.7

    def test_heat_moderate(self):
        """测试 burst 50-65 -> heat_moderate"""
        agent = ShortTermHeatAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"short_term_burst_score": 55.0, "trend_continuation_score": 50.0},
        )
        assert result["heat_label"] == "heat_moderate"

    def test_heat_fading(self):
        """测试 burst 35-50 -> heat_fading"""
        agent = ShortTermHeatAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"short_term_burst_score": 40.0, "trend_continuation_score": 50.0},
        )
        assert result["heat_label"] == "heat_fading"

    def test_heat_weak(self):
        """测试 burst < 35 -> heat_weak"""
        agent = ShortTermHeatAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"short_term_burst_score": 30.0, "trend_continuation_score": 50.0},
        )
        assert result["heat_label"] == "heat_weak"

    def test_burst_high_trend_low_conflict(self):
        """测试 burst 高但 trend 低时有 conflict"""
        agent = ShortTermHeatAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"short_term_burst_score": 70.0, "trend_continuation_score": 40.0},
        )
        assert len(result["heat_conflicts"]) > 0
        assert any("短线热度强但趋势未确认" in c for c in result["heat_conflicts"])


class TestRiskControlAgent:
    """测试风险控制智能体"""

    def test_risk_low(self):
        """测试 risk_penalty <= 3 -> risk_low"""
        agent = RiskControlAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"risk_penalty": 2.0, "trend_window_status": "ok", "data_warnings": []},
        )
        assert result["risk_label"] == "risk_low"
        assert result["risk_score"] >= 0.8

    def test_risk_moderate(self):
        """测试 risk_penalty <= 8 -> risk_moderate"""
        agent = RiskControlAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"risk_penalty": 6.0, "trend_window_status": "ok", "data_warnings": []},
        )
        assert result["risk_label"] == "risk_moderate"

    def test_risk_high(self):
        """测试 risk_penalty <= 15 -> risk_high"""
        agent = RiskControlAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"risk_penalty": 12.0, "trend_window_status": "ok", "data_warnings": []},
        )
        assert result["risk_label"] == "risk_high"

    def test_risk_extreme(self):
        """测试 risk_penalty > 15 -> risk_extreme"""
        agent = RiskControlAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"risk_penalty": 18.0, "trend_window_status": "ok", "data_warnings": []},
        )
        assert result["risk_label"] == "risk_extreme"

    def test_data_warning_in_flags(self):
        """测试 data_warnings 能进入 risk_flags"""
        agent = RiskControlAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"risk_penalty": 5.0, "trend_window_status": "ok", "data_warnings": ["test warning"]},
        )
        assert "data_warning_present" in result["risk_flags"]

    def test_partial_history_is_a_soft_risk_flag(self):
        agent = RiskControlAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={
                "risk_penalty": 2.0,
                "trend_window_status": "partial_history",
                "data_warnings": [],
            },
        )

        assert "history_partial" in result["risk_flags"]
        assert "history_unreliable" not in result["risk_flags"]
        assert result["vote"] == "neutral"


class TestDataQualityAgent:
    """测试数据质量智能体"""

    def test_data_reliable(self):
        """测试 coverage=1.0 status=ok -> data_reliable"""
        agent = DataQualityAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"history_coverage_ratio": 1.0, "trend_window_status": "ok", "actual_history_days": 20},
        )
        assert result["data_quality_label"] == "data_reliable"
        assert result["data_quality_score"] == 1.0

    def test_data_usable(self):
        """测试 coverage=0.8 -> data_usable"""
        agent = DataQualityAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"history_coverage_ratio": 0.8, "trend_window_status": "ok", "actual_history_days": 16},
        )
        assert result["data_quality_label"] == "data_usable"

    def test_data_limited(self):
        """测试 coverage<0.8 -> data_limited"""
        agent = DataQualityAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"history_coverage_ratio": 0.5, "trend_window_status": "ok", "actual_history_days": 10},
        )
        assert result["data_quality_label"] == "data_limited"

    def test_data_unreliable(self):
        """测试 status!=ok -> data_unreliable"""
        agent = DataQualityAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={"history_coverage_ratio": 1.0, "trend_window_status": "insufficient_history", "actual_history_days": 5},
        )
        assert result["data_quality_label"] == "data_unreliable"
        assert result["data_quality_score"] == 0.2

    def test_partial_history_is_limited_but_usable_for_research(self):
        agent = DataQualityAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            score_data={
                "history_coverage_ratio": 0.5,
                "trend_window_status": "partial_history",
                "actual_history_days": 10,
            },
        )

        assert result["data_quality_label"] == "data_limited"
        assert result["data_quality_score"] == 0.5
        assert result["vote"] == "neutral"
        assert any("部分覆盖" in warning for warning in result["data_quality_warnings"])


class TestNarrativeAgent:
    """测试产业叙事智能体"""

    def test_technology_growth(self):
        """测试 半导体 -> technology_growth"""
        agent = NarrativeAgent()
        result = agent.analyze(sector_name="半导体", sector_type="industry")
        assert result["narrative_label"] == "technology_growth"

    def test_healthcare_defensive_recovery(self):
        """测试 医疗服务 -> healthcare_defensive_recovery"""
        agent = NarrativeAgent()
        result = agent.analyze(sector_name="医疗服务", sector_type="industry")
        assert result["narrative_label"] == "healthcare_defensive_recovery"

    def test_financial_stability(self):
        """测试 保险 -> financial_stability"""
        agent = NarrativeAgent()
        result = agent.analyze(sector_name="保险", sector_type="industry")
        assert result["narrative_label"] == "financial_stability"

    def test_general_sector(self):
        """测试 未知板块 -> general_sector"""
        agent = NarrativeAgent()
        result = agent.analyze(sector_name="未知板块", sector_type="industry")
        assert result["narrative_label"] == "general_sector"


class TestConsensusDecisionAgent:
    """测试最终共识确认智能体"""

    def test_insufficient_data(self):
        """测试 数据不可用 -> insufficient_data"""
        agent = ConsensusDecisionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_unreliable", "technical_score": 0.2},
            heat_view={"heat_label": "heat_weak", "heat_score": 0.3},
            rotation_view={"rotation_label": "rotation_neutral", "rotation_score": 0.5},
            risk_view={"risk_label": "risk_moderate", "risk_score": 0.6},
            data_quality_view={"data_quality_label": "data_unreliable", "data_quality_score": 0.2},
            market_context_view={"market_context_label": "neutral_vs_benchmark", "market_context_score": 0.5},
            narrative_view={"narrative_label": "general_sector"},
        )
        assert result["consensus_label"] == "insufficient_data"

    def test_strong_consensus(self):
        """测试 技术确认 + 热度适中 + 风险低 -> strong_consensus"""
        agent = ConsensusDecisionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_confirmed", "technical_score": 0.7},
            heat_view={"heat_label": "heat_moderate", "heat_score": 0.6},
            rotation_view={"rotation_label": "rotation_rising", "rotation_score": 0.7},
            risk_view={"risk_label": "risk_low", "risk_score": 0.9},
            data_quality_view={"data_quality_label": "data_reliable", "data_quality_score": 1.0},
            market_context_view={"market_context_label": "outperforming_benchmark", "market_context_score": 0.8},
            narrative_view={"narrative_label": "technology_growth"},
        )
        assert result["consensus_label"] == "strong_consensus"
        assert result["confirm_level"] == "high"

    def test_trend_confirmed(self):
        """测试 技术确认但热度弱 -> trend_confirmed"""
        agent = ConsensusDecisionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_confirmed", "technical_score": 0.7},
            heat_view={"heat_label": "heat_weak", "heat_score": 0.3},
            rotation_view={"rotation_label": "rotation_neutral", "rotation_score": 0.5},
            risk_view={"risk_label": "risk_moderate", "risk_score": 0.6},
            data_quality_view={"data_quality_label": "data_reliable", "data_quality_score": 1.0},
            market_context_view={"market_context_label": "neutral_vs_benchmark", "market_context_score": 0.5},
            narrative_view={"narrative_label": "general_sector"},
        )
        assert result["consensus_label"] == "trend_confirmed"

    def test_weak_or_avoid(self):
        """测试 默认 weak_or_avoid 或其他弱标签"""
        agent = ConsensusDecisionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_weak", "technical_score": 0.2},
            heat_view={"heat_label": "heat_weak", "heat_score": 0.2},
            rotation_view={"rotation_label": "rotation_weak", "rotation_score": 0.2},
            risk_view={"risk_label": "risk_high", "risk_score": 0.3},
            data_quality_view={"data_quality_label": "data_limited", "data_quality_score": 0.5},
            market_context_view={"market_context_label": "underperforming_benchmark", "market_context_score": 0.3},
            narrative_view={"narrative_label": "general_sector"},
        )
        # 可能是 weak_or_avoid, weak_continuation, 或 low_signal_noise
        assert result["consensus_label"] in ["weak_or_avoid", "weak_continuation", "low_signal_noise"]
