import pytest

from theme_sector_radar.models import SectorSnapshot, SectorType
from theme_sector_radar.scoring.industry_three_layer_shadow import (
    calculate_industry_three_layer_shadow,
)


def _sector() -> SectorSnapshot:
    return SectorSnapshot(
        sector_id="BK0001",
        name="Test Industry",
        type=SectorType.INDUSTRY,
        price_change_pct=1.0,
        turnover=1_000_000_000,
        main_net_inflow=0.0,
        data_quality_score=80.0,
    )


def test_cross_section_strength_does_not_change_time_series_layer():
    common = {
        "recent_returns": [0.5] * 20,
        "daily_rank_percentiles": [0.8] * 10,
    }
    strong = calculate_industry_three_layer_shadow(
        _sector(),
        {
            **common,
            "relative_strength_percentiles": {5: 0.9, 10: 0.9, 20: 0.9},
        },
    )
    weak = calculate_industry_three_layer_shadow(
        _sector(),
        {
            **common,
            "relative_strength_percentiles": {5: 0.1, 10: 0.1, 20: 0.1},
        },
    )

    assert strong["time_series"]["score"] == weak["time_series"]["score"]
    assert strong["cross_section"]["score"] > weak["cross_section"]["score"]


def test_rank_momentum_rewards_an_improving_cross_sectional_path():
    common = {
        "recent_returns": [0.5] * 20,
        "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
    }
    improving = calculate_industry_three_layer_shadow(
        _sector(),
        {**common, "daily_rank_percentiles": [0.3, 0.4, 0.5, 0.7, 0.8]},
    )
    weakening = calculate_industry_three_layer_shadow(
        _sector(),
        {**common, "daily_rank_percentiles": [0.9, 0.8, 0.7, 0.6, 0.5]},
    )

    assert improving["rank_momentum"]["status"] == "ok"
    assert improving["rank_momentum"]["score"] > weakening["rank_momentum"]["score"]


def test_missing_rank_history_does_not_fabricate_direction_score():
    result = calculate_industry_three_layer_shadow(
        _sector(),
        {
            "recent_returns": [0.5] * 20,
            "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
            "daily_rank_percentiles": [0.8] * 4,
        },
    )

    assert result["rank_momentum"]["status"] == "unavailable"
    assert result["rank_momentum"]["score"] is None
    assert result["direction_score_shadow"] is None
    assert result["direction_state"] == "unavailable"


def test_partial_cross_section_does_not_fabricate_direction_score():
    result = calculate_industry_three_layer_shadow(
        _sector(),
        {
            "recent_returns": [0.5] * 20,
            "relative_strength_percentiles": {5: 0.8, 10: 0.8},
            "daily_rank_percentiles": [0.8] * 5,
        },
    )

    assert result["cross_section"]["status"] == "partial"
    assert result["direction_score_shadow"] is None
    assert result["direction_state"] == "unavailable"


def test_rank_endpoint_gap_does_not_get_compressed_into_five_day_momentum():
    result = calculate_industry_three_layer_shadow(
        _sector(),
        {
            "recent_returns": [0.5] * 20,
            "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
            "daily_rank_percentiles": [0.4, 0.5, None, 0.7, 0.8],
        },
    )

    assert result["rank_momentum"]["status"] == "unavailable"
    assert result["rank_momentum"]["missing_endpoint_count"] == 1
    assert result["direction_score_shadow"] is None


def test_direction_state_separates_acceleration_from_risk_observation():
    features = {
        "recent_returns": [0.5] * 20,
        "relative_strength_percentiles": {5: 0.9, 10: 0.9, 20: 0.9},
        "daily_rank_percentiles": [0.3, 0.4, 0.5, 0.7, 0.9],
    }
    emerging = calculate_industry_three_layer_shadow(_sector(), features)
    risk_observation = calculate_industry_three_layer_shadow(
        _sector(),
        features,
        risk_flags=["overheat"],
    )

    assert emerging["direction_state"] == "emerging_acceleration"
    assert risk_observation["direction_state"] == "risk_observation"
    assert emerging["direction_score_shadow"] == risk_observation["direction_score_shadow"]


@pytest.mark.parametrize(
    "features",
    [
        {
            "recent_returns": [0.5] * 19 + [float("nan")],
            "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
            "daily_rank_percentiles": [0.8] * 5,
        },
        {
            "recent_returns": [0.5] * 20,
            "relative_strength_percentiles": {5: float("inf")},
            "daily_rank_percentiles": [0.8] * 5,
        },
        {
            "recent_returns": [0.5] * 20,
            "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
            "daily_rank_percentiles": [0.8] * 4 + [float("-inf")],
        },
    ],
)
def test_non_finite_inputs_fail_closed_before_strict_json_output(features):
    with pytest.raises(ValueError, match="finite"):
        calculate_industry_three_layer_shadow(_sector(), features)


def test_finite_extreme_inputs_fail_closed_when_wealth_path_overflows():
    with pytest.raises(ValueError, match="finite"):
        calculate_industry_three_layer_shadow(
            _sector(),
            {
                "recent_returns": [1e308] * 20,
                "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
                "daily_rank_percentiles": [0.8] * 5,
            },
        )


def test_finite_but_untrusted_daily_returns_fail_closed():
    with pytest.raises(ValueError, match="trusted daily return range"):
        calculate_industry_three_layer_shadow(
            _sector(),
            {
                "recent_returns": [1e10] * 20,
                "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
                "daily_rank_percentiles": [0.8] * 5,
            },
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("relative_strength_percentiles", 2.0),
        ("daily_rank_percentiles", -3.0),
    ],
)
def test_out_of_range_percentiles_fail_closed(field, value):
    features = {
        "recent_returns": [0.5] * 20,
        "relative_strength_percentiles": {5: 0.8, 10: 0.8, 20: 0.8},
        "daily_rank_percentiles": [0.8] * 5,
    }
    if field == "relative_strength_percentiles":
        features[field][20] = value
    else:
        features[field][-1] = value

    with pytest.raises(ValueError, match=r"percentile.*\[0, 1\]"):
        calculate_industry_three_layer_shadow(_sector(), features)
