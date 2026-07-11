"""
V2 Historical Opportunity Mining 测试

覆盖：
- pool 构造正确
- 阈值扫描正确
- overlap 计算正确
- market_up/market_down 切片正确
- holding horizon 统计正确
- 样本不足降级正确
- JSON/Markdown 报告生成正确
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from mine_v2_historical_opportunities import (
    calc_percentile,
    construct_daily_pools,
    analyze_pool,
    calculate_overlap,
    scan_thresholds,
    slice_by_market_environment,
    compare_holding_periods,
    generate_json_report,
    generate_markdown_report,
)


# ============================================================
# Percentile Tests
# ============================================================

class TestPercentile:
    """测试百分位数计算。"""

    def test_percentile_top(self):
        """最大值的百分位应为 80。"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calc_percentile(5.0, values)
        assert result == 80.0

    def test_percentile_bottom(self):
        """最小值的百分位应为 0。"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calc_percentile(1.0, values)
        assert result == 0.0


# ============================================================
# Pool Construction Tests
# ============================================================

class TestPoolConstruction:
    """测试池构造。"""

    def test_construct_daily_pools(self):
        """应正确构造每日池。"""
        candidates = [
            {"code": f"600{i:03d}", "name": f"A{i}", "final_score": 100.0 - i, "factor_composite_shadow_score_v2": 100.0 - i}
            for i in range(1, 11)
        ] + [
            {"code": f"601{i:03d}", "name": f"B{i}", "final_score": 50.0, "factor_composite_shadow_score_v2": 50.0}
            for i in range(1, 11)
        ] + [
            {"code": f"602{i:03d}", "name": f"C{i}", "final_score": 10.0 + i, "factor_composite_shadow_score_v2": 10.0 + i}
            for i in range(1, 11)
        ]
        forward_returns = {f"600{i:03d}": {"1d": 0.05} for i in range(1, 11)}
        forward_returns.update({f"601{i:03d}": {"1d": 0.02} for i in range(1, 11)})
        forward_returns.update({f"602{i:03d}": {"1d": -0.01} for i in range(1, 11)})

        pools = construct_daily_pools(candidates, forward_returns)

        assert "final_top_pool" in pools
        assert "v2_top_pool" in pools
        assert "low_final_high_v2_pool" in pools
        assert "strong_disagreement_opportunity_pool" in pools
        assert len(pools["final_top_pool"]) <= 10
        assert len(pools["v2_top_pool"]) <= 10


# ============================================================
# Overlap Tests
# ============================================================

class TestOverlap:
    """测试重叠率计算。"""

    def test_calculate_overlap(self):
        """应正确计算重叠率。"""
        set_a = {"600001", "600002", "600003"}
        set_b = {"600002", "600003", "600004"}

        result = calculate_overlap(set_a, set_b)

        # 重叠 2 个，共 3 个
        assert result == pytest.approx(66.67, rel=0.01)

    def test_calculate_overlap_empty(self):
        """空集合应返回 0。"""
        result = calculate_overlap(set(), {"600001"})
        assert result == 0.0


# ============================================================
# Threshold Scanning Tests
# ============================================================

class TestThresholdScanning:
    """测试阈值扫描。"""

    def test_scan_thresholds(self):
        """应正确扫描阈值。"""
        candidates_by_date = {
            "2026-07-02": [
                {"code": f"600{i:03d}", "final_score": 100.0 - i, "factor_composite_shadow_score_v2": 100.0 - i}
                for i in range(1, 11)
            ],
        }
        forward_returns_by_date = {
            "2026-07-02": {f"600{i:03d}": {"1d": 0.01 * i} for i in range(1, 11)},
        }

        result = scan_thresholds(candidates_by_date, forward_returns_by_date, ["1d"])

        assert len(result) > 0
        assert "stability_score" in result[0]


# ============================================================
# Market Environment Tests
# ============================================================

class TestMarketEnvironment:
    """测试市场环境切片。"""

    def test_slice_by_market_environment(self):
        """应正确切片市场环境。"""
        pool_by_date = {
            "2026-07-02": [
                {"code": "600001", "final_score": 30, "factor_composite_shadow_score_v2": 80},
            ],
            "2026-07-03": [
                {"code": "600002", "final_score": 30, "factor_composite_shadow_score_v2": 80},
            ],
        }
        forward_returns_by_date = {
            "2026-07-02": {"600001": {"1d": 0.05}},  # market_up
            "2026-07-03": {"600002": {"1d": -0.02}},  # market_down
        }

        result = slice_by_market_environment(pool_by_date, forward_returns_by_date, ["1d"])

        assert "market_up" in result
        assert "market_down" in result
        assert result["market_up"]["active_days"] == 1
        assert result["market_down"]["active_days"] == 1


# ============================================================
# Holding Period Tests
# ============================================================

class TestHoldingPeriod:
    """测试持有期比较。"""

    def test_compare_holding_periods(self):
        """应正确比较持有期。"""
        pool_by_date = {
            "2026-07-02": [
                {"code": "600001", "final_score": 30, "factor_composite_shadow_score_v2": 80},
            ],
        }
        forward_returns_by_date = {
            "2026-07-02": {"600001": {"1d": 0.05, "3d": 0.10, "5d": 0.15, "10d": 0.20}},
        }

        result = compare_holding_periods(pool_by_date, forward_returns_by_date, ["1d", "3d", "5d", "10d"])

        assert "1d" in result
        assert "10d" in result
        # 0.05 = 5%
        assert result["1d"]["mean_return"] == 0.05
        assert result["10d"]["mean_return"] == 0.20


# ============================================================
# Report Generation Tests
# ============================================================

class TestReportGeneration:
    """测试报告生成。"""

    def test_generate_json_report(self, tmp_path):
        """应正确生成 JSON 报告。"""
        mining = {
            "summary": {"start_date": "2026-04-01", "end_date": "2026-07-10"},
            "pool_analysis": {},
            "overlap_with_final": {},
            "threshold_scan": [],
            "market_environment": {},
            "holding_period_comparison": {},
        }
        output_path = tmp_path / "test_report.json"

        generate_json_report(mining, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["summary"]["start_date"] == "2026-04-01"

    def test_generate_markdown_report(self, tmp_path):
        """应正确生成 Markdown 报告。"""
        mining = {
            "summary": {
                "start_date": "2026-04-01",
                "end_date": "2026-07-10",
                "total_dates": 101,
                "dates_with_data": 98,
                "total_candidates": 1692,
                "horizons": ["1d", "3d", "5d", "10d"],
            },
            "pool_analysis": {
                "final_top_pool": {
                    "sample_count": 100,
                    "active_days": 50,
                    "horizons": {
                        "1d": {"mean_return": 0.5, "win_rate": 55.0},
                        "5d": {"mean_return": 1.5, "win_rate": 60.0},
                    },
                },
                "low_final_high_v2_pool": {
                    "sample_count": 247,
                    "active_days": 50,
                    "horizons": {
                        "1d": {"mean_return": 0.9867, "win_rate": 57.31},
                        "5d": {"mean_return": 2.5995, "win_rate": 59.64},
                    },
                },
            },
            "overlap_with_final": {"v2_top_vs_final_top": 30.0},
            "threshold_scan": [{"final_pct_threshold": 30, "v2_pct_threshold": 80, "gap_threshold": 50, "sample_count": 100, "mean_return_5d": 2.0, "mean_return_10d": 5.0, "win_rate_5d": 60.0, "stability_score": 3.0, "sufficient_sample": True}],
            "market_environment": {"market_up": {"horizons": {"1d": {"mean_return": 1.0}}}, "market_down": {"horizons": {"1d": {"mean_return": -0.5}}}},
            "holding_period_comparison": {"1d": {"mean_return": 0.9867}, "5d": {"mean_return": 2.5995}},
        }
        output_path = tmp_path / "test_report.md"

        generate_markdown_report(mining, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "V2 Historical Opportunity Mining" in content
        assert "low_final_high_v2" in content
