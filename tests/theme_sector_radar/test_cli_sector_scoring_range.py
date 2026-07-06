"""
批量板块评分 CLI 测试

测试 --score-sectors-range 命令。
"""

import json
import os
import sys
import tempfile

import pytest

from theme_sector_radar.cli import main


class TestCLISectorScoringRange:
    """测试批量板块评分 CLI"""

    def test_score_sectors_range_help(self):
        """测试 --score-sectors-range 帮助"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = ["cli", "--score-sectors-range", "--help"]
            main()
        assert exc_info.value.code == 0

    def test_score_sectors_range_missing_dates(self):
        """测试缺少日期参数"""
        with pytest.raises(SystemExit) as exc_info:
            sys.argv = [
                "cli",
                "--score-sectors-range",
                "--sector-type", "industry",
            ]
            main()
        assert exc_info.value.code == 1

    def test_score_sectors_range_with_missing_reports(self):
        """测试缺少日报时记录 skipped"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建空的 report-root
            report_root = os.path.join(tmpdir, "reports")
            os.makedirs(report_root)

            # 运行批量评分
            output_dir = os.path.join(tmpdir, "output")
            batch_output = os.path.join(tmpdir, "batch")
            sys.argv = [
                "cli",
                "--score-sectors-range",
                "--start-date", "2026-06-29",
                "--end-date", "2026-06-30",
                "--sector-type", "industry",
                "--report-root", report_root,
                "--score-output", output_dir,
                "--batch-output", batch_output,
                "--history-lookback-days", "5",
                "--top-n", "10",
                "--score-mode", "dual",
                "--benchmark", "none",
            ]
            main()

            # 验证 batch_summary.json
            batch_summary_path = os.path.join(batch_output, "2026-06-29_to_2026-06-30", "batch_summary.json")
            assert os.path.exists(batch_summary_path)

            with open(batch_summary_path, "r", encoding="utf-8") as f:
                batch_summary = json.load(f)

            # 验证字段
            assert batch_summary["start_date"] == "2026-06-29"
            assert batch_summary["end_date"] == "2026-06-30"
            assert batch_summary["total_dates"] == 2
            assert batch_summary["completed_dates"] == 0
            assert len(batch_summary["skipped_dates"]) == 2

    def test_score_sectors_range_with_existing_reports(self):
        """测试有日报时调用评分"""
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

            # 运行批量评分
            output_dir = os.path.join(tmpdir, "output")
            batch_output = os.path.join(tmpdir, "batch")
            sys.argv = [
                "cli",
                "--score-sectors-range",
                "--start-date", "2026-06-29",
                "--end-date", "2026-06-29",
                "--sector-type", "industry",
                "--report-root", report_root,
                "--score-output", output_dir,
                "--batch-output", batch_output,
                "--history-lookback-days", "5",
                "--top-n", "10",
                "--score-mode", "dual",
                "--benchmark", "none",
            ]
            main()

            # 验证 batch_summary.json
            batch_summary_path = os.path.join(batch_output, "2026-06-29_to_2026-06-29", "batch_summary.json")
            assert os.path.exists(batch_summary_path)

            with open(batch_summary_path, "r", encoding="utf-8") as f:
                batch_summary = json.load(f)

            # 验证字段
            assert batch_summary["total_dates"] == 1
            assert batch_summary["completed_dates"] == 1
            assert len(batch_summary["skipped_dates"]) == 0

            # 验证单日评分输出
            score_path = os.path.join(output_dir, "2026-06-29", "sector_scores.json")
            assert os.path.exists(score_path)
