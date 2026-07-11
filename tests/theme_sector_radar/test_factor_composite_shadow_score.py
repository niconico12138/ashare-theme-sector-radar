"""
Factor Composite Shadow Score 测试

覆盖：
- factor_snapshot 缺失时返回中性 50
- 部分因子缺失时可降级
- risk_bucket 正确反向
- 所有 bucket 有效时总分符合权重
- enrich_candidates_with_scoring 后 candidate 包含 factor_composite_shadow_score
- generate_aihf_request 输出 stocks[] 包含 factor_composite_shadow_score
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.factor_composite_shadow_score import (
    compute_factor_composite_shadow_score,
    _extract_factor_score,
    _calc_bucket_score,
)
from theme_sector_radar.factors.snapshot import build_factor_snapshot

import export_top30_candidates as export_candidates


# ============================================================
# Helper Functions
# ============================================================

def _make_factor_snapshot(factors: dict[str, float]) -> dict:
    """创建 factor_snapshot 用于测试。

    Args:
        factors: dict mapping factor_id -> score (0-100)
    """
    factor_list = []
    for factor_id, score in factors.items():
        factor_list.append({
            "factor_id": factor_id,
            "raw_value": score,
            "score": score,
            "category": "test",
            "source_project": "test",
            "direction": "already_scored",
            "lookback_days": None,
            "quality": "good",
            "display_name": factor_id,
            "description": "",
            "tags": [],
        })
    return {
        "schema_version": "1.0",
        "as_of": "2026-07-10",
        "code": "600001",
        "name": "测试股",
        "factors": factor_list,
        "summary": {
            "factor_count": len(factor_list),
            "missing_count": 0,
            "missing_factors": [],
            "bars_calculated": [],
            "bars_available": False,
            "avg_score": sum(factors.values()) / len(factors) if factors else 0,
        },
    }


# ============================================================
# Extract Factor Score Tests
# ============================================================

class TestExtractFactorScore:
    """测试因子分数提取。"""

    def test_extract_existing_factor(self):
        """应正确提取存在的因子分数。"""
        snapshot = _make_factor_snapshot({"stock_trend_score": 75.0})
        score, quality = _extract_factor_score(snapshot, "stock_trend_score")
        assert score == 75.0
        assert quality == "good"

    def test_extract_missing_factor(self):
        """不存在的因子应返回 None。"""
        snapshot = _make_factor_snapshot({})
        score, quality = _extract_factor_score(snapshot, "stock_trend_score")
        assert score is None
        assert quality == "missing"

    def test_extract_quality_missing(self):
        """quality 为 missing 的因子应返回 None。"""
        snapshot = {
            "factors": [
                {
                    "factor_id": "stock_trend_score",
                    "score": 75.0,
                    "quality": "missing",
                }
            ]
        }
        score, quality = _extract_factor_score(snapshot, "stock_trend_score")
        assert score is None
        assert quality == "missing"


# ============================================================
# Bucket Score Tests
# ============================================================

class TestCalcBucketScore:
    """测试 bucket 分数计算。"""

    def test_bucket_all_factors_present(self):
        """所有因子存在时应返回等权平均。"""
        snapshot = _make_factor_snapshot({
            "ma20_slope_5": 80.0,
            "near_high_250": 60.0,
            "stock_trend_score": 70.0,
        })
        result = _calc_bucket_score(snapshot, ["ma20_slope_5", "near_high_250", "stock_trend_score"], "trend")

        assert result["score"] == 70.0  # (80 + 60 + 70) / 3
        assert len(result["used_factors"]) == 3
        assert len(result["missing_factors"]) == 0
        assert result["tag"] == ""

    def test_bucket_partial_factors_missing(self):
        """部分因子缺失时应使用有效因子的平均。"""
        snapshot = _make_factor_snapshot({
            "ma20_slope_5": 80.0,
            "stock_trend_score": 70.0,
        })
        result = _calc_bucket_score(snapshot, ["ma20_slope_5", "near_high_250", "stock_trend_score"], "trend")

        assert result["score"] == 75.0  # (80 + 70) / 2
        assert len(result["used_factors"]) == 2
        assert "near_high_250" in result["missing_factors"]

    def test_bucket_no_factors_missing(self):
        """所有因子缺失时应返回中性值。"""
        snapshot = _make_factor_snapshot({})
        result = _calc_bucket_score(snapshot, ["ma20_slope_5", "near_high_250"], "trend")

        assert result["score"] == 50.0
        assert len(result["used_factors"]) == 0
        assert result["tag"] == "trend_no_valid_factors"

    def test_bucket_reverse_risk(self):
        """反向处理时应返回 100 - score。"""
        snapshot = _make_factor_snapshot({
            "drawdown_risk_score": 30.0,  # 低风险
            "risk_penalty_score": 20.0,   # 低风险
        })
        result = _calc_bucket_score(
            snapshot,
            ["drawdown_risk_score", "risk_penalty_score"],
            "risk",
            reverse=True,
        )

        # 正常平均 = 25.0，反向 = 75.0
        assert result["score"] == 75.0


# ============================================================
# Composite Score Tests
# ============================================================

class TestComputeFactorCompositeShadowScore:
    """测试综合影子评分计算。"""

    def test_factor_snapshot_missing(self):
        """factor_snapshot 缺失时应返回中性 50。"""
        candidate = {"code": "600001", "name": "测试股"}
        result = compute_factor_composite_shadow_score(candidate)

        assert result["factor_composite_shadow_score"] == 50.0
        assert "factor_snapshot_missing" in result["factor_composite_tags"]

    def test_factor_snapshot_empty(self):
        """factor_snapshot 为空时应返回中性 50。"""
        candidate = {"code": "600001", "name": "测试股", "factor_snapshot": {}}
        result = compute_factor_composite_shadow_score(candidate)

        assert result["factor_composite_shadow_score"] == 50.0

    def test_all_buckets_valid(self):
        """所有 bucket 有效时总分应符合权重。"""
        # 创建包含所有因子的 snapshot
        snapshot = _make_factor_snapshot({
            # trend_bucket (35%)
            "ma20_slope_5": 80.0,
            "near_high_250": 70.0,
            "stock_trend_score": 75.0,
            # momentum_bucket (15%)
            "stock_short_score_v2": 65.0,
            "amount_ratio_20": 60.0,
            # volatility_bucket (15%)
            "contraction_score": 70.0,
            # sector_bucket (15%)
            "sector_trend_score": 72.0,
            "sector_burst_score": 68.0,
            # risk_bucket (10%)
            "drawdown_risk_score": 25.0,  # 低风险
            "risk_penalty_score": 20.0,   # 低风险
            # agent_bucket (10%)
            "agent_score": 70.0,
            "trend_agent_score": 72.0,
            "short_agent_score": 68.0,
        })
        candidate = {"code": "600001", "name": "测试股", "factor_snapshot": snapshot}

        result = compute_factor_composite_shadow_score(candidate)

        # 计算预期分数
        # trend: (80 + 70 + 75) / 3 = 75.0, weight 0.35
        # momentum: (65 + 60) / 2 = 62.5, weight 0.15
        # volatility: 70.0, weight 0.15
        # sector: (72 + 68) / 2 = 70.0, weight 0.15
        # risk: (100 - 25 + 100 - 20) / 2 = 77.5, weight 0.10
        # agent: (70 + 72 + 68) / 3 = 70.0, weight 0.10
        # total = 75 * 0.35 + 62.5 * 0.15 + 70 * 0.15 + 70 * 0.15 + 77.5 * 0.10 + 70 * 0.10
        #       = 26.25 + 9.375 + 10.5 + 10.5 + 7.75 + 7.0 = 71.375

        score = result["factor_composite_shadow_score"]
        assert 70.0 <= score <= 73.0  # 允许舍入误差

        # 检查 breakdown
        assert "trend" in result["factor_composite_breakdown"]
        assert "momentum" in result["factor_composite_breakdown"]
        assert "volatility" in result["factor_composite_breakdown"]
        assert "sector" in result["factor_composite_breakdown"]
        assert "risk" in result["factor_composite_breakdown"]
        assert "agent" in result["factor_composite_breakdown"]

        # 检查没有异常 tag
        assert len(result["factor_composite_tags"]) == 0

    def test_risk_bucket_reverse(self):
        """risk_bucket 应正确反向处理。"""
        # 高风险
        snapshot_high_risk = _make_factor_snapshot({
            "drawdown_risk_score": 45.0,
            "risk_penalty_score": 40.0,
        })
        candidate_high = {"code": "600001", "factor_snapshot": snapshot_high_risk}
        result_high = compute_factor_composite_shadow_score(candidate_high)

        # 低风险
        snapshot_low_risk = _make_factor_snapshot({
            "drawdown_risk_score": 10.0,
            "risk_penalty_score": 5.0,
        })
        candidate_low = {"code": "600001", "factor_snapshot": snapshot_low_risk}
        result_low = compute_factor_composite_shadow_score(candidate_low)

        # 低风险的分数应该更高
        assert result_low["factor_composite_shadow_score"] > result_high["factor_composite_shadow_score"]

    def test_breakdown_structure(self):
        """breakdown 应包含正确的结构。"""
        snapshot = _make_factor_snapshot({
            "ma20_slope_5": 80.0,
            "stock_trend_score": 75.0,
        })
        candidate = {"code": "600001", "factor_snapshot": snapshot}
        result = compute_factor_composite_shadow_score(candidate)

        breakdown = result["factor_composite_breakdown"]
        assert "trend" in breakdown
        trend = breakdown["trend"]
        assert "score" in trend
        assert "weight" in trend
        assert "weighted_score" in trend
        assert "used_factors" in trend
        assert "missing_factors" in trend
        assert trend["weight"] == 0.35


# ============================================================
# Integration Tests with export_top30_candidates
# ============================================================

class TestExportTop30Integration:
    """测试与 export_top30_candidates 的集成。"""

    def test_enrich_candidates_adds_factor_composite_shadow_score(self):
        """enrich_candidates_with_scoring 后 candidate 应包含 factor_composite_shadow_score。"""
        candidates = [
            {
                "code": "600001",
                "name": "测试股A",
                "boards": ["半导体"],
                "change_pct": 3.0,
                "amount": 50_000_000,
                "turnover_rate": 2.0,
                "sector_burst_score": 65.0,
                "sector_trend_score": 70.0,
                "final_score": 75.0,
            },
        ]
        enriched = export_candidates.enrich_candidates_with_scoring(candidates)

        assert len(enriched) == 1
        assert "factor_composite_shadow_score" in enriched[0]
        assert "factor_composite_breakdown" in enriched[0]
        assert "factor_composite_tags" in enriched[0]

        score = enriched[0]["factor_composite_shadow_score"]
        assert 0 <= score <= 100

    def test_enrich_empty_list(self):
        """空列表不应异常。"""
        result = export_candidates.enrich_candidates_with_scoring([])
        assert result == []

    def test_factor_composite_shadow_score_shadow_only(self):
        """factor_composite_shadow_score 不应影响 final_score。"""
        candidates = [
            {
                "code": "600001",
                "name": "测试股A",
                "boards": ["半导体"],
                "change_pct": 3.0,
                "amount": 50_000_000,
                "turnover_rate": 2.0,
                "sector_burst_score": 65.0,
                "sector_trend_score": 70.0,
                "final_score": 75.0,
            },
        ]
        enriched = export_candidates.enrich_candidates_with_scoring(candidates)

        # final_score 不应被修改
        assert enriched[0]["final_score"] == 75.0


class TestAIHFRequestIntegration:
    """测试与 generate_aihf_request 的集成。"""

    def test_aihf_request_includes_factor_composite_shadow_score(self, tmp_path, monkeypatch):
        """aihf_request.json stocks 应包含 factor_composite_shadow_score。"""
        top30_path = tmp_path / "top30_candidates.json"
        top30_path.write_text(
            json.dumps({
                "candidates": [
                    {
                        "code": "600001",
                        "name": "测试股",
                        "source_pool": "trend",
                        "trend_score": 70.0,
                        "burst_score": 60.0,
                        "final_score": 75.0,
                        "factor_composite_shadow_score": 72.5,
                        "factor_composite_breakdown": {"trend": {"score": 75.0}},
                        "factor_composite_tags": [],
                    },
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(export_candidates, "_build_board_context", lambda date: {"industry_top": [], "concept_top": []})

        request_path = export_candidates.generate_aihf_request(
            top30_path, "2026-07-07", agent_stock_limit=10,
        )
        request = json.loads(request_path.read_text(encoding="utf-8"))
        stock = request["stocks"][0]
        assert "factor_composite_shadow_score" in stock
        assert stock["factor_composite_shadow_score"] == 72.5
        assert "factor_composite_breakdown" in stock
        assert "factor_composite_tags" in stock

    def test_aihf_request_missing_factor_composite(self, tmp_path, monkeypatch):
        """factor_composite_shadow_score 缺失时不应报错。"""
        top30_path = tmp_path / "top30_candidates.json"
        top30_path.write_text(
            json.dumps({
                "candidates": [
                    {
                        "code": "600001",
                        "name": "测试股",
                        "source_pool": "trend",
                        "trend_score": 70.0,
                        "burst_score": 60.0,
                        "final_score": 75.0,
                    },
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(export_candidates, "_build_board_context", lambda date: {"industry_top": [], "concept_top": []})

        request_path = export_candidates.generate_aihf_request(
            top30_path, "2026-07-07", agent_stock_limit=10,
        )
        request = json.loads(request_path.read_text(encoding="utf-8"))
        stock = request["stocks"][0]
        assert "factor_composite_shadow_score" in stock
        # 默认值应为 50
        assert stock["factor_composite_shadow_score"] == 50.0
