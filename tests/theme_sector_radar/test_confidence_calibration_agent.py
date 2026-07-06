"""
ConfidenceCalibrationAgent 测试

测试置信度校准 Agent。
"""

import pytest

from theme_sector_radar.agents.sector_research.confidence_calibration_agent import ConfidenceCalibrationAgent
from theme_sector_radar.agents.sector_research.opinion import AgentOpinion, LAYER_SPECIALIZED, LAYER_CONFLICT_CONSISTENCY


class TestConfidenceCalibrationAgent:
    """测试 ConfidenceCalibrationAgent"""

    def test_calibrate_high_confidence(self):
        """测试高置信度校准"""
        agent = ConfidenceCalibrationAgent()

        vote_opinion = AgentOpinion(
            agent_id="vote_aggregator",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="majority_positive",
            metadata={"positive_votes": 5, "neutral_votes": 1, "negative_votes": 0, "total_votes": 6},
        )

        conflict_opinion = AgentOpinion(
            agent_id="conflict_detection",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="none",
            metadata={"conflict_level": "none", "conflicts": []},
        )

        veto_opinion = AgentOpinion(
            agent_id="veto_rule",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="veto_not_applied",
            veto=False,
            metadata={"veto_triggered": False, "veto_reasons": []},
        )

        result = agent.calibrate(
            score_data={
                "data_quality_score": 0.9,
                "history_coverage_ratio": 1.0,
                "confidence_score": 0.8,
            },
            vote_opinion=vote_opinion,
            conflict_opinion=conflict_opinion,
            veto_opinion=veto_opinion,
        )

        # 校准后置信度应该 > 0
        assert result.metadata["calibrated_confidence_score"] > 0

    def test_calibrate_low_confidence_with_veto(self):
        """测试有 veto 时的低置信度校准"""
        agent = ConfidenceCalibrationAgent()

        vote_opinion = AgentOpinion(
            agent_id="vote_aggregator",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="majority_negative",
            metadata={"positive_votes": 1, "neutral_votes": 1, "negative_votes": 4, "total_votes": 6},
        )

        conflict_opinion = AgentOpinion(
            agent_id="conflict_detection",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="high",
            metadata={"conflict_level": "high", "conflicts": [{"type": "test"}]},
        )

        veto_opinion = AgentOpinion(
            agent_id="veto_rule",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="veto_applied",
            veto=True,
            metadata={"veto_triggered": True, "veto_reasons": ["test veto"]},
        )

        result = agent.calibrate(
            score_data={
                "data_quality_score": 0.5,
                "history_coverage_ratio": 0.5,
                "confidence_score": 0.7,
            },
            vote_opinion=vote_opinion,
            conflict_opinion=conflict_opinion,
            veto_opinion=veto_opinion,
        )

        # 有 veto 时置信度应该降低
        assert result.metadata["calibrated_confidence_score"] < 0.5
