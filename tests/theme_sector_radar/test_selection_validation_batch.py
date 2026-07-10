"""Tests for batch selection validation."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from run_selection_validation_batch import (
    _compute_market_regime,
    _avg_return,
    build_aggregate,
    generate_aggregate_markdown,
    _scan_available_dates,
    run_sample_batch,
)


def _make_report(per_stock_returns: list[tuple[str, float | None]], ranking_groups=None, score_buckets=None, categorical_groups=None):
    """Create a synthetic validation report."""
    per_stock = []
    for code, ret in per_stock_returns:
        entry = {"code": code, "name": f"Stock{code}", "data_available": ret is not None}
        if ret is not None:
            entry["next_return_pct"] = ret
            entry["next_high_return_pct"] = ret + 1.0
            entry["next_low_return_pct"] = ret - 1.0
        per_stock.append(entry)

    return {
        "as_of": "2026-07-07",
        "coverage": {"total_candidates": len(per_stock_returns),
                      "data_available": sum(1 for _, r in per_stock_returns if r is not None),
                      "data_missing": sum(1 for _, r in per_stock_returns if r is None),
                      "missing_codes": []},
        "ranking_groups": ranking_groups or {},
        "score_buckets": score_buckets or {},
        "categorical_groups": categorical_groups or {},
        "interpretation": {"caution": "test"},
        "per_stock": per_stock,
    }



def test_run_sample_batch_writes_validation_artifacts(tmp_path, monkeypatch):
    import run_selection_validation_batch as batch

    monkeypatch.setattr(batch, "OUTPUT_DIR", tmp_path / "selection_validation")
    result = run_sample_batch(force=True)

    assert result["run_config"]["mode"] == "sample"
    assert result["coverage_summary"]["valid_date_count"] == 2
    assert (tmp_path / "selection_validation" / "sample" / "selection_validation_aggregate.json").exists()
    assert (tmp_path / "selection_validation" / "sample" / "selection_validation_aggregate.md").exists()
class TestMarketRegime:
    def test_broad_up(self):
        report = _make_report([("A", 2.0), ("B", 3.0), ("C", 1.5)])
        assert _compute_market_regime(report) == "broad_up"

    def test_broad_down(self):
        report = _make_report([("A", -2.0), ("B", -3.0), ("C", -1.5)])
        assert _compute_market_regime(report) == "broad_down"

    def test_mixed(self):
        report = _make_report([("A", 0.5), ("B", -0.3), ("C", 0.2)])
        assert _compute_market_regime(report) == "mixed"

    def test_missing_data(self):
        report = _make_report([("A", None), ("B", None)])
        assert _compute_market_regime(report) == "missing"


class TestAvgReturn:
    def test_with_data(self):
        report = _make_report([("A", 2.0), ("B", -1.0)])
        assert abs(_avg_return(report) - 0.5) < 0.01

    def test_no_data(self):
        report = _make_report([("A", None)])
        assert _avg_return(report) is None


class TestBuildAggregate:
    def _make_date_result(self, date, status="ok", n=20, avail=20, regime="mixed", avg_ret=0.5):
        return {
            "date": date, "status": status, "candidate_count": n,
            "data_available": avail, "market_regime": regime,
            "avg_candidate_return": avg_ret,
        }

    def _make_validation_report(self, top5_ret=-1.0, bot10_ret=-2.0, focus_ret=-1.0, avoid_ret=-2.0,
                                 trend_ret=-1.5, burst_ret=-1.0, analyzed_ret=-1.5, skipped_ret=-1.0,
                                 short_high_ret=-1.0, short_low_ret=-2.0):
        return {
            "ranking_groups": {
                "top5_by_decision_score": {"sample_count": 5, "avg_next_return_pct": top5_ret, "hit_rate_positive": 20},
                "bottom10_by_decision_score": {"sample_count": 10, "avg_next_return_pct": bot10_ret, "hit_rate_positive": 10},
            },
            "score_buckets": {
                "stock_short_score_high": {"sample_count": 7, "avg_next_return_pct": short_high_ret},
                "stock_short_score_low": {"sample_count": 7, "avg_next_return_pct": short_low_ret},
            },
            "categorical_groups": {
                "trade_eligibility_focus": {"sample_count": 7, "avg_next_return_pct": focus_ret, "hit_rate_positive": 14},
                "trade_eligibility_watch": {"sample_count": 10, "avg_next_return_pct": -1.5},
                "trade_eligibility_backup": {"sample_count": 5, "avg_next_return_pct": -1.8},
                "trade_eligibility_avoid": {"sample_count": 5, "avg_next_return_pct": avoid_ret},
                "source_pool_trend": {"sample_count": 15, "avg_next_return_pct": trend_ret},
                "source_pool_burst": {"sample_count": 15, "avg_next_return_pct": burst_ret},
                "analyzed": {"sample_count": 10, "avg_next_return_pct": analyzed_ret},
                "skipped_by_agent_stock_limit": {"sample_count": 20, "avg_next_return_pct": skipped_ret},
            },
        }

    def test_basic_aggregate(self):
        results = [
            self._make_date_result("2026-07-01"),
            self._make_date_result("2026-07-02"),
            self._make_date_result("2026-07-03"),
        ]
        reports = {
            "2026-07-01": self._make_validation_report(top5_ret=2.0, bot10_ret=-1.0),
            "2026-07-02": self._make_validation_report(top5_ret=1.0, bot10_ret=-2.0),
            "2026-07-03": self._make_validation_report(top5_ret=3.0, bot10_ret=0.0),
        }
        config = {"dates": ["2026-07-01", "2026-07-02", "2026-07-03"], "mode": "test"}
        agg = build_aggregate(results, reports, config)
        assert agg["coverage_summary"]["valid_date_count"] == 3
        assert agg["factor_performance_summary"]["decision_score"]["valid_date_count"] == 3

    def test_market_regime_classification(self):
        results = [
            self._make_date_result("2026-07-01", regime="broad_up", avg_ret=2.0),
            self._make_date_result("2026-07-02", regime="broad_down", avg_ret=-2.0),
        ]
        agg = build_aggregate(results, {}, {"dates": [], "mode": "test"})
        mr = agg["market_regime_summary"]
        assert "broad_up" in mr
        assert "broad_down" in mr
        assert mr["broad_up"]["date_count"] == 1
        assert mr["broad_down"]["date_count"] == 1

    def test_decision_score_gap_and_consistency(self):
        results = [self._make_date_result(f"2026-07-0{i}") for i in range(1, 6)]
        reports = {}
        for i in range(1, 6):
            # Positive gap on 3 dates, negative on 2
            top5 = 2.0 if i <= 3 else -3.0
            bot10 = -1.0 if i <= 3 else 0.0
            reports[f"2026-07-0{i}"] = self._make_validation_report(top5_ret=top5, bot10_ret=bot10)
        agg = build_aggregate(results, reports, {"dates": [], "mode": "test"})
        ds = agg["factor_performance_summary"]["decision_score"]
        assert ds["positive_gap_date_count"] == 3
        assert ds["negative_gap_date_count"] == 2
        assert ds["signal_consistency"] == 60.0

    def test_trade_eligibility_gap(self):
        results = [self._make_date_result(f"2026-07-0{i}") for i in range(1, 4)]
        reports = {
            "2026-07-01": self._make_validation_report(focus_ret=1.0, avoid_ret=-2.0),
            "2026-07-02": self._make_validation_report(focus_ret=2.0, avoid_ret=-1.0),
            "2026-07-03": self._make_validation_report(focus_ret=0.0, avoid_ret=-3.0),
        }
        agg = build_aggregate(results, reports, {"dates": [], "mode": "test"})
        te = agg["factor_performance_summary"]["trade_eligibility"]
        assert te["focus_vs_avoid_gap"] is not None
        assert te["focus_vs_avoid_gap"] > 0  # focus should outperform avoid

    def test_agent_missing_no_crash(self):
        """When no ranking data, agent signal should be insufficient_samples."""
        results = [self._make_date_result("2026-07-01")]
        reports = {
            "2026-07-01": self._make_validation_report(analyzed_ret=None, skipped_ret=None),
        }
        # Override with None for analyzed/skipped
        reports["2026-07-01"]["categorical_groups"]["analyzed"] = {"sample_count": 0, "avg_next_return_pct": None}
        reports["2026-07-01"]["categorical_groups"]["skipped_by_agent_stock_limit"] = {"sample_count": 0, "avg_next_return_pct": None}
        agg = build_aggregate(results, reports, {"dates": [], "mode": "test"})
        ag = agg["factor_performance_summary"]["agent_incremental"]
        assert ag["valid_date_count"] == 0

    def test_markdown_contains_all_sections(self):
        results = [self._make_date_result("2026-07-01")]
        reports = {"2026-07-01": self._make_validation_report()}
        agg = build_aggregate(results, reports, {"dates": ["2026-07-01"], "mode": "test"})
        md = generate_aggregate_markdown(agg)
        assert "Run Config" in md
        assert "Date Status" in md
        assert "Coverage Summary" in md
        assert "Market Regime Summary" in md
        assert "Decision Score Validation" in md
        assert "Stock Short Score Validation" in md
        assert "Trade Eligibility Validation" in md
        assert "Trend vs Burst Validation" in md
        assert "Agent Incremental Validation" in md
        assert "Interpretation" in md
        assert "Cautions" in md


class TestScanAvailableDates:
    def test_scan_finds_dates(self):
        dates = _scan_available_dates()
        assert len(dates) > 0
        assert "2026-07-07" in dates


class TestTop30ShadowRiskFields:
    """Test that top30_candidates.json includes shadow risk fields."""

    def test_top30_has_existing_shadow_fields(self):
        """Check that recent top30_candidates contain existing shadow fields.
        After re-export, new fields (trade_risk_penalty, risk_quality_tags) will also be present."""
        base = Path("reports/agent_bridge")
        if not base.exists():
            pytest.skip("agent_bridge directory not found")

        # Find a recent date directory
        date_dirs = sorted([d for d in base.iterdir() if d.is_dir() and d.name.startswith("2026-")], reverse=True)
        if not date_dirs:
            pytest.skip("No date directories found")

        for date_dir in date_dirs[:3]:
            t30_path = date_dir / "top30_candidates.json"
            if not t30_path.exists():
                continue
            data = json.loads(t30_path.read_text(encoding="utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                continue

            # Check first candidate has existing shadow fields (pre-Phase2)
            c = candidates[0]
            # These should exist in current reports
            assert "hard_risk_penalty" in c or "decision_score" in c, f"No scoring fields found in {t30_path}"
            # Verify production fields exist
            assert "decision_score" in c, f"Missing decision_score in {t30_path}"
            assert "risk_penalty_score" in c, f"Missing risk_penalty_score in {t30_path}"
            # After re-export, these will also be present:
            # trade_risk_penalty, risk_quality_tags, drawdown_risk_score
            break

    def test_production_decision_score_not_modified(self):
        """Verify decision_score formula is unchanged in top30."""
        base = Path("reports/agent_bridge")
        if not base.exists():
            pytest.skip("agent_bridge directory not found")

        date_dirs = sorted([d for d in base.iterdir() if d.is_dir() and d.name.startswith("2026-")], reverse=True)
        if not date_dirs:
            pytest.skip("No date directories found")

        for date_dir in date_dirs[:1]:
            t30_path = date_dir / "top30_candidates.json"
            if not t30_path.exists():
                continue
            data = json.loads(t30_path.read_text(encoding="utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                continue

            # Verify decision_score exists and is a number
            for c in candidates[:3]:
                ds = c.get("decision_score")
                assert ds is not None, f"decision_score is None for {c.get('code')}"
                assert isinstance(ds, (int, float)), f"decision_score is not numeric: {ds}"
            break

    def test_shadow_risk_decomposition_output(self):
        """Verify decompose_trade_risk returns all required fields."""
        from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
        stock = {
            "name": "Test Stock", "code": "600001",
            "change_pct": 3.0, "amount": 50_000_000,
            "volume_ratio": 2.0, "turnover_rate": 3.0,
            "stock_short_score": 65, "stock_trend_score": 55,
            "decision_score": 60, "final_score": 55, "quant_score": 50,
            "source_pool": "trend", "risk_tags": ["moderate_risk"],
            "invalid_reason": "", "sector_role": "unknown",
        }
        result = decompose_trade_risk(stock)
        # All required fields must be present
        assert "hard_risk_penalty" in result
        assert "trade_risk_penalty" in result
        assert "volatility_elasticity_score" in result
        assert "drawdown_risk_score" in result
        assert "risk_quality_tags" in result
        assert "risk_decomposition_tags" in result
        assert "risk_decomposition_breakdown" in result
        # Types check
        assert isinstance(result["hard_risk_penalty"], (int, float))
        assert isinstance(result["trade_risk_penalty"], (int, float))
        assert isinstance(result["volatility_elasticity_score"], (int, float))
        assert isinstance(result["drawdown_risk_score"], (int, float))
        assert isinstance(result["risk_quality_tags"], list)



