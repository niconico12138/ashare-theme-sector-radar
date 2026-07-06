"""
分层 Agent 回测报告测试

测试 agent_layer_backtest_report.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.agent_layer_backtest_report import (
    generate_agent_layer_backtest_markdown_report,
    save_agent_layer_backtest_report,
)


class TestAgentLayerBacktestReport:
    """测试 agent_layer_backtest_report"""

    def test_generate_markdown_report(self):
        """测试生成 Markdown 报告"""
        report_data = {
            "start_date": "2026-06-25",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "input_summary": {
                "research_report_count": 5,
                "sample_count": 100,
                "skipped_dates": [],
            },
            "layer_performance": {},
            "agent_performance": {},
            "vote_performance": {},
            "conflict_performance": {},
            "veto_performance": {},
            "confidence_calibration_performance": {},
            "false_positive_by_agent": [],
            "missed_opportunity_by_agent": [],
        }

        md_report = generate_agent_layer_backtest_markdown_report(report_data)

        assert "分层 Agent 回测报告" in md_report
        assert "免责声明" in md_report
        assert "输入摘要" in md_report
        assert "买" not in md_report.lower()
        assert "卖" not in md_report.lower()

    def test_save_report(self):
        """测试保存报告"""
        report_data = {
            "start_date": "2026-06-25",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "input_summary": {
                "research_report_count": 5,
                "sample_count": 100,
                "skipped_dates": [],
            },
            "layer_performance": {},
            "agent_performance": {},
            "vote_performance": {},
            "conflict_performance": {},
            "veto_performance": {},
            "confidence_calibration_performance": {},
            "false_positive_by_agent": [],
            "missed_opportunity_by_agent": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            save_agent_layer_backtest_report(tmpdir, report_data)

            assert os.path.exists(os.path.join(tmpdir, "agent_layer_backtest.json"))
            assert os.path.exists(os.path.join(tmpdir, "agent_layer_backtest.md"))
