"""
Run Log 测试

测试 run_log.json 生成。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestRunLog:
    """测试 Run Log"""

    def test_run_log_generated(self):
        """测试 run_log.json 生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "2026-06-28")
            os.makedirs(output_dir, exist_ok=True)

            # 运行分析
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=output_dir,
                offline_fixture=True,
                fixture_profile="full",
            )

            # 手动创建 run_log（模拟 daily 模式）
            run_log = {
                "command_args": "--daily --as-of 2026-06-28",
                "started_at": "2026-06-29T10:00:00",
                "finished_at": "2026-06-29T10:00:30",
                "duration_ms": 30000,
                "provider": "fixture",
                "status": "ok",
                "comparison_status": "none",
                "cache_fallback_used": False,
                "warnings": [],
                "output_files": [
                    "theme_sector_radar.json",
                    "theme_sector_radar.md",
                    "raw_snapshot.json",
                ],
            }
            run_log_path = os.path.join(output_dir, "run_log.json")
            with open(run_log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)

            # 验证 run_log
            assert os.path.exists(run_log_path)
            with open(run_log_path, "r", encoding="utf-8") as f:
                loaded_log = json.load(f)

            assert loaded_log["status"] == "ok"
            assert loaded_log["provider"] == "fixture"
            assert "theme_sector_radar.json" in loaded_log["output_files"]

    def test_run_log_has_required_fields(self):
        """测试 run_log 包含必要字段"""
        required_fields = [
            "command_args",
            "started_at",
            "finished_at",
            "duration_ms",
            "provider",
            "status",
            "comparison_status",
            "cache_fallback_used",
            "warnings",
            "output_files",
        ]

        run_log = {
            "command_args": "--daily --as-of 2026-06-28",
            "started_at": "2026-06-29T10:00:00",
            "finished_at": "2026-06-29T10:00:30",
            "duration_ms": 30000,
            "provider": "fixture",
            "status": "ok",
            "comparison_status": "none",
            "cache_fallback_used": False,
            "warnings": [],
            "output_files": [],
        }

        for field in required_fields:
            assert field in run_log, f"Missing field: {field}"
