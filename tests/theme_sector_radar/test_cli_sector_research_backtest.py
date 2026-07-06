"""
CLI Agent 组复盘评估测试

测试 --backtest-research-agents 命令。
"""

import json
import os
import sys
import tempfile

import pytest

from theme_sector_radar.cli import main


class TestCLIBacktestResearchAgents:
    """测试 CLI Agent 组复盘评估"""

    def test_backtest_research_agents_help(self):
        """测试 --backtest-research-agents 帮助"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["cli", "--backtest-research-agents", "--help"]
            main()
        assert exc_info.value.code == 0

    def test_backtest_research_agents_generates_reports(self):
        """测试 CLI 能生成 research_backtest.json 和 .md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_research.json
            research_dir = os.path.join(tmpdir, "sector_research", "2026-06-29")
            os.makedirs(research_dir)
            research_data = {
                "research_results": [
                    {
                        "sector_name": "测试板块",
                        "consensus_label": "weak_or_avoid",
                        "ranking_score": 0.3,
                        "confidence_score": 0.6,
                    }
                ],
            }
            with open(os.path.join(research_dir, "sector_research.json"), "w") as f:
                json.dump(research_data, f)

            # 运行回测
            output_dir = os.path.join(tmpdir, "reports")
            sys.argv = [
                "cli",
                "--backtest-research-agents",
                "--start-date", "2026-06-29",
                "--end-date", "2026-06-29",
                "--sector-type", "industry",
                "--history-root", os.path.join(tmpdir, "data_cache", "sector_history"),
                "--report-root", output_dir,
            ]
            main()

            # 验证输出文件
            backtest_dir = os.path.join(output_dir, "backtests", "sector_research", "2026-06-29_to_2026-06-29")
            assert os.path.exists(os.path.join(backtest_dir, "research_backtest.json"))
            assert os.path.exists(os.path.join(backtest_dir, "research_backtest.md"))

            # 验证 JSON 内容
            with open(os.path.join(backtest_dir, "research_backtest.json"), "r", encoding="utf-8") as f:
                backtest_data = json.load(f)
            assert backtest_data["report_type"] == "sector_research_backtest"
            assert "label_performance" in backtest_data
