"""Immutable source collection and maturity monitoring for frozen industry OOS dates."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from theme_sector_radar.ml.contract import canonical_sha256
from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .industry_sector_shadow import CLASSIFICATION, DISCLAIMER, MODE, _load_histories
from .industry_sector_oos_readiness import CANDIDATE_CONFIGS


FROZEN_TEST_SIGNAL_DATES = ("2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16")
LABEL_HORIZON_TRADING_DAYS = 5
SAFETY_FLAGS = (
    "strict_pit_eligible",
    "eligible_for_oos_claim",
    "promotion_allowed",
    "live_trading_allowed",
    "formal_predictor_compatible",
)


def _false_safety() -> dict[str, bool]:
    return {key: False for key in SAFETY_FLAGS}


def _write_immutable(path: Path, payload: Mapping[str, Any]) -> dict[str, str]:
    if path.exists():
        existing, sha256 = load_strict_json_with_sha256(path)
        if canonical_sha256(existing) != canonical_sha256(payload):
            raise ValueError(f"immutable prospective artifact differs: {path}")
        return {"path": str(path.resolve()), "sha256": sha256}
    validate_no_executable_instructions(payload, context=f"prospective artifact {path.name}")
    write_strict_json_atomic(path, payload)
    _loaded, sha256 = load_strict_json_with_sha256(path)
    return {"path": str(path.resolve()), "sha256": sha256}


def _rows_by_date(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["date"]): dict(row) for row in rows}


def _source_state(source_root: Path | str) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    histories, manifest = _load_histories(Path(source_root).resolve())
    return ({name: [dict(row) for row in rows] for name, rows in histories.items()}, manifest)


def _snapshot_payload(
    signal_date: str,
    histories: Mapping[str, Sequence[Mapping[str, Any]]],
    source_manifest: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    source_by_sector = {str(item["sector_name"]): item for item in source_manifest}
    sectors: list[dict[str, Any]] = []
    for sector_name in sorted(histories):
        rows = [dict(row) for row in histories[sector_name] if str(row["date"]) <= signal_date]
        signal_rows = [row for row in rows if str(row["date"]) == signal_date]
        if len(signal_rows) != 1:
            raise ValueError(f"missing or duplicate signal bar: {signal_date} {sector_name}")
        source = source_by_sector[sector_name]
        sectors.append({
            "sector_name": sector_name,
            "signal_bar": signal_rows[0],
            "prefix_record_count": len(rows),
            "prefix_sha256": canonical_sha256(rows),
            "source_path": source["path"],
            "source_file_sha256_at_collection": source["sha256"],
        })
    payload = {
        "schema_version": "ml-industry-sector-prospective-source-snapshot-v1",
        "mode": MODE,
        "status": "source_snapshot_frozen",
        "dataset_classification": CLASSIFICATION,
        "signal_date": signal_date,
        "sector_count": len(sectors),
        "sectors": sectors,
        **_false_safety(),
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "disclaimer": DISCLAIMER,
    }
    return payload


def _snapshot_manifest_payload(signal_date: str, snapshot_ref: Mapping[str, str], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "ml-industry-sector-prospective-source-manifest-v1",
        "mode": MODE,
        "status": "source_snapshot_frozen",
        "signal_date": signal_date,
        "snapshot": dict(snapshot_ref),
        "sector_count": snapshot["sector_count"],
        "aggregate_prefix_sha256": canonical_sha256([
            {"sector_name": row["sector_name"], "prefix_sha256": row["prefix_sha256"]}
            for row in snapshot["sectors"]
        ]),
        **_false_safety(),
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "disclaimer": DISCLAIMER,
    }


def _replay_snapshot(snapshot: Mapping[str, Any], histories: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[str]:
    errors: list[str] = []
    signal_date = str(snapshot["signal_date"])
    current_sectors = set(histories)
    expected_sectors = {str(row["sector_name"]) for row in snapshot["sectors"]}
    missing = sorted(expected_sectors - current_sectors)
    extra = sorted(current_sectors - expected_sectors)
    if missing:
        errors.append(f"missing_industries:{','.join(missing)}")
    if extra:
        errors.append(f"unexpected_industries:{','.join(extra)}")
    for frozen in snapshot["sectors"]:
        sector_name = str(frozen["sector_name"])
        if sector_name not in histories:
            continue
        rows = [dict(row) for row in histories[sector_name] if str(row["date"]) <= signal_date]
        if canonical_sha256(rows) != frozen["prefix_sha256"]:
            errors.append(f"source_revision:{signal_date}:{sector_name}")
            continue
        by_date = _rows_by_date(rows)
        if signal_date not in by_date:
            errors.append(f"missing_signal_bar:{signal_date}:{sector_name}")
        elif by_date[signal_date] != frozen["signal_bar"]:
            errors.append(f"signal_bar_revision:{signal_date}:{sector_name}")
    return errors


def _complete_calendar(histories: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[list[str], dict[str, list[str]]]:
    sector_dates = {
        sector: {str(row["date"]) for row in rows}
        for sector, rows in histories.items()
    }
    union_dates = sorted(set().union(*sector_dates.values()))
    complete_dates = sorted(set.intersection(*sector_dates.values()))
    missing_by_date = {
        day: sorted(sector for sector, dates in sector_dates.items() if day not in dates)
        for day in union_dates
        if day not in complete_dates
    }
    return complete_dates, missing_by_date


def _maturity(signal_date: str, complete_dates: Sequence[str]) -> dict[str, Any]:
    later = [day for day in complete_dates if day > signal_date]
    observed = later[:LABEL_HORIZON_TRADING_DAYS]
    mature = len(observed) == LABEL_HORIZON_TRADING_DAYS
    return {
        "signal_date": signal_date,
        "label_horizon_trading_days": LABEL_HORIZON_TRADING_DAYS,
        "observed_future_trading_dates": observed,
        "observed_future_trading_day_count": len(observed),
        "label_mature": mature,
        "label_maturity_date": observed[-1] if mature else None,
        "missing_future_trading_day_count": LABEL_HORIZON_TRADING_DAYS - len(observed),
    }


def collect_prospective_collection_status(
    source_root: Path | str,
    output_root: Path | str,
    *,
    signal_dates: Sequence[str] = FROZEN_TEST_SIGNAL_DATES,
) -> dict[str, Any]:
    frozen_dates = tuple(str(value) for value in signal_dates)
    if frozen_dates != FROZEN_TEST_SIGNAL_DATES:
        raise ValueError("prospective signal date drift from frozen contract")
    for value in frozen_dates:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("prospective signal dates must be canonical")

    output = Path(output_root).resolve()
    snapshot_root = output / "snapshots"
    manifest_root = output / "manifests"
    output.mkdir(parents=True, exist_ok=True)
    snapshot_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    histories, source_manifest = _source_state(source_root)
    required_sectors = sorted(histories)
    complete_dates, missing_by_date = _complete_calendar(histories)
    initial_complete_end = complete_dates[-1]

    contract_path = output / "collection_contract.json"
    if contract_path.exists():
        contract, contract_sha = load_strict_json_with_sha256(contract_path)
        contract_ref = {"path": str(contract_path.resolve()), "sha256": contract_sha}
    else:
        contract_payload = {
            "schema_version": "ml-industry-sector-prospective-collection-contract-v1",
            "mode": MODE,
            "status": "frozen",
            "signal_dates": list(FROZEN_TEST_SIGNAL_DATES),
            "required_sectors": required_sectors,
            "required_sector_count": len(required_sectors),
            "label_horizon_trading_days": LABEL_HORIZON_TRADING_DAYS,
            "initial_complete_trading_date_end": initial_complete_end,
            **_false_safety(),
            "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        }
        contract_ref = _write_immutable(contract_path, contract_payload)
        contract, _contract_sha = load_strict_json_with_sha256(contract_ref["path"])

    candidate_freeze_payload = {
        "schema_version": "ml-industry-sector-prospective-candidate-freeze-v1",
        "mode": MODE,
        "status": "frozen_not_trained",
        "candidate_configs": [dict(config) for config in CANDIDATE_CONFIGS],
        "candidate_configs_sha256": canonical_sha256(CANDIDATE_CONFIGS),
        "event_source_read": False,
        "candidate_model_training_run": False,
        **_false_safety(),
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "disclaimer": DISCLAIMER,
    }
    candidate_freeze_ref = _write_immutable(
        output / "candidate_freeze.json", candidate_freeze_payload
    )

    errors: list[str] = []
    if contract["signal_dates"] != list(FROZEN_TEST_SIGNAL_DATES):
        errors.append("date_drift:contract_signal_dates")
    if contract["required_sectors"] != required_sectors:
        missing = sorted(set(contract["required_sectors"]) - set(required_sectors))
        extra = sorted(set(required_sectors) - set(contract["required_sectors"]))
        errors.append(f"industry_set_drift:missing={missing}:extra={extra}")

    snapshot_refs: dict[str, Any] = {}
    for signal_date in FROZEN_TEST_SIGNAL_DATES:
        snapshot_path = snapshot_root / f"{signal_date}.json"
        manifest_path = manifest_root / f"{signal_date}.manifest.json"
        if snapshot_path.exists():
            snapshot, snapshot_sha = load_strict_json_with_sha256(snapshot_path)
            snapshot_ref = {"path": str(snapshot_path.resolve()), "sha256": snapshot_sha}
        else:
            snapshot = _snapshot_payload(signal_date, histories, source_manifest)
            snapshot_ref = _write_immutable(snapshot_path, snapshot)
        manifest_payload = _snapshot_manifest_payload(signal_date, snapshot_ref, snapshot)
        manifest_ref = _write_immutable(manifest_path, manifest_payload)
        manifest, _manifest_sha = load_strict_json_with_sha256(manifest_path)
        if manifest["snapshot"]["sha256"] != snapshot_ref["sha256"]:
            errors.append(f"snapshot_sha_replay_failed:{signal_date}")
        errors.extend(_replay_snapshot(snapshot, histories))
        snapshot_refs[signal_date] = {"snapshot": snapshot_ref, "manifest": manifest_ref}

    maturity = [_maturity(signal_date, complete_dates) for signal_date in FROZEN_TEST_SIGNAL_DATES]
    relevant_missing_bars = {
        day: sectors for day, sectors in missing_by_date.items()
        if day >= FROZEN_TEST_SIGNAL_DATES[0]
    }
    if relevant_missing_bars:
        errors.append("missing_bars_in_prospective_calendar")
    all_mature = all(item["label_mature"] for item in maturity)
    replay_ok = not any("revision" in item or "sha_replay" in item for item in errors)
    source_complete = not any(
        item.startswith(("missing_industries", "unexpected_industries", "missing_signal_bar", "missing_bars"))
        for item in errors
    )
    collection_ready = all_mature and replay_ok and source_complete and not errors
    if collection_ready:
        status = "ready_for_frozen_candidate_evaluation"
    elif errors:
        status = "rejected_source_integrity"
    else:
        status = "blocked_pending_label_maturity"

    initial_end = str(contract["initial_complete_trading_date_end"])
    new_complete_dates = [day for day in complete_dates if day > initial_end]
    current_source_sha = canonical_sha256([
        {"sector_name": row["sector_name"], "sha256": row["sha256"]}
        for row in sorted(source_manifest, key=lambda item: str(item["sector_name"]))
    ])
    report = {
        "schema_version": "ml-industry-sector-prospective-collection-status-v1",
        "mode": MODE,
        "status": status,
        "dataset_classification": CLASSIFICATION,
        "frozen_signal_dates": list(FROZEN_TEST_SIGNAL_DATES),
        "label_horizon_trading_days": LABEL_HORIZON_TRADING_DAYS,
        "contract": contract_ref,
        "candidate_freeze": candidate_freeze_ref,
        "snapshots": snapshot_refs,
        "required_sector_count": len(contract["required_sectors"]),
        "current_sector_count": len(histories),
        "complete_trading_date_end": complete_dates[-1],
        "new_complete_trading_dates": new_complete_dates,
        "source_manifest_current_sha256": current_source_sha,
        "maturity": maturity,
        "source_complete": source_complete,
        "snapshot_sha_replay_passed": replay_ok,
        "all_test_labels_mature": all_mature,
        "collection_ready": collection_ready,
        "missing_bars_by_date": relevant_missing_bars,
        "errors": errors,
        "event_source_read": False,
        "candidate_model_training_run": False,
        **_false_safety(),
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="industry sector prospective collection status")
    write_strict_json_atomic(output / "prospective_collection_status.json", report)
    return report
