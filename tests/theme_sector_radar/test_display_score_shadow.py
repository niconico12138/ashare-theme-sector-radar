"""
Display Score Shadow 测试

覆盖：
- 正常计算 90/10、80/20、70/30
- 缺 v2 使用 50
- 缺 final_score 返回 None
- enrich_candidates_with_scoring 添加字段
- generate_aihf_request 透传字段
- evaluate_display_score_shadow 能生成报告
- 不改变 final_score
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.display_score_shadow import (
    compute_display_score_shadow,
    _safe_float,
)

import export_top30_candidates as export_candidates


# ============================================================
# Basic Calculation Tests
# ============================================================

class TestBasicCalculation:
    """测试基本计算。"""

    def test_normal_calculation(self):
        """正常计算应正确。"""
        candidate = {
            "code": "600001",
            "final_score": 80.0,
            "factor_composite_shadow_score_v2": 60.0,
        }

        result = compute_display_score_shadow(candidate)

        # 90/10: 80 * 0.90 + 60 * 0.10 = 72 + 6 = 78
        assert result["display_score_shadow_90_10"] == pytest.approx(78.0, rel=0.01)
        # 80/20: 80 * 0.80 + 60 * 0.20 = 64 + 12 = 76
        assert result["display_score_shadow_80_20"] == pytest.approx(76.0, rel=0.01)
        # 70/30: 80 * 0.70 + 60 * 0.30 = 56 + 18 = 74
        assert result["display_score_shadow_70_30"] == pytest.approx(74.0, rel=0.01)

    def test_missing_v2_uses_neutral(self):
        """缺 v2 时应使用 50 中性值。"""
        candidate = {
            "code": "600001",
            "final_score": 80.0,
        }

        result = compute_display_score_shadow(candidate)

        # 90/10: 80 * 0.90 + 50 * 0.10 = 72 + 5 = 77
        assert result["display_score_shadow_90_10"] == pytest.approx(77.0, rel=0.01)
        assert "missing_v2_neutral" in result["display_score_shadow_tags"]

    def test_missing_final_score_returns_none(self):
        """缺 final_score 时应返回 None。"""
        candidate = {
            "code": "600001",
            "factor_composite_shadow_score_v2": 60.0,
        }

        result = compute_display_score_shadow(candidate)

        assert result["display_score_shadow_90_10"] is None
        assert result["display_score_shadow_80_20"] is None
        assert result["display_score_shadow_70_30"] is None
        assert "missing_final_score" in result["display_score_shadow_tags"]

    def test_score_clamped_to_0_100(self):
        """分数应限制在 0-100。"""
        candidate = {
            "code": "600001",
            "final_score": 150.0,  # 超过 100
            "factor_composite_shadow_score_v2": 150.0,
        }

        result = compute_display_score_shadow(candidate)

        assert result["display_score_shadow_90_10"] <= 100.0
        assert result["display_score_shadow_80_20"] <= 100.0
        assert result["display_score_shadow_70_30"] <= 100.0

    def test_breakdown_structure(self):
        """breakdown 应包含正确结构。"""
        candidate = {
            "code": "600001",
            "final_score": 80.0,
            "factor_composite_shadow_score_v2": 60.0,
        }

        result = compute_display_score_shadow(candidate)

        breakdown = result["display_score_shadow_breakdown"]
        assert "final_score" in breakdown
        assert "v2_score" in breakdown
        assert "weights_90_10" in breakdown
        assert "weights_80_20" in breakdown
        assert "weights_70_30" in breakdown


# ============================================================
# Integration Tests with export_top30_candidates
# ============================================================

class TestExportTop30Integration:
    """测试与 export_top30_candidates 的集成。"""

    def test_enrich_candidates_adds_display_score_shadow(self):
        """enrich_candidates_with_scoring 后应包含 display_score_shadow 字段。"""
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
        assert "display_score_shadow_90_10" in enriched[0]
        assert "display_score_shadow_80_20" in enriched[0]
        assert "display_score_shadow_70_30" in enriched[0]
        assert "display_score_shadow_breakdown" in enriched[0]
        assert "display_score_shadow_tags" in enriched[0]

    def test_display_score_shadow_does_not_change_final_score(self):
        """display_score_shadow 不应改变 final_score。"""
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


# ============================================================
# AIHF Request Integration Tests
# ============================================================

class TestAIHFRequestIntegration:
    """测试与 generate_aihf_request 的集成。"""

    def test_aihf_request_includes_display_score_shadow(self, tmp_path, monkeypatch):
        """aihf_request.json stocks 应包含 display_score_shadow 字段。"""
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
                        "display_score_shadow_90_10": 74.5,
                        "display_score_shadow_80_20": 74.0,
                        "display_score_shadow_70_30": 73.5,
                        "display_score_shadow_breakdown": {},
                        "display_score_shadow_tags": [],
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
        assert "display_score_shadow_90_10" in stock
        assert stock["display_score_shadow_90_10"] == 74.5
        assert "display_score_shadow_80_20" in stock
        assert "display_score_shadow_70_30" in stock
        assert "display_score_shadow_breakdown" in stock
        assert "display_score_shadow_tags" in stock
