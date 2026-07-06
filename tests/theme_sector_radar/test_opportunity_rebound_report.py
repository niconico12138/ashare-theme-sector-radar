"""
Opportunity Rebound Report 测试

测试归因报告生成。
"""

import os
import tempfile

import pytest

from theme_sector_radar.reports.opportunity_rebound_report import (
    generate_opportunity_rebound_report,
    save_opportunity_rebound_report,
)


class TestOpportunityReboundReport:
    """测试 Opportunity Rebound Report"""

    def test_generate_report_basic(self):
        """测试生成基本报告"""
        report_data = {
            "start_date": "2026-06-01",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "input_summary": {"sample_count": 560, "research_report_count": 28},
            "missed_opportunity": {"count": 10, "samples": [], "clusters": {}},
            "failed_rebound": {"count": 5, "samples": [], "clusters": {}},
            "opportunity_buckets": {
                "high": {"sample_count": 0},
                "medium": {"sample_count": 6},
                "low": {"sample_count": 554},
            },
            "high_bucket_diagnosis": {
                "high_bucket_count": 0,
                "near_high_count": 0,
                "dimension_averages": {"technical": 0.35, "heat": 0.30},
                "max_opportunity_score": 0.55,
            },
        }

        report = generate_opportunity_rebound_report(report_data)
        assert "Opportunity Score" in report
        assert "560" in report
        assert "免责声明" in report

    def test_no_trade_advice_words(self):
        """测试报告不包含交易建议词"""
        report_data = {
            "start_date": "2026-06-01",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "input_summary": {"sample_count": 100, "research_report_count": 10},
            "missed_opportunity": {"count": 5, "samples": [], "clusters": {}},
            "failed_rebound": {"count": 3, "samples": [], "clusters": {}},
            "opportunity_buckets": {},
            "high_bucket_diagnosis": {
                "high_bucket_count": 0,
                "near_high_count": 0,
                "dimension_averages": {},
                "max_opportunity_score": 0.5,
            },
        }

        report = generate_opportunity_rebound_report(report_data)
        trade_words = [
            "buy", "sell", "hold", "买入", "卖出", "持有", "推荐",
            "建仓", "加仓", "减仓", "止盈", "止损", "目标价",
        ]
        for word in trade_words:
            assert word not in report.lower(), f"报告中包含交易建议词: {word}"

    def test_save_report(self):
        """测试保存报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_data = {
                "start_date": "2026-06-01",
                "end_date": "2026-06-29",
                "sector_type": "industry",
                "input_summary": {"sample_count": 100},
                "missed_opportunity": {"count": 0, "samples": [], "clusters": {}},
                "failed_rebound": {"count": 0, "samples": [], "clusters": {}},
                "opportunity_buckets": {},
                "high_bucket_diagnosis": {},
            }

            save_opportunity_rebound_report(tmpdir, report_data)

            assert os.path.exists(os.path.join(tmpdir, "opportunity_rebound_analysis.json"))
            assert os.path.exists(os.path.join(tmpdir, "opportunity_rebound_analysis.md"))

    def test_report_with_clusters(self):
        """测试报告包含聚类信息"""
        report_data = {
            "start_date": "2026-06-01",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "input_summary": {"sample_count": 100},
            "missed_opportunity": {
                "count": 5,
                "samples": [
                    {
                        "signal_date": "2026-06-10",
                        "sector_name": "测试板块",
                        "consensus_label": "weak_or_avoid",
                        "ranking_score": 0.2,
                        "opportunity_score": 0.15,
                        "forward_5d_return": 5.0,
                        "pre_5d_return": -8.0,
                        "heat_label": "heat_weak",
                    }
                ],
                "clusters": {
                    "oversold_bounce": {"count": 3, "avg_forward_5d_return": 4.5, "samples": []},
                    "momentum_repair": {"count": 2, "avg_forward_5d_return": 3.0, "samples": []},
                },
            },
            "failed_rebound": {"count": 0, "samples": [], "clusters": {}},
            "opportunity_buckets": {},
            "high_bucket_diagnosis": {
                "high_bucket_count": 0,
                "near_high_count": 0,
                "dimension_averages": {},
                "max_opportunity_score": 0.5,
            },
        }

        report = generate_opportunity_rebound_report(report_data)
        assert "oversold_bounce" in report
        assert "momentum_repair" in report
