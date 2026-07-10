"""Tests for agent score merge into top30_candidates.json."""

import json

import pytest

from scripts.export_top30_candidates import merge_agent_scores_into_candidates


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class TestMergeAgentScoresIntoCandidates:
    def test_agent_score_fields_appear_in_enriched_candidates(self, tmp_path):
        """agent_score, risk_adjusted_score, risk_level are added to candidates."""
        top30_data = {
            "schema_version": "1.0",
            "as_of": "2026-07-08",
            "candidates": [
                {"code": "600001", "name": "Stock1", "final_score": 80},
                {"code": "600002", "name": "Stock2", "final_score": 70},
            ],
        }
        top30_path = tmp_path / "top30_candidates.json"
        _write_json(top30_path, top30_data)

        ranking_data = {
            "schema_version": "1.0",
            "as_of": "2026-07-08",
            "items": [
                {"rank": 1, "code": "600001", "name": "Stock1",
                 "agent_score": 75.5, "risk_adjusted_score": 73.2, "risk_level": "medium"},
                {"rank": 2, "code": "600002", "name": "Stock2",
                 "agent_score": 65.0, "risk_adjusted_score": 62.8, "risk_level": "low"},
            ],
        }
        ranking_path = tmp_path / "aihf_stock_ranking.json"
        _write_json(ranking_path, ranking_data)

        result = merge_agent_scores_into_candidates(top30_path, ranking_path)
        assert result is True

        enriched = json.loads(top30_path.read_text(encoding="utf-8"))
        candidates = enriched["candidates"]

        assert candidates[0]["agent_score"] == 75.5
        assert candidates[0]["risk_adjusted_score"] == 73.2
        assert candidates[0]["risk_level"] == "medium"
        assert candidates[1]["agent_score"] == 65.0

    def test_no_agent_score_when_ranking_missing(self, tmp_path):
        """No agent_score fields added when ranking file does not exist."""
        top30_data = {
            "schema_version": "1.0",
            "candidates": [{"code": "600001", "name": "Stock1", "final_score": 80}],
        }
        top30_path = tmp_path / "top30_candidates.json"
        _write_json(top30_path, top30_data)

        ranking_path = tmp_path / "aihf_stock_ranking.json"  # does not exist

        result = merge_agent_scores_into_candidates(top30_path, ranking_path)
        assert result is False

        enriched = json.loads(top30_path.read_text(encoding="utf-8"))
        assert "agent_score" not in enriched["candidates"][0]
        assert "risk_adjusted_score" not in enriched["candidates"][0]
        assert "risk_level" not in enriched["candidates"][0]

    def test_rank_hidden_constraint_preserved(self, tmp_path):
        """rank_hidden stays True and no raw rank is exposed in candidates."""
        top30_data = {
            "schema_version": "1.0",
            "rank_hidden": True,
            "candidates": [{"code": "600001", "name": "Stock1", "final_score": 80}],
        }
        top30_path = tmp_path / "top30_candidates.json"
        _write_json(top30_path, top30_data)

        ranking_data = {
            "items": [{"rank": 1, "code": "600001", "name": "Stock1",
                        "agent_score": 75.5, "risk_adjusted_score": 73.2, "risk_level": "medium"}],
        }
        ranking_path = tmp_path / "aihf_stock_ranking.json"
        _write_json(ranking_path, ranking_data)

        result = merge_agent_scores_into_candidates(top30_path, ranking_path)
        assert result is True

        enriched = json.loads(top30_path.read_text(encoding="utf-8"))
        assert enriched.get("rank_hidden") is True
        assert "rank" not in enriched["candidates"][0]

    def test_partial_merge_when_ranking_incomplete(self, tmp_path):
        """Merge works when ranking has fewer stocks than candidates."""
        top30_data = {
            "schema_version": "1.0",
            "candidates": [
                {"code": "600001", "name": "Stock1", "final_score": 80},
                {"code": "600002", "name": "Stock2", "final_score": 70},
                {"code": "600003", "name": "Stock3", "final_score": 60},
            ],
        }
        top30_path = tmp_path / "top30_candidates.json"
        _write_json(top30_path, top30_data)

        ranking_data = {
            "items": [
                {"rank": 1, "code": "600001", "agent_score": 75.5,
                 "risk_adjusted_score": 73.2, "risk_level": "medium"},
                {"rank": 2, "code": "600002", "agent_score": 65.0,
                 "risk_adjusted_score": 62.8, "risk_level": "low"},
            ],
        }
        ranking_path = tmp_path / "aihf_stock_ranking.json"
        _write_json(ranking_path, ranking_data)

        result = merge_agent_scores_into_candidates(top30_path, ranking_path)
        assert result is True

        enriched = json.loads(top30_path.read_text(encoding="utf-8"))
        candidates = enriched["candidates"]

        assert candidates[0]["agent_score"] == 75.5
        assert candidates[1]["agent_score"] == 65.0
        # Third stock not in ranking — no agent_score
        assert "agent_score" not in candidates[2]
        assert "risk_adjusted_score" not in candidates[2]
        assert "risk_level" not in candidates[2]

    def test_merge_metadata_updated(self, tmp_path):
        """Merge metadata fields are written to top30_candidates.json."""
        top30_data = {
            "schema_version": "1.0",
            "candidates": [{"code": "600001", "name": "Stock1", "final_score": 80}],
        }
        top30_path = tmp_path / "top30_candidates.json"
        _write_json(top30_path, top30_data)

        ranking_data = {
            "items": [{"rank": 1, "code": "600001", "agent_score": 75.5,
                        "risk_adjusted_score": 73.2, "risk_level": "medium"}],
        }
        ranking_path = tmp_path / "aihf_stock_ranking.json"
        _write_json(ranking_path, ranking_data)

        result = merge_agent_scores_into_candidates(top30_path, ranking_path)
        assert result is True

        enriched = json.loads(top30_path.read_text(encoding="utf-8"))
        assert enriched.get("agent_score_merged") is True
        assert enriched.get("agent_score_merge_count") == 1
        assert enriched.get("agent_score_source") == str(ranking_path)


def test_merge_function_handles_invalid_json(tmp_path):
    """Invalid JSON in top30 file is handled gracefully."""
    top30_path = tmp_path / "top30_candidates.json"
    top30_path.write_text("not valid json {{{", encoding="utf-8")

    ranking_data = {"items": []}
    ranking_path = tmp_path / "aihf_stock_ranking.json"
    _write_json(ranking_path, ranking_data)

    result = merge_agent_scores_into_candidates(top30_path, ranking_path)
    assert result is False


# ---------------------------------------------------------------------------
# Regression: merge → calibration pipeline produces agent_score data
# ---------------------------------------------------------------------------


def test_merge_then_calibration_sees_agent_score(tmp_path):
    """After merge, evaluate_score_layers should see agent_score in candidates."""
    from scripts.evaluate_scoring_calibration import evaluate_score_layers

    # 1. Build top30_candidates.json WITHOUT agent_score
    top30_data = {
        "schema_version": "1.0",
        "as_of": "2026-07-07",
        "rank_hidden": True,
        "candidates": [
            {"code": "600001", "name": "S1", "final_score": 70, "quant_score": 65},
            {"code": "600002", "name": "S2", "final_score": 55, "quant_score": 50},
        ],
    }
    top30_path = tmp_path / "top30_candidates.json"
    _write_json(top30_path, top30_data)

    # 2. Build aihf_stock_ranking.json with agent_score
    ranking_data = {
        "items": [
            {"rank": 1, "code": "600001", "agent_score": 82.0,
             "risk_adjusted_score": 80.0, "risk_level": "low"},
            {"rank": 2, "code": "600002", "agent_score": 45.0,
             "risk_adjusted_score": 42.0, "risk_level": "high"},
        ],
    }
    ranking_path = tmp_path / "aihf_stock_ranking.json"
    _write_json(ranking_path, ranking_data)

    # 3. Merge
    ok = merge_agent_scores_into_candidates(top30_path, ranking_path)
    assert ok is True

    # 4. Load merged candidates and run calibration
    merged = json.loads(top30_path.read_text(encoding="utf-8"))
    candidates = merged["candidates"]

    # Verify agent_score is present
    assert candidates[0]["agent_score"] == 82.0
    assert candidates[1]["agent_score"] == 45.0

    forward_returns = {
        "600001": {"1d": 2.5},
        "600002": {"1d": -1.0},
    }

    result = evaluate_score_layers(candidates, forward_returns, horizons=("1d",), as_of="2026-07-07")

    # 5. Verify agent_score layer has non-missing buckets
    agent_layer = result["layers"]["agent_score"]
    missing_count = agent_layer["buckets"]["missing"]["candidate_count"]
    non_missing = sum(
        b["candidate_count"]
        for bname, b in agent_layer["buckets"].items()
        if bname != "missing"
    )

    # All candidates should have agent_score (no missing)
    assert missing_count == 0, f"agent_score still has {missing_count} missing candidates"
    assert non_missing == 2, f"Expected 2 non-missing candidates, got {non_missing}"

    # The 80+ bucket should have the high-score stock
    high_bucket = agent_layer["buckets"]["80+"]
    assert high_bucket["candidate_count"] == 1
    assert high_bucket["horizons"]["1d"]["avg_return_pct"] == pytest.approx(2.5)


def test_merge_then_calibration_rank_hidden_preserved(tmp_path):
    """After merge + calibration, rank_hidden is still True and no rank in candidates."""
    from scripts.evaluate_scoring_calibration import evaluate_score_layers

    top30_data = {
        "rank_hidden": True,
        "candidates": [{"code": "600001", "name": "S1", "final_score": 70}],
    }
    top30_path = tmp_path / "top30_candidates.json"
    _write_json(top30_path, top30_data)

    ranking_data = {
        "items": [{"rank": 1, "code": "600001", "agent_score": 80.0}],
    }
    ranking_path = tmp_path / "aihf_stock_ranking.json"
    _write_json(ranking_path, ranking_data)

    merge_agent_scores_into_candidates(top30_path, ranking_path)

    merged = json.loads(top30_path.read_text(encoding="utf-8"))
    assert merged.get("rank_hidden") is True
    for c in merged["candidates"]:
        assert "rank" not in c
