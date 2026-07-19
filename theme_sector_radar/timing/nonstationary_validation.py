"""Recent-dominant windows for nonstationary paper research."""

from __future__ import annotations

from datetime import date
from collections import Counter
import math
from typing import Any, Mapping, Sequence


OBSERVED_HOLDOUT_EVIDENCE = {
    "status": "observed_evaluation_tail",
    "blind": False,
    "eligible_for_oos_claim": False,
    "reason": "strategy thresholds were observed and iterated before an immutable prospective freeze",
}

CANDIDATE_DATE_COVERAGE_FIELDS = (
    "source_document_date_count",
    "complete_candidate_date_count",
    "source_document_date_coverage_rate",
    "complete_candidate_date_coverage_rate",
    "candidate_date_coverage_status",
)


def observed_evaluation_tail_summary(
    report: Mapping[str, Any],
    *,
    allow_short_window: bool = False,
) -> dict[str, Any]:
    evidence = report.get("holdout_evidence") or {}
    if (
        evidence.get("status") != "observed_evaluation_tail"
        or evidence.get("blind") is not False
        or evidence.get("eligible_for_oos_claim") is not False
    ):
        raise ValueError("report must identify the current tail as observed and ineligible for OOS claims")
    window = (report.get("windows") or {}).get("holdout") or {}
    date_count = window.get("date_count")
    if date_count is None:
        date_count = window.get("window_date_count")
    required = {
        "date_count": date_count,
        **{field: window.get(field) for field in CANDIDATE_DATE_COVERAGE_FIELDS},
    }
    short_window = type(date_count) is int and 0 < date_count < 20
    if type(date_count) is not int or (date_count != 20 and not (allow_short_window and short_window)):
        raise ValueError("observed evaluation tail must report exactly 20 dates")
    dates = window.get("dates")
    as_of = report.get("as_of")
    try:
        parsed_as_of = date.fromisoformat(as_of) if isinstance(as_of, str) else None
        parsed_dates = [date.fromisoformat(value) for value in dates] if isinstance(dates, list) else []
    except (TypeError, ValueError) as exc:
        raise ValueError("observed evaluation tail must contain valid ISO dates") from exc
    if (
        parsed_as_of is None
        or len(parsed_dates) != date_count
        or len(set(parsed_dates)) != date_count
        or any(value > parsed_as_of for value in parsed_dates)
    ):
        raise ValueError("observed evaluation tail dates are inconsistent with date_count or as_of")
    calendar_source = report.get("calendar_source") or {}
    calendar_dates = calendar_source.get("dates") if isinstance(calendar_source, Mapping) else None
    if not isinstance(calendar_dates, list):
        raise ValueError("observed evaluation tail requires a verified calendar source")
    try:
        parsed_calendar_dates = [date.fromisoformat(value) for value in calendar_dates]
    except (TypeError, ValueError) as exc:
        raise ValueError("observed evaluation tail calendar contains invalid ISO dates") from exc
    if (
        len(parsed_calendar_dates) < date_count
        or parsed_calendar_dates != sorted(parsed_calendar_dates)
        or len(set(parsed_calendar_dates)) != len(parsed_calendar_dates)
        or any(value > parsed_as_of for value in parsed_calendar_dates)
        or dates != calendar_dates[-date_count:]
    ):
        raise ValueError("observed evaluation tail must equal the verified calendar last 20 trading dates")

    candidate_identity = _report_candidate_source_identity(report)
    source_dates = candidate_identity.get("document_dates")
    complete_dates = candidate_identity.get("complete_candidate_dates")
    if not isinstance(source_dates, list) or not isinstance(complete_dates, list):
        raise ValueError("observed evaluation tail candidate manifest date sets are missing")
    tail_dates = set(dates)
    source_date_set = set(source_dates)
    complete_date_set = set(complete_dates)
    expected_source_count = len(tail_dates & source_date_set)
    expected_complete_count = len(tail_dates & complete_date_set)
    expected_source_rate = round(expected_source_count / date_count, 4)
    expected_complete_rate = round(expected_complete_count / date_count, 4)
    if (
        required["source_document_date_count"] != expected_source_count
        or required["complete_candidate_date_count"] != expected_complete_count
        or required["source_document_date_coverage_rate"] != expected_source_rate
        or required["complete_candidate_date_coverage_rate"] != expected_complete_rate
    ):
        raise ValueError("observed evaluation tail coverage does not match the current candidate manifest")
    for field in ("source_document_date_count", "complete_candidate_date_count"):
        if type(required[field]) is not int or not 0 <= required[field] <= date_count:
            raise ValueError(f"observed evaluation tail must report {field}")
    if required["complete_candidate_date_count"] > required["source_document_date_count"]:
        raise ValueError("observed evaluation tail complete candidates must be covered by source documents")
    count_rate_pairs = (
        ("source_document_date_count", "source_document_date_coverage_rate"),
        ("complete_candidate_date_count", "complete_candidate_date_coverage_rate"),
    )
    for count_field, rate_field in count_rate_pairs:
        value = required[rate_field]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0
            or not math.isclose(
                float(value),
                required[count_field] / date_count,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise ValueError(f"observed evaluation tail must report consistent {rate_field}")
    expected_status = "ok" if required["complete_candidate_date_count"] == date_count else "insufficient"
    if short_window and required["candidate_date_coverage_status"] != "insufficient":
        raise ValueError("short observed evaluation tail must be marked insufficient")
    if required["candidate_date_coverage_status"] != expected_status:
        raise ValueError("observed evaluation tail must report candidate_date_coverage_status")
    return {
        "status": evidence["status"],
        "blind": False,
        "eligible_for_oos_claim": False,
        "reason": evidence.get("reason"),
        "required_date_count": 20,
        **required,
    }


def _report_candidate_source_identity(report: Mapping[str, Any]) -> Mapping[str, Any]:
    label_source = report.get("label_source")
    if isinstance(label_source, Mapping):
        identity = label_source.get("revalidated_candidate_source_identity")
        if isinstance(identity, Mapping) and identity.get("status") == "validated":
            return identity
    candidate_source = report.get("candidate_source")
    if isinstance(candidate_source, Mapping):
        identity = candidate_source.get("candidate_source_identity")
        if isinstance(identity, Mapping) and identity.get("status") == "validated":
            return identity
    identity = report.get("candidate_source_identity")
    if isinstance(identity, Mapping) and identity.get("status") == "validated":
        return identity
    raise ValueError("observed evaluation tail requires a validated current candidate manifest")


def observed_evaluation_tail_markdown_lines(summary: Mapping[str, Any]) -> list[str]:
    date_count = summary.get("date_count")
    return [
        f"- evaluation tail: `{summary.get('status')}`",
        f"- blind: `{str(summary.get('blind')).lower()}`",
        f"- eligible_for_oos_claim: `{str(summary.get('eligible_for_oos_claim')).lower()}`",
        f"- source document coverage: `{summary.get('source_document_date_count')}/{date_count}` "
        f"(`{summary.get('source_document_date_coverage_rate')}`)",
        f"- complete candidate coverage: `{summary.get('complete_candidate_date_count')}/{date_count}` "
        f"(`{summary.get('complete_candidate_date_coverage_rate')}`)",
        f"- candidate date coverage status: `{summary.get('candidate_date_coverage_status')}`",
    ]


def labeled_trading_dates(
    records: Sequence[Mapping[str, Any]],
    *,
    as_of: str | None = None,
) -> list[str]:
    """Return chronological dates that have an explicit forward-return label."""
    return sorted(
        {
            _date(row)
            for row in records
            if isinstance(row, Mapping)
            and row.get("forward_return_pct") is not None
            and not bool(row.get("_sample_mode") or row.get("sample_mode"))
            and _date(row)
            and _is_weekday(_date(row))
            and (not as_of or _date(row) <= as_of)
        }
    )


def build_nonstationary_windows(
    records: Sequence[Mapping[str, Any]],
    *,
    as_of: str | None = None,
    calendar_dates: Sequence[str] | None = None,
    holdout_days: int = 20,
    recent_windows: tuple[int, ...] = (60, 120),
) -> dict[str, Any]:
    rows = [dict(row) for row in records if isinstance(row, Mapping)]
    if as_of:
        rows = [row for row in rows if _date(row) and _date(row) <= as_of]
    if calendar_dates is not None:
        dates = sorted({str(value) for value in calendar_dates if str(value) and (not as_of or str(value) <= as_of)})
        calendar_source = "explicit"
    else:
        dates = labeled_trading_dates(rows, as_of=as_of)
        calendar_source = "labeled_records" if dates else "missing_labeled_records"
    holdout_count = min(max(0, holdout_days), len(dates))
    holdout_dates = dates[-holdout_count:] if holdout_count else []
    training_dates = dates[:-holdout_count] if holdout_count else dates
    report = {
        "schema_version": "timing_nonstationary_windows.v1",
        "as_of": as_of,
        "calendar_source": calendar_source,
        "holdout_evidence": dict(OBSERVED_HOLDOUT_EVIDENCE),
        "all_history": _window(rows, dates, required_days=1),
        "holdout": _window(rows, holdout_dates, required_days=holdout_days),
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    for days in recent_windows:
        selected_dates = training_dates[-days:]
        report[f"recent_{days}"] = _window(rows, selected_dates, required_days=days)
    return report


def attach_candidate_date_coverage(
    windows: Mapping[str, Any],
    *,
    source_document_dates: Sequence[str] | None,
    complete_candidate_dates: Sequence[str] | None,
) -> None:
    source_dates = set(source_document_dates or [])
    complete_dates = set(complete_candidate_dates or [])
    for item in windows.values():
        if not isinstance(item, dict) or "records" not in item:
            continue
        dates = set(item.get("dates") or [])
        date_count = len(dates)
        source_count = len(dates & source_dates)
        complete_count = len(dates & complete_dates)
        source_rate = round(source_count / date_count, 4) if date_count else None
        complete_rate = round(complete_count / date_count, 4) if date_count else None
        item.update(
            {
                "source_document_date_count": source_count,
                "complete_candidate_date_count": complete_count,
                "source_document_date_coverage_rate": source_rate,
                "complete_candidate_date_coverage_rate": complete_rate,
                "candidate_date_coverage_status": (
                    "ok"
                    if date_count > 0 and source_count == date_count and complete_count == date_count
                    else "insufficient"
                ),
            }
        )


def group_by_regime(records: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in records:
        row = dict(raw)
        regime = str(row.get("market_regime") or _regime_from_score(row.get("market_regime_score")))
        grouped.setdefault(regime, []).append(row)
    return grouped


def current_regime_summary(
    records: Sequence[Mapping[str, Any]],
    *,
    calendar_dates: Sequence[str],
) -> dict[str, Any]:
    current_date = max((str(value) for value in calendar_dates), default=None)
    labels = []
    if current_date:
        for row in records:
            if _date(row) != current_date:
                continue
            explicit = str(row.get("market_regime") or "")
            label = explicit if explicit in {"strong", "range", "weak"} else _regime_from_score(row.get("market_regime_score"))
            if label != "unknown":
                labels.append(label)
    counts = Counter(labels)
    regime = None
    if counts:
        ordered = counts.most_common()
        if len(ordered) == 1 or ordered[0][1] > ordered[1][1]:
            regime = ordered[0][0]
    return {
        "status": "ok" if regime else "insufficient",
        "date": current_date,
        "regime": regime,
        "labeled_record_count": len(labels),
    }


def concentration_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
    rows = [dict(row) for row in records]
    board_counts: dict[str, int] = {}
    board_covered = 0
    for row in rows:
        boards = set(_boards(row))
        if boards:
            board_covered += 1
        for board in boards:
            board_counts[board] = board_counts.get(board, 0) + 1
    return {
        "top_date_share": _top_share([_date(row) or "unknown" for row in rows]),
        "top_code_share": _top_share([str(row.get("code") or "unknown") for row in rows]),
        "top_board_share": round(max(board_counts.values()) / len(rows), 4) if rows and board_counts else None,
        "board_coverage_rate": round(board_covered / len(rows), 4) if rows else None,
    }


def _window(rows: list[dict[str, Any]], dates: list[str], *, required_days: int) -> dict[str, Any]:
    date_set = set(dates)
    selected = [row for row in rows if _date(row) in date_set]
    return {
        "status": "ok" if len(dates) >= required_days else "insufficient_sample",
        "date_count": len(dates),
        "record_count": len(selected),
        "dates": dates,
        "records": selected,
    }


def _date(row: Mapping[str, Any]) -> str:
    return str(row.get("as_of") or row.get("_sample_date") or row.get("date") or "")


def _is_weekday(value: str) -> bool:
    try:
        return date.fromisoformat(value).weekday() < 5
    except ValueError:
        return False


def _regime_from_score(value: Any) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if not math.isfinite(score):
        return "unknown"
    if score >= 60:
        return "strong"
    if score <= 40:
        return "weak"
    return "range"


def _boards(row: Mapping[str, Any]) -> list[str]:
    value = row.get("boards") or row.get("source_boards") or []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _top_share(values: list[str]) -> float | None:
    if not values:
        return None
    counts = {value: values.count(value) for value in set(values)}
    return round(max(counts.values()) / len(values), 4)
