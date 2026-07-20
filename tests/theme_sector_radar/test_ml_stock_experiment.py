from __future__ import annotations

import copy

import pytest


def _small_training_records() -> list[dict]:
    from datetime import date, timedelta

    from theme_sector_radar.ml.schema import V1_FEATURE_NAMES

    records = []
    for day_index in range(2):
        for stock_index in range(2):
            records.append(
                {
                    "as_of_date": (
                        date(2026, 4, 1) + timedelta(days=day_index)
                    ).isoformat(),
                    "stock_code": f"00000{stock_index + 1}",
                    "sector_name": "bank",
                    "features": {
                        name: float(stock_index + day_index)
                        for name in V1_FEATURE_NAMES
                    },
                    "training_label": float(stock_index + day_index),
                    "training_label_end_date": (
                        date(2026, 4, 6) + timedelta(days=day_index)
                    ).isoformat(),
                    "labels": {
                        "future_excess_return_5d": float(stock_index + day_index)
                    },
                }
            )
    return records


def test_registered_ml_experiment_is_stable_and_paper_only():
    from theme_sector_radar.ml.experiment import (
        default_experiment_config,
        experiment_config_sha256,
        validate_experiment_config,
    )

    config = default_experiment_config()
    validated = validate_experiment_config(config)

    assert validated == config
    assert experiment_config_sha256(config) == experiment_config_sha256(validated)
    assert config["feature_contract"]["legacy_relevance_included"] is False
    assert config["safety"]["promotion_allowed"] is False
    assert config["safety"]["live_trading_allowed"] is False


def test_ml_experiment_rejects_legacy_relevance_or_weak_split():
    from theme_sector_radar.ml.experiment import (
        default_experiment_config,
        validate_experiment_config,
    )

    legacy = copy.deepcopy(default_experiment_config())
    legacy["feature_contract"]["legacy_relevance_included"] = True
    with pytest.raises(ValueError, match="legacy relevance"):
        validate_experiment_config(legacy)

    weak_split = copy.deepcopy(default_experiment_config())
    weak_split["split"]["min_train_dates"] = 20
    with pytest.raises(ValueError, match="split"):
        validate_experiment_config(weak_split)


def test_ml_experiment_rejects_any_live_or_promotion_flag():
    from theme_sector_radar.ml.experiment import (
        default_experiment_config,
        validate_experiment_config,
    )

    config = default_experiment_config()
    config["safety"]["live_trading_allowed"] = True
    with pytest.raises(ValueError, match="live_trading_allowed"):
        validate_experiment_config(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("backend", "other"),
        ("objective", "regression"),
        ("metric", ["map"]),
        ("label_gain", [0, 1, 2, 3, 4]),
    ],
)
def test_ml_experiment_rejects_booster_contract_drift(field, value):
    from theme_sector_radar.ml.experiment import (
        default_experiment_config,
        validate_experiment_config,
    )

    config = default_experiment_config()
    config["model"][field] = value

    with pytest.raises(ValueError, match="model|label_gain|metric|objective"):
        validate_experiment_config(config)


def test_effective_experiment_hash_includes_controlled_overrides():
    from theme_sector_radar.ml.experiment import (
        build_effective_experiment_config,
        default_experiment_config,
        experiment_config_sha256,
    )

    base = default_experiment_config()
    effective = build_effective_experiment_config(
        base,
        split_overrides={"test_dates": 1},
        model_overrides={"n_estimators": 2},
    )

    assert effective["split"]["test_dates"] == 1
    assert effective["model"]["n_estimators"] == 2
    assert experiment_config_sha256(effective) != experiment_config_sha256(base)


def test_observed_model_cannot_register_without_strict_experiment_contract(tmp_path):
    from theme_sector_radar.ml.experiment import (
        default_experiment_config,
        experiment_config_sha256,
    )
    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import save_model_bundle

    records = []
    for day_index in range(2):
        for stock_index in range(2):
            from datetime import date, timedelta
            from theme_sector_radar.ml.schema import V1_FEATURE_NAMES

            records.append(
                {
                    "as_of_date": (date(2026, 4, 1) + timedelta(days=day_index)).isoformat(),
                    "stock_code": f"00000{stock_index + 1}",
                    "sector_name": "bank",
                    "features": {name: float(stock_index + day_index) for name in V1_FEATURE_NAMES},
                    "training_label": float(stock_index + day_index),
                    "training_label_end_date": (date(2026, 4, 6) + timedelta(days=day_index)).isoformat(),
                    "labels": {"future_excess_return_5d": float(stock_index + day_index)},
                }
            )
    model = train_lambdarank(records, n_estimators=2)

    with pytest.raises(ValueError, match="strict PIT eligibility"):
        save_model_bundle(
            model,
            tmp_path / "observed-model",
            model_version="observed-without-pit",
            dataset_sha256="1" * 64,
            strict_pit_eligible=False,
            dataset_classification="observed_research",
            model_available_from="2026-04-06",
        )

    fixture_config = default_experiment_config()
    with pytest.raises(ValueError, match="model parameter mismatch"):
        save_model_bundle(
            model,
            tmp_path / "fixture-parameter-mismatch",
            model_version="fixture-parameter-mismatch",
            dataset_sha256="2" * 64,
            strict_pit_eligible=False,
            dataset_classification="synthetic_fixture",
            model_available_from="2026-04-06",
            experiment_config=fixture_config,
            experiment_config_sha256=experiment_config_sha256(fixture_config),
        )


def test_model_bundle_rejects_registry_parameters_that_disagree_with_booster(tmp_path):
    from theme_sector_radar.ml.experiment import (
        build_effective_experiment_config,
        experiment_config_sha256,
        default_experiment_config,
    )
    from theme_sector_radar.ml.ranker import RankerModel, train_lambdarank
    from theme_sector_radar.ml.registry import save_model_bundle

    records = []
    for day_index in range(2):
        for stock_index in range(2):
            from datetime import date, timedelta
            from theme_sector_radar.ml.schema import V1_FEATURE_NAMES

            records.append(
                {
                    "as_of_date": (date(2026, 4, 1) + timedelta(days=day_index)).isoformat(),
                    "stock_code": f"00000{stock_index + 1}",
                    "sector_name": "bank",
                    "features": {name: float(stock_index + day_index) for name in V1_FEATURE_NAMES},
                    "training_label": float(stock_index + day_index),
                    "training_label_end_date": (date(2026, 4, 6) + timedelta(days=day_index)).isoformat(),
                    "labels": {"future_excess_return_5d": float(stock_index + day_index)},
                }
            )
    trained = train_lambdarank(records, n_estimators=2)
    forged_metadata = copy.deepcopy(dict(trained.metadata))
    forged_metadata["parameters"]["n_estimators"] = 3
    forged = RankerModel(
        booster=trained.booster,
        feature_names=trained.feature_names,
        metadata=forged_metadata,
    )
    config = build_effective_experiment_config(
        default_experiment_config(), model_overrides={"n_estimators": 3}
    )

    with pytest.raises(ValueError, match="serialized booster parameter mismatch"):
        save_model_bundle(
            forged,
            tmp_path / "mismatched-booster",
            model_version="mismatched-booster",
            dataset_sha256="3" * 64,
            strict_pit_eligible=False,
            dataset_classification="synthetic_fixture",
            model_available_from="2026-04-06",
            experiment_config=config,
            experiment_config_sha256=experiment_config_sha256(config),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("objective", "regression"),
        ("metric", ["map"]),
        ("label_gain", [0, 1, 2, 3, 4]),
    ],
)
def test_serialized_booster_rejects_fixed_parameter_drift(field, value):
    from theme_sector_radar.ml.experiment import (
        build_effective_experiment_config,
        default_experiment_config,
        validate_booster_parameter_binding,
    )
    from theme_sector_radar.ml.ranker import train_lambdarank

    trained = train_lambdarank(
        _small_training_records(), n_estimators=2
    )
    trained.booster.params[field] = value
    config = build_effective_experiment_config(
        default_experiment_config(), model_overrides={"n_estimators": 2}
    )

    with pytest.raises(ValueError, match="serialized booster"):
        validate_booster_parameter_binding(trained.booster, config)
