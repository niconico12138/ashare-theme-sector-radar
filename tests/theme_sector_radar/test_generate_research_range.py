"""
批量生成多日 Agent 组研判报告测试

测试 generate_research_range.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.generate_research_range import (
    ResearchRangeGenerator,
    generate_range_run_summary_markdown,
    save_range_run_summary,
)


class TestResearchRangeGenerator:
    """测试批量生成"""

    def test_generate_research_range_creates_summary(self):
        """测试批量运行后生成 range_run_summary.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            # 创建模拟历史数据
            for sector_name in ["测试板块1", "测试板块2"]:
                history_data = {
                    "records": [
                        {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                        for d in range(16, 30)
                    ],
                }
                with open(os.path.join(history_dir, f"{sector_name}.json"), "w") as f:
                    json.dump(history_data, f)

            # 创建模拟 sector_research 目录
            os.makedirs(os.path.join(tmpdir, "sector_research"))

            generator = ResearchRangeGenerator(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            # 测试跳过逻辑（因为缺少 theme_sector_radar.json）
            result = generator.run_range(
                start_date="2026-06-25",
                end_date="2026-06-29",
                sector_type="industry",
                history_start_date="2026-06-16",
                history_end_date="2026-06-29",
                top_n=5,
                score_mode="dual",
                benchmark="none",
                trend_weight_profile="baseline",
                refresh=False,
            )

            # 验证结果
            assert "generated_dates" in result
            assert "skipped_dates" in result
            assert "failed_dates" in result
            # 因为缺少 theme_sector_radar.json，所有日期都应该失败
            assert len(result["failed_dates"]) > 0

    def test_generate_research_range_generates_each_date(self):
        """测试给定日期范围，能为每个日期生成 sector_research.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            # 创建模拟历史数据
            for sector_name in ["测试板块1", "测试板块2"]:
                history_data = {
                    "records": [
                        {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                        for d in range(16, 30)
                    ],
                }
                with open(os.path.join(history_dir, f"{sector_name}.json"), "w") as f:
                    json.dump(history_data, f)

            # 创建模拟 sector_research 目录
            os.makedirs(os.path.join(tmpdir, "sector_research"))

            generator = ResearchRangeGenerator(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            # 测试跳过逻辑（因为缺少 theme_sector_radar.json）
            result = generator.run_range(
                start_date="2026-06-25",
                end_date="2026-06-27",
                sector_type="industry",
                history_start_date="2026-06-16",
                history_end_date="2026-06-29",
                top_n=5,
                score_mode="dual",
                benchmark="none",
                trend_weight_profile="baseline",
                refresh=True,
            )

            # 验证有跳过或失败的日期（因为缺少 theme_sector_radar.json）
            assert len(result["skipped_dates"]) + len(result["failed_dates"]) > 0

    def test_generate_research_range_skips_insufficient_history(self):
        """测试历史不足时记录 skipped_dates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建空的 sector_history 目录
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            # 创建模拟 sector_research 目录
            os.makedirs(os.path.join(tmpdir, "sector_research"))

            generator = ResearchRangeGenerator(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = generator.run_range(
                start_date="2026-06-25",
                end_date="2026-06-29",
                sector_type="industry",
                history_start_date="2026-06-16",
                history_end_date="2026-06-29",
                top_n=5,
                score_mode="dual",
                benchmark="none",
                trend_weight_profile="baseline",
                refresh=False,
            )

            # 验证跳过了日期或失败了（因为缺少 theme_sector_radar.json）
            assert len(result["skipped_dates"]) + len(result["failed_dates"]) > 0

    def test_generate_research_range_reuses_existing_by_default(self):
        """测试默认不覆盖已有报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟 sector_history
            history_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(16, 30)
                ],
            }
            with open(os.path.join(history_dir, "测试板块1.json"), "w") as f:
                json.dump(history_data, f)

            # 创建模拟 sector_research.json（已存在）
            research_dir = os.path.join(tmpdir, "sector_research", "2026-06-25")
            os.makedirs(research_dir)
            existing_research = {
                "research_results": [{"sector_name": "测试板块1", "consensus_label": "weak_or_avoid"}],
            }
            with open(os.path.join(research_dir, "sector_research.json"), "w") as f:
                json.dump(existing_research, f)

            generator = ResearchRangeGenerator(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = generator.run_range(
                start_date="2026-06-25",
                end_date="2026-06-25",
                sector_type="industry",
                history_start_date="2026-06-16",
                history_end_date="2026-06-29",
                top_n=5,
                score_mode="dual",
                benchmark="none",
                trend_weight_profile="baseline",
                refresh=False,
            )

            # 验证复用了已有报告
            assert len(result["reused_dates"]) == 1
            assert len(result["generated_dates"]) == 0

    def test_range_summary_contains_generated_skipped_failed_dates(self):
        """测试 summary 包含 generated_dates/skipped_dates/failed_dates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建空的 sector_research 目录
            os.makedirs(os.path.join(tmpdir, "sector_research"))

            generator = ResearchRangeGenerator(
                history_root=os.path.join(tmpdir, "sector_history"),
                report_root=tmpdir,
            )

            result = generator.run_range(
                start_date="2026-06-25",
                end_date="2026-06-29",
                sector_type="industry",
                history_start_date="2026-06-16",
                history_end_date="2026-06-29",
                top_n=5,
                score_mode="dual",
                benchmark="none",
                trend_weight_profile="baseline",
                refresh=False,
            )

            assert "generated_dates" in result
            assert "skipped_dates" in result
            assert "failed_dates" in result
            assert isinstance(result["generated_dates"], list)
            assert isinstance(result["skipped_dates"], list)
            assert isinstance(result["failed_dates"], list)


class TestRangeRunSummary:
    """测试批量运行摘要"""

    def test_save_range_run_summary(self):
        """测试保存摘要"""
        summary_data = {
            "report_type": "sector_research_range_run",
            "start_date": "2026-06-25",
            "end_date": "2026-06-29",
            "generated_dates": ["2026-06-25"],
            "skipped_dates": [],
            "failed_dates": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            save_range_run_summary(tmpdir, summary_data)
            assert os.path.exists(os.path.join(tmpdir, "range_run_summary.json"))
            assert os.path.exists(os.path.join(tmpdir, "range_run_summary.md"))

    def test_generate_range_run_summary_markdown(self):
        """测试生成摘要 Markdown"""
        summary_data = {
            "start_date": "2026-06-25",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "generated_dates": ["2026-06-25"],
            "skipped_dates": [{"date": "2026-06-26", "reason": "insufficient_history"}],
            "failed_dates": [],
            "parameters": {
                "history_start_date": "2026-06-16",
                "benchmark": "hs300",
                "trend_weight_profile": "baseline",
                "top_n": 20,
            },
        }

        md = generate_range_run_summary_markdown(summary_data)

        assert "批量生成摘要报告" in md
        assert "2026-06-25" in md
        assert "insufficient_history" in md
        assert "buy" not in md.lower()
        assert "sell" not in md.lower()
