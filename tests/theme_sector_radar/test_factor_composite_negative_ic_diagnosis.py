"""
Factor Composite Shadow Score 负 IC 诊断测试

覆盖：
- bucket IC 计算正确
- factor IC 计算正确
- Top5/Bottom5 spread 计算正确
- signal inverted 时正确标记
- 缺失 bucket/factor 时优雅降级
- 报告 JSON/Markdown 正常生成
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_factor_composite_negative_ic import (
    calc_rank_ic,
    calc_correlation,
    diagnose_date_level,
    diagnose_bucket_level,
    diagnose_factor_level,
    diagnose_top_bottom_spread,
    diagnose_direction_issues,
    run_diagnosis,
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

    def test_rank_ic_perfect_negative(self):
        """完美负相关的 Rank IC 应为 -1.0。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.5, 0.4, 0.3, 0.2, 0.1]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert abs(ic - (-1.0)) < 0.01

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
# Bucket Diagnosis Tests
# ============================================================

class TestBucketDiagnosis:
    """测试 bucket 级别诊断。"""

    def test_bucket_ic_calculation(self):
        """bucket IC 应正确计算。"""
        candidates = [
            {
                "code": "600001",
                "factor_composite_shadow_score": 75.0,
                "final_score": 70.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 80.0},
                    "momentum": {"score": 70.0},
                },
            },
            {
                "code": "600002",
                "factor_composite_shadow_score": 65.0,
                "final_score": 60.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 60.0},
                    "momentum": {"score": 65.0},
                },
            },
            {
                "code": "600003",
                "factor_composite_shadow_score": 55.0,
                "final_score": 50.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 50.0},
                    "momentum": {"score": 55.0},
                },
            },
            {
                "code": "600004",
                "factor_composite_shadow_score": 45.0,
                "final_score": 40.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 40.0},
                    "momentum": {"score": 45.0},
                },
            },
            {
                "code": "600005",
                "factor_composite_shadow_score": 35.0,
                "final_score": 30.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 30.0},
                    "momentum": {"score": 35.0},
                },
            },
        ]
        forward_returns = {"600001": 0.05, "600002": 0.03, "600003": 0.01, "600004": -0.01, "600005": -0.03}

        result = diagnose_bucket_level(candidates, forward_returns)

        assert "trend" in result["buckets"]
        assert "momentum" in result["buckets"]
        assert result["buckets"]["trend"]["rank_ic"] is not None

    def test_missing_bucket(self):
        """缺失 bucket 应被记录。"""
        candidates = [
            {
                "code": "600001",
                "factor_composite_shadow_score": 75.0,
                "final_score": 70.0,
                "factor_composite_breakdown": {},
            },
        ]
        forward_returns = {"600001": 0.05}

        result = diagnose_bucket_level(candidates, forward_returns)

        assert len(result["missing_buckets"]) > 0


# ============================================================
# Factor Diagnosis Tests
# ============================================================

class TestFactorDiagnosis:
    """测试 factor 级别诊断。"""

    def test_factor_ic_calculation(self):
        """factor IC 应正确计算。"""
        candidates = [
            {
                "code": "600001",
                "factor_composite_shadow_score": 75.0,
                "final_score": 70.0,
                "factor_snapshot": {
                    "factors": [
                        {"factor_id": "stock_trend_score", "score": 80.0, "quality": "good"},
                        {"factor_id": "stock_short_score_v2", "score": 70.0, "quality": "good"},
                    ]
                },
            },
            {
                "code": "600002",
                "factor_composite_shadow_score": 65.0,
                "final_score": 60.0,
                "factor_snapshot": {
                    "factors": [
                        {"factor_id": "stock_trend_score", "score": 60.0, "quality": "good"},
                        {"factor_id": "stock_short_score_v2", "score": 65.0, "quality": "good"},
                    ]
                },
            },
            {
                "code": "600003",
                "factor_composite_shadow_score": 55.0,
                "final_score": 50.0,
                "factor_snapshot": {
                    "factors": [
                        {"factor_id": "stock_trend_score", "score": 50.0, "quality": "good"},
                        {"factor_id": "stock_short_score_v2", "score": 55.0, "quality": "good"},
                    ]
                },
            },
            {
                "code": "600004",
                "factor_composite_shadow_score": 45.0,
                "final_score": 40.0,
                "factor_snapshot": {
                    "factors": [
                        {"factor_id": "stock_trend_score", "score": 40.0, "quality": "good"},
                        {"factor_id": "stock_short_score_v2", "score": 45.0, "quality": "good"},
                    ]
                },
            },
            {
                "code": "600005",
                "factor_composite_shadow_score": 35.0,
                "final_score": 30.0,
                "factor_snapshot": {
                    "factors": [
                        {"factor_id": "stock_trend_score", "score": 30.0, "quality": "good"},
                        {"factor_id": "stock_short_score_v2", "score": 35.0, "quality": "good"},
                    ]
                },
            },
        ]
        forward_returns = {"600001": 0.05, "600002": 0.03, "600003": 0.01, "600004": -0.01, "600005": -0.03}

        result = diagnose_factor_level(candidates, forward_returns)

        assert "stock_trend_score" in result["factors"]
        assert "stock_short_score_v2" in result["factors"]
        assert result["factors"]["stock_trend_score"]["rank_ic"] is not None

    def test_missing_factor(self):
        """缺失 factor 应被记录。"""
        candidates = [
            {
                "code": "600001",
                "factor_composite_shadow_score": 75.0,
                "final_score": 70.0,
                "factor_snapshot": {"factors": []},
            },
        ]
        forward_returns = {"600001": 0.05}

        result = diagnose_factor_level(candidates, forward_returns)

        assert len(result["missing_factors"]) > 0


# ============================================================
# Top/Bottom Spread Tests
# ============================================================

class TestTopBottomSpread:
    """测试 Top/Bottom spread 诊断。"""

    def test_spread_calculation(self):
        """spread 应正确计算。"""
        candidates = [
            {"code": f"60000{i}", "factor_composite_shadow_score": 100 - i * 10}
            for i in range(1, 11)
        ]
        forward_returns = {f"60000{i}": i * 0.01 for i in range(1, 11)}

        result = diagnose_top_bottom_spread(candidates, forward_returns, n=3)

        assert result["top_avg_return"] is not None
        assert result["bottom_avg_return"] is not None
        assert result["spread"] is not None
        assert len(result["top_codes"]) == 3
        assert len(result["bottom_codes"]) == 3

    def test_inverted_signal(self):
        """当 Top < Bottom 时应标记 inverted_signal。"""
        # 构造反转信号：高分对应低收益
        candidates = [
            {"code": f"60000{i}", "factor_composite_shadow_score": 100 - i * 10}
            for i in range(1, 11)
        ]
        # 高分 (600001=100) 对应低收益，低分 (600010=10) 对应高收益
        forward_returns = {
            "600001": -0.10,
            "600002": -0.08,
            "600003": -0.06,
            "600004": -0.04,
            "600005": -0.02,
            "600006": 0.02,
            "600007": 0.04,
            "600008": 0.06,
            "600009": 0.08,
            "600010": 0.10,
        }

        result = diagnose_top_bottom_spread(candidates, forward_returns, n=3)

        assert result["inverted_signal"] is True
        assert result["spread"] < 0


# ============================================================
# Direction Issues Tests
# ============================================================

class TestDirectionIssues:
    """测试方向错误检查。"""

    def test_risk_bucket_reversed(self):
        """risk_bucket 负 IC 时应标记。"""
        bucket_diagnosis = {
            "buckets": {
                "risk": {"is_negative": True},
            }
        }
        factor_diagnosis = {"factors": {}}

        result = diagnose_direction_issues(bucket_diagnosis, factor_diagnosis)

        assert result["risk_bucket_reversed"] is True
        assert len(result["issues"]) > 0

    def test_contraction_reversed(self):
        """contraction_score 负 IC 时应标记。"""
        bucket_diagnosis = {"buckets": {}}
        factor_diagnosis = {
            "factors": {
                "contraction_score": {"is_negative": True},
            }
        }

        result = diagnose_direction_issues(bucket_diagnosis, factor_diagnosis)

        assert result["contraction_reversed"] is True

    def test_no_issues(self):
        """没有问题时应返回空 issues。"""
        bucket_diagnosis = {"buckets": {}}
        factor_diagnosis = {"factors": {}}

        result = diagnose_direction_issues(bucket_diagnosis, factor_diagnosis)

        assert len(result["issues"]) == 0


# ============================================================
# Report Generation Tests
# ============================================================

class TestReportGeneration:
    """测试报告生成。"""

    def test_generate_json_report(self, tmp_path):
        """应正确生成 JSON 报告。"""
        diagnosis = {
            "summary": {"start_date": "2026-07-01", "end_date": "2026-07-10"},
            "overall_ic": -0.29,
            "daily_results": [],
            "bucket_diagnosis": {"buckets": {}},
            "factor_diagnosis": {"factors": {}},
            "spread_diagnosis": {},
            "direction_issues": {"issues": []},
        }
        output_path = tmp_path / "test_report.json"

        generate_json_report(diagnosis, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["overall_ic"] == -0.29

    def test_generate_markdown_report(self, tmp_path):
        """应正确生成 Markdown 报告。"""
        diagnosis = {
            "summary": {
                "start_date": "2026-07-01",
                "end_date": "2026-07-10",
                "total_dates": 10,
                "dates_with_returns": 5,
                "total_candidates": 100,
                "horizon": "1d",
            },
            "overall_ic": -0.29,
            "daily_results": [],
            "bucket_diagnosis": {"buckets": {}},
            "factor_diagnosis": {"factors": {}},
            "spread_diagnosis": {
                "top_n": 5,
                "top_avg_return": 0.05,
                "bottom_avg_return": -0.02,
                "spread": 0.07,
                "inverted_signal": False,
            },
            "direction_issues": {"issues": ["test issue"]},
        }
        output_path = tmp_path / "test_report.md"

        generate_markdown_report(diagnosis, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "负 IC 诊断报告" in content
        assert "test issue" in content


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """集成测试。"""

    def test_run_diagnosis(self, tmp_path):
        """端到端测试。"""
        # 创建测试数据
        for date in ["2026-07-02", "2026-07-03"]:
            candidate_dir = tmp_path / "candidate" / date
            candidate_dir.mkdir(parents=True, exist_ok=True)
            (candidate_dir / "top30_candidates.factor_backfilled.json").write_text(
                json.dumps({
                    "candidates": [
                        {
                            "code": "600001",
                            "name": "测试股A",
                            "final_score": 75.0,
                            "factor_composite_shadow_score": 70.0,
                            "factor_composite_breakdown": {"trend": {"score": 80.0}},
                            "factor_snapshot": {
                                "factors": [
                                    {"factor_id": "stock_trend_score", "score": 80.0, "quality": "good"},
                                ]
                            },
                        },
                        {
                            "code": "600002",
                            "name": "测试股B",
                            "final_score": 65.0,
                            "factor_composite_shadow_score": 60.0,
                            "factor_composite_breakdown": {"trend": {"score": 60.0}},
                            "factor_snapshot": {
                                "factors": [
                                    {"factor_id": "stock_trend_score", "score": 60.0, "quality": "good"},
                                ]
                            },
                        },
                    ]
                }),
                encoding="utf-8",
            )

            forward_dir = tmp_path / "forward_returns"
            forward_dir.mkdir(parents=True, exist_ok=True)
            (forward_dir / f"{date}.json").write_text(
                json.dumps({
                    "items": [
                        {"code": "600001", "1d": 0.05},
                        {"code": "600002", "1d": -0.02},
                    ]
                }),
                encoding="utf-8",
            )

        # 运行诊断
        diagnosis = run_diagnosis(
            start_date="2026-07-02",
            end_date="2026-07-03",
            candidate_root=tmp_path / "candidate",
            forward_return_root=tmp_path / "forward_returns",
        )

        assert diagnosis["summary"]["dates_with_returns"] == 2
        assert diagnosis["overall_ic"] is not None
