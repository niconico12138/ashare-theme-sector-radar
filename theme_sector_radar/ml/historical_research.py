"""Non-promotable historical reconstruction research for the ML shadow ranker."""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .contract import canonical_sha256, require_finite
from .ranker import RankerModel, walk_forward_ranker_predictions
from .schema import DISCLAIMER, MODE


HISTORICAL_DATASET_SCHEMA_VERSION = "ml-stock-historical-research-dataset-v1"
HISTORICAL_MODEL_SCHEMA_VERSION = "ml-stock-historical-research-model-v1"
HISTORICAL_DATASET_CLASSIFICATION = "historical_reconstruction_research"
HISTORICAL_LABEL_DEFINITION = "historical_forward_5d_stock_return"
HISTORICAL_LABEL_LINEAGE_STATUS = (
    "forward_summary_prices_replayed_source_bars_not_content_addressed"
)
HISTORICAL_FEATURE_NAMES = (
    "ma20_slope_5",
    "near_high_250",
    "contraction_score",
    "atr10_atr50",
    "range10_range20",
    "range20_range60",
    "amount_ratio_20",
    "liquidity_score",
    "chasing_risk_score",
    "drawdown_depth_20",
    "breakout_distance_20",
    "relative_strength_20",
    "relative_strength_60",
    "risk_adjusted_return_20",
    "volume_stability_score",
    "trend_persistence_score",
    "short_emotion_heat_score",
    "limit_attention_score",
    "intraday_reversal_risk_score",
    "close_strength_score",
    "volume_burst_quality_score",
    "single_name_overheat_score",
    "short_burst_emotion_score_v1",
    "short_burst_emotion_score_v2",
    "sector_support_score",
)
HISTORICAL_FEATURE_PROFILES = {
    "all_v1": HISTORICAL_FEATURE_NAMES,
    "stability_core_v1": (
        "contraction_score",
        "range10_range20",
        "drawdown_depth_20",
        "breakout_distance_20",
        "volume_stability_score",
        "trend_persistence_score",
        "limit_attention_score",
        "intraday_reversal_risk_score",
        "close_strength_score",
        "volume_burst_quality_score",
        "sector_support_score",
    ),
}
_PROTECTED_SCORE_NAMES = frozenset(
    {
        "quant_score",
        "final_score",
        "v2_score",
        "selection_score",
        "selection_score_adjusted",
    }
)
_SHA256 = re.compile(r"[0-9a-f]{64}")


def historical_feature_schema_sha256(
    feature_names: Sequence[str] = HISTORICAL_FEATURE_NAMES,
) -> str:
    return canonical_sha256(
        {
            "schema_version": "ml-stock-historical-research-features-v1",
            "feature_names": list(feature_names),
        }
    )


def _canonical_date(value: Any, *, context: str) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{context} must be a canonical ISO date") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{context} must be a canonical ISO date")
    return text


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def _code(value: Any, *, context: str) -> str:
    code = str(value or "").zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"{context} stock code is invalid")
    return code


def _load_calendar(path: Path) -> tuple[list[str], str]:
    payload, sha256 = load_strict_json_with_sha256(path)
    raw_dates = payload.get("dates") if isinstance(payload, Mapping) else None
    if not isinstance(raw_dates, list):
        raise ValueError("historical research calendar dates are missing")
    dates = [
        _canonical_date(value, context="historical research calendar date")
        for value in raw_dates
    ]
    if not dates or dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("historical research calendar must be sorted and unique")
    return dates, sha256


def _extract_features(candidate: Mapping[str, Any]) -> tuple[dict[str, float], float]:
    snapshot = candidate.get("factor_snapshot")
    rows = snapshot.get("factors") if isinstance(snapshot, Mapping) else None
    if not isinstance(rows, list):
        rows = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        factor_id = str(row.get("factor_id") or "")
        if factor_id in by_id:
            raise ValueError(f"duplicate historical feature factor: {factor_id}")
        by_id[factor_id] = row
    features: dict[str, float] = {}
    observed = 0
    for name in HISTORICAL_FEATURE_NAMES:
        row = by_id.get(name)
        value = _finite(row.get("raw_value")) if isinstance(row, Mapping) else None
        if value is not None:
            observed += 1
        features[name] = value if value is not None else 0.0
    return features, observed / len(HISTORICAL_FEATURE_NAMES)


def _rule_baseline(candidate: Mapping[str, Any]) -> float | None:
    for name in ("selection_score_adjusted", "selection_score", "final_score"):
        value = _finite(candidate.get(name))
        if value is not None:
            return value
    return None


def _verify_source_entry(entry: Mapping[str, Any], *, context: str) -> None:
    path = Path(str(entry.get("path") or ""))
    expected = str(entry.get("sha256") or "").lower()
    if not path.is_absolute() or not path.is_file() or not _SHA256.fullmatch(expected):
        raise ValueError(f"{context} physical identity is invalid")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"{context} physical identity changed")


def build_historical_research_dataset(
    candidate_root: Path | str,
    forward_root: Path | str,
    calendar_path: Path | str,
    *,
    _validate: bool = True,
) -> dict[str, Any]:
    """Build a real historical dataset that can never satisfy the formal PIT gate."""

    candidate_root = Path(candidate_root).resolve()
    forward_root = Path(forward_root).resolve()
    calendar_path = Path(calendar_path).resolve()
    if not candidate_root.is_dir() or not forward_root.is_dir():
        raise ValueError("historical research source root is missing")
    calendar_dates, calendar_sha = _load_calendar(calendar_path)
    calendar_index = {day: index for index, day in enumerate(calendar_dates)}
    feature_universe: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    baselines: list[dict[str, Any]] = []
    candidate_sources: list[dict[str, Any]] = []
    forward_sources: list[dict[str, Any]] = []

    for candidate_path in sorted(
        candidate_root.glob("*/top30_candidates.intraday_backfilled.json")
    ):
        day = _canonical_date(candidate_path.parent.name, context="candidate directory")
        candidate_payload, candidate_sha = load_strict_json_with_sha256(candidate_path)
        if candidate_payload.get("as_of") != day:
            raise ValueError("candidate source date mismatch")
        candidates = candidate_payload.get("candidates")
        if (
            not isinstance(candidates, list)
            or candidate_payload.get("candidate_count") != len(candidates)
        ):
            raise ValueError("candidate source count mismatch")
        day_index = calendar_index.get(day)
        if day_index is None or day_index + 5 >= len(calendar_dates):
            continue
        maturity_day = calendar_dates[day_index + 5]
        forward_path = forward_root / f"{day}.json"
        if not forward_path.is_file():
            continue
        forward_payload, forward_sha = load_strict_json_with_sha256(forward_path)
        if forward_payload.get("as_of") != day:
            raise ValueError("forward source date mismatch")
        generated_text = str(forward_payload.get("generated_at") or "")
        try:
            generated = datetime.fromisoformat(generated_text)
        except ValueError as exc:
            raise ValueError("forward source generated_at is invalid") from exc
        items = forward_payload.get("items")
        if not isinstance(items, list):
            raise ValueError("forward source items are missing")
        if generated.date() < date.fromisoformat(maturity_day):
            if any(
                isinstance(item, Mapping) and _finite(item.get("5d")) is not None
                for item in items
            ):
                raise ValueError("forward source predates label maturity")
            continue
        labels: dict[str, float] = {}
        for item in items:
            if not isinstance(item, Mapping):
                continue
            if item.get("as_of") not in (None, "", day):
                raise ValueError("forward item date mismatch")
            code = _code(item.get("code"), context="forward item")
            if code in labels:
                raise ValueError(f"duplicate forward label identity: {day} {code}")
            value = _finite(item.get("5d"))
            if value is not None and item.get("data_quality") in (None, "", "ok"):
                close_t = _finite(item.get("close_t"))
                close_5d = _finite(item.get("close_5d"))
                bars_count = item.get("bars_count")
                bars_source = str(item.get("bars_source") or "")
                if (
                    close_t is None
                    or close_t <= 0
                    or close_5d is None
                    or close_5d <= 0
                    or not isinstance(bars_count, int)
                    or bars_count < 6
                    or not bars_source
                    or bars_source in {"none", "empty", "no_client"}
                    or bars_source.startswith("error:")
                    or str(item.get("bars_end") or "") < maturity_day
                ):
                    raise ValueError("forward label price summary is incomplete")
                replayed = close_5d / close_t - 1.0
                if not math.isclose(replayed, value / 100.0, abs_tol=1e-6):
                    raise ValueError("forward label return cannot be replayed from prices")
                labels[code] = value / 100.0

        seen_codes: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ValueError("candidate row must be an object")
            code = _code(candidate.get("code"), context="candidate")
            if code in seen_codes:
                raise ValueError(f"duplicate candidate identity: {day} {code}")
            seen_codes.add(code)
            features, coverage = _extract_features(candidate)
            sector_name = str(candidate.get("sector_name") or "")
            if not sector_name:
                boards = candidate.get("boards")
                if isinstance(boards, list) and boards:
                    sector_name = str(boards[0])
            feature_row = {
                "as_of_date": day,
                "stock_code": code,
                "sector_name": sector_name,
                "features": features,
                "feature_coverage": round(coverage, 6),
            }
            feature_universe.append(feature_row)
            baseline = _rule_baseline(candidate)
            baselines.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "rule_baseline_score": baseline,
                    "rule_baseline_available": baseline is not None,
                }
            )
            if code in labels:
                records.append(
                    {
                        **feature_row,
                        "training_label": labels[code],
                        "training_label_end_date": maturity_day,
                    }
                )
        candidate_sources.append(
            {"as_of_date": day, "path": str(candidate_path.resolve()), "sha256": candidate_sha}
        )
        forward_sources.append(
            {"as_of_date": day, "path": str(forward_path.resolve()), "sha256": forward_sha}
        )

    if not feature_universe or not records:
        raise ValueError("historical research dataset has no usable labeled rows")
    feature_universe.sort(key=lambda row: (row["as_of_date"], row["stock_code"]))
    records.sort(key=lambda row: (row["as_of_date"], row["stock_code"]))
    baselines.sort(key=lambda row: (row["as_of_date"], row["stock_code"]))
    source_manifest = {
        "candidate_root": str(candidate_root),
        "forward_root": str(forward_root),
        "calendar": {"path": str(calendar_path), "sha256": calendar_sha},
        "candidate_sources": candidate_sources,
        "forward_sources": forward_sources,
    }
    core = {
        "schema_version": HISTORICAL_DATASET_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "feature_schema_version": "ml-stock-historical-research-features-v1",
        "feature_schema_sha256": historical_feature_schema_sha256(),
        "feature_names": list(HISTORICAL_FEATURE_NAMES),
        "label_definition": HISTORICAL_LABEL_DEFINITION,
        "label_price_lineage_status": HISTORICAL_LABEL_LINEAGE_STATUS,
        "max_label_horizon": 5,
        "strict_pit_eligible": False,
        "pit_evidence_status": "historical_reconstruction_not_prospective",
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "source_manifest": source_manifest,
        "counts": {
            "candidate_dates": len({row["as_of_date"] for row in feature_universe}),
            "labeled_dates": len({row["as_of_date"] for row in records}),
            "candidate_rows": len(feature_universe),
            "labeled_rows": len(records),
        },
        "feature_universe_records": feature_universe,
        "baseline_records": baselines,
        "records": records,
    }
    dataset = {**core, "dataset_sha256": canonical_sha256(core), "disclaimer": DISCLAIMER}
    if _validate:
        validate_historical_research_dataset(dataset)
    validate_no_executable_instructions(dataset, context="historical ML research dataset")
    return dataset


def validate_historical_research_dataset(dataset: Mapping[str, Any]) -> list[dict[str, Any]]:
    expected = {
        "schema_version": HISTORICAL_DATASET_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "feature_schema_version": "ml-stock-historical-research-features-v1",
        "feature_schema_sha256": historical_feature_schema_sha256(),
        "feature_names": list(HISTORICAL_FEATURE_NAMES),
        "label_definition": HISTORICAL_LABEL_DEFINITION,
        "label_price_lineage_status": HISTORICAL_LABEL_LINEAGE_STATUS,
        "max_label_horizon": 5,
        "strict_pit_eligible": False,
        "pit_evidence_status": "historical_reconstruction_not_prospective",
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }
    if any(dataset.get(key) != value for key, value in expected.items()):
        raise ValueError("historical research dataset contract mismatch")
    source_manifest = dataset.get("source_manifest")
    if not isinstance(source_manifest, Mapping):
        raise ValueError("historical research source manifest is missing")
    calendar = source_manifest.get("calendar")
    if not isinstance(calendar, Mapping):
        raise ValueError("historical research calendar identity is missing")
    _verify_source_entry(calendar, context="historical research calendar")
    for name in ("candidate_sources", "forward_sources"):
        entries = source_manifest.get(name)
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"historical research {name} are missing")
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError(f"historical research {name} entry is invalid")
            _verify_source_entry(entry, context=f"historical research {name}")
    rebuilt = build_historical_research_dataset(
        source_manifest.get("candidate_root"),
        source_manifest.get("forward_root"),
        (source_manifest.get("calendar") or {}).get("path"),
        _validate=False,
    )
    if rebuilt.get("dataset_sha256") != dataset.get("dataset_sha256"):
        raise ValueError("historical dataset does not match its source manifest")
    feature_rows = dataset.get("feature_universe_records")
    records = dataset.get("records")
    baselines = dataset.get("baseline_records")
    if not isinstance(feature_rows, list) or not isinstance(records, list) or not isinstance(baselines, list):
        raise ValueError("historical research dataset rows are missing")
    feature_by_id: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in feature_rows:
        day = _canonical_date(row.get("as_of_date"), context="historical feature date")
        code = _code(row.get("stock_code"), context="historical feature")
        identity = (day, code)
        if identity in feature_by_id:
            raise ValueError(f"duplicate historical feature identity: {identity}")
        features = row.get("features")
        if not isinstance(features, Mapping) or tuple(features) != HISTORICAL_FEATURE_NAMES:
            raise ValueError("historical feature order/schema mismatch")
        if _PROTECTED_SCORE_NAMES & set(features):
            raise ValueError("protected score leaked into historical model features")
        require_finite(features, context=f"historical features {day} {code}")
        feature_by_id[identity] = row
    validated: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in records:
        day = _canonical_date(row.get("as_of_date"), context="historical label date")
        code = _code(row.get("stock_code"), context="historical label")
        identity = (day, code)
        if identity in seen or identity not in feature_by_id:
            raise ValueError(f"historical labeled identity mismatch: {identity}")
        seen.add(identity)
        if row.get("features") != feature_by_id[identity].get("features"):
            raise ValueError("historical labeled feature view mismatch")
        label = _finite(row.get("training_label"))
        maturity = _canonical_date(
            row.get("training_label_end_date"), context="historical label maturity"
        )
        if label is None or maturity <= day:
            raise ValueError("historical training label contract mismatch")
        validated.append(dict(row))
    core = {key: dataset.get(key) for key in (
        "schema_version", "mode", "status", "dataset_classification",
        "feature_schema_version", "feature_schema_sha256", "feature_names",
        "label_definition", "label_price_lineage_status", "max_label_horizon", "strict_pit_eligible",
        "pit_evidence_status", "eligible_for_oos_claim", "promotion_allowed",
        "live_trading_allowed", "formal_predictor_compatible", "source_manifest",
        "counts", "feature_universe_records", "baseline_records", "records",
    )}
    if canonical_sha256(core) != dataset.get("dataset_sha256"):
        raise ValueError("historical research dataset SHA mismatch")
    return validated


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: Sequence[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _rank(values: Sequence[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=lambda index: (-values[index], index))
    output = [0.0] * len(values)
    for rank, index in enumerate(ordered, start=1):
        output[index] = float(rank)
    return output


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_var = sum((a - left_mean) ** 2 for a in left)
    right_var = sum((b - right_mean) ** 2 for b in right)
    denominator = math.sqrt(left_var * right_var)
    return numerator / denominator if denominator > 0 else 0.0


def bind_historical_walk_forward_report(
    dataset: Mapping[str, Any],
    prediction_report: Mapping[str, Any],
    *,
    feature_profile: str,
) -> dict[str, Any]:
    """Bind a raw deterministic walk-forward result to one historical dataset."""

    validate_historical_research_dataset(dataset)
    feature_names = HISTORICAL_FEATURE_PROFILES.get(feature_profile)
    if feature_names is None or tuple(prediction_report.get("feature_names") or ()) != feature_names:
        raise ValueError("historical walk-forward feature profile mismatch")
    if prediction_report.get("status") != "ok":
        raise ValueError("historical walk-forward result is unavailable")
    predictions = prediction_report.get("predictions")
    if not isinstance(predictions, list):
        raise ValueError("historical walk-forward predictions are missing")
    document = {
        **dict(prediction_report),
        "schema_version": "ml-stock-historical-research-walk-forward-v1",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "feature_profile": feature_profile,
        "dataset_sha256": dataset["dataset_sha256"],
        "prediction_rows_sha256": canonical_sha256(predictions),
        "strict_pit_eligible": False,
        "pit_evidence_status": "historical_reconstruction_not_prospective",
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(document, context="historical ML walk-forward")
    return document


def _replay_historical_walk_forward(
    dataset: Mapping[str, Any], prediction_report: Mapping[str, Any]
) -> None:
    """Re-run the declared deterministic experiment before accepting its metrics."""

    feature_names = tuple(prediction_report.get("feature_names") or ())
    model_parameters = prediction_report.get("model_parameters")
    if not isinstance(model_parameters, Mapping):
        raise ValueError("historical walk-forward model parameters are missing")
    records = validate_historical_research_dataset(dataset)
    model_records = [
        {**row, "features": {name: row["features"][name] for name in feature_names}}
        for row in records
    ]
    model_universe = [
        {**row, "features": {name: row["features"][name] for name in feature_names}}
        for row in dataset["feature_universe_records"]
    ]
    replay = walk_forward_ranker_predictions(
        model_records,
        prediction_universe_records=model_universe,
        feature_names=feature_names,
        min_train_dates=int(prediction_report.get("min_train_dates") or 0),
        test_dates=int(prediction_report.get("test_dates") or 0),
        purge_dates=int(prediction_report.get("purge_dates") or 0),
        max_train_dates=prediction_report.get("max_train_dates"),
        max_label_horizon=int(prediction_report.get("max_label_horizon") or 0),
        relevance_levels=int(model_parameters.get("relevance_levels") or 0),
        n_estimators=int(model_parameters.get("n_estimators") or 0),
        learning_rate=float(model_parameters.get("learning_rate") or 0.0),
        num_leaves=int(model_parameters.get("num_leaves") or 0),
        random_state=int(model_parameters.get("random_state") or 0),
    )
    if replay.get("status") != "ok" or any(
        replay.get(name) != prediction_report.get(name)
        for name in ("feature_names", "model_parameters", "folds", "predictions")
    ):
        raise ValueError("historical walk-forward deterministic replay mismatch")
    if canonical_sha256(replay["predictions"]) != prediction_report.get(
        "prediction_rows_sha256"
    ):
        raise ValueError("historical walk-forward prediction SHA mismatch")


def evaluate_historical_walk_forward(
    dataset: Mapping[str, Any],
    prediction_report: Mapping[str, Any],
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    """Compare historical ML ranking with the existing rule score as evaluation only."""

    records = validate_historical_research_dataset(dataset)
    if top_k <= 0:
        raise ValueError("historical evaluation top_k must be positive")
    if (
        prediction_report.get("schema_version")
        != "ml-stock-historical-research-walk-forward-v1"
        or prediction_report.get("status") != "ok"
        or prediction_report.get("mode") != MODE
        or prediction_report.get("dataset_classification")
        != HISTORICAL_DATASET_CLASSIFICATION
        or prediction_report.get("dataset_sha256") != dataset.get("dataset_sha256")
        or prediction_report.get("strict_pit_eligible") is not False
        or prediction_report.get("eligible_for_oos_claim") is not False
        or prediction_report.get("promotion_allowed") is not False
        or prediction_report.get("live_trading_allowed") is not False
        or prediction_report.get("formal_predictor_compatible") is not False
    ):
        raise ValueError("historical walk-forward prediction contract mismatch")
    prediction_features = tuple(prediction_report["feature_names"])
    feature_profile = str(prediction_report.get("feature_profile") or "")
    if HISTORICAL_FEATURE_PROFILES.get(feature_profile) != prediction_features:
        raise ValueError("historical walk-forward feature profile is not registered")
    _replay_historical_walk_forward(dataset, prediction_report)
    labels = {
        (row["as_of_date"], row["stock_code"]): float(row["training_label"])
        for row in records
    }
    baselines = {
        (str(row.get("as_of_date") or ""), str(row.get("stock_code") or "").zfill(6)):
        row.get("rule_baseline_score")
        for row in dataset["baseline_records"]
        if isinstance(row, Mapping)
    }
    by_date: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()
    for row in prediction_report.get("predictions") or []:
        if not isinstance(row, Mapping):
            raise ValueError("historical prediction row is invalid")
        day = _canonical_date(row.get("as_of_date"), context="historical prediction date")
        code = _code(row.get("stock_code"), context="historical prediction")
        identity = (day, code)
        if identity in seen:
            raise ValueError(f"duplicate historical prediction identity: {identity}")
        seen.add(identity)
        label = labels.get(identity)
        ml_score = _finite(row.get("ml_quant_score_shadow"))
        rule_score = _finite(baselines.get(identity))
        if label is None or ml_score is None:
            continue
        by_date.setdefault(day, []).append(
            {
                "stock_code": code,
                "label": label,
                "ml_score": ml_score,
                "rule_score": rule_score,
                "fold": int(row.get("fold") or 0),
            }
        )
    daily: list[dict[str, Any]] = []
    for day, rows in sorted(by_date.items()):
        if len(rows) < 2:
            continue
        count = min(top_k, len(rows))
        ml_top = sorted(rows, key=lambda row: (-row["ml_score"], row["stock_code"]))[:count]
        rule_rows = [row for row in rows if row["rule_score"] is not None]
        rule_count = min(top_k, len(rule_rows))
        rule_top = sorted(
            rule_rows, key=lambda row: (-row["rule_score"], row["stock_code"])
        )[:rule_count]
        universe_mean = float(_mean([row["label"] for row in rows]))
        ml_mean = float(_mean([row["label"] for row in ml_top]))
        rule_mean = _mean([row["label"] for row in rule_top])
        rank_ic = _pearson(
            _rank([row["ml_score"] for row in rows]),
            _rank([row["label"] for row in rows]),
        )
        daily.append(
            {
                "as_of_date": day,
                "fold": rows[0]["fold"],
                "row_count": len(rows),
                "top_k": count,
                "universe_mean_return": universe_mean,
                "ml_top_k_mean_return": ml_mean,
                "rule_comparison_row_count": len(rule_rows),
                "rule_top_k_mean_return": rule_mean,
                "ml_lift_vs_universe": ml_mean - universe_mean,
                "rule_lift_vs_universe": (
                    rule_mean - float(_mean([row["label"] for row in rule_rows]))
                    if rule_mean is not None
                    else None
                ),
                "ml_win_vs_universe": ml_mean > universe_mean,
                "ml_win_vs_rule": ml_mean > rule_mean if rule_mean is not None else None,
                "spearman_rank_ic": rank_ic,
            }
        )
    def top_k_metrics(k: int) -> dict[str, float | None]:
        ml_values: list[float] = []
        rule_values: list[float] = []
        universe_values: list[float] = []
        rule_universe_values: list[float] = []
        for day, rows in sorted(by_date.items()):
            if len(rows) < 2:
                continue
            count = min(k, len(rows))
            ml_values.append(
                float(_mean([row["label"] for row in sorted(
                    rows, key=lambda row: (-row["ml_score"], row["stock_code"])
                )[:count]]))
            )
            rule_rows = [row for row in rows if row["rule_score"] is not None]
            rule_count = min(k, len(rule_rows))
            if rule_count:
                rule_values.append(
                    float(_mean([row["label"] for row in sorted(
                        rule_rows, key=lambda row: (-row["rule_score"], row["stock_code"])
                    )[:rule_count]]))
                )
                rule_universe_values.append(
                    float(_mean([row["label"] for row in rule_rows]))
                )
            universe_values.append(float(_mean([row["label"] for row in rows])))
        return {
            "evaluated_date_count": len(ml_values),
            "ml_top_k_mean_return": _mean(ml_values),
            "rule_top_k_mean_return": _mean(rule_values),
            "universe_mean_return": _mean(universe_values),
            "ml_lift_vs_universe": _mean(
                [ml - universe for ml, universe in zip(ml_values, universe_values)]
            ),
            "rule_lift_vs_universe": _mean([
                rule - universe
                for rule, universe in zip(rule_values, rule_universe_values)
            ]),
        }
    fold_metrics: list[dict[str, Any]] = []
    for fold in sorted({row["fold"] for row in daily}):
        fold_rows = [row for row in daily if row["fold"] == fold]
        fold_metrics.append(
            {
                "fold": fold,
                "date_count": len(fold_rows),
                "ml_lift_vs_universe": _mean(
                    [row["ml_lift_vs_universe"] for row in fold_rows]
                ),
                "rule_lift_vs_universe": _mean(
                    [
                        row["rule_lift_vs_universe"]
                        for row in fold_rows
                        if row["rule_lift_vs_universe"] is not None
                    ]
                ),
                "mean_spearman_rank_ic": _mean(
                    [row["spearman_rank_ic"] for row in fold_rows]
                ),
            }
        )
    ml_lifts = [row["ml_lift_vs_universe"] for row in daily]
    rule_lifts = [
        row["rule_lift_vs_universe"]
        for row in daily
        if row["rule_lift_vs_universe"] is not None
    ]
    metrics = {
        "evaluated_date_count": len(daily),
        "evaluated_row_count": sum(row["row_count"] for row in daily),
        "top_k": top_k,
        "universe_mean_return": _mean([row["universe_mean_return"] for row in daily]),
        "ml_top_k_mean_return": _mean([row["ml_top_k_mean_return"] for row in daily]),
        "rule_top_k_mean_return": _mean([
            row["rule_top_k_mean_return"]
            for row in daily
            if row["rule_top_k_mean_return"] is not None
        ]),
        "ml_lift_vs_universe": _mean([row["ml_lift_vs_universe"] for row in daily]),
        "rule_lift_vs_universe": _mean([
            row["rule_lift_vs_universe"]
            for row in daily
            if row["rule_lift_vs_universe"] is not None
        ]),
        "ml_lift_median_vs_universe": _median(ml_lifts),
        "rule_lift_median_vs_universe": _median(rule_lifts),
        "ml_win_rate_vs_universe": _mean(
            [float(row["ml_win_vs_universe"]) for row in daily]
        ),
        "ml_win_rate_vs_rule": _mean([
            float(row["ml_win_vs_rule"])
            for row in daily
            if row["ml_win_vs_rule"] is not None
        ]),
        "mean_spearman_rank_ic": _mean(
            [row["spearman_rank_ic"] for row in daily]
        ),
        "ml_positive_date_rate": _mean(
            [float(row["ml_top_k_mean_return"] > 0) for row in daily]
        ),
        "rule_positive_date_rate": _mean(
            [
                float(row["rule_top_k_mean_return"] > 0)
                for row in daily
                if row["rule_top_k_mean_return"] is not None
            ]
        ),
    }
    require_finite(metrics, context="historical walk-forward metrics")
    report = {
        "schema_version": "ml-stock-historical-research-evaluation-v1",
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "feature_profile": str(prediction_report.get("feature_profile") or "custom"),
        "dataset_sha256": dataset["dataset_sha256"],
        "feature_schema_sha256": historical_feature_schema_sha256(prediction_features),
        "label_definition": HISTORICAL_LABEL_DEFINITION,
        "label_price_lineage_status": HISTORICAL_LABEL_LINEAGE_STATUS,
        "metrics": metrics,
        "daily_metrics": daily,
        "top_k_sensitivity": {
            str(k): top_k_metrics(k) for k in (1, 3, 5)
        },
        "fold_metrics": fold_metrics,
        "strict_pit_eligible": False,
        "pit_evidence_status": "historical_reconstruction_not_prospective",
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="historical ML research evaluation")
    return report


def save_historical_research_bundle(
    model: RankerModel,
    output_dir: Path | str,
    *,
    model_version: str,
    dataset_sha256: str,
) -> dict[str, Any]:
    """Persist a model that the formal registry intentionally cannot load."""

    if not model_version or not _SHA256.fullmatch(str(dataset_sha256 or "")):
        raise ValueError("historical model identity is invalid")
    if not model.feature_names or not set(model.feature_names).issubset(
        set(HISTORICAL_FEATURE_NAMES)
    ):
        raise ValueError("historical model feature schema mismatch")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    model_path = destination / "model.txt"
    registry_path = destination / "registry.json"
    if model_path.exists() or registry_path.exists():
        raise FileExistsError(f"historical model bundle already exists: {destination}")
    temporary = destination / ".model.txt.tmp"
    try:
        model.booster.save_model(str(temporary))
        os.replace(temporary, model_path)
    finally:
        temporary.unlink(missing_ok=True)
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    registry = {
        "schema_version": HISTORICAL_MODEL_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "model_version": model_version,
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset_sha256,
        "feature_schema_version": "ml-stock-historical-research-features-v1",
        "feature_schema_sha256": historical_feature_schema_sha256(model.feature_names),
        "feature_names": list(model.feature_names),
        "label_definition": HISTORICAL_LABEL_DEFINITION,
        "label_price_lineage_status": HISTORICAL_LABEL_LINEAGE_STATUS,
        "training_period": dict(model.metadata["training_period"]),
        "label_maturity_period": dict(model.metadata["label_maturity_period"]),
        "training_records_sha256": model.metadata["training_records_sha256"],
        "parameters": dict(model.metadata["parameters"]),
        "strict_pit_eligible": False,
        "pit_evidence_status": "historical_reconstruction_not_prospective",
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "model_artifact": {"path": "model.txt", "sha256": model_sha},
        "registered_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(registry, context="historical ML research registry")
    write_strict_json_atomic(registry_path, registry)
    return {
        "registry": registry,
        "registry_path": str(registry_path),
        "registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
        "model_path": str(model_path),
        "model_sha256": model_sha,
    }
