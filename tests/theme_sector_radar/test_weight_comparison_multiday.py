"""
权重对比多日模式测试

测试多日实验功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.experiments.weight_comparison import (
    generate_multi_day_summary,
    generate_multi_day_summary_md,
)


class TestWeightComparisonMultiday:
    """测试权重对比多日模式"""

    def test_generate_multi_day_summary(self):
        """测试生成多日汇总"""
        comparisons = [
            {
                "as_of_date": "2026-06-27",
                "diff": {
                    "industry_top_changes": {"overlap_rate": 0.8},
                    "concept_top_changes": {"overlap_rate": 0.9},
                    "focus_level_changes": [{"name": "A"}],
                    "risk_level_changes": [],
                },
            },
            {
                "as_of_date": "2026-06-28",
                "diff": {
                    "industry_top_changes": {"overlap_rate": 0.9},
                    "concept_top_changes": {"overlap_rate": 0.85},
                    "focus_level_changes": [],
                    "risk_level_changes": [{"name": "B"}],
                },
            },
        ]

        summary = generate_multi_day_summary(comparisons, "test_output")

        assert summary["total_days"] == 2
        assert len(summary["daily_results"]) == 2
        assert summary["aggregate"]["total_focus_changes"] == 1
        assert summary["aggregate"]["total_risk_changes"] == 1

    def test_generate_multi_day_summary_md(self):
        """测试生成多日汇总 Markdown"""
        summary = {
            "generated_at": "2026-06-29T10:00:00",
            "date_range": {"start": "2026-06-27", "end": "2026-06-28"},
            "total_days": 2,
            "daily_results": [
                {"as_of_date": "2026-06-27", "industry_overlap_rate": 0.8, "concept_overlap_rate": 0.9, "focus_level_changes": 1, "risk_level_changes": 0},
                {"as_of_date": "2026-06-28", "industry_overlap_rate": 0.9, "concept_overlap_rate": 0.85, "focus_level_changes": 0, "risk_level_changes": 1},
            ],
            "aggregate": {
                "avg_industry_overlap_rate": 0.85,
                "avg_concept_overlap_rate": 0.875,
                "total_focus_changes": 1,
                "total_risk_changes": 1,
            },
        }

        md = generate_multi_day_summary_md(summary)

        assert "权重实验多日汇总报告" in md
        assert "2026-06-27" in md
        assert "2026-06-28" in md
        assert "声明" in md

    def test_multiday_insufficient_data(self):
        """测试多日数据不足时结论为 need_more_data"""
        from theme_sector_radar.experiments.weight_comparison import generate_recommendation

        recommendation = generate_recommendation(
            baseline={},
            capital_focused={},
            trend_focused={},
            is_fixture=False,
            cache_days=3,  # 不足 5 天
        )

        assert recommendation["recommendation"] == "need_more_data"
