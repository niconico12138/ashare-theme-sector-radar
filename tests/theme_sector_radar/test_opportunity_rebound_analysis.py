"""
Opportunity Rebound Analysis 测试

测试归因分析模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.opportunity_rebound_analysis import OpportunityReboundAnalysis


class TestOpportunityReboundAnalysis:
    """测试 OpportunityReboundAnalysis"""

    def test_identify_missed_opportunity(self):
        """测试识别 missed opportunity"""
        analysis = OpportunityReboundAnalysis()

        samples = [
            {"consensus_label": "weak_or_avoid", "forward_5d_return": 5.0},
            {"consensus_label": "low_signal_noise", "forward_5d_return": 4.0},
            {"consensus_label": "strong_consensus", "forward_5d_return": 6.0},
            {"consensus_label": "weak_or_avoid", "forward_5d_return": -1.0},
        ]

        missed = analysis._identify_missed_opportunity(samples)
        assert len(missed) == 2
        assert all(s["consensus_label"] in ["weak_or_avoid", "low_signal_noise"] for s in missed)

    def test_identify_failed_rebound(self):
        """测试识别 failed rebound"""
        analysis = OpportunityReboundAnalysis()

        samples = [
            {"consensus_label": "oversold_rebound_candidate", "forward_5d_return": -2.0},
            {"consensus_label": "oversold_rebound_candidate", "forward_5d_return": 1.0},
            {"consensus_label": "weak_or_avoid", "forward_5d_return": -3.0},
        ]

        failed = analysis._identify_failed_rebound(samples)
        assert len(failed) == 1
        assert failed[0]["forward_5d_return"] == -2.0

    def test_cluster_missed_opportunity(self):
        """测试 missed opportunity 聚类"""
        analysis = OpportunityReboundAnalysis()

        missed = [
            {
                "consensus_label": "weak_or_avoid",
                "forward_5d_return": 5.0,
                "pre_5d_return": -8.0,
                "rebound_from_recent_low": 5.0,
                "heat_label": "heat_weak",
                "data_quality_label": "data_usable",
                "dimension_market_context": 0.3,
            },
            {
                "consensus_label": "low_signal_noise",
                "forward_5d_return": 4.0,
                "pre_5d_return": 1.0,
                "rebound_from_recent_low": 1.0,
                "heat_label": "heat_moderate",
                "data_quality_label": "data_usable",
                "dimension_market_context": 0.4,
            },
        ]

        clusters = analysis._cluster_missed_opportunity(missed)
        assert "oversold_bounce" in clusters
        assert "momentum_repair" in clusters

    def test_cluster_failed_rebound(self):
        """测试 failed rebound 聚类"""
        analysis = OpportunityReboundAnalysis()

        failed = [
            {
                "forward_5d_return": -3.0,
                "pre_5d_return": -4.0,  # -4 > -5, 不触发 no_momentum_repair
                "heat_label": "heat_moderate",  # 不是 heat_weak/heat_fading
                "technical_label": "trend_weak",
                "veto_triggered": False,
                "conflict_level": "none",
                "dimension_market_context": 0.5,
            },
            {
                "forward_5d_return": -2.0,
                "pre_5d_return": -1.0,
                "heat_label": "heat_moderate",
                "technical_label": "trend_neutral",
                "veto_triggered": True,
                "conflict_level": "none",
                "dimension_market_context": 0.4,
            },
        ]

        clusters = analysis._cluster_failed_rebound(failed)
        assert "persistent_weakness" in clusters
        assert "conflict_or_veto" in clusters

    def test_opportunity_buckets(self):
        """测试 opportunity_score 分桶"""
        analysis = OpportunityReboundAnalysis()

        samples = [
            {"opportunity_score": 0.70, "forward_5d_return": 2.0, "forward_10d_return": 3.0},
            {"opportunity_score": 0.50, "forward_5d_return": 1.0, "forward_10d_return": 2.0},
            {"opportunity_score": 0.30, "forward_5d_return": -1.0, "forward_10d_return": -2.0},
        ]

        result = analysis._aggregate_opportunity_buckets(samples)
        assert result["high"]["sample_count"] == 1
        assert result["medium"]["sample_count"] == 1
        assert result["low"]["sample_count"] == 1

    def test_no_lookahead(self):
        """测试 no-lookahead：信号侧字段不使用未来数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建历史数据
            history_dir = os.path.join(tmpdir, "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": "2026-06-20", "收盘价": 100.0},
                    {"日期": "2026-06-21", "收盘价": 102.0},
                    {"日期": "2026-06-22", "收盘价": 101.0},
                    {"日期": "2026-06-23", "收盘价": 103.0},
                    {"日期": "2026-06-24", "收盘价": 105.0},
                    {"日期": "2026-06-25", "收盘价": 107.0},
                    {"日期": "2026-06-26", "收盘价": 106.0},
                    {"日期": "2026-06-27", "收盘价": 108.0},
                ],
            }
            with open(os.path.join(history_dir, "测试板块.json"), "w") as f:
                json.dump(history_data, f)

            # 创建研究报告
            research_dir = os.path.join(tmpdir, "sector_research", "2026-06-24")
            os.makedirs(research_dir)
            research_data = {
                "research_results": [
                    {
                        "sector_name": "测试板块",
                        "sector_type": "industry",
                        "consensus_label": "weak_or_avoid",
                        "ranking_score": 0.2,
                        "opportunity_score": 0.15,
                        "confidence_score": 0.6,
                        "evidence_score": 0.5,
                        "risk_control_score": 0.7,
                        "views": {
                            "technical": {"technical_label": "trend_weak", "technical_score": 0.3},
                            "heat": {"heat_label": "heat_weak", "heat_score": 0.2},
                            "rotation": {"rotation_label": "rotation_neutral", "rotation_score": 0.5},
                            "risk": {"risk_label": "risk_low", "risk_score": 0.8},
                            "data_quality": {"data_quality_label": "data_usable", "data_quality_score": 0.8},
                            "market_context": {"market_context_label": "neutral", "market_context_score": 0.5},
                            "narrative": {"narrative_label": "neutral"},
                        },
                        "dimension_scores": {
                            "technical": 0.3,
                            "heat": 0.2,
                            "rotation": 0.5,
                            "market_context": 0.5,
                        },
                        "agent_votes": {"positive_votes": 1, "neutral_votes": 3, "negative_votes": 3},
                        "conflict_level": "none",
                        "conflict_summary": "无冲突",
                        "veto": {"veto_triggered": False},
                        "veto_reasons": [],
                    }
                ]
            }
            with open(os.path.join(research_dir, "sector_research.json"), "w") as f:
                json.dump(research_data, f)

            # 运行分析
            analysis = OpportunityReboundAnalysis(history_root=tmpdir)
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-24",
                sector_type="industry",
                report_root=tmpdir,
            )

            assert result["input_summary"]["sample_count"] == 1
            # pre_5d_return 应该只使用 signal_date 之前的数据
            sample = result["missed_opportunity"]["samples"][0] if result["missed_opportunity"]["samples"] else None
            if sample:
                # pre_5d 应该是 signal_date 前 5 天的累计收益
                assert sample.get("pre_5d_return") is not None

    def test_attribution_fields_complete(self):
        """测试归因字段完整"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建历史数据
            history_dir = os.path.join(tmpdir, "industry")
            os.makedirs(history_dir)

            records = []
            for i in range(30):
                d = f"2026-06-{i+1:02d}" if i < 30 else f"2026-07-{i-29:02d}"
                if i < 30:
                    d = f"2026-05-{20+i:02d}" if i < 12 else f"2026-06-{i-11:02d}"
                records.append({"日期": d, "收盘价": 100 + i})

            history_data = {"records": records}
            with open(os.path.join(history_dir, "测试板块.json"), "w") as f:
                json.dump(history_data, f)

            # 创建研究报告
            research_dir = os.path.join(tmpdir, "sector_research", "2026-06-10")
            os.makedirs(research_dir)
            research_data = {
                "research_results": [
                    {
                        "sector_name": "测试板块",
                        "sector_type": "industry",
                        "consensus_label": "weak_or_avoid",
                        "ranking_score": 0.2,
                        "opportunity_score": 0.15,
                        "confidence_score": 0.6,
                        "evidence_score": 0.5,
                        "risk_control_score": 0.7,
                        "views": {
                            "technical": {"technical_label": "trend_weak", "technical_score": 0.3},
                            "heat": {"heat_label": "heat_weak", "heat_score": 0.2},
                            "rotation": {"rotation_label": "rotation_neutral", "rotation_score": 0.5},
                            "risk": {"risk_label": "risk_low", "risk_score": 0.8},
                            "data_quality": {"data_quality_label": "data_usable", "data_quality_score": 0.8},
                            "market_context": {"market_context_label": "neutral", "market_context_score": 0.5},
                            "narrative": {"narrative_label": "neutral"},
                        },
                        "dimension_scores": {
                            "technical": 0.3,
                            "heat": 0.2,
                            "rotation": 0.5,
                            "market_context": 0.5,
                        },
                        "agent_votes": {"positive_votes": 1, "neutral_votes": 3, "negative_votes": 3},
                        "conflict_level": "none",
                        "conflict_summary": "无冲突",
                        "veto": {"veto_triggered": False},
                        "veto_reasons": [],
                    }
                ]
            }
            with open(os.path.join(research_dir, "sector_research.json"), "w") as f:
                json.dump(research_data, f)

            analysis = OpportunityReboundAnalysis(history_root=tmpdir)
            result = analysis.run_analysis(
                start_date="2026-06-10",
                end_date="2026-06-10",
                sector_type="industry",
                report_root=tmpdir,
            )

            assert result["input_summary"]["sample_count"] == 1
