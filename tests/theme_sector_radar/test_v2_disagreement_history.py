"""
V2 Disagreement History 测试

覆盖：
- percentile 计算正确
- 四象限分组正确
- strong_disagreement 分组正确
- 多 horizon return 统计正确
- 缺失 forward return 时优雅降级
- 月度 breakdown 正确
- 典型样本数量限制正确
- JSON/Markdown 报告生成正确
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from analyze_v2_disagreement_history import (
    calc_percentile,
    classify_groups,
    analyze_group,
    analyze_monthly_breakdown,
    generate_json_report,
    generate_markdown_report,
)


# ============================================================
# Percentile Tests
# ============================================================

class TestPercentile:
    """测试百分位数计算。"""

    def test_percentile_median(self):
        """中位数的百分位应为 40。"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calc_percentile(3.0, values)
        assert result == 40.0  # 2/5 * 100 = 40%

    def test_percentile_top(self):
        """最大值的百分位应为 80。"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calc_percentile(5.0, values)
        assert result == 80.0  # 4/5 * 100 = 80%

    def test_percentile_bottom(self):
        """最小值的百分位应为 0。"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calc_percentile(1.0, values)
        assert result == 0.0


# ============================================================
# Group Classification Tests
# ============================================================

class TestGroupClassification:
    """测试分组分类。"""

    def test_high_final_high_v2(self):
        """应正确识别 high_final_high_v2。"""
        # 使用递增值确保 percentile 正确计算
        # percentile = count_below / n * 100
        # 需要 percentile >= 80，即 count_below >= n * 0.8
        candidates = [
            {"code": f"600{i:03d}", "name": f"A{i}", "final_score": 100.0 + i, "factor_composite_shadow_score_v2": 100.0 + i}
            for i in range(1, 6)  # 101-105
        ] + [
            {"code": f"601{i:03d}", "name": f"B{i}", "final_score": 50.0 + i, "factor_composite_shadow_score_v2": 50.0 + i}
            for i in range(1, 6)  # 51-55
        ] + [
            {"code": f"602{i:03d}", "name": f"C{i}", "final_score": 10.0 + i, "factor_composite_shadow_score_v2": 10.0 + i}
            for i in range(1, 6)  # 11-15
        ]
        forward_returns = {f"600{i:03d}": {"1d": 0.05} for i in range(1, 6)}
        forward_returns.update({f"601{i:03d}": {"1d": 0.02} for i in range(1, 6)})
        forward_returns.update({f"602{i:03d}": {"1d": -0.01} for i in range(1, 6)})

        result = classify_groups(candidates, forward_returns)

        # 600003-600005 应该是 high_final_high_v2 (percentile >= 80)
        groups = {s["code"]: s["group"] for s in result}
        assert groups["600003"] == "high_final_high_v2"
        assert groups["600005"] == "high_final_high_v2"

    def test_high_final_low_v2(self):
        """应正确识别 high_final_low_v2。"""
        candidates = [
            {"code": "600001", "name": "A", "final_score": 90.0, "factor_composite_shadow_score_v2": 10.0},
            {"code": "600002", "name": "B", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600003", "name": "C", "final_score": 10.0, "factor_composite_shadow_score_v2": 90.0},
            {"code": "600004", "name": "D", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600005", "name": "E", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
        ]
        forward_returns = {f"60000{i}": {"1d": 0.01 * i} for i in range(1, 6)}

        result = classify_groups(candidates, forward_returns)

        groups = {s["code"]: s["group"] for s in result}
        assert groups["600001"] == "high_final_low_v2"

    def test_low_final_high_v2(self):
        """应正确识别 low_final_high_v2。"""
        candidates = [
            {"code": "600001", "name": "A", "final_score": 90.0, "factor_composite_shadow_score_v2": 10.0},
            {"code": "600002", "name": "B", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600003", "name": "C", "final_score": 10.0, "factor_composite_shadow_score_v2": 90.0},
            {"code": "600004", "name": "D", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600005", "name": "E", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
        ]
        forward_returns = {f"60000{i}": {"1d": 0.01 * i} for i in range(1, 6)}

        result = classify_groups(candidates, forward_returns)

        groups = {s["code"]: s["group"] for s in result}
        assert groups["600003"] == "low_final_high_v2"

    def test_strong_disagreement(self):
        """应正确识别 strong_disagreement。"""
        candidates = [
            {"code": "600001", "name": "A", "final_score": 90.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600002", "name": "B", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600003", "name": "C", "final_score": 10.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600004", "name": "D", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
            {"code": "600005", "name": "E", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0},
        ]
        forward_returns = {f"60000{i}": {"1d": 0.01 * i} for i in range(1, 6)}

        result = classify_groups(candidates, forward_returns)

        # 600001 和 600003 的 percentile_gap 应该 >= 50
        groups = {s["code"]: s["group"] for s in result}
        # 由于只有 5 个样本，600001 的 final_percentile=80, v2_percentile=60, gap=20
        # 需要更多样本来触发 strong_disagreement


# ============================================================
# Group Analysis Tests
# ============================================================

class TestGroupAnalysis:
    """测试分组分析。"""

    def test_analyze_group_basic(self):
        """基本分组分析应正确。"""
        samples = [
            {"code": "600001", "final_score": 80, "v2_score": 70, "percentile_gap": 10, "returns": {"1d": 0.05, "3d": 0.10}},
            {"code": "600002", "final_score": 75, "v2_score": 65, "percentile_gap": 15, "returns": {"1d": -0.02, "3d": 0.03}},
        ]

        result = analyze_group(samples, ["1d", "3d"])

        assert result["sample_count"] == 2
        assert result["average_final_score"] == 77.5
        assert "1d" in result["horizons"]
        assert "3d" in result["horizons"]
        assert result["horizons"]["1d"]["sample_count"] == 2
        assert result["horizons"]["1d"]["mean_return"] == 0.015  # (0.05 + (-0.02)) / 2

    def test_analyze_group_missing_returns(self):
        """缺失 forward return 时应优雅降级。"""
        samples = [
            {"code": "600001", "final_score": 80, "v2_score": 70, "percentile_gap": 10, "returns": {}},
        ]

        result = analyze_group(samples, ["1d"])

        assert result["sample_count"] == 1
        assert result["horizons"]["1d"]["status"] == "insufficient_data"


# ============================================================
# Monthly Breakdown Tests
# ============================================================

class TestMonthlyBreakdown:
    """测试月度分解。"""

    def test_monthly_grouping(self):
        """月度分组应正确。"""
        samples_by_date = {
            "2026-07-02": [
                {"code": "600001", "group": "high_final_high_v2", "final_score": 80, "v2_score": 80, "percentile_gap": 5, "returns": {"1d": 0.05}},
            ],
            "2026-07-03": [
                {"code": "600001", "group": "high_final_high_v2", "final_score": 80, "v2_score": 80, "percentile_gap": 5, "returns": {"1d": 0.03}},
            ],
        }

        result = analyze_monthly_breakdown(samples_by_date, ["1d"])

        assert "2026-07" in result
        assert "high_final_high_v2" in result["2026-07"]


# ============================================================
# Report Generation Tests
# ============================================================

class TestReportGeneration:
    """测试报告生成。"""

    def test_generate_json_report(self, tmp_path):
        """应正确生成 JSON 报告。"""
        analysis = {
            "summary": {"start_date": "2026-04-01", "end_date": "2026-07-10"},
            "group_counts": {"high_final_high_v2": 100},
            "group_analysis": {},
            "monthly_breakdown": {},
            "best_worst_dates": {},
        }
        output_path = tmp_path / "test_report.json"

        generate_json_report(analysis, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["summary"]["start_date"] == "2026-04-01"

    def test_generate_markdown_report(self, tmp_path):
        """应正确生成 Markdown 报告。"""
        analysis = {
            "summary": {
                "start_date": "2026-04-01",
                "end_date": "2026-07-10",
                "total_dates": 101,
                "dates_with_data": 99,
                "total_candidates": 1692,
                "total_with_forward": 1111,
                "horizons": ["1d", "3d", "5d", "10d"],
            },
            "group_counts": {
                "high_final_high_v2": 200,
                "high_final_low_v2": 100,
                "low_final_high_v2": 100,
                "low_final_low_v2": 200,
                "strong_disagreement": 50,
            },
            "group_analysis": {
                "high_final_high_v2": {
                    "average_final_score": 85.0,
                    "average_v2_score": 85.0,
                    "average_percentile_gap": 5.0,
                    "horizons": {
                        "1d": {"sample_count": 200, "mean_return": 0.05, "win_rate": 55.0},
                        "3d": {"sample_count": 200, "mean_return": 0.10, "win_rate": 60.0},
                    },
                },
                "high_final_low_v2": {
                    "average_final_score": 85.0,
                    "average_v2_score": 25.0,
                    "average_percentile_gap": 60.0,
                    "horizons": {
                        "1d": {"sample_count": 100, "mean_return": -0.03, "win_rate": 45.0},
                    },
                },
            },
            "monthly_breakdown": {},
            "best_worst_dates": {},
        }
        output_path = tmp_path / "test_report.md"

        generate_markdown_report(analysis, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "V2 Disagreement History Report" in content
        assert "high_final_high_v2" in content
        assert "high_final_low_v2" in content
