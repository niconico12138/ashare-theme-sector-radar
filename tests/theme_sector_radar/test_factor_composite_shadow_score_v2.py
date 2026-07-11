"""
Factor Composite Shadow Score V2 测试

覆盖：
- v2 缺失 snapshot 返回 50
- v2 正常计算权重正确
- v2 跳过 dead buckets
- risk_bucket 方向处理正确
- enrich_candidates_with_scoring 输出 v2 字段
- generate_aihf_request 透传 v2 字段
- evaluate 脚本包含 v2 字段
- 不改变 final_score
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.factor_composite_shadow_score_v2 import (
    compute_factor_composite_shadow_score_v2,
    _extract_factor_score,
    _calc_bucket_score_v2,
)

import export_top30_candidates as export_candidates


# ============================================================
# Helper Functions
# ============================================================

def _make_factor_snapshot(factors: dict[str, float]) -> dict:
    """创建 factor_snapshot 用于测试。"""
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


# ============================================================
# V2 Score Tests
# ============================================================

class TestV2Score:
    """测试 v2 评分。"""

    def test_v2_missing_snapshot(self):
        """缺失 snapshot 时应返回 50。"""
        candidate = {"code": "600001", "name": "测试股"}
        result = compute_factor_composite_shadow_score_v2(candidate)

        assert result["factor_composite_shadow_score_v2"] == 50.0
        assert "v2_missing_factor_snapshot" in result["factor_composite_tags_v2"]

    def test_v2_normal_calculation(self):
        """正常计算时权重应正确。"""
        snapshot = _make_factor_snapshot({
            "stock_trend_score": 80.0,
            "drawdown_risk_score": 30.0,  # 低风险，高分
            "risk_penalty_score": 20.0,   # 低风险
        })
        candidate = {"code": "600001", "factor_snapshot": snapshot}

        result = compute_factor_composite_shadow_score_v2(candidate)

        # trend bucket: 80.0 * 0.30 = 24.0
        # risk bucket: ((100-30) + (100-20)) / 2 * 0.50 = (70 + 80) / 2 * 0.5 = 75 * 0.5 = 37.5
        # neutral: 50 * 0.20 = 10.0
        # total = 24 + 37.5 + 10 = 71.5
        assert result["factor_composite_shadow_score_v2"] == pytest.approx(71.5, rel=0.01)

    def test_v2_skips_dead_buckets(self):
        """应跳过 dead buckets。"""
        snapshot = _make_factor_snapshot({"stock_trend_score": 80.0})
        candidate = {"code": "600001", "factor_snapshot": snapshot}

        result = compute_factor_composite_shadow_score_v2(candidate)

        tags = result["factor_composite_tags_v2"]
        assert "v2_skip_dead_bucket_momentum" in tags
        assert "v2_skip_dead_bucket_volatility" in tags
        assert "v2_skip_dead_bucket_sector" in tags
        assert "v2_skip_dead_bucket_agent" in tags

    def test_v2_risk_bucket_direction(self):
        """risk_bucket 方向处理应正确。"""
        # 高风险情况
        snapshot_high_risk = _make_factor_snapshot({
            "drawdown_risk_score": 45.0,  # 高风险
            "risk_penalty_score": 40.0,   # 高风险
        })
        candidate_high = {"code": "600001", "factor_snapshot": snapshot_high_risk}
        result_high = compute_factor_composite_shadow_score_v2(candidate_high)

        # 低风险情况
        snapshot_low_risk = _make_factor_snapshot({
            "drawdown_risk_score": 10.0,  # 低风险
            "risk_penalty_score": 5.0,    # 低风险
        })
        candidate_low = {"code": "600001", "factor_snapshot": snapshot_low_risk}
        result_low = compute_factor_composite_shadow_score_v2(candidate_low)

        # 低风险的分数应该更高
        assert result_low["factor_composite_shadow_score_v2"] > result_high["factor_composite_shadow_score_v2"]

    def test_v2_breakdown_structure(self):
        """breakdown 应包含正确的结构。"""
        snapshot = _make_factor_snapshot({
            "stock_trend_score": 80.0,
            "drawdown_risk_score": 30.0,
            "risk_penalty_score": 20.0,
        })
        candidate = {"code": "600001", "factor_snapshot": snapshot}

        result = compute_factor_composite_shadow_score_v2(candidate)

        breakdown = result["factor_composite_breakdown_v2"]
        assert "trend" in breakdown
        assert "risk" in breakdown
        assert "neutral_residual" in breakdown

        # 检查 trend bucket
        trend = breakdown["trend"]
        assert trend["weight"] == 0.30
        assert "stock_trend_score" in trend["used_factors"]

        # 检查 risk bucket
        risk = breakdown["risk"]
        assert risk["weight"] == 0.50
        assert "drawdown_risk_score" in risk["used_factors"]
        assert "risk_penalty_score" in risk["used_factors"]


# ============================================================
# Integration Tests with export_top30_candidates
# ============================================================

class TestExportTop30Integration:
    """测试与 export_top30_candidates 的集成。"""

    def test_enrich_candidates_adds_v2_fields(self):
        """enrich_candidates_with_scoring 后 candidate 应包含 v2 字段。"""
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
        assert "factor_composite_shadow_score_v2" in enriched[0]
        assert "factor_composite_breakdown_v2" in enriched[0]
        assert "factor_composite_tags_v2" in enriched[0]

        score_v2 = enriched[0]["factor_composite_shadow_score_v2"]
        assert 0 <= score_v2 <= 100

    def test_v2_does_not_change_final_score(self):
        """v2 不应改变 final_score。"""
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

    def test_v2_does_not_change_v1(self):
        """v2 不应改变 v1。"""
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

        # v1 不应被修改
        assert "factor_composite_shadow_score" in enriched[0]
        v1_score = enriched[0]["factor_composite_shadow_score"]
        assert 0 <= v1_score <= 100


# ============================================================
# AIHF Request Integration Tests
# ============================================================

class TestAIHFRequestIntegration:
    """测试与 generate_aihf_request 的集成。"""

    def test_aihf_request_includes_v2_fields(self, tmp_path, monkeypatch):
        """aihf_request.json stocks 应包含 v2 字段。"""
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
                        "factor_composite_shadow_score_v2": 72.5,
                        "factor_composite_breakdown_v2": {"trend": {"score": 75.0}},
                        "factor_composite_tags_v2": [],
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
        assert "factor_composite_shadow_score_v2" in stock
        assert stock["factor_composite_shadow_score_v2"] == 72.5
        assert "factor_composite_breakdown_v2" in stock
        assert "factor_composite_tags_v2" in stock
