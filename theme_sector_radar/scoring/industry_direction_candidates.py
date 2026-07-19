"""Paper-only candidate selection from industry direction shadow scores."""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, Iterable


PAPER_MODE = "paper_shadow_research_only"
BLOCKED_STATES = frozenset({"weakening", "trend_weakening", "unavailable"})
PROTECTED_SCORE_FIELDS = frozenset(
    {"final_score", "v2_score", "selection_score", "selection_score_adjusted"}
)


def _finite_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def select_industry_direction_candidates(
    sectors: Iterable[Dict[str, Any]],
    *,
    candidate_top_n: int = 7,
    core_top_n: int = 5,
    observation_top_n: int = 10,
    minimum_direction_score: float = 50.0,
    minimum_time_series_score: float = 40.0,
) -> Dict[str, Any]:
    """Combine relative direction rank with independent time-series confirmation.

    The selector copies every emitted row and never changes formal or protected scores.
    Pulse rows remain confirmation candidates instead of being promoted by a high
    composite direction score alone.
    """
    if not 1 <= core_top_n <= candidate_top_n <= observation_top_n:
        raise ValueError(
            "candidate limits must satisfy 1 <= core_top_n <= candidate_top_n "
            "<= observation_top_n"
        )
    direction_floor = _finite_number(
        minimum_direction_score, field="minimum_direction_score"
    )
    time_series_floor = _finite_number(
        minimum_time_series_score, field="minimum_time_series_score"
    )

    available: list[tuple[float, str, Dict[str, Any]]] = []
    unavailable_count = 0
    for source in sectors:
        if not isinstance(source, dict):
            raise ValueError("sector rows must be objects")
        score = source.get("direction_score_shadow")
        if score is None:
            unavailable_count += 1
            continue
        number = _finite_number(score, field="direction_score_shadow")
        identity = str(source.get("sector_id") or source.get("sector_name") or "")
        available.append((number, identity, source))

    available.sort(key=lambda item: (-item[0], item[1]))
    groups: dict[str, list[Dict[str, Any]]] = {
        "core_candidates": [],
        "supplemental_candidates": [],
        "confirmation_required": [],
        "observations": [],
    }
    for candidate_rank, (_score, _identity, source) in enumerate(available, 1):
        if candidate_rank > observation_top_n:
            break
        item = copy.deepcopy(source)
        item["candidate_rank"] = candidate_rank
        reasons: list[str] = []

        if candidate_rank > candidate_top_n:
            reasons.append("outside_candidate_top_n")
        if float(item["direction_score_shadow"]) < direction_floor:
            reasons.append("direction_score_below_floor")

        raw_time_score = item.get("time_series_score")
        if raw_time_score is None:
            reasons.append("time_series_unavailable")
        else:
            time_score = _finite_number(raw_time_score, field="time_series_score")
            if time_score < time_series_floor:
                reasons.append("time_series_score_below_floor")

        state = str(item.get("direction_state") or "unavailable")
        if state in BLOCKED_STATES:
            reasons.append("direction_state_blocked")

        hard_failure = bool(reasons)
        if hard_failure:
            tier = "observation"
            target = groups["observations"]
        elif state == "pulse_confirmation_required":
            tier = "confirmation_required"
            reasons.append("pulse_requires_confirmation")
            target = groups["confirmation_required"]
        elif candidate_rank <= core_top_n:
            tier = "core"
            reasons.append("top_rank_and_time_series_confirmed")
            target = groups["core_candidates"]
        else:
            tier = "supplemental"
            reasons.append("supplemental_rank_and_time_series_confirmed")
            target = groups["supplemental_candidates"]

        item["candidate_tier"] = tier
        item["candidate_reasons"] = reasons
        target.append(item)

    return {
        "schema_version": "industry_direction_candidate_selection.v1",
        "mode": PAPER_MODE,
        "disclaimer": "No broker connection and no live order instruction.",
        "policy": {
            "candidate_top_n": candidate_top_n,
            "core_top_n": core_top_n,
            "observation_top_n": observation_top_n,
            "minimum_direction_score": direction_floor,
            "minimum_time_series_score": time_series_floor,
            "blocked_states": sorted(BLOCKED_STATES),
            "pulse_policy": "confirmation_required_not_auto_promoted",
            "protected_score_fields": sorted(PROTECTED_SCORE_FIELDS),
        },
        "input_counts": {
            "available": len(available),
            "unavailable": unavailable_count,
        },
        "selection_counts": {key: len(value) for key, value in groups.items()},
        **groups,
    }
