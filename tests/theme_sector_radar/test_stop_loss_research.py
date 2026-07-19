import pytest

from theme_sector_radar.timing.stop_loss_research import (
    build_metric_negative_sample,
    build_stop_loss_negative_sample,
    validate_stop_trigger_factor_paths,
)


def _trigger_record(day, code, *, mae, mfe, end_return, recovered, factors, next_day=None):
    return {
        "date": day,
        "code": code,
        "next_day_return_pct": next_day,
        "fixed_stop_path": {
            "triggered": True,
            "next_bar_fill_available": True,
            "next_bar_fill_return_pct": -3.2,
            "horizons": {
                "5": {
                    "complete": True,
                    "end_return_from_entry_pct": end_return,
                    "post_trigger_mae_pct": mae,
                    "post_trigger_mfe_pct": mfe,
                    "recovered_entry": recovered,
                }
            },
        },
        "trigger_factor_features": factors,
    }


def test_stop_factor_validation_uses_post_trigger_path_as_primary_label():
    rows = [
        _trigger_record(
            "2024-01-02",
            "000001",
            mae=-7.0,
            mfe=-1.0,
            end_return=-6.0,
            recovered=False,
            factors={"relative_weakness": True, "money_flow_deterioration": True, "board_synchronous_weakness": False},
            next_day=-6.0,
        ),
        _trigger_record(
            "2024-01-03",
            "000002",
            mae=-3.5,
            mfe=2.0,
            end_return=1.0,
            recovered=True,
            factors={"relative_weakness": False, "money_flow_deterioration": False, "board_synchronous_weakness": True},
            next_day=2.0,
        ),
    ]

    report = validate_stop_trigger_factor_paths(rows, horizons=(5,), fold_count=2, min_signals=1)

    assert report["baseline"]["by_horizon"]["5"]["signal_count"] == 2
    assert report["baseline"]["by_horizon"]["5"]["next_bar_fill_rate"] == 1.0
    relative = report["factors"]["relative_weakness"]["by_horizon"]["5"]
    assert relative["signal_count"] == 1
    assert relative["avg_post_trigger_mae_pct"] == -7.0
    assert relative["continuation_tail_rate"] == 1.0
    assert relative["recovery_rate"] == 0.0
    assert relative["next_day_tail_rate_auxiliary"] == 1.0
    assert report["factors"]["relative_weakness"]["concentration"]["top_code_share"] == 1.0
    board = report["factors"]["board_synchronous_weakness"]["by_horizon"]["5"]
    assert board["recovery_rate"] == 1.0
    assert report["factors"]["board_synchronous_weakness"]["eligible_baseline"]["by_horizon"]["5"]["signal_count"] == 2
    assert report["factors"]["board_synchronous_weakness"]["signal_rate_within_eligible"] == 0.5
    assert report["paper_trading_only"] is True


def test_stop_fill_rate_uses_all_triggered_records_not_complete_horizon_subset():
    rows = [
        _trigger_record(
            "2024-01-02",
            "000001",
            mae=-5.0,
            mfe=-2.0,
            end_return=-4.0,
            recovered=False,
            factors={"relative_weakness": True},
        ),
        {
            **_trigger_record(
                "2024-01-03",
                "000002",
                mae=-5.0,
                mfe=-2.0,
                end_return=-4.0,
                recovered=False,
                factors={"relative_weakness": True},
            ),
            "fixed_stop_path": {
                "triggered": True,
                "next_bar_fill_available": False,
                "next_bar_fill_return_pct": None,
                "horizons": {"5": {"complete": False}},
            },
        },
    ]

    report = validate_stop_trigger_factor_paths(rows, horizons=(5,), min_signals=1)
    summary = report["baseline"]["by_horizon"]["5"]

    assert summary["next_bar_fill_rate"] == 0.5
    assert summary["horizon_complete_rate"] == 0.5


@pytest.mark.parametrize(
    ("mutate", "expected_signal_count", "expected_fill_rate", "expected_complete_count"),
    [
        (
            lambda row: row["fixed_stop_path"].update(triggered="yes"),
            0,
            None,
            0,
        ),
        (
            lambda row: row["fixed_stop_path"].update(next_bar_fill_available="yes"),
            1,
            0.0,
            1,
        ),
        (
            lambda row: row["fixed_stop_path"]["horizons"]["5"].update(complete="yes"),
            1,
            1.0,
            0,
        ),
    ],
)
def test_stop_factor_validation_rejects_truthy_non_boolean_path_flags(
    mutate,
    expected_signal_count,
    expected_fill_rate,
    expected_complete_count,
):
    row = _trigger_record(
        "2024-01-02",
        "000001",
        mae=-5.0,
        mfe=-2.0,
        end_return=-4.0,
        recovered=False,
        factors={"relative_weakness": True},
    )
    mutate(row)

    report = validate_stop_trigger_factor_paths([row], horizons=(5,), min_signals=1)
    summary = report["baseline"]["by_horizon"]["5"]

    assert summary["signal_count"] == expected_signal_count
    assert summary["next_bar_fill_rate"] == expected_fill_rate
    assert summary["complete_path_count"] == expected_complete_count


def test_negative_sample_labels_drawdown_tail_and_same_date_control():
    rows = [
        {
            "_sample_date": "2026-07-01",
            "code": "600001",
            "boards": ["gas"],
            "intraday_bars": [
                {"time": "09:30", "price": 10.0, "low": 9.9},
                {"time": "10:00", "price": 9.6, "low": 9.5},
            ],
            "forward_return_pct": -6.0,
            "relative_resilience_score": 30.0,
            "late_breakdown_risk": 60.0,
        },
        {
            "_sample_date": "2026-07-01",
            "code": "600002",
            "boards": ["gas"],
            "intraday_bars": [
                {"time": "09:30", "price": 10.0, "low": 9.9},
                {"time": "10:00", "price": 10.2, "low": 10.0},
            ],
            "forward_return_pct": 1.0,
            "relative_resilience_score": 70.0,
            "late_breakdown_risk": 5.0,
        },
    ]

    report = build_stop_loss_negative_sample(rows)

    assert report["summary"]["negative_event_count"] == 1
    negative = report["negative_events"][0]
    assert set(negative["negative_labels"]) == {
        "intraday_drawdown",
        "close_structure_break",
        "next_day_tail_loss",
    }
    assert negative["control_code"] == "600002"
    assert negative["factor_evidence"]["relative_weakness"] is True
    assert negative["factor_evidence"]["money_flow_deterioration"] is True


def test_metric_negative_sample_uses_strict_breakdown_and_same_day_control():
    rows = [
        {"date": "2024-01-02", "code": "000001", "mae_pct": -4.0, "close_return_pct": -2.0, "close_position_pct": 20.0, "next_day_return_pct": -6.0, "close_vs_vwap_pct": -1.5, "late_amount_ratio": 1.4},
        {"date": "2024-01-02", "code": "000002", "mae_pct": -1.0, "close_return_pct": 1.0, "close_position_pct": 70.0, "next_day_return_pct": 2.0, "close_vs_vwap_pct": 0.5, "late_amount_ratio": 0.8},
        {"date": "2024-01-02", "code": "000003", "mae_pct": -1.0, "close_return_pct": -0.5, "close_position_pct": 60.0, "next_day_return_pct": 1.0},
    ]

    report = build_metric_negative_sample(rows)

    assert report["summary"]["negative_event_count"] == 1
    assert report["events"][0]["control_code"] == "000002"
    assert set(report["events"][0]["negative_labels"]) == {"intraday_drawdown", "close_structure_break", "next_day_tail_loss"}
    assert report["events"][0]["factor_features"]["relative_vs_control_pct"] == -3.0
    assert report["events"][0]["factor_features"]["money_flow_deterioration"] is True
