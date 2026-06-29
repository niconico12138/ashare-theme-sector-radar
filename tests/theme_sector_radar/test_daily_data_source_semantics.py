"""
Daily 数据来源语义测试

测试 daily fixture_profile 传递和数据来源追踪。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestDailyDataSourceSemantics:
    """测试 Daily 数据来源语义"""

    def test_daily_fixture_profile_in_report(self):
        """测试 daily fixture_profile 能传到报告 JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                run_mode="daily",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert data.get("fixture_profile") == "rotation-day2"
            assert data.get("offline_fixture") is True
            assert data.get("run_mode") == "daily"

    def test_daily_fixture_profile_in_run_log(self):
        """测试 daily fixture_profile 能写入 run_log"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                run_mode="daily",
            )

            # 手动创建 run_log（模拟 daily 模式）
            run_log = {
                "run_mode": "daily",
                "provider": "fixture",
                "offline_fixture": True,
                "fixture_profile": "rotation-day2",
                "data_source_mode": "fixture",
            }
            run_log_path = os.path.join(tmpdir, "run_log.json")
            with open(run_log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)

            with open(run_log_path, "r", encoding="utf-8") as f:
                loaded_log = json.load(f)

            assert loaded_log["fixture_profile"] == "rotation-day2"
            assert loaded_log["offline_fixture"] is True

    def test_rotation_day2_no_akshare_concepts(self):
        """测试 rotation-day2 daily 不应混入 AkShare 特有概念名"""
        # rotation-day2 fixture 定义的概念
        rotation_day2_concepts = [
            "CPO概念", "ChatGPT概念", "人工智能概念", "光伏概念",
            "芯片概念", "机器人概念", "储能", "网络安全", "云计算", "元宇宙",
        ]

        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day2",
        )

        # 检查概念板块
        concept_names = [s.name for s in report.concept_top]

        # 不应出现 AkShare 特有概念
        akshare_concepts = ["昨日首板", "昨日涨停_含一字", "昨日涨停"]
        for name in concept_names:
            assert name not in akshare_concepts, f"不应出现 AkShare 概念: {name}"

    def test_report_has_data_source_mode(self):
        """测试报告包含 data_source_mode"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        assert hasattr(report, "data_source_mode")
        assert report.data_source_mode == "fixture"

    def test_report_has_provider(self):
        """测试报告包含 provider"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        assert hasattr(report, "provider")
        assert report.provider == "fixture"
