"""
权重对比报告测试

测试权重对比报告生成。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.experiments.weight_comparison import (
    generate_comparison_md,
    generate_comparison_report,
)


class TestWeightComparisonReport:
    """测试权重对比报告"""

    def test_comparison_md_has_required_sections(self):
        """测试 comparison.md 包含必要章节"""
        report = {
            "as_of_date": "2026-06-28",
            "generated_at": "2026-06-29T10:00:00",
            "input_snapshot_path": "test.json",
            "input_snapshot_hash": "abc123def456",
            "input_snapshot_source": "fixture",
            "weight_configs": [
                {"name": "baseline", "description": "baseline", "industry_weights": {"capital_flow": 0.25, "trend_strength": 0.25}},
            ],
            "results": {
                "baseline": {"industry_top": [{"name": "A"}], "concept_top": [{"name": "X"}]},
                "capital_focused": {"industry_top": [{"name": "A"}], "concept_top": [{"name": "X"}]},
                "trend_focused": {"industry_top": [{"name": "A"}], "concept_top": [{"name": "X"}]},
            },
            "diff": {
                "industry_top_changes": {"overlap_rate": 1.0},
                "concept_top_changes": {"overlap_rate": 1.0},
                "focus_level_changes": [],
                "risk_level_changes": [],
            },
            "recommendation": {"recommendation": "need_more_data", "reasons": ["test"]},
        }

        md = generate_comparison_md(report)

        # 检查必要章节
        assert "权重实验对比报告" in md
        assert "实验输入" in md
        assert "权重方案" in md
        assert "行业 Top N 对比" in md
        assert "概念 Top N 对比" in md
        assert "初步结论" in md
        assert "声明" in md

    def test_comparison_md_has_disclaimer(self):
        """测试 comparison.md 包含声明"""
        report = {
            "as_of_date": "2026-06-28",
            "generated_at": "2026-06-29T10:00:00",
            "input_snapshot_path": "test.json",
            "input_snapshot_hash": "abc123def456",
            "input_snapshot_source": "fixture",
            "weight_configs": [],
            "results": {
                "baseline": {"industry_top": [], "concept_top": []},
                "capital_focused": {"industry_top": [], "concept_top": []},
                "trend_focused": {"industry_top": [], "concept_top": []},
            },
            "diff": {
                "industry_top_changes": {"overlap_rate": 0},
                "concept_top_changes": {"overlap_rate": 0},
                "focus_level_changes": [],
                "risk_level_changes": [],
            },
            "recommendation": {"recommendation": "need_more_data", "reasons": []},
        }

        md = generate_comparison_md(report)

        assert "不作为个股操作依据" in md

    def test_comparison_md_no_stock_recommendation(self):
        """测试 comparison.md 不包含个股操作结论"""
        report = {
            "as_of_date": "2026-06-28",
            "generated_at": "2026-06-29T10:00:00",
            "input_snapshot_path": "test.json",
            "input_snapshot_hash": "abc123def456",
            "input_snapshot_source": "fixture",
            "weight_configs": [],
            "results": {
                "baseline": {"industry_top": [], "concept_top": []},
                "capital_focused": {"industry_top": [], "concept_top": []},
                "trend_focused": {"industry_top": [], "concept_top": []},
            },
            "diff": {
                "industry_top_changes": {"overlap_rate": 0},
                "concept_top_changes": {"overlap_rate": 0},
                "focus_level_changes": [],
                "risk_level_changes": [],
            },
            "recommendation": {"recommendation": "need_more_data", "reasons": []},
        }

        md = generate_comparison_md(report)

        assert "buy" not in md.lower()
        assert "sell" not in md.lower()
        assert "hold" not in md.lower()

    def test_single_day_fixture_recommendation(self):
        """测试单日 fixture 默认 recommendation=need_more_data"""
        from theme_sector_radar.experiments.weight_comparison import generate_recommendation

        recommendation = generate_recommendation(
            baseline={},
            capital_focused={},
            trend_focused={},
            is_fixture=True,
        )

        assert recommendation["recommendation"] == "need_more_data"
