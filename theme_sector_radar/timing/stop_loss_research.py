"""Paper-only negative-event sampling for stop-loss research."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from theme_sector_radar.timing.nonstationary_validation import concentration_summary


STOP_FACTOR_IDS = (
    "relative_weakness",
    "money_flow_deterioration",
    "board_synchronous_weakness",
)


def validate_stop_trigger_factor_paths(
    records: Sequence[Mapping[str, Any]],
    *,
    horizons: tuple[int, ...] = (5, 15, 30),
    fold_count: int = 5,
    min_signals: int = 30,
    continuation_tail_pct: float = -5.0,
    next_day_tail_pct: float = -5.0,
) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in records
        if isinstance(row, Mapping) and ((row.get("fixed_stop_path") or {}).get("triggered")) is True
    ]
    baseline = {
        "concentration": concentration_summary(rows),
        "by_horizon": {
            str(horizon): _stop_path_summary(
                rows,
                horizon,
                min_signals=min_signals,
                continuation_tail_pct=continuation_tail_pct,
                next_day_tail_pct=next_day_tail_pct,
            )
            for horizon in horizons
        },
        "walk_forward": _stop_walk_forward(
            rows,
            horizons=horizons,
            fold_count=fold_count,
            min_signals=min_signals,
            continuation_tail_pct=continuation_tail_pct,
            next_day_tail_pct=next_day_tail_pct,
        ),
    }
    factors = {}
    for factor_id in STOP_FACTOR_IDS:
        eligible = [
            row
            for row in rows
            if ((row.get("trigger_factor_features") or {}).get(factor_id)) is not None
        ]
        selected = [row for row in rows if ((row.get("trigger_factor_features") or {}).get(factor_id)) is True]
        eligible_baseline = {
            "concentration": concentration_summary(eligible),
            "by_horizon": {
                str(horizon): _stop_path_summary(
                    eligible,
                    horizon,
                    min_signals=min_signals,
                    continuation_tail_pct=continuation_tail_pct,
                    next_day_tail_pct=next_day_tail_pct,
                )
                for horizon in horizons
            },
            "walk_forward": _stop_walk_forward(
                eligible,
                horizons=horizons,
                fold_count=fold_count,
                min_signals=min_signals,
                continuation_tail_pct=continuation_tail_pct,
                next_day_tail_pct=next_day_tail_pct,
            ),
        }
        by_horizon = {
            str(horizon): _stop_path_summary(
                selected,
                horizon,
                min_signals=min_signals,
                continuation_tail_pct=continuation_tail_pct,
                next_day_tail_pct=next_day_tail_pct,
            )
            for horizon in horizons
        }
        factors[factor_id] = {
            "eligible_count": len(eligible),
            "signal_rate_within_eligible": _ratio(len(selected), len(eligible)),
            "concentration": concentration_summary(selected),
            "eligible_baseline": eligible_baseline,
            "by_horizon": by_horizon,
            "vs_fixed_baseline": {
                str(horizon): _stop_path_delta(by_horizon[str(horizon)], eligible_baseline["by_horizon"][str(horizon)])
                for horizon in horizons
            },
            "walk_forward": _stop_walk_forward(
                selected,
                horizons=horizons,
                fold_count=fold_count,
                min_signals=min_signals,
                continuation_tail_pct=continuation_tail_pct,
                next_day_tail_pct=next_day_tail_pct,
            ),
        }
    return {
        "schema_version": "timing_stop_trigger_factor_validation.v1",
        "parameters": {
            "horizons": list(horizons),
            "fold_count": fold_count,
            "min_signals": min_signals,
            "continuation_tail_pct": continuation_tail_pct,
            "next_day_tail_pct": next_day_tail_pct,
            "primary_label": "post_trigger_path",
            "next_day_tail_is_auxiliary": True,
        },
        "summary": {"triggered_record_count": len(rows)},
        "baseline": baseline,
        "factors": factors,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def _stop_path_summary(
    rows: list[dict[str, Any]],
    horizon: int,
    *,
    min_signals: int,
    continuation_tail_pct: float,
    next_day_tail_pct: float,
) -> dict[str, Any]:
    pairs = []
    filled_trigger_count = 0
    for row in rows:
        path = row.get("fixed_stop_path") or {}
        if path.get("next_bar_fill_available") is True and _number(path.get("next_bar_fill_return_pct")) is not None:
            filled_trigger_count += 1
        horizon_path = (path.get("horizons") or {}).get(str(horizon)) or {}
        if horizon_path.get("complete") is True:
            pairs.append((row, path, horizon_path))
    end_returns = [_number(item.get("end_return_from_entry_pct")) for _, _, item in pairs]
    maes = [_number(item.get("post_trigger_mae_pct")) for _, _, item in pairs]
    mfes = [_number(item.get("post_trigger_mfe_pct")) for _, _, item in pairs]
    fills = [_number(path.get("next_bar_fill_return_pct")) for _, path, _ in pairs]
    end_returns = [value for value in end_returns if value is not None]
    maes = [value for value in maes if value is not None]
    mfes = [value for value in mfes if value is not None]
    fills = [value for value in fills if value is not None]
    recoveries = [bool(item.get("recovered_entry")) for _, _, item in pairs if item.get("recovered_entry") is not None]
    saved_drawdown = [
        max(0.0, fill - mae)
        for (_, path, item) in pairs
        if (fill := _number(path.get("next_bar_fill_return_pct"))) is not None
        and (mae := _number(item.get("post_trigger_mae_pct"))) is not None
    ]
    missed_recovery = [
        max(0.0, mfe - fill)
        for (_, path, item) in pairs
        if (fill := _number(path.get("next_bar_fill_return_pct"))) is not None
        and (mfe := _number(item.get("post_trigger_mfe_pct"))) is not None
    ]
    next_day = [_number(row.get("next_day_return_pct")) for row, _, _ in pairs]
    next_day = [value for value in next_day if value is not None]
    return {
        "status": "ok" if len(pairs) >= min_signals else "insufficient_sample",
        "signal_count": len(rows),
        "complete_path_count": len(pairs),
        "horizon_complete_rate": _ratio(len(pairs), len(rows)),
        "avg_end_return_from_entry_pct": _average(end_returns),
        "avg_post_trigger_mae_pct": _average(maes),
        "avg_post_trigger_mfe_pct": _average(mfes),
        "recovery_rate": _ratio(sum(recoveries), len(recoveries)),
        "continuation_tail_count": sum(value <= continuation_tail_pct for value in end_returns),
        "continuation_tail_rate": _ratio(sum(value <= continuation_tail_pct for value in end_returns), len(end_returns)),
        "avg_drawdown_saved_by_next_bar_exit_pct": _average(saved_drawdown),
        "avg_missed_recovery_pct": _average(missed_recovery),
        "next_bar_fill_rate": _ratio(filled_trigger_count, len(rows)),
        "next_day_labeled_count": len(next_day),
        "next_day_tail_rate_auxiliary": _ratio(sum(value <= next_day_tail_pct for value in next_day), len(next_day)),
    }


def _stop_walk_forward(
    rows: list[dict[str, Any]],
    *,
    horizons: tuple[int, ...],
    fold_count: int,
    min_signals: int,
    continuation_tail_pct: float,
    next_day_tail_pct: float,
) -> dict[str, Any]:
    dates = sorted({str(row.get("date") or row.get("as_of") or "") for row in rows})
    folds = _split_dates(dates, fold_count)
    return {
        "fold_count": len(folds),
        "folds": [
            {
                "fold_index": index,
                "start_date": dates_in_fold[0] if dates_in_fold else None,
                "end_date": dates_in_fold[-1] if dates_in_fold else None,
                "by_horizon": {
                    str(horizon): _stop_path_summary(
                        [row for row in rows if str(row.get("date") or row.get("as_of") or "") in dates_in_fold],
                        horizon,
                        min_signals=min_signals,
                        continuation_tail_pct=continuation_tail_pct,
                        next_day_tail_pct=next_day_tail_pct,
                    )
                    for horizon in horizons
                },
            }
            for index, dates_in_fold in enumerate(folds, start=1)
        ],
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


def _stop_path_delta(candidate: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    return {
        metric: _difference(candidate.get(metric), baseline.get(metric))
        for metric in (
            "avg_end_return_from_entry_pct",
            "avg_post_trigger_mae_pct",
            "recovery_rate",
            "continuation_tail_rate",
            "avg_drawdown_saved_by_next_bar_exit_pct",
            "avg_missed_recovery_pct",
        )
    }


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _difference(left: Any, right: Any) -> float | None:
    left_value = _number(left)
    right_value = _number(right)
    return round(left_value - right_value, 4) if left_value is not None and right_value is not None else None


def build_metric_negative_sample(
    records: Sequence[Mapping[str, Any]],
    *,
    drawdown_pct: float = -3.0,
    tail_loss_pct: float = -5.0,
    close_position_pct: float = 25.0,
) -> dict[str, Any]:
    rows = [dict(row) for row in records if isinstance(row, Mapping)]
    labels_by_index = [_metric_labels(row, drawdown_pct, tail_loss_pct, close_position_pct) for row in rows]
    controls_by_date: dict[str, list[dict[str, Any]]] = {}
    for row, labels in zip(rows, labels_by_index):
        if not labels:
            controls_by_date.setdefault(str(row.get("date") or ""), []).append(row)
    offsets: dict[str, int] = {}
    events = []
    for row, labels in zip(rows, labels_by_index):
        if not labels:
            continue
        date = str(row.get("date") or "")
        controls = controls_by_date.get(date) or []
        offset = offsets.get(date, 0)
        control = controls[offset % len(controls)] if controls else None
        offsets[date] = offset + 1
        close_return = _number(row.get("close_return_pct"))
        control_return = _number(control.get("close_return_pct")) if control else None
        close_vs_vwap = _number(row.get("close_vs_vwap_pct"))
        late_amount_ratio = _number(row.get("late_amount_ratio"))
        events.append(
            {
                **row,
                "negative_labels": labels,
                "control_code": control.get("code") if control else None,
                "control_metrics": control,
                "control_unavailable": control is None,
                "factor_features": {
                    "relative_vs_control_pct": round(close_return - control_return, 4)
                    if close_return is not None and control_return is not None
                    else None,
                    "close_vs_vwap_pct": close_vs_vwap,
                    "late_amount_ratio": late_amount_ratio,
                    "money_flow_deterioration": close_vs_vwap <= -1.0 and late_amount_ratio >= 1.2
                    if close_vs_vwap is not None and late_amount_ratio is not None
                    else None,
                },
                "paper_research_only": True,
            }
        )
    return {
        "schema_version": "timing_metric_negative_sample.v1",
        "summary": {
            "record_count": len(rows),
            "negative_event_count": len(events),
            "matched_control_count": sum(not event["control_unavailable"] for event in events),
        },
        "events": events,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def _metric_labels(row: Mapping[str, Any], drawdown_pct: float, tail_loss_pct: float, close_position_pct: float) -> list[str]:
    labels = []
    if (_number(row.get("mae_pct")) or 0.0) <= drawdown_pct:
        labels.append("intraday_drawdown")
    close_return = _number(row.get("close_return_pct"))
    position = _number(row.get("close_position_pct"))
    if close_return is not None and close_return < 0 and position is not None and position <= close_position_pct:
        labels.append("close_structure_break")
    next_return = _number(row.get("next_day_return_pct"))
    if next_return is not None and next_return <= tail_loss_pct:
        labels.append("next_day_tail_loss")
    return labels


def build_stop_loss_negative_sample(
    records: Sequence[Mapping[str, Any]],
    *,
    drawdown_pct: float = -3.0,
    tail_loss_pct: float = -5.0,
) -> dict[str, Any]:
    rows = [dict(row) for row in records if isinstance(row, Mapping)]
    negatives = []
    normals = [row for row in rows if not _labels(row, drawdown_pct, tail_loss_pct)]
    for row in rows:
        labels = _labels(row, drawdown_pct, tail_loss_pct)
        if not labels:
            continue
        control = _control(row, normals)
        event = {
            "as_of": str(row.get("_sample_date") or row.get("as_of") or ""),
            "code": row.get("code"),
            "boards": _boards(row),
            "negative_labels": labels,
            "control_code": control.get("code") if control else None,
            "control_unavailable": control is None,
            "factor_evidence": _factor_evidence(row),
            "paper_research_only": True,
        }
        negatives.append(event)
    return {
        "schema_version": "timing_stop_loss_negative_sample.v1",
        "summary": {
            "record_count": len(rows),
            "negative_event_count": len(negatives),
            "matched_control_count": sum(event["control_code"] is not None for event in negatives),
        },
        "negative_events": negatives,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def _labels(row: Mapping[str, Any], drawdown_pct: float, tail_loss_pct: float) -> list[str]:
    labels = []
    prices = [_number(bar.get("low")) or _number(bar.get("price")) for bar in row.get("intraday_bars") or row.get("minute_bars") or []]
    prices = [price for price in prices if price is not None]
    entry = _number((row.get("intraday_bars") or row.get("minute_bars") or [{}])[0].get("price")) if prices else None
    if entry and min(prices) / entry * 100.0 - 100.0 <= drawdown_pct:
        labels.append("intraday_drawdown")
    if (_number(row.get("late_breakdown_risk")) or 0.0) >= 50.0:
        labels.append("close_structure_break")
    if (_number(row.get("forward_return_pct")) or 0.0) <= tail_loss_pct:
        labels.append("next_day_tail_loss")
    return labels


def _control(row: Mapping[str, Any], normals: list[dict[str, Any]]) -> dict[str, Any] | None:
    date = str(row.get("_sample_date") or row.get("as_of") or "")
    boards = set(_boards(row))
    candidates = [item for item in normals if str(item.get("_sample_date") or item.get("as_of") or "") == date]
    same_board = [item for item in candidates if boards.intersection(_boards(item))]
    return (same_board or candidates or [None])[0]


def _factor_evidence(row: Mapping[str, Any]) -> dict[str, bool | None]:
    sector = _number(row.get("sector_breadth_quality_score"))
    relative = _number(row.get("relative_resilience_score"))
    money = _number(row.get("late_breakdown_risk"))
    return {
        "sector_weakness": sector <= 40.0 if sector is not None else None,
        "relative_weakness": relative <= 40.0 if relative is not None else None,
        "money_flow_deterioration": money >= 50.0 if money is not None else None,
    }


def _boards(row: Mapping[str, Any]) -> list[str]:
    value = row.get("boards") or row.get("source_boards") or []
    return [str(item) for item in value] if isinstance(value, list) else [str(value)] if value else []


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None
