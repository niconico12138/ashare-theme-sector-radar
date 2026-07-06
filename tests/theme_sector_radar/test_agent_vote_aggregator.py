"""
AgentVoteAggregator 测试

测试 Agent 投票聚合器。
"""

import pytest

from theme_sector_radar.agents.sector_research.agent_vote_aggregator import AgentVoteAggregator
from theme_sector_radar.agents.sector_research.opinion import AgentOpinion, LAYER_SPECIALIZED, VOTE_POSITIVE, VOTE_NEUTRAL, VOTE_NEGATIVE


class TestAgentVoteAggregator:
    """测试 AgentVoteAggregator"""

    def test_aggregate_majority_positive(self):
        """测试多数正向投票"""
        agent = AgentVoteAggregator()
        opinions = [
            AgentOpinion(agent_id="a1", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(agent_id="a2", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(agent_id="a3", layer=LAYER_SPECIALIZED, label="neutral", vote=VOTE_NEUTRAL),
        ]

        result = agent.aggregate(opinions)
        assert result.vote == VOTE_POSITIVE
        assert result.metadata["positive_votes"] == 2
        assert result.metadata["neutral_votes"] == 1

    def test_aggregate_majority_negative(self):
        """测试多数负向投票"""
        agent = AgentVoteAggregator()
        opinions = [
            AgentOpinion(agent_id="a1", layer=LAYER_SPECIALIZED, label="negative", vote=VOTE_NEGATIVE),
            AgentOpinion(agent_id="a2", layer=LAYER_SPECIALIZED, label="negative", vote=VOTE_NEGATIVE),
            AgentOpinion(agent_id="a3", layer=LAYER_SPECIALIZED, label="neutral", vote=VOTE_NEUTRAL),
        ]

        result = agent.aggregate(opinions)
        assert result.vote == VOTE_NEGATIVE
        assert result.metadata["negative_votes"] == 2

    def test_aggregate_mixed_signals(self):
        """测试混合信号"""
        agent = AgentVoteAggregator()
        opinions = [
            AgentOpinion(agent_id="a1", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(agent_id="a2", layer=LAYER_SPECIALIZED, label="neutral", vote=VOTE_NEUTRAL),
            AgentOpinion(agent_id="a3", layer=LAYER_SPECIALIZED, label="negative", vote=VOTE_NEGATIVE),
        ]

        result = agent.aggregate(opinions)
        assert result.metadata["positive_votes"] == 1
        assert result.metadata["neutral_votes"] == 1
        assert result.metadata["negative_votes"] == 1

    def test_report_only_excluded_from_voting(self):
        """H2: report-only (catalyst_event) 不参与投票计数"""
        agent = AgentVoteAggregator()
        opinions = [
            AgentOpinion(agent_id="a1", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(
                agent_id="catalyst_event",
                layer=LAYER_SPECIALIZED,
                label="catalyst_observed",
                vote="neutral",
                metadata={"decision_impact": "report_only"},
            ),
        ]

        result = agent.aggregate(opinions)
        # catalyst_event 的 neutral 不应计入
        assert result.metadata["positive_votes"] == 1
        assert result.metadata["neutral_votes"] == 0
        assert result.metadata["total_votes"] == 1
        assert result.metadata["report_only_count"] == 1
        # positive_ratio 应为 1.0 (不是 0.5)
        assert result.score == 1.0
        assert result.vote == VOTE_POSITIVE

    def test_report_only_majority_positive_excludes_neutral_report_only(self):
        """H2: 4 个 positive 决策 Agent + 1 个 catalyst neutral => ratio = 1.0"""
        agent = AgentVoteAggregator()
        opinions = [
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(agent_id="short_term_heat", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(agent_id="rotation_analysis", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(agent_id="risk_control", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(
                agent_id="catalyst_event",
                layer=LAYER_SPECIALIZED,
                label="catalyst_observed",
                vote="neutral",
                metadata={"decision_impact": "report_only"},
            ),
        ]

        result = agent.aggregate(opinions)
        assert result.metadata["positive_votes"] == 4
        assert result.metadata["neutral_votes"] == 0  # catalyst 不计数
        assert result.metadata["total_votes"] == 4
        assert result.score == 1.0
        assert result.vote == VOTE_POSITIVE
        assert result.label == "majority_positive"

    def test_all_report_only_no_division_by_zero(self):
        """H2: 所有 opinion 都是 report-only 时不除零"""
        agent = AgentVoteAggregator()
        opinions = [
            AgentOpinion(
                agent_id="catalyst_event",
                layer=LAYER_SPECIALIZED,
                label="catalyst_unknown",
                vote="neutral",
                metadata={"decision_impact": "report_only"},
            ),
        ]

        result = agent.aggregate(opinions)
        # 不应除零
        assert result.metadata["total_votes"] == 0
        assert result.metadata["report_only_count"] == 1
        assert result.label == "no_decision_opinions"
        assert result.score == 0.0

    def test_market_regime_report_only_excluded(self):
        """H2: MarketRegimeContext report-only 也不参与投票"""
        agent = AgentVoteAggregator()
        opinions = [
            AgentOpinion(agent_id="a1", layer=LAYER_SPECIALIZED, label="positive", vote=VOTE_POSITIVE),
            AgentOpinion(agent_id="a2", layer=LAYER_SPECIALIZED, label="negative", vote=VOTE_NEGATIVE),
            AgentOpinion(
                agent_id="market_context",
                layer=LAYER_SPECIALIZED,
                label="risk_on",
                vote="neutral",
                metadata={"decision_impact": "report_only"},
            ),
        ]

        result = agent.aggregate(opinions)
        assert result.metadata["positive_votes"] == 1
        assert result.metadata["negative_votes"] == 1
        assert result.metadata["neutral_votes"] == 0  # market_context report-only 不计数
        assert result.metadata["total_votes"] == 2
        # ratio = 1/2 = 0.5 → mixed_signals
        assert result.vote == "neutral"
        assert result.label == "mixed_signals"
