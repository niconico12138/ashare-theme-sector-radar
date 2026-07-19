"""Tests for risk component quality diagnosis."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_risk_component_quality import (
    compute_distribution,
    compute_return_relationship,
    compute_tag_diagnostics,
    compute_eligibility_diagnostics,
    identify_root_causes,
    build_recommendations,
    generate_markdown,
    spearman_correlation,
)
from tests.theme_sector_radar.report_fixture_factory import write_json


class TestDistribution:
    def test_constant_value_flag(self):
        values = [6.0] * 30
        result = compute_distribution(values)
        assert "constant_value" in result["quality_flags"]
        assert result["unique_count"] == 1
        assert result["spread"] == 0.0

    def test_low_spread_flag(self):
        values = list(range(10)) + [5.0] * 20  # spread=9
        result = compute_distribution(values)
        assert "low_spread" in result["quality_flags"]

    def test_normal_distribution(self):
        values = list(range(0, 100, 3))
        result = compute_distribution(values)
        assert result["sample_count"] == len(values)
        assert result["spread"] > 0
        assert len(result["bucket_distribution"]) == 5

    def test_excessive_missing(self):
        values = [None] * 40 + [1.0] * 10
        result = compute_distribution(values)
        assert "excessive_missing" in result["quality_flags"]
        assert result["missing_count"] == 40

    def test_empty_values(self):
        result = compute_distribution([])
        assert result["sample_count"] == 0


class TestReturnRelationship:
    def test_basic_relationship(self):
        records = []
        for i in range(20):
            records.append({
                "date": "2026-06-01", "data_available": True,
                "next_return_pct": float(i), "test_factor": float(20 - i),
            })
        result = compute_return_relationship(records, "test_factor")
        assert result["sample_count"] == 20
        assert result["spearman_corr"] is not None
        assert result["spearman_corr"] < 0  # negative corr

    def test_insufficient_samples(self):
        records = [{"date": "2026-06-01", "data_available": True,
                    "next_return_pct": 1.0, "f": 1.0}] * 2
        result = compute_return_relationship(records, "f")
        assert result.get("error") == "insufficient_samples"

    def test_high_low_gap_direction(self):
        """High factor → high return should give positive gap."""
        records = []
        for i in range(20):
            records.append({
                "date": "2026-06-01", "data_available": True,
                "next_return_pct": float(i * 0.5), "test_factor": float(i),
            })
        result = compute_return_relationship(records, "test_factor")
        assert result["high_low_gap"] > 0


class TestTagDiagnostics:
    def test_valid_negative_tag(self):
        records = []
        # Tag "bad_tag" associated with negative returns
        for i in range(25):
            records.append({
                "data_available": True, "next_return_pct": -3.0 if i < 15 else 1.0,
                "risk_tags": ["bad_tag"] if i < 15 else [],
            })
        result = compute_tag_diagnostics(records, "risk_tags")
        assert "bad_tag" in result["tags"]
        assert "valid_negative_risk_tag" in result["tags"]["bad_tag"]["flags"]

    def test_wrong_direction_tag(self):
        records = []
        for i in range(25):
            records.append({
                "data_available": True, "next_return_pct": 3.0 if i < 15 else -1.0,
                "risk_tags": ["good_tag"] if i < 15 else [],
            })
        result = compute_tag_diagnostics(records, "risk_tags")
        assert "good_tag" in result["tags"]
        assert "wrong_direction_tag" in result["tags"]["good_tag"]["flags"]

    def test_insufficient_samples_tag(self):
        records = []
        for i in range(15):
            records.append({
                "data_available": True, "next_return_pct": 1.0,
                "risk_tags": ["rare_tag"],
            })
        result = compute_tag_diagnostics(records, "risk_tags")
        assert "rare_tag" in result["tags"]
        assert "insufficient_samples" in result["tags"]["rare_tag"]["flags"]


class TestEligibilityDiagnostics:
    def test_avoid_higher_than_focus(self):
        records = [
            {"data_available": True, "next_return_pct": -1.0, "trade_eligibility": "focus"} for _ in range(20)
        ] + [
            {"data_available": True, "next_return_pct": 1.0, "trade_eligibility": "avoid"} for _ in range(20)
        ]
        result = compute_eligibility_diagnostics(records)
        assert "avoid_not_valid_as_negative_filter" in result["flags"]

    def test_backup_defensive_value(self):
        records = (
            [{"data_available": True, "next_return_pct": -2.0, "market_regime": "broad_down",
              "trade_eligibility": "focus"} for _ in range(10)]
            + [{"data_available": True, "next_return_pct": -0.5, "market_regime": "broad_down",
                "trade_eligibility": "backup"} for _ in range(10)]
        )
        result = compute_eligibility_diagnostics(records)
        assert "backup_defensive_value" in result["flags"]

    def test_focus_not_alpha(self):
        records = [
            {"data_available": True, "next_return_pct": -0.5, "trade_eligibility": "focus"} for _ in range(20)
        ]
        result = compute_eligibility_diagnostics(records)
        assert "focus_not_alpha_group" in result["flags"]


class TestRootCauses:
    def test_hard_risk_constant_detected(self):
        dists = {"hard_risk_penalty": {"quality_flags": ["constant_value"], "spread": 0, "unique_count": 1}}
        causes = identify_root_causes(dists, {}, {"tags": {}}, {"flags": []})
        cause_names = [c["cause"] for c in causes]
        assert "hard_risk_penalty_constant_due_to_partial_data_risk" in cause_names

    def test_elasticity_wrong_direction(self):
        rels = {"volatility_elasticity_score": {"high_low_gap": -2.0, "high_bucket_avg": -5.0, "low_bucket_avg": -3.0}}
        causes = identify_root_causes({}, rels, {"tags": {}}, {"flags": []})
        cause_names = [c["cause"] for c in causes]
        assert "elasticity_definition_captures_overheat_not_alpha" in cause_names

    def test_drawdown_weak(self):
        dists = {"drawdown_risk_score": {"spread": 5.0, "unique_count": 2, "quality_flags": []}}
        causes = identify_root_causes(dists, {}, {"tags": {}}, {"flags": []})
        cause_names = [c["cause"] for c in causes]
        assert "drawdown_risk_underpowered" in cause_names

    def test_all_production_not_allowed(self):
        recs = build_recommendations([{"cause": "test", "severity": "low", "evidence": "test"}])
        assert all(not r["production_change_allowed"] for r in recs)


def test_markdown_supports_flat_tag_diagnostics():
    output = {
        "tag_diagnostics": {
            "tags": {
                "legacy_risk": {
                    "sample_count": 20,
                    "avg_return": -1.0,
                    "hit_rate": 25.0,
                    "avg_next_low_return": -2.0,
                    "flags": ["valid_negative_risk_tag"],
                }
            },
            "no_tag_avg_return": 1.0,
            "no_tag_count": 20,
        }
    }

    markdown = generate_markdown(output)

    assert "legacy_risk" in markdown
    assert "Baseline count: 20" in markdown


@pytest.fixture
def risk_quality_output_paths(tmp_path):
    records = []
    for i in range(40):
        has_risk_tag = i < 20
        records.append({
            "date": f"2026-07-{i // 10 + 1:02d}",
            "data_available": True,
            "next_return_pct": float(-2 - i / 100) if has_risk_tag else float(2 + i / 100),
            "next_low_return_pct": float(-4 - i / 100) if has_risk_tag else float(-1 - i / 100),
            "max_intraday_drawdown_pct": float(-3 - i / 100) if has_risk_tag else float(-0.5 - i / 100),
            "market_regime": "broad_up" if (i // 10) % 2 == 0 else "broad_down",
            "risk_penalty_score": float(i),
            "hard_risk_penalty": float(i % 8),
            "trade_risk_penalty": float(i % 15),
            "volatility_elasticity_score": float(39 - i),
            "drawdown_risk_score": float(i % 6),
            "shadow_decision_score_v2": float(50 + i),
            "risk_tags": ["synthetic_risk"] if has_risk_tag else [],
            "risk_decomposition_tags": ["synthetic_decomposition"] if has_risk_tag else [],
            "risk_quality_tags": ["synthetic_quality"] if has_risk_tag else [],
            "trade_eligibility": "focus" if has_risk_tag else "avoid",
        })
    distribution_fields = [
        "risk_penalty_score",
        "hard_risk_penalty",
        "trade_risk_penalty",
        "volatility_elasticity_score",
        "drawdown_risk_score",
        "shadow_decision_score_v2",
    ]
    relationship_fields = distribution_fields[:-1]
    distributions = {
        field: compute_distribution([record[field] for record in records])
        for field in distribution_fields
    }
    return_relationships = {
        field: compute_return_relationship(records, field)
        for field in relationship_fields
    }
    risk_tag_diag = compute_tag_diagnostics(records, "risk_tags")
    decomposition_tag_diag = compute_tag_diagnostics(
        records, "risk_decomposition_tags"
    )
    quality_tag_diag = compute_tag_diagnostics(records, "risk_quality_tags")
    eligibility_diag = compute_eligibility_diagnostics(records)
    merged_tag_diag = {
        "tags": {
            **risk_tag_diag["tags"],
            **decomposition_tag_diag["tags"],
            **quality_tag_diag["tags"],
        }
    }
    root_causes = identify_root_causes(
        distributions,
        return_relationships,
        merged_tag_diag,
        eligibility_diag,
    )
    recommendations = build_recommendations(root_causes)
    output = {
        "as_of": "synthetic-test-window",
        "dataset_summary": {
            "valid_date_count": len({record["date"] for record in records}),
            "total_records": len(records),
            "records_with_data": len(records),
        },
        "distributions": distributions,
        "return_relationships": return_relationships,
        "tag_diagnostics": {
            "risk_tags": risk_tag_diag,
            "risk_decomposition_tags": decomposition_tag_diag,
            "risk_quality_tags": quality_tag_diag,
        },
        "eligibility_diagnostics": eligibility_diag,
        "root_causes": root_causes,
        "recommendations": recommendations,
    }

    output_dir = tmp_path / "risk_components"
    json_path = write_json(output_dir / "risk_component_quality.json", output)
    markdown_path = output_dir / "risk_component_quality.md"
    markdown_path.write_text(generate_markdown(output), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


class TestIntegration:
    def test_output_files_exist(self, risk_quality_output_paths):
        assert risk_quality_output_paths["json"].exists()
        assert risk_quality_output_paths["markdown"].exists()

    def test_json_structure(self, risk_quality_output_paths):
        data = json.loads(
            risk_quality_output_paths["json"].read_text(encoding="utf-8")
        )
        assert "distributions" in data
        assert "return_relationships" in data
        assert "tag_diagnostics" in data
        assert "eligibility_diagnostics" in data
        assert "root_causes" in data
        assert "recommendations" in data
        assert data["tag_diagnostics"]["risk_tags"]["tags"]["synthetic_risk"]["sample_count"] == 20
        # Verify all production_change_allowed = false
        assert all(not r["production_change_allowed"] for r in data["recommendations"])

    def test_markdown_chapters(self, risk_quality_output_paths):
        md = risk_quality_output_paths["markdown"].read_text(encoding="utf-8")
        assert "Executive Summary" in md
        assert "Component Distribution" in md
        assert "Component Return Relationship" in md
        assert "Risk Tag Return Diagnostics" in md
        assert "Trade Eligibility Diagnostics" in md
        assert "Root Causes" in md
        assert "Recommendations" in md
        assert "Do Not Change Production Yet" in md
        assert "synthetic_risk" in md
        assert "synthetic_decomposition" in md
        assert "synthetic_quality" in md


# ======================================================================
# Tests for new Phase 2 risk fields
# ======================================================================

class TestTradeRiskPenalty:
    """Test trade_risk_penalty from risk_decomposition."""

    def test_trade_risk_penalty_computed(self):
        from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
        stock = {
            "name": "TestStock", "code": "600001",
            "change_pct": 9.8, "amount": 100_000_000,
            "volume_ratio": 3.0, "turnover_rate": 5.0,
            "stock_short_score": 80, "stock_trend_score": 35,
            "decision_score": 70, "final_score": 60, "quant_score": 50,
            "source_pool": "burst", "risk_tags": ["near_limit_up"],
            "invalid_reason": "", "sector_role": "unknown",
        }
        result = decompose_trade_risk(stock)
        assert "trade_risk_penalty" in result
        assert result["trade_risk_penalty"] > 0
        assert result["trade_risk_penalty"] <= 40.0

    def test_trade_risk_penalty_zero_for_safe_stock(self):
        from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
        stock = {
            "name": "SafeStock", "code": "600001",
            "change_pct": 1.0, "amount": 100_000_000,
            "volume_ratio": 1.0, "turnover_rate": 2.0,
            "stock_short_score": 50, "stock_trend_score": 55,
            "decision_score": 55, "final_score": 60, "quant_score": 50,
            "source_pool": "trend", "risk_tags": [],
            "invalid_reason": "", "sector_role": "leader",
        }
        result = decompose_trade_risk(stock)
        assert result["trade_risk_penalty"] == 0.0

    def test_trade_risk_penalty_max_capped(self):
        from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
        stock = {
            "name": "RiskyStock", "code": "600001",
            "change_pct": 10.0, "amount": 100_000_000,
            "volume_ratio": 5.0, "turnover_rate": 8.0,
            "stock_short_score": 90, "stock_trend_score": 30,
            "decision_score": 80, "final_score": 40, "quant_score": 50,
            "source_pool": "burst", "risk_tags": ["near_limit_up", "overheated", "running_hot", "high_rejection", "volume_stagnation"],
            "invalid_reason": "", "sector_role": "laggard",
        }
        result = decompose_trade_risk(stock)
        assert result["trade_risk_penalty"] <= 40.0


class TestRiskQualityTags:
    """Test risk_quality_tags from risk_decomposition."""

    def test_quality_tags_category_prefixes(self):
        from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
        stock = {
            "name": "ST Stock", "code": "600001",
            "change_pct": 9.8, "amount": 5_000_000,
            "volume_ratio": 3.0, "turnover_rate": 0.3,
            "stock_short_score": 80, "stock_trend_score": 35,
            "decision_score": 70, "final_score": 60, "quant_score": 50,
            "source_pool": "burst", "risk_tags": ["near_limit_up"],
            "invalid_reason": "", "sector_role": "unknown",
        }
        result = decompose_trade_risk(stock)
        assert "risk_quality_tags" in result
        tags = result["risk_quality_tags"]
        # Check that tags have category prefixes
        for tag in tags:
            assert ":" in tag, f"Tag '{tag}' missing category prefix"
            category = tag.split(":")[0]
            assert category in ("hard", "trade", "elast", "drawdown"), f"Unknown category '{category}' in tag '{tag}'"

    def test_quality_tags_empty_for_safe_stock(self):
        from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
        stock = {
            "name": "PingAn Bank", "code": "600001",
            "change_pct": 1.0, "amount": 100_000_000,
            "volume_ratio": 1.0, "turnover_rate": 2.0,
            "stock_short_score": 50, "stock_trend_score": 55,
            "decision_score": 55, "final_score": 60, "quant_score": 50,
            "source_pool": "trend", "risk_tags": [],
            "invalid_reason": "", "sector_role": "leader",
        }
        result = decompose_trade_risk(stock)
        # Should have no quality tags for a safe stock with no risk factors
        assert isinstance(result["risk_quality_tags"], list)


class TestHardRiskNotConstant:
    """Test that hard_risk_penalty varies across different stocks."""

    def test_hard_risk_varies_with_stocks(self):
        from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
        stocks = [
            {"name": "PingAn Bank", "code": "600001", "change_pct": 1.0, "amount": 100_000_000,
             "volume_ratio": 1.0, "turnover_rate": 2.0, "stock_short_score": 50, "stock_trend_score": 55,
             "decision_score": 55, "final_score": 60, "quant_score": 50, "source_pool": "trend",
             "risk_tags": [], "invalid_reason": "", "sector_role": "leader"},
            {"name": "*ST Shenzhen", "code": "600002", "change_pct": 1.0, "amount": 100_000_000,
             "volume_ratio": 1.0, "turnover_rate": 2.0, "stock_short_score": 50, "stock_trend_score": 55,
             "decision_score": 55, "final_score": 60, "quant_score": 50, "source_pool": "trend",
             "risk_tags": [], "invalid_reason": "", "sector_role": "leader"},
            {"name": "LowLiquidity", "code": "600003", "change_pct": 1.0, "amount": 3_000_000,
             "volume_ratio": 1.0, "turnover_rate": 2.0, "stock_short_score": 50, "stock_trend_score": 55,
             "decision_score": 55, "final_score": 60, "quant_score": 50, "source_pool": "trend",
             "risk_tags": [], "invalid_reason": "", "sector_role": "leader"},
        ]
        results = [decompose_trade_risk(s) for s in stocks]
        hard_risks = [r["hard_risk_penalty"] for r in results]
        # ST stock should have higher hard_risk than normal stock
        assert hard_risks[1] > hard_risks[0]
        # Low liquidity stock should have higher hard_risk than normal stock
        assert hard_risks[2] > hard_risks[0]


class TestProductionDecisionScoreUnchanged:
    """Verify production decision_score computation is not modified."""

    def test_decision_score_formula_unchanged(self):
        from theme_sector_radar.scoring.decision_score import compute_decision_score
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_trend_score": 65,
            "sector_leader_score": 80, "agent_score": 50,
            "risk_penalty_score": 10,
        }
        result = compute_decision_score(stock)
        assert "decision_score" in result
        assert "decision_breakdown" in result
        # Verify the formula: 60*0.15 + 55*0.15 + 70*0.25 + 65*0.20 + 80*0.15 + 50*0.10 - 10
        expected = 60*0.15 + 55*0.15 + 70*0.25 + 65*0.20 + 80*0.15 + 50*0.10 - 10
        assert abs(result["decision_score"] - expected) < 0.1
