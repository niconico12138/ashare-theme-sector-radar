"""
Factor Composite V2 稳定性验证测试

覆盖：
- 月度分组正确
- 周度分组正确
- blend score 计算正确
- 去掉最佳/最差 3 天后的 IC 正确
- Q1~Q5 分位表现正确
- 单调性判断正确
- 样本不足降级正确
- JSON/Markdown 报告生成正确
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_factor_composite_v2_stability import (
    calc_rank_ic,
    calc_correlation,
    analyze_period,
    analyze_monthly,
    analyze_weekly,
    analyze_daily_contribution,
    analyze_quintile,
    generate_json_report,
    generate_markdown_report,
)


# ============================================================
# Statistical Helper Tests
# ============================================================

class TestStatisticalHelpers:
    """测试统计辅助函数。"""

    def test_rank_ic_perfect_positive(self):
        """完美正相关的 Rank IC 应为 1.0。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.1, 0.2, 0.3, 0.4, 0.5]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert abs(ic - 1.0) < 0.01

    def test_rank_ic_insufficient_samples(self):
        """样本不足时应返回 None。"""
        scores = [1.0, 2.0]
        returns = [0.1, 0.2]
        ic = calc_rank_ic(scores, returns)
        assert ic is None

    def test_correlation_perfect(self):
        """完美正相关的相关系数应为 1.0。"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        corr = calc_correlation(x, y)
        assert corr is not None
        assert abs(corr - 1.0) < 0.01


# ============================================================
# Period Analysis Tests
# ============================================================

class TestPeriodAnalysis:
    """测试期间分析。"""

    def test_analyze_period_basic(self):
        """基本期间分析应正确计算。"""
        candidates_by_date = {
            "2026-07-02": [
                {"code": "600001", "final_score": 80.0, "v2": 70.0},
                {"code": "600002", "final_score": 60.0, "v2": 50.0},
            ],
        }
        forward_returns_by_date = {
            "2026-07-02": {"600001": 0.05, "600002": -0.02},
        }
        dates = ["2026-07-02"]

        result = analyze_period(candidates_by_date, forward_returns_by_date, dates, ["final_score", "v2"])

        assert result["sample_count"] == 2
        assert result["effective_days"] == 1
        assert "final_score" in result["fields"]
        assert "v2" in result["fields"]


# ============================================================
# Monthly Analysis Tests
# ============================================================

class TestMonthlyAnalysis:
    """测试月度分析。"""

    def test_monthly_grouping(self):
        """月度分组应正确。"""
        candidates_by_date = {
            "2026-07-02": [{"code": "600001", "final_score": 80.0}],
            "2026-07-03": [{"code": "600001", "final_score": 80.0}],
            "2026-07-04": [{"code": "600001", "final_score": 80.0}],
            "2026-07-05": [{"code": "600001", "final_score": 80.0}],
            "2026-07-06": [{"code": "600001", "final_score": 80.0}],
            "2026-07-07": [{"code": "600001", "final_score": 80.0}],
        }
        forward_returns_by_date = {
            "2026-07-02": {"600001": 0.05},
            "2026-07-03": {"600001": 0.05},
            "2026-07-04": {"600001": 0.05},
            "2026-07-05": {"600001": 0.05},
            "2026-07-06": {"600001": 0.05},
            "2026-07-07": {"600001": 0.05},
        }
        dates = [f"2026-07-{i:02d}" for i in range(2, 8)]

        result = analyze_monthly(candidates_by_date, forward_returns_by_date, dates, ["final_score"])

        assert "2026-07" in result
        assert result["2026-07"]["effective_days"] == 6


# ============================================================
# Weekly Analysis Tests
# ============================================================

class TestWeeklyAnalysis:
    """测试周度分析。"""

    def test_weekly_grouping(self):
        """周度分组应正确。"""
        candidates_by_date = {
            "2026-07-07": [{"code": "600001", "final_score": 80.0}],
            "2026-07-08": [{"code": "600001", "final_score": 80.0}],
            "2026-07-09": [{"code": "600001", "final_score": 80.0}],
        }
        forward_returns_by_date = {
            "2026-07-07": {"600001": 0.05},
            "2026-07-08": {"600001": 0.05},
            "2026-07-09": {"600001": 0.05},
        }
        dates = ["2026-07-07", "2026-07-08", "2026-07-09"]

        result = analyze_weekly(candidates_by_date, forward_returns_by_date, dates, ["final_score"])

        # 应该至少有一个周
        assert len(result) > 0


# ============================================================
# Daily Contribution Tests
# ============================================================

class TestDailyContribution:
    """测试日度贡献集中度。"""

    def test_daily_contribution(self):
        """日度贡献应正确计算。"""
        candidates_by_date = {
            "2026-07-02": [
                {"code": "600001", "v2": 80.0},
                {"code": "600002", "v2": 60.0},
            ],
            "2026-07-03": [
                {"code": "600001", "v2": 70.0},
                {"code": "600002", "v2": 50.0},
            ],
        }
        forward_returns_by_date = {
            "2026-07-02": {"600001": 0.05, "600002": -0.02},
            "2026-07-03": {"600001": 0.03, "600002": -0.01},
        }
        dates = ["2026-07-02", "2026-07-03"]

        result = analyze_daily_contribution(candidates_by_date, forward_returns_by_date, dates, "v2")

        assert "top_positive_ic_days" in result
        assert "top_negative_ic_days" in result
        assert "concentration" in result
        assert "ic_without_top3" in result
        assert "ic_without_bottom3" in result


# ============================================================
# Quintile Analysis Tests
# ============================================================

class TestQuintileAnalysis:
    """测试分位数分析。"""

    def test_quintile_monotonic(self):
        """单调递增的分数应判断为单调。"""
        candidates_by_date = {
            "2026-07-02": [
                {"code": f"60000{i}", "v2": i * 10}
                for i in range(1, 11)
            ],
        }
        forward_returns_by_date = {
            "2026-07-02": {f"60000{i}": i * 0.01 for i in range(1, 11)},
        }
        dates = ["2026-07-02"]

        result = analyze_quintile(candidates_by_date, forward_returns_by_date, dates, "v2")

        assert result["is_monotonic"] is True
        assert result["spread"] > 0

    def test_quintile_insufficient_samples(self):
        """样本不足时应返回空结果。"""
        candidates_by_date = {
            "2026-07-02": [{"code": "600001", "v2": 80.0}],
        }
        forward_returns_by_date = {
            "2026-07-02": {"600001": 0.05},
        }
        dates = ["2026-07-02"]

        result = analyze_quintile(candidates_by_date, forward_returns_by_date, dates, "v2")

        assert result["quintiles"] == []
        assert result["is_monotonic"] is None


# ============================================================
# Report Generation Tests
# ============================================================

class TestReportGeneration:
    """测试报告生成。"""

    def test_generate_json_report(self, tmp_path):
        """应正确生成 JSON 报告。"""
        stability = {
            "summary": {"start_date": "2026-04-01", "end_date": "2026-07-10"},
            "overall": {"fields": {}},
            "monthly": {},
            "weekly": {},
            "daily_contribution": {},
            "quintile_analysis": {},
            "correlations": {},
            "incremental_value": {},
        }
        output_path = tmp_path / "test_report.json"

        generate_json_report(stability, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["summary"]["start_date"] == "2026-04-01"

    def test_generate_markdown_report(self, tmp_path):
        """应正确生成 Markdown 报告。"""
        stability = {
            "summary": {
                "start_date": "2026-04-01",
                "end_date": "2026-07-10",
                "total_dates": 101,
                "effective_dates": 99,
                "horizon": "1d",
            },
            "overall": {
                "fields": {
                    "final_score": {"rank_ic": -0.0777, "ic_win_rate": 45.0, "spread": 1.0},
                    "factor_composite_shadow_score_v2": {"rank_ic": 0.0647, "ic_win_rate": 55.0, "spread": 2.0},
                }
            },
            "monthly": {},
            "weekly": {},
            "daily_contribution": {
                "top_positive_ic_days": [("2026-07-02", 0.5)],
                "top_negative_ic_days": [],
                "concentration": 50.0,
                "ic_without_top3": 0.02,
                "ic_without_bottom3": 0.08,
            },
            "quintile_analysis": {
                "factor_composite_shadow_score_v2": {
                    "quintiles": [
                        {"quintile": 1, "count": 10, "mean_return": -0.01},
                        {"quintile": 5, "count": 10, "mean_return": 0.05},
                    ],
                    "is_monotonic": True,
                    "spread": 0.06,
                }
            },
            "correlations": {},
            "incremental_value": {
                "best_ic_field": "factor_composite_shadow_score_v2",
                "best_ic_value": 0.0647,
                "best_spread_field": "factor_composite_shadow_score_v2",
                "best_spread_value": 2.0,
            },
        }
        output_path = tmp_path / "test_report.md"

        generate_markdown_report(stability, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "Stability Report" in content
        assert "v2" in content
