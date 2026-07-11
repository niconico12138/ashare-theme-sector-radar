"""
Sector Support Score by Opportunity Type 测试

覆盖：
- 数据加载
- 字段提取
- 统计函数
- policy 规则
- 端到端
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_sector_support_by_opportunity_type import (
    calc_mean,
    calc_rank_ic,
    extract_sector_support_score,
    infer_opportunity_type,
    get_sector_support_state,
    analyze_sector_support_for_opportunity,
    generate_policy,
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

    def test_calc_rank_ic(self):
        """calc_rank_ic 应正确计算。"""
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        returns = [0.1, 0.2, 0.3, 0.4, 0.5]
        ic = calc_rank_ic(scores, returns)
        assert ic is not None
        assert ic > 0


# ============================================================
# Field Extraction Tests
# ============================================================

class TestFieldExtraction:
    """测试字段提取。"""

    def test_extract_from_direct_field(self):
        """应从 candidate 直接字段提取。"""
        candidate = {"sector_support_score": 70.0}
        score = extract_sector_support_score(candidate)
        assert score == 70.0

    def test_extract_from_factor_snapshot(self):
        """应从 factor_snapshot 提取。"""
        candidate = {
            "factor_snapshot": {
                "factors": [
                    {"factor_id": "sector_support_score", "score": 65.0, "quality": "good"},
                ]
            }
        }
        score = extract_sector_support_score(candidate)
        assert score == 65.0

    def test_extract_from_trend_burst(self):
        """应从 trend_score 和 burst_score 计算。"""
        candidate = {"trend_score": 70.0, "burst_score": 60.0}
        score = extract_sector_support_score(candidate)
        # 70 * 0.7 + 60 * 0.3 = 49 + 18 = 67
        assert score == 67.0

    def test_infer_opportunity_type(self):
        """应正确推断 opportunity_type。"""
        assert infer_opportunity_type({"selection_bucket": "v2_opportunity"}) == "v2_recovery"
        assert infer_opportunity_type({"selection_bucket": "core_watch"}) == "trend_follow"
        assert infer_opportunity_type({"source_pool": "burst_top"}) == "short_burst"
        assert infer_opportunity_type({"selection_bucket": "divergence_review"}) == "divergence_review"
        assert infer_opportunity_type({"selection_bucket": "blocked"}) == "blocked"
        assert infer_opportunity_type({}) == "unknown"

    def test_get_sector_support_state(self):
        """应正确判断 sector_support_state。"""
        assert get_sector_support_state(70.0) == "strong"
        assert get_sector_support_state(55.0) == "neutral"
        assert get_sector_support_state(40.0) == "weak"
        assert get_sector_support_state(None) == "unknown"


# ============================================================
# Policy Tests
# ============================================================

class TestPolicy:
    """测试 policy 规则。"""

    def test_insufficient_sample(self):
        """样本不足应返回 insufficient_sample。"""
        analysis = {"sample_count": 10}
        policy = generate_policy("trend_follow", analysis, min_samples=30)

        assert policy["policy"] == "insufficient_sample"

    def test_enable_adjustment(self):
        """IC 正且 spread 正应返回 enable_adjustment。"""
        analysis = {
            "sample_count": 50,
            "best_ic": 0.08,
            "best_horizon": "5d",
            "horizon_results": {
                "5d": {"strong_vs_weak_spread": 2.0},
            },
        }
        policy = generate_policy("trend_follow", analysis, min_samples=30)

        assert policy["policy"] == "enable_adjustment"

    def test_display_only(self):
        """弱正向效果应返回 display_only。"""
        analysis = {
            "sample_count": 50,
            "best_ic": 0.03,
            "best_horizon": "5d",
            "horizon_results": {
                "5d": {"strong_vs_weak_spread": 0.5},
            },
        }
        policy = generate_policy("trend_follow", analysis, min_samples=30)

        assert policy["policy"] == "display_only"

    def test_disable_adjustment(self):
        """明显负向应返回 disable_adjustment。"""
        analysis = {
            "sample_count": 50,
            "best_ic": -0.05,
            "best_horizon": "5d",
            "horizon_results": {
                "5d": {"strong_vs_weak_spread": -1.0},
            },
        }
        policy = generate_policy("trend_follow", analysis, min_samples=30)

        assert policy["policy"] == "disable_adjustment"

    def test_blocked_disabled(self):
        """blocked 类型应返回 disabled。"""
        analysis = {
            "sample_count": 50,
            "best_ic": 0.10,
            "best_horizon": "5d",
            "horizon_results": {
                "5d": {"strong_vs_weak_spread": 2.0},
            },
        }
        policy = generate_policy("blocked", analysis, min_samples=30)

        assert policy["policy"] == "disabled"

    def test_divergence_review_display_only(self):
        """divergence_review 类型应返回 display_only。"""
        analysis = {
            "sample_count": 50,
            "best_ic": 0.10,
            "best_horizon": "5d",
            "horizon_results": {
                "5d": {"strong_vs_weak_spread": 2.0},
            },
        }
        policy = generate_policy("divergence_review", analysis, min_samples=30)

        assert policy["policy"] == "display_only"


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
                            "sector_support_score": 70.0,
                            "selection_bucket": "core_watch",
                        },
                        {
                            "code": "600002",
                            "name": "测试股B",
                            "final_score": 65.0,
                            "sector_support_score": 40.0,
                            "selection_bucket": "core_watch",
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
        assert "sector_support_adjustment_policy_shadow" in data

    def test_no_forbidden_words(self, tmp_path):
        """报告不应包含 forbidden words。"""
        # 创建简单测试数据
        date = "2026-07-02"
        candidate_dir = tmp_path / "candidate" / date
        candidate_dir.mkdir(parents=True)
        (candidate_dir / "top30_candidates.json").write_text(
            json.dumps({"candidates": [{"code": "600001", "final_score": 75.0, "sector_support_score": 70.0}]}),
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
            if word == "hold":
                import re
                assert not re.search(r'\bhold\b', content.lower()), f"Found forbidden word: {word}"
            else:
                assert word not in content.lower(), f"Found forbidden word: {word}"
