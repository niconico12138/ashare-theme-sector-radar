"""Auditable source reconstruction for historical stock-ML shadow factors."""

from __future__ import annotations

from collections import Counter
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .contract import canonical_sha256
from .historical_research import validate_historical_research_dataset
from .schema import DISCLAIMER, MODE


SOURCE_CATALOG_SCHEMA_VERSION = "ml-stock-historical-factor-source-catalog-v1"
SOURCE_DATASET_SCHEMA_VERSION = "ml-stock-historical-factor-source-rebuild-v2"
SOURCE_REPORT_SCHEMA_VERSION = "ml-stock-historical-factor-source-rebuild-report-v2"
CLASSIFICATION = "historical_factor_source_reconstruction_research"
FORBIDDEN_FIELDS = frozenset(
    {
        "quant_score",
        "final_score",
        "v2_score",
        "selection_score",
        "selection_score_adjusted",
        "relevance_score",
        "legacy_relevance_score",
    }
)


def _safe_flags() -> dict[str, bool]:
    return {
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _code(value: Any) -> str:
    code = str(value or "").zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise ValueError("historical factor source candidate code is invalid")
    return code


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _logical_artifact(
    core: Mapping[str, Any], *, sha_field: str
) -> dict[str, Any]:
    return {**dict(core), sha_field: canonical_sha256(core), "disclaimer": DISCLAIMER}


def _load_candidate_rows(
    dataset: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in dataset["source_manifest"]["candidate_sources"]:
        path = Path(str(entry.get("path") or ""))
        payload, sha256 = load_strict_json_with_sha256(path)
        if sha256 != entry.get("sha256"):
            raise ValueError("historical factor candidate source SHA mismatch")
        day = str(entry.get("as_of_date") or "")
        if payload.get("as_of") != day:
            raise ValueError("historical factor candidate source as-of mismatch")
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or payload.get("candidate_count") != len(candidates):
            raise ValueError("historical factor candidate source count mismatch")
        sources.append({"as_of_date": day, "path": str(path.resolve()), "sha256": sha256})
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ValueError("historical factor candidate row must be an object")
            identity = (day, _code(candidate.get("code")))
            if identity in seen:
                raise ValueError(f"duplicate historical factor candidate identity: {identity}")
            seen.add(identity)
            boards = candidate.get("boards")
            board_types = candidate.get("board_types")
            boards = list(boards) if isinstance(boards, list) else []
            board_types = list(board_types) if isinstance(board_types, list) else []
            if len(boards) != len(board_types):
                raise ValueError("historical factor candidate board identity is incomplete")
            rows.append(
                {
                    "as_of_date": day,
                    "stock_code": identity[1],
                    "candidate_source_path": str(path.resolve()),
                    "candidate_source_sha256": sha256,
                    "board_identities": [
                        {"name": str(name), "type": str(board_type), "source": "candidate_archive"}
                        for name, board_type in zip(boards, board_types)
                    ],
                }
            )
    expected = {
        (str(row["as_of_date"]), str(row["stock_code"]).zfill(6))
        for row in dataset["feature_universe_records"]
    }
    if seen != expected:
        raise ValueError("historical factor candidate identities do not match v9 dataset")
    rows.sort(key=lambda row: (row["as_of_date"], row["stock_code"]))
    return rows, sources


def _load_direction_source(
    path: Path,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    payload, report_sha = load_strict_json_with_sha256(path)
    if payload.get("schema_version") != "industry_direction_shadow_range.v1":
        raise ValueError("historical direction source schema mismatch")
    if payload.get("mode") != MODE:
        raise ValueError("historical direction source is not paper/shadow")
    manifest = payload.get("source_manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("historical direction source manifest is missing")
    root = Path(str(manifest.get("root") or ""))
    documents = manifest.get("documents")
    if not root.is_dir() or not isinstance(documents, list):
        raise ValueError("historical direction physical source catalog is invalid")
    verified_documents: list[dict[str, Any]] = []
    for document in documents:
        if not isinstance(document, Mapping):
            raise ValueError("historical direction source document is invalid")
        document_path = root / str(document.get("relative_path") or "")
        sha256 = str(document.get("sha256") or "")
        if not document_path.is_file() or _sha256(document_path) != sha256:
            raise ValueError("historical direction physical source SHA mismatch")
        verified_documents.append(
            {
                "relative_path": str(document.get("relative_path")),
                "sha256": sha256,
                "first_date": str(document.get("first_date") or ""),
                "last_date": str(document.get("last_date") or ""),
            }
        )
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for daily in payload.get("daily_results") or []:
        day = str(daily.get("as_of_date") or "")
        for sector in daily.get("sectors") or []:
            name = str(sector.get("sector_name") or "")
            identity = (day, name)
            if not day or not name or identity in index:
                raise ValueError("historical direction identity is invalid or duplicated")
            feature_max_date = str(sector.get("feature_max_date") or "")
            if feature_max_date > day:
                raise ValueError("historical direction source contains future-dated features")
            index[identity] = dict(sector)
    if len(index) != payload.get("row_count"):
        raise ValueError("historical direction source row count mismatch")
    catalog = {
        "report": {"path": str(path.resolve()), "sha256": report_sha},
        "actual_start_date": payload.get("actual_start_date"),
        "actual_end_date": payload.get("actual_end_date"),
        "date_count": payload.get("date_count"),
        "row_count": payload.get("row_count"),
        "history_root": str(root.resolve()),
        "history_manifest_sha256": manifest.get("manifest_sha256"),
        "history_documents": verified_documents,
        "history_document_count": len(verified_documents),
        "universe_vintage_status": manifest.get("universe_vintage_status"),
        "source_strict_pit_eligible": manifest.get("strict_pit_eligible") is True,
        "universe_vintage_limitation": manifest.get("universe_vintage_limitation"),
    }
    return index, catalog


def _load_linkage_sources(paths: Sequence[Path]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    by_date: dict[str, dict[str, Any]] = {}
    catalog: list[dict[str, Any]] = []
    for path in paths:
        payload, sha256 = load_strict_json_with_sha256(path)
        day = str(payload.get("as_of_date") or "")
        if not day or payload.get("score_as_of_date") != day:
            raise ValueError("historical Linkage V2 source as-of mismatch")
        if day in by_date:
            raise ValueError("duplicate historical Linkage V2 source date")
        by_date[day] = payload
        selection = payload.get("direction_linkage_v2_selection_shadow")
        selected_count = selection.get("selected_count") if isinstance(selection, Mapping) else None
        catalog.append(
            {
                "as_of_date": day,
                "path": str(path.resolve()),
                "sha256": sha256,
                "selected_count": selected_count,
                "source_strict_pit_eligible": False,
                "limitation": "single-day report without a dated constituent/input manifest for the 99-day candidate archive",
            }
        )
    return by_date, catalog


def match_candidate_factor_sources(
    candidate: Mapping[str, Any],
    direction_index: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    direction_catalog: Mapping[str, Any],
    linkage_by_date: Mapping[str, Mapping[str, Any]],
    linkage_source_catalog: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Match exact identities while keeping merely observed values ineligible."""

    day = str(candidate["as_of_date"])
    board_identities = list(candidate.get("board_identities") or [])
    exact = []
    for board in board_identities:
        identity = (day, str(board.get("name") or ""))
        source = direction_index.get(identity)
        if source is not None:
            exact.append((board, source))
    reasons: list[str] = []
    if not any(key[0] == day for key in direction_index):
        reasons.append("direction_no_exact_as_of_source")
    elif not exact:
        reasons.append("direction_no_exact_board_name_match")
    if exact and any(str(board.get("type") or "") != "industry" for board, _ in exact):
        reasons.append("direction_board_type_semantics_mismatch")
    if not direction_catalog.get("source_strict_pit_eligible"):
        reasons.append("direction_source_universe_not_point_in_time")
    if len(exact) > 1:
        reasons.append("direction_multiple_exact_board_matches")
    direction_eligible = (
        len(exact) == 1
        and str(exact[0][0].get("type") or "") == "industry"
        and direction_catalog.get("source_strict_pit_eligible") is True
        and str(exact[0][1].get("feature_max_date") or "") <= day
    )
    observed = []
    for board, source in exact:
        observed.append(
            {
                "sector_name": str(source.get("sector_name") or ""),
                "sector_id": str(source.get("sector_id") or ""),
                "candidate_board_type": str(board.get("type") or ""),
                "direction_score_shadow": _finite(source.get("direction_score_shadow")),
                "time_series_score": _finite(source.get("time_series_score")),
                "cross_section_score": _finite(source.get("cross_section_score")),
                "rank_momentum_score": _finite(source.get("rank_momentum_score")),
                "feature_max_date": str(source.get("feature_max_date") or ""),
            }
        )
    linkage_source = linkage_by_date.get(day)
    if linkage_source is None:
        reasons.append("linkage_v2_no_exact_as_of_source")
    else:
        reasons.append("linkage_v2_no_dated_constituent_input_manifest")
    direction_report = direction_catalog.get("report")
    if not isinstance(direction_report, Mapping):
        raise ValueError("historical direction report provenance is missing")
    linkage_provenance = None
    if linkage_source is not None and linkage_source_catalog is not None:
        linkage_provenance = linkage_source_catalog.get(day)
    return {
        **dict(candidate),
        "direction": {
            "source": {
                "report_path": str(direction_report.get("path") or ""),
                "report_sha256": str(direction_report.get("sha256") or ""),
                "history_manifest_sha256": str(
                    direction_catalog.get("history_manifest_sha256") or ""
                ),
            },
            "observed_exact_name_matches": observed,
            "observed": bool(observed),
            "strict_pit_eligible": direction_eligible,
            "usable_value": (
                observed[0]["direction_score_shadow"] if direction_eligible else None
            ),
        },
        "linkage_v2": {
            "source": (
                {
                    "report_path": str(linkage_provenance.get("path") or ""),
                    "report_sha256": str(linkage_provenance.get("sha256") or ""),
                }
                if isinstance(linkage_provenance, Mapping)
                else None
            ),
            "observed_exact_as_of_report": linkage_source is not None,
            "strict_pit_eligible": False,
            "usable_value": None,
        },
        "usable_for_direction_ml": direction_eligible,
        "usable_for_linkage_v2_ml": False,
        "excluded_reason": sorted(set(reasons)),
    }


def validate_source_rebuilt_dataset(artifact: Mapping[str, Any]) -> None:
    expected = {
        "schema_version": SOURCE_DATASET_SCHEMA_VERSION,
        "mode": MODE,
        "status": "blocked_insufficient_strict_pit_coverage",
        "dataset_classification": CLASSIFICATION,
        **_safe_flags(),
    }
    if any(artifact.get(key) != value for key, value in expected.items()):
        raise ValueError("historical factor source-rebuilt safety contract mismatch")
    forbidden = _forbidden_keys(artifact)
    if forbidden:
        raise ValueError(f"historical factor source-rebuilt protected fields: {sorted(forbidden)}")
    rows = artifact.get("records")
    if not isinstance(rows, list) or artifact.get("counts", {}).get("candidate_rows") != len(rows):
        raise ValueError("historical factor source-rebuilt record count mismatch")
    for row in rows:
        direction_source = row.get("direction", {}).get("source")
        if (
            not isinstance(direction_source, Mapping)
            or not direction_source.get("report_path")
            or len(str(direction_source.get("report_sha256") or "")) != 64
            or len(str(direction_source.get("history_manifest_sha256") or "")) != 64
        ):
            raise ValueError("historical factor direction row provenance is missing")
        if row.get("linkage_v2", {}).get("usable_value") is not None:
            raise ValueError("historical factor source-rebuilt Linkage value is not proven")
        linkage_source = row.get("linkage_v2", {}).get("source")
        if row.get("linkage_v2", {}).get("observed_exact_as_of_report"):
            if (
                not isinstance(linkage_source, Mapping)
                or len(str(linkage_source.get("report_sha256") or "")) != 64
            ):
                raise ValueError("historical factor Linkage row provenance is missing")
        elif linkage_source is not None:
            raise ValueError("historical factor unavailable Linkage row has a source")
        if not row.get("excluded_reason"):
            raise ValueError("historical factor source-rebuilt exclusion reason is missing")
    core = {key: value for key, value in artifact.items() if key not in {"source_rebuilt_dataset_sha256", "disclaimer"}}
    if artifact.get("source_rebuilt_dataset_sha256") != canonical_sha256(core):
        raise ValueError("historical factor source-rebuilt logical SHA mismatch")
    validate_no_executable_instructions(artifact, context="historical factor source-rebuilt dataset")


def rebuild_historical_factor_sources(
    dataset: Mapping[str, Any],
    direction_report_path: Path | str,
    linkage_report_paths: Sequence[Path | str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Rebuild only exact, content-bound observations and emit a blocking gate."""

    validate_historical_research_dataset(dataset)
    candidates, candidate_sources = _load_candidate_rows(dataset)
    direction_index, direction_catalog = _load_direction_source(Path(direction_report_path))
    linkage_by_date, linkage_catalog = _load_linkage_sources(
        [Path(path) for path in linkage_report_paths]
    )
    linkage_source_catalog = {
        str(item["as_of_date"]): item for item in linkage_catalog
    }
    records = [
        match_candidate_factor_sources(
            candidate,
            direction_index,
            direction_catalog=direction_catalog,
            linkage_by_date=linkage_by_date,
            linkage_source_catalog=linkage_source_catalog,
        )
        for candidate in candidates
    ]
    reason_counts = Counter(
        reason for row in records for reason in row["excluded_reason"]
    )
    counts = {
        "candidate_dates": len({row["as_of_date"] for row in records}),
        "candidate_rows": len(records),
        "direction_exact_as_of_rows": sum(
            "direction_no_exact_as_of_source" not in row["excluded_reason"] for row in records
        ),
        "direction_exact_name_observed_rows": sum(row["direction"]["observed"] for row in records),
        "direction_strict_pit_eligible_rows": sum(row["usable_for_direction_ml"] for row in records),
        "linkage_exact_as_of_report_rows": sum(row["linkage_v2"]["observed_exact_as_of_report"] for row in records),
        "linkage_strict_pit_eligible_rows": sum(row["usable_for_linkage_v2_ml"] for row in records),
        "fully_usable_rows": sum(
            row["usable_for_direction_ml"] and row["usable_for_linkage_v2_ml"]
            for row in records
        ),
        "excluded_rows": sum(bool(row["excluded_reason"]) for row in records),
    }
    catalog_core = {
        "schema_version": SOURCE_CATALOG_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": CLASSIFICATION,
        "v9_dataset_sha256": dataset["dataset_sha256"],
        "candidate_sources": candidate_sources,
        "direction_source": direction_catalog,
        "linkage_v2_sources": linkage_catalog,
        **_safe_flags(),
    }
    catalog = _logical_artifact(catalog_core, sha_field="source_catalog_sha256")
    dataset_core = {
        "schema_version": SOURCE_DATASET_SCHEMA_VERSION,
        "mode": MODE,
        "status": "blocked_insufficient_strict_pit_coverage",
        "dataset_classification": CLASSIFICATION,
        "v9_dataset_sha256": dataset["dataset_sha256"],
        "source_catalog_sha256": catalog["source_catalog_sha256"],
        "missing_value_policy": "missing historical values remain null and carry excluded_reason; zero/current/future/fixture substitution is forbidden",
        "counts": counts,
        "excluded_reason_counts": dict(sorted(reason_counts.items())),
        "records": records,
        **_safe_flags(),
    }
    rebuilt = _logical_artifact(dataset_core, sha_field="source_rebuilt_dataset_sha256")
    validate_source_rebuilt_dataset(rebuilt)
    factor_allowed = (
        counts["direction_strict_pit_eligible_rows"] > 0
        and counts["linkage_strict_pit_eligible_rows"] > 0
        and counts["fully_usable_rows"] > 0
    )
    report_core = {
        "schema_version": SOURCE_REPORT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "blocked_insufficient_strict_pit_coverage",
        "dataset_classification": CLASSIFICATION,
        "v9_dataset_sha256": dataset["dataset_sha256"],
        "source_catalog_sha256": catalog["source_catalog_sha256"],
        "source_rebuilt_dataset_sha256": rebuilt["source_rebuilt_dataset_sha256"],
        "counts": counts,
        "coverage": {
            "direction_exact_name_observed_ratio": counts["direction_exact_name_observed_rows"] / counts["candidate_rows"],
            "direction_strict_pit_eligible_ratio": counts["direction_strict_pit_eligible_rows"] / counts["candidate_rows"],
            "linkage_strict_pit_eligible_ratio": counts["linkage_strict_pit_eligible_rows"] / counts["candidate_rows"],
        },
        "incremental_direction_linkage_experiment_allowed": factor_allowed,
        "decision": "blocked_do_not_validate_direction_or_linkage_v2",
        "blocking_reasons": [
            "candidate board identities are concept-typed while the available direction report is industry-typed",
            "direction source declares a non-point-in-time universe projected backward",
            "Linkage V2 is available only after the candidate archive end and lacks dated historical constituent/input manifests",
        ],
        "next_data_requirements": [
            "dated stock-to-sector membership snapshots with capture timestamps and content SHAs",
            "daily Linkage V2 stock/sector return, constituent-weight, flow, and quality inputs bound to exact as_of dates",
            "at least 60 eligible training dates plus purge and independent test dates before any incremental factor comparison",
        ],
        **_safe_flags(),
    }
    report = _logical_artifact(report_core, sha_field="rebuild_report_sha256")
    if _forbidden_keys(report):
        raise ValueError("historical factor source report contains protected fields")
    validate_no_executable_instructions(report, context="historical factor source rebuild report")
    return catalog, rebuilt, report


def write_historical_factor_source_rebuild(
    dataset_path: Path | str,
    direction_report_path: Path | str,
    linkage_report_paths: Sequence[Path | str],
    output_root: Path | str,
    *,
    replace_existing: bool = False,
) -> dict[str, Any]:
    destination = Path(output_root)
    expected_files = {
        "source_catalog.json",
        "source_rebuilt_dataset.json",
        "rebuild_report.json",
    }
    if destination.exists() and not replace_existing:
        raise FileExistsError(f"historical factor source rebuild output exists: {destination}")
    if destination.exists():
        actual_files = {path.name for path in destination.iterdir() if path.is_file()}
        if any(path.is_dir() for path in destination.iterdir()) or actual_files != expected_files:
            raise ValueError("historical factor source rebuild replacement target is not exact")
    dataset = load_strict_json(dataset_path)
    catalog, rebuilt, report = rebuild_historical_factor_sources(
        dataset, direction_report_path, linkage_report_paths
    )
    destination.mkdir(parents=True, exist_ok=replace_existing)
    write_strict_json_atomic(destination / "source_catalog.json", catalog)
    write_strict_json_atomic(destination / "source_rebuilt_dataset.json", rebuilt)
    report = {
        **report,
        "artifacts": {
            "source_catalog": {
                "path": str((destination / "source_catalog.json").resolve()),
                "sha256": _sha256(destination / "source_catalog.json"),
            },
            "source_rebuilt_dataset": {
                "path": str((destination / "source_rebuilt_dataset.json").resolve()),
                "sha256": _sha256(destination / "source_rebuilt_dataset.json"),
            },
        },
    }
    report_core = {key: value for key, value in report.items() if key not in {"rebuild_report_sha256", "disclaimer"}}
    report["rebuild_report_sha256"] = canonical_sha256(report_core)
    write_strict_json_atomic(destination / "rebuild_report.json", report)
    return report
