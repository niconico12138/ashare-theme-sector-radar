"""
CLI 分层 Agent 回测测试

测试 --backtest-agent-layers 命令。
"""

import json
import os
import sys
import tempfile

import pytest

from theme_sector_radar.cli import main


class TestCLIAgentLayerBacktest:
    """测试 CLI 分层 Agent 回测"""

    def test_backtest_agent_layers_help(self):
        """测试 --backtest-agent-layers 帮助"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["cli", "--backtest-agent-layers", "--help"]
            main()
        assert exc_info.value.code == 0

    def test_backtest_agent_layers_missing_dates(self):
        """测试缺少日期参数"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = [
                "cli",
                "--backtest-agent-layers",
                "--sector-type", "industry",
            ]
            main()
        assert exc_info.value.code == 1

    def test_backtest_agent_layers_generates_report(self):
        """测试能生成报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建空的 sector_research 目录
            os.makedirs(os.path.join(tmpdir, "sector_research"))

            # 运行回测
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--backtest-agent-layers",
                "--start-date", "2026-06-25",
                "--end-date", "2026-06-29",
                "--sector-type", "industry",
                "--history-root", os.path.join(tmpdir, "sector_history"),
                "--report-root", tmpdir,
            ]
            main()

            # 验证输出文件
            backtest_dir = os.path.join(tmpdir, "backtests", "agent_layers", "2026-06-25_to_2026-06-29")
            assert os.path.exists(os.path.join(backtest_dir, "agent_layer_backtest.json"))
            assert os.path.exists(os.path.join(backtest_dir, "agent_layer_backtest.md"))
