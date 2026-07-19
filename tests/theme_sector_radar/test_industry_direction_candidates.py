import copy
import hashlib
import json

import pytest

from scripts.select_industry_direction_candidates import build_candidate_report
from theme_sector_radar.scoring.industry_direction_candidates import (
    select_industry_direction_candidates,
)


def _row(
    rank: int,
    *,
    score: float | None = None,
    time_score: float = 45.0,
    state: str = "watch",
) -> dict:
    return {
        "sector_id": f"industry_{rank}",
        "sector_name": f"Industry {rank}",
        "direction_score_shadow": score if score is not None else 80.0 - rank,
        "time_series_score": time_score,
        "direction_state": state,
        "final_score": 100.0 - rank,
        "v2_score": 90.0 - rank,
        "selection_score": 70.0 - rank,
        "selection_score_adjusted": 60.0 - rank,
    }


def test_top_rank_and_time_series_confirmation_create_expected_tiers():
    rows = [_row(rank) for rank in range(1, 12)]

    result = select_industry_direction_candidates(rows)

    assert [row["candidate_rank"] for row in result["core_candidates"]] == [1, 2, 3, 4, 5]
    assert [row["candidate_rank"] for row in result["supplemental_candidates"]] == [6, 7]
    assert [row["candidate_rank"] for row in result["observations"]] == [8, 9, 10]
    assert result["selection_counts"] == {
        "core_candidates": 5,
        "supplemental_candidates": 2,
        "confirmation_required": 0,
        "observations": 3,
    }


def test_time_series_floor_and_blocked_state_fail_closed_to_observation():
    rows = [
        _row(1, time_score=39.99),
        _row(2, state="weakening"),
        _row(3, score=49.99),
        _row(4),
    ]

    result = select_industry_direction_candidates(rows)

    reasons = {
        row["sector_id"]: row["candidate_reasons"]
        for row in result["observations"]
    }
    assert "time_series_score_below_floor" in reasons["industry_1"]
    assert "direction_state_blocked" in reasons["industry_2"]
    assert "direction_score_below_floor" in reasons["industry_3"]
    assert [row["sector_id"] for row in result["core_candidates"]] == ["industry_4"]


def test_pulse_is_not_promoted_by_high_composite_score():
    result = select_industry_direction_candidates(
        [_row(1, score=95.0, time_score=45.0, state="pulse_confirmation_required")]
    )

    assert result["core_candidates"] == []
    assert result["confirmation_required"][0]["candidate_tier"] == "confirmation_required"
    assert result["confirmation_required"][0]["candidate_reasons"] == [
        "pulse_requires_confirmation"
    ]


def test_selector_does_not_mutate_inputs_or_protected_scores():
    rows = [_row(rank) for rank in range(1, 9)]
    original = copy.deepcopy(rows)

    result = select_industry_direction_candidates(rows)

    assert rows == original
    emitted = (
        result["core_candidates"]
        + result["supplemental_candidates"]
        + result["confirmation_required"]
        + result["observations"]
    )
    by_id = {row["sector_id"]: row for row in original}
    for row in emitted:
        source = by_id[row["sector_id"]]
        for field in (
            "final_score",
            "v2_score",
            "selection_score",
            "selection_score_adjusted",
        ):
            assert row[field] == source[field]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_candidate_inputs_are_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        select_industry_direction_candidates([_row(1, score=value)])


def test_candidate_report_accepts_range_input_and_binds_source_sha(tmp_path):
    source = {
        "schema_version": "industry_direction_shadow_range.v1",
        "daily_results": [
            {"as_of_date": "2026-07-16", "sectors": [_row(2)]},
            {"as_of_date": "2026-07-17", "sectors": [_row(1)]},
        ],
    }
    source_path = tmp_path / "direction.json"
    raw = json.dumps(source, allow_nan=False).encode("utf-8")
    source_path.write_bytes(raw)

    result = build_candidate_report(
        source,
        source_path=source_path,
        source_sha256=hashlib.sha256(raw).hexdigest(),
    )

    assert result["as_of_date"] == "2026-07-17"
    assert result["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["core_candidates"][0]["sector_id"] == "industry_1"
