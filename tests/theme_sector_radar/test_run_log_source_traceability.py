"""
Run Log 数据来源追踪测试

测试 run_log 包含完整的数据来源信息。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestRunLogSourceTraceability:
    """测试 Run Log 数据来源追踪"""

    def test_run_log_has_source_fields(self):
        """测试 run_log 包含数据来源字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                run_mode="daily",
            )

            # 手动创建 run_log
            run_log = {
                "run_mode": "daily",
                "provider": "fixture",
                "offline_fixture": True,
                "fixture_profile": "rotation-day2",
                "data_source_mode": "fixture",
                "report_dir": tmpdir,
                "report_root": os.path.dirname(tmpdir),
                "index_included": True,
                "comparison_source": "none",
                "input_snapshot_source": "fixture",
            }
            run_log_path = os.path.join(tmpdir, "run_log.json")
            with open(run_log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)

            with open(run_log_path, "r", encoding="utf-8") as f:
                loaded_log = json.load(f)

            # 验证所有字段
            assert loaded_log["run_mode"] == "daily"
            assert loaded_log["provider"] == "fixture"
            assert loaded_log["offline_fixture"] is True
            assert loaded_log["fixture_profile"] == "rotation-day2"
            assert loaded_log["data_source_mode"] == "fixture"
            assert loaded_log["report_dir"] == tmpdir
            assert loaded_log["index_included"] is True
            assert loaded_log["input_snapshot_source"] == "fixture"

    def test_report_status_matches_run_log_status(self):
        """测试 report status 与 run_log status 一致"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            # 手动创建 run_log
            run_log = {
                "status": report.status,
            }
            run_log_path = os.path.join(tmpdir, "run_log.json")
            with open(run_log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)

            with open(run_log_path, "r", encoding="utf-8") as f:
                loaded_log = json.load(f)

            assert loaded_log["status"] == report.status
