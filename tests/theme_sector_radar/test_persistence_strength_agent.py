"""
PersistenceStrengthAgent 测试

测试持续性强度智能体。
"""

import pytest

from theme_sector_radar.agents.sector_research.persistence_strength_agent import (
    PersistenceStrengthAgent,
    PERSISTENCE_LABEL_CN,
)
from theme_sector_radar.agents.sector_research.opinion import AgentOpinion


class TestPersistenceStrengthAgent:
    """测试 PersistenceStrengthAgent"""

    def test_timeline_missing_returns_unknown(self):
        """timeline 缺失时返回 persistence_unknown + neutral"""
        agent = PersistenceStrengthAgent()
        result = agent.analyze(
            "测试", "industry", {}, [], None, None
        )
        assert result.label == "persistence_unknown"
        assert result.vote == "neutral"
        assert result.veto is False
        assert result.confidence <= 0.5

    def test_streak_3_rising_returns_confirmed(self):
        """streak >= 3 且趋势 rising 时返回 persistence_confirmed + positive"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.4, "opportunity_score": 0.25, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.5, "opportunity_score": 0.3, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        assert result.label == "persistence_confirmed"
        assert result.vote == "positive"
        assert result.veto is False

    def test_streak_2_building(self):
        """streak == 2 且趋势 rising 时返回 persistence_building"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": False, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.4, "opportunity_score": 0.25, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.5, "opportunity_score": 0.3, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        assert result.label == "persistence_building"

    def test_long_streak_flat_no_risk_building(self):
        """streak >= 5 且 trend flat、无风险时，应为 persistence_building"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        assert result.label == "persistence_building"
        # score may be < 0.55 with flat trend, so vote may be neutral
        assert result.vote in ["positive", "neutral"]

    def test_falling_risk_deteriorating(self):
        """ranking/opportunity falling 且风险延续时返回 persistence_deteriorating + negative"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.5, "opportunity_score": 0.4, "confidence_score": 0.6,
             "is_top_watch": False, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 0.8, "market_regime": {}},
            {"ranking_score": 0.4, "opportunity_score": 0.3, "confidence_score": 0.6,
             "is_top_watch": False, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": True, "risk_control_score": 0.4, "market_regime": {}},
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": False, "consensus_label": "weak_or_avoid",
             "conflict_level": "medium", "veto_triggered": False, "risk_control_score": 0.5, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        assert result.label == "persistence_deteriorating"
        assert result.vote == "negative"

    def test_veto_always_false(self):
        """veto 永远 False"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        assert result.veto is False

    def test_score_range(self):
        """score 在 0-1 范围内"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
            {"ranking_score": 0.4, "opportunity_score": 0.25, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        assert 0 <= result.score <= 1

    def test_confidence_range(self):
        """confidence 在 0-1 范围内"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        assert 0 <= result.confidence <= 1

    def test_all_labels_in_cn_dict(self):
        """所有标签都在中文解释字典中"""
        for label in ["persistence_confirmed", "persistence_building", "persistence_weak",
                      "persistence_deteriorating", "persistence_unknown"]:
            assert label in PERSISTENCE_LABEL_CN

    def test_no_trade_advice_words(self):
        """不包含交易建议词"""
        agent = PersistenceStrengthAgent()
        timeline = [
            {"ranking_score": 0.3, "opportunity_score": 0.2, "confidence_score": 0.6,
             "is_top_watch": True, "consensus_label": "weak_or_avoid",
             "conflict_level": "none", "veto_triggered": False, "risk_control_score": 1.0, "market_regime": {}},
        ]
        result = agent.analyze(
            "测试", "industry",
            {"consensus_label": "weak_or_avoid", "market_regime": {}},
            timeline, None, None,
        )
        all_text = " ".join(result.evidence + result.warnings)
        trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
        for word in trade_words:
            assert word not in all_text.lower(), f"包含交易建议词: {word}"
