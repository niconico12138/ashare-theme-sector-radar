"""
Stock Enhanced Factors Evaluation 测试

覆盖：
- 数据加载
- 因子提取
- 统计函数
- opportunity_type 推断
- recommendation 规则
- 端到端
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_stock_enhanced_factors import (
    calc_mean,
    calc_median,
    calc_std,
    calc_rank_ic,
    calc_correlation,
    load_candidates,
    load_forward_returns,
    extract_factor_score,
    infer_opportunity_type,
    analyze_factor_for_horizon,
    generate_recommendation,
    run_evaluation,
    generate_json_report,
    generate_markdown_report,
)


# ============================================================
# Forbidden Words
# ============================================================

FORBIDDEN_WORDS = [
    "buy", "sell", "hold",
    "买入", "卖出", "持有", "推荐",
    "建仓", "加仓", "减仓",
    "止盈", "止损", "目标价",
]


# ============================================================
# Statistical Helper Tests
# ============================================================

class TestStatisticalHelpers:
    """测试统计辅助函数。"""

    def test_calc_mean(self):
        """calc_mean 应正确计算均值。"""
        assert calc_mean([1.0, 2.0, 3.0, 4.0, 5.0]) == 3.0
        assert calc_mean([]) == 0.0

    def test_calc_median(self):
        """calc_median 应正确计算中位数。"""
        assert calc_median([1.0, 2.0, 3.0, 4.0, 5.0]) == 3.0
        assert calc_median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_calc_std(self):
        """calc_std 应正确计算标准差。"""
        std = calc_std([1.0, 2.0, 3.0, 4.0, 5.0])
        assert std > 0

    def test_calc_rank_ic_positive(self):
        """正相关的 Rank IC 应为正。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.1, 0.2, 0.3, 0.4, 0.5]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert ic > 0

    def test_calc_rank_ic_negative(self):
        """负相关的 Rank IC 应为负。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.5, 0.4, 0.3, 0.2, 0.1]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert ic < 0

    def test_calc_rank_ic_insufficient(self):
        """样本不足时应返回 None。"""
        scores = [1.0, 2.0]
        returns = [0.1, 0.2]
        ic = calc_rank_ic(scores, returns)
        assert ic is None

    def test_calc_correlation(self):
        """calc_correlation 应正确计算相关性。"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        corr = calc_correlation(x, y)
        assert corr is not None
        assert abs(corr - 1.0) < 0.01


# ============================================================
# Data Loading Tests
# ============================================================

class TestDataLoading:
    """测试数据加载。"""

    def test_load_candidates_backfilled(self, tmp_path):
        """应优先读取 factor_backfilled 文件。"""
        date = "2026-07-10"
        path = tmp_path / date
        path.mkdir(parents=True)
        (path / "top30_candidates.factor_backfilled.json").write_text(
            json.dumps({"candidates": [{"code": "600001"}]}),
            encoding="utf-8",
        )

        result = load_candidates(date, tmp_path)
        assert result is not None
        assert len(result) == 1

    def test_load_candidates_fallback(self, tmp_path):
        """应 fallback 到原始文件。"""
        date = "2026-07-10"
        path = tmp_path / date
        path.mkdir(parents=True)
        (path / "top30_candidates.json").write_text(
            json.dumps({"candidates": [{"code": "600001"}]}),
            encoding="utf-8",
        )

        result = load_candidates(date, tmp_path)
        assert result is not None
        assert len(result) == 1

    def test_load_candidates_missing(self, tmp_path):
        """缺失文件应返回 None。"""
        result = load_candidates("2026-07-10", tmp_path)
        assert result is None

    def test_load_forward_returns_new_format(self, tmp_path):
        """应支持新格式 forward return。"""
        date = "2026-07-10"
        path = tmp_path / f"{date}.json"
        path.write_text(
            json.dumps({"items": [{"code": "600001", "1d": 0.05, "5d": 0.10}]}),
            encoding="utf-8",
        )

        result = load_forward_returns(date, tmp_path)
        assert result is not None
        assert result["600001"]["1d"] == 0.05

    def test_load_forward_returns_missing(self, tmp_path):
        """缺失文件应返回 None。"""
        result = load_forward_returns("2026-07-10", tmp_path)
        assert result is None


# ============================================================
# Factor Extraction Tests
# ============================================================

class TestFactorExtraction:
    """测试因子提取。"""

    def test_extract_from_direct_field(self):
        """应从 candidate 直接字段提取。"""
        candidate = {"liquidity_score": 80.0}
        score = extract_factor_score(candidate, "liquidity_score")
        assert score == 80.0

    def test_extract_from_factor_snapshot(self):
        """应从 factor_snapshot 提取。"""
        candidate = {
            "factor_snapshot": {
                "factors": [
                    {"factor_id": "liquidity_score", "score": 75.0, "quality": "good"},
                ]
            }
        }
        score = extract_factor_score(candidate, "liquidity_score")
        assert score == 75.0

    def test_extract_quality_missing(self):
        """quality == missing 应返回 None。"""
        candidate = {
            "factor_snapshot": {
                "factors": [
                    {"factor_id": "liquidity_score", "score": 75.0, "quality": "missing"},
                ]
            }
        }
        score = extract_factor_score(candidate, "liquidity_score")
        assert score is None

    def test_extract_missing_factor(self):
        """缺失因子应返回 None。"""
        candidate = {}
        score = extract_factor_score(candidate, "liquidity_score")
        assert score is None


# ============================================================
# Opportunity Type Inference Tests
# ============================================================

class TestOpportunityTypeInference:
    """测试 opportunity_type 推断。"""

    def test_v2_opportunity(self):
        """v2_opportunity -> v2_recovery。"""
        candidate = {"selection_bucket": "v2_opportunity"}
        assert infer_opportunity_type(candidate) == "v2_recovery"

    def test_core_watch(self):
        """core_watch -> trend_follow。"""
        candidate = {"selection_bucket": "core_watch"}
        assert infer_opportunity_type(candidate) == "trend_follow"

    def test_burst_top(self):
        """burst_top -> short_burst。"""
        candidate = {"source_pool": "burst_top"}
        assert infer_opportunity_type(candidate) == "short_burst"

    def test_divergence_review(self):
        """divergence_review -> divergence_review。"""
        candidate = {"selection_bucket": "divergence_review"}
        assert infer_opportunity_type(candidate) == "divergence_review"

    def test_blocked(self):
        """blocked -> blocked。"""
        candidate = {"selection_bucket": "blocked"}
        assert infer_opportunity_type(candidate) == "blocked"

    def test_unknown(self):
        """缺失 -> unknown。"""
        candidate = {}
        assert infer_opportunity_type(candidate) == "unknown"


# ============================================================
# Recommendation Tests
# ============================================================

class TestRecommendation:
    """测试 recommendation 规则。"""

    def test_insufficient_samples(self):
        """样本不足应返回 profile_only。"""
        factor_result = {
            "coverage": {"valid_factor_count": 10},
            "horizon_results": {},
            "opp_type_results": {},
        }

        rec = generate_recommendation("liquidity_score", factor_result, min_samples=30)

        assert rec["recommendation"] == "profile_only"
        assert "样本不足" in rec["reason"]

    def test_weak_ic(self):
        """弱 IC 应返回 profile_only。"""
        factor_result = {
            "coverage": {"valid_factor_count": 50},
            "horizon_results": {
                "5d": {"rank_ic": 0.02},
            },
            "opp_type_results": {},
        }

        rec = generate_recommendation("liquidity_score", factor_result, min_samples=30)

        assert rec["recommendation"] == "profile_only"

    def test_strong_ic_liquidity(self):
        """强 IC + liquidity_score 应返回 keep。"""
        factor_result = {
            "coverage": {"valid_factor_count": 50},
            "horizon_results": {
                "5d": {"rank_ic": 0.10},
            },
            "opp_type_results": {},
        }

        rec = generate_recommendation("liquidity_score", factor_result, min_samples=30)

        assert rec["recommendation"] == "keep"

    def test_strong_ic_chasing_risk_negative(self):
        """强 IC + chasing_risk_score 负相关应返回 soft_warning。"""
        factor_result = {
            "coverage": {"valid_factor_count": 50},
            "horizon_results": {
                "5d": {"rank_ic": -0.10},
            },
            "opp_type_results": {},
        }

        rec = generate_recommendation("chasing_risk_score", factor_result, min_samples=30)

        assert rec["recommendation"] == "soft_warning"

    def test_strong_ic_breakout_negative(self):
        """强 IC + breakout_distance_20 负相关应返回 trigger_candidate。"""
        factor_result = {
            "coverage": {"valid_factor_count": 50},
            "horizon_results": {
                "5d": {"rank_ic": -0.10},
            },
            "opp_type_results": {},
        }

        rec = generate_recommendation("breakout_distance_20", factor_result, min_samples=30)

        assert rec["recommendation"] == "trigger_candidate"


# ============================================================
# End-to-End Tests
# ============================================================

class TestEndToEnd:
    """端到端测试。"""

    def test_evaluate_and_generate_reports(self, tmp_path):
        """构造假数据并生成报告。"""
        # 创建测试数据
        for date in ["2026-07-02", "2026-07-03"]:
            candidate_dir = tmp_path / "candidate" / date
            candidate_dir.mkdir(parents=True)
            (candidate_dir / "top30_candidates.json").write_text(
                json.dumps({
                    "candidates": [
                        {
                            "code": "600001",
                            "name": "测试股A",
                            "final_score": 75.0,
                            "liquidity_score": 80.0,
                            "factor_snapshot": {
                                "factors": [
                                    {"factor_id": "chasing_risk_score", "score": 30.0, "quality": "good"},
                                ]
                            },
                        },
                        {
                            "code": "600002",
                            "name": "测试股B",
                            "final_score": 65.0,
                            "liquidity_score": 40.0,
                        },
                    ]
                }),
                encoding="utf-8",
            )

            forward_dir = tmp_path / "forward" / date
            forward_dir.mkdir(parents=True)
            (forward_dir / f"{date}.json").write_text(
                json.dumps({
                    "items": [
                        {"code": "600001", "1d": 0.05, "5d": 0.10},
                        {"code": "600002", "1d": -0.02, "5d": 0.03},
                    ]
                }),
                encoding="utf-8",
            )

        # 运行评估
        evaluation = run_evaluation(
            start_date="2026-07-02",
            end_date="2026-07-03",
            candidate_root=tmp_path / "candidate",
            forward_return_root=tmp_path / "forward",
            horizons=["1d", "5d"],
            min_samples=2,
        )

        # 生成报告
        json_path = tmp_path / "test_report.json"
        md_path = tmp_path / "test_report.md"

        generate_json_report(evaluation, json_path)
        generate_markdown_report(evaluation, md_path)

        assert json_path.exists()
        assert md_path.exists()

        # 检查 JSON
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert len(data["factor_results"]) == 5
        assert len(data["overall_recommendations"]) == 5

    def test_no_forbidden_words(self, tmp_path):
        """报告不应包含 forbidden words。"""
        # 创建简单测试数据
        date = "2026-07-02"
        candidate_dir = tmp_path / "candidate" / date
        candidate_dir.mkdir(parents=True)
        (candidate_dir / "top30_candidates.json").write_text(
            json.dumps({"candidates": [{"code": "600001", "final_score": 75.0}]}),
            encoding="utf-8",
        )
        forward_dir = tmp_path / "forward" / date
        forward_dir.mkdir(parents=True)
        (forward_dir / f"{date}.json").write_text(
            json.dumps({"items": [{"code": "600001", "1d": 0.05}]}),
            encoding="utf-8",
        )

        evaluation = run_evaluation(
            start_date="2026-07-02",
            end_date="2026-07-02",
            candidate_root=tmp_path / "candidate",
            forward_return_root=tmp_path / "forward",
            horizons=["1d"],
            min_samples=1,
        )

        md_path = tmp_path / "test_report.md"
        generate_markdown_report(evaluation, md_path)

        content = md_path.read_text(encoding="utf-8")

        for word in FORBIDDEN_WORDS:
            # watch_only 包含 hold 子串，需要排除
            if word == "hold":
                # 检查是否是独立的 hold 单词
                import re
                assert not re.search(r'\bhold\b', content.lower()), f"Found forbidden word: {word}"
            else:
                assert word not in content.lower(), f"Found forbidden word: {word}"
