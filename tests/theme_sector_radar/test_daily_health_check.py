"""
每日健康检查测试

测试 daily_health_check.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.daily_health_check import (
    DailyHealthCheck,
    save_daily_health_check,
    generate_daily_health_check_md,
)


class TestDailyHealthCheck:
    """测试 DailyHealthCheck"""

    def _create_mock_data(self, tmpdir: str, as_of_date: str = "2026-06-29"):
        """创建模拟数据"""
        # 创建 radar report
        radar_dir = os.path.join(tmpdir, "theme_sector_radar", as_of_date)
        os.makedirs(radar_dir)
        radar_data = {
            "status": "ok",
            "data_quality_score": 85.0,
            "data_source_mode": "akshare_refresh",
            "provider_status": {"effective_provider": "akshare"},
        }
        with open(os.path.join(radar_dir, "theme_sector_radar.json"), "w") as f:
            json.dump(radar_data, f)

        # 创建 sector_research
        research_dir = os.path.join(tmpdir, "sector_research", as_of_date)
        os.makedirs(research_dir)
        research_data = {
            "research_results": [
                {
                    "sector_name": "测试",
                    "consensus_label": "weak_or_avoid",
                    "agent_opinions": [{"agent_id": "test", "vote": "neutral"}],
                }
            ],
            "daily_summary": {"market_regime": "choppy_market"},
        }
        with open(os.path.join(research_dir, "sector_research.json"), "w") as f:
            json.dump(research_data, f)

    def test_check_basic(self):
        """测试基本检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            checker = DailyHealthCheck(report_root=tmpdir)
            result = checker.run_check("2026-06-29")

            assert result["overall_status"] == "ok"
            assert result["radar_status"] == "ok"
            assert result["research_status"] == "ok"

    def test_missing_radar_failed(self):
        """测试缺 radar report => failed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = DailyHealthCheck(report_root=tmpdir)
            result = checker.run_check("2026-06-29")

            assert result["overall_status"] == "failed"

    def test_fixture_audit_required(self):
        """测试 fixture 混入 real daily => audit_required"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 radar report with fixture mode
            radar_dir = os.path.join(tmpdir, "theme_sector_radar", "2026-06-29")
            os.makedirs(radar_dir)
            radar_data = {"status": "ok", "data_source_mode": "fixture"}
            with open(os.path.join(radar_dir, "theme_sector_radar.json"), "w") as f:
                json.dump(radar_data, f)

            checker = DailyHealthCheck(report_root=tmpdir)
            result = checker.run_check("2026-06-29")

            assert result["overall_status"] == "audit_required"

    def test_health_check_json_fields(self):
        """测试 health_check JSON 字段完整"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            checker = DailyHealthCheck(report_root=tmpdir)
            result = checker.run_check("2026-06-29")

            assert "as_of_date" in result
            assert "overall_status" in result
            assert "checks" in result
            assert "warnings" in result
            assert "key_outputs" in result

    def test_health_check_md_generation(self):
        """测试 health_check Markdown 生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            checker = DailyHealthCheck(report_root=tmpdir)
            result = checker.run_check("2026-06-29")

            md = generate_daily_health_check_md(result)
            assert "每日健康检查报告" in md
            assert "总体状态" in md

    def test_save_health_check(self):
        """测试保存 health check"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            checker = DailyHealthCheck(report_root=tmpdir)
            result = checker.run_check("2026-06-29")

            output_dir = os.path.join(tmpdir, "output")
            save_daily_health_check(output_dir, result)

            assert os.path.exists(os.path.join(output_dir, "daily_health_check.json"))
            assert os.path.exists(os.path.join(output_dir, "daily_health_check.md"))

    def test_no_trade_advice_words(self):
        """测试不包含交易建议词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            checker = DailyHealthCheck(report_root=tmpdir)
            result = checker.run_check("2026-06-29")

            md = generate_daily_health_check_md(result)
            trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
            for word in trade_words:
                assert word not in md.lower(), f"报告包含交易建议词: {word}"
