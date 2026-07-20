"""LightGBM LambdaRank backend for the independent ML shadow path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from collections import defaultdict
import math
from typing import Any, Mapping, Sequence

from .contract import (
    canonical_sha256,
    import_optional_ml_module,
    optional_ml_dependency_readiness,
)
from .schema import DISCLAIMER, MODE, V1_FEATURE_NAMES
from .split import expanding_walk_forward_splits


@dataclass(frozen=True)
class RankerModel:
    """Small public wrapper around a trained or loaded LightGBM Booster."""

    booster: Any
    feature_names: tuple[str, ...]
    metadata: Mapping[str, Any]

    def predict(self, records: Sequence[Mapping[str, Any]]):
        raise RuntimeError(
            "RankerModel.predict is disabled; use the verified predict_shadow API"
        )


def _require_numpy():
    readiness = optional_ml_dependency_readiness(("numpy",))
    if readiness["status"] != "ready":
        raise RuntimeError("optional ML dependency unavailable: numpy")
    import numpy as np

    return np


def _discrete_relevance(values: Sequence[float], *, levels: int) -> list[int]:
    if levels < 2:
        raise ValueError("relevance_levels must be at least 2")
    unique = sorted(set(values))
    if len(unique) == 1:
        return [0 for _value in values]
    grade_by_value = {
        value: int(round(index / (len(unique) - 1) * (levels - 1)))
        for index, value in enumerate(unique)
    }
    return [grade_by_value[value] for value in values]


def prepare_ranking_matrix(
    records: Sequence[Mapping[str, Any]],
    *,
    feature_names: tuple[str, ...] = V1_FEATURE_NAMES,
    relevance_levels: int = 5,
) -> dict[str, Any]:
    """Sort complete date groups and derive non-negative LambdaRank labels."""

    np = _require_numpy()
    ordered = sorted(
        records,
        key=lambda row: (str(row.get("as_of_date") or ""), str(row.get("stock_code") or "")),
    )
    if not ordered:
        raise ValueError("ranking records must not be empty")

    dates: list[str] = []
    codes: list[str] = []
    features: list[list[float]] = []
    continuous: list[float] = []
    by_date: dict[str, list[int]] = {}
    for index, row in enumerate(ordered):
        day = str(row.get("as_of_date") or "")
        code = str(row.get("stock_code") or "").zfill(6)
        raw_features = row.get("features")
        if not day or len(code) != 6 or not isinstance(raw_features, Mapping):
            raise ValueError("ranking record identity/features are invalid")
        if tuple(raw_features) != feature_names:
            raise ValueError("ranking feature order/schema mismatch")
        feature_values = [float(raw_features[name]) for name in feature_names]
        label = float(row.get("training_label"))
        if not all(math.isfinite(value) for value in feature_values) or not math.isfinite(label):
            raise ValueError("ranking matrix contains non-finite values")
        dates.append(day)
        codes.append(code)
        features.append(feature_values)
        continuous.append(label)
        by_date.setdefault(day, []).append(index)

    relevance: list[int] = [0] * len(ordered)
    groups: list[int] = []
    for day in sorted(by_date):
        indices = by_date[day]
        groups.append(len(indices))
        grades = _discrete_relevance(
            [continuous[index] for index in indices], levels=relevance_levels
        )
        for index, grade in zip(indices, grades):
            relevance[index] = grade
    if sum(groups) != len(ordered):
        raise ValueError("ranking groups do not cover all rows")
    return {
        "features": np.asarray(features, dtype=float),
        "relevance_labels": np.asarray(relevance, dtype=int),
        "continuous_labels": np.asarray(continuous, dtype=float),
        "groups": groups,
        "dates": dates,
        "stock_codes": codes,
        "records": ordered,
    }


def prepare_prediction_matrix(
    records: Sequence[Mapping[str, Any]],
    *,
    feature_names: tuple[str, ...] = V1_FEATURE_NAMES,
) -> dict[str, Any]:
    """Prepare ordered prediction rows without importing or accepting labels."""

    np = _require_numpy()
    ordered = sorted(
        records,
        key=lambda row: (str(row.get("as_of_date") or ""), str(row.get("stock_code") or "")),
    )
    if not ordered:
        raise ValueError("prediction records must not be empty")
    values: list[list[float]] = []
    for row in ordered:
        raw = row.get("features")
        if not isinstance(raw, Mapping) or tuple(raw) != feature_names:
            raise ValueError("prediction feature order/schema mismatch")
        feature_values = [float(raw[name]) for name in feature_names]
        if not all(math.isfinite(value) for value in feature_values):
            raise ValueError("prediction matrix contains non-finite values")
        values.append(feature_values)
    return {
        "features": np.asarray(values, dtype=float),
        "records": ordered,
        "dates": [str(row.get("as_of_date")) for row in ordered],
        "stock_codes": [str(row.get("stock_code")).zfill(6) for row in ordered],
    }


def train_lambdarank(
    records: Sequence[Mapping[str, Any]],
    *,
    feature_names: tuple[str, ...] = V1_FEATURE_NAMES,
    relevance_levels: int = 5,
    n_estimators: int = 80,
    learning_rate: float = 0.05,
    num_leaves: int = 15,
    random_state: int = 20260718,
) -> RankerModel:
    """Train the optional LightGBM LambdaRank backend, or fail closed."""

    readiness = optional_ml_dependency_readiness()
    if readiness["status"] != "ready":
        missing = ", ".join(readiness["missing_packages"])
        raise RuntimeError(
            f"optional ML dependencies unavailable: {missing}; "
            f"errors={readiness['import_errors']}"
        )
    lgb = import_optional_ml_module("lightgbm")

    matrix = prepare_ranking_matrix(
        records,
        feature_names=feature_names,
        relevance_levels=relevance_levels,
    )
    if len(matrix["groups"]) < 2 or min(matrix["groups"]) < 2:
        raise ValueError("LambdaRank requires at least two date groups with two rows each")
    parameter_contract = {
        "backend": "lightgbm_lambdarank",
        "objective": "lambdarank",
        "metric": ["ndcg"],
        "relevance_levels": int(relevance_levels),
        "label_gain": [(2**index) - 1 for index in range(relevance_levels)],
        "n_estimators": int(n_estimators),
        "learning_rate": float(learning_rate),
        "num_leaves": int(num_leaves),
        "random_state": int(random_state),
        "min_child_samples": 2,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "reg_lambda": 1.0,
        "deterministic": True,
        "force_col_wise": True,
        "n_jobs": 1,
        "verbosity": -1,
    }
    estimator = lgb.LGBMRanker(
        objective=parameter_contract["objective"],
        metric=parameter_contract["metric"],
        n_estimators=int(n_estimators),
        learning_rate=float(learning_rate),
        num_leaves=int(num_leaves),
        min_child_samples=parameter_contract["min_child_samples"],
        subsample=parameter_contract["subsample"],
        colsample_bytree=parameter_contract["colsample_bytree"],
        reg_lambda=parameter_contract["reg_lambda"],
        random_state=int(random_state),
        deterministic=parameter_contract["deterministic"],
        force_col_wise=parameter_contract["force_col_wise"],
        n_jobs=parameter_contract["n_jobs"],
        verbosity=parameter_contract["verbosity"],
        label_gain=parameter_contract["label_gain"],
    )
    estimator.fit(
        matrix["features"],
        matrix["relevance_labels"],
        group=matrix["groups"],
        feature_name=list(feature_names),
    )
    dates = sorted(set(matrix["dates"]))
    maturity_dates: list[str] = []
    for row in matrix["records"]:
        maturity_text = str(row.get("training_label_end_date") or "")
        try:
            maturity = date.fromisoformat(maturity_text)
            signal = date.fromisoformat(str(row.get("as_of_date") or ""))
        except ValueError as exc:
            raise ValueError("training row label maturity date is invalid") from exc
        if maturity <= signal:
            raise ValueError("training row label maturity must follow as_of_date")
        maturity_dates.append(maturity.isoformat())
    metadata = {
        "backend": "lightgbm_lambdarank",
        "objective": "lambdarank",
        "relevance_levels": relevance_levels,
        "continuous_label_retained_for_evaluation": True,
        "training_period": {
            "start": dates[0],
            "end": dates[-1],
            "date_count": len(dates),
            "row_count": len(records),
        },
        "label_maturity_period": {
            "start": min(maturity_dates),
            "end": max(maturity_dates),
        },
        "training_records_sha256": canonical_sha256(matrix["records"]),
        "libraries": readiness["versions"],
        "parameters": {
            **parameter_contract,
            "date_grouped": True,
            "relevance_encoding": "within_date_nonnegative_discrete_0_to_4",
        },
    }
    return RankerModel(
        booster=estimator.booster_,
        feature_names=feature_names,
        metadata=metadata,
    )


def walk_forward_ranker_predictions(
    records: Sequence[Mapping[str, Any]],
    *,
    prediction_universe_records: Sequence[Mapping[str, Any]] | None = None,
    feature_names: tuple[str, ...] = V1_FEATURE_NAMES,
    min_train_dates: int,
    test_dates: int,
    purge_dates: int,
    max_train_dates: int | None = None,
    max_label_horizon: int = 5,
    n_estimators: int = 80,
    relevance_levels: int = 5,
    learning_rate: float = 0.05,
    num_leaves: int = 15,
    random_state: int = 20260718,
) -> dict[str, Any]:
    """Train expanding folds and return only purged future-fold predictions."""

    if max_train_dates is not None and max_train_dates < min_train_dates:
        raise ValueError("max_train_dates must be at least min_train_dates")

    universe_records = list(prediction_universe_records or records)
    folds = expanding_walk_forward_splits(
        universe_records,
        min_train_dates=min_train_dates,
        test_dates=test_dates,
        purge_dates=purge_dates,
        max_label_horizon=max_label_horizon,
    )
    if not folds:
        return {
            "schema_version": "ml-stock-walk-forward-v1",
            "mode": MODE,
            "status": "insufficient_data",
            "reason": "no_complete_walk_forward_fold",
            "folds": [],
            "predictions": [],
            "promotion_allowed": False,
            "live_trading_allowed": False,
            "generated_at": datetime.now().astimezone().isoformat(),
            "disclaimer": DISCLAIMER,
        }
    predictions: list[dict[str, Any]] = []
    fold_audit: list[dict[str, Any]] = []
    labels_by_identity: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in records:
        identity = (
            str(row.get("as_of_date") or ""),
            str(row.get("stock_code") or "").zfill(6),
        )
        if identity in labels_by_identity:
            raise ValueError(f"duplicate labeled ranking identity: {identity}")
        labels_by_identity[identity] = row
    for fold in folds:
        test_start = date.fromisoformat(fold["test_dates"][0])
        available_train_dates = sorted(set(fold["train_dates"]))
        selected_train_dates = (
            available_train_dates[-max_train_dates:]
            if max_train_dates is not None
            else available_train_dates
        )
        train_dates = set(selected_train_dates)
        train_rows = []
        for row in records:
            if str(row.get("as_of_date") or "") not in train_dates:
                continue
            try:
                maturity = date.fromisoformat(
                    str(row.get("training_label_end_date") or "")
                )
            except ValueError as exc:
                raise ValueError("walk-forward training maturity date is invalid") from exc
            if maturity < test_start:
                train_rows.append(row)
        test_rows = [universe_records[index] for index in fold["test_indices"]]
        if not train_rows:
            raise ValueError("walk-forward fold has no matured training labels")
        mature_train_dates = sorted(
            {str(row.get("as_of_date") or "") for row in train_rows}
        )
        if len(mature_train_dates) < min_train_dates:
            return {
                "schema_version": "ml-stock-walk-forward-v1",
                "mode": MODE,
                "status": "insufficient_data",
                "reason": "fewer_than_minimum_mature_training_dates",
                "required_mature_training_dates": min_train_dates,
                "available_mature_training_dates": len(mature_train_dates),
                "folds": fold_audit,
                "predictions": [],
                "promotion_allowed": False,
                "live_trading_allowed": False,
                "generated_at": datetime.now().astimezone().isoformat(),
                "disclaimer": DISCLAIMER,
            }
        model = train_lambdarank(
            train_rows,
            feature_names=feature_names,
            relevance_levels=relevance_levels,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
            random_state=random_state,
        )
        matrix = prepare_prediction_matrix(test_rows, feature_names=model.feature_names)
        raw = [float(value) for value in model.booster.predict(matrix["features"])]
        by_date: dict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(matrix["records"]):
            by_date[str(row["as_of_date"])].append(index)
        percentile_by_index: dict[int, tuple[int, float]] = {}
        for day in sorted(by_date):
            ranked = sorted(
                by_date[day],
                key=lambda index: (-raw[index], str(matrix["records"][index]["stock_code"])),
            )
            count = len(ranked)
            for rank, index in enumerate(ranked, start=1):
                percentile = 100.0 if count == 1 else (count - rank) / (count - 1) * 100.0
                percentile_by_index[index] = (rank, round(percentile, 6))
        for index, row in enumerate(matrix["records"]):
            rank, percentile = percentile_by_index[index]
            identity = (
                str(row["as_of_date"]),
                str(row["stock_code"]).zfill(6),
            )
            label_row = labels_by_identity.get(identity)
            prediction = {
                "fold": fold["fold"],
                "as_of_date": identity[0],
                "stock_code": identity[1],
                "sector_name": str(row.get("sector_name") or ""),
                "prediction": raw[index],
                "ml_quant_score_shadow": percentile,
                "rank": rank,
                "label_available": label_row is not None,
            }
            if label_row is not None:
                prediction["continuous_label"] = float(label_row["training_label"])
                prediction["labels"] = dict(label_row.get("labels") or {})
            predictions.append(prediction)
        fold_audit.append(
            {
                "fold": fold["fold"],
                "train_start": mature_train_dates[0],
                "train_end": mature_train_dates[-1],
                "train_date_count": len(mature_train_dates),
                "train_labeled_date_count": len(mature_train_dates),
                "train_universe_start": selected_train_dates[0],
                "train_universe_end": selected_train_dates[-1],
                "train_universe_date_count": len(selected_train_dates),
                "purged_dates": list(fold["purged_dates"]),
                "test_start": fold["test_dates"][0],
                "test_end": fold["test_dates"][-1],
                "test_date_count": len(fold["test_dates"]),
                "train_row_count": len(train_rows),
                "test_row_count": len(test_rows),
                "latest_training_label_maturity": max(
                    str(row["training_label_end_date"]) for row in train_rows
                ),
            }
        )
    return {
        "schema_version": "ml-stock-walk-forward-v1",
        "mode": MODE,
        "status": "ok",
        "split_type": "expanding_date_grouped_walk_forward",
        "min_train_dates": min_train_dates,
        "test_dates": test_dates,
        "purge_dates": purge_dates,
        "max_train_dates": max_train_dates,
        "max_label_horizon": max_label_horizon,
        "model_parameters": {
            "backend": "lightgbm_lambdarank",
            "objective": "lambdarank",
            "metric": ["ndcg"],
            "relevance_levels": relevance_levels,
            "label_gain": [(2**index) - 1 for index in range(relevance_levels)],
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "num_leaves": num_leaves,
            "random_state": random_state,
            "min_child_samples": 2,
            "subsample": 1.0,
            "colsample_bytree": 1.0,
            "reg_lambda": 1.0,
            "deterministic": True,
            "force_col_wise": True,
            "n_jobs": 1,
            "verbosity": -1,
        },
        "feature_names": list(feature_names),
        "continuous_label_retained_for_evaluation": True,
        "folds": fold_audit,
        "predictions": predictions,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
