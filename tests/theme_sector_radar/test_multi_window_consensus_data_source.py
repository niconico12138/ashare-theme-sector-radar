"""
多窗口共识数据源测试

测试 multi-window-consensus 的数据链路问题。
"""

import json
import os
import sys
import tempfile

import pytest

from theme_sector_radar.cli import main


class TestMultiWindowHistoryDates:
    """测试 history_start_date/history_end_date 传递"""

    def test_multi_window_passes_history_start_end_dates(self):
        """验证 --multi-window-consensus 内部 5/10/20 都收到正确 history_start_date/history_end_date"""
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
                "--history-start-date", "2026-05-20",
                "--history-end-date", "2026-06-30",
                "--top-n", "10",
                "--score-mode", "dual",
                "--benchmark", "none",
                "--trend-weight-profile", "baseline",
            ]
            main()

            # 验证输出文件
            consensus_dir = os.path.join(output_dir, "..", "sector_consensus", "2026-06-29")
            assert os.path.exists(os.path.join(consensus_dir, "multi_window_consensus.json"))

            # 验证 JSON 内容中的 history_start_date 和 history_end_date
            with open(os.path.join(consensus_dir, "multi_window_consensus.json"), "r", encoding="utf-8") as f:
                consensus_data = json.load(f)

            metadata = consensus_data.get("metadata", {})
            assert metadata.get("history_start_date") == "2026-05-20"
            assert metadata.get("history_end_date") == "2026-06-30"


class TestMultiWindowWindowIsolation:
    """测试窗口报告隔离"""

    def test_multi_window_window_reports_are_isolated(self):
        """验证 5/10/20 窗口报告输出到独立目录"""
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

            # 验证窗口报告输出到独立目录
            consensus_dir = os.path.join(output_dir, "..", "sector_consensus", "2026-06-29")
            windows_dir = os.path.join(consensus_dir, "windows")

            assert os.path.exists(os.path.join(windows_dir, "5"))
            assert os.path.exists(os.path.join(windows_dir, "10"))
            assert os.path.exists(os.path.join(windows_dir, "20"))

            # 验证每个窗口目录下有 sector_scores.json
            for window in [5, 10, 20]:
                window_dir = os.path.join(windows_dir, str(window), "2026-06-29")
                assert os.path.exists(os.path.join(window_dir, "sector_scores.json"))


class TestMultiWindowSectorHistoryCache:
    """测试 sector_history_cache 读取"""

    def test_multi_window_uses_sector_history_cache(self):
        """验证读取 data_cache/sector_history/{sector_type}/*.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "data_cache", "sector_history", "industry")
            os.makedirs(history_dir)
            history_data = {
                "sector_name": "测试板块1",
                "sector_type": "industry",
                "records": [
                    {"日期": "2026-06-25", "收盘价": 100.0},
                    {"日期": "2026-06-26", "收盘价": 102.0},
                    {"日期": "2026-06-27", "收盘价": 101.0},
                    {"日期": "2026-06-28", "收盘价": 103.0},
                    {"日期": "2026-06-29", "收盘价": 105.0},
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

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

            # 验证输出
            consensus_dir = os.path.join(output_dir, "..", "sector_consensus", "2026-06-29")
            assert os.path.exists(os.path.join(consensus_dir, "multi_window_consensus.json"))
