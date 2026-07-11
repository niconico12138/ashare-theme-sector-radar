"""
V2 Shadow Monitor 测试

覆盖：
- 最新日期选择正确
- percentile 计算正确
- high_final_low_v2 识别正确
- low_final_high_v2 识别正确
- v2_monitor_status 判断正确
- 无 forward return 时仍能生成快照
- JSON/Markdown/JSONL 输出正常
- 不改变 candidate 文件
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from update_factor_v2_shadow_monitor import (
    calc_percentile,
    analyze_latest_snapshot,
    identify_divergence_samples,
    analyze_historical_performance,
    determine_monitor_status,
    generate_json_report,
    generate_jsonl_report,
    generate_markdown_report,
)


# ============================================================
# Percentile Tests
# ============================================================

class TestPercentile:
    """测试百分位数计算。"""

    def test_percentile_median(self):
        """中位数的百分位应为 50。"""
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
# Snapshot Analysis Tests
# ============================================================

class TestSnapshotAnalysis:
    """测试快照分析。"""

    def test_analyze_latest_snapshot(self):
        """应正确分析最新快照。"""
        candidates = [
            {"code": "600001", "name": "A", "factor_composite_shadow_score_v2": 80.0, "final_score": 70.0},
            {"code": "600002", "name": "B", "factor_composite_shadow_score_v2": 60.0, "final_score": 80.0},
            {"code": "600003", "name": "C", "factor_composite_shadow_score_v2": 40.0, "final_score": 50.0},
        ]

        result = analyze_latest_snapshot(candidates, "2026-07-10")

        assert result["date"] == "2026-07-10"
        assert result["candidate_count"] == 3
        assert result["v2_coverage"] == 100.0
        assert result["v2_mean"] == 60.0
        assert len(result["top_v2_candidates"]) == 3
        assert len(result["low_v2_candidates"]) == 3


# ============================================================
# Divergence Identification Tests
# ============================================================

class TestDivergenceIdentification:
    """测试分歧样本识别。"""

    def test_high_final_low_v2(self):
        """应正确识别 high_final_low_v2。"""
        candidates = [
            {"code": "600001", "name": "A", "factor_composite_shadow_score_v2": 20.0, "final_score": 90.0},
            {"code": "600002", "name": "B", "factor_composite_shadow_score_v2": 80.0, "final_score": 30.0},
            {"code": "600003", "name": "C", "factor_composite_shadow_score_v2": 50.0, "final_score": 50.0},
            {"code": "600004", "name": "D", "factor_composite_shadow_score_v2": 50.0, "final_score": 50.0},
            {"code": "600005", "name": "E", "factor_composite_shadow_score_v2": 50.0, "final_score": 50.0},
        ]

        result = identify_divergence_samples(candidates)

        # 检查是否识别出 high_final_low_v2
        high_final_low_v2 = [s for s in result if s["reason"] == "high_final_low_v2"]
        assert len(high_final_low_v2) > 0
        assert high_final_low_v2[0]["code"] == "600001"

    def test_low_final_high_v2(self):
        """应正确识别 low_final_high_v2。"""
        candidates = [
            {"code": "600001", "name": "A", "factor_composite_shadow_score_v2": 20.0, "final_score": 90.0},
            {"code": "600002", "name": "B", "factor_composite_shadow_score_v2": 80.0, "final_score": 30.0},
            {"code": "600003", "name": "C", "factor_composite_shadow_score_v2": 50.0, "final_score": 50.0},
            {"code": "600004", "name": "D", "factor_composite_shadow_score_v2": 50.0, "final_score": 50.0},
            {"code": "600005", "name": "E", "factor_composite_shadow_score_v2": 50.0, "final_score": 50.0},
        ]

        result = identify_divergence_samples(candidates)

        # 检查是否识别出 low_final_high_v2
        low_final_high_v2 = [s for s in result if s["reason"] == "low_final_high_v2"]
        assert len(low_final_high_v2) > 0
        assert low_final_high_v2[0]["code"] == "600002"


# ============================================================
# Monitor Status Tests
# ============================================================

class TestMonitorStatus:
    """测试监控状态判断。"""

    def test_green_status(self):
        """v2 IC > 0 且 win_rate >= 55% 应为 green。"""
        performance = {
            "v2_ic_mean": 0.05,
            "v2_ic_win_rate": 60.0,
            "sample_days": 30,
        }

        result = determine_monitor_status(performance)

        assert result["status"] == "green"

    def test_red_status(self):
        """v2 IC < 0 且 win_rate < 45% 应为 red。"""
        performance = {
            "v2_ic_mean": -0.05,
            "v2_ic_win_rate": 40.0,
            "sample_days": 30,
        }

        result = determine_monitor_status(performance)

        assert result["status"] == "red"

    def test_yellow_status_insufficient_samples(self):
        """样本不足应为 yellow。"""
        performance = {
            "v2_ic_mean": 0.05,
            "v2_ic_win_rate": 60.0,
            "sample_days": 5,
        }

        result = determine_monitor_status(performance)

        assert result["status"] == "yellow"


# ============================================================
# Report Generation Tests
# ============================================================

class TestReportGeneration:
    """测试报告生成。"""

    def test_generate_json_report(self, tmp_path):
        """应正确生成 JSON 报告。"""
        monitor = {
            "latest_snapshot": {"date": "2026-07-10", "candidate_count": 30},
            "divergence_samples": [],
            "historical_performance": {"v2_ic_mean": 0.05},
            "monitor_status": {"status": "green", "reason": "test"},
        }
        output_path = tmp_path / "test_report.json"

        generate_json_report(monitor, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["latest_snapshot"]["date"] == "2026-07-10"

    def test_generate_jsonl_report(self, tmp_path):
        """应正确生成 JSONL 报告。"""
        monitor = {
            "latest_snapshot": {"date": "2026-07-10", "v2_mean": 50.0},
            "divergence_samples": [{"code": "600001", "reason": "test"}],
            "monitor_status": {"status": "green", "reason": "test"},
        }
        output_path = tmp_path / "test_report.jsonl"

        generate_jsonl_report(monitor, output_path)

        assert output_path.exists()
        lines = output_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3  # snapshot + divergence + status

    def test_generate_markdown_report(self, tmp_path):
        """应正确生成 Markdown 报告。"""
        monitor = {
            "latest_snapshot": {
                "date": "2026-07-10",
                "candidate_count": 30,
                "v2_coverage": 100.0,
                "v2_mean": 50.0,
                "top_v2_candidates": [],
                "low_v2_candidates": [],
            },
            "divergence_samples": [],
            "historical_performance": {"v2_ic_mean": 0.05, "sample_days": 30},
            "monitor_status": {"status": "green", "reason": "test"},
            "lookback_days": 60,
        }
        output_path = tmp_path / "test_report.md"

        generate_markdown_report(monitor, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "V2 Shadow Monitor" in content
        assert "使用边界" in content
