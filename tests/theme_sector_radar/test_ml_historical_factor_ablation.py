from __future__ import annotations

from pathlib import Path


def test_ablation_missing_values_have_explicit_indicators():
    from theme_sector_radar.ml.historical_factor_ablation import (
        FEATURE_GROUPS,
        _empty_context,
        _features,
    )
    from theme_sector_radar.ml.historical_research import (
        HISTORICAL_FEATURE_PROFILES,
    )

    row = {"features": {name: 1.0 for name in HISTORICAL_FEATURE_PROFILES["stability_core_v1"]}}
    context = _empty_context()
    features = _features(row, context, "D_direction_linkage_interaction")

    assert features["direction_score"] == 0.0
    assert features["direction_score_missing"] == 1.0
    assert features["linkage_score"] == 0.0
    assert features["linkage_score_missing"] == 1.0
    assert features["direction_x_linkage_score"] == 0.0
    assert features["direction_x_linkage_score_missing"] == 1.0
    assert tuple(features) == FEATURE_GROUPS["D_direction_linkage_interaction"]


def test_ablation_feature_contract_excludes_forbidden_score_inputs():
    from theme_sector_radar.ml.historical_factor_ablation import FEATURE_GROUPS

    forbidden = {
        "quant_score",
        "final_score",
        "v2_score",
        "selection_score",
        "selection_score_adjusted",
        "relevance_score",
        "legacy_relevance_score",
    }
    assert not forbidden.intersection(
        {name for names in FEATURE_GROUPS.values() for name in names}
    )


def test_ablation_run_has_four_groups_and_common_fold_contract(tmp_path: Path):
    from tests.theme_sector_radar.test_ml_stock_historical_research import (
        _write_fixture,
    )
    from theme_sector_radar.ml.historical_factor_ablation import (
        run_historical_factor_ablation,
        validate_historical_factor_ablation_report,
    )
    from theme_sector_radar.ml.historical_research import (
        build_historical_research_dataset,
    )

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    dataset = build_historical_research_dataset(
        candidate_root, forward_root, calendar_path
    )
    report = run_historical_factor_ablation(
        dataset,
        min_train_dates=2,
        test_dates=2,
        purge_dates=5,
        n_estimators=2,
    )
    validate_historical_factor_ablation_report(report)

    assert set(report["groups"]) == {
        "A_technical_baseline",
        "B_plus_direction",
        "C_plus_linkage_v2",
        "D_direction_linkage_interaction",
    }
    folds = {
        (item["test_start"], item["test_end"], item["test_date_count"])
        for result in report["groups"].values()
        for item in result["prediction"]["folds"]
    }
    assert folds
    for result in report["groups"].values():
        assert result["prediction"]["min_train_dates"] == 2
        assert result["prediction"]["purge_dates"] == 5
        assert {
            (item["test_start"], item["test_end"], item["test_date_count"])
            for item in result["prediction"]["folds"]
        } == folds
        assert result["prediction"]["strict_pit_eligible"] is False
        assert result["prediction"]["promotion_allowed"] is False
        assert result["prediction"]["live_trading_allowed"] is False
    assert report["strict_pit_eligible"] is False
    assert report["formal_predictor_compatible"] is False
