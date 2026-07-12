import json

from theme_sector_radar.timing.factor_research import (
    INTRADAY_FACTOR_RESEARCH_SPECS,
    compare_frequency_factor_reports,
    evaluate_intraday_factor_research,
)
from theme_sector_radar.timing.factor_catalog import TIMING_FACTOR_CATEGORIES


def _sample(code, forward_return_pct, **factors):
    row = {"code": code, "forward_return_pct": forward_return_pct}
    row.update(factors)
    return row


def test_intraday_factor_research_covers_all_eight_categories_and_ranks_value():
    samples = [
        _sample(
            "600001",
            3.0,
            opening_drive_score=86,
            amount_acceleration_score=88,
            close_vs_vwap_score=82,
            late_high_near_close_score=85,
            sector_late_breadth_score=80,
            stock_vs_sector_intraday_alpha=78,
            high_to_close_drawdown_score=12,
            morning_strength_persist_score=84,
        ),
        _sample(
            "600002",
            2.2,
            opening_drive_score=80,
            amount_acceleration_score=75,
            close_vs_vwap_score=78,
            late_high_near_close_score=76,
            sector_late_breadth_score=74,
            stock_vs_sector_intraday_alpha=72,
            high_to_close_drawdown_score=18,
            morning_strength_persist_score=77,
        ),
        _sample(
            "600003",
            -1.0,
            opening_drive_score=35,
            amount_acceleration_score=30,
            close_vs_vwap_score=42,
            late_high_near_close_score=38,
            sector_late_breadth_score=44,
            stock_vs_sector_intraday_alpha=40,
            high_to_close_drawdown_score=68,
            morning_strength_persist_score=36,
        ),
        _sample(
            "600004",
            -1.8,
            opening_drive_score=28,
            amount_acceleration_score=24,
            close_vs_vwap_score=36,
            late_high_near_close_score=32,
            sector_late_breadth_score=30,
            stock_vs_sector_intraday_alpha=34,
            high_to_close_drawdown_score=80,
            morning_strength_persist_score=29,
        ),
    ]

    report = evaluate_intraday_factor_research(samples, min_labeled_samples=4)

    assert report["schema_version"] == "intraday_factor_research.v1"
    assert report["summary"]["category_count"] == 8
    assert set(report["categories"]) == set(TIMING_FACTOR_CATEGORIES)
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True

    valuable = {item["factor_id"] for item in report["valuable_factors"]}
    assert "opening_drive_score" in valuable
    assert "amount_acceleration_score" in valuable
    assert "high_to_close_drawdown_score" in valuable
    assert report["factors"]["high_to_close_drawdown_score"]["direction"] == "lower_is_better"


def test_intraday_factor_research_marks_unlabeled_factors_as_pending_validation():
    report = evaluate_intraday_factor_research(
        [{"code": "600001", "opening_drive_score": 80.0}],
        min_labeled_samples=3,
    )

    opening = report["factors"]["opening_drive_score"]
    assert opening["rating"] == "insufficient_labeled_samples"
    assert opening["labeled_sample_count"] == 0
    assert report["summary"]["valuable_factor_count"] == 0
    assert report["summary"]["pending_validation_factor_count"] > 0


def test_intraday_factor_research_scans_thresholds_by_factor_direction():
    samples = [
        _sample("600001", 3.0, open_to_midday_resilience_score=85, volume_without_price_progress_risk=10),
        _sample("600002", 2.0, open_to_midday_resilience_score=75, volume_without_price_progress_risk=20),
        _sample("600003", -1.0, open_to_midday_resilience_score=45, volume_without_price_progress_risk=70),
        _sample("600004", -2.0, open_to_midday_resilience_score=35, volume_without_price_progress_risk=80),
    ]

    report = evaluate_intraday_factor_research(samples, min_labeled_samples=4, thresholds=[50, 70])

    resilience = report["factors"]["open_to_midday_resilience_score"]
    risk = report["factors"]["volume_without_price_progress_risk"]

    assert resilience["threshold_results"][70]["selected_count"] == 2
    assert resilience["threshold_results"][70]["selected_avg_return_pct"] == 2.5
    assert resilience["threshold_results"][70]["selection_rule"] == "value >= threshold"
    assert risk["threshold_results"][50]["selected_count"] == 2
    assert risk["threshold_results"][50]["selected_avg_return_pct"] == 2.5
    assert risk["threshold_results"][50]["selection_rule"] == "value <= threshold"


def test_intraday_factor_research_specs_keep_each_factor_in_one_category():
    factor_ids = [spec.factor_id for spec in INTRADAY_FACTOR_RESEARCH_SPECS]

    assert len(factor_ids) == len(set(factor_ids))
    assert set(spec.category for spec in INTRADAY_FACTOR_RESEARCH_SPECS) == set(TIMING_FACTOR_CATEGORIES)


def test_price_momentum_research_has_at_least_eleven_factors():
    specs = [spec for spec in INTRADAY_FACTOR_RESEARCH_SPECS if spec.category == "price_momentum"]

    assert len(specs) >= 11
    assert {spec.factor_id for spec in specs} >= {
        "return_5m_strength_score",
        "return_15m_strength_score",
        "return_60m_strength_score",
        "positive_bar_ratio_score",
        "rolling_price_slope_score",
        "intraday_breakout_strength_score",
        "breakout_hold_score",
        "pullback_reclaim_momentum_score",
    }


def test_volume_money_flow_research_has_at_least_eleven_factors():
    specs = [spec for spec in INTRADAY_FACTOR_RESEARCH_SPECS if spec.category == "volume_money_flow"]

    assert len(specs) >= 11
    assert {spec.factor_id for spec in specs} >= {
        "early_amount_surge_score",
        "midday_amount_sustain_score",
        "late_amount_surge_score",
        "amount_trend_persistence_score",
        "volume_price_alignment_score",
        "breakout_volume_confirm_score",
        "pullback_volume_dryup_score",
        "late_money_flow_concentration_score",
    }


def test_remaining_timing_categories_have_at_least_ten_factors():
    expected = {
        "vwap_mean_price": {
            "open_vwap_reclaim_score",
            "midday_vwap_support_score",
            "vwap_distance_stability_score",
            "vwap_pullback_support_score",
            "vwap_breakout_confirm_score",
            "vwap_above_ratio_score",
        },
        "intraday_position": {
            "open_to_high_progress_score",
            "close_above_midrange_score",
            "low_reclaim_position_score",
            "late_range_expansion_score",
            "high_area_acceptance_score",
            "close_location_stability_score",
        },
        "sector_confirmation": {
            "sector_breadth_persistence_score",
            "sector_late_acceleration_score",
            "leader_sync_persistence_score",
            "sector_alpha_confirmation_score",
            "sector_breadth_quality_score",
            "theme_confirmation_composite_score",
        },
        "relative_strength": {
            "stock_intraday_rank_proxy_score",
            "stock_vs_market_intraday_alpha_score",
            "relative_late_strength_score",
            "relative_vwap_strength_score",
            "relative_breakout_leadership_score",
            "relative_resilience_score",
        },
        "risk_reversal": {
            "open_high_reversal_risk",
            "late_breakdown_risk",
            "failed_breakout_risk",
            "lower_low_sequence_risk",
            "volatility_expansion_reversal_risk",
            "weak_close_after_volume_risk",
        },
        "time_structure": {
            "first_hour_follow_through_score",
            "midday_hold_score",
            "afternoon_recovery_score",
            "late_session_acceleration_score",
            "session_consistency_score",
            "close_auction_strength_proxy_score",
        },
    }

    for category, factor_ids in expected.items():
        specs = [spec for spec in INTRADAY_FACTOR_RESEARCH_SPECS if spec.category == category]
        assert len(specs) >= 10, category
        assert {spec.factor_id for spec in specs} >= factor_ids

    risk_specs = {
        spec.factor_id: spec
        for spec in INTRADAY_FACTOR_RESEARCH_SPECS
        if spec.category == "risk_reversal"
    }
    for factor_id in expected["risk_reversal"]:
        assert risk_specs[factor_id].direction == "lower_is_better"


def test_frequency_validation_only_confirms_promoted_5m_price_momentum_factors():
    report_5m = {
        "factors": {
            "opening_drive_score": {
                "category": "price_momentum",
                "direction": "higher_is_better",
                "rating": "valuable",
            },
            "late_return_30m_score": {
                "category": "price_momentum",
                "direction": "higher_is_better",
                "rating": "weak",
            },
            "amount_acceleration_score": {
                "category": "volume_money_flow",
                "direction": "higher_is_better",
                "rating": "valuable",
            },
        }
    }
    report_1m = {
        "factors": {
            "opening_drive_score": {
                "direction": "higher_is_better",
                "rating": "watchlist",
                "adjusted_spread_pct": 0.4,
                "labeled_sample_count": 52,
            },
            "late_return_30m_score": {
                "direction": "higher_is_better",
                "rating": "valuable",
                "adjusted_spread_pct": 1.2,
                "labeled_sample_count": 52,
            },
        }
    }

    comparison = compare_frequency_factor_reports(report_5m, report_1m)

    assert comparison["eligible_factor_ids"] == ["opening_drive_score"]
    assert comparison["factors"]["opening_drive_score"]["confirmation_status"] == "1m_confirmed"
    assert "late_return_30m_score" not in comparison["factors"]


def test_frequency_validation_filters_requested_category():
    report_5m = {
        "factors": {
            "opening_drive_score": {
                "category": "price_momentum",
                "direction": "higher_is_better",
                "rating": "valuable",
            },
            "amount_acceleration_score": {
                "category": "volume_money_flow",
                "direction": "higher_is_better",
                "rating": "valuable",
            },
            "late_volume_efficiency_score": {
                "category": "volume_money_flow",
                "direction": "higher_is_better",
                "rating": "weak",
            },
        }
    }
    report_1m = {
        "factors": {
            "opening_drive_score": {
                "direction": "higher_is_better",
                "rating": "valuable",
                "adjusted_spread_pct": 1.2,
                "labeled_sample_count": 52,
            },
            "amount_acceleration_score": {
                "direction": "higher_is_better",
                "rating": "watchlist",
                "adjusted_spread_pct": 0.3,
                "labeled_sample_count": 52,
            },
        }
    }

    comparison = compare_frequency_factor_reports(report_5m, report_1m, category="volume_money_flow")

    assert comparison["category"] == "volume_money_flow"
    assert comparison["eligible_factor_ids"] == ["amount_acceleration_score"]
    assert comparison["factors"]["amount_acceleration_score"]["confirmation_status"] == "1m_confirmed"
    assert "opening_drive_score" not in comparison["factors"]
