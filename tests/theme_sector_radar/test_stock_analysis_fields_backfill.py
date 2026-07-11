"""
Stock Analysis Fields Backfill 测试

覆盖：
- 数据加载
- 字段回填
- 分类回填
- summary
- 不包含 forbidden words
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from backfill_stock_analysis_fields import (
    infer_source_pool,
    backfill_stock_analysis_fields,
    backfill_date,
    generate_report,
    load_top30_candidates,
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
# Source Pool Inference Tests
# ============================================================

class TestSourcePoolInference:
    """测试 source_pool 推断。"""

    def test_infer_from_direct_field(self):
        """应从 candidate 直接字段读取。"""
        candidate = {"source_pool": "trend_top"}
        assert infer_source_pool(candidate) == "trend_top"

    def test_infer_from_signal_type(self):
        """应从 signal_type 推断。"""
        assert infer_source_pool({"signal_type": "low_final_high_v2"}) == "v2_potential"
        assert infer_source_pool({"signal_type": "high_final_low_v2"}) == "divergence_review"

    def test_infer_from_selection_bucket(self):
        """应从 selection_bucket 推断。"""
        assert infer_source_pool({"selection_bucket": "v2_opportunity"}) == "v2_potential"
        assert infer_source_pool({"selection_bucket": "divergence_review"}) == "divergence_review"
        assert infer_source_pool({"selection_bucket": "blocked"}) == "unknown_source"

    def test_infer_from_features(self):
        """应从字段特征推断。"""
        assert infer_source_pool({"stock_short_score_v2": 70.0}) == "burst_top"
        assert infer_source_pool({"final_score": 60.0}) == "trend_top"
        assert infer_source_pool({}) == "unknown_source"


# ============================================================
# Backfill Tests
# ============================================================

class TestBackfill:
    """测试回填逻辑。"""

    def test_backfill_preserves_order(self):
        """回填应保持 candidate 顺序。"""
        data = {
            "candidates": [
                {"code": "600001", "name": "A", "final_score": 75.0},
                {"code": "600002", "name": "B", "final_score": 65.0},
                {"code": "600003", "name": "C", "final_score": 55.0},
            ]
        }

        result = backfill_stock_analysis_fields(data)

        codes = [c["code"] for c in result["candidates"]]
        assert codes == ["600001", "600002", "600003"]

    def test_backfill_preserves_original_fields(self):
        """回填应保留原字段。"""
        data = {
            "candidates": [
                {"code": "600001", "name": "A", "final_score": 75.0, "custom_field": "value"},
            ]
        }

        result = backfill_stock_analysis_fields(data)

        assert result["candidates"][0]["custom_field"] == "value"
        assert result["candidates"][0]["final_score"] == 75.0

    def test_backfill_sets_action_state(self):
        """回填应设置 action_state 为 watch_only。"""
        data = {
            "candidates": [
                {"code": "600001", "name": "A", "final_score": 75.0},
            ]
        }

        result = backfill_stock_analysis_fields(data)

        assert result["candidates"][0]["action_state"] == "watch_only"

    def test_backfill_adds_opportunity_type(self):
        """回填应添加 opportunity_type。"""
        data = {
            "candidates": [
                {"code": "600001", "name": "A", "final_score": 75.0, "selection_bucket": "core_watch"},
            ]
        }

        result = backfill_stock_analysis_fields(data)

        assert "opportunity_type" in result["candidates"][0]
        assert result["candidates"][0]["opportunity_type"] == "trend_follow"

    def test_backfill_adds_stock_profile(self):
        """回填应添加 stock_profile。"""
        data = {
            "candidates": [
                {"code": "600001", "name": "A", "final_score": 75.0},
            ]
        }

        result = backfill_stock_analysis_fields(data)

        assert "stock_profile" in result["candidates"][0]
        assert "sector_support_state" in result["candidates"][0]


    def test_backfill_adds_sector_peer_rank_and_v2_shadow_score(self):
        data = {
            "candidates": [
                {"code": "600001", "name": "A", "sector_name": "AI", "final_score": 75.0, "stock_trend_score": 80.0},
                {"code": "600002", "name": "B", "sector_name": "AI", "final_score": 70.0, "stock_trend_score": 55.0},
            ]
        }

        result = backfill_stock_analysis_fields(data)
        by_code = {candidate["code"]: candidate for candidate in result["candidates"]}

        assert by_code["600001"]["sector_peer_rank_score"] > by_code["600002"]["sector_peer_rank_score"]
        assert "optimized_watch_score_v2_shadow" in by_code["600001"]
        assert "risk_adjusted_watch_score_shadow" in by_code["600001"]
        assert by_code["600001"]["risk_gate_decision"]["policy"] == "watch_ranking_shadow_only"
        assert by_code["600001"]["factor_value_overlay_v2_shadow"]["policy"] == "shadow_watch_ranking_only"
        assert by_code["600001"]["watch_ranking_decision"]["current_sort_model"] == "risk_adjusted_watch_score_shadow"

    def test_backfill_persists_short_burst_emotion_overlay(self):
        data = {
            "candidates": [
                {
                    "code": "600003",
                    "name": "C",
                    "source_pool": "burst_top",
                    "final_score": 66.0,
                    "v2_score": 58.0,
                    "short_burst_emotion_score_v2": 61.0,
                    "volume_burst_quality_score": 65.0,
                    "limit_attention_score": 42.0,
                    "next_day_cashout_risk_score": 35.0,
                },
            ]
        }

        result = backfill_stock_analysis_fields(data)
        candidate = result["candidates"][0]

        assert candidate["opportunity_type"] == "short_burst"
        assert candidate["short_burst_emotion_overlay_shadow"]["policy"] == "shadow_observation_only"
        assert candidate["watch_ranking_decision"]["short_burst_shadow_model"] == "short_burst_emotion_score_v2"

    def test_backfill_persists_intraday_shadow_overlay(self):
        data = {
            "candidates": [
                {
                    "code": "600004",
                    "name": "D",
                    "source_pool": "burst_top",
                    "final_score": 66.0,
                    "v2_score": 58.0,
                    "prev_close": 100.0,
                    "sector_intraday_breadth_score": 72.0,
                    "intraday_bars": [
                        {"time": "09:30", "price": 100.0, "amount": 8_000_000.0},
                        {"time": "10:30", "price": 101.0, "amount": 10_000_000.0},
                        {"time": "13:30", "price": 102.0, "amount": 12_000_000.0},
                        {"time": "14:30", "price": 103.0, "amount": 16_000_000.0},
                        {"time": "14:55", "price": 104.0, "amount": 20_000_000.0},
                    ],
                },
            ]
        }

        result = backfill_stock_analysis_fields(data)
        candidate = result["candidates"][0]

        assert candidate["intraday_factor_snapshot"]["schema_version"] == "intraday_factor_snapshot.v1"
        assert candidate["short_burst_intraday_emotion_overlay_shadow"]["policy"] == "shadow_observation_only"
        assert candidate["watch_ranking_decision"]["intraday_shadow_model"] == "short_burst_intraday_emotion_score_shadow"


# ============================================================
# Report Tests
# ============================================================

class TestReport:
    """测试报告生成。"""

    def test_generate_report(self):
        """应正确生成报告。"""
        daily_results = [
            {"date": "2026-07-02", "status": "processed", "candidate_count": 20,
             "opportunity_types": {"trend_follow": 15, "short_burst": 5},
             "selection_buckets": {"core_watch": 20},
             "source_pools": {"trend_top": 15, "burst_top": 5},
             "sector_support_states": {"strong": 10, "weak": 10},
             "missing_counts": {"final_score": 0, "v2_score": 5, "factor_snapshot": 0, "sector_support_score": 0}},
            {"date": "2026-07-03", "status": "processed", "candidate_count": 18,
             "opportunity_types": {"trend_follow": 12, "short_burst": 6},
             "selection_buckets": {"core_watch": 18},
             "source_pools": {"trend_top": 12, "burst_top": 6},
             "sector_support_states": {"strong": 8, "weak": 10},
             "missing_counts": {"final_score": 0, "v2_score": 3, "factor_snapshot": 0, "sector_support_score": 0}},
        ]

        report = generate_report("2026-07-02", "2026-07-03", daily_results)

        assert report["processed_days"] == 2
        assert report["processed_candidates"] == 38
        assert report["opportunity_type_counts"]["trend_follow"] == 27
        assert report["opportunity_type_counts"]["short_burst"] == 11


# ============================================================
# End-to-End Tests
# ============================================================

class TestEndToEnd:
    """端到端测试。"""

    def test_backfill_and_report(self, tmp_path):
        """回填并生成报告。"""
        # 创建测试数据
        for date in ["2026-07-02", "2026-07-03"]:
            candidate_dir = tmp_path / "candidate" / date
            candidate_dir.mkdir(parents=True)
            (candidate_dir / "top30_candidates.json").write_text(
                json.dumps({
                    "candidates": [
                        {"code": "600001", "name": "测试股A", "final_score": 75.0, "selection_bucket": "core_watch"},
                        {"code": "600002", "name": "测试股B", "final_score": 65.0, "selection_bucket": "core_watch"},
                    ]
                }),
                encoding="utf-8",
            )

        # 运行回填
        from backfill_stock_analysis_fields import backfill_date

        for date in ["2026-07-02", "2026-07-03"]:
            result = backfill_date(
                date=date,
                candidate_root=tmp_path / "candidate",
                output_root=tmp_path / "output",
                dry_run=False,
                force=False,
                write_copy=True,
            )
            assert result["status"] == "processed"

        # 验证输出
        for date in ["2026-07-02", "2026-07-03"]:
            output_path = tmp_path / "output" / date / "top30_candidates.analysis_backfilled.json"
            assert output_path.exists()
            data = json.loads(output_path.read_text(encoding="utf-8"))
            assert len(data["candidates"]) == 2
            for c in data["candidates"]:
                assert "opportunity_type" in c
                assert "stock_profile" in c
                assert c["action_state"] == "watch_only"

    def test_no_forbidden_words(self, tmp_path):
        """报告不应包含 forbidden words。"""
        daily_results = [
            {"date": "2026-07-02", "status": "processed", "candidate_count": 20,
             "opportunity_types": {"trend_follow": 20},
             "selection_buckets": {"core_watch": 20},
             "source_pools": {"trend_top": 20},
             "sector_support_states": {"strong": 20},
             "missing_counts": {"final_score": 0, "v2_score": 0, "factor_snapshot": 0, "sector_support_score": 0}},
        ]

        report = generate_report("2026-07-02", "2026-07-02", daily_results)

        report_str = json.dumps(report, ensure_ascii=False)

        for word in FORBIDDEN_WORDS:
            if word == "hold":
                import re
                assert not re.search(r'\bhold\b', report_str.lower()), f"Found forbidden word: {word}"
            else:
                assert word not in report_str.lower(), f"Found forbidden word: {word}"
