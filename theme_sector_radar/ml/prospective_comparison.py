"""Paper-only prospective comparison runner with hard data gates."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
import hashlib
import math
from pathlib import Path
from statistics import mean, pstdev
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
from .historical_factor_source_rebuild import FORBIDDEN_FIELDS
from .prospective_candidate_archive import (
    RAW_FEATURE_NAMES,
    verify_prospective_archive,
)
from .schema import DISCLAIMER, MODE


COMPARISON_SCHEMA_VERSION = "ml-stock-prospective-comparison-v1"
EVALUATION_INPUT_SCHEMA_VERSION = "ml-stock-prospective-evaluation-input-v1"
MIN_SNAPSHOT_DATES = 60
LABEL_HORIZON = "5d"
TOP_KS = (1, 3, 5)
COST_BPS = (0, 10, 25)

RULE_POSITIVE_FEATURES = (
    "ma20_slope_5",
    "relative_strength_20",
    "relative_strength_60",
    "risk_adjusted_return_20",
    "near_high_250",
    "breakout_distance_20",
    "close_strength_score",
    "amount_ratio_20",
    "liquidity_score",
    "volume_stability_score",
    "volume_burst_quality_score",
    "sector_support_score",
)
RULE_NEGATIVE_FEATURES = (
    "drawdown_depth_20",
    "atr10_atr50",
    "chasing_risk_score",
    "intraday_reversal_risk_score",
    "single_name_overheat_score",
)
RULE_GATE_FEATURES = (
    "ma20_slope_5",
    "relative_strength_20",
    "drawdown_depth_20",
    "close_strength_score",
)
HYBRID_RULE_WEIGHT = 0.30
HYBRID_ML_WEIGHT = 0.70

PRE_REGISTERED_CONTRACT: dict[str, Any] = {
    "contract_version": "prospective-comparison-contract-v1",
    "minimum_snapshot_dates": MIN_SNAPSHOT_DATES,
    "label_horizon": LABEL_HORIZON,
    "top_ks": list(TOP_KS),
    "cost_bps": list(COST_BPS),
    "strategies": ["rule-only", "ML-only", "rule-gated+ML/hybrid"],
    "rule_positive_features": list(RULE_POSITIVE_FEATURES),
    "rule_negative_features": list(RULE_NEGATIVE_FEATURES),
    "rule_gate_features": list(RULE_GATE_FEATURES),
    "hybrid_rule_weight": HYBRID_RULE_WEIGHT,
    "hybrid_ml_weight": HYBRID_ML_WEIGHT,
    "event_adjustment_enabled": False,
    "cross_section_group": "as_of_date",
    "missing_value_policy": "retain_null_and_missing_indicator; never impute unknown as zero",
    "ranking_policy": "cross_sectional_descending_score; ties by stock_code",
}
CONTRACT_SHA256 = canonical_sha256(PRE_REGISTERED_CONTRACT)

_PROTECTED_FIELDS = frozenset(
    set(FORBIDDEN_FIELDS)
    | {
        "direction_score_shadow",
        "linkage_selection_score",
        "quant_baseline_score_shadow",
        "linkage_v2_baseline_score_shadow",
        "ml_quant_score_shadow",
    }
)


def _safe_flags() -> dict[str, bool]:
    return {
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }


def _reject_protected(value: Any, *, context: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in _PROTECTED_FIELDS:
                raise ValueError(f"{context} contains protected field: {key}")
            _reject_protected(child, context=f"{context}.{key}")
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_protected(child, context=context)


def _finite(value: Any, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be finite numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{context} must be finite numeric")
    return result


def _source_identity(path: Path, sha256: str, *, context: str) -> dict[str, str]:
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"{context} source path must be an existing absolute file")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != sha256:
        raise ValueError(f"{context} source SHA mismatch")
    return {"path": str(path.resolve()), "sha256": actual}


def _validate_contract(contract: Mapping[str, Any] | None) -> dict[str, Any]:
    supplied = PRE_REGISTERED_CONTRACT if contract is None else dict(contract)
    if supplied != PRE_REGISTERED_CONTRACT:
        raise ValueError("prospective comparison parameter drift rejected")
    return {**PRE_REGISTERED_CONTRACT, "contract_sha256": CONTRACT_SHA256}


def _validate_event_manifest(event_manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    if event_manifest is None:
        return {
            "enabled": False,
            "status": "disabled_by_contract",
            "review_status": "not_applicable",
        }
    if event_manifest.get("enabled") is not False:
        raise ValueError("event adjustment is disabled by the comparison contract")
    if event_manifest.get("review_status") not in {"approved", "not_applicable"}:
        raise ValueError("unreviewed event adjustment manifest rejected")
    manifest_sha256 = str(event_manifest.get("manifest_sha256") or "")
    if event_manifest.get("review_status") == "approved" and (
        len(manifest_sha256) != 64
        or any(character not in "0123456789abcdef" for character in manifest_sha256)
    ):
        raise ValueError("approved event adjustment manifest SHA is invalid")
    return {
        "enabled": False,
        "status": "disabled_by_contract",
        "review_status": str(event_manifest.get("review_status")),
        "manifest_sha256": manifest_sha256,
    }


def _load_evaluation_source(
    path: Path,
    *,
    expected_sha256: str,
    source_type: str,
    as_of_dates: set[str],
) -> tuple[dict[str, str], dict[str, Any]]:
    identity = _source_identity(path, expected_sha256, context=source_type)
    payload, loaded_sha = load_strict_json_with_sha256(path)
    if (
        payload.get("schema_version") != EVALUATION_INPUT_SCHEMA_VERSION
        or payload.get("input_type") != source_type
        or loaded_sha != identity["sha256"]
    ):
        raise ValueError(f"{source_type} evaluation source schema mismatch")
    records = payload.get("records")
    if not isinstance(records, list) or any(not isinstance(row, Mapping) for row in records):
        raise ValueError(f"{source_type} evaluation records are invalid")
    _reject_protected(records, context=source_type)
    seen: set[tuple[str, str]] = set()
    for row in records:
        day = str(row.get("as_of_date") or "")
        code = str(row.get("stock_code") or "").zfill(6)
        if day not in as_of_dates or len(code) != 6 or not code.isdigit():
            raise ValueError(f"{source_type} record is outside the verified snapshot universe")
        identity_key = (day, code)
        if identity_key in seen:
            raise ValueError(f"duplicate {source_type} evaluation record")
        seen.add(identity_key)
    return identity, dict(payload)


def _load_labels(
    path: Path,
    *,
    expected_sha256: str,
    snapshot_by_date: Mapping[str, Mapping[str, Any]],
    as_of_dates: set[str],
    report_as_of_date: str,
) -> tuple[dict[str, str], dict[tuple[str, str], dict[str, Any]]]:
    identity, payload = _load_evaluation_source(
        path,
        expected_sha256=expected_sha256,
        source_type="labels_5d",
        as_of_dates=as_of_dates,
    )
    labels: dict[tuple[str, str], dict[str, Any]] = {}
    for row in payload["records"]:
        day = str(row["as_of_date"])
        code = str(row["stock_code"]).zfill(6)
        target = str(snapshot_by_date[day].get("target_5d") or "")
        label_as_of = str(row.get("label_as_of_date") or "")
        try:
            mature = date.fromisoformat(label_as_of) >= date.fromisoformat(target)
        except ValueError as exc:
            raise ValueError("5d label maturity date is invalid") from exc
        if not mature:
            raise ValueError(f"5d label is not mature: {day} {code}")
        if date.fromisoformat(label_as_of) > date.fromisoformat(report_as_of_date):
            raise ValueError(f"5d label is future data relative to report date: {day} {code}")
        labels[(day, code)] = {
            "future_return_5d": _finite(row.get("future_return_5d"), context="future_return_5d"),
            "future_excess_return_5d": _finite(
                row.get("future_excess_return_5d"), context="future_excess_return_5d"
            ),
            "label_as_of_date": label_as_of,
        }
    return identity, labels


def _load_predictions(
    path: Path, *, expected_sha256: str, as_of_dates: set[str], report_as_of_date: str
) -> tuple[dict[str, str], dict[tuple[str, str], float]]:
    identity, payload = _load_evaluation_source(
        path,
        expected_sha256=expected_sha256,
        source_type="predictions",
        as_of_dates=as_of_dates,
    )
    for field in (
        "model_artifact_sha256",
        "model_parameters_sha256",
        "feature_contract_sha256",
    ):
        value = str(payload.get(field) or "")
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"prediction source {field} is invalid")
    if payload.get("paper_shadow_only") is not True or payload.get("formal_predictor_compatible") is not False:
        raise ValueError("prediction source safety boundary mismatch")
    if payload.get("comparison_contract_sha256") != CONTRACT_SHA256:
        raise ValueError("prediction source comparison contract drift")
    available_at = payload.get("available_at")
    if available_at:
        try:
            available_date = datetime.fromisoformat(str(available_at)).date()
            report_date = date.fromisoformat(report_as_of_date)
        except ValueError as exc:
            raise ValueError("prediction source available_at is invalid") from exc
        if available_date > report_date:
            raise ValueError("prediction source is future data relative to report date")
    predictions: dict[tuple[str, str], float] = {}
    for row in payload["records"]:
        key = (str(row["as_of_date"]), str(row["stock_code"]).zfill(6))
        predictions[key] = _finite(row.get("prediction"), context="ML prediction")
    return identity, predictions


def _percentiles(rows: Sequence[Mapping[str, Any]], feature_name: str) -> dict[str, float]:
    values = [
        (str(row["stock_code"]), float(row["features"][feature_name]))
        for row in rows
        if not bool(row["missing_indicators"].get(feature_name))
        and row["features"].get(feature_name) is not None
    ]
    values.sort(key=lambda item: (item[1], item[0]))
    count = len(values)
    return {
        code: (index + 1) / count if count else 0.0
        for index, (code, _value) in enumerate(values)
    }


def _rule_scores(rows: Sequence[Mapping[str, Any]]) -> dict[str, tuple[float | None, bool]]:
    positive = {name: _percentiles(rows, name) for name in RULE_POSITIVE_FEATURES}
    negative = {name: _percentiles(rows, name) for name in RULE_NEGATIVE_FEATURES}
    output: dict[str, tuple[float | None, bool]] = {}
    for row in rows:
        code = str(row["stock_code"])
        components: list[float] = []
        for name, lookup in positive.items():
            if code in lookup:
                components.append(lookup[code])
        for name, lookup in negative.items():
            if code in lookup:
                components.append(1.0 - lookup[code])
        gate = all(
            not bool(row["missing_indicators"].get(name))
            and row["features"].get(name) is not None
            for name in RULE_GATE_FEATURES
        )
        output[code] = (mean(components) if components else None, gate)
    return output


def _rank_values(values: Mapping[str, float | None]) -> dict[str, float]:
    ordered = sorted(
        ((code, value) for code, value in values.items() if value is not None),
        key=lambda item: (-float(item[1]), item[0]),
    )
    count = len(ordered)
    return {code: (count - index) / count for index, (code, _value) in enumerate(ordered)}


def _spearman(pairs: Sequence[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    left = {str(index): value[0] for index, value in enumerate(pairs)}
    right = {str(index): value[1] for index, value in enumerate(pairs)}
    left_rank = _rank_values(left)
    right_rank = _rank_values(right)
    left_values = [left_rank[str(index)] for index in range(len(pairs))]
    right_values = [right_rank[str(index)] for index in range(len(pairs))]
    left_mean = mean(left_values)
    right_mean = mean(right_values)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_values, right_values)
    )
    left_scale = math.sqrt(sum((value - left_mean) ** 2 for value in left_values))
    right_scale = math.sqrt(sum((value - right_mean) ** 2 for value in right_values))
    return numerator / (left_scale * right_scale) if left_scale and right_scale else None


def _max_drawdown(returns: Sequence[float]) -> float:
    equity = 1.0
    peak = equity
    drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        if peak:
            drawdown = max(drawdown, 1.0 - equity / peak)
    return drawdown


def _metric_block(
    *,
    dates: Sequence[str],
    ranked: Mapping[str, Mapping[str, float]],
    labels: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for top_k in TOP_KS:
        selections: dict[str, list[str]] = {}
        gross_by_day: dict[str, float | None] = {}
        rank_ics: list[float] = []
        for day in dates:
            scores = ranked.get(day, {})
            selected = [code for code, _score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]]
            selections[day] = selected
            selected_returns = [labels[(day, code)]["future_excess_return_5d"] for code in selected if (day, code) in labels]
            gross_by_day[day] = mean(selected_returns) if selected_returns else None
            pairs = [
                (score, labels[(day, code)]["future_excess_return_5d"])
                for code, score in scores.items()
                if (day, code) in labels
            ]
            ic = _spearman(pairs)
            if ic is not None:
                rank_ics.append(ic)
        turnover_by_day: dict[str, float] = {}
        prior: set[str] = set()
        for day in dates:
            current = set(selections[day])
            denominator = max(1, top_k)
            turnover_by_day[day] = len(current.symmetric_difference(prior)) / (2.0 * denominator)
            prior = current
        cost_results = {}
        for cost_bps in COST_BPS:
            net_returns = [
                gross_by_day[day] - turnover_by_day[day] * cost_bps / 10000.0
                for day in dates
                if gross_by_day[day] is not None
            ]
            observed_turnover = [
                turnover_by_day[day]
                for day in dates
                if gross_by_day[day] is not None
            ]
            cost_results[str(cost_bps)] = {
                "mean_return": mean(net_returns) if net_returns else None,
                "win_rate": (
                    sum(value > 0 for value in net_returns) / len(net_returns)
                    if net_returns
                    else None
                ),
                "max_drawdown": _max_drawdown(net_returns) if net_returns else None,
                "turnover": mean(observed_turnover) if observed_turnover else None,
            }
        result[str(top_k)] = {
            "observed_dates": sum(value is not None for value in gross_by_day.values()),
            "rank_ic": mean(rank_ics) if rank_ics else None,
            "rank_ic_observations": len(rank_ics),
            "cost_bps": cost_results,
        }
    return result


def _quality_report(
    feature_rows_by_date: Mapping[str, Sequence[Mapping[str, Any]]],
    predictions: Mapping[tuple[str, str], float],
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for feature_name in RAW_FEATURE_NAMES:
        values: list[float] = []
        missing = 0
        for rows in feature_rows_by_date.values():
            for row in rows:
                if row["missing_indicators"].get(feature_name) or row["features"].get(feature_name) is None:
                    missing += 1
                else:
                    values.append(float(row["features"][feature_name]))
        report[feature_name] = {
            "observations": len(values),
            "missing_count": missing,
            "missing_rate": missing / (missing + len(values)) if missing + len(values) else 0.0,
            "mean": mean(values) if values else None,
            "std": pstdev(values) if len(values) > 1 else None,
        }
    prediction_values = list(predictions.values())
    report["ml_prediction"] = {
        "observations": len(prediction_values),
        "missing_count": 0,
        "missing_rate": 0.0,
        "mean": mean(prediction_values) if prediction_values else None,
        "std": pstdev(prediction_values) if len(prediction_values) > 1 else None,
    }
    return report


def _drift_report(
    feature_rows_by_date: Mapping[str, Sequence[Mapping[str, Any]]],
    predictions: Mapping[tuple[str, str], float],
) -> dict[str, Any]:
    dates = sorted(feature_rows_by_date)
    midpoint = max(1, len(dates) // 2)
    first, second = dates[:midpoint], dates[midpoint:]
    output: dict[str, Any] = {}
    for feature_name in RAW_FEATURE_NAMES:
        groups = []
        for subset in (first, second):
            values = [
                float(row["features"][feature_name])
                for day in subset
                for row in feature_rows_by_date[day]
                if not row["missing_indicators"].get(feature_name)
                and row["features"].get(feature_name) is not None
            ]
            groups.append(mean(values) if values else None)
        output[feature_name] = {
            "first_half_mean": groups[0],
            "second_half_mean": groups[1],
            "absolute_mean_shift": (
                abs(groups[1] - groups[0])
                if groups[0] is not None and groups[1] is not None
                else None
            ),
        }
    prediction_groups = [
        [predictions[(day, code)] for day in subset for code in {key[1] for key in predictions if key[0] == day} if (day, code) in predictions]
        for subset in (first, second)
    ]
    output["ml_prediction"] = {
        "first_half_mean": mean(prediction_groups[0]) if prediction_groups[0] else None,
        "second_half_mean": mean(prediction_groups[1]) if prediction_groups[1] else None,
        "absolute_mean_shift": (
            abs(mean(prediction_groups[1]) - mean(prediction_groups[0]))
            if prediction_groups[0] and prediction_groups[1]
            else None
        ),
    }
    return output


def _evaluate_complete(
    *,
    archive_root: Path,
    contract: Mapping[str, Any],
    event_manifest: Mapping[str, Any],
    labels: Mapping[tuple[str, str], Mapping[str, Any]],
    predictions: Mapping[tuple[str, str], float],
    label_identity: Mapping[str, str],
    prediction_identity: Mapping[str, str],
) -> dict[str, Any]:
    verified = verify_prospective_archive(archive_root)
    feature_rows_by_date: dict[str, list[dict[str, Any]]] = {}
    direction_status = defaultdict(int)
    linkage_status = defaultdict(int)
    for entry in verified["entries"]:
        day_root = Path(entry["manifest_path"]).parent
        schema_a, _ = load_strict_json_with_sha256(day_root / "schema_a.json")
        snapshot, _ = load_strict_json_with_sha256(day_root / "snapshot.json")
        feature_rows_by_date[entry["as_of_date"]] = list(schema_a["rows"])
        for source_type, counter in (("direction_inputs", direction_status), ("linkage_v2_inputs", linkage_status)):
            status = str(((snapshot.get("source_manifest") or {}).get(source_type) or {}).get("status") or "missing")
            counter[status] += 1

    rule_ranked: dict[str, dict[str, float]] = {}
    ml_ranked: dict[str, dict[str, float]] = {}
    hybrid_ranked: dict[str, dict[str, float]] = {}
    for day, rows in feature_rows_by_date.items():
        rule = _rule_scores(rows)
        rule_raw = {code: value for code, (value, _gate) in rule.items()}
        rule_rank = _rank_values(rule_raw)
        ml_raw = {
            row["stock_code"]: predictions[(day, row["stock_code"])]
            for row in rows
            if (day, row["stock_code"]) in predictions
        }
        ml_rank = _rank_values(ml_raw)
        hybrid_raw = {
            code: HYBRID_RULE_WEIGHT * rule_rank[code] + HYBRID_ML_WEIGHT * ml_rank[code]
            for code, (_score, gate) in rule.items()
            if gate and code in ml_rank and code in rule_rank
        }
        rule_ranked[day] = rule_rank
        ml_ranked[day] = ml_rank
        hybrid_ranked[day] = hybrid_raw

    dates = sorted(feature_rows_by_date)
    return {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "mode": MODE,
        "status": "evaluated",
        "contract": dict(contract),
        "contract_sha256": CONTRACT_SHA256,
        "event_adjustment": dict(event_manifest),
        "strategies": {
            "rule-only": _metric_block(dates=dates, ranked=rule_ranked, labels=labels),
            "ML-only": _metric_block(dates=dates, ranked=ml_ranked, labels=labels),
            "rule-gated+ML/hybrid": _metric_block(dates=dates, ranked=hybrid_ranked, labels=labels),
        },
        "data_quality": _quality_report(feature_rows_by_date, predictions),
        "drift": _drift_report(feature_rows_by_date, predictions),
        "source_status": {
            "direction_inputs": dict(sorted(direction_status.items())),
            "linkage_v2_inputs": dict(sorted(linkage_status.items())),
            "labels_5d": dict(label_identity),
            "predictions": dict(prediction_identity),
        },
        "counts": {
            "snapshot_dates": len(dates),
            "label_rows": len(labels),
            "prediction_rows": len(predictions),
        },
        **_safe_flags(),
    }


def run_prospective_comparison(
    *,
    archive_root: Path | str,
    output_root: Path | str,
    report_as_of_date: str,
    labels_path: Path | str | None = None,
    labels_sha256: str | None = None,
    predictions_path: Path | str | None = None,
    predictions_sha256: str | None = None,
    event_manifest: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run or block the pre-registered comparison; never trains a model."""

    try:
        normalized_report_as_of = date.fromisoformat(report_as_of_date).isoformat()
    except ValueError as exc:
        raise ValueError("comparison report_as_of_date is invalid") from exc
    if normalized_report_as_of != report_as_of_date:
        raise ValueError("comparison report_as_of_date is invalid")
    registered = _validate_contract(contract)
    event = _validate_event_manifest(event_manifest)
    verified = verify_prospective_archive(archive_root)
    entries = verified["entries"]
    snapshot_by_date = {entry["as_of_date"]: entry for entry in entries}
    as_of_dates = set(snapshot_by_date)
    blockers: list[str] = []
    if len(entries) < MIN_SNAPSHOT_DATES:
        blockers.append("minimum_60_real_snapshot_dates_not_met")
    if any(not entry["prospective_pit_eligible"] for entry in entries):
        blockers.append("snapshot_source_or_pit_gate_not_complete")
    if any(not entry.get("target_5d") for entry in entries):
        blockers.append("snapshot_5d_target_missing")
    if labels_path is None:
        blockers.append("mature_5d_labels_source_missing")
    elif not labels_sha256:
        blockers.append("mature_5d_labels_source_sha256_missing")
    if predictions_path is None:
        blockers.append("external_ml_predictions_source_missing")
    elif not predictions_sha256:
        blockers.append("external_ml_predictions_source_sha256_missing")

    label_identity: dict[str, str] = {}
    prediction_identity: dict[str, str] = {}
    labels: dict[tuple[str, str], dict[str, Any]] = {}
    predictions: dict[tuple[str, str], float] = {}
    expected = {
        (day, code)
        for day, entry in snapshot_by_date.items()
        for code in load_strict_json(
            Path(entry["manifest_path"]).parent / "snapshot.json"
        ).get("candidate_codes", [])
    }
    if not blockers and labels_path is not None:
        label_identity, labels = _load_labels(
            Path(labels_path).resolve(),
            expected_sha256=str(labels_sha256),
            snapshot_by_date=snapshot_by_date,
            as_of_dates=as_of_dates,
            report_as_of_date=report_as_of_date,
        )
        if set(labels) != expected:
            blockers.append("mature_5d_labels_do_not_cover_all_candidates")
    if not blockers and predictions_path is not None:
        prediction_identity, predictions = _load_predictions(
            Path(predictions_path).resolve(),
            expected_sha256=str(predictions_sha256),
            as_of_dates=as_of_dates,
            report_as_of_date=report_as_of_date,
        )
        if set(predictions) != expected:
            blockers.append("ML_predictions_do_not_cover_all_candidates")

    input_identity = {
        "archive_index_sha256": verified.get("index_sha256"),
        "label_source": label_identity,
        "prediction_source": prediction_identity,
        "contract_sha256": CONTRACT_SHA256,
        "event_adjustment": event,
        "report_as_of_date": report_as_of_date,
    }
    input_identity_sha256 = canonical_sha256(input_identity)
    if blockers:
        report_core = {
            "schema_version": COMPARISON_SCHEMA_VERSION,
            "mode": MODE,
            "status": "blocked",
            "report_as_of_date": report_as_of_date,
            "contract": registered,
            "event_adjustment": event,
            "blockers": sorted(set(blockers)),
            "counts": {"snapshot_dates": len(entries), "label_rows": len(labels), "prediction_rows": len(predictions)},
            "input_identity_sha256": input_identity_sha256,
            "strategies": ["rule-only", "ML-only", "rule-gated+ML/hybrid"],
            "metrics_available": False,
            **_safe_flags(),
        }
    else:
        report_core = _evaluate_complete(
            archive_root=Path(archive_root).resolve(),
            contract=registered,
            event_manifest=event,
            labels=labels,
            predictions=predictions,
            label_identity=label_identity,
            prediction_identity=prediction_identity,
        )
        report_core["report_as_of_date"] = report_as_of_date
        report_core["input_identity_sha256"] = input_identity_sha256
        report_core["metrics_available"] = True
    report = {**report_core, "report_sha256": canonical_sha256(report_core), "disclaimer": DISCLAIMER}
    validate_no_executable_instructions(report, context="prospective comparison")
    destination = Path(output_root).resolve()
    path = destination / "comparison_report.json"
    if path.exists():
        existing, existing_sha = load_strict_json_with_sha256(path)
        if existing != report:
            raise ValueError("duplicate comparison execution with changed inputs or parameters")
        return {"created": False, "path": str(path), "sha256": existing_sha, "report": existing}
    write_strict_json_atomic(path, report)
    _loaded, report_file_sha = load_strict_json_with_sha256(path)
    return {"created": True, "path": str(path), "sha256": report_file_sha, "report": report}


def validate_prospective_comparison_report(output_root: Path | str) -> dict[str, Any]:
    path = Path(output_root).resolve() / "comparison_report.json"
    report, physical_sha = load_strict_json_with_sha256(path)
    core = {key: value for key, value in report.items() if key not in {"report_sha256", "disclaimer"}}
    if report.get("report_sha256") != canonical_sha256(core):
        raise ValueError("prospective comparison report SHA mismatch")
    if any(report.get(key) is not False for key in _safe_flags()):
        raise ValueError("prospective comparison report safety flag mismatch")
    _reject_protected(report, context="prospective comparison report")
    return {
        "status": report.get("status"),
        "snapshot_dates": (report.get("counts") or {}).get("snapshot_dates"),
        "metrics_available": report.get("metrics_available") is True,
        "physical_sha256": physical_sha,
    }
