"""
VetoRuleAgent 测试

测试 Veto 规则 Agent。
"""

import pytest

from theme_sector_radar.agents.sector_research.veto_rule_agent import VetoRuleAgent
from theme_sector_radar.agents.sector_research.opinion import AgentOpinion, LAYER_SPECIALIZED


class TestVetoRuleAgent:
    """测试 VetoRuleAgent"""

    def test_no_veto(self):
        """测试无 veto"""
        agent = VetoRuleAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_confirmed"),
        ]

        result = agent.apply_veto(
            opinions,
            score_data={
                "data_quality_score": 0.8,
                "history_coverage_ratio": 1.0,
                "risk_level": "risk_low",
                "opportunity_score": 0.6,
            },
            conflict_level="none",
        )

        assert result.veto is False
        assert result.metadata["veto_triggered"] is False

    def test_veto_low_data_quality(self):
        """测试数据质量不足 veto"""
        agent = VetoRuleAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_confirmed"),
        ]

        result = agent.apply_veto(
            opinions,
            score_data={
                "history_coverage_ratio": 0.2,  # 数据覆盖率不足
                "actual_history_days": 3,
                "risk_level": "risk_low",
                "opportunity_score": 0.6,
            },
            conflict_level="none",
        )

        assert result.veto is True
        assert "数据不足" in result.veto_reason

    def test_veto_high_risk(self):
        """测试高风险 veto"""
        agent = VetoRuleAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_confirmed"),
        ]

        result = agent.apply_veto(
            opinions,
            score_data={
                "data_quality_score": 0.8,
                "history_coverage_ratio": 1.0,
                "risk_level": "risk_high",
                "opportunity_score": 0.6,
            },
            conflict_level="none",
        )

        assert result.veto is True
        assert "风险等级过高" in result.veto_reason

    def test_no_veto_low_opportunity(self):
        """测试低机会不再触发 veto（已移除该规则）"""
        agent = VetoRuleAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_confirmed"),
        ]

        result = agent.apply_veto(
            opinions,
            score_data={
                "data_quality_score": 0.8,
                "history_coverage_ratio": 1.0,
                "risk_level": "risk_low",
                "opportunity_score": 0.2,  # 低机会不再 veto
            },
            conflict_level="none",
        )

        assert result.veto is False

    def test_veto_data_unreliable(self):
        """测试数据不可靠 veto"""
        agent = VetoRuleAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_confirmed"),
        ]

        result = agent.apply_veto(
            opinions,
            score_data={
                "data_quality_score": 0.8,
                "history_coverage_ratio": 1.0,
                "risk_level": "risk_low",
                "opportunity_score": 0.5,
                "data_quality_label": "data_unreliable",
            },
            conflict_level="none",
        )

        assert result.veto is True
        assert "数据质量不可靠" in result.veto_reason

    def test_no_veto_low_signal_noise(self):
        """测试 low_signal_noise 默认不 veto"""
        agent = VetoRuleAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_weak"),
        ]

        result = agent.apply_veto(
            opinions,
            score_data={
                "data_quality_score": 0.8,
                "history_coverage_ratio": 1.0,
                "risk_level": "risk_low",
                "opportunity_score": 0.2,
                "consensus_label": "low_signal_noise",
            },
            conflict_level="none",
        )

        assert result.veto is False
