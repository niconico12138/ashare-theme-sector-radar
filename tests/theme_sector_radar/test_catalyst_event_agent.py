"""
CatalystEventAgent 测试

测试催化事件智能体。
"""

import pytest

from theme_sector_radar.agents.sector_research.catalyst_event_agent import CatalystEventAgent
from theme_sector_radar.agents.sector_research.opinion import AgentOpinion


class TestCatalystEventAgent:
    """测试 CatalystEventAgent"""

    def test_cache_not_exists_returns_unknown(self):
        """cache 不存在时返回 catalyst_unknown + neutral"""
        agent = CatalystEventAgent()
        result = agent.analyze(
            "白酒", "industry", "2026-06-29", {}, [], None
        )
        assert result.label == "catalyst_unknown"
        assert result.vote == "neutral"
        assert result.veto is False
        assert result.metadata["decision_impact"] == "report_only"

    def test_matched_industry_event(self):
        """有匹配行业事件时返回 catalyst_observed + neutral"""
        agent = CatalystEventAgent()
        events = [
            {
                "event_id": "test_001",
                "event_date": "2026-06-29",
                "source": "akshare_stock_news_em",
                "title": "茅台发布业绩预告",
                "event_type": "stock_news",
                "related_industries": ["白酒"],
                "related_concepts": [],
                "confidence": 0.8,
                "freshness": "same_day",
            },
        ]
        result = agent.analyze(
            "白酒", "industry", "2026-06-29", {}, events, None
        )
        assert result.label == "catalyst_observed"
        assert result.vote == "neutral"  # report-only
        assert result.veto is False
        assert result.metadata["matched_event_count"] == 1

    def test_matched_concept_event(self):
        """有匹配概念事件时返回 catalyst_observed + neutral"""
        agent = CatalystEventAgent()
        events = [
            {
                "event_id": "test_002",
                "event_date": "2026-06-29",
                "source": "akshare_stock_news_em",
                "title": "宁德时代发布动力电池",
                "event_type": "stock_news",
                "related_industries": [],
                "related_concepts": ["新能源汽车"],
                "confidence": 0.9,
                "freshness": "same_day",
            },
        ]
        result = agent.analyze(
            "新能源汽车", "concept", "2026-06-29", {}, events, None
        )
        assert result.label == "catalyst_observed"
        assert result.vote == "neutral"

    def test_no_matched_event(self):
        """无匹配事件时返回 no_catalyst_observed"""
        agent = CatalystEventAgent()
        events = [
            {
                "event_id": "test_003",
                "related_industries": ["白酒"],
                "related_concepts": [],
                "confidence": 0.8,
                "freshness": "same_day",
            },
        ]
        result = agent.analyze(
            "半导体", "industry", "2026-06-29", {}, events, None
        )
        assert result.label == "no_catalyst_observed"
        assert result.vote == "neutral"

    def test_veto_always_false(self):
        """veto 永远 False"""
        agent = CatalystEventAgent()
        events = [
            {
                "event_id": "test_001",
                "related_industries": ["白酒"],
                "confidence": 0.8,
                "freshness": "same_day",
            },
        ]
        result = agent.analyze(
            "白酒", "industry", "2026-06-29", {}, events, None
        )
        assert result.veto is False

    def test_decision_impact_report_only(self):
        """decision_impact 始终为 report_only"""
        agent = CatalystEventAgent()
        result = agent.analyze(
            "白酒", "industry", "2026-06-29", {}, [], None
        )
        assert result.metadata["decision_impact"] == "report_only"

    def test_all_labels_in_cn_dict(self):
        """所有标签都在中文解释字典中"""
        from theme_sector_radar.agents.sector_research.catalyst_event_agent import CATALYST_LABEL_CN
        for label in ["catalyst_observed", "catalyst_sparse", "no_catalyst_observed", "catalyst_unknown"]:
            assert label in CATALYST_LABEL_CN

    def test_no_trade_advice_words(self):
        """不包含交易建议词"""
        agent = CatalystEventAgent()
        events = [
            {
                "event_id": "test_001",
                "related_industries": ["白酒"],
                "confidence": 0.8,
                "freshness": "same_day",
                "title": "Test event",
            },
        ]
        result = agent.analyze(
            "白酒", "industry", "2026-06-29", {}, events, None
        )
        all_text = " ".join(result.evidence + result.warnings)
        trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
        for word in trade_words:
            assert word not in all_text.lower(), f"包含交易建议词: {word}"

    def test_report_includes_catalyst_section(self):
        """测试报告包含催化事件小节"""
        from theme_sector_radar.reports.sector_research_report import generate_sector_research_markdown_report

        report_data = {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "research_results": [
                {
                    "sector_name": "白酒",
                    "consensus_label": "weak_or_avoid",
                    "ranking_score": 0.3,
                    "opportunity_score": 0.2,
                    "confidence_score": 0.6,
                    "evidence_score": 0.5,
                    "risk_control_score": 0.8,
                    "agent_opinions": [
                        {
                            "agent_id": "catalyst_event",
                            "label": "catalyst_observed",
                            "score": 0.4,
                            "evidence": ["匹配到 1 条外部事件", "事件来源: akshare_stock_news_em"],
                            "metadata": {"matched_event_count": 1},
                        }
                    ],
                    "watch_points": [],
                    "veto": {"veto_triggered": False},
                    "agent_votes": {"positive_votes": 1, "neutral_votes": 3, "negative_votes": 1},
                    "conflict_level": "none",
                    "views": {"data_quality": {"data_quality_label": "data_usable"}},
                },
            ],
        }

        md = generate_sector_research_markdown_report(report_data)
        assert "外部催化事件" in md
        assert "report-only" in md
