"""Structural validation for sector score report payloads."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


_REQUIRED_NUMERIC_FIELDS = (
    "trend_continuation_score",
    "short_term_burst_score",
)

_OPTIONAL_TEXT_FIELDS = (
    "trend_level",
    "trend_level_cn",
    "burst_level",
    "burst_level_cn",
)


def validate_sector_score_payload(payload: Any, *, expected_as_of: str) -> None:
    """Raise ``ValueError`` unless a score payload is usable by the bridge."""
    if not isinstance(payload, Mapping):
        raise ValueError("sector_scores payload must be an object")
    if payload.get("as_of_date") != expected_as_of:
        raise ValueError(
            "sector_scores.as_of_date mismatch: "
            f"expected={expected_as_of}, actual={payload.get('as_of_date')}"
        )

    scores = payload.get("scores")
    if not isinstance(scores, list) or not scores:
        raise ValueError("sector_scores.scores must be a non-empty list")
    for index, score in enumerate(scores):
        if not isinstance(score, Mapping):
            raise ValueError(f"sector_scores.scores[{index}] must be an object")
        sector_name = score.get("sector_name")
        if not isinstance(sector_name, str) or not sector_name.strip():
            raise ValueError(
                f"sector_scores.scores[{index}].sector_name must be non-empty"
            )
        sector_type = score.get("sector_type")
        if sector_type not in {"industry", "concept"}:
            raise ValueError(
                f"sector_scores.scores[{index}].sector_type must be industry or concept"
            )
        for field in _REQUIRED_NUMERIC_FIELDS:
            value = score.get(field)
            finite = False
            if not isinstance(value, bool) and isinstance(value, (int, float)):
                try:
                    finite = math.isfinite(value)
                except OverflowError:
                    finite = False
            if not finite:
                raise ValueError(
                    f"sector_scores.scores[{index}].{field} must be finite numeric"
                )
        for field in _OPTIONAL_TEXT_FIELDS:
            if field in score and not isinstance(score[field], str):
                raise ValueError(
                    f"sector_scores.scores[{index}].{field} must be text"
                )
