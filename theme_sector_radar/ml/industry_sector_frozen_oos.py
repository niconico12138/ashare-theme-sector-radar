"""Fail-closed frozen OOS runner for industry-sector ML candidates."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import math
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .contract import canonical_sha256
from .industry_sector_oos_readiness import (
    CANDIDATE_CONFIGS,
    STRICT_SPLIT_CONTRACT,
    calculate_drawdown_metrics,
)
from .industry_sector_prospective_collection import FROZEN_TEST_SIGNAL_DATES, SAFETY_FLAGS
from .industry_sector_shadow import (
    CLASSIFICATION,
    DISCLAIMER,
    MODE,
    _ndcg,
    _spearman,
    build_industry_sector_dataset,
    feature_names_for_profile,
    prepare_round_records,
    write_industry_sector_model_artifact,
)


EVENT_MANIFEST_SCHEMA = "ml-industry-sector-event-adjustment-manifest-v1"
ARM_SCHEMA = "ml-industry-sector-frozen-oos-arm-contract-v1"
REPORT_SCHEMA = "ml-industry-sector-frozen-oos-arm-report-v1"
EVENT_ARM_IDS = frozenset({
    "industry_ml_event_features",
    "industry_ml_event_adjustment",
})
PROTECTED_SCORE_FIELDS = frozenset({
    "quant_score",
    "final_score",
    "v2_score",
    "selection_score",
    "selection_score_adjusted",
})
REPORT_METRIC_FIELDS = (
    "gross_excess_return",
    "net_excess_return",
    "rank_ic",
    "ndcg",
    "win_rate",
    "turnover",
    "max_drawdown",
    "regime",
    "paired_deltas",
)


def _false_safety() -> dict[str, bool]:
    return {key: False for key in SAFETY_FLAGS}


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def _verify_ref(ref: Mapping[str, Any], expected: Path, root: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = Path(str(ref.get("path") or ""))
    if not path.is_absolute() or path.resolve() != expected.resolve() or not _within(path, root):
        return None, f"artifact_path_mismatch:{expected.name}"
    if not path.is_file():
        return None, f"artifact_missing:{expected.name}"
    payload, sha256 = load_strict_json_with_sha256(path)
    if sha256 != ref.get("sha256"):
        return None, f"artifact_sha_mismatch:{expected.name}"
    return payload, None


def validate_no_protected_score_fields(payload: Any) -> None:
    """Keep frozen industry artifacts separate from protected formal scores."""

    def visit(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if isinstance(key, str) and key.casefold() in PROTECTED_SCORE_FIELDS:
                    raise ValueError(f"{path} contains protected score field: {key}")
                visit(child, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(payload, "industry_sector_frozen_oos")


def _build_arm_contract(*, ready: bool) -> dict[str, Any]:
    state = "ready_pending_evaluation" if ready else "reserved_blocked"
    return {
        "schema_version": ARM_SCHEMA,
        "report_schema_version": REPORT_SCHEMA,
        "arms": [
            {
                "arm_id": "industry_ml_baseline",
                "label": "industry ML baseline",
                "enabled": True,
                "status": state,
                "event_source_read": False,
                "paper_only": True,
                "metric_fields": list(REPORT_METRIC_FIELDS),
            },
            {
                "arm_id": "industry_ml_event_features",
                "label": "industry ML plus event features",
                "enabled": False,
                "status": "disabled_event_input",
                "event_source_read": False,
                "paper_only": True,
                "metric_fields": list(REPORT_METRIC_FIELDS),
            },
            {
                "arm_id": "industry_ml_event_adjustment",
                "label": "industry ML plus event adjustment",
                "enabled": False,
                "status": "disabled_event_input",
                "event_source_read": False,
                "paper_only": True,
                "metric_fields": list(REPORT_METRIC_FIELDS),
            },
        ],
        "formal_chain_integrated": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
    }


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _validate_event_manifest(path: Path | str | None) -> tuple[dict[str, Any], list[str]]:
    if path is None:
        return {"enabled": False, "status": "disabled", "event_source_read": False}, []
    source = Path(path)
    payload, _sha256 = load_strict_json_with_sha256(source)
    errors: list[str] = []
    if payload.get("schema_version") != EVENT_MANIFEST_SCHEMA:
        errors.append("event_manifest_schema_mismatch")
    if payload.get("review_status") != "approved" or payload.get("approved_for_frozen_oos_ab") is not True:
        errors.append("event_manifest_not_reviewed_approved")
    if payload.get("arm_id") not in EVENT_ARM_IDS:
        errors.append("event_manifest_arm_not_b_or_c")
    pit_contract = payload.get("pit_contract")
    if not isinstance(pit_contract, Mapping) or pit_contract.get("strict_pit") is not True:
        errors.append("event_pit_strict_contract_missing")
    if not isinstance(pit_contract, Mapping) or pit_contract.get("effective_from_not_after_as_of") is not True:
        errors.append("event_pit_effective_date_contract_missing")
    if not isinstance(pit_contract, Mapping) or pit_contract.get("no_future_revision") is not True:
        errors.append("event_pit_future_revision_contract_missing")
    source_manifest_sha = payload.get("source_manifest_sha256")
    if not _is_sha256(source_manifest_sha):
        errors.append("event_source_manifest_sha_missing")
    record_time = payload.get("event_record_time_contract")
    if not isinstance(record_time, Mapping):
        errors.append("event_record_time_contract_missing")
    else:
        if record_time.get("as_of_field") != "as_of_date":
            errors.append("event_record_as_of_field_missing")
        if record_time.get("effective_from_field") != "effective_from":
            errors.append("event_record_effective_from_field_missing")
    if errors:
        return {
            "enabled": True,
            "status": "rejected",
            "manifest_path": str(source.resolve()),
            "event_source_read": False,
        }, errors
    adjustment = payload.get("adjustment_artifact") or {}
    adjustment_path = Path(str(adjustment.get("path") or ""))
    if not adjustment_path.is_absolute() or not adjustment_path.is_file():
        errors.append("event_adjustment_artifact_missing")
    elif hashlib.sha256(adjustment_path.read_bytes()).hexdigest() != adjustment.get("sha256"):
        errors.append("event_adjustment_artifact_sha_mismatch")
    return {
        "enabled": True,
        "status": "approved" if not errors else "rejected",
        "manifest_path": str(source.resolve()),
        "event_source_read": not errors,
    }, errors


def frozen_oos_preflight(
    status_path: Path | str,
    *,
    event_adjustment_manifest: Path | str | None = None,
) -> dict[str, Any]:
    status_source = Path(status_path).resolve(strict=True)
    collection_root = status_source.parent
    status, status_sha = load_strict_json_with_sha256(status_source)
    errors: list[str] = []
    blocked: list[str] = []
    if status.get("schema_version") != "ml-industry-sector-prospective-collection-status-v1":
        errors.append("prospective_status_schema_mismatch")
    if status.get("frozen_signal_dates") != list(FROZEN_TEST_SIGNAL_DATES):
        errors.append("frozen_signal_date_drift")
    if any(status.get(key) is not False for key in SAFETY_FLAGS):
        errors.append("prospective_status_safety_flags_not_false")

    immutable_count = 0
    contract, error = _verify_ref(
        status.get("contract") or {}, collection_root / "collection_contract.json", collection_root
    )
    if error:
        errors.append(error)
    else:
        immutable_count += 1
        if contract.get("signal_dates") != list(FROZEN_TEST_SIGNAL_DATES):
            errors.append("collection_contract_date_drift")

    candidate_freeze, error = _verify_ref(
        status.get("candidate_freeze") or {}, collection_root / "candidate_freeze.json", collection_root
    )
    if error:
        errors.append(error)
    else:
        immutable_count += 1
        expected_configs = [dict(config) for config in CANDIDATE_CONFIGS]
        if candidate_freeze.get("candidate_configs") != expected_configs:
            errors.append("candidate_parameter_drift")
        if candidate_freeze.get("candidate_configs_sha256") != canonical_sha256(CANDIDATE_CONFIGS):
            errors.append("candidate_parameter_sha_drift")
        if candidate_freeze.get("status") != "frozen_not_trained":
            errors.append("candidate_freeze_status_mismatch")

    snapshots = status.get("snapshots") or {}
    for signal_date in FROZEN_TEST_SIGNAL_DATES:
        refs = snapshots.get(signal_date) or {}
        snapshot, snapshot_error = _verify_ref(
            refs.get("snapshot") or {}, collection_root / "snapshots" / f"{signal_date}.json", collection_root
        )
        manifest, manifest_error = _verify_ref(
            refs.get("manifest") or {}, collection_root / "manifests" / f"{signal_date}.manifest.json", collection_root
        )
        if snapshot_error:
            errors.append(snapshot_error)
        else:
            immutable_count += 1
        if manifest_error:
            errors.append(manifest_error)
        else:
            immutable_count += 1
        if snapshot and snapshot.get("signal_date") != signal_date:
            errors.append(f"snapshot_date_drift:{signal_date}")
        if manifest and snapshot:
            if manifest.get("signal_date") != signal_date:
                errors.append(f"manifest_date_drift:{signal_date}")
            if manifest.get("snapshot", {}).get("sha256") != refs.get("snapshot", {}).get("sha256"):
                errors.append(f"manifest_snapshot_sha_mismatch:{signal_date}")

    maturity = status.get("maturity") or []
    maturity_by_date = {str(item.get("signal_date")): item for item in maturity}
    for signal_date in FROZEN_TEST_SIGNAL_DATES:
        item = maturity_by_date.get(signal_date)
        if not item:
            errors.append(f"maturity_missing:{signal_date}")
            continue
        observed = item.get("observed_future_trading_dates") or []
        if item.get("label_horizon_trading_days") != 5:
            errors.append(f"maturity_horizon_drift:{signal_date}")
        if item.get("observed_future_trading_day_count") != len(observed):
            errors.append(f"maturity_count_mismatch:{signal_date}")
        if item.get("label_mature") is not True or len(observed) != 5:
            blocked.append(f"label_not_mature:{signal_date}:{len(observed)}/5")
        elif item.get("label_maturity_date") != observed[-1]:
            errors.append(f"maturity_date_mismatch:{signal_date}")

    if status.get("source_complete") is not True:
        blocked.append("source_not_complete")
    if status.get("snapshot_sha_replay_passed") is not True:
        errors.append("source_snapshot_replay_not_passed")
    if status.get("all_test_labels_mature") is not True:
        blocked.append("all_test_labels_not_mature")
    if status.get("collection_ready") is not True:
        blocked.append("prospective_collection_not_ready")
    if status.get("status") != "ready_for_frozen_candidate_evaluation":
        blocked.append(f"prospective_status:{status.get('status')}")

    event_state, event_errors = _validate_event_manifest(event_adjustment_manifest)
    errors.extend(event_errors)
    ready = not errors and not blocked and immutable_count == 10
    if errors:
        result_status = "rejected_frozen_oos_preflight"
    elif blocked:
        result_status = "blocked_frozen_oos_not_ready"
    else:
        result_status = "ready_for_frozen_oos_evaluation"
    return {
        "schema_version": "ml-industry-sector-frozen-oos-preflight-v1",
        "mode": MODE,
        "status": result_status,
        "ready": ready,
        "prospective_status_path": str(status_source),
        "prospective_status_sha256": status_sha,
        "immutable_file_count_verified": immutable_count,
        "candidate_ids": [config["candidate_id"] for config in CANDIDATE_CONFIGS],
        "frozen_test_signal_dates": list(FROZEN_TEST_SIGNAL_DATES),
        "blocking_reasons": sorted(set(blocked)),
        "integrity_errors": sorted(set(errors)),
        "event_adjustment": event_state,
        "event_ab": {
            "schema_version": REPORT_SCHEMA,
            "event_input_default_enabled": False,
            "event_source_read": event_state.get("event_source_read", False),
            "arms": _build_arm_contract(ready=ready)["arms"][1:],
        },
        "arm_contract": _build_arm_contract(ready=ready),
        "candidate_model_training_run": False,
        **_false_safety(),
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "disclaimer": DISCLAIMER,
    }


def evaluate_frozen_scores(
    records: Sequence[Mapping[str, Any]],
    scores_by_identity: Mapping[tuple[str, str], float],
    *,
    top_k_values: Sequence[int] = (3, 5, 7),
    cost_bps_values: Sequence[float] = (0.0, 10.0, 25.0),
) -> dict[str, Any]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        identity = (str(row["as_of_date"]), str(row["sector_name"]))
        if identity not in scores_by_identity:
            raise ValueError(f"missing frozen OOS score: {identity}")
        by_date[identity[0]].append({
            "sector_name": identity[1],
            "score": float(scores_by_identity[identity]),
            "label": float(row["training_label"]),
            "raw_return": float(row["future_return_5d"]),
            "regime": str(row["market_regime"]),
        })
    result: dict[str, Any] = {}
    for top_k in top_k_values:
        daily: list[dict[str, Any]] = []
        prior: set[str] | None = None
        for day, rows in sorted(by_date.items()):
            selected = sorted(rows, key=lambda row: (-row["score"], row["sector_name"]))[:top_k]
            current = {row["sector_name"] for row in selected}
            turnover = 0.0 if prior is None else 1.0 - len(prior & current) / max(len(prior), len(current), 1)
            prior = current
            ic = _spearman([row["score"] for row in rows], [row["label"] for row in rows])
            ndcg = _ndcg([row["score"] for row in rows], [row["label"] for row in rows], top_k)
            daily.append({
                "date": day,
                "gross_excess_return": mean(row["label"] for row in selected),
                "gross_raw_return": mean(row["raw_return"] for row in selected),
                "win_rate": sum(row["raw_return"] > 0 for row in selected) / len(selected),
                "turnover": turnover,
                "rank_ic": ic,
                "ndcg": ndcg,
                "regime": selected[0]["regime"],
            })
        cost_scenarios = {}
        for cost_bps in cost_bps_values:
            cost_rate = float(cost_bps) / 10000.0
            net_excess = [row["gross_excess_return"] - cost_rate * row["turnover"] for row in daily]
            cost_scenarios[str(float(cost_bps))] = {
                "cost_bps": float(cost_bps),
                "mean_net_excess_return": mean(net_excess) if net_excess else None,
                "net_excess_path": calculate_drawdown_metrics(net_excess),
            }
        regime = {}
        for regime_name in ("risk_on", "mixed", "risk_off"):
            rows = [row for row in daily if row["regime"] == regime_name]
            regime[regime_name] = {
                "date_count": len(rows),
                "mean_gross_excess_return": mean(row["gross_excess_return"] for row in rows) if rows else None,
                "win_rate": mean(row["win_rate"] for row in rows) if rows else None,
            }
        result[f"top{top_k}"] = {
            "date_count": len(daily),
            "mean_gross_excess_return": mean(row["gross_excess_return"] for row in daily) if daily else None,
            "mean_gross_raw_return": mean(row["gross_raw_return"] for row in daily) if daily else None,
            "rank_ic": mean(row["rank_ic"] for row in daily if row["rank_ic"] is not None) if daily else None,
            "ndcg": mean(row["ndcg"] for row in daily if row["ndcg"] is not None) if daily else None,
            "win_rate": mean(row["win_rate"] for row in daily) if daily else None,
            "turnover": mean(row["turnover"] for row in daily) if daily else None,
            "gross_excess_path": calculate_drawdown_metrics([row["gross_excess_return"] for row in daily]),
            "gross_raw_path": calculate_drawdown_metrics([row["gross_raw_return"] for row in daily]),
            "cost_scenarios": cost_scenarios,
            "regime": regime,
            "daily": daily,
        }
    return result


def paired_candidate_comparison(candidate_reports: Mapping[str, Mapping[str, Any]], *, baseline_id: str) -> dict[str, Any]:
    if baseline_id not in candidate_reports:
        raise ValueError("paired comparison baseline is missing")
    baseline = candidate_reports[baseline_id]
    comparisons: dict[str, Any] = {}
    for candidate_id, report in candidate_reports.items():
        if candidate_id == baseline_id:
            continue
        per_top_k = {}
        for metric_key in ("top3", "top5", "top7"):
            base_daily = {row["date"]: row for row in baseline[metric_key]["daily"]}
            candidate_daily = {row["date"]: row for row in report[metric_key]["daily"]}
            if set(base_daily) != set(candidate_daily):
                raise ValueError("paired candidate dates differ")
            deltas = [
                candidate_daily[day]["gross_excess_return"] - base_daily[day]["gross_excess_return"]
                for day in sorted(base_daily)
            ]
            per_top_k[metric_key] = {
                "paired_date_count": len(deltas),
                "mean_gross_excess_delta": mean(deltas) if deltas else None,
                "candidate_win_rate_vs_baseline": sum(value > 0 for value in deltas) / len(deltas) if deltas else None,
                "rank_ic_delta": report[metric_key]["rank_ic"] - baseline[metric_key]["rank_ic"],
                "ndcg_delta": report[metric_key]["ndcg"] - baseline[metric_key]["ndcg"],
                "max_drawdown_delta": (
                    report[metric_key]["gross_excess_path"]["max_drawdown"]
                    - baseline[metric_key]["gross_excess_path"]["max_drawdown"]
                ),
            }
        comparisons[candidate_id] = per_top_k
    return {"baseline_id": baseline_id, "comparisons": comparisons}


def _run_ready_evaluation(
    source_root: Path | str,
    output_root: Path | str,
    model_root: Path | str,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    from .ranker import prepare_prediction_matrix, train_lambdarank

    dataset = build_industry_sector_dataset(source_root)
    test_dates = set(FROZEN_TEST_SIGNAL_DATES)
    validation_end = STRICT_SPLIT_CONTRACT["validation_signal_window"]["end"]
    test_start = FROZEN_TEST_SIGNAL_DATES[0]
    train_pool = [
        row for row in dataset["records"]
        if row["as_of_date"] <= validation_end and row["training_label_end_date"] < test_start
    ]
    test_rows = [row for row in dataset["records"] if row["as_of_date"] in test_dates]
    if {row["as_of_date"] for row in test_rows} != test_dates:
        raise ValueError("frozen OOS test labels are incomplete after ready preflight")

    candidate_reports: dict[str, Any] = {}
    model_artifacts: dict[str, Any] = {}
    for config in CANDIDATE_CONFIGS:
        feature_names = feature_names_for_profile(str(config["feature_profile"]))
        available_dates = sorted({row["as_of_date"] for row in train_pool})
        selected_dates = (
            available_dates[-int(config["max_train_dates"]):]
            if config.get("max_train_dates") else available_dates
        )
        if len(selected_dates) < int(config["min_train_dates"]):
            raise ValueError(f"candidate has insufficient frozen training dates: {config['candidate_id']}")
        selected = [row for row in train_pool if row["as_of_date"] in set(selected_dates)]
        prepared = prepare_round_records(selected, feature_names)
        model = train_lambdarank(
            prepared,
            feature_names=feature_names,
            relevance_levels=int(config["relevance_levels"]),
            n_estimators=int(config["n_estimators"]),
            learning_rate=float(config["learning_rate"]),
            num_leaves=int(config["num_leaves"]),
            random_state=int(config["random_state"]),
        )
        prepared_test = prepare_round_records(test_rows, feature_names)
        matrix = prepare_prediction_matrix(prepared_test, feature_names=feature_names)
        raw_scores = model.booster.predict(matrix["features"])
        scores = {
            (str(row["as_of_date"]), str(row["sector_name"])): float(score)
            for row, score in zip(matrix["records"], raw_scores)
        }
        candidate_id = str(config["candidate_id"])
        metrics = evaluate_frozen_scores(test_rows, scores)
        top3 = metrics["top3"]
        candidate_reports[candidate_id] = {
            "candidate_id": candidate_id,
            "arm_id": "industry_ml_baseline",
            "frozen_signal_dates": list(FROZEN_TEST_SIGNAL_DATES),
            "dataset_sha256": dataset["dataset_sha256"],
            "source_status_sha256": preflight["prospective_status_sha256"],
            "metric_summary": {
                "gross_excess_return": top3["mean_gross_excess_return"],
                "net_excess_return": {
                    cost: scenario["mean_net_excess_return"]
                    for cost, scenario in top3["cost_scenarios"].items()
                },
                "rank_ic": top3["rank_ic"],
                "ndcg": top3["ndcg"],
                "win_rate": top3["win_rate"],
                "turnover": top3["turnover"],
                "max_drawdown": top3["gross_excess_path"]["max_drawdown"],
                "regime": top3["regime"],
                "paired_deltas": None,
            },
            **metrics,
        }
        model_artifacts[candidate_id] = write_industry_sector_model_artifact(
            model,
            Path(model_root) / candidate_id,
            dataset_sha256=dataset["dataset_sha256"],
            feature_profile=str(config["feature_profile"]),
            experiment={"frozen_oos": True, **dict(config)},
        )

    paired = paired_candidate_comparison(
        candidate_reports, baseline_id="round28_low_complexity10_v1"
    )
    arm_reports = {
        "industry_ml_baseline": {
            "arm_id": "industry_ml_baseline",
            "enabled": True,
            "status": "evaluated",
            "event_source_read": False,
            "candidate_reports": candidate_reports,
            "paired_deltas": paired,
        },
        "industry_ml_event_features": {
            "arm_id": "industry_ml_event_features",
            "enabled": False,
            "status": "disabled_event_input",
            "event_source_read": False,
            "candidate_reports": None,
            "paired_deltas": None,
        },
        "industry_ml_event_adjustment": {
            "arm_id": "industry_ml_event_adjustment",
            "enabled": False,
            "status": "disabled_event_input",
            "event_source_read": False,
            "candidate_reports": None,
            "paired_deltas": None,
        },
    }
    report = {
        "schema_version": "ml-industry-sector-frozen-oos-evaluation-v2",
        "arm_report_schema": REPORT_SCHEMA,
        "mode": MODE,
        "status": "paper_oos_evaluated_no_promotion",
        "dataset_classification": CLASSIFICATION,
        "frozen_test_signal_dates": list(FROZEN_TEST_SIGNAL_DATES),
        "preflight": dict(preflight),
        "candidate_reports": candidate_reports,
        "paired_candidate_comparison": paired,
        "arm_contract": _build_arm_contract(ready=True),
        "arm_reports": arm_reports,
        "model_artifacts": model_artifacts,
        "event_ab": preflight["event_ab"],
        "event_adjustment": preflight["event_adjustment"],
        "candidate_model_training_run": True,
        **_false_safety(),
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "disclaimer": DISCLAIMER,
    }
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    validate_no_executable_instructions(report, context="frozen industry OOS evaluation")
    validate_no_protected_score_fields(report)
    write_strict_json_atomic(output / "frozen_oos_evaluation.json", report)
    return report


def run_frozen_oos_evaluation(
    status_path: Path | str,
    source_root: Path | str,
    output_root: Path | str,
    model_root: Path | str,
    *,
    event_adjustment_manifest: Path | str | None = None,
) -> dict[str, Any]:
    preflight = frozen_oos_preflight(
        status_path, event_adjustment_manifest=event_adjustment_manifest
    )
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)
    readiness_path = output / "frozen_oos_evaluation_readiness.json"
    if not preflight["ready"]:
        validate_no_executable_instructions(preflight, context="frozen industry OOS readiness")
        write_strict_json_atomic(readiness_path, preflight)
        return preflight
    write_strict_json_atomic(readiness_path, preflight)
    return _run_ready_evaluation(source_root, output_root, model_root, preflight)
