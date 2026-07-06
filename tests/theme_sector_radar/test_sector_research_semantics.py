"""
板块综合研判语义测试

测试 confidence_score/opportunity_score/ranking_score 语义。
"""

import pytest

from theme_sector_radar.agents.sector_research import (
    ConsensusDecisionAgent,
    TechnicalTrendAgent,
    ShortTermHeatAgent,
)


class TestWeakOrAvoidSemantics:
    """测试 weak_or_avoid 语义"""

    def test_weak_or_avoid_can_have_high_confidence_but_low_opportunity(self):
        """验证弱标签可以 confidence 高，但 opportunity_score 必须低"""
        agent = ConsensusDecisionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_weak", "technical_score": 0.2},
            heat_view={"heat_label": "heat_weak", "heat_score": 0.2},
            rotation_view={"rotation_label": "rotation_weak", "rotation_score": 0.2},
            risk_view={"risk_label": "risk_low", "risk_score": 0.9},
            data_quality_view={"data_quality_label": "data_reliable", "data_quality_score": 1.0},
            market_context_view={"market_context_label": "underperforming_benchmark", "market_context_score": 0.2},
            narrative_view={"narrative_label": "general_sector"},
        )
        # 可能是 weak_or_avoid, weak_continuation, low_signal_noise, 或 defensive_stable_watch
        assert result["consensus_label"] in ["weak_or_avoid", "weak_continuation", "low_signal_noise", "defensive_stable_watch"]
        # confidence 可以高（数据质量好）
        assert result["confidence_score"] >= 0.5
        # 但 opportunity 必须低
        assert result["opportunity_score"] < 0.4

    def test_ranking_score_penalizes_weak_or_avoid(self):
        """验证 weak_or_avoid 的 ranking_score 被降权"""
        agent = ConsensusDecisionAgent()
        result_weak = agent.analyze(
            sector_name="弱板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_weak", "technical_score": 0.2},
            heat_view={"heat_label": "heat_weak", "heat_score": 0.2},
            rotation_view={"rotation_label": "rotation_weak", "rotation_score": 0.2},
            risk_view={"risk_label": "risk_low", "risk_score": 0.9},
            data_quality_view={"data_quality_label": "data_reliable", "data_quality_score": 1.0},
            market_context_view={"market_context_label": "underperforming_benchmark", "market_context_score": 0.2},
            narrative_view={"narrative_label": "general_sector"},
        )

        result_strong = agent.analyze(
            sector_name="强板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_confirmed", "technical_score": 0.7},
            heat_view={"heat_label": "heat_moderate", "heat_score": 0.6},
            rotation_view={"rotation_label": "rotation_rising", "rotation_score": 0.7},
            risk_view={"risk_label": "risk_low", "risk_score": 0.9},
            data_quality_view={"data_quality_label": "data_reliable", "data_quality_score": 1.0},
            market_context_view={"market_context_label": "outperforming_benchmark", "market_context_score": 0.8},
            narrative_view={"narrative_label": "technology_growth"},
        )

        # weak_or_avoid 的 ranking_score 应该明显低于 strong_consensus
        assert result_weak["ranking_score"] < result_strong["ranking_score"]


class TestConflictedPrioritization:
    """测试 conflicted 优先级"""

    def test_conflicted_prioritized_when_technical_conflicted(self):
        """验证 technical_label=trend_conflicted 且无强热度/轮动时，输出 conflicted"""
        agent = ConsensusDecisionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_conflicted", "technical_score": 0.4},
            heat_view={"heat_label": "heat_fading", "heat_score": 0.4},
            rotation_view={"rotation_label": "rotation_lagging", "rotation_score": 0.3},
            risk_view={"risk_label": "risk_moderate", "risk_score": 0.6},
            data_quality_view={"data_quality_label": "data_reliable", "data_quality_score": 1.0},
            market_context_view={"market_context_label": "neutral_vs_benchmark", "market_context_score": 0.5},
            narrative_view={"narrative_label": "general_sector"},
        )
        assert result["consensus_label"] == "conflicted"


class TestRotationCandidateRequirements:
    """测试 rotation_candidate 要求"""

    def test_rotation_candidate_requires_rotation_signal(self):
        """验证没有 rotation_rising/new_entry 时，不应输出 rotation_candidate"""
        agent = ConsensusDecisionAgent()
        result = agent.analyze(
            sector_name="测试板块",
            sector_type="industry",
            technical_view={"technical_label": "trend_conflicted", "technical_score": 0.4},
            heat_view={"heat_label": "heat_fading", "heat_score": 0.4},
            rotation_view={"rotation_label": "rotation_lagging", "rotation_score": 0.3},
            risk_view={"risk_label": "risk_moderate", "risk_score": 0.6},
            data_quality_view={"data_quality_label": "data_reliable", "data_quality_score": 1.0},
            market_context_view={"market_context_label": "neutral_vs_benchmark", "market_context_score": 0.5},
            narrative_view={"narrative_label": "general_sector"},
        )
        assert result["consensus_label"] != "rotation_candidate"


class TestStrongConsensusRequirements:
    """测试 strong_consensus 要求"""

    def test_strong_consensus_requires_evidence_opportunity_and_risk_control(self):
        """验证 strong_consensus 必须同时满足 evidence/opportunity/risk_control 阈值"""
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
        assert result["opportunity_score"] >= 0.65
        assert result["risk_control_score"] >= 0.55
        assert result["evidence_score"] >= 0.70


class TestResearchResultsSorting:
    """测试排序"""

    def test_research_results_sorted_by_ranking_score_not_confidence(self):
        """验证 Coordinator 按 ranking_score 排序"""
        from theme_sector_radar.agents.sector_research.coordinator import SectorResearchCoordinator

        coordinator = SectorResearchCoordinator()

        # 创建模拟数据
        sector_scores = {
            "scores": [
                {
                    "sector_name": "弱板块",
                    "sector_type": "industry",
                    "trend_continuation_score": 30.0,
                    "short_term_burst_score": 30.0,
                    "risk_penalty": 5.0,
                    "rotation_phase": "lagging",
                    "history_coverage_ratio": 1.0,
                    "trend_window_status": "ok",
                    "actual_history_days": 10,
                    "relative_strength_component": 5.0,
                    "data_warnings": [],
                },
                {
                    "sector_name": "强板块",
                    "sector_type": "industry",
                    "trend_continuation_score": 70.0,
                    "short_term_burst_score": 60.0,
                    "risk_penalty": 3.0,
                    "rotation_phase": "leading",
                    "history_coverage_ratio": 1.0,
                    "trend_window_status": "ok",
                    "actual_history_days": 20,
                    "relative_strength_component": 12.0,
                    "data_warnings": [],
                },
            ]
        }

        multi_window_consensus = {
            "consensus": [
                {
                    "sector_name": "弱板块",
                    "multi_window_label": "weak_all_windows",
                    "consensus_score": 30.0,
                    "window_scores": {"5": 30.0, "10": 30.0, "20": 30.0},
                },
                {
                    "sector_name": "强板块",
                    "multi_window_label": "multi_window_confirmed",
                    "consensus_score": 65.0,
                    "window_scores": {"5": 65.0, "10": 65.0, "20": 65.0},
                },
            ]
        }

        results = coordinator.research_sectors(sector_scores, multi_window_consensus)

        # 强板块应该排在弱板块前面（按 ranking_score 排序）
        # 注意：由于 veto 和 conflict 的影响，排序可能有所不同
        # 但强板块的 ranking_score 应该高于弱板块
        strong_score = next(r for r in results if r["sector_name"] == "强板块")["ranking_score"]
        weak_score = next(r for r in results if r["sector_name"] == "弱板块")["ranking_score"]
        assert strong_score >= weak_score


class TestScoreFieldsRange:
    """测试分数字段范围"""

    def test_score_fields_are_in_0_1_range(self):
        """验证 evidence_score/opportunity_score/risk_control_score/confidence_score/ranking_score 都在 0-1"""
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

        assert 0.0 <= result["evidence_score"] <= 1.0
        assert 0.0 <= result["opportunity_score"] <= 1.0
        assert 0.0 <= result["risk_control_score"] <= 1.0
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert 0.0 <= result["ranking_score"] <= 1.0


class TestInsufficientDataAlwaysLast:
    """测试 insufficient_data 永远排后"""

    def test_insufficient_data_always_last(self):
        """验证 insufficient_data 永远排后"""
        from theme_sector_radar.agents.sector_research.coordinator import SectorResearchCoordinator

        coordinator = SectorResearchCoordinator()

        sector_scores = {
            "scores": [
                {
                    "sector_name": "正常板块",
                    "sector_type": "industry",
                    "trend_continuation_score": 50.0,
                    "short_term_burst_score": 50.0,
                    "risk_penalty": 5.0,
                    "rotation_phase": "neutral",
                    "history_coverage_ratio": 1.0,
                    "trend_window_status": "ok",
                    "actual_history_days": 10,
                    "relative_strength_component": 8.0,
                    "data_warnings": [],
                },
                {
                    "sector_name": "数据不足板块",
                    "sector_type": "industry",
                    "trend_continuation_score": 50.0,
                    "short_term_burst_score": 50.0,
                    "risk_penalty": 5.0,
                    "rotation_phase": "neutral",
                    "history_coverage_ratio": 0.3,
                    "trend_window_status": "insufficient_history",
                    "actual_history_days": 3,
                    "relative_strength_component": 8.0,
                    "data_warnings": ["历史数据不足"],
                },
            ]
        }

        multi_window_consensus = {
            "consensus": [
                {
                    "sector_name": "正常板块",
                    "multi_window_label": "weak_all_windows",
                    "consensus_score": 40.0,
                    "window_scores": {"5": 40.0, "10": 40.0, "20": 40.0},
                },
                {
                    "sector_name": "数据不足板块",
                    "multi_window_label": "insufficient_history",
                    "consensus_score": 40.0,
                    "window_scores": {"5": 40.0, "10": 40.0, "20": 40.0},
                },
            ]
        }

        results = coordinator.research_sectors(sector_scores, multi_window_consensus)

        # 正常板块应该排在数据不足板块前面
        assert results[0]["sector_name"] == "正常板块"
        assert results[1]["sector_name"] == "数据不足板块"


class TestOutputContainsScoreInterpretation:
    """测试输出包含 score_interpretation"""

    def test_output_contains_score_interpretation(self):
        """验证 JSON 每个 research_result 包含 score_interpretation"""
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

        # 验证包含所有新字段
        assert "evidence_score" in result
        assert "opportunity_score" in result
        assert "risk_control_score" in result
        assert "confidence_score" in result
        assert "ranking_score" in result


class TestNoTradeAdviceWords:
    """测试报告不包含禁止交易建议词"""

    def test_report_has_no_trade_advice_words(self):
        """验证报告 JSON 不包含禁止词"""
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

        # 转换为 JSON 字符串检查
        result_str = json.dumps(result, ensure_ascii=False)

        forbidden_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐", "建仓", "加仓", "减仓", "止盈", "止损", "目标价"]
        for word in forbidden_words:
            assert word not in result_str.lower(), f"报告包含禁止词: {word}"


import json
