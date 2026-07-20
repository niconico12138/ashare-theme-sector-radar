"""Independent three-layer direction scoring for concept research."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any, Mapping

from ..agents.ranking_report.sector_ranking_agent import (
    _build_industry_trend_features,
)
from ..data.akshare_concept_history import validate_history_payload
from ..data.board_membership_snapshot import (
    membership_snapshot_sha256,
    validate_membership_snapshot,
)
from .industry_three_layer_shadow import calculate_industry_three_layer_shadow


SCHEMA_VERSION = "concept_direction_score_shadow.v1"
PAPER_MODE = "paper_shadow_research_only"
DISCLAIMER = "Paper/shadow research output only; not executable."
BLOCKED_STATES = frozenset({"unavailable", "weakening", "trend_weakening"})


def score_concept_directions(
    membership_snapshot: dict[str, Any],
    histories: Mapping[str, dict[str, Any]],
    *,
    snapshot_sha256: str,
    as_of_date: str,
    minimum_history_rows: int = 20,
) -> dict[str, Any]:
    """Score concepts without mutating membership, history, or formal scores."""
    snapshot = copy.deepcopy(membership_snapshot)
    history_inputs = copy.deepcopy(dict(histories))
    validate_membership_snapshot(snapshot, expected_as_of_date=as_of_date)
    if isinstance(minimum_history_rows, bool) or not isinstance(minimum_history_rows, int):
        raise ValueError("minimum_history_rows must be an integer")
    if minimum_history_rows < 20:
        raise ValueError("minimum_history_rows must be at least 20")
    if not _is_sha256(snapshot_sha256):
        raise ValueError("snapshot_sha256 must be a SHA-256 digest")
    expected_snapshot_sha256 = membership_snapshot_sha256(snapshot)
    if snapshot_sha256.lower() != expected_snapshot_sha256:
        raise ValueError("snapshot_sha256 does not match membership snapshot")

    boards = snapshot["boards"]
    expected_codes = {board["board_code"] for board in boards}
    if set(history_inputs) != expected_codes:
        missing = sorted(expected_codes - set(history_inputs))
        unexpected = sorted(set(history_inputs) - expected_codes)
        raise ValueError(
            f"concept history identity set mismatch; missing={missing}, unexpected={unexpected}"
        )

    history_for_features: dict[str, dict[str, Any]] = {}
    histories_by_code: dict[str, dict[str, Any]] = {}
    for board in boards:
        code = board["board_code"]
        history = history_inputs[code]
        expected_identity = {
            "board_code": code,
            "board_name": board["board_name"],
        }
        validate_history_payload(history, expected_identity=expected_identity)
        query = history["query"]
        if (
            query["as_of_date"] != as_of_date
            or query["end_date"] != as_of_date
        ):
            raise ValueError(f"concept history is not PIT for {code}")
        histories_by_code[code] = history
        history_for_features[code] = {
            "recent_returns": [row["pct_change"] for row in history["rows"]],
            "recent_dates": [row["date"] for row in history["rows"]],
        }

    sector_stubs = [SimpleNamespace(name=board["board_code"]) for board in boards]
    features_by_code = _build_industry_trend_features(
        sector_stubs,
        history_for_features,
    )
    concept_rows: list[dict[str, Any]] = []
    for board in boards:
        code = board["board_code"]
        history = histories_by_code[code]
        features = features_by_code[code]
        layers = calculate_industry_three_layer_shadow(None, features)
        if len(history["rows"]) < minimum_history_rows:
            layers["direction_score_shadow"] = None
            layers["direction_state"] = "unavailable"
        layer_values = {
            "time_series": copy.deepcopy(layers["time_series"]),
            "cross_section": copy.deepcopy(layers["cross_section"]),
            "rank_momentum": copy.deepcopy(layers["rank_momentum"]),
        }
        layer_statuses = {
            name: value["status"] for name, value in layer_values.items()
        }
        concept_rows.append(
            {
                "board_code": code,
                "board_name": board["board_name"],
                "member_count": board["member_count"],
                "direction_score_shadow": layers["direction_score_shadow"],
                "direction_state": layers["direction_state"],
                "weights": copy.deepcopy(layers["weights"]),
                "layers": layer_values,
                "data_quality": {
                    "status": (
                        "complete"
                        if layers["direction_score_shadow"] is not None
                        else "unavailable"
                    ),
                    "history_days": len(history["rows"]),
                    "layer_statuses": layer_statuses,
                },
                "provenance": {
                    "membership_snapshot_sha256": snapshot_sha256.lower(),
                    "membership_source_key": board["source_key"],
                    "membership_symbols_sha256": board["symbols_sha256"],
                    "history_rows_sha256": history["rows_sha256"],
                    "history_query": copy.deepcopy(history["query"]),
                },
                "formal_candidate_eligible": False,
            }
        )
    concept_rows.sort(key=lambda item: (item["board_code"], item["board_name"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": PAPER_MODE,
        "disclaimer": DISCLAIMER,
        "as_of_date": as_of_date,
        "formal_candidate_eligible": False,
        "provenance": {
            "membership_snapshot_sha256": snapshot_sha256.lower(),
            "membership_boards_sha256": snapshot["boards_sha256"],
            "history_rows_sha256_by_board": {
                code: histories_by_code[code]["rows_sha256"]
                for code in sorted(histories_by_code)
            },
        },
        "input_counts": {
            "concepts": len(concept_rows),
            "scored": sum(
                row["direction_score_shadow"] is not None for row in concept_rows
            ),
            "unavailable": sum(
                row["direction_score_shadow"] is None for row in concept_rows
            ),
        },
        "minimum_history_rows": minimum_history_rows,
        "concepts": concept_rows,
    }


def select_concept_shadow_candidates(
    score_report: dict[str, Any],
    *,
    top_n: int = 10,
) -> dict[str, Any]:
    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n must be a positive integer")
    report = copy.deepcopy(score_report)
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("concept direction score schema mismatch")
    if report.get("mode") != PAPER_MODE or report.get("formal_candidate_eligible") is not False:
        raise ValueError("concept direction input must remain shadow-only")
    concepts = report.get("concepts")
    if not isinstance(concepts, list):
        raise ValueError("concept direction concepts must be an array")

    eligible = []
    for row in concepts:
        if not isinstance(row, dict) or row.get("formal_candidate_eligible") is not False:
            raise ValueError("concept direction row must remain shadow-only")
        score = row.get("direction_score_shadow")
        state = str(row.get("direction_state") or "unavailable")
        if score is None or state in BLOCKED_STATES:
            continue
        eligible.append(row)
    eligible.sort(
        key=lambda item: (
            -float(item["direction_score_shadow"]),
            item["board_code"],
            item["board_name"],
        )
    )
    selected = eligible[:top_n]
    for rank, row in enumerate(selected, 1):
        row["concept_shadow_rank"] = rank
        row["formal_candidate_eligible"] = False
    return {
        "schema_version": "concept_shadow_candidate_selection.v1",
        "mode": PAPER_MODE,
        "disclaimer": DISCLAIMER,
        "as_of_date": report.get("as_of_date"),
        "formal_candidate_eligible": False,
        "selection_policy": {
            "top_n": top_n,
            "blocked_states": sorted(BLOCKED_STATES),
        },
        "concept_shadow_candidates": selected,
    }


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())
