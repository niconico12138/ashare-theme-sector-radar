"""Paper-only validation for dual intraday exit candidates."""

from __future__ import annotations

import math
import json
from collections import Counter
from typing import Any, Mapping, Sequence


CANDIDATE_IDS = (
    "paper_fixed_exit_baseline",
    "paper_take_profit_protect_candidate",
    "paper_stop_loss_risk_candidate",
)


def validate_dual_exit_records(
    records: Sequence[Mapping[str, Any]],
    *,
    fold_count: int = 3,
    min_labeled_triggers: int = 5,
    tail_loss_pct: float = -5.0,
) -> dict[str, Any]:
    rows = sorted((dict(row) for row in records if isinstance(row, Mapping)), key=lambda row: str(row.get("as_of") or ""))
    deduplicated = _deduplicate_entries(rows)
    return {
        "schema_version": "timing_dual_exit_validation.v1",
        "summary": {
            "record_count": len(rows),
            "deduplicated_entry_count": len(deduplicated),
            "duplicate_record_count": len(rows) - len(deduplicated),
            "fold_count": fold_count,
            "min_labeled_triggers": min_labeled_triggers,
            "tail_loss_pct": tail_loss_pct,
        },
        "candidates": {
            candidate_id: _candidate_validation(
                rows,
                deduplicated,
                candidate_id,
                fold_count=fold_count,
                min_labeled_triggers=min_labeled_triggers,
                tail_loss_pct=tail_loss_pct,
            )
            for candidate_id in CANDIDATE_IDS
        },
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def _candidate_validation(
    records: list[dict[str, Any]],
    deduplicated_records: list[dict[str, Any]],
    candidate_id: str,
    *,
    fold_count: int,
    min_labeled_triggers: int,
    tail_loss_pct: float,
) -> dict[str, Any]:
    triggered = _triggered_records(deduplicated_records, candidate_id)
    return {
        "summary": _summary(deduplicated_records, candidate_id, tail_loss_pct=tail_loss_pct),
        "walk_forward": _walk_forward(
            deduplicated_records,
            candidate_id,
            fold_count=fold_count,
            min_labeled_triggers=min_labeled_triggers,
            tail_loss_pct=tail_loss_pct,
        ),
        "by_version": _group_summary(records, candidate_id, "timing_version_id", tail_loss_pct=tail_loss_pct),
        "by_board": _board_summary(deduplicated_records, candidate_id, tail_loss_pct=tail_loss_pct),
        "by_trigger_factor": _factor_summary(deduplicated_records, candidate_id, tail_loss_pct=tail_loss_pct),
        "concentration": _concentration(triggered),
        "paper_research_only": True,
    }


def _deduplicate_entries(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[str, str, str, str], tuple[dict[str, Any], str]] = {}
    for index, record in enumerate(records):
        signal_date = str(record.get("signal_date") or record.get("as_of") or "")
        entry_date = str(record.get("entry_date") or "")
        code = str(record.get("code") or "")
        interval = str((record.get("execution_assumptions") or {}).get("bar_interval") or "")
        key = (
            signal_date or f"__row_{index}",
            entry_date,
            code or f"__row_{index}",
            interval,
        )
        signature = json.dumps(
            {
                "entry_path_sha256": (
                    record.get("source_1m_bars_sha256")
                    if interval == "5m"
                    else record.get("entry_bars_sha256")
                ),
                "forward_return_pct": record.get("forward_return_pct"),
                "path_stats": record.get("path_stats"),
                "paper_exit_candidates": record.get("paper_exit_candidates"),
            },
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=True,
        )
        existing = unique.get(key)
        if existing is not None and existing[1] != signature:
            raise ValueError(f"duplicate entry policy/path conflict for {signal_date} {entry_date} {code}")
        unique.setdefault(key, (record, signature))
    return [item[0] for item in unique.values()]


def _summary(records: list[dict[str, Any]], candidate_id: str, *, tail_loss_pct: float) -> dict[str, Any]:
    triggered = _triggered_records(records, candidate_id)
    labeled = [
        (record, candidate)
        for record, candidate in triggered
        if candidate.get("fill_available")
        and _float(candidate.get("simulated_exit_return_pct")) is not None
        and _float(record.get("forward_return_pct")) is not None
    ]
    exit_returns = [_float(candidate.get("simulated_exit_return_pct")) for _, candidate in labeled]
    forwards = [_float(record.get("forward_return_pct")) for record, _ in labeled]
    saved = [exit_return - forward for exit_return, forward in zip(exit_returns, forwards) if exit_return is not None and forward is not None]
    return {
        "record_count": len(records),
        "trigger_count": len(triggered),
        "labeled_trigger_count": len(labeled),
        "fill_unavailable_trigger_count": sum(1 for _, candidate in triggered if not candidate.get("fill_available")),
        "avg_simulated_exit_return_pct": _avg(exit_returns),
        "avg_forward_return_pct": _avg(forwards),
        "avg_saved_vs_forward_pct": _avg(saved),
        "avg_missed_upside_pct": _avg([max(0.0, -value) for value in saved]),
        "forward_tail_loss_count": sum(1 for value in forwards if value is not None and value <= tail_loss_pct),
        "forward_tail_avoided_count": sum(
            1
            for exit_return, forward in zip(exit_returns, forwards)
            if exit_return is not None and forward is not None and forward <= tail_loss_pct and exit_return > tail_loss_pct
        ),
        "paper_research_only": True,
    }


def _walk_forward(
    records: list[dict[str, Any]],
    candidate_id: str,
    *,
    fold_count: int,
    min_labeled_triggers: int,
    tail_loss_pct: float,
) -> dict[str, Any]:
    dates = sorted({str(record.get("as_of") or "unknown_date") for record in records})
    fold_dates = _split_dates(dates, fold_count)
    folds = []
    for index, dates_in_fold in enumerate(fold_dates, start=1):
        fold_records = [record for record in records if str(record.get("as_of") or "unknown_date") in dates_in_fold]
        summary = _summary(fold_records, candidate_id, tail_loss_pct=tail_loss_pct)
        summary.update(
            {
                "fold_index": index,
                "start_date": dates_in_fold[0] if dates_in_fold else None,
                "end_date": dates_in_fold[-1] if dates_in_fold else None,
                "status": "ok" if summary["labeled_trigger_count"] >= min_labeled_triggers else "insufficient_sample",
            }
        )
        folds.append(summary)
    return {
        "fold_count": len(folds),
        "folds": folds,
        "paper_research_only": True,
    }


def _split_dates(dates: list[str], fold_count: int) -> list[list[str]]:
    if not dates:
        return []
    count = max(1, min(fold_count, len(dates)))
    base, extra = divmod(len(dates), count)
    result = []
    start = 0
    for index in range(count):
        size = base + (1 if index < extra else 0)
        result.append(dates[start : start + size])
        start += size
    return result


def _group_summary(
    records: list[dict[str, Any]],
    candidate_id: str,
    field: str,
    *,
    tail_loss_pct: float,
) -> dict[str, dict[str, Any]]:
    keys = sorted({str(record.get(field) or "unknown") for record in records})
    return {
        key: _summary(
            [record for record in records if str(record.get(field) or "unknown") == key],
            candidate_id,
            tail_loss_pct=tail_loss_pct,
        )
        for key in keys
    }


def _board_summary(records: list[dict[str, Any]], candidate_id: str, *, tail_loss_pct: float) -> dict[str, dict[str, Any]]:
    boards = sorted({board for record in records for board in _boards(record)})
    return {
        board: _summary(
            [record for record in records if board in _boards(record)],
            candidate_id,
            tail_loss_pct=tail_loss_pct,
        )
        for board in boards
    }


def _factor_summary(records: list[dict[str, Any]], candidate_id: str, *, tail_loss_pct: float) -> dict[str, dict[str, Any]]:
    factors = sorted(
        {
            str(factor)
            for _, candidate in _triggered_records(records, candidate_id)
            for factor in candidate.get("trigger_factors") or []
            if str(factor)
        }
    )
    return {
        factor: _summary(
            [
                record
                for record in records
                if factor in (((record.get("paper_exit_candidates") or {}).get(candidate_id) or {}).get("trigger_factors") or [])
            ],
            candidate_id,
            tail_loss_pct=tail_loss_pct,
        )
        for factor in factors
    }


def _triggered_records(records: list[dict[str, Any]], candidate_id: str) -> list[tuple[dict[str, Any], Mapping[str, Any]]]:
    rows = []
    for record in records:
        candidate = ((record.get("paper_exit_candidates") or {}).get(candidate_id) or {})
        if isinstance(candidate, Mapping) and candidate.get("triggered"):
            rows.append((record, candidate))
    return rows


def _concentration(triggered: list[tuple[dict[str, Any], Mapping[str, Any]]]) -> dict[str, Any]:
    unique = {}
    for index, item in enumerate(triggered):
        record, _ = item
        date = str(record.get("as_of") or record.get("_sample_date") or "")
        code = str(record.get("code") or "")
        key = (date, code) if date and code else ("__row__", str(index))
        unique.setdefault(key, item)
    triggered = list(unique.values())
    total = len(triggered)
    board_counts: Counter[str] = Counter()
    board_covered = 0
    for record, _ in triggered:
        boards = set(_boards(record))
        if boards:
            board_covered += 1
        board_counts.update(boards)
    return {
        "trigger_count": total,
        "top_date_share": _top_share([str(record.get("as_of") or "unknown_date") for record, _ in triggered], total),
        "top_board_share": _round(max(board_counts.values()) / total) if board_counts and total else None,
        "board_coverage_rate": _round(board_covered / total) if total else None,
        "top_code_share": _top_share([str(record.get("code") or "unknown_code") for record, _ in triggered], total),
        "paper_research_only": True,
    }


def _boards(record: Mapping[str, Any]) -> list[str]:
    boards = record.get("boards")
    if isinstance(boards, list) and boards:
        return [str(board) for board in boards if str(board)]
    return []


def _top_share(values: list[str], total: int) -> float | None:
    if not values or total <= 0:
        return None
    return _round(max(Counter(values).values()) / total)


def _avg(values: list[float | None]) -> float | None:
    numbers = [value for value in values if value is not None]
    return _round(sum(numbers) / len(numbers)) if numbers else None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
