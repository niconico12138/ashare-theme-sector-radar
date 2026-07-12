from theme_sector_radar.timing.factor_catalog import (
    TIMING_FACTOR_CATEGORIES,
    TIMING_FACTOR_REGISTRY,
    get_timing_factor_metadata,
    list_timing_factor_categories,
)


def test_timing_factor_catalog_defines_eight_intraday_categories():
    categories = list_timing_factor_categories()

    assert categories == [
        "price_momentum",
        "volume_money_flow",
        "vwap_mean_price",
        "intraday_position",
        "sector_confirmation",
        "relative_strength",
        "risk_reversal",
        "time_structure",
    ]
    assert set(TIMING_FACTOR_CATEGORIES) == set(categories)


def test_current_buy_timing_factors_are_mapped_to_categories():
    expected = {
        "intraday_momentum": "price_momentum",
        "amount_strength": "volume_money_flow",
        "sector_confirmation": "sector_confirmation",
        "vwap_position": "vwap_mean_price",
        "anti_chasing": "risk_reversal",
    }

    for factor_id, category in expected.items():
        metadata = get_timing_factor_metadata(factor_id)
        assert metadata is not None
        assert metadata.category == category
        assert metadata.enabled is True
        assert "buy_timing" in metadata.tags

    assert set(expected).issubset(TIMING_FACTOR_REGISTRY)
