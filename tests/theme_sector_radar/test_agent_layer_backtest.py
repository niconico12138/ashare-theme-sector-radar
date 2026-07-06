"""
分层 Agent 回测测试

测试 agent_layer_backtest.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.agent_layer_backtest import AgentLayerBacktest


class TestAgentLayerBacktest:
    """测试 AgentLayerBacktest"""

    def test_run_backtest_with_missing_reports(self):
        """测试缺少报告时记录 skipped_dates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建空的 sector_research 目录
            os.makedirs(os.path.join(tmpdir, "sector_research"))

            backtest = AgentLayerBacktest(history_root=os.path.join(tmpdir, "sector_history"))
            result = backtest.run_backtest(
                start_date="2026-06-25",
                end_date="2026-06-29",
                sector_type="industry",
                report_root=tmpdir,
            )

            assert result["input_summary"]["sample_count"] == 0
            assert len(result["input_summary"]["skipped_dates"]) == 5

    def test_compute_forward_returns_missing_file(self):
        """测试计算后续表现时文件不存在"""
        backtest = AgentLayerBacktest(history_root="/nonexistent/path")
        result = backtest._compute_forward_returns(
            sector_name="test",
            signal_date="2026-06-25",
            end_date="2026-06-29",
            sector_type="industry",
        )

        assert result["forward_1d_return"] is None
        assert result["forward_5d_return"] is None

    def test_compute_group_stats_empty(self):
        """测试空分组统计"""
        backtest = AgentLayerBacktest()
        result = backtest._compute_group_stats([])

        assert result["sample_count"] == 0
        assert result["avg_forward_5d_return"] is None
