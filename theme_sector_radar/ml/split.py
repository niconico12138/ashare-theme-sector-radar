"""Chronological, date-grouped walk-forward splits with label purge."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence


def _canonical_date(value: Any) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"record as_of_date must be an ISO date: {text!r}") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"record as_of_date must be canonical: {text!r}")
    return text


def expanding_walk_forward_splits(
    records: Sequence[Mapping[str, Any]],
    *,
    min_train_dates: int,
    test_dates: int,
    purge_dates: int,
    max_label_horizon: int,
) -> list[dict[str, Any]]:
    """Split complete trading-date groups; no row from a date crosses a fold."""

    if max_label_horizon <= 0:
        raise ValueError("max_label_horizon must be positive")
    if purge_dates < max_label_horizon:
        raise ValueError(
            f"purge_dates must be at least max_label_horizon ({max_label_horizon})"
        )
    if min_train_dates <= 0 or test_dates <= 0:
        raise ValueError("min_train_dates and test_dates must be positive")
    dates = sorted({_canonical_date(row.get("as_of_date")) for row in records})
    first_test_index = min_train_dates + purge_dates
    if len(dates) <= first_test_index:
        return []

    folds: list[dict[str, Any]] = []
    test_start = first_test_index
    while test_start < len(dates):
        train_end = test_start - purge_dates
        train = dates[:train_end]
        purged = dates[train_end:test_start]
        test = dates[test_start : test_start + test_dates]
        if not test:
            break
        train_set = set(train)
        test_set = set(test)
        folds.append(
            {
                "fold": len(folds) + 1,
                "train_dates": train,
                "purged_dates": purged,
                "test_dates": test,
                "train_indices": [
                    index
                    for index, row in enumerate(records)
                    if str(row.get("as_of_date")) in train_set
                ],
                "test_indices": [
                    index
                    for index, row in enumerate(records)
                    if str(row.get("as_of_date")) in test_set
                ],
                "purge_dates": purge_dates,
                "max_label_horizon": max_label_horizon,
            }
        )
        test_start += test_dates
    return folds
