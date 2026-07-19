#!/usr/bin/env python
"""Evaluate legacy, membership-only, and linkage V2 stock paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.strict_json import (  # noqa: E402
    load_strict_json,
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)
from theme_sector_radar.data.trading_calendar import load_trading_calendar  # noqa: E402


HORIZONS = ("1d", "3d", "5d")
FORWARD_LABEL_CONTRACT = {
    "schema_version": "forward-return-label-contract-v2",
    "frequency": "1d",
    "adjustment": "qfq",
    "target_date_basis": "versioned_exchange_calendar",
}


def _canonical_sha256(document: Mapping[str, Any]) -> str:
    payload = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _pit_source_manifest_sha256(
    dates: list[str],
    reports_by_date: Mapping[str, Mapping[str, Any]],
    forward_by_date: Mapping[str, Mapping[str, Any]],
) -> str:
    manifest = [
        {
            "date": day,
            "unified_payload_sha256": _canonical_sha256(reports_by_date[day]),
            "forward_payload_sha256": _canonical_sha256(forward_by_date[day]),
        }
        for day in dates
    ]
    return _canonical_sha256({"documents": manifest})


def _finite(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _dedupe(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_code = {}
    for source in rows:
        code = str(source.get("code") or "").strip()
        if code and code not in by_code:
            by_code[code] = dict(source)
    return list(by_code.values())


def _groups(report: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    research = report.get("linkage_research", {})
    cluster_contract = (
        research.get("sector_cluster_map", {})
        if isinstance(research, Mapping)
        else {}
    )
    cluster_map = (
        cluster_contract.get("mapping", {})
        if isinstance(cluster_contract, Mapping)
        else {}
    )

    def attach_clusters(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for row in rows:
            sector_name = str(row.get("sector_name") or "").strip()
            row["sector_cluster"] = cluster_map.get(
                sector_name, "__unmapped__"
            )
        return rows

    legacy = attach_clusters(_dedupe(
        list(report.get("trend_candidates_all", []))
        + list(report.get("burst_candidates_all", []))
    ))
    membership = attach_clusters(
        _dedupe(list(report.get("direction_shadow_candidates_all", [])))
    )
    selection = report.get("direction_linkage_v2_selection_shadow", {})
    linkage = (
        attach_clusters(_dedupe(list(selection.get("selected", []))))
        if isinstance(selection, Mapping)
        else []
    )
    return {"A_legacy": legacy, "B_membership_only": membership, "C_linkage_v2": linkage}


def _cluster_contract_identity(
    report: Mapping[str, Any],
) -> tuple[str, str] | None:
    research = report.get("linkage_research", {})
    contract = (
        research.get("sector_cluster_map", {})
        if isinstance(research, Mapping)
        else {}
    )
    if not isinstance(contract, Mapping) or contract.get("status") != "ok":
        return None
    source_sha = str(contract.get("sha256") or "")
    mapping_sha = str(contract.get("mapping_sha256") or "")
    mapping = contract.get("mapping")
    if (
        len(source_sha) != 64
        or len(mapping_sha) != 64
        or not isinstance(mapping, Mapping)
        or not mapping
        or _canonical_sha256(mapping) != mapping_sha
    ):
        return None
    return source_sha, mapping_sha


def _forward_map(document: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    contract = document.get("label_contract")
    metadata_by_code = document.get("label_metadata")
    metadata_by_code = metadata_by_code if isinstance(metadata_by_code, Mapping) else {}
    if isinstance(document.get("forward_returns"), Mapping):
        return {
            str(code).strip(): {
                **dict(values),
                "__label_contract__": contract,
                "__label_metadata__": metadata_by_code.get(str(code).strip()),
            }
            for code, values in document["forward_returns"].items()
            if str(code).strip() and isinstance(values, Mapping)
        }
    items = document.get("items", [])
    if not isinstance(items, list):
        raise ValueError("forward return items must be an array")
    return {
        str(item.get("code") or "").strip(): {
            **dict(item),
            "__label_contract__": contract,
            "__label_metadata__": metadata_by_code.get(
                str(item.get("code") or "").strip()
            ),
        }
        for item in items
        if isinstance(item, Mapping) and str(item.get("code") or "").strip()
    }


def _validate_day_identity(
    day: str,
    report: Mapping[str, Any],
    forward: Mapping[str, Any],
    *,
    report_file_sha256: str | None,
) -> None:
    try:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"invalid evaluation date key: {day}") from exc
    if report.get("as_of_date") != day:
        raise ValueError(f"unified report as_of date mismatch for {day}")
    if forward.get("as_of") != day:
        raise ValueError(f"forward as_of date mismatch for {day}")
    candidate_input = forward.get("candidate_input")
    if not isinstance(candidate_input, Mapping):
        raise ValueError(f"forward candidate input identity is missing for {day}")
    basis = candidate_input.get("sha256_basis")
    expected = None
    if basis == "canonical_json_payload_v1":
        expected = _canonical_sha256(report)
    elif basis == "raw_utf8_file_bytes":
        expected = str(report_file_sha256 or "").lower()
    actual = str(candidate_input.get("sha256") or "").lower()
    if not expected or actual != expected:
        raise ValueError(f"candidate input SHA mismatch for {day}")


def _calendar_targets(
    document: Mapping[str, Any], *, signal_date: str
) -> dict[str, str | None] | None:
    calendar = document.get("trading_calendar")
    if not isinstance(calendar, Mapping):
        return None
    raw_dates = calendar.get("dates")
    if not isinstance(raw_dates, list):
        return None
    try:
        dates = [date.fromisoformat(str(value)).isoformat() for value in raw_dates]
    except ValueError:
        return None
    if dates != raw_dates or dates != sorted(dates) or len(dates) != len(set(dates)):
        return None
    if signal_date not in dates:
        return None
    sha256 = str(calendar.get("sha256") or "")
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        return None
    signal_index = dates.index(signal_date)
    return {
        horizon: (
            dates[signal_index + int(horizon[:-1])]
            if signal_index + int(horizon[:-1]) < len(dates)
            else None
        )
        for horizon in HORIZONS
    }


def _validate_forward_bar_snapshots(
    document: Mapping[str, Any], *, signal_date: str
) -> None:
    """Recompute every persisted bar snapshot when the v2 manifest is present."""
    metadata_by_code = document.get("label_metadata") or {}
    source_manifest = document.get("source_bar_manifest") or {}
    for raw_code, metadata in metadata_by_code.items():
        code = str(raw_code).strip()
        source = source_manifest.get(code)
        if not isinstance(metadata, Mapping) or not isinstance(source, Mapping):
            continue
        normalized = source.get("normalized_bars")
        if normalized is None:
            # Compatibility for pre-v2 hand-authored fixtures. All generated
            # forward documents carry normalized_bars and are checked below.
            continue
        if source.get("stock_code", code) != code:
            raise ValueError(f"{signal_date}.{code} stock identity mismatch")
        if not isinstance(normalized, list):
            raise ValueError(f"{signal_date}.{code} normalized bars are invalid")
        previous = None
        for bar in normalized:
            if not isinstance(bar, Mapping):
                raise ValueError(f"{signal_date}.{code} normalized bar is invalid")
            day = str(bar.get("date") or "")
            try:
                parsed = date.fromisoformat(day)
            except ValueError as exc:
                raise ValueError(f"{signal_date}.{code} normalized bar date is invalid") from exc
            if parsed.isoformat() != day or (previous is not None and day <= previous):
                raise ValueError(f"{signal_date}.{code} normalized bar dates are not sorted")
            previous = day
            close = bar.get("close")
            if close is not None and _finite(close, field=f"{signal_date}.{code}.close") <= 0:
                raise ValueError(f"{signal_date}.{code} normalized close is not positive")
        expected_sha = _canonical_sha256(
            {
                "stock_code": code,
                "frequency": "1d",
                "adjustment": "qfq",
                "bars": normalized,
            }
        )
        if source.get("bar_snapshot_sha256") != expected_sha or metadata.get(
            "bar_snapshot_sha256"
        ) != expected_sha:
            raise ValueError(f"{signal_date}.{code} bar snapshot SHA mismatch")
        if source.get("bar_count") != len(normalized):
            raise ValueError(f"{signal_date}.{code} bar count mismatch")
        query = source.get("query")
        if not isinstance(query, Mapping):
            raise ValueError(f"{signal_date}.{code} source query is missing")
        if (
            query.get("frequency") != "1d"
            or query.get("adjustment") != "qfq"
            or query.get("projected_fields")
            != ["date", "code", "close", "open"]
        ):
            raise ValueError(f"{signal_date}.{code} source query identity mismatch")
        try:
            start = date.fromisoformat(str(query.get("start") or ""))
            end = date.fromisoformat(str(query.get("end") or ""))
        except ValueError as exc:
            raise ValueError(f"{signal_date}.{code} source query dates are invalid") from exc
        if start.isoformat() != str(query.get("start")) or end.isoformat() != str(query.get("end")):
            raise ValueError(f"{signal_date}.{code} source query dates are non-canonical")
        if start > end or any(
            day < start.isoformat() or day > end.isoformat()
            for day in [bar["date"] for bar in normalized]
        ):
            raise ValueError(f"{signal_date}.{code} source query range mismatch")
        by_date = {bar["date"]: bar.get("close") for bar in normalized}
        if metadata.get("signal_close") != by_date.get(signal_date):
            raise ValueError(f"{signal_date}.{code} signal close snapshot mismatch")
        for horizon, horizon_metadata in (metadata.get("horizons") or {}).items():
            if not isinstance(horizon_metadata, Mapping):
                continue
            target = horizon_metadata.get("target_trading_date")
            if target and target in by_date and horizon_metadata.get("target_close") != by_date[target]:
                raise ValueError(f"{signal_date}.{code}.{horizon} target close snapshot mismatch")


def _forward_document_contract_verified(
    document: Mapping[str, Any],
    *,
    signal_date: str,
    expected_trading_calendar: Mapping[str, Any] | None = None,
) -> bool:
    if document.get("label_contract") != FORWARD_LABEL_CONTRACT:
        return False
    metadata_by_code = document.get("label_metadata")
    source_manifest = document.get("source_bar_manifest")
    targets = _calendar_targets(document, signal_date=signal_date)
    if (
        not isinstance(metadata_by_code, Mapping)
        or not isinstance(source_manifest, Mapping)
        or targets is None
    ):
        return False
    if expected_trading_calendar is not None:
        recorded_calendar = document.get("trading_calendar")
        if not isinstance(recorded_calendar, Mapping):
            return False
        for field in (
            "dates",
            "source",
            "sha256",
            "requested_start",
            "requested_end",
        ):
            if recorded_calendar.get(field) != expected_trading_calendar.get(field):
                return False
    forward = _forward_map(document)
    for code, item in forward.items():
        metadata = item.get("__label_metadata__")
        source = source_manifest.get(code)
        if not isinstance(metadata, Mapping) or not isinstance(source, Mapping):
            return False
        bar_sha = str(metadata.get("bar_snapshot_sha256") or "")
        if (
            len(bar_sha) != 64
            or source.get("bar_snapshot_sha256") != bar_sha
            or metadata.get("signal_date") != signal_date
            or metadata.get("frequency") != "1d"
            or metadata.get("adjustment") != "qfq"
        ):
            return False
        query = source.get("query")
        if not isinstance(query, Mapping) or query.get("adjustment") != "qfq":
            return False
        latest = metadata.get("source_latest_bar_date")
        try:
            latest_date = date.fromisoformat(str(latest)) if latest else None
        except ValueError:
            return False
        horizons = metadata.get("horizons")
        if not isinstance(horizons, Mapping):
            return False
        for horizon in HORIZONS:
            horizon_metadata = horizons.get(horizon)
            if not isinstance(horizon_metadata, Mapping):
                return False
            expected_target = targets[horizon]
            if horizon_metadata.get("target_trading_date") != expected_target:
                return False
            expected_mature = bool(
                expected_target
                and latest_date is not None
                and latest_date >= date.fromisoformat(expected_target)
            )
            if horizon_metadata.get("mature") is not expected_mature:
                return False
            value = item.get(horizon)
            available = horizon_metadata.get("return_available") is True
            if available != (value is not None):
                return False
            if available and _verified_forward_value(
                item,
                signal_date=signal_date,
                horizon=horizon,
                field=f"{signal_date}.{code}.{horizon}",
            ) is None:
                return False
    return True


def _verified_forward_value(
    item: Mapping[str, Any] | None,
    *,
    signal_date: str,
    horizon: str,
    field: str,
) -> float | None:
    if not isinstance(item, Mapping):
        return None
    if item.get("__label_contract__") != FORWARD_LABEL_CONTRACT:
        return None
    metadata = item.get("__label_metadata__")
    if not isinstance(metadata, Mapping):
        return None
    if (
        metadata.get("signal_date") != signal_date
        or metadata.get("frequency") != "1d"
        or metadata.get("adjustment") != "qfq"
    ):
        return None
    horizons = metadata.get("horizons")
    horizon_metadata = horizons.get(horizon) if isinstance(horizons, Mapping) else None
    if not isinstance(horizon_metadata, Mapping):
        return None
    try:
        horizon_days = int(horizon[:-1])
        target_date = date.fromisoformat(
            str(horizon_metadata.get("target_trading_date") or "")
        )
        signal = date.fromisoformat(signal_date)
    except (TypeError, ValueError):
        return None
    if (
        horizon_metadata.get("horizon_trading_days") != horizon_days
        or horizon_metadata.get("mature") is not True
        or horizon_metadata.get("return_available") is not True
        or target_date <= signal
    ):
        return None
    value = item.get(horizon)
    if value is None:
        return None
    signal_close = _finite(metadata.get("signal_close"), field=f"{field}.signal_close")
    target_close = _finite(
        horizon_metadata.get("target_close"), field=f"{field}.target_close"
    )
    if signal_close <= 0 or target_close <= 0:
        raise ValueError(f"{field} source closes must be positive")
    observed = _finite(value, field=field)
    recomputed = round((target_close - signal_close) / signal_close * 100.0, 4)
    if not math.isclose(observed, recomputed, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"{field} does not match source closes")
    return observed


def _turnover(code_sets: list[set[str]]) -> float | None:
    if len(code_sets) < 2:
        return None
    values = []
    for previous, current in zip(code_sets, code_sets[1:]):
        denominator = max(len(previous), len(current), 1)
        values.append(1.0 - len(previous & current) / denominator)
    return sum(values) / len(values)


def _max_drawdown(daily_returns_pct: list[float]) -> float | None:
    if not daily_returns_pct:
        return None
    equity = peak = 1.0
    drawdown = 0.0
    for value in daily_returns_pct:
        equity *= 1.0 + value / 100.0
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1.0)
    return drawdown * 100.0


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _linkage_status(row: Mapping[str, Any]) -> str:
    linkage = row.get("linkage_v2_shadow")
    if not isinstance(linkage, Mapping):
        return "missing"
    return str(linkage.get("status") or "missing")


def _component_status_counts(rows: list[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter] = {}
    for row in rows:
        linkage = row.get("linkage_v2_shadow")
        components = linkage.get("components", {}) if isinstance(linkage, Mapping) else {}
        if not isinstance(components, Mapping):
            continue
        for name, component in components.items():
            if not isinstance(component, Mapping):
                continue
            status = str(component.get("status") or "missing")
            counts.setdefault(str(name), Counter())[status] += 1
    return {
        name: dict(sorted(statuses.items()))
        for name, statuses in sorted(counts.items())
    }


def _paired_daily_difference(
    a_rows: list[Mapping[str, Any]],
    c_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    a_by_date = {str(row["date"]): float(row["mean_return_pct"]) for row in a_rows}
    c_by_date = {str(row["date"]): float(row["mean_return_pct"]) for row in c_rows}
    common_dates = sorted(set(a_by_date) & set(c_by_date))
    daily = [
        {
            "date": day,
            "a_mean_return_pct": a_by_date[day],
            "c_mean_return_pct": c_by_date[day],
            "c_minus_a_pct": c_by_date[day] - a_by_date[day],
        }
        for day in common_dates
    ]
    differences = [row["c_minus_a_pct"] for row in daily]
    worst = min(daily, key=lambda row: row["c_minus_a_pct"]) if daily else None
    return {
        "observation_count": len(daily),
        "mean_difference_pct": _mean(differences),
        "positive_difference_ratio": (
            sum(value > 0 for value in differences) / len(differences)
            if differences
            else None
        ),
        "worst_date": worst["date"] if worst else None,
        "worst_difference_pct": worst["c_minus_a_pct"] if worst else None,
        "daily_differences": daily,
    }


def _strict_pit_evidence_verified(
    evidence: Any,
    dates: list[str],
    reports_by_date: Mapping[str, Mapping[str, Any]],
    forward_by_date: Mapping[str, Mapping[str, Any]],
) -> bool:
    # Stage 1 has no independently trusted verifier or signed historical
    # constituent-universe manifest. Caller-authored evidence cannot promote.
    return False


def _self_attested_pit_evidence_shape_valid(
    evidence: Any,
    dates: list[str],
    reports_by_date: Mapping[str, Mapping[str, Any]],
    forward_by_date: Mapping[str, Mapping[str, Any]],
) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    if evidence.get("schema_version") != "stock_sector_linkage_pit_evidence.v1":
        return False
    if evidence.get("status") != "verified":
        return False
    if evidence.get("document_dates") != dates:
        return False
    for day in dates:
        report = reports_by_date.get(day, {})
        forward = forward_by_date.get(day, {})
        if report.get("as_of_date") != day or forward.get("as_of") != day:
            return False
    return evidence.get("source_manifest_sha256") == _pit_source_manifest_sha256(
        dates,
        reports_by_date,
        forward_by_date,
    )


def evaluate_linkage_paths(
    reports_by_date: Mapping[str, Mapping[str, Any]],
    forward_by_date: Mapping[str, Mapping[str, Any]],
    *,
    strict_pit_evidence: Any = None,
    historical_constituent_universe_versioned: bool = False,
    report_file_sha256_by_date: Mapping[str, str] | None = None,
    expected_trading_calendar: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    dates = sorted(reports_by_date)
    if set(forward_by_date) != set(dates):
        raise ValueError("unified and forward date sets must match exactly")
    report_file_sha256_by_date = report_file_sha256_by_date or {}
    for day in dates:
        _validate_day_identity(
            day,
            reports_by_date[day],
            forward_by_date[day],
            report_file_sha256=report_file_sha256_by_date.get(day),
        )
        _validate_forward_bar_snapshots(forward_by_date[day], signal_date=day)
    cluster_identities = [
        _cluster_contract_identity(reports_by_date[day]) for day in dates
    ]
    cluster_map_consistent = bool(cluster_identities) and all(
        identity is not None and identity == cluster_identities[0]
        for identity in cluster_identities
    )
    strict_pit_eligible = _strict_pit_evidence_verified(
        strict_pit_evidence,
        dates,
        reports_by_date,
        forward_by_date,
    )
    self_attested_pit_shape_valid = _self_attested_pit_evidence_shape_valid(
        strict_pit_evidence,
        dates,
        reports_by_date,
        forward_by_date,
    )
    forward_label_maturity_verified = bool(dates) and all(
        _forward_document_contract_verified(
            forward_by_date.get(day, {}),
            signal_date=day,
            expected_trading_calendar=expected_trading_calendar,
        )
        for day in dates
    )
    group_names = ("A_legacy", "B_membership_only", "C_linkage_v2")
    accumulators = {
        group: {
            "candidate_count": [],
            "code_sets": [],
            "max_cluster_share": [],
            "max_sector_share": [],
            "daily": {horizon: [] for horizon in HORIZONS},
            "selected": {horizon: 0 for horizon in HORIZONS},
            "labeled": {horizon: 0 for horizon in HORIZONS},
            "positive_labels": {horizon: 0 for horizon in HORIZONS},
        }
        for group in group_names
    }
    universe_daily = {horizon: [] for horizon in HORIZONS}
    all_linkage_rows: list[Mapping[str, Any]] = []
    selected_linkage_rows: list[Mapping[str, Any]] = []
    ok_only_daily = {horizon: [] for horizon in HORIZONS}
    ok_only_selected = {horizon: 0 for horizon in HORIZONS}
    ok_only_labeled = {horizon: 0 for horizon in HORIZONS}
    for day in dates:
        groups = _groups(reports_by_date[day])
        document = forward_by_date[day]
        forward = (
            _forward_map(document)
            if _forward_document_contract_verified(
                document,
                signal_date=day,
                expected_trading_calendar=expected_trading_calendar,
            )
            else {}
        )
        raw_direction_rows = reports_by_date[day].get(
            "direction_shadow_candidates_all", []
        )
        if isinstance(raw_direction_rows, list):
            all_linkage_rows.extend(
                row for row in raw_direction_rows if isinstance(row, Mapping)
            )
        selected_linkage_rows.extend(groups["C_linkage_v2"])
        universe_codes = {
            str(row.get("code") or "").strip()
            for rows in groups.values()
            for row in rows
        }
        universe_codes.discard("")
        universe_means: dict[str, float | None] = {}
        for horizon in HORIZONS:
            values = []
            for code in universe_codes:
                item = forward.get(code)
                value = _verified_forward_value(
                    item,
                    signal_date=day,
                    horizon=horizon,
                    field=f"{day}.{code}.{horizon}",
                )
                if value is not None:
                    values.append(value)
            universe_means[horizon] = _mean(values)
            if values:
                universe_daily[horizon].append(
                    {
                        "date": day,
                        "selected_stock_count": len(universe_codes),
                        "labeled_stock_count": len(values),
                        "mean_return_pct": universe_means[horizon],
                    }
                )
        for group, rows in groups.items():
            accumulator = accumulators[group]
            codes = {str(row.get("code") or "").strip() for row in rows}
            codes.discard("")
            accumulator["candidate_count"].append(len(codes))
            accumulator["code_sets"].append(codes)
            if rows:
                clusters = Counter(
                    str(
                        row.get("sector_cluster")
                        or row.get("sector_name")
                        or "unknown"
                    )
                    for row in rows
                )
                accumulator["max_cluster_share"].append(
                    max(clusters.values()) / len(rows)
                )
                sectors = Counter(
                    str(row.get("sector_name") or "unknown") for row in rows
                )
                accumulator["max_sector_share"].append(
                    max(sectors.values()) / len(rows)
                )
            for horizon in HORIZONS:
                values = []
                accumulator["selected"][horizon] += len(codes)
                for code in codes:
                    item = forward.get(code)
                    value = _verified_forward_value(
                        item,
                        signal_date=day,
                        horizon=horizon,
                        field=f"{day}.{code}.{horizon}",
                    )
                    if value is not None:
                        values.append(value)
                accumulator["labeled"][horizon] += len(values)
                accumulator["positive_labels"][horizon] += sum(
                    value > 0 for value in values
                )
                if values:
                    mean_return = sum(values) / len(values)
                    universe_mean = universe_means[horizon]
                    accumulator["daily"][horizon].append(
                        {
                            "date": day,
                            "selected_stock_count": len(codes),
                            "labeled_stock_count": len(values),
                            "mean_return_pct": mean_return,
                            "universe_mean_return_pct": universe_mean,
                            "excess_return_pct": (
                                mean_return - universe_mean
                                if universe_mean is not None
                                else None
                            ),
                        }
                    )

        ok_rows = [
            row
            for row in groups["C_linkage_v2"]
            if _linkage_status(row) == "ok"
        ]
        ok_codes = {str(row.get("code") or "").strip() for row in ok_rows}
        ok_codes.discard("")
        for horizon in HORIZONS:
            values = []
            ok_only_selected[horizon] += len(ok_codes)
            for code in ok_codes:
                item = forward.get(code)
                value = _verified_forward_value(
                    item,
                    signal_date=day,
                    horizon=horizon,
                    field=f"{day}.{code}.{horizon}",
                )
                if value is not None:
                    values.append(value)
            ok_only_labeled[horizon] += len(values)
            if values:
                ok_only_daily[horizon].append(
                    {"date": day, "mean_return_pct": sum(values) / len(values)}
                )

    groups_output = {}
    for group, accumulator in accumulators.items():
        horizons = {}
        for horizon in HORIZONS:
            daily = accumulator["daily"][horizon]
            returns = [row["mean_return_pct"] for row in daily]
            excess_returns = [
                row["excess_return_pct"]
                for row in daily
                if row["excess_return_pct"] is not None
            ]
            selected = accumulator["selected"][horizon]
            labeled = accumulator["labeled"][horizon]
            worst = min(daily, key=lambda row: row["mean_return_pct"]) if daily else None
            horizons[horizon] = {
                "daily_observation_count": len(returns),
                "selected_stock_days": selected,
                "labeled_stock_days": labeled,
                "coverage_ratio": labeled / selected if selected else 0.0,
                "mean_return_pct": _mean(returns),
                "mean_excess_return_pct": _mean(excess_returns),
                "positive_label_ratio": (
                    accumulator["positive_labels"][horizon] / labeled
                    if labeled
                    else None
                ),
                "positive_day_ratio": (
                    sum(value > 0 for value in returns) / len(returns)
                    if returns
                    else None
                ),
                "max_drawdown_pct": _max_drawdown(returns) if horizon == "1d" else None,
                "worst_date": worst["date"] if worst else None,
                "worst_daily_return_pct": (
                    worst["mean_return_pct"] if worst else None
                ),
                "daily_returns": daily,
            }
        counts = accumulator["candidate_count"]
        cluster_concentration = accumulator["max_cluster_share"]
        sector_concentration = accumulator["max_sector_share"]
        nonempty_candidate_dates = sum(count > 0 for count in counts)
        average_max_cluster_share = (
            _mean(cluster_concentration) or 0.0
        )
        average_max_sector_share = _mean(sector_concentration) or 0.0
        maximum_cluster_share = (
            max(cluster_concentration) if cluster_concentration else 0.0
        )
        groups_output[group] = {
            "average_candidate_count": sum(counts) / len(counts) if counts else 0.0,
            "nonempty_candidate_dates": nonempty_candidate_dates,
            "candidate_date_ratio": (
                nonempty_candidate_dates / len(dates) if dates else 0.0
            ),
            "average_max_cluster_share": average_max_cluster_share,
            "average_max_sector_share": average_max_sector_share,
            "maximum_cluster_share": maximum_cluster_share,
            "maximum_sector_share": (
                max(sector_concentration) if sector_concentration else 0.0
            ),
            "average_turnover": _turnover(accumulator["code_sets"]),
            "horizons": horizons,
        }

    universe_output = {}
    for horizon, daily in universe_daily.items():
        values = [row["mean_return_pct"] for row in daily]
        universe_output[horizon] = {
            "daily_observation_count": len(daily),
            "mean_return_pct": _mean(values),
            "daily_returns": daily,
        }

    paired = {
        horizon: _paired_daily_difference(
            groups_output["A_legacy"]["horizons"][horizon]["daily_returns"],
            groups_output["C_linkage_v2"]["horizons"][horizon]["daily_returns"],
        )
        for horizon in HORIZONS
    }
    all_status_counts = Counter(_linkage_status(row) for row in all_linkage_rows)
    selected_status_counts = Counter(
        _linkage_status(row) for row in selected_linkage_rows
    )
    selected_total = len(selected_linkage_rows)
    ok_only_horizons = {}
    for horizon in HORIZONS:
        daily = ok_only_daily[horizon]
        values = [row["mean_return_pct"] for row in daily]
        selected = ok_only_selected[horizon]
        labeled = ok_only_labeled[horizon]
        ok_only_horizons[horizon] = {
            "daily_observation_count": len(daily),
            "selected_stock_days": selected,
            "labeled_stock_days": labeled,
            "coverage_ratio": labeled / selected if selected else 0.0,
            "mean_return_pct": _mean(values),
        }

    months = {day[:7] for day in dates}
    legacy = groups_output["A_legacy"]
    linkage = groups_output["C_linkage_v2"]
    minimum_observation_dates = max(60, math.ceil(len(dates) * 0.90))
    mean_excess_better = all(
        linkage["horizons"][horizon]["mean_excess_return_pct"] is not None
        and legacy["horizons"][horizon]["mean_excess_return_pct"] is not None
        and linkage["horizons"][horizon]["mean_excess_return_pct"]
        > legacy["horizons"][horizon]["mean_excess_return_pct"]
        for horizon in ("3d", "5d")
    )
    mean_return_better = all(
        linkage["horizons"][horizon]["mean_return_pct"] is not None
        and legacy["horizons"][horizon]["mean_return_pct"] is not None
        and linkage["horizons"][horizon]["mean_return_pct"]
        > legacy["horizons"][horizon]["mean_return_pct"]
        for horizon in ("3d", "5d")
    )
    gates = {
        "minimum_60_dates": len(dates) >= 60,
        "minimum_3_months": len(months) >= 3,
        "strict_pit_eligible": bool(strict_pit_eligible),
        "historical_constituent_universe_versioned": False,
        "forward_label_maturity_verified": forward_label_maturity_verified,
        "cluster_map_consistent": cluster_map_consistent,
        "minimum_c_observation_dates": all(
            linkage["horizons"][horizon]["daily_observation_count"]
            >= minimum_observation_dates
            for horizon in HORIZONS
        ),
        "coverage_90pct": all(
            linkage["horizons"][horizon]["coverage_ratio"] >= 0.90
            and legacy["horizons"][horizon]["coverage_ratio"] >= 0.90
            for horizon in HORIZONS
        ),
        "three_and_five_day_mean_excess_return_better": mean_excess_better,
        "three_and_five_day_mean_return_better": mean_return_better,
        "three_and_five_day_win_rate_not_worse": all(
            linkage["horizons"][horizon]["positive_label_ratio"] is not None
            and legacy["horizons"][horizon]["positive_label_ratio"] is not None
            and linkage["horizons"][horizon]["positive_label_ratio"]
            >= legacy["horizons"][horizon]["positive_label_ratio"]
            for horizon in ("3d", "5d")
        ),
        "one_day_drawdown_not_worse": (
            linkage["horizons"]["1d"]["max_drawdown_pct"] is not None
            and legacy["horizons"]["1d"]["max_drawdown_pct"] is not None
            and linkage["horizons"]["1d"]["max_drawdown_pct"]
            >= legacy["horizons"]["1d"]["max_drawdown_pct"]
        ),
        "turnover_not_more_than_10pct_worse": (
            linkage["average_turnover"] is not None
            and legacy["average_turnover"] is not None
            and linkage["average_turnover"] <= legacy["average_turnover"] * 1.10
        ),
        "concentration_lower": (
            linkage["nonempty_candidate_dates"] > 0
            and legacy["nonempty_candidate_dates"] > 0
            and linkage["maximum_cluster_share"]
            < legacy["maximum_cluster_share"]
        ),
        "market_regime_stability_verified": False,
        "date_and_industry_concentration_verified": False,
        "ok_only_sensitivity_usable": (
            selected_total > 0
            and selected_status_counts.get("partial", 0) == 0
            and all(
                ok_only_horizons[horizon]["daily_observation_count"]
                >= minimum_observation_dates
                and ok_only_horizons[horizon]["coverage_ratio"] >= 0.90
                for horizon in HORIZONS
            )
        ),
    }
    promoted = all(gates.values())
    return {
        "schema_version": "stock_sector_linkage_shadow_evaluation.v2",
        "mode": "paper_shadow_research_only",
        "date_count": len(dates),
        "month_count": len(months),
        "evaluated_dates": dates,
        "minimum_required_c_observation_dates": minimum_observation_dates,
        "cluster_map_identity": (
            {
                "source_sha256": cluster_identities[0][0],
                "mapping_sha256": cluster_identities[0][1],
            }
            if cluster_map_consistent
            else None
        ),
        "pit_evidence_status": (
            "verified"
            if strict_pit_eligible
            else "unverified_no_trusted_verifier"
        ),
        "self_attested_pit_evidence_shape_valid": self_attested_pit_shape_valid,
        "historical_constituent_universe_versioned": False,
        "historical_constituent_universe_versioned_claimed": bool(
            historical_constituent_universe_versioned
        ),
        "groups": groups_output,
        "same_day_candidate_universe": {"horizons": universe_output},
        "paired_daily_differences": {"C_minus_A": paired},
        "comparison_coverage": {
            horizon: {
                "a_label_coverage_ratio": legacy["horizons"][horizon][
                    "coverage_ratio"
                ],
                "c_label_coverage_ratio": linkage["horizons"][horizon][
                    "coverage_ratio"
                ],
                "paired_daily_observation_count": paired[horizon][
                    "observation_count"
                ],
                "paired_daily_coverage_ratio": (
                    paired[horizon]["observation_count"] / len(dates)
                    if dates
                    else 0.0
                ),
            }
            for horizon in HORIZONS
        },
        "linkage_evidence_sensitivity": {
            "all_candidate_status_counts": dict(sorted(all_status_counts.items())),
            "selected_status_counts": dict(sorted(selected_status_counts.items())),
            "selected_partial_ratio": (
                selected_status_counts.get("partial", 0) / selected_total
                if selected_total
                else 0.0
            ),
            "ok_only_candidate_count": selected_status_counts.get("ok", 0),
            "ok_only_horizons": ok_only_horizons,
            "all_candidate_component_status_counts": _component_status_counts(
                all_linkage_rows
            ),
            "selected_component_status_counts": _component_status_counts(
                selected_linkage_rows
            ),
        },
        "stability_analysis": {
            "market_regime_status": "unavailable",
            "reason": "no_date_bound_market_regime_labels_in_replay_inputs",
            "single_date_or_industry_dominance_eligible": False,
        },
        "promotion_gates": gates,
        "promotion_status": "eligible" if promoted else "insufficient_evidence",
        "disclaimer": "No broker connection and no live order instruction.",
    }


def _format_metric(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    number = float(value)
    return f"{number:.4f}{'%' if percent else ''}"


def render_markdown_report(
    report: Mapping[str, Any], *, artifact_sha256: str | None = None
) -> str:
    groups = report.get("groups", {})
    lines = [
        "# Linkage V2 Replacement Decision",
        "",
        f"- Mode: `{report.get('mode')}`",
        f"- Promotion status: `{report.get('promotion_status')}`",
        f"- Evaluated dates: {report.get('date_count', 0)}",
        f"- Strict PIT: `strict_pit_eligible={str(report.get('pit_evidence_status') == 'verified').lower()}`",
    ]
    if artifact_sha256:
        lines.append(f"- JSON SHA256: `{artifact_sha256}`")
    lines.extend(
        [
            "",
            "## A/B/C Results",
            "",
            "| Group | Avg candidates | Horizon | Coverage | Mean return | Mean excess | Stock win rate |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for group_name in ("A_legacy", "B_membership_only", "C_linkage_v2"):
        group = groups.get(group_name, {})
        horizons = group.get("horizons", {}) if isinstance(group, Mapping) else {}
        for horizon in HORIZONS:
            metrics = horizons.get(horizon, {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        group_name,
                        _format_metric(group.get("average_candidate_count")),
                        horizon,
                        _format_metric(metrics.get("coverage_ratio", 0) * 100, percent=True),
                        _format_metric(metrics.get("mean_return_pct"), percent=True),
                        _format_metric(metrics.get("mean_excess_return_pct"), percent=True),
                        _format_metric(
                            metrics.get("positive_label_ratio") * 100,
                            percent=True,
                        )
                        if metrics.get("positive_label_ratio") is not None
                        else "N/A",
                    ]
                )
                + " |"
            )
    lines.extend(["", "## Promotion Gates", ""])
    gates = report.get("promotion_gates", {})
    for name, passed in (gates.items() if isinstance(gates, Mapping) else []):
        lines.append(f"- `{name}`: {'PASS' if passed else 'FAIL'}")
    sensitivity = report.get("linkage_evidence_sensitivity", {})
    lines.extend(
        [
            "",
            "## Evidence Limits",
            "",
            f"- Selected linkage statuses: `{json.dumps(sensitivity.get('selected_status_counts', {}), ensure_ascii=False, sort_keys=True)}`",
            f"- Market-regime analysis: `{report.get('stability_analysis', {}).get('market_regime_status', 'unavailable')}`",
            "- Future returns are labels only and are never used by feature construction or ranking.",
            "- Unversioned historical constituent universes make this development evidence, not OOS or blind-test evidence.",
            "- No broker connection and no live order instruction.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--unified-root", type=Path, required=True)
    parser.add_argument("--forward-root", type=Path, required=True)
    parser.add_argument(
        "--pit-evidence",
        type=Path,
        default=None,
        help="Verified, date- and manifest-bound PIT evidence JSON",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trading-calendar-path", type=Path, required=True)
    parser.add_argument("--expected-calendar-sha256", required=True)
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Markdown companion path; defaults to the JSON path with .md suffix",
    )
    args = parser.parse_args()
    reports = {}
    forwards = {}
    report_file_sha256_by_date = {}
    manifests = []
    for path in sorted(args.unified_root.glob("*/unified_report.json")):
        day = path.parent.name
        if args.start <= day <= args.end:
            reports[day], report_sha256 = load_strict_json_with_sha256(path)
            report_file_sha256_by_date[day] = report_sha256
            manifests.append({"path": str(path.resolve()), "sha256": report_sha256})
            forward_path = args.forward_root / day / "forward_returns.json"
            if forward_path.is_file():
                forwards[day], forward_sha256 = load_strict_json_with_sha256(
                    forward_path
                )
                manifests.append({"path": str(forward_path.resolve()), "sha256": forward_sha256})
    if args.pit_evidence:
        pit_evidence, pit_evidence_sha256 = load_strict_json_with_sha256(
            args.pit_evidence
        )
    else:
        pit_evidence = None
        pit_evidence_sha256 = None
    trading_calendar = load_trading_calendar(
        args.trading_calendar_path,
        as_of=args.end,
        include_future=True,
    )
    if trading_calendar["sha256"] != args.expected_calendar_sha256.lower():
        raise ValueError("trading calendar SHA mismatch")
    manifests.append(
        {
            "path": str(args.trading_calendar_path.resolve()),
            "sha256": trading_calendar["sha256"],
        }
    )
    report = evaluate_linkage_paths(
        reports,
        forwards,
        strict_pit_evidence=pit_evidence,
        report_file_sha256_by_date=report_file_sha256_by_date,
        expected_trading_calendar=trading_calendar,
    )
    report["source_manifest"] = manifests
    report["source_manifest_sha256"] = _canonical_sha256(
        {"documents": manifests}
    )
    report["evaluation_window"] = {
        "requested_start": args.start,
        "requested_end": args.end,
        "actual_start": min(reports) if reports else None,
        "actual_end": max(reports) if reports else None,
    }
    report["provenance"] = {
        "unified_root": str(args.unified_root.resolve()),
        "forward_root": str(args.forward_root.resolve()),
        "future_returns_role": "labels_only",
        "trading_calendar": trading_calendar,
        "historical_constituent_universe_versioned": False,
        "strict_pit_eligible": report["pit_evidence_status"] == "verified",
    }
    report["pit_evidence_input"] = (
        {
            "path": str(args.pit_evidence.resolve()),
            "sha256": pit_evidence_sha256,
        }
        if args.pit_evidence
        else None
    )
    write_strict_json_atomic(args.output, report)
    artifact_sha256 = hashlib.sha256(args.output.read_bytes()).hexdigest()
    markdown_output = args.markdown_output or args.output.with_suffix(".md")
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(
        render_markdown_report(report, artifact_sha256=artifact_sha256),
        encoding="utf-8",
    )
    print(f"evaluated {report['date_count']} dates: {report['promotion_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
