"""Paper-only inventory and coverage audit for future stock-ML inputs."""

from __future__ import annotations

from collections import Counter
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .contract import canonical_sha256
from .historical_factor_source_rebuild import FORBIDDEN_FIELDS
from .historical_research import HISTORICAL_FEATURE_NAMES, validate_historical_research_dataset
from .schema import DISCLAIMER, MODE


PREPARATION_SCHEMA_VERSION = "ml-stock-candidate-data-preparation-v2"
SOURCE_INVENTORY_SCHEMA_VERSION = "ml-stock-candidate-source-inventory-v2"
FEATURE_SCHEMA_CONTRACT_VERSION = "ml-stock-candidate-feature-schema-contract-v2"
_SHA256_LENGTH = 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _safe_flags() -> dict[str, bool]:
    return {
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }


def _forbidden_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in FORBIDDEN_FIELDS:
                found.add(str(key))
            found.update(_forbidden_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_forbidden_keys(item))
    return found


def _logical_artifact(core: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {**dict(core), field: canonical_sha256(core), "disclaimer": DISCLAIMER}


def _candidate_bar_audit(candidate: Mapping[str, Any], day: str) -> dict[str, Any]:
    identity = candidate.get("intraday_bar_identity")
    bars = candidate.get("intraday_bars")
    if not isinstance(identity, Mapping) or not isinstance(bars, list):
        return {
            "bar_count": 0,
            "complete_session": False,
            "future_bar_count": 0,
            "source_sha256_present": False,
        }
    future = 0
    for bar in bars:
        if not isinstance(bar, Mapping):
            continue
        stamp = str(bar.get("date") or bar.get("time") or "")
        if stamp[:8] > day.replace("-", ""):
            future += 1
    source_sha = str(identity.get("source_security_bars_sha256") or "")
    return {
        "bar_count": len(bars),
        "complete_session": identity.get("complete_session") is True,
        "future_bar_count": future,
        "source_sha256_present": len(source_sha) == _SHA256_LENGTH,
    }


def _scan_candidate_archive(
    dataset: Mapping[str, Any],
) -> tuple[dict[str, Any], set[str], list[tuple[str, str, tuple[str, ...]]]]:
    root = Path(str(dataset["source_manifest"]["candidate_root"]))
    bound = {str(entry["as_of_date"]): entry for entry in dataset["source_manifest"]["candidate_sources"]}
    sources: list[dict[str, Any]] = []
    candidate_dates: set[str] = set()
    identities: list[tuple[str, str, tuple[str, ...]]] = []
    valid_rows = 0
    v9_rows = 0
    extra_rows = 0
    complete_rows = 0
    no_future_bar_rows = 0
    v9_complete_rows = 0
    v9_no_future_bar_rows = 0
    extra_complete_rows = 0
    extra_no_future_bar_rows = 0
    for path in sorted(root.glob("*/top30_candidates.intraday_backfilled.json")):
        day = path.parent.name
        source_sha = _sha256(path)
        item: dict[str, Any] = {
            "as_of_date": day,
            "path": str(path.resolve()),
            "sha256": source_sha,
            "bound_by_v9_manifest": day in bound,
            "status": "invalid",
            "candidate_count": 0,
            "bar_complete_rows": 0,
            "bar_pit_safe_rows": 0,
        }
        try:
            payload = load_strict_json(path)
            candidates = payload.get("candidates")
            valid = (
                payload.get("as_of") == day
                and isinstance(candidates, list)
                and payload.get("candidate_count") == len(candidates)
            )
            if not valid:
                item["reason"] = "source_as_of_or_count_mismatch"
                sources.append(item)
                continue
            item["status"] = "valid_content_bound_source"
            item["candidate_count"] = len(candidates)
            valid_rows += len(candidates)
            if day in bound:
                v9_rows += len(candidates)
            else:
                extra_rows += len(candidates)
            candidate_dates.add(day)
            for candidate in candidates:
                if not isinstance(candidate, Mapping):
                    continue
                code = str(candidate.get("code") or "").zfill(6)
                boards = tuple(str(value) for value in (candidate.get("boards") or []))
                identities.append((day, code, boards))
                bars = _candidate_bar_audit(candidate, day)
                if bars["complete_session"] and bars["bar_count"] > 0:
                    item["bar_complete_rows"] += 1
                    complete_rows += 1
                    if day in bound:
                        v9_complete_rows += 1
                    else:
                        extra_complete_rows += 1
                if (
                    bars["complete_session"]
                    and bars["bar_count"] > 0
                    and bars["future_bar_count"] == 0
                    and bars["source_sha256_present"]
                ):
                    item["bar_pit_safe_rows"] += 1
                    no_future_bar_rows += 1
                    if day in bound:
                        v9_no_future_bar_rows += 1
                    else:
                        extra_no_future_bar_rows += 1
            sources.append(item)
        except (OSError, ValueError) as exc:
            item["reason"] = f"{type(exc).__name__}: {exc}"
            sources.append(item)
    summary = {
        "source_id": "candidate_archive",
        "root": str(root.resolve()),
        "physical_file_count": len(sources),
        "valid_content_bound_file_count": sum(item["status"] == "valid_content_bound_source" for item in sources),
        "v9_manifest_file_count": len(bound),
        "v9_manifest_row_count": v9_rows,
        "extra_valid_file_count": sum(
            item["status"] == "valid_content_bound_source" and not item["bound_by_v9_manifest"]
            for item in sources
        ),
        "extra_valid_row_count": extra_rows,
        "candidate_date_count": len(candidate_dates),
        "complete_intraday_bar_rows": complete_rows,
        "content_bound_no_future_intraday_bar_rows": no_future_bar_rows,
        "v9_complete_intraday_bar_rows": v9_complete_rows,
        "v9_content_bound_no_future_intraday_bar_rows": v9_no_future_bar_rows,
        "extra_complete_intraday_bar_rows": extra_complete_rows,
        "extra_content_bound_no_future_intraday_bar_rows": extra_no_future_bar_rows,
        "status": "partial_content_bound_historical_reconstruction",
        "strict_pit_eligible": False,
        "blocking_reason": "nested factor snapshot as_of is blank for all rows and candidate archive is not a prospective PIT archive",
        "sources": sources,
    }
    return summary, candidate_dates, identities


def _scan_sector_history(direction_payload: Mapping[str, Any]) -> dict[str, Any]:
    manifest = direction_payload.get("source_manifest") or {}
    root = Path(str(manifest.get("root") or ""))
    files = []
    for path in (sorted((root / "industry").glob("*.json")) if root.is_dir() else []):
        files.append({
            "path": str(path.resolve()),
            "sha256": _sha256(path),
        })
    return {
        "source_id": "industry_sector_history",
        "root": str(root.resolve()),
        "file_count": len(files),
        "manifest_document_count": manifest.get("document_count"),
        "first_date": min((str(x.get("first_date") or "") for x in manifest.get("documents") or []), default=None),
        "last_date": max((str(x.get("last_date") or "") for x in manifest.get("documents") or []), default=None),
        "universe_vintage_status": manifest.get("universe_vintage_status"),
        "strict_pit_eligible": manifest.get("strict_pit_eligible") is True,
        "status": "partial_historical_values_non_pit_membership",
        "blocking_reason": manifest.get("universe_vintage_limitation"),
        "files": files,
    }


def _scan_json_snapshot_root(root: Path, source_id: str) -> dict[str, Any]:
    files = []
    as_of_dates: set[str] = set()
    for path in (sorted(root.rglob("*.json")) if root.is_dir() else []):
        try:
            payload = load_strict_json(path)
            as_of = str(payload.get("as_of_date") or "") if isinstance(payload, Mapping) else ""
            if as_of:
                as_of_dates.add(as_of)
            files.append({"path": str(path.resolve()), "sha256": _sha256(path), "as_of_date": as_of or None})
        except (OSError, ValueError) as exc:
            files.append({"path": str(path.resolve()), "sha256": _sha256(path), "error": type(exc).__name__})
    return {
        "source_id": source_id,
        "root": str(root.resolve()),
        "file_count": len(files),
        "as_of_dates": sorted(as_of_dates),
        "status": "partial_current_or_sparse_snapshot" if files else "unavailable",
        "strict_pit_eligible": False,
        "files": files,
    }


def _scan_linkage_reports(
    project_root: Path,
    candidate_dates: set[str],
) -> dict[str, Any]:
    paths = sorted(project_root.glob("reports/paper_shadow/linkage_v2_unified*/2026-*/unified_report.json"))
    reports = []
    for path in paths:
        payload, sha = load_strict_json_with_sha256(path)
        day = str(payload.get("as_of_date") or "")
        reports.append({
            "path": str(path.resolve()),
            "sha256": sha,
            "as_of_date": day,
            "score_as_of_date": payload.get("score_as_of_date"),
            "candidate_date_overlap": day in candidate_dates,
            "dated_input_manifest_present": False,
            "strict_pit_eligible": False,
        })
    dates = sorted({item["as_of_date"] for item in reports})
    return {
        "source_id": "linkage_v2_unified_reports",
        "report_count": len(reports),
        "date_count": len(dates),
        "dates": dates,
        "candidate_date_overlap_count": sum(item["candidate_date_overlap"] for item in reports),
        "dated_input_manifest_count": sum(item["dated_input_manifest_present"] for item in reports),
        "strict_pit_eligible": False,
        "status": "unavailable_for_99_day_replay",
        "blocking_reason": "available reports are single-day and lack dated historical constituent/return/flow input manifests",
        "reports": reports,
    }


def _schema_contract() -> dict[str, Any]:
    return {
        "schema_version": FEATURE_SCHEMA_CONTRACT_VERSION,
        "mode": MODE,
        "status": "planning_only_no_model_training",
        "schema_a_candidate_snapshot": {
            "grain": "one row per stock_code and as_of_date",
            "required_fields": [
                "as_of_date", "stock_code", "feature_family", "features",
                "missing_indicators", "source_ref", "as_of_evidence", "eligibility_state",
            ],
            "feature_families": {
                "technical_price_structure": ["ma20_slope_5", "relative_strength_20", "relative_strength_60", "risk_adjusted_return_20"],
                "support_resistance": ["near_high_250", "drawdown_depth_20", "breakout_distance_20", "close_strength_score"],
                "volume_liquidity": ["amount_ratio_20", "liquidity_score", "volume_stability_score", "volume_burst_quality_score"],
                "volatility_risk": ["atr10_atr50", "chasing_risk_score", "intraday_reversal_risk_score", "single_name_overheat_score"],
                "sector_context": ["sector_support_score"],
            },
            "prohibited_inputs": sorted(FORBIDDEN_FIELDS | {"training_label", "training_label_end_date", "direction_score_shadow", "linkage_v2"}),
        },
        "schema_b_feature_panel": {
            "grain": "one row per stock_code, as_of_date, feature_name",
            "required_fields": [
                "as_of_date", "stock_code", "feature_name", "feature_family", "value",
                "missing", "source_ref", "source_sha256", "feature_max_date", "eligibility_state",
            ],
            "states": ["strict_replayable", "partial_content_bound", "missing", "excluded"],
            "no_silent_zero_policy": "missing must be represented by missing=true; numeric zero cannot replace unknown",
        },
        "future_comparison_design": {
            "rule_only": "existing rule baseline kept parallel and read-only",
            "ml_only": "technical Schema A/B features only, date-grouped cross-sectional rank",
            "hybrid": "pre-registered rule gate plus ML rank or blend, paper-only and never formal overwrite",
            "common_contract": "same candidate cohort, as_of_date groups, label horizon, expanding folds, purge, Top1/3/5, Rank IC, fold/regime slices, turnover and cost stress",
            "promotion_policy": "no comparison may promote a model from the same reconstruction window",
        },
        **_safe_flags(),
    }


def build_candidate_data_preparation(
    dataset_path: Path | str,
    feature_inventory_path: Path | str,
    direction_report_path: Path | str,
    project_root: Path | str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    dataset = load_strict_json(dataset_path)
    validate_historical_research_dataset(dataset)
    feature_inventory, inventory_sha = load_strict_json_with_sha256(Path(feature_inventory_path))
    inventory_core = {
        key: value for key, value in feature_inventory.items()
        if key not in {"inventory_sha256", "disclaimer"}
    }
    if feature_inventory.get("inventory_sha256") != canonical_sha256(inventory_core):
        raise ValueError("candidate data preparation feature inventory SHA mismatch")
    direction_payload, direction_sha = load_strict_json_with_sha256(Path(direction_report_path))
    candidates, candidate_dates, identities = _scan_candidate_archive(dataset)
    direction_dates = {str(x.get("as_of_date")) for x in direction_payload.get("daily_results") or []}
    direction_index = {
        (str(day.get("as_of_date")), str(sector.get("sector_name") or "")): sector
        for day in direction_payload.get("daily_results") or []
        for sector in day.get("sectors") or []
    }
    exact_name_rows = 0
    v9_candidate_dates = {
        str(entry["as_of_date"]) for entry in dataset["source_manifest"]["candidate_sources"]
    }
    for day, _code, boards in identities:
        if day not in v9_candidate_dates:
            continue
        matches = [
            (board, direction_index[(day, board)])
            for board in boards if (day, board) in direction_index
        ]
        if matches:
            exact_name_rows += 1
    sector_history = _scan_sector_history(direction_payload)
    project = Path(project_root)
    sector_stocks = _scan_json_snapshot_root(project / "data_cache" / "sector_stocks", "sector_membership_snapshots")
    sector_scores = _scan_json_snapshot_root(project / "reports" / "sector_scores", "sector_score_reports")
    linkage = _scan_linkage_reports(project, v9_candidate_dates)
    source_inventory_core = {
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
        "mode": MODE,
        "status": "planning_only_no_model_training",
        "dataset_sha256": dataset["dataset_sha256"],
        "feature_inventory": {"path": str(Path(feature_inventory_path).resolve()), "sha256": inventory_sha, "logical_sha256": feature_inventory["inventory_sha256"]},
        "candidate_archive": candidates,
        "direction_source": {
            "path": str(Path(direction_report_path).resolve()),
            "sha256": direction_sha,
            "date_count": len(direction_dates),
            "row_count": direction_payload.get("row_count"),
            "candidate_date_overlap_count": len(direction_dates & v9_candidate_dates),
            "exact_name_observed_rows": exact_name_rows,
            "strict_pit_eligible": False,
            "universe_vintage_status": (direction_payload.get("source_manifest") or {}).get("universe_vintage_status"),
        },
        "industry_sector_history": sector_history,
        "sector_membership_snapshots": sector_stocks,
        "sector_score_reports": sector_scores,
        "linkage_v2": linkage,
        **_safe_flags(),
    }
    source_inventory = _logical_artifact(source_inventory_core, "source_inventory_sha256")
    schema_contract = _schema_contract()
    schema_contract = _logical_artifact(schema_contract, "schema_contract_sha256")
    coverage_core = {
        "schema_version": PREPARATION_SCHEMA_VERSION,
        "mode": MODE,
        "status": "blocked_for_strict_pit_factor_expansion",
        "dataset_sha256": dataset["dataset_sha256"],
        "source_inventory_sha256": source_inventory["source_inventory_sha256"],
        "schema_contract_sha256": schema_contract["schema_contract_sha256"],
        "coverage_summary": {
            "v9_candidate_dates": len(dataset["source_manifest"]["candidate_sources"]),
            "v9_candidate_rows": len(dataset["feature_universe_records"]),
            "physical_candidate_source_dates": candidates["candidate_date_count"],
            "physical_candidate_source_rows": candidates["v9_manifest_row_count"] + candidates["extra_valid_row_count"],
            "extra_candidate_source_dates": candidates["extra_valid_file_count"],
            "extra_candidate_source_rows": candidates["extra_valid_row_count"],
            "v9_complete_intraday_bar_rows": candidates["v9_complete_intraday_bar_rows"],
            "v9_content_bound_no_future_intraday_bar_rows": candidates["v9_content_bound_no_future_intraday_bar_rows"],
            "v9_complete_intraday_bar_coverage_ratio": candidates["v9_complete_intraday_bar_rows"] / len(dataset["feature_universe_records"]),
            "strict_direction_rows": 0,
            "strict_linkage_rows": 0,
        },
        "availability_levels": {
            "replayable_content_bound_but_nonprospective": ["candidate_archive", "candidate_intraday_bars"],
            "partial": ["industry_sector_history", "sector_membership_snapshots", "sector_score_reports"],
            "unavailable_for_strict_replay": ["direction_stock_binding", "linkage_v2_daily_inputs"],
        },
        "blocking_facts": [
            "direction strict PIT remains zero because historical membership universe is not point-in-time versioned",
            "Linkage V2 strict usable rows remain zero because only single-day reports and no dated constituent/return/flow manifests exist",
            "extra candidate files are not label-bound and include non-trading/empty days; they are inventory-only",
            "candidate factor_snapshot nested as_of is blank and inherits outer content-bound source date; this is not prospective PIT evidence",
        ],
        "next_data_requirements": [
            "versioned daily candidate snapshots with embedded as_of and source capture timestamp",
            "content-addressed daily stock bars/technical inputs for every candidate row",
            "dated stock-to-industry membership snapshots with effective and capture dates",
            "daily Linkage V2 constituent weights, stock/sector returns, flow and quality inputs with per-file SHA",
        ],
        "future_comparison_ready": False,
        **_safe_flags(),
    }
    coverage = _logical_artifact(coverage_core, "coverage_report_sha256")
    for artifact, context in ((source_inventory, "candidate source inventory"), (schema_contract, "candidate schema contract"), (coverage, "candidate coverage report")):
        if _forbidden_keys(artifact):
            raise ValueError(f"{context} contains protected fields")
        validate_no_executable_instructions(artifact, context=context)
    return source_inventory, schema_contract, coverage


def write_candidate_data_preparation(
    dataset_path: Path | str,
    feature_inventory_path: Path | str,
    direction_report_path: Path | str,
    project_root: Path | str,
    output_root: Path | str,
) -> dict[str, Any]:
    destination = Path(output_root)
    if destination.exists():
        raise FileExistsError(f"candidate data preparation output exists: {destination}")
    source_inventory, schema_contract, coverage = build_candidate_data_preparation(
        dataset_path, feature_inventory_path, direction_report_path, project_root
    )
    destination.mkdir(parents=True)
    write_strict_json_atomic(destination / "source_inventory.json", source_inventory)
    write_strict_json_atomic(destination / "schema_contract.json", schema_contract)
    coverage = {
        **coverage,
        "artifacts": {
            "source_inventory": {"path": "source_inventory.json", "sha256": _sha256(destination / "source_inventory.json")},
            "schema_contract": {"path": "schema_contract.json", "sha256": _sha256(destination / "schema_contract.json")},
        },
    }
    core = {key: value for key, value in coverage.items() if key not in {"coverage_report_sha256", "disclaimer"}}
    coverage["coverage_report_sha256"] = canonical_sha256(core)
    write_strict_json_atomic(destination / "coverage_report.json", coverage)
    return coverage


def validate_candidate_data_preparation_artifacts(output_root: Path | str) -> dict[str, Any]:
    destination = Path(output_root)
    expected_files = {"source_inventory.json", "schema_contract.json", "coverage_report.json"}
    actual_files = {path.name for path in destination.iterdir() if path.is_file()}
    if actual_files != expected_files or any(path.is_dir() for path in destination.iterdir()):
        raise ValueError("candidate data preparation artifact file contract mismatch")
    source = load_strict_json(destination / "source_inventory.json")
    schema = load_strict_json(destination / "schema_contract.json")
    coverage = load_strict_json(destination / "coverage_report.json")
    for artifact, field in (
        (source, "source_inventory_sha256"),
        (schema, "schema_contract_sha256"),
        (coverage, "coverage_report_sha256"),
    ):
        core = {key: value for key, value in artifact.items() if key not in {field, "disclaimer"}}
        if artifact.get(field) != canonical_sha256(core):
            raise ValueError(f"candidate data preparation {field} mismatch")
        if any(artifact.get(key) is not False for key in _safe_flags()):
            raise ValueError("candidate data preparation safety flags mismatch")
        if _forbidden_keys(artifact):
            raise ValueError("candidate data preparation contains protected fields")
    if coverage.get("status") != "blocked_for_strict_pit_factor_expansion":
        raise ValueError("candidate data preparation coverage status mismatch")
    summary = coverage.get("coverage_summary") or {}
    if summary.get("strict_direction_rows") != 0 or summary.get("strict_linkage_rows") != 0:
        raise ValueError("candidate data preparation strict factor gate changed unexpectedly")
    refs = coverage.get("artifacts") or {}
    for key, filename in (("source_inventory", "source_inventory.json"), ("schema_contract", "schema_contract.json")):
        if refs.get(key, {}).get("path") != filename or refs[key].get("sha256") != _sha256(destination / filename):
            raise ValueError("candidate data preparation artifact SHA mismatch")
    if list(destination.glob("model*")) or list(destination.glob("registry*")):
        raise ValueError("candidate data preparation unexpectedly contains model artifacts")
    return {
        "v9_candidate_dates": summary.get("v9_candidate_dates"),
        "v9_candidate_rows": summary.get("v9_candidate_rows"),
        "physical_candidate_source_dates": summary.get("physical_candidate_source_dates"),
        "extra_candidate_source_dates": summary.get("extra_candidate_source_dates"),
        "strict_direction_rows": summary.get("strict_direction_rows"),
        "strict_linkage_rows": summary.get("strict_linkage_rows"),
    }
