from __future__ import annotations


def test_iteration_suite_declares_ten_distinct_paper_only_specs():
    from theme_sector_radar.ml.historical_iteration import (
        ITERATION_COUNT,
        iteration_specs,
    )

    specs = iteration_specs()
    assert len(specs) == ITERATION_COUNT == 10
    assert [item["iteration"] for item in specs] == list(range(1, 11))
    assert len({item["id"] for item in specs}) == 10


def test_iteration_suite_rejects_protected_feature_names():
    import pytest

    from theme_sector_radar.ml.historical_iteration import _assert_safe_feature_names

    with pytest.raises(ValueError, match="forbidden feature"):
        _assert_safe_feature_names(("contraction_score", "selection_score"))


def test_datewise_shuffle_preserves_identities_and_feature_order():
    from theme_sector_radar.ml.historical_factor_ablation import BASE_FEATURE_NAMES
    from theme_sector_radar.ml.historical_iteration import _technical_views

    first_features = {name: 1.0 for name in BASE_FEATURE_NAMES}
    second_features = {name: 2.0 for name in BASE_FEATURE_NAMES}
    rows = [
        {
            "as_of_date": "2026-01-01",
            "stock_code": "000001",
            "features": first_features,
        },
        {
            "as_of_date": "2026-01-01",
            "stock_code": "000002",
            "features": second_features,
        },
    ]
    dataset = {
        "records": [dict(row, training_label=0.1, training_label_end_date="2026-01-06") for row in rows],
        "feature_universe_records": rows,
    }
    contexts = {
        ("2026-01-01", "000001"): {"regime": "unknown"},
        ("2026-01-01", "000002"): {"regime": "unknown"},
    }
    records, universe = _technical_views(
        dataset,
        contexts,
        feature_names=BASE_FEATURE_NAMES,
        shuffle=True,
    )
    assert [(row["as_of_date"], row["stock_code"]) for row in records] == [
        ("2026-01-01", "000001"),
        ("2026-01-01", "000002"),
    ]
    assert set(universe[0]["features"]) == set(BASE_FEATURE_NAMES)
    assert set(universe[1]["features"]) == set(BASE_FEATURE_NAMES)
    assert set(universe[0]["features"].values()) == {2.0}
    assert set(universe[1]["features"].values()) == {1.0}


def test_bootstrap_is_deterministic():
    from theme_sector_radar.ml.historical_iteration import _bootstrap_report

    baseline = {
        "groups": {
            "A_technical_baseline": {
                "daily_metrics": {
                    "1": [
                        {"lift_vs_universe": -0.1},
                        {"lift_vs_universe": 0.2},
                    ]
                },
                "metrics": {"1": {"lift_vs_universe": 0.05}},
            }
        }
    }
    assert _bootstrap_report(baseline, replicates=20, seed=7) == _bootstrap_report(
        baseline, replicates=20, seed=7
    )
