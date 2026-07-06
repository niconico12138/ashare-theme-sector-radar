"""
CLI 多窗口共识测试

测试 --multi-window-consensus 命令。
"""

import json
import os
import sys
import tempfile

import pytest

from theme_sector_radar.cli import main


class TestCLIMultiWindowConsensus:
    """测试 CLI 多窗口共识"""

    def test_multi_window_consensus_help(self):
        """测试 --multi-window-consensus 帮助"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["cli", "--multi-window-consensus", "--help"]
            main()
        assert exc_info.value.code == 0

    def test_multi_window_consensus_generates_reports(self):
        """测试 CLI 能生成 multi_window_consensus.json 和 .md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟日报
            report_root = os.path.join(tmpdir, "reports")
            report_dir = os.path.join(report_root, "2026-06-29")
            os.makedirs(report_dir)
            report_data = {
                "report_type": "theme_sector_radar",
                "as_of_date": "2026-06-29",
                "industry_top": [
                    {
                        "sector_id": "test_1",
                        "name": "测试板块1",
                        "type": "industry",
                        "score": 70.0,
                        "positive_score": 75.0,
                        "risk_penalty": 5.0,
                        "data_quality_score": 60.0,
                    }
                ],
                "concept_top": [],
                "provider_status": {},
                "data_completeness": {},
                "cache_fallback": {},
                "fund_flow_coverage": {},
                "constituent_coverage": {},
                "rotation_summary": {},
                "comparison": {},
            }
            with open(os.path.join(report_dir, "theme_sector_radar.json"), "w") as f:
                json.dump(report_data, f)

            # 运行多窗口共识
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--multi-window-consensus",
                "--as-of", "2026-06-29",
                "--sector-type", "industry",
                "--report-root", report_root,
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, "data_cache", "sector_history"),
                "--history-start-date", "2026-06-25",
                "--history-end-date", "2026-06-29",
                "--top-n", "10",
                "--score-mode", "dual",
                "--benchmark", "none",
                "--trend-weight-profile", "baseline",
            ]
            main()

            # 验证输出文件
            consensus_dir = os.path.join(output_dir, "..", "sector_consensus", "2026-06-29")
            assert os.path.exists(os.path.join(consensus_dir, "multi_window_consensus.json"))
            assert os.path.exists(os.path.join(consensus_dir, "multi_window_consensus.md"))

            # 验证 JSON 内容
            with open(os.path.join(consensus_dir, "multi_window_consensus.json"), "r", encoding="utf-8") as f:
                consensus_data = json.load(f)
            assert consensus_data["report_type"] == "multi_window_consensus"
            assert "consensus" in consensus_data

    def test_missing_window_sector_does_not_crash(self):
        """测试某个板块缺少一个窗口时不崩溃"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟日报
            report_root = os.path.join(tmpdir, "reports")
            report_dir = os.path.join(report_root, "2026-06-29")
            os.makedirs(report_dir)
            report_data = {
                "report_type": "theme_sector_radar",
                "as_of_date": "2026-06-29",
                "industry_top": [
                    {
                        "sector_id": "test_1",
                        "name": "测试板块1",
                        "type": "industry",
                        "score": 70.0,
                        "positive_score": 75.0,
                        "risk_penalty": 5.0,
                        "data_quality_score": 60.0,
                    }
                ],
                "concept_top": [],
                "provider_status": {},
                "data_completeness": {},
                "cache_fallback": {},
                "fund_flow_coverage": {},
                "constituent_coverage": {},
                "rotation_summary": {},
                "comparison": {},
            }
            with open(os.path.join(report_dir, "theme_sector_radar.json"), "w") as f:
                json.dump(report_data, f)

            # 运行多窗口共识（使用不同的 top-n 来模拟部分窗口缺失）
            output_dir = os.path.join(tmpdir, "output")
            sys.argv = [
                "cli",
                "--multi-window-consensus",
                "--as-of", "2026-06-29",
                "--sector-type", "industry",
                "--report-root", report_root,
                "--score-output", output_dir,
                "--history-root", os.path.join(tmpdir, "data_cache", "sector_history"),
                "--history-start-date", "2026-06-25",
                "--history-end-date", "2026-06-29",
                "--top-n", "10",
                "--score-mode", "dual",
                "--benchmark", "none",
                "--trend-weight-profile", "baseline",
            ]

            # 不应该崩溃
            main()

            # 验证输出文件存在
            consensus_dir = os.path.join(output_dir, "..", "sector_consensus", "2026-06-29")
            assert os.path.exists(os.path.join(consensus_dir, "multi_window_consensus.json"))
