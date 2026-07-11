"""Helpers for reading factor values from candidate records."""

from __future__ import annotations

from typing import Any, Mapping


def coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_factor_value(
    candidate: Mapping[str, Any],
    factor_id: str,
    *,
    prefer: str = "score",
    allow_direct: bool = True,
) -> float | None:
    """Read a factor from a candidate top-level field or factor_snapshot.

    ``prefer`` can be ``"score"`` or ``"raw_value"``. Missing-quality snapshot
    entries are ignored so downstream logic does not treat neutral placeholders
    as usable observations.
    """
    if allow_direct:
        direct = coerce_float(candidate.get(factor_id))
        if direct is not None:
            return direct

    snapshot = candidate.get("factor_snapshot")
    if not isinstance(snapshot, Mapping):
        return None

    legacy_direct = coerce_float(snapshot.get(factor_id))
    if legacy_direct is not None:
        return legacy_direct

    factors = snapshot.get("factors")
    if not isinstance(factors, list):
        return None

    primary = prefer if prefer in {"score", "raw_value"} else "score"
    secondary = "raw_value" if primary == "score" else "score"
    for item in factors:
        if not isinstance(item, Mapping):
            continue
        if item.get("factor_id") != factor_id:
            continue
        if item.get("quality") == "missing":
            return None
        value = coerce_float(item.get(primary))
        if value is not None:
            return value
        return coerce_float(item.get(secondary))
    return None
