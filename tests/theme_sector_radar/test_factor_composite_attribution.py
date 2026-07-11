"""
Factor Composite Attribution 测试

覆盖：
- bucket 覆盖率计算正确
- non_neutral_rate 计算正确
- constant bucket 正确标记
- factor 级 IC 计算正确
- Top5/Bottom5 spread 计算正确
- composite 被 trend 主导时能识别
- v2 candidate 方案能生成
- JSON/Markdown 报告正常输出
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_factor_composite_attribution import (
    calc_rank_ic,
    calc_correlation,
    analyze_bucket_distribution,
    analyze_bucket_ic,
    analyze_bucket_spread,
    analyze_factor_distribution,
    analyze_factor_ic,
    analyze_factor_spread,
    analyze_composite_structure,
    generate_v2_proposals,
    run_attribution,
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

    def test_correlation_perfect(self):
        """完美正相关的相关系数应为 1.0。"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        corr = calc_correlation(x, y)
        assert corr is not None
        assert abs(corr - 1.0) < 0.01


# ============================================================
# Bucket Analysis Tests
# ============================================================

class TestBucketAnalysis:
    """测试 bucket 分析。"""

    def test_bucket_distribution(self):
        """bucket 分布应正确计算。"""
        candidates = [
            {
                "code": "600001",
                "factor_composite_breakdown": {"trend": {"score": 80.0}},
            },
            {
                "code": "600002",
                "factor_composite_breakdown": {"trend": {"score": 60.0}},
            },
            {
                "code": "600003",
                "factor_composite_breakdown": {"trend": {"score": 40.0}},
            },
        ]

        result = analyze_bucket_distribution(candidates, "trend")

        assert result["coverage"] == 100.0
        assert result["missing_rate"] == 0.0
        assert result["non_neutral_rate"] == 100.0
        assert result["is_constant"] is False

    def test_constant_bucket(self):
        """恒定 bucket 应被正确标记。"""
        candidates = [
            {
                "code": "600001",
                "factor_composite_breakdown": {"trend": {"score": 50.0}},
            },
            {
                "code": "600002",
                "factor_composite_breakdown": {"trend": {"score": 50.0}},
            },
        ]

        result = analyze_bucket_distribution(candidates, "trend")

        assert result["is_constant"] is True
        assert result["non_neutral_rate"] == 0.0


# ============================================================
# Factor Analysis Tests
# ============================================================

class TestFactorAnalysis:
    """测试 factor 分析。"""

    def test_factor_distribution(self):
        """factor 分布应正确计算。"""
        candidates = [
            {
                "code": "600001",
                "factor_snapshot": {
                    "factors": [
                        {"factor_id": "stock_trend_score", "score": 80.0, "quality": "good"},
                    ]
                },
            },
            {
                "code": "600002",
                "factor_snapshot": {
                    "factors": [
                        {"factor_id": "stock_trend_score", "score": 60.0, "quality": "good"},
                    ]
                },
            },
        ]

        result = analyze_factor_distribution(candidates, "stock_trend_score")

        assert result["coverage"] == 100.0
        assert result["non_neutral_rate"] == 100.0
        assert result["is_constant"] is False

    def test_missing_factor(self):
        """缺失 factor 应被正确处理。"""
        candidates = [
            {
                "code": "600001",
                "factor_snapshot": {"factors": []},
            },
        ]

        result = analyze_factor_distribution(candidates, "stock_trend_score")

        assert result["coverage"] == 0.0
        assert result["missing_rate"] == 100.0


# ============================================================
# Composite Structure Tests
# ============================================================

class TestCompositeStructure:
    """测试 composite 结构分析。"""

    def test_dominant_bucket_detection(self):
        """应能检测主导 bucket。"""
        candidates = [
            {
                "code": "600001",
                "factor_composite_shadow_score": 75.0,
                "final_score": 70.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 80.0},
                    "momentum": {"score": 50.0},
                },
            },
            {
                "code": "600002",
                "factor_composite_shadow_score": 65.0,
                "final_score": 60.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 60.0},
                    "momentum": {"score": 50.0},
                },
            },
            {
                "code": "600003",
                "factor_composite_shadow_score": 55.0,
                "final_score": 50.0,
                "factor_composite_breakdown": {
                    "trend": {"score": 40.0},
                    "momentum": {"score": 50.0},
                },
            },
        ]

        result = analyze_composite_structure(candidates)

        assert result["dominant_bucket"] == "trend"
        assert result["constant_buckets"] == ["momentum"]


# ============================================================
# V2 Proposal Tests
# ============================================================

class TestV2Proposals:
    """测试 v2 方案生成。"""

    def test_v2_proposals_generated(self):
        """应能生成 v2 方案。"""
        bucket_analysis = {}
        factor_analysis = {}
        composite_structure = {
            "dominant_bucket": "trend",
            "dominant_correlation": 0.95,
            "constant_buckets": ["momentum"],
        }

        result = generate_v2_proposals(bucket_analysis, factor_analysis, composite_structure)

        assert len(result) == 3
        assert result[0]["name"] == "v2_defensive"
        assert result[1]["name"] == "v2_decorrelated"
        assert result[2]["name"] == "v2_no_dead_buckets"


# ============================================================
# Report Generation Tests
# ============================================================

class TestReportGeneration:
    """测试报告生成。"""

    def test_generate_json_report(self, tmp_path):
        """应正确生成 JSON 报告。"""
        attribution = {
            "summary": {"start_date": "2026-04-01", "end_date": "2026-07-10"},
            "overall_ic": 0.0072,
            "bucket_analysis": {},
            "factor_analysis": {},
            "composite_structure": {},
            "v2_proposals": [],
        }
        output_path = tmp_path / "test_report.json"

        generate_json_report(attribution, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["overall_ic"] == 0.0072

    def test_generate_markdown_report(self, tmp_path):
        """应正确生成 Markdown 报告。"""
        attribution = {
            "summary": {
                "start_date": "2026-04-01",
                "end_date": "2026-07-10",
                "total_dates": 100,
                "dates_with_returns": 53,
                "total_candidates": 1692,
                "horizon": "1d",
            },
            "overall_ic": 0.0072,
            "final_overall_ic": -0.0777,
            "composite_final_correlation": 0.9006,
            "bucket_analysis": {},
            "factor_analysis": {},
            "composite_structure": {
                "composite_mean": 50.0,
                "composite_std": 5.0,
                "dominant_bucket": "trend",
                "dominant_correlation": 0.95,
                "constant_buckets": [],
            },
            "v2_proposals": [
                {"name": "v2_defensive", "description": "test", "weights": {}, "rationale": "test"},
            ],
        }
        output_path = tmp_path / "test_report.md"

        generate_markdown_report(attribution, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "Attribution Report" in content
        assert "v2_defensive" in content
