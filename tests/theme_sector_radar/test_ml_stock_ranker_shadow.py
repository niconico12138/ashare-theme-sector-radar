from __future__ import annotations

import ast
import copy
from datetime import date, timedelta
from pathlib import Path
import subprocess
import sys

import pytest


def _bars(count: int = 25) -> list[dict[str, object]]:
    start = date(2026, 1, 1)
    rows = []
    for index in range(count):
        rows.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "open": 10.0 + index * 0.1,
                "high": 10.2 + index * 0.1,
                "low": 9.8 + index * 0.1,
                "close": 10.0 + index * 0.1,
                "volume": 1_000_000 + index * 10_000,
                "amount": 10_000_000 + index * 100_000,
            }
        )
    return rows


def _feature_and_label() -> tuple[dict, dict]:
    from theme_sector_radar.ml.feature_builder import build_feature_row
    from theme_sector_radar.ml.schema import LABEL_DEFINITION

    feature = build_feature_row(
        {"code": "000001", "sector_name": "bank"},
        _bars(),
        as_of_date=str(_bars()[-1]["date"]),
    )
    label = {
        "as_of_date": feature["as_of_date"],
        "stock_code": "000001",
        "sector_name": "bank",
        "training_label": 0.03,
        "labels": {"future_excess_return_5d": 0.03},
        "label_dates": {"future_excess_return_5d": "2026-01-30"},
        "training_label_end_date": "2026-01-30",
        "label_definition": LABEL_DEFINITION,
        "max_label_horizon": 5,
    }
    return feature, label


def test_feature_builder_uses_only_as_of_data_and_excludes_rule_scores():
    from theme_sector_radar.ml.feature_builder import build_feature_row
    from theme_sector_radar.ml.schema import V1_FEATURE_NAMES

    bars = _bars()
    as_of = str(bars[-2]["date"])
    bars[-1]["close"] = 9999.0
    candidate = {
        "code": "000001",
        "sector_name": "银行",
        "pe": 6.5,
        "pb": 0.7,
        "total_mv": 2500.0,
        "quant_score": 88.0,
        "final_score": 91.0,
        "relevance_score": 0.12,
        "legacy_relevance_score": 0.12,
        "sector_trend_score": 63.0,
        "sector_burst_score": 51.0,
    }
    candidate_before = copy.deepcopy(candidate)
    bars_before = copy.deepcopy(bars)

    row = build_feature_row(candidate, bars, as_of_date=as_of)

    assert row["as_of_date"] == as_of
    assert row["stock_code"] == "000001"
    assert tuple(row["features"]) == V1_FEATURE_NAMES
    assert "quant_score" not in row["features"]
    assert "final_score" not in row["features"]
    assert "relevance_score" not in row["features"]
    assert "legacy_relevance_score" not in row["features"]
    assert row["features"]["momentum_1d"] == pytest.approx(12.3 / 12.2 - 1.0)
    assert row["provenance"]["latest_bar_date"] == as_of
    assert candidate == candidate_before
    assert bars == bars_before


def test_ml_shadow_sources_have_no_protected_score_assignments():
    project_root = Path(__file__).resolve().parents[2]
    protected = {
        "quant_score",
        "final_score",
        "v2_score",
        "selection_score",
        "selection_score_adjusted",
    }
    paths = sorted((project_root / "theme_sector_radar" / "ml").glob("*.py"))
    paths += sorted((project_root / "scripts").glob("*ml*.py"))
    writes = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (
                    list(node.targets)
                    if isinstance(node, ast.Assign)
                    else [node.target]
                )
            for target in targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value in protected
                ):
                    writes.append((path.name, target.slice.value, node.lineno))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"update", "setdefault", "__setitem__"}:
                    for argument in [*node.args, *node.keywords]:
                        value = argument.value if isinstance(argument, ast.keyword) else argument
                        for child in ast.walk(value):
                            if isinstance(child, ast.Constant) and child.value in protected:
                                writes.append((path.name, child.value, node.lineno))
    assert writes == []


def test_feature_coverage_counts_valid_zero_values_as_observed():
    from theme_sector_radar.ml.feature_builder import build_feature_row

    bars = _bars()
    for bar in bars:
        bar["open"] = bar["high"] = bar["low"] = bar["close"] = 10.0
    candidate = {
        "code": "000001",
        "sector_name": "银行",
        "pe": 0.0,
        "pb": 0.0,
        "total_mv": 0.0,
        "pe_sector_relative": 0.0,
        "pb_sector_relative": 0.0,
        "market_cap_sector_percentile": 0.0,
        "sector_trend_score": 0.0,
        "sector_burst_score": 0.0,
        "sector_direction_score": 0.0,
        "data_quality_score": 0.0,
        "factor_coverage": 0.0,
        "linkage_v2": {
            "comovement_20d": 0.0,
            "relative_strength_5d": 0.0,
            "relative_strength_10d": 0.0,
            "weight": 0.0,
            "fund_flow": 0.0,
            "data_quality": 0.0,
        },
    }

    row = build_feature_row(candidate, bars, as_of_date=str(bars[-1]["date"]))

    assert row["features"]["momentum_20d"] == 0.0
    assert row["features"]["volatility_20d"] == 0.0
    assert row["feature_coverage"] == 1.0


def test_feature_builder_rejects_future_or_label_fields():
    from theme_sector_radar.ml.feature_builder import build_feature_row

    candidate = {
        "code": "000001",
        "sector_name": "银行",
        "future_5d_return": 0.25,
    }

    with pytest.raises(ValueError, match="forbidden future/label field"):
        build_feature_row(candidate, _bars(), as_of_date=str(_bars()[-1]["date"]))

    for field in (
        "training_label",
        "training_label_end_date",
        "label_date",
        "label_value",
        "target_return",
    ):
        with pytest.raises(ValueError, match="forbidden future/label field"):
            build_feature_row(
                {"code": "000001", "sector_name": "bank", field: "future"},
                _bars(),
                as_of_date=str(_bars()[-1]["date"]),
            )


def test_feature_builder_rejects_stale_bar_on_as_of_date():
    from theme_sector_radar.ml.feature_builder import build_feature_row

    with pytest.raises(ValueError, match="latest bar must equal as_of_date"):
        build_feature_row(
            {"code": "000001", "sector_name": "bank"},
            _bars(10),
            as_of_date="2026-01-15",
        )


def test_feature_builder_maps_production_linkage_v2_components():
    from theme_sector_radar.ml.feature_builder import build_feature_row

    candidate = {
        "code": "000001",
        "sector_name": "bank",
        "linkage_v2_shadow": {
            "status": "partial",
            "score": 0.56,
            "components": {
                "return_comovement_20d": {"status": "ok", "score": 0.75},
                "relative_strength_5d_10d": {"status": "ok", "score": 0.65},
                "constituent_weight": {"status": "ok", "score": 0.55},
                "fund_flow_alignment": {"status": "unavailable", "score": None},
                "data_quality": {"status": "ok", "score": 0.95},
            },
            "feature_inputs": {
                "relative_strength_5d": 0.6,
                "relative_strength_10d": 0.7,
            },
        },
    }

    row = build_feature_row(candidate, _bars(), as_of_date=str(_bars()[-1]["date"]))

    assert row["features"]["linkage_comovement_20d"] == 0.75
    assert row["features"]["linkage_relative_strength_5d"] == 0.6
    assert row["features"]["linkage_relative_strength_10d"] == 0.7
    assert row["features"]["linkage_weight"] == 0.55
    assert row["features"]["linkage_fund_flow"] == 0.0
    assert row["features"]["linkage_data_quality"] == 0.95
    assert row["features"]["missing_linkage"] == 0.0


def test_label_builder_creates_sector_relative_1d_3d_5d_labels():
    from theme_sector_radar.ml.label_builder import build_forward_label_rows

    dates = [(date(2026, 2, 1) + timedelta(days=index)).isoformat() for index in range(7)]
    stock_prices = [
        {"date": day, "stock_code": "000001", "sector_name": "银行", "close": 100 + 2 * index}
        for index, day in enumerate(dates)
    ]
    sector_prices = [
        {"date": day, "sector_name": "银行", "close": 100 + index}
        for index, day in enumerate(dates)
    ]

    rows = build_forward_label_rows(
        stock_prices, sector_prices, trading_dates=dates
    )

    first = rows[0]
    assert first["as_of_date"] == dates[0]
    assert first["labels"]["future_return_1d"] == pytest.approx(0.02)
    assert first["labels"]["future_excess_return_3d"] == pytest.approx(1.06 - 1.03)
    assert first["labels"]["future_excess_return_5d"] == pytest.approx(1.10 - 1.05)
    assert first["training_label"] == pytest.approx(0.05)
    assert first["label_dates"]["future_excess_return_5d"] == dates[5]
    assert first["training_label_end_date"] == dates[5]


def test_label_builder_preserves_as_of_identity_when_future_stock_label_is_missing():
    from theme_sector_radar.ml.label_builder import build_forward_label_rows

    dates = [(date(2026, 2, 1) + timedelta(days=index)).isoformat() for index in range(7)]
    stock_prices = [
        {"date": day, "stock_code": "000001", "sector_name": "bank", "close": 100 + index}
        for index, day in enumerate(dates)
        if index != 5
    ]
    sector_prices = [
        {"date": day, "sector_name": "bank", "close": 100 + index}
        for index, day in enumerate(dates)
    ]

    rows = build_forward_label_rows(
        stock_prices, sector_prices, trading_dates=dates
    )
    first = next(row for row in rows if row["as_of_date"] == dates[0])

    assert first["labels"]["future_excess_return_5d"] is None
    assert first["label_dates"]["future_excess_return_5d"] == dates[5]
    assert first["training_label"] is None
    assert first["training_label_end_date"] is None


def test_label_builder_does_not_treat_missing_stock_bar_as_next_trading_day():
    from theme_sector_radar.ml.label_builder import build_forward_label_rows

    dates = [(date(2026, 2, 1) + timedelta(days=index)).isoformat() for index in range(7)]
    stock_prices = [
        {"date": day, "stock_code": "000001", "sector_name": "银行", "close": 100 + index}
        for index, day in enumerate(dates)
        if index != 1
    ]
    sector_prices = [
        {"date": day, "sector_name": "银行", "close": 100 + index}
        for index, day in enumerate(dates)
    ]

    rows = build_forward_label_rows(
        stock_prices, sector_prices, trading_dates=dates
    )

    first = next(row for row in rows if row["as_of_date"] == dates[0])
    assert first["labels"]["future_return_1d"] is None
    assert first["labels"]["future_excess_return_1d"] is None
    assert first["label_dates"]["future_excess_return_1d"] == dates[1]


def test_label_builder_uses_explicit_exchange_calendar_when_sector_bar_is_missing():
    from theme_sector_radar.ml.label_builder import build_forward_label_rows

    trading_dates = ["2026-07-16", "2026-07-17", "2026-07-20"]
    stock_prices = [
        {"date": day, "stock_code": "000001", "sector_name": "bank", "close": close}
        for day, close in zip(trading_dates, (10.0, 11.0, 12.0))
    ]
    sector_prices = [
        {"date": "2026-07-16", "sector_name": "bank", "close": 100.0},
        {"date": "2026-07-20", "sector_name": "bank", "close": 102.0},
    ]

    rows = build_forward_label_rows(
        stock_prices,
        sector_prices,
        horizons=(1, 2),
        training_horizon=2,
        trading_dates=trading_dates,
    )

    first = next(row for row in rows if row["as_of_date"] == "2026-07-16")
    assert first["label_dates"]["future_excess_return_1d"] == "2026-07-17"
    assert first["labels"]["future_excess_return_1d"] is None
    assert first["label_dates"]["future_excess_return_2d"] == "2026-07-20"


def test_label_source_requires_bound_versioned_calendar_identity():
    from theme_sector_radar.ml.source import build_label_rows_from_source

    source = {
        "schema_version": "ml-stock-label-source-v1",
        "mode": "paper_shadow_research_only",
        "fixture_only": True,
        "strict_pit_eligible": False,
        "trading_calendar": {"sha256": "a" * 64},
        "stock_price_rows": [],
        "sector_price_rows": [],
    }
    calendar = {
        "dates": ["2026-07-16", "2026-07-17"],
        "source": "unit_test",
        "path": "calendar.json",
        "sha256": "b" * 64,
        "requested_start": "2026-07-16",
        "requested_end": "2026-07-17",
    }

    with pytest.raises(ValueError, match="calendar identity mismatch"):
        build_label_rows_from_source(
            source, trading_calendar=calendar, allow_fixture=True
        )


def test_dataset_builder_joins_identity_and_freezes_feature_manifest():
    from theme_sector_radar.ml.dataset import build_training_dataset
    from theme_sector_radar.ml.feature_builder import build_feature_row
    from theme_sector_radar.ml.schema import LABEL_DEFINITION, V1_FEATURE_NAMES

    feature = build_feature_row(
        {"code": "000001", "sector_name": "银行"},
        _bars(),
        as_of_date=str(_bars()[-1]["date"]),
    )
    label = {
        "as_of_date": feature["as_of_date"],
        "stock_code": "000001",
        "sector_name": "银行",
        "training_label": 0.03,
        "labels": {
            "future_return_1d": 0.01,
            "future_excess_return_1d": 0.005,
            "future_return_3d": 0.02,
            "future_excess_return_3d": 0.01,
            "future_return_5d": 0.04,
            "future_excess_return_5d": 0.03,
        },
        "label_definition": LABEL_DEFINITION,
        "max_label_horizon": 5,
        "label_dates": {
            "future_excess_return_1d": "2026-01-26",
            "future_excess_return_3d": "2026-01-28",
            "future_excess_return_5d": "2026-01-30",
        },
        "training_label_end_date": "2026-01-30",
    }

    second_feature = dict(feature)
    second_feature["stock_code"] = "000002"

    dataset = build_training_dataset(
        [feature, second_feature], [label], strict_pit_eligible=False
    )

    assert dataset["status"] == "ok"
    assert dataset["strict_pit_eligible"] is False
    assert dataset["feature_names"] == list(V1_FEATURE_NAMES)
    assert dataset["label_definition"] == LABEL_DEFINITION
    assert len(dataset["dataset_sha256"]) == 64
    assert dataset["records"][0]["training_label"] == 0.03
    assert len(dataset["feature_universe_records"]) == 2
    assert len(dataset["evaluation_label_records"]) == 1
    assert dataset["counts"]["unmatched_feature_rows"] == 1

    with pytest.raises(ValueError, match="self-attested strict PIT"):
        build_training_dataset([feature], [label], strict_pit_eligible=True)


def test_dataset_rejects_training_label_or_safety_envelope_tampering():
    from theme_sector_radar.ml.dataset import (
        build_training_dataset,
        validate_training_dataset,
    )
    from theme_sector_radar.ml.feature_builder import build_feature_row
    from theme_sector_radar.ml.schema import LABEL_DEFINITION

    feature = build_feature_row(
        {"code": "000001", "sector_name": "bank"},
        _bars(),
        as_of_date=str(_bars()[-1]["date"]),
    )
    label = {
        "as_of_date": feature["as_of_date"],
        "stock_code": "000001",
        "sector_name": "bank",
        "training_label": 0.99,
        "labels": {"future_excess_return_5d": 0.03},
        "label_dates": {"future_excess_return_5d": "2026-01-30"},
        "training_label_end_date": "2026-01-30",
        "label_definition": LABEL_DEFINITION,
        "max_label_horizon": 5,
    }
    with pytest.raises(ValueError, match="training label must equal"):
        build_training_dataset([feature], [label], strict_pit_eligible=False)

    label["training_label"] = 0.03
    dataset = build_training_dataset([feature], [label], strict_pit_eligible=False)
    dataset["strict_pit_eligible"] = True
    with pytest.raises(ValueError, match="safety envelope"):
        validate_training_dataset(dataset)


def test_dataset_rejects_cross_view_feature_or_label_identity_drift():
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.dataset import validate_training_dataset
    from theme_sector_radar.reporting.strict_json import load_strict_json

    fixture = (
        Path(__file__).resolve().parents[2]
        / "reports/paper_shadow/ml_stock_ranker/synthetic_fixture_calendar_v2_2026-07-18/dataset.json"
    )
    dataset = load_strict_json(fixture)
    dataset["live_trading_allowed"] = False
    dataset["feature_universe_records"][0]["features"]["momentum_1d"] += 123.0
    core = {
        key: dataset[key]
        for key in (
            "schema_version", "mode", "feature_schema_version",
            "feature_schema_sha256", "feature_names", "label_definition",
            "max_label_horizon", "strict_pit_eligible", "pit_evidence_status",
            "eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed",
            "fixture_only",
            "feature_universe_records", "evaluation_label_records", "records",
        )
    }
    dataset["dataset_sha256"] = canonical_sha256(core)

    with pytest.raises(ValueError, match="cross-view feature mismatch"):
        validate_training_dataset(dataset)


def test_walk_forward_split_groups_dates_and_enforces_five_day_purge():
    from theme_sector_radar.ml.split import expanding_walk_forward_splits

    records = []
    for day_index in range(20):
        day = (date(2026, 3, 1) + timedelta(days=day_index)).isoformat()
        for code in ("000001", "000002"):
            records.append({"as_of_date": day, "stock_code": code})

    folds = expanding_walk_forward_splits(
        records,
        min_train_dates=5,
        test_dates=2,
        purge_dates=5,
        max_label_horizon=5,
    )

    assert folds[0]["train_dates"] == [
        (date(2026, 3, 1) + timedelta(days=index)).isoformat() for index in range(5)
    ]
    assert folds[0]["purged_dates"] == [
        (date(2026, 3, 1) + timedelta(days=index)).isoformat() for index in range(5, 10)
    ]
    assert folds[0]["test_dates"] == ["2026-03-11", "2026-03-12"]
    assert len(folds[0]["train_indices"]) == 10
    assert len(folds[0]["test_indices"]) == 4

    with pytest.raises(ValueError, match="purge_dates must be at least"):
        expanding_walk_forward_splits(
            records,
            min_train_dates=5,
            test_dates=2,
            purge_dates=4,
            max_label_horizon=5,
        )


def test_ranker_discretizes_continuous_labels_within_contiguous_date_groups():
    from theme_sector_radar.ml.ranker import prepare_ranking_matrix
    from theme_sector_radar.ml.schema import V1_FEATURE_NAMES

    records = []
    for day in ("2026-04-02", "2026-04-01"):
        for code, label in (("000003", 0.1), ("000001", -0.1), ("000002", 0.0)):
            records.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "features": {
                        name: float(index + int(code[-1]))
                        for index, name in enumerate(V1_FEATURE_NAMES)
                    },
                    "training_label": label,
                }
            )

    matrix = prepare_ranking_matrix(records)

    assert matrix["groups"] == [3, 3]
    assert matrix["dates"] == ["2026-04-01"] * 3 + ["2026-04-02"] * 3
    assert matrix["stock_codes"] == ["000001", "000002", "000003"] * 2
    assert matrix["relevance_labels"].tolist() == [0, 2, 4, 0, 2, 4]
    assert matrix["continuous_labels"].tolist() == [-0.1, 0.0, 0.1] * 2
    assert min(matrix["relevance_labels"]) >= 0


def _synthetic_training_records(date_count: int = 12, stock_count: int = 8):
    from theme_sector_radar.ml.schema import V1_FEATURE_NAMES

    rows = []
    for day_index in range(date_count):
        signal_day = date(2026, 4, 1) + timedelta(days=day_index)
        day = signal_day.isoformat()
        for stock_index in range(stock_count):
            signal = stock_index / max(stock_count - 1, 1)
            rows.append(
                {
                    "as_of_date": day,
                    "stock_code": f"{stock_index + 1:06d}",
                    "sector_name": "合成行业",
                    "features": {
                        name: float(signal + feature_index * 0.001 + day_index * 0.0001)
                        for feature_index, name in enumerate(V1_FEATURE_NAMES)
                    },
                    "feature_coverage": 1.0,
                    "labels": {
                        "future_return_1d": signal * 0.01,
                        "future_excess_return_1d": signal * 0.005,
                        "future_return_3d": signal * 0.02,
                        "future_excess_return_3d": signal * 0.01,
                        "future_return_5d": signal * 0.04,
                        "future_excess_return_5d": signal * 0.03,
                    },
                    "training_label": signal * 0.03 - 0.015,
                    "label_dates": {
                        "future_excess_return_1d": (signal_day + timedelta(days=1)).isoformat(),
                        "future_excess_return_3d": (signal_day + timedelta(days=3)).isoformat(),
                        "future_excess_return_5d": (signal_day + timedelta(days=5)).isoformat(),
                    },
                    "training_label_end_date": (signal_day + timedelta(days=5)).isoformat(),
                }
            )
    return rows


def test_lightgbm_bundle_round_trip_binds_schema_versions_and_hashes(tmp_path):
    from theme_sector_radar.ml.ranker import RankerModel, train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.ml.schema import LABEL_DEFINITION, V1_FEATURE_NAMES

    records = _synthetic_training_records()
    trained = train_lambdarank(records, n_estimators=12)
    output = tmp_path / "model"

    saved = save_model_bundle(
        trained,
        output,
        model_version="stock_ranker_lgbm_v1_test",
        dataset_sha256="a" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    loaded = load_model_bundle(
        output, expected_registry_sha256=saved["registry_sha256"]
    )

    with pytest.raises(TypeError):
        loaded.booster.params["objective"] = "tampered"

    assert saved["registry"]["label_definition"] == LABEL_DEFINITION
    assert saved["registry"]["feature_names"] == list(V1_FEATURE_NAMES)
    assert saved["registry"]["training_period"]["date_count"] == 12
    assert len(saved["registry"]["model_artifact"]["sha256"]) == 64
    assert len(saved["registry_sha256"]) == 64
    from theme_sector_radar.ml.ranker import prepare_prediction_matrix
    from theme_sector_radar.ml.registry import predict_verified_booster

    matrix = prepare_prediction_matrix(records[:8])
    before = trained.booster.predict(matrix["features"])
    after = predict_verified_booster(loaded, matrix["features"])
    assert after.tolist() == pytest.approx(before.tolist())


def test_model_bundle_requires_external_registry_sha_and_rejects_reclassification(tmp_path):
    import hashlib

    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json,
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    trained = train_lambdarank(_synthetic_training_records(), n_estimators=4)
    output = tmp_path / "model"
    saved = save_model_bundle(
        trained,
        output,
        model_version="stock_ranker_lgbm_v1_fixture",
        dataset_sha256="9" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    registry = load_strict_json(output / "registry.json")
    registry["dataset_classification"] = "observed_research"
    write_strict_json_atomic(output / "registry.json", registry)

    with pytest.raises(ValueError, match="registry SHA mismatch"):
        load_model_bundle(
            output, expected_registry_sha256=saved["registry_sha256"]
        )

    registry["strict_pit_eligible"] = True
    write_strict_json_atomic(output / "registry.json", registry)
    tampered_sha = hashlib.sha256((output / "registry.json").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="safety envelope"):
        load_model_bundle(output, expected_registry_sha256=tampered_sha)


def test_legacy_fixture_registry_without_live_flag_is_rejected(tmp_path):
    import hashlib

    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json,
        write_strict_json_atomic,
    )

    trained = train_lambdarank(_synthetic_training_records(), n_estimators=4)
    output = tmp_path / "legacy-model"
    save_model_bundle(
        trained,
        output,
        model_version="legacy-fixture",
        dataset_sha256="8" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    registry = load_strict_json(output / "registry.json")
    registry.pop("live_trading_allowed")
    write_strict_json_atomic(output / "registry.json", registry)
    registry_sha = hashlib.sha256((output / "registry.json").read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="safety envelope"):
        load_model_bundle(output, expected_registry_sha256=registry_sha)


def test_synthetic_fixture_registry_requires_experiment_contract(tmp_path):
    import hashlib

    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json,
        write_strict_json_atomic,
    )

    trained = train_lambdarank(_synthetic_training_records(), n_estimators=4)
    output = tmp_path / "fixture-model"
    save_model_bundle(
        trained,
        output,
        model_version="fixture-without-contract",
        dataset_sha256="7" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    registry = load_strict_json(output / "registry.json")
    registry.pop("experiment")
    write_strict_json_atomic(output / "registry.json", registry)
    registry_sha = hashlib.sha256((output / "registry.json").read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="experiment contract"):
        load_model_bundle(output, expected_registry_sha256=registry_sha)


def test_legacy_fixture_dataset_without_live_flag_is_rejected():
    from theme_sector_radar.ml.dataset import (
        build_training_dataset,
        validate_training_dataset,
    )

    feature, label = _feature_and_label()
    dataset = build_training_dataset([feature], [label], strict_pit_eligible=False)
    dataset.pop("live_trading_allowed")

    with pytest.raises(ValueError, match="safety envelope"):
        validate_training_dataset(dataset)


def test_strict_registry_evidence_must_reverify_archive(tmp_path):
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.registry import _validate_pit_evidence

    core = {
        "schema_version": "ml-stock-pit-evidence-v1",
        "mode": "paper_shadow_research_only",
        "status": "verified",
        "verifier": "theme_sector_radar.ml.accumulation.verify_accumulation_archive",
        "archive_root": str(tmp_path),
        "strict_pit_eligible": True,
        "minimum_60_dates_satisfied": True,
    }
    evidence = {**core, "evidence_sha256": canonical_sha256(core)}

    with pytest.raises((ValueError, FileNotFoundError)):
        _validate_pit_evidence(evidence)


def test_predictor_outputs_daily_percentiles_and_fails_closed_on_drift(tmp_path):
    from theme_sector_radar.ml.predictor import predict_shadow
    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.ml.schema import FEATURE_SCHEMA_VERSION, feature_schema_sha256

    trained = train_lambdarank(_synthetic_training_records(), n_estimators=12)
    output = tmp_path / "model"
    saved = save_model_bundle(
        trained,
        output,
        model_version="stock_ranker_lgbm_v1_test",
        dataset_sha256="b" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    loaded = load_model_bundle(
        output, expected_registry_sha256=saved["registry_sha256"]
    )
    prediction_rows = []
    for day_index, record in enumerate(
        _synthetic_training_records(date_count=2, stock_count=4)
    ):
        prediction_rows.append(
            {
                "schema_version": FEATURE_SCHEMA_VERSION,
                "as_of_date": (
                    date(2026, 4, 18) + timedelta(days=day_index // 4)
                ).isoformat(),
                "stock_code": record["stock_code"],
                "sector_name": record["sector_name"],
                "features": record["features"],
                "feature_coverage": 1.0,
                "provenance": {"feature_schema_sha256": feature_schema_sha256()},
            }
        )

    report = predict_shadow(loaded, prediction_rows, allow_fixture=True)

    assert report["status"] == "ok"
    assert report["mode"] == "paper_shadow_research_only"
    assert len(report["predictions"]) == 8
    for day in ("2026-04-18", "2026-04-19"):
        daily = [row for row in report["predictions"] if row["as_of_date"] == day]
        assert sorted(row["rank"] for row in daily) == [1, 2, 3, 4]
        assert sorted(row["ml_quant_score_shadow"] for row in daily) == pytest.approx(
            [0.0, 33.333333, 66.666667, 100.0]
        )
        assert all("prediction" in row and "top_drivers" in row for row in daily)

    drifted = [dict(prediction_rows[0])]
    drifted[0]["features"] = dict(reversed(list(drifted[0]["features"].items())))
    unavailable = predict_shadow(loaded, drifted, allow_fixture=True)
    assert unavailable["status"] == "unavailable"
    assert unavailable["reason"] == "feature_or_model_contract_rejected"
    assert unavailable["predictions"] == []


def test_predictor_fails_closed_outside_training_forward_window(tmp_path):
    from theme_sector_radar.ml.predictor import predict_shadow
    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.ml.schema import FEATURE_SCHEMA_VERSION, feature_schema_sha256

    trained = train_lambdarank(_synthetic_training_records(), n_estimators=4)
    output = tmp_path / "model"
    saved = save_model_bundle(
        trained,
        output,
        model_version="stock_ranker_lgbm_v1_test",
        dataset_sha256="e" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    loaded = load_model_bundle(
        output, expected_registry_sha256=saved["registry_sha256"]
    )
    record = _synthetic_training_records(date_count=1, stock_count=1)[0]
    feature_row = {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "as_of_date": "2026-06-02",
        "stock_code": record["stock_code"],
        "sector_name": record["sector_name"],
        "features": record["features"],
        "feature_coverage": 1.0,
        "provenance": {"feature_schema_sha256": feature_schema_sha256()},
    }

    report = predict_shadow(loaded, [feature_row], allow_fixture=True)

    assert report["status"] == "unavailable"
    assert report["reason"] == "feature_or_model_contract_rejected"

    feature_row["as_of_date"] = "2026-04-16"
    report = predict_shadow(loaded, [feature_row], allow_fixture=True)

    assert report["status"] == "unavailable"
    assert report["reason"] == "feature_or_model_contract_rejected"


def test_fixture_bundle_is_bound_and_rejected_by_normal_prediction(tmp_path):
    from theme_sector_radar.ml.predictor import predict_shadow
    from theme_sector_radar.ml.ranker import RankerModel, train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.ml.schema import FEATURE_SCHEMA_VERSION, feature_schema_sha256

    trained = train_lambdarank(_synthetic_training_records(), n_estimators=4)
    output = tmp_path / "fixture-model"
    saved = save_model_bundle(
        trained,
        output,
        model_version="fixture",
        dataset_sha256="f" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    loaded = load_model_bundle(
        output, expected_registry_sha256=saved["registry_sha256"]
    )
    record = _synthetic_training_records(date_count=1, stock_count=1)[0]
    row = {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "as_of_date": "2026-04-17",
        "stock_code": record["stock_code"],
        "sector_name": record["sector_name"],
        "features": record["features"],
        "feature_coverage": 1.0,
        "provenance": {"feature_schema_sha256": feature_schema_sha256()},
    }

    assert saved["registry"]["dataset_classification"] == "synthetic_fixture"
    assert predict_shadow(loaded, [row])["status"] == "unavailable"
    assert predict_shadow(loaded, [row], allow_fixture=True)["status"] == "ok"
    with pytest.raises(RuntimeError, match="verified|shadow"):
        loaded.booster.predict([[0.0] * len(loaded.feature_names)])

    original_version = loaded.metadata["model_version"]
    loaded.metadata["model_version"] = "forged-version"
    assert predict_shadow(loaded, [row], allow_fixture=True)["status"] == "unavailable"
    loaded.metadata["model_version"] = original_version

    forged_direct_wrapper = RankerModel(
        booster=loaded.booster,
        feature_names=loaded.feature_names,
        metadata=dict(loaded.metadata),
    )
    assert (
        predict_shadow(forged_direct_wrapper, [row], allow_fixture=True)["status"]
        == "unavailable"
    )

    for field, value in (
        ("dataset_classification", None),
        ("dataset_classification", "unknown"),
        ("eligible_for_oos_claim", True),
        ("promotion_allowed", True),
        ("live_trading_allowed", None),
        ("live_trading_allowed", True),
    ):
        metadata = dict(loaded.metadata)
        if value is None:
            metadata.pop(field, None)
        else:
            metadata[field] = value
        tampered = RankerModel(
            booster=loaded.booster,
            feature_names=loaded.feature_names,
            metadata=metadata,
        )
        assert (
            predict_shadow(tampered, [row], allow_fixture=True)["status"]
            == "unavailable"
        )

    from theme_sector_radar.ml.experiment import (
        build_effective_experiment_config,
        default_experiment_config,
        experiment_config_sha256,
    )

    observed_config = build_effective_experiment_config(
        default_experiment_config(), model_overrides={"n_estimators": 4}
    )
    forged_observed_metadata = dict(loaded.metadata)
    forged_observed_metadata.update(
        {
            "dataset_classification": "observed_research",
            "strict_pit_eligible": True,
            "experiment": {
                "config": observed_config,
                "config_sha256": experiment_config_sha256(observed_config),
            },
            "pit_evidence": None,
        }
    )
    forged_observed = RankerModel(
        booster=loaded.booster,
        feature_names=loaded.feature_names,
        metadata=forged_observed_metadata,
    )
    assert predict_shadow(forged_observed, [row])['status'] == 'unavailable'


def test_evaluation_compares_rule_ml_hybrid_and_consensus_same_day():
    from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow

    predictions = []
    dataset_records = []
    rule_rows = []
    for day_index in range(6):
        day = (date(2026, 5, 1) + timedelta(days=day_index)).isoformat()
        for stock_index in range(4):
            code = f"{stock_index + 1:06d}"
            excess = stock_index * 0.01 - 0.015
            predictions.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "行业A" if stock_index < 2 else "行业B",
                    "ml_quant_score_shadow": stock_index * 25.0,
                }
            )
            dataset_records.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "行业A" if stock_index < 2 else "行业B",
                    "labels": {
                        f"future_return_{horizon}d": excess + 0.005
                        for horizon in (1, 3, 5)
                    }
                    | {
                        f"future_excess_return_{horizon}d": excess
                        for horizon in (1, 3, 5)
                    },
                }
            )
            rule_rows.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "rule_score": 100.0 - stock_index * 25.0,
                    "rule_eligible": True,
                }
            )

    report = evaluate_rule_vs_ml_shadow(
        {"status": "ok", "predictions": predictions},
        {
            "evaluation_label_records": [
                row for row in dataset_records if row["stock_code"] != "000004"
            ],
            "strict_pit_eligible": False,
        },
        rule_rows,
        top_ks=(2,),
    )

    a_5d = next(
        row for row in report["results"]
        if row["strategy"] == "A_rule" and row["top_k"] == 2 and row["horizon"] == 5
    )
    b_5d = next(
        row for row in report["results"]
        if row["strategy"] == "B_ml" and row["top_k"] == 2 and row["horizon"] == 5
    )
    assert b_5d["mean_excess_return"] > a_5d["mean_excess_return"]
    assert b_5d["spearman_ic"] == pytest.approx(1.0)
    assert b_5d["coverage_ratio"] == 0.5
    assert b_5d["turnover"] == 0.0
    assert b_5d["max_drawdown"] is None
    assert report["paired_date_count"] == 6
    assert report["label_coverage_by_horizon"]["5d"] == 0.75
    assert report["promotion_status"] == "architecture_only_shadow"
    assert report["promotion_allowed"] is False
    assert {row["strategy"] for row in report["results"]} == {
        "A_rule", "B_ml", "C_rule_gate_ml_rank", "D_consensus"
    }
    assert report["feature_drift"]["status"] == "unavailable"


def test_stage_one_evaluation_can_never_promote_without_complete_hard_gates():
    from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow

    predictions = []
    dataset_records = []
    rule_rows = []
    for day_index in range(60):
        day = (date(2025, 1, 1) + timedelta(days=day_index)).isoformat()
        for stock_index in range(2):
            code = f"{stock_index + 1:06d}"
            predictions.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "行业",
                    "ml_quant_score_shadow": float(stock_index * 100),
                }
            )
            dataset_records.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "行业",
                    "labels": {
                        f"future_return_{horizon}d": 0.01 * stock_index
                        for horizon in (1, 3, 5)
                    }
                    | {
                        f"future_excess_return_{horizon}d": 0.01 * stock_index
                        for horizon in (1, 3, 5)
                    },
                }
            )
            rule_rows.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "rule_score": float(stock_index * 100),
                    "rule_eligible": True,
                }
            )

    report = evaluate_rule_vs_ml_shadow(
        {"status": "ok", "predictions": predictions},
            {"evaluation_label_records": dataset_records, "strict_pit_eligible": False},
        rule_rows,
        top_ks=(1,),
    )

    assert report is not None
    assert report["promotion_allowed"] is False
    assert report["strict_pit_eligible"] is False
    assert report["promotion_status"] == "architecture_only_shadow"
    assert report["promotion_gates"]["complete_performance_hard_gates"] is False


def test_multi_baseline_evaluation_uses_one_common_candidate_pool():
    from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow

    day = "2026-07-16"
    predictions = {
        "status": "ok",
        "fixture_only": False,
        "predictions": [
            {
                "as_of_date": day,
                "stock_code": code,
                "sector_name": "sector-a",
                "ml_quant_score_shadow": ml_score,
            }
            for code, ml_score in (
                ("000001", 90.0),
                ("000002", 60.0),
                ("000003", 30.0),
            )
        ],
    }
    dataset = {
        "fixture_only": False,
        "strict_pit_eligible": False,
        "evaluation_label_records": [
            {
                "as_of_date": day,
                "stock_code": code,
                "sector_name": "sector-a",
                "labels": {
                    "future_return_1d": outcome,
                    "future_excess_return_1d": outcome,
                },
            }
            for code, outcome in (
                ("000001", 0.01),
                ("000002", 0.00),
                ("000003", -0.01),
            )
        ],
    }
    rules = [
        {
            "as_of_date": day,
            "stock_code": "000001",
            "sector_name": "sector-a",
            "quant_baseline_score_shadow": 90.0,
            "linkage_v2_baseline_score_shadow": 80.0,
            "linkage_v2_status": "ok",
            "rule_eligible": True,
        },
        {
            "as_of_date": day,
            "stock_code": "000002",
            "sector_name": "sector-a",
            "quant_baseline_score_shadow": 60.0,
            "linkage_v2_baseline_score_shadow": 50.0,
            "linkage_v2_status": "partial",
            "rule_eligible": True,
        },
        {
            "as_of_date": day,
            "stock_code": "000003",
            "sector_name": "sector-a",
            "quant_baseline_score_shadow": 30.0,
            "linkage_v2_baseline_score_shadow": None,
            "linkage_v2_status": "unavailable",
            "rule_eligible": True,
        },
    ]

    report = evaluate_rule_vs_ml_shadow(
        predictions,
        dataset,
        rules,
        top_ks=(3,),
        horizons=(1,),
    )

    assert {row["selected_row_count"] for row in report["results"]} == {3}
    assert {row["selection_fill_ratio"] for row in report["results"]} == {1.0}
    assert set(
        report["ranking_audit"][0]["selections"]["B_linkage_v2"]
    ) == {"000001", "000002", "000003"}


def test_walk_forward_ranker_trains_only_before_purge_and_keeps_continuous_labels():
    from theme_sector_radar.ml.ranker import walk_forward_ranker_predictions

    records = _synthetic_training_records(date_count=16, stock_count=6)
    feature_universe = [
        {
            key: value
            for key, value in row.items()
            if key not in {"labels", "training_label", "label_dates", "training_label_end_date"}
        }
        for row in records
    ]
    for day_index in range(16):
        template = feature_universe[day_index * 6]
        feature_universe.append(
            {
                **template,
                "stock_code": "999999",
                "features": {
                    name: value + 0.5 for name, value in template["features"].items()
                },
            }
        )
    report = walk_forward_ranker_predictions(
        records,
        prediction_universe_records=feature_universe,
        min_train_dates=5,
        test_dates=3,
        purge_dates=5,
        n_estimators=5,
    )

    assert report["status"] == "ok"
    assert report["folds"][0]["train_end"] == "2026-04-05"
    assert report["folds"][0]["purged_dates"] == [
        "2026-04-06", "2026-04-07", "2026-04-08", "2026-04-09", "2026-04-10"
    ]
    assert report["folds"][0]["test_start"] == "2026-04-11"
    assert len(report["predictions"]) == 42
    missing = [row for row in report["predictions"] if row["stock_code"] == "999999"]
    assert len(missing) == 6
    assert all(row["label_available"] is False for row in missing)
    assert all("continuous_label" not in row for row in missing)
    for day in sorted({row["as_of_date"] for row in report["predictions"]}):
        daily = [row for row in report["predictions"] if row["as_of_date"] == day]
        assert sorted(row["ml_quant_score_shadow"] for row in daily) == pytest.approx(
            [0.0, 16.666667, 33.333333, 50.0, 66.666667, 83.333333, 100.0]
        )


def test_walk_forward_requires_minimum_mature_labeled_training_dates():
    from theme_sector_radar.ml.ranker import walk_forward_ranker_predictions

    labeled = _synthetic_training_records(date_count=2, stock_count=2)
    template = labeled[0]
    feature_universe = []
    for offset in range(70):
        day = (date(2026, 4, 1) + timedelta(days=offset)).isoformat()
        for stock_index in range(2):
            feature_universe.append(
                {
                    "as_of_date": day,
                    "stock_code": f"{stock_index + 1:06d}",
                    "sector_name": "合成行业",
                    "features": dict(template["features"]),
                    "feature_coverage": 1.0,
                }
            )

    report = walk_forward_ranker_predictions(
        labeled,
        prediction_universe_records=feature_universe,
        min_train_dates=60,
        test_dates=2,
        purge_dates=5,
        n_estimators=2,
    )

    assert report["status"] == "insufficient_data"
    assert report["reason"] == "fewer_than_minimum_mature_training_dates"


def test_optional_ml_dependency_failure_is_explicit_and_has_no_fallback(monkeypatch):
    import theme_sector_radar.ml.contract as contract
    from theme_sector_radar.ml.ranker import train_lambdarank

    original = contract.import_optional_ml_module

    def fail_lightgbm(package):
        if package == "lightgbm":
            raise ImportError("not installed")
        return original(package)

    monkeypatch.setattr(contract, "import_optional_ml_module", fail_lightgbm)

    readiness = contract.optional_ml_dependency_readiness()
    assert readiness["status"] == "unavailable"
    assert readiness["missing_packages"] == ["lightgbm"]
    with pytest.raises(RuntimeError, match="optional ML dependencies unavailable"):
        train_lambdarank(_synthetic_training_records(), n_estimators=2)


def test_optional_ml_dependency_value_error_is_reported_as_unavailable(monkeypatch):
    import theme_sector_radar.ml.contract as contract

    original = contract.import_optional_ml_module

    def fail_numpy(package):
        if package == "numpy":
            raise ValueError("ABI mismatch")
        return original(package)

    monkeypatch.setattr(contract, "import_optional_ml_module", fail_numpy)

    readiness = contract.optional_ml_dependency_readiness()
    assert readiness["status"] == "unavailable"
    assert readiness["missing_packages"] == ["numpy"]
    assert readiness["import_errors"]["numpy"].startswith("ValueError:")


def test_model_bundle_rejects_model_artifact_tampering(tmp_path):
    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle

    trained = train_lambdarank(_synthetic_training_records(), n_estimators=4)
    output = tmp_path / "model"
    saved = save_model_bundle(
        trained,
        output,
        model_version="stock_ranker_lgbm_v1_test",
        dataset_sha256="c" * 64,
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from="2026-04-17",
    )
    with (output / "model.txt").open("a", encoding="utf-8") as handle:
        handle.write("\n# tampered\n")

    with pytest.raises(ValueError, match="model artifact SHA mismatch"):
        load_model_bundle(
            output, expected_registry_sha256=saved["registry_sha256"]
        )


def test_evaluation_concentration_uses_full_selection_and_single_day_turnover_is_unavailable():
    from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow

    day = "2026-07-16"
    predictions = {
        "status": "ok",
        "fixture_only": False,
        "predictions": [
            {
                "as_of_date": day,
                "stock_code": code,
                "sector_name": "same_sector",
                "ml_quant_score_shadow": score,
            }
            for code, score in (("000001", 100.0), ("000002", 0.0))
        ],
    }
    dataset = {
        "fixture_only": False,
        "evaluation_label_records": [
            {
                "as_of_date": day,
                "stock_code": "000001",
                "sector_name": "same_sector",
                "labels": {
                    "future_return_1d": 0.01,
                    "future_excess_return_1d": 0.01,
                },
            }
        ],
    }
    rules = [
        {
            "as_of_date": day,
            "stock_code": code,
            "rule_score": score,
            "rule_eligible": True,
        }
        for code, score in (("000001", 100.0), ("000002", 0.0))
    ]

    report = evaluate_rule_vs_ml_shadow(
        predictions, dataset, rules, top_ks=(2,), horizons=(1,)
    )
    ml_result = next(
        row for row in report["results"] if row["strategy"] == "B_ml"
    )

    assert ml_result["sector_concentration"] == 1.0
    assert ml_result["turnover"] is None


def test_synthetic_fixture_sources_use_explicit_anchor_date():
    from scripts.run_ml_stock_synthetic_fixture import _sources

    feature_source, label_source = _sources(anchor_date=date(2026, 7, 18))

    assert feature_source["anchor_date"] == "2026-07-18"
    assert label_source["anchor_date"] == "2026-07-18"
    assert feature_source["snapshots"][-1]["as_of_date"] == "2026-07-17"
    assert all(
        date.fromisoformat(value).weekday() < 5
        for value in label_source["trading_calendar"]["dates"]
    )


def test_observed_feature_source_requires_verified_archive_identity():
    from theme_sector_radar.ml.source import build_feature_rows_from_source

    source = {
        "schema_version": "ml-stock-feature-source-v1",
        "mode": "paper_shadow_research_only",
        "fixture_only": False,
        "strict_pit_eligible": True,
        "snapshots": [],
    }
    with pytest.raises(ValueError, match="PIT manifest|physical identity"):
        build_feature_rows_from_source(source)


def test_observed_feature_source_must_replay_verified_archive_rows(
    tmp_path, monkeypatch
):
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.source import build_feature_rows_from_source
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    day = str(_bars()[-1]["date"])
    candidate = {"code": "000001", "sector_name": "bank", "pe": 6.0}
    archive_root = tmp_path / "archive"
    snapshot_path = archive_root / "snapshots" / f"{day}.json"
    archive_snapshot = {
        "as_of_date": day,
        "feature_candidates": [candidate],
        "bars_by_code": {"000001": _bars()},
    }
    write_strict_json_atomic(snapshot_path, archive_snapshot)
    _snapshot, snapshot_sha = load_strict_json_with_sha256(snapshot_path)
    evidence_core = {
        "archive_root": str(archive_root.resolve()),
        "strict_pit_eligible": True,
        "snapshots": [
            {
                "as_of_date": day,
                "path": str(snapshot_path.resolve()),
                "sha256": snapshot_sha,
                "strict_pit_eligible": True,
            }
        ],
    }
    evidence = {
        **evidence_core,
        "evidence_sha256": canonical_sha256(evidence_core),
    }
    monkeypatch.setattr(
        "theme_sector_radar.ml.accumulation.verify_accumulation_archive",
        lambda _root: evidence,
    )
    source = {
        "schema_version": "ml-stock-feature-source-v1",
        "mode": "paper_shadow_research_only",
        "fixture_only": False,
        "strict_pit_eligible": True,
        "source_manifest": {
            "archive_root": str(archive_root.resolve()),
            "pit_evidence_sha256": evidence["evidence_sha256"],
        },
        "snapshots": [
            {
                "as_of_date": day,
                "candidates": [{**candidate, "pe": 600.0}],
                "bars_by_code": {"000001": _bars()},
            }
        ],
    }
    source_path = tmp_path / "feature_source.json"
    write_strict_json_atomic(source_path, source)
    _source, source_sha = load_strict_json_with_sha256(source_path)

    with pytest.raises(ValueError, match="verified archive"):
        build_feature_rows_from_source(
            source,
            source_identity={"path": str(source_path.resolve()), "sha256": source_sha},
        )


def test_observed_feature_source_rejects_non_strict_archive_snapshot(
    tmp_path, monkeypatch
):
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.source import build_feature_rows_from_source
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    day = str(_bars()[-1]["date"])
    archive_root = tmp_path / "archive"
    snapshot_path = archive_root / "snapshots" / f"{day}.json"
    candidate = {"code": "000001", "sector_name": "bank", "pe": 6.0}
    snapshot = {
        "as_of_date": day,
        "feature_candidates": [candidate],
        "bars_by_code": {"000001": _bars()},
    }
    write_strict_json_atomic(snapshot_path, snapshot)
    _snapshot, snapshot_sha = load_strict_json_with_sha256(snapshot_path)
    evidence_core = {
        "archive_root": str(archive_root.resolve()),
        "strict_pit_eligible": True,
        "snapshots": [
            {
                "as_of_date": day,
                "path": str(snapshot_path.resolve()),
                "sha256": snapshot_sha,
                "strict_pit_eligible": False,
            }
        ],
    }
    evidence = {**evidence_core, "evidence_sha256": canonical_sha256(evidence_core)}
    monkeypatch.setattr(
        "theme_sector_radar.ml.accumulation.verify_accumulation_archive",
        lambda _root: evidence,
    )
    source = {
        "schema_version": "ml-stock-feature-source-v1",
        "mode": "paper_shadow_research_only",
        "fixture_only": False,
        "strict_pit_eligible": True,
        "source_manifest": {
            "archive_root": str(archive_root.resolve()),
            "pit_evidence_sha256": evidence["evidence_sha256"],
        },
        "snapshots": [
            {
                "as_of_date": day,
                "candidates": [candidate],
                "bars_by_code": {"000001": _bars()},
            }
        ],
    }
    source_path = tmp_path / "source.json"
    write_strict_json_atomic(source_path, source)
    _source, source_sha = load_strict_json_with_sha256(source_path)

    with pytest.raises(ValueError, match="strict"):
        build_feature_rows_from_source(
            source,
            source_identity={"path": str(source_path.resolve()), "sha256": source_sha},
        )


def test_observed_label_source_must_replay_verified_archive_rows(
    tmp_path, monkeypatch
):
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.source import build_label_rows_from_source
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    day = "2026-01-05"
    archive_root = tmp_path / "archive"
    label_snapshot_path = archive_root / "labels" / f"{day}.json"
    stock_rows = [{"date": day, "stock_code": "000001", "close": 10.0}]
    sector_rows = [{"date": day, "sector_name": "bank", "close": 100.0}]
    calendar = {
        "schema_version": "a_share_trading_calendar.v1",
        "market": "CN_A",
        "dates": [day, "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09", "2026-01-12"],
    }
    label_snapshot = {
        "signal_date": day,
        "stock_price_rows": stock_rows,
        "sector_price_rows": sector_rows,
        "source_manifest": {"trading_calendar": calendar},
    }
    write_strict_json_atomic(label_snapshot_path, label_snapshot)
    _label_doc, label_sha = load_strict_json_with_sha256(label_snapshot_path)
    evidence_core = {
        "archive_root": str(archive_root.resolve()),
        "strict_pit_eligible": True,
        "labels": [
            {
                "signal_date": day,
                "path": str(label_snapshot_path.resolve()),
                "sha256": label_sha,
                "strict_pit_eligible": True,
            }
        ],
    }
    evidence = {**evidence_core, "evidence_sha256": canonical_sha256(evidence_core)}
    monkeypatch.setattr(
        "theme_sector_radar.ml.accumulation.verify_accumulation_archive",
        lambda _root: evidence,
    )
    source = {
        "schema_version": "ml-stock-label-source-v1",
        "mode": "paper_shadow_research_only",
        "fixture_only": False,
        "strict_pit_eligible": True,
        "source_manifest": {
            "archive_root": str(archive_root.resolve()),
            "pit_evidence_sha256": evidence["evidence_sha256"],
        },
        "trading_calendar": calendar,
        "stock_price_rows": [{**stock_rows[0], "close": 999.0}],
        "sector_price_rows": sector_rows,
    }
    source_path = tmp_path / "label_source.json"
    write_strict_json_atomic(source_path, source)
    _source, source_sha = load_strict_json_with_sha256(source_path)

    with pytest.raises(ValueError, match="verified archive"):
        build_label_rows_from_source(
            source,
            source_identity={"path": str(source_path.resolve()), "sha256": source_sha},
        )


def test_ml_shadow_cli_synthetic_end_to_end(tmp_path):
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json,
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    project_root = Path(__file__).resolve().parents[2]
    stock_codes = [f"{index + 1:06d}" for index in range(6)]
    all_dates = []
    cursor = date.today()
    while len(all_dates) < 42:
        if cursor.weekday() < 5:
            all_dates.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    all_dates.reverse()
    snapshots = []
    for as_of_index in (*range(20, 36), 41):
        candidates = []
        bars_by_code = {}
        for stock_index, code in enumerate(stock_codes):
            candidates.append(
                {
                    "code": code,
                    "sector_name": "合成行业",
                    "pe": 10.0 + stock_index,
                    "pb": 1.0 + stock_index * 0.1,
                    "total_mv": 100.0 + stock_index * 20,
                    "sector_trend_score": 60.0,
                    "sector_burst_score": 50.0,
                    "sector_direction_score": 65.0,
                    "data_quality_score": 100.0,
                    "factor_coverage": 1.0,
                }
            )
            bars_by_code[code] = [
                {
                    "date": all_dates[index],
                    "open": 10.0 + stock_index + index * (0.02 + stock_index * 0.002),
                    "high": 10.1 + stock_index + index * (0.02 + stock_index * 0.002),
                    "low": 9.9 + stock_index + index * (0.02 + stock_index * 0.002),
                    "close": 10.0 + stock_index + index * (0.02 + stock_index * 0.002),
                    "volume": 1_000_000 + stock_index * 100_000 + index * 1_000,
                    "amount": 10_000_000 + stock_index * 1_000_000 + index * 10_000,
                }
                for index in range(as_of_index + 1)
            ]
        snapshots.append(
            {
                "as_of_date": all_dates[as_of_index],
                "candidates": candidates,
                "bars_by_code": bars_by_code,
            }
        )
    feature_source = {
        "schema_version": "ml-stock-feature-source-v1",
        "mode": "paper_shadow_research_only",
        "fixture_only": True,
        "strict_pit_eligible": False,
        "snapshots": snapshots,
    }
    stock_price_rows = []
    sector_price_rows = []
    for index, day in enumerate(all_dates):
        sector_price_rows.append(
            {"date": day, "sector_name": "合成行业", "close": 100.0 + index * 0.1}
        )
        for stock_index, code in enumerate(stock_codes):
            stock_price_rows.append(
                {
                    "date": day,
                    "stock_code": code,
                    "sector_name": "合成行业",
                    "close": 10.0 + stock_index + index * (0.02 + stock_index * 0.002),
                }
            )
    label_source = {
        "schema_version": "ml-stock-label-source-v1",
        "mode": "paper_shadow_research_only",
        "fixture_only": True,
        "strict_pit_eligible": False,
        "trading_dates": all_dates,
        "stock_price_rows": stock_price_rows,
        "sector_price_rows": sector_price_rows,
    }
    calendar_payload = {
        "schema_version": "a_share_trading_calendar.v1",
        "market": "CN_A",
        "source": "unit_test_calendar",
        "requested_start": all_dates[0],
        "requested_end": all_dates[-1],
        "dates": all_dates,
        "date_count": len(all_dates),
    }
    feature_path = tmp_path / "feature_source.json"
    label_path = tmp_path / "label_source.json"
    calendar_path = tmp_path / "trading_calendar.json"
    dataset_path = tmp_path / "dataset.json"
    write_strict_json_atomic(calendar_path, calendar_payload)
    _calendar_doc, calendar_sha = load_strict_json_with_sha256(calendar_path)
    label_source["trading_calendar"] = {
        **calendar_payload,
        "path": str(calendar_path.resolve()),
        "sha256": calendar_sha,
    }
    write_strict_json_atomic(feature_path, feature_source)
    write_strict_json_atomic(label_path, label_source)

    build = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "build_ml_stock_dataset.py"),
            "--feature-source", str(feature_path),
            "--label-source", str(label_path),
            "--output", str(dataset_path),
            "--trading-calendar-path", str(calendar_path),
            "--expected-calendar-sha256", calendar_sha,
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    dataset = load_strict_json(dataset_path)
    _dataset_doc, dataset_file_sha = load_strict_json_with_sha256(dataset_path)
    assert dataset["status"] == "ok"
    assert dataset["date_range"]["date_count"] == 16
    assert len(dataset["records"]) == 96

    model_dir = tmp_path / "model"
    training_report_path = tmp_path / "training_report.json"
    walk_forward_path = tmp_path / "walk_forward_predictions.json"
    train = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "train_ml_stock_ranker_shadow.py"),
            "--dataset", str(dataset_path),
            "--expected-dataset-file-sha256", dataset_file_sha,
            "--model-dir", str(model_dir),
            "--report", str(training_report_path),
            "--walk-forward-output", str(walk_forward_path),
            "--model-version", "stock_ranker_lgbm_v1_fixture",
            "--model-available-from", all_dates[41],
            "--min-train-dates", "5",
            "--test-dates", "3",
            "--purge-dates", "5",
            "--n-estimators", "5",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert train.returncode == 0, train.stderr
    training_report = load_strict_json(training_report_path)
    assert training_report["status"] == "ok"
    assert (model_dir / "model.txt").exists()
    assert (model_dir / "registry.json").exists()

    prediction_path = tmp_path / "prediction.json"
    predict = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "run_ml_stock_shadow.py"),
            "--model-dir", str(model_dir),
            "--expected-registry-sha256",
            training_report["model_bundle"]["registry_sha256"],
            "--feature-source", str(feature_path),
            "--as-of", all_dates[41],
            "--output", str(prediction_path),
            "--allow-fixture",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert predict.returncode == 0, predict.stderr
    prediction = load_strict_json(prediction_path)
    assert prediction["status"] == "ok"
    assert len(prediction["predictions"]) == 6

    rule_path = tmp_path / "rules.json"
    rule_records = [
        {
            "as_of_date": row["as_of_date"],
            "stock_code": row["stock_code"],
            "rule_score": 100.0 - int(row["stock_code"]),
            "rule_eligible": True,
        }
        for row in dataset["feature_universe_records"]
    ]
    write_strict_json_atomic(
        rule_path,
        {"mode": "paper_shadow_research_only", "records": rule_records},
    )
    evaluation_path = tmp_path / "evaluation.json"
    evaluate = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "evaluate_rule_vs_ml_shadow.py"),
            "--predictions", str(walk_forward_path),
            "--dataset", str(dataset_path),
            "--expected-dataset-file-sha256", dataset_file_sha,
            "--rule-rows", str(rule_path),
            "--output", str(evaluation_path),
            "--top-k", "2", "3",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert evaluate.returncode == 0, evaluate.stderr
    evaluation = load_strict_json(evaluation_path)
    assert evaluation["status"] == "ok"
    assert evaluation["promotion_status"] == "architecture_only_shadow"


def test_real_data_readiness_fails_closed_when_only_one_candidate_date_exists():
    from theme_sector_radar.ml.readiness import build_data_readiness_report

    report = build_data_readiness_report(
        candidate_snapshots=[
            {"as_of_date": "2026-07-16", "candidate_count": 30, "stock_count": 30}
        ],
        forward_stock_return_dates_by_horizon={
            "1d": ["2026-07-16"],
            "3d": [],
            "5d": [],
        },
        forward_excess_label_dates_by_horizon={"1d": [], "3d": [], "5d": []},
        forward_label_coverage_by_horizon={"1d": 1.0, "3d": 0.0, "5d": 0.0},
        sector_history_date_count=117,
        historical_candidate_universe_versioned=False,
        source_manifest={"candidate_source_sha256": "d" * 64},
    )

    assert report["status"] == "insufficient_data"
    assert report["model_training_ready"] is False
    assert report["strict_pit_eligible"] is False
    assert report["counts"]["candidate_snapshot_dates"] == 1
    assert report["counts"]["forward_label_dates"] == 0
    assert report["counts"]["forward_stock_return_dates_by_horizon"] == {
        "1d": 1,
        "3d": 0,
        "5d": 0,
    }
    assert report["counts"]["forward_excess_label_dates_by_horizon"] == {
        "1d": 0,
        "3d": 0,
        "5d": 0,
    }
    assert report["blocking_reasons"] == [
        "fewer_than_60_candidate_snapshot_dates",
        "historical_candidate_universe_not_trusted",
        "fewer_than_60_mature_5d_excess_label_dates",
        "five_day_excess_label_coverage_below_90_percent",
    ]


def test_readiness_forward_coverage_uses_candidate_identity_intersection():
    from scripts.audit_ml_stock_data_readiness import _mature_stock_return_count

    day = "2026-07-16"
    payload = {
        "label_contract": {
            "schema_version": "forward-return-label-contract-v2",
            "frequency": "1d",
            "adjustment": "qfq",
            "target_date_basis": "versioned_exchange_calendar",
        },
        "forward_returns": {
            "000001": {"1d": 1.0},
            "999999": {"1d": 2.0},
        },
        "label_metadata": {
            code: {
                "signal_date": day,
                "frequency": "1d",
                "adjustment": "qfq",
                "signal_close": 10.0,
                "bar_snapshot_sha256": "a" * 64,
                "horizons": {
                    "1d": {
                        "horizon_trading_days": 1,
                        "target_trading_date": "2026-07-17",
                        "target_close": 10.1,
                        "mature": True,
                        "return_available": True,
                    }
                },
            }
            for code in ("000001", "999999")
        },
    }

    audit = _mature_stock_return_count(
        payload,
        day=day,
        horizon="1d",
        candidate_codes={"000001", "000002"},
    )

    assert audit == {
        "mature_candidate_rows": 1,
        "candidate_rows": 2,
        "forward_rows_outside_candidate_pool": 1,
        "candidate_rows_missing_from_forward": 1,
    }
