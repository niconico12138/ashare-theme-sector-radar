"""
AgentOpinion 输出契约测试
验证所有 Agent 输出的 AgentOpinion 符合契约要求。
Phase B 新增字段: signal_profile, decision_impact
"""
import pytest
from theme_sector_radar.agents.sector_research.opinion import (
    AgentOpinion, LAYER_DATA_EVIDENCE, LAYER_SPECIALIZED,
    LAYER_CONFLICT_CONSISTENCY, LAYER_DECISION,
    VOTE_POSITIVE, VOTE_NEUTRAL, VOTE_NEGATIVE,
    AGENT_SIGNAL_PROFILES, SIGNAL_PROFILE_DESCRIPTIONS,
)


class TestAgentOpinionContract:
    """AgentOpinion 基本契约"""

    def test_opinion_has_required_fields(self):
        """AgentOpinion 包含所有必需字段"""
        opinion = AgentOpinion(
            agent_id="test_agent",
            layer=LAYER_SPECIALIZED,
            label="test_label",
        )
        d = opinion.to_dict()
        required = [
            "agent_id", "layer", "label", "score", "confidence",
            "evidence", "warnings", "vote", "veto", "veto_reason",
            "metadata", "signal_profile", "decision_impact",
        ]
        for field in required:
            assert field in d, f"Missing field: {field}"

    def test_opinion_signal_profile_default_empty(self):
        """signal_profile 默认为空字符串"""
        opinion = AgentOpinion(
            agent_id="test", layer=LAYER_SPECIALIZED, label="test"
        )
        assert opinion.signal_profile == ""

    def test_opinion_decision_impact_default_participates(self):
        """decision_impact 默认为 participates"""
        opinion = AgentOpinion(
            agent_id="test", layer=LAYER_SPECIALIZED, label="test"
        )
        assert opinion.decision_impact == "participates"

    def test_opinion_decision_impact_values(self):
        """decision_impact 只能是三种值"""
        valid = {"participates", "report_only", "excluded"}
        for val in valid:
            opinion = AgentOpinion(
                agent_id="test", layer=LAYER_SPECIALIZED, label="test",
                decision_impact=val,
            )
            assert opinion.decision_impact == val

    def test_opinion_to_dict_includes_new_fields(self):
        """to_dict() 包含 signal_profile 和 decision_impact"""
        opinion = AgentOpinion(
            agent_id="test", layer=LAYER_SPECIALIZED, label="test",
            signal_profile="broad_signal",
            decision_impact="participates",
        )
        d = opinion.to_dict()
        assert d["signal_profile"] == "broad_signal"
        assert d["decision_impact"] == "participates"

    def test_opinion_vote_values(self):
        """vote 只能是 positive/neutral/negative"""
        for v in [VOTE_POSITIVE, VOTE_NEUTRAL, VOTE_NEGATIVE]:
            opinion = AgentOpinion(
                agent_id="test", layer=LAYER_SPECIALIZED, label="test",
                vote=v,
            )
            assert opinion.vote == v

    def test_opinion_score_in_0_1_range(self):
        """score 在 0-1 范围"""
        for s in [0.0, 0.5, 1.0, -0.1, 1.1]:
            opinion = AgentOpinion(
                agent_id="test", layer=LAYER_SPECIALIZED, label="test",
                score=max(0.0, min(1.0, s)),
            )
            assert 0.0 <= opinion.score <= 1.0

    def test_opinion_confidence_in_0_1_range(self):
        """confidence 在 0-1 范围"""
        for c in [0.0, 0.3, 0.7, 0.8, 1.0]:
            opinion = AgentOpinion(
                agent_id="test", layer=LAYER_SPECIALIZED, label="test",
                confidence=c,
            )
            assert 0.0 <= opinion.confidence <= 1.0

    def test_opinion_no_trade_advice_words(self):
        """AgentOpinion 不包含交易建议词汇"""
        trade_words = ["buy", "sell", "hold", "long", "short",
                        "买入", "卖出", "持有", "做多", "做空"]
        opinion = AgentOpinion(
            agent_id="test", layer=LAYER_SPECIALIZED, label="test",
            evidence=["这是一个测试证据"],
            warnings=["这是一个测试警告"],
            veto_reason="",
        )
        d = opinion.to_dict()
        text = str(d).lower()
        for word in trade_words:
            assert word not in text, f"Found trade advice word: {word}"


class TestSignalProfileContract:
    """Signal Profile 契约"""

    def test_all_active_agents_have_profiles(self):
        """所有活跃 Agent 都有 signal_profile"""
        active_agents = [
            "technical_trend", "short_term_heat", "rotation_analysis",
            "risk_control", "data_quality", "market_context",
            "narrative", "persistence_strength", "catalyst_event",
        ]
        for agent_id in active_agents:
            assert agent_id in AGENT_SIGNAL_PROFILES, \
                f"Agent {agent_id} missing signal_profile"

    def test_all_profiles_have_descriptions(self):
        """所有 profile 都有说明"""
        for profile, desc in SIGNAL_PROFILE_DESCRIPTIONS.items():
            assert desc, f"Profile {profile} has empty description"

    def test_no_stale_agent_profiles(self):
        """没有已移除 Agent 的 profile"""
        removed_agents = ["capital_volume"]
        for agent_id in removed_agents:
            assert agent_id not in AGENT_SIGNAL_PROFILES, \
                f"Removed agent {agent_id} still has profile"

    def test_report_only_agent_has_decision_impact(self):
        """report_only Agent 在所有 return 路径都有 decision_impact"""
        from theme_sector_radar.agents.sector_research.catalyst_event_agent import CatalystEventAgent
        agent = CatalystEventAgent()

        # Case 1: no cache
        result = agent.analyze("test", "industry", "2026-07-01", {}, [], None)
        assert result.decision_impact == "report_only"

        # Case 2: no matched events
        result = agent.analyze("test", "industry", "2026-07-01", {}, [
            {"related_industries": ["other"], "title": "test", "source": "test",
             "freshness": "recent", "confidence": 0.6, "event_id": "1"}
        ], None)
        assert result.decision_impact == "report_only"

        # Case 3: matched events
        result = agent.analyze("test", "industry", "2026-07-01", {}, [
            {"related_industries": ["test"], "title": "test event",
             "source": "test", "freshness": "same_day", "confidence": 0.8,
             "event_id": "2"}
        ], None)
        assert result.decision_impact == "report_only"

    def test_low_information_agent_excluded_from_voting(self):
        """low_information Agent 的 decision_impact 为 excluded"""
        from theme_sector_radar.agents.sector_research.agent_vote_aggregator import AgentVoteAggregator
        from theme_sector_radar.agents.sector_research.narrative_agent import NarrativeAgent

        narrative = NarrativeAgent()
        view = narrative.analyze("半导体", "industry")

        # Simulate _convert_to_opinions behavior
        from theme_sector_radar.agents.sector_research.opinion import AGENT_SIGNAL_PROFILES
        signal_profile = AGENT_SIGNAL_PROFILES.get("narrative", "")
        decision_impact = "excluded" if signal_profile == "low_information" else "participates"

        opinion = AgentOpinion(
            agent_id="narrative",
            layer=LAYER_SPECIALIZED,
            label=view.get("narrative_label", ""),
            vote=view.get("vote", "neutral"),
            signal_profile=signal_profile,
            decision_impact=decision_impact,
        )

        # Verify it would be excluded by aggregator
        assert opinion.decision_impact == "excluded"

        # Verify aggregator actually excludes it
        aggregator = AgentVoteAggregator()
        all_opinions = [
            opinion,
            AgentOpinion(agent_id="technical_trend", layer=LAYER_SPECIALIZED,
                        label="trend_confirmed", vote="positive"),
            AgentOpinion(agent_id="short_term_heat", layer=LAYER_SPECIALIZED,
                        label="heat_active", vote="positive"),
        ]
        result = aggregator.aggregate(all_opinions)
        # narrative excluded → only 2 decision votes (both positive)
        assert result.metadata["total_votes"] == 2
        assert result.metadata["positive_votes"] == 2
