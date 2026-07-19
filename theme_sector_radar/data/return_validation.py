"""Validation for trusted daily return inputs."""

from __future__ import annotations

import math
from typing import Any, Iterable


def trusted_daily_return(value: Any, *, field: str = "daily return") -> float:
    """Return a finite A-share sector daily return in the trusted domain."""
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(result) or not (-100.0 < result <= 100.0):
        raise ValueError(
            f"{field} must be finite and within trusted daily return range (-100, 100]"
        )
    return result


def trusted_daily_returns(values: Iterable[Any]) -> list[float]:
    if isinstance(values, (str, bytes)):
        raise ValueError("daily returns must be an array")
    try:
        return [trusted_daily_return(value) for value in values]
    except TypeError as exc:
        raise ValueError("daily returns must be an array") from exc
