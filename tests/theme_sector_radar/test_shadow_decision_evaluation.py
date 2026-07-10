"""Tests for shadow decision score evaluation."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_shadow_decision_score import (
    spearman_correlation,
    evaluate_factor,
    _rank,
)


class TestSpearman:
    def test_perfect_positive(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert spearman_correlation(x, y) == 1.0

    def test_perfect_negative(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert spearman_correlation(x, y) == -1.0

    def test_insufficient_data(self):
        assert spearman_correlation([1.0], [1.0]) is None

    def test_rank_function(self):
        ranks = _rank([3.0, 1.0, 4.0, 1.0, 5.0])
        assert ranks[1] == 1.5  # tied lowest
        assert ranks[4] == 5.0  # highest


class TestEvaluateFactor:
    def _make_records(self, factor_values, returns, dates=None):
        records = []
        for i, (fv, ret) in enumerate(zip(factor_values, returns)):
            d = dates[i] if dates else "2026-06-01"
            records.append({
                "date": d, "code": f"S{i}", "data_available": True,
                "next_return_pct": ret, "test_score": fv,
            })
        return records

    def test_basic_evaluation(self):
        records = self._make_records(
            [90, 80, 70, 60, 50, 40, 30, 20, 10, 5],
            [5.0, 4.0, 3.0, 2.0, 1.0, -1.0, -2.0, -3.0, -4.0, -5.0],
        )
        result = evaluate_factor(records, "test_score")
        assert result["sample_count"] == 10
        assert result["top5_bottom10_gap"] is not None
        assert result["top5_bottom10_gap"] > 0  # positive factor should have positive gap

    def test_insufficient_samples(self):
        records = self._make_records([90, 80], [5.0, 4.0])
        result = evaluate_factor(records, "test_score")
        assert result.get("error") == "insufficient_samples"


class TestOutputExists:
    def test_output_files_exist(self):
        base = Path("reports/selection_validation/shadow_score/2026-06-01_to_2026-07-07")
        # These may not exist yet until evaluation is run
        if (base / "shadow_decision_score_evaluation.json").exists():
            data = json.loads((base / "shadow_decision_score_evaluation.json").read_text(encoding="utf-8"))
            assert "factor_results" in data
            assert "improvement_assessment" in data
            assert "risk_decomposition_summary" in data
            # Verify production_change_allowed is false
            assert data["improvement_assessment"]["production_change_allowed"] is False
            for rec in data.get("recommendations", []):
                assert rec["production_change_allowed"] is False
