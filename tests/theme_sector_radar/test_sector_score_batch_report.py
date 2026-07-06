"""
批量评分报告测试

测试 sector_score_batch_report.py 模块的各项功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.sector_score_batch_report import (
    generate_batch_summary,
    generate_batch_summary_markdown,
    generate_timeseries_data,
    generate_timeseries_markdown,
    save_batch_reports,
)


class TestBatchSummary:
    """测试批量汇总"""

    def test_generate_batch_summary(self):
        """测试生成批量汇总"""
        summary = generate_batch_summary(
            start_date="2026-06-29",
            end_date="2026-06-30",
            sector_type="industry",
            score_mode="dual",
            benchmark="hs300",
            total_dates=2,
            completed_dates=["2026-06-29"],
            skipped_dates=[{"date": "2026-06-30", "reason": "missing_daily_report"}],
            failed_dates=[],
            output_dirs=["reports/sector_scores/2026-06-29"],
        )

        assert summary["start_date"] == "2026-06-29"
        assert summary["end_date"] == "2026-06-30"
        assert summary["total_dates"] == 2
        assert summary["completed_dates"] == 1
        assert len(summary["skipped_dates"]) == 1
        assert len(summary["failed_dates"]) == 0

    def test_generate_batch_summary_markdown(self):
        """测试生成批量汇总 Markdown"""
        summary = generate_batch_summary(
            start_date="2026-06-29",
            end_date="2026-06-30",
            sector_type="industry",
            score_mode="dual",
            benchmark="hs300",
            total_dates=2,
            completed_dates=["2026-06-29"],
            skipped_dates=[{"date": "2026-06-30", "reason": "missing_daily_report"}],
            failed_dates=[],
            output_dirs=["reports/sector_scores/2026-06-29"],
        )

        daily_scores = {
            "2026-06-29": {
                "scores": [
                    {
                        "sector_name": "测试板块1",
                        "trend_continuation_score": 51.0,
                        "trend_level": "neutral",
                        "short_term_burst_score": 49.5,
                        "burst_level": "burst_fading",
                        "score_interpretation": {"profile": "neutral"},
                    }
                ]
            }
        }

        md_report = generate_batch_summary_markdown(summary, daily_scores)

        assert "批量评分汇总" in md_report
        assert "2026-06-29" in md_report
        assert "测试板块1" in md_report
        assert "buy" not in md_report.lower()
        assert "sell" not in md_report.lower()


class TestTimeseriesData:
    """测试时间序列数据"""

    def test_generate_timeseries_data(self):
        """测试生成时间序列数据"""
        daily_scores = {
            "2026-06-29": {
                "scores": [
                    {
                        "sector_name": "测试板块1",
                        "sector_type": "industry",
                        "trend_continuation_score": 51.0,
                        "trend_level": "neutral",
                        "short_term_burst_score": 49.5,
                        "burst_level": "burst_fading",
                        "score_interpretation": {"profile": "neutral"},
                        "history_source": "sector_history_cache",
                        "benchmark_mode": "market_benchmark",
                    }
                ]
            },
            "2026-06-30": {
                "scores": [
                    {
                        "sector_name": "测试板块1",
                        "sector_type": "industry",
                        "trend_continuation_score": 55.0,
                        "trend_level": "neutral",
                        "short_term_burst_score": 52.0,
                        "burst_level": "burst_neutral",
                        "score_interpretation": {"profile": "neutral"},
                        "history_source": "sector_history_cache",
                        "benchmark_mode": "market_benchmark",
                    }
                ]
            },
        }

        timeseries = generate_timeseries_data(daily_scores)

        assert len(timeseries) == 1
        assert timeseries[0]["sector_name"] == "测试板块1"
        assert len(timeseries[0]["records"]) == 2
        assert timeseries[0]["summary"]["days"] == 2
        assert timeseries[0]["summary"]["avg_trend_score"] == 53.0

    def test_generate_timeseries_markdown(self):
        """测试生成时间序列 Markdown"""
        timeseries = [
            {
                "sector_name": "测试板块1",
                "sector_type": "industry",
                "records": [
                    {"date": "2026-06-29", "trend_continuation_score": 51.0, "trend_level": "neutral",
                     "short_term_burst_score": 49.5, "burst_level": "burst_fading", "profile": "neutral",
                     "rank_trend": 1, "history_source": "sector_history_cache", "benchmark_mode": "market_benchmark"},
                ],
                "summary": {
                    "days": 1,
                    "avg_trend_score": 51.0,
                    "avg_burst_score": 49.5,
                    "best_trend_score": 51.0,
                    "best_burst_score": 49.5,
                    "trend_level_counts": {"neutral": 1},
                    "burst_level_counts": {"burst_fading": 1},
                },
            }
        ]

        md_report = generate_timeseries_markdown(timeseries)

        assert "板块分数时间序列" in md_report
        assert "测试板块1" in md_report
        assert "2026-06-29" in md_report
        assert "buy" not in md_report.lower()
        assert "sell" not in md_report.lower()


class TestSaveBatchReports:
    """测试保存批量报告"""

    def test_save_batch_reports(self):
        """测试保存批量报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = generate_batch_summary(
                start_date="2026-06-29",
                end_date="2026-06-29",
                sector_type="industry",
                score_mode="dual",
                benchmark="hs300",
                total_dates=1,
                completed_dates=["2026-06-29"],
                skipped_dates=[],
                failed_dates=[],
                output_dirs=[],
            )

            daily_scores = {
                "2026-06-29": {
                    "scores": [
                        {
                            "sector_name": "测试板块1",
                            "trend_continuation_score": 51.0,
                            "trend_level": "neutral",
                            "short_term_burst_score": 49.5,
                            "burst_level": "burst_fading",
                            "score_interpretation": {"profile": "neutral"},
                        }
                    ]
                }
            }

            timeseries = generate_timeseries_data(daily_scores)

            save_batch_reports(tmpdir, summary, daily_scores, timeseries)

            # 验证文件
            assert os.path.exists(os.path.join(tmpdir, "batch_summary.json"))
            assert os.path.exists(os.path.join(tmpdir, "batch_summary.md"))
            assert os.path.exists(os.path.join(tmpdir, "sector_score_timeseries.json"))
            assert os.path.exists(os.path.join(tmpdir, "sector_score_timeseries.md"))
