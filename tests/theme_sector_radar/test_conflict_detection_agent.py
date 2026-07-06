"""
ConflictDetectionAgent 测试

测试冲突检测 Agent。
"""

import pytest

from theme_sector_radar.agents.sector_research.conflict_detection_agent import ConflictDetectionAgent
from theme_sector_radar.agents.sector_research.opinion import AgentOpinion, LAYER_SPECIALIZED


class TestConflictDetectionAgent:
    """测试 ConflictDetectionAgent"""

    def test_detect_no_conflict(self):
        """测试无冲突 - 所有Agent投票一致"""
        agent = ConflictDetectionAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_confirmed", vote="positive"),
            AgentOpinion(agent_id="short_term_heat", layer=LAYER_SPECIALIZED, label="heat_moderate", vote="neutral"),
            AgentOpinion(agent_id="rotation_analysis", layer=LAYER_SPECIALIZED, label="rotation_neutral", vote="neutral"),
            AgentOpinion(agent_id="risk_control", layer=LAYER_SPECIALIZED, label="risk_low", vote="positive"),
            AgentOpinion(agent_id="data_quality", layer=LAYER_SPECIALIZED, label="data_usable", vote="neutral"),
            AgentOpinion(agent_id="market_context", layer=LAYER_SPECIALIZED, label="neutral_vs_benchmark", vote="neutral"),
        ]

        result = agent.detect(opinions)
        assert result.metadata["conflict_level"] == "none"
        assert len(result.metadata["conflicts"]) == 0

    def test_detect_trend_heat_conflict(self):
        """测试趋势-热度投票冲突"""
        agent = ConflictDetectionAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_weak", vote="negative"),
            AgentOpinion(agent_id="short_term_heat", layer=LAYER_SPECIALIZED, label="heat_active", vote="positive"),
            AgentOpinion(agent_id="rotation_analysis", layer=LAYER_SPECIALIZED, label="rotation_neutral", vote="neutral"),
            AgentOpinion(agent_id="risk_control", layer=LAYER_SPECIALIZED, label="risk_low", vote="positive"),
            AgentOpinion(agent_id="data_quality", layer=LAYER_SPECIALIZED, label="data_usable", vote="neutral"),
            AgentOpinion(agent_id="market_context", layer=LAYER_SPECIALIZED, label="neutral_vs_benchmark", vote="neutral"),
        ]

        result = agent.detect(opinions)
        assert result.metadata["conflict_level"] != "none"
        assert len(result.metadata["conflicts"]) > 0

    def test_detect_rotation_trend_conflict(self):
        """测试轮动-趋势投票冲突"""
        agent = ConflictDetectionAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_weak", vote="negative"),
            AgentOpinion(agent_id="short_term_heat", layer=LAYER_SPECIALIZED, label="heat_weak", vote="negative"),
            AgentOpinion(agent_id="rotation_analysis", layer=LAYER_SPECIALIZED, label="rotation_rising", vote="positive"),
            AgentOpinion(agent_id="risk_control", layer=LAYER_SPECIALIZED, label="risk_low", vote="positive"),
            AgentOpinion(agent_id="data_quality", layer=LAYER_SPECIALIZED, label="data_usable", vote="neutral"),
            AgentOpinion(agent_id="market_context", layer=LAYER_SPECIALIZED, label="neutral_vs_benchmark", vote="neutral"),
        ]

        result = agent.detect(opinions)
        assert result.metadata["conflict_level"] != "none"

    def test_no_conflict_when_all_neutral(self):
        """测试全neutral不触发冲突"""
        agent = ConflictDetectionAgent()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_neutral", vote="neutral"),
            AgentOpinion(agent_id="short_term_heat", layer=LAYER_SPECIALIZED, label="heat_moderate", vote="neutral"),
            AgentOpinion(agent_id="rotation_analysis", layer=LAYER_SPECIALIZED, label="rotation_neutral", vote="neutral"),
            AgentOpinion(agent_id="risk_control", layer=LAYER_SPECIALIZED, label="risk_moderate", vote="neutral"),
            AgentOpinion(agent_id="data_quality", layer=LAYER_SPECIALIZED, label="data_usable", vote="neutral"),
            AgentOpinion(agent_id="market_context", layer=LAYER_SPECIALIZED, label="neutral_vs_benchmark", vote="neutral"),
        ]

        result = agent.detect(opinions)
        assert result.metadata["conflict_level"] == "none"
        assert len(result.metadata["conflicts"]) == 0

    def test_data_confidence_conflict_requires_majority_positive(self):
        """测试数据-置信度冲突需要多数positive投票"""
        agent = ConflictDetectionAgent()
        # data质量负向但多数Agent正向
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="trend_confirmed", vote="positive"),
            AgentOpinion(agent_id="short_term_heat", layer=LAYER_SPECIALIZED, label="heat_active", vote="positive"),
            AgentOpinion(agent_id="rotation_analysis", layer=LAYER_SPECIALIZED, label="rotation_rising", vote="positive"),
            AgentOpinion(agent_id="risk_control", layer=LAYER_SPECIALIZED, label="risk_low", vote="positive"),
            AgentOpinion(agent_id="data_quality", layer=LAYER_SPECIALIZED, label="data_limited", vote="negative"),
            AgentOpinion(agent_id="market_context", layer=LAYER_SPECIALIZED, label="outperforming_benchmark", vote="positive"),
        ]

        result = agent.detect(opinions)
        # 应该触发 data_confidence_conflict
        conflict_types = [c["type"] for c in result.metadata["conflicts"]]
        assert "data_confidence_conflict" in conflict_types
