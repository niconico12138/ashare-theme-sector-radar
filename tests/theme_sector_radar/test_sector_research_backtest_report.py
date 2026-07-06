"""
Agent 组复盘评估报告测试

测试 sector_research_backtest_report.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.sector_research_backtest_report import (
    generate_backtest_markdown_report,
    save_backtest_report,
)


class TestSectorResearchBacktestReport:
    """测试 Agent 组复盘评估报告"""

    def _create_mock_report_data(self) -> dict:
        """创建模拟报告数据"""
        return {
            "report_type": "sector_research_backtest",
            "start_date": "2026-06-01",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "input_summary": {
                "research_report_count": 5,
                "sample_count": 50,
                "skipped_dates": [{"date": "2026-06-15", "reason": "Missing report"}],
            },
            "label_performance": {
                "strong_consensus": {"sample_count": 10, "avg_forward_5d_return": 2.5},
                "weak_or_avoid": {"sample_count": 20, "avg_forward_5d_return": -1.0},
            },
            "ranking_score_bucket_performance": {
                "high": {"sample_count": 15, "avg_forward_5d_return": 2.0},
                "medium": {"sample_count": 20, "avg_forward_5d_return": 0.5},
                "low": {"sample_count": 15, "avg_forward_5d_return": -0.5},
            },
            "opportunity_score_bucket_performance": {},
            "confidence_score_bucket_performance": {},
            "sample_analysis": {
                "best_follow_through": [],
                "worst_follow_through": [],
                "false_positive_candidates": [],
                "missed_opportunity_candidates": [],
                "high_confidence_label_checks": [],
            },
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

    def test_generate_backtest_markdown_report(self):
        """测试生成 Markdown 字符串"""
        report_data = self._create_mock_report_data()
        report = generate_backtest_markdown_report(report_data)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_report_contains_required_sections(self):
        """测试报告包含必需章节"""
        report_data = self._create_mock_report_data()
        report = generate_backtest_markdown_report(report_data)

        assert "Agent 组复盘评估报告" in report
        assert "免责声明" in report
        assert "回测参数" in report
        assert "总览" in report
        assert "按标签表现" in report
        assert "按 ranking_score 分桶表现" in report
        assert "复盘观察" in report
        assert "数据限制" in report

    def test_report_has_no_trade_advice_words(self):
        """测试报告不包含禁止词"""
        report_data = self._create_mock_report_data()
        report = generate_backtest_markdown_report(report_data)

        forbidden_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐", "建仓", "加仓", "减仓", "止盈", "止损", "目标价"]
        for word in forbidden_words:
            assert word not in report.lower(), f"报告包含禁止词: {word}"

    def test_save_backtest_report(self):
        """测试保存报告"""
        report_data = self._create_mock_report_data()

        with tempfile.TemporaryDirectory() as tmpdir:
            save_backtest_report(tmpdir, report_data)
            assert os.path.exists(os.path.join(tmpdir, "research_backtest.md"))
