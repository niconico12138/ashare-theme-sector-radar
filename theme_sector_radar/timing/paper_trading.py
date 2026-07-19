"""Paper-only timing observation records for intraday strategy versions."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence

from theme_sector_radar.data.local_minute_archive import (
    aggregate_complete_1m_session_to_5m,
    is_expected_next_bar,
    validate_complete_a_share_session,
)
from theme_sector_radar.timing.combination_experiment import StrategyVersion, build_default_strategy_versions
from theme_sector_radar.timing.factor_exit import evaluate_factor_exit_triggers
from theme_sector_radar.timing.paper_record_identity import entry_bars_sha256


DEFAULT_PAPER_TIMING_VERSION_IDS = (
    "v31_expanded_balanced_tail_guard",
    "v32_expanded_defensive_breakdown_guard",
)


def build_timing_paper_trading_records(
    candidates: Sequence[Mapping[str, Any]],
    *,
    minute_bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    source_1m_bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    entry_date_by_code: Mapping[str, str] | None = None,
    as_of: str,
    snapshot_label: str,
    version_ids: Sequence[str] = DEFAULT_PAPER_TIMING_VERSION_IDS,
    concentration_threshold: int = 2,
    factor_exit_peak_giveback_pct: float = 2.0,
    bar_interval: str | None = None,
    bar_source: str | None = None,
) -> dict[str, Any]:
    versions = _select_versions(version_ids)
    minute_bars_by_code = minute_bars_by_code or {}
    source_1m_bars_by_code = source_1m_bars_by_code or {}
    entry_date_by_code = entry_date_by_code or {}
    rows = [dict(candidate) for candidate in candidates]
    matched: list[dict[str, Any]] = []
    for row in rows:
        for version in versions:
            if all(condition.matches(row) for condition in version.conditions):
                matched.append(
                    _build_record(
                        row,
                        version,
                        bars=list(minute_bars_by_code.get(str(row.get("code") or "")) or []),
                        source_1m_bars=list(source_1m_bars_by_code.get(str(row.get("code") or "")) or []),
                        entry_date=str(entry_date_by_code.get(str(row.get("code") or "")) or ""),
                        as_of=as_of,
                        snapshot_label=snapshot_label,
                        factor_exit_peak_giveback_pct=factor_exit_peak_giveback_pct,
                        bar_interval=bar_interval,
                        bar_source=bar_source,
                    )
                )
    _apply_concentration_tags(matched, threshold=concentration_threshold)
    return {
        "schema_version": "timing_paper_trading_records.v1",
        "as_of": as_of,
        "snapshot_label": snapshot_label,
        "summary": {
            "candidate_count": len(rows),
            "record_count": len(matched),
            "labeled_record_count": sum(1 for record in matched if record.get("forward_return_pct") is not None),
            "causal_entry_valid_count": sum(1 for record in matched if record.get("causal_entry_valid")),
            "version_counts": dict(Counter(record["timing_version_id"] for record in matched)),
            "risk_tag_counts": dict(Counter(tag for record in matched for tag in record.get("paper_risk_tags") or [])),
        },
        "records": matched,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def _select_versions(version_ids: Sequence[str]) -> list[StrategyVersion]:
    versions_by_id = {version.version_id: version for version in build_default_strategy_versions()}
    missing = [version_id for version_id in version_ids if version_id not in versions_by_id]
    if missing:
        raise ValueError(f"Unknown strategy version ids: {', '.join(missing)}")
    return [versions_by_id[version_id] for version_id in version_ids]


def _build_record(
    candidate: Mapping[str, Any],
    version: StrategyVersion,
    *,
    bars: list[Mapping[str, Any]],
    source_1m_bars: list[Mapping[str, Any]],
    entry_date: str,
    as_of: str,
    snapshot_label: str,
    factor_exit_peak_giveback_pct: float,
    bar_interval: str | None,
    bar_source: str | None,
) -> dict[str, Any]:
    normalized_bars = _normalize_bars(bars)
    normalized_source_1m_bars = _normalize_bars(source_1m_bars)
    expected_interval = {"1m": 1, "5m": 5}.get(str(bar_interval or ""))
    complete_session = bool(
        expected_interval
        and validate_complete_a_share_session(normalized_bars, interval_minutes=expected_interval)
    )
    base_entry_valid = bool(
        entry_date
        and entry_date > as_of
        and normalized_bars
        and all(_bar_date(row) == entry_date for row in normalized_bars)
        and complete_session
    )
    source_1m_binding_valid = _source_1m_binding_valid(
        normalized_source_1m_bars,
        normalized_bars,
        bar_interval=bar_interval,
    )
    causal_entry_valid = base_entry_valid and source_1m_binding_valid
    causal_bars = normalized_bars if causal_entry_valid else []
    derived_path_fields = derive_paper_record_path_fields(
        causal_bars,
        factor_exit_peak_giveback_pct=factor_exit_peak_giveback_pct,
        bar_interval=bar_interval,
    )
    path_stats = derived_path_fields["path_stats"]
    invalid_reasons = _causal_entry_invalid_reasons(
        signal_date=as_of,
        entry_date=entry_date,
        bars=normalized_bars,
        complete_session=complete_session,
    )
    if base_entry_valid and not source_1m_binding_valid:
        invalid_reasons.append("source_1m_identity_invalid")
    record = {
        "schema_version": "timing_paper_trading_record.v1",
        "as_of": as_of,
        "signal_date": as_of,
        "entry_date": entry_date or None,
        "causal_entry_valid": causal_entry_valid,
        "causal_entry_invalid_reasons": invalid_reasons,
        "entry_bars": causal_bars,
        "entry_bars_sha256": entry_bars_sha256(causal_bars) if causal_bars else None,
        "snapshot_label": snapshot_label,
        "code": candidate.get("code"),
        "name": candidate.get("name"),
        "boards": _boards(candidate),
        "forward_return_pct": path_stats.get("close_return_pct") if causal_entry_valid else None,
        "timing_version_id": version.version_id,
        "timing_version_description": version.description,
        "paper_action_state": "watch_only",
        "paper_risk_tags": [],
        **derived_path_fields,
        "execution_assumptions": {
            "signal_available": "after_signal_session_close",
            "entry_model": "next_trading_session_first_bar_open",
            "fill_model": "next_contiguous_bar_open_when_available",
            "bar_interval": bar_interval,
            "bar_source": bar_source,
            "factor_exit_peak_giveback_pct": _round(factor_exit_peak_giveback_pct),
            "paper_research_only": True,
        },
        "factor_snapshot": _factor_snapshot(candidate),
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    if causal_entry_valid:
        record["selection_forward_return_pct"] = _round(_float(candidate.get("forward_return_pct")))
        if bar_interval == "5m":
            record["source_1m_bars"] = normalized_source_1m_bars
            record["source_1m_bars_sha256"] = entry_bars_sha256(normalized_source_1m_bars)
    return record


def _source_1m_binding_valid(
    source_1m_bars: list[Mapping[str, Any]],
    entry_bars: list[Mapping[str, Any]],
    *,
    bar_interval: str | None,
) -> bool:
    if bar_interval != "5m":
        return True
    if not validate_complete_a_share_session(source_1m_bars, interval_minutes=1):
        return False
    return aggregate_complete_1m_session_to_5m(source_1m_bars) == entry_bars


def derive_paper_record_path_fields(
    bars: list[Mapping[str, Any]],
    *,
    factor_exit_peak_giveback_pct: float,
    bar_interval: str,
) -> dict[str, Any]:
    normalized_bars = _normalize_bars(bars)
    path_stats = _path_stats(normalized_bars)
    entry_price = _float(path_stats.get("entry_reference_price"))
    factor_exit_triggers = evaluate_factor_exit_triggers(
        normalized_bars,
        entry_price=entry_price or 0.0,
        protect_peak_giveback_pct=factor_exit_peak_giveback_pct,
    )
    return {
        "path_stats": path_stats,
        "exit_research": _exit_research(path_stats),
        "factor_exit_triggers": factor_exit_triggers,
        "paper_exit_candidates": _paper_exit_candidates(
            factor_exit_triggers,
            normalized_bars,
            entry_price,
            bar_interval=bar_interval,
        ),
        "exit_data_quality": _exit_data_quality(
            normalized_bars,
            interval_minutes={"1m": 1, "5m": 5}.get(bar_interval),
        ),
    }


def _paper_exit_candidates(
    factor_exit_triggers: Mapping[str, Any],
    bars: list[Mapping[str, Any]],
    entry_price: float | None,
    *,
    bar_interval: str | None,
) -> dict[str, Any]:
    strategies = factor_exit_triggers.get("strategies") or {}
    return {
        "paper_fixed_exit_baseline": _paper_exit_candidate(
            strategies.get("exit_v1_fixed") or {},
            "exit_v1_fixed",
            bars,
            entry_price,
            bar_interval,
        ),
        "paper_take_profit_protect_candidate": _paper_exit_candidate(
            strategies.get("exit_v4_confirmed_factor_protect") or {},
            "exit_v4_confirmed_factor_protect",
            bars,
            entry_price,
            bar_interval,
        ),
        "paper_stop_loss_risk_candidate": _paper_exit_candidate(
            strategies.get("exit_v5_factor_risk_confirmed") or {},
            "exit_v5_factor_risk_confirmed",
            bars,
            entry_price,
            bar_interval,
        ),
    }


def _paper_exit_candidate(
    strategy: Mapping[str, Any],
    strategy_id: str,
    bars: list[Mapping[str, Any]],
    entry_price: float | None,
    bar_interval: str | None,
) -> dict[str, Any]:
    fill_price = (
        _next_bar_fill_price(
            bars,
            str(strategy.get("trigger_time") or ""),
            bar_interval,
        )
        if strategy.get("triggered")
        else None
    )
    return {
        "strategy_id": strategy_id,
        "candidate_kind": strategy.get("paper_candidate_kind"),
        "triggered": bool(strategy.get("triggered")),
        "trigger_time": strategy.get("trigger_time"),
        "trigger_factors": list(strategy.get("trigger_factors") or []),
        "fill_available": fill_price is not None,
        "simulated_exit_price": _round(fill_price),
        "simulated_exit_return_pct": _round((fill_price - entry_price) / entry_price * 100.0)
        if fill_price is not None and entry_price is not None and entry_price > 0
        else None,
        "paper_research_only": True,
    }


def _next_bar_fill_price(
    bars: list[Mapping[str, Any]],
    trigger_time: str,
    bar_interval: str | None,
) -> float | None:
    interval = {"1m": 1, "5m": 5}.get(str(bar_interval or ""))
    if interval is None or not trigger_time:
        return None
    rows = _normalize_bars(bars)
    for index, row in enumerate(rows):
        if str(row.get("time") or row.get("date") or "") != trigger_time:
            continue
        if index + 1 >= len(rows) or not is_expected_next_bar(row, rows[index + 1], interval):
            return None
        next_row = rows[index + 1]
        return _float(next_row.get("open"))
    return None


def _exit_data_quality(
    bars: list[Mapping[str, Any]],
    *,
    interval_minutes: int | None,
) -> dict[str, Any]:
    rows = [dict(row) for row in bars if isinstance(row, Mapping)]
    times = [str(row.get("time") or row.get("date") or "") for row in rows]
    return {
        "bar_count": len(rows),
        "chronological": times == sorted(times),
        "missing_price_bar_count": sum(1 for row in rows if _price(row) is None),
        "complete_a_share_session": bool(
            interval_minutes
            and validate_complete_a_share_session(rows, interval_minutes=interval_minutes)
        ),
        "paper_research_only": True,
    }


def _causal_entry_invalid_reasons(
    *,
    signal_date: str,
    entry_date: str,
    bars: list[Mapping[str, Any]],
    complete_session: bool,
) -> list[str]:
    reasons = []
    if not entry_date:
        reasons.append("entry_date_missing")
    elif entry_date <= signal_date:
        reasons.append("entry_date_not_after_signal")
    if not bars:
        reasons.append("entry_bars_missing")
    elif any(_bar_date(row) != entry_date for row in bars):
        reasons.append("entry_bar_date_mismatch")
    if bars and not complete_session:
        reasons.append("entry_session_incomplete")
    return reasons


def _apply_concentration_tags(records: list[dict[str, Any]], *, threshold: int) -> None:
    counts: Counter[str] = Counter()
    unique_entries: dict[tuple[str, str, str], set[str]] = {}
    for record in records:
        key = (
            str(record.get("signal_date") or record.get("as_of") or ""),
            str(record.get("entry_date") or ""),
            str(record.get("code") or ""),
        )
        unique_entries.setdefault(key, set()).update(record.get("boards") or ["unknown_board"])
    for (signal_date, _, _), boards in unique_entries.items():
        for board in boards:
            counts[f"{signal_date}|{board}"] += 1
    for record in records:
        tags = list(record.get("paper_risk_tags") or [])
        max_group_count = 0
        for board in record.get("boards") or ["unknown_board"]:
            group_count = counts.get(f"{record.get('as_of')}|{board}", 0)
            max_group_count = max(max_group_count, group_count)
        if max_group_count >= threshold:
            tags.append("same_day_board_concentration")
        if max_group_count >= max(threshold + 1, 3):
            tags.append("same_day_board_strong_concentration")
        record["paper_risk_tags"] = sorted(set(tags))
        record["concentration_snapshot"] = {
            "max_same_day_board_trigger_count": max_group_count,
            "concentration_threshold": threshold,
            "paper_research_only": True,
        }


def _path_stats(bars: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = _normalize_bars(bars)
    if not rows:
        return {
            "entry_reference_price": None,
            "max_favorable_excursion_pct": None,
            "max_adverse_excursion_pct": None,
            "close_return_pct": None,
            "bar_count": 0,
            "paper_research_only": True,
        }
    entry = _float(rows[0].get("open")) or _price(rows[0])
    if entry is None or entry <= 0:
        return {
            "entry_reference_price": None,
            "max_favorable_excursion_pct": None,
            "max_adverse_excursion_pct": None,
            "close_return_pct": None,
            "bar_count": len(rows),
            "paper_research_only": True,
        }
    highs = [_float(row.get("high")) or _price(row) for row in rows]
    lows = [_float(row.get("low")) or _price(row) for row in rows]
    closes = [_price(row) for row in rows]
    max_high = max(value for value in highs if value is not None)
    min_low = min(value for value in lows if value is not None)
    last_close = next((value for value in reversed(closes) if value is not None), None)
    return {
        "entry_reference_price": _round(entry),
        "max_favorable_excursion_pct": _round((max_high - entry) / entry * 100.0),
        "max_adverse_excursion_pct": _round((min_low - entry) / entry * 100.0),
        "close_return_pct": _round((last_close - entry) / entry * 100.0) if last_close is not None else None,
        "bar_count": len(rows),
        "paper_research_only": True,
    }


def _exit_research(path_stats: Mapping[str, Any]) -> dict[str, Any]:
    mfe = _float(path_stats.get("max_favorable_excursion_pct"))
    mae = _float(path_stats.get("max_adverse_excursion_pct"))
    close_return = _float(path_stats.get("close_return_pct"))
    return {
        "stop_loss_hit_3pct": bool(mae is not None and mae <= -3.0),
        "stop_loss_hit_5pct": bool(mae is not None and mae <= -5.0),
        "take_profit_hit_3pct": bool(mfe is not None and mfe >= 3.0),
        "take_profit_hit_5pct": bool(mfe is not None and mfe >= 5.0),
        "take_profit_hit_8pct": bool(mfe is not None and mfe >= 8.0),
        "close_return_pct": close_return,
        "paper_research_only": True,
    }


def _factor_snapshot(candidate: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "late_amount_surge_score",
        "failed_breakout_risk",
        "late_breakdown_risk",
        "weak_close_after_volume_risk",
        "execution_tradeability_score",
        "execution_turnover_depth_score",
        "sector_breadth_quality_score",
        "market_regime_score",
    )
    return {field: _round(_float(candidate.get(field))) for field in fields if candidate.get(field) is not None}


def _normalize_bars(bars: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted([dict(row) for row in bars if isinstance(row, Mapping)], key=lambda row: str(row.get("time") or row.get("date") or ""))


def _bar_date(row: Mapping[str, Any]) -> str:
    raw = "".join(character for character in str(row.get("time") or row.get("date") or "") if character.isdigit())
    if len(raw) < 8:
        return ""
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _boards(candidate: Mapping[str, Any]) -> list[str]:
    raw = candidate.get("boards") or candidate.get("source_boards")
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item)]
    if isinstance(raw, str) and raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _price(row: Mapping[str, Any]) -> float | None:
    for key in ("price", "close", "latest_price"):
        value = _float(row.get(key))
        if value is not None:
            return value
    return None


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
