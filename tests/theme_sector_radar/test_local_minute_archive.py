from datetime import datetime
import zipfile

import pytest

from theme_sector_radar.data.local_minute_archive import (
    aggregate_complete_1m_session_to_5m,
    annotate_board_trigger_features,
    available_board_dates,
    build_stop_trigger_path_labels,
    detect_bar_interval_minutes,
    is_expected_next_bar,
    read_board_day_bars,
    read_board_day_bars_batch,
    read_board_name_code_map,
    read_stock_day_bars,
    scan_stock_daily_paths,
    scan_stock_daily_paths_batch,
    _trigger_snapshot,
    _stockdb_trading_elapsed,
    validate_complete_a_share_session,
)


def test_money_flow_deterioration_is_unknown_without_prior_amount_window():
    snapshot = _trigger_snapshot(
        [{"close": 9.5, "volume": 100.0, "amount": 950.0}],
        entry_price=10.0,
    )

    assert snapshot["recent_amount_ratio"] is None
    assert snapshot["money_flow_deterioration"] is None


def _complete_1m_session():
    times = ["0930"]
    times.extend(f"{hour:02d}{minute:02d}" for hour in (9, 10, 11) for minute in range(60) if (hour, minute) >= (9, 31) and (hour, minute) <= (11, 30))
    times.extend(f"{hour:02d}{minute:02d}" for hour in (13, 14, 15) for minute in range(60) if (hour, minute) >= (13, 1) and (hour, minute) <= (15, 0))
    return [
        {
            "date": f"20260702{value}00",
            "open": 10.0 + index / 100.0,
            "high": 10.1 + index / 100.0,
            "low": 9.9 + index / 100.0,
            "close": 10.05 + index / 100.0,
            "volume": 1.0,
            "amount": 10.0,
        }
        for index, value in enumerate(times)
    ]


def _stockdb_start_time_session():
    times = [f"{hour:02d}{minute:02d}" for hour in (9, 10, 11) for minute in range(60)]
    times = [value for value in times if "0930" <= value <= "1129"]
    times.extend(
        f"{hour:02d}{minute:02d}"
        for hour in (13, 14, 15)
        for minute in range(60)
        if "1300" <= f"{hour:02d}{minute:02d}" <= "1500"
    )
    return [
        {
            "date": f"20260702{value}00",
            "open": 10.0 + index / 100.0,
            "high": 10.1 + index / 100.0,
            "low": 9.9 + index / 100.0,
            "close": 10.05 + index / 100.0,
            "volume": 1.0,
            "amount": 10.0,
        }
        for index, value in enumerate(times)
    ]


def test_complete_session_validation_and_5m_aggregation_preserve_true_open():
    bars = _complete_1m_session()

    assert len(bars) == 241
    assert validate_complete_a_share_session(bars, interval_minutes=1) is True

    aggregated = aggregate_complete_1m_session_to_5m(bars)

    assert len(aggregated) == 48
    assert str(aggregated[0]["date"]) == "20260702093500"
    assert aggregated[0]["open"] == bars[0]["open"]
    assert aggregated[0]["close"] == bars[5]["close"]
    assert aggregated[0]["volume"] == 6.0
    assert validate_complete_a_share_session(aggregated, interval_minutes=5) is True


def test_stockdb_start_time_session_is_complete_and_aggregates_without_crossing_lunch():
    bars = _stockdb_start_time_session()

    assert len(bars) == 241
    assert validate_complete_a_share_session(bars, interval_minutes=1) is True

    aggregated = aggregate_complete_1m_session_to_5m(bars)

    assert len(aggregated) == 48
    assert str(aggregated[0]["date"]) == "20260702093500"
    assert aggregated[0]["open"] == bars[0]["open"]
    assert aggregated[0]["close"] == bars[5]["close"]
    assert str(aggregated[23]["date"]) == "20260702113000"
    assert str(aggregated[24]["date"]) == "20260702130500"
    assert str(aggregated[-1]["date"]) == "20260702150000"
    assert validate_complete_a_share_session(aggregated, interval_minutes=5) is True


def test_stockdb_elapsed_clock_has_unique_lunch_boundary_and_5m_groups_do_not_cross_it():
    assert _stockdb_trading_elapsed(datetime(2026, 7, 2, 11, 29)) == 119
    assert _stockdb_trading_elapsed(datetime(2026, 7, 2, 13, 0)) == 120
    assert _stockdb_trading_elapsed(datetime(2026, 7, 2, 13, 1)) == 121

    bars = _stockdb_start_time_session()
    aggregated = aggregate_complete_1m_session_to_5m(bars)

    assert aggregated[23]["close"] == bars[119]["close"]
    assert aggregated[24]["open"] == bars[120]["open"]


def test_expected_next_bar_accepts_stockdb_start_time_lunch_boundary():
    previous = {"time": "20260702112900"}
    current = {"time": "20260702130000"}

    assert is_expected_next_bar(previous, current, 1) is True


def test_complete_session_validation_rejects_internal_gap():
    bars = _complete_1m_session()
    bars.pop(2)

    assert validate_complete_a_share_session(bars, interval_minutes=1) is False
    with pytest.raises(ValueError, match="complete"):
        aggregate_complete_1m_session_to_5m(bars)


def test_complete_session_validation_rejects_unordered_input():
    bars = list(reversed(_complete_1m_session()))

    assert validate_complete_a_share_session(bars, interval_minutes=1) is False
    with pytest.raises(ValueError, match="complete"):
        aggregate_complete_1m_session_to_5m(bars)


@pytest.mark.parametrize("field", ["volume", "amount"])
def test_complete_session_validation_rejects_missing_turnover_fields(field):
    bars = _complete_1m_session()
    bars[10].pop(field)

    assert validate_complete_a_share_session(bars, interval_minutes=1) is False


def test_complete_session_validation_rejects_nonfinite_or_incoherent_ohlc():
    nonfinite = _complete_1m_session()
    nonfinite[10]["amount"] = float("nan")
    incoherent = _complete_1m_session()
    incoherent[10]["high"] = incoherent[10]["low"] - 1.0

    assert validate_complete_a_share_session(nonfinite, interval_minutes=1) is False
    assert validate_complete_a_share_session(incoherent, interval_minutes=1) is False


def test_stop_trigger_path_labels_exclude_the_trigger_bar_from_forward_metrics():
    bars = [
        {"time": "20240102093000", "open": 10.0, "close": 10.0, "high": 10.0, "low": 10.0, "volume": 100.0, "amount": 1000.0},
        {"time": "20240102093100", "open": 10.0, "close": 9.6, "high": 10.0, "low": 9.0, "volume": 200.0, "amount": 1960.0},
        {"time": "20240102093200", "open": 9.7, "close": 9.8, "high": 9.9, "low": 9.6, "volume": 100.0, "amount": 980.0},
        {"time": "20240102093300", "open": 9.8, "close": 9.9, "high": 10.0, "low": 9.7, "volume": 100.0, "amount": 990.0},
        {"time": "20240102093400", "open": 9.9, "close": 10.1, "high": 10.2, "low": 9.8, "volume": 100.0, "amount": 1010.0},
    ]

    result = build_stop_trigger_path_labels(bars, trigger_drawdown_pct=-3.0, horizons=(2, 3), bar_interval_minutes=1)

    assert result["triggered"] is True
    assert result["trigger_index"] == 1
    assert result["trigger_time"] == "20240102093100"
    assert result["decision_model"] == "trigger_bar_close_confirmed_next_bar_open_fill"
    assert result["next_bar_fill_return_pct"] == -3.0
    assert result["horizons"]["2"]["end_return_from_entry_pct"] == -1.0
    assert result["horizons"]["2"]["post_trigger_mae_pct"] == -4.0
    assert result["horizons"]["2"]["post_trigger_mfe_pct"] == 0.0
    assert result["horizons"]["2"]["recovered_entry"] is True
    assert result["horizons"]["3"]["end_return_from_entry_pct"] == 1.0


def test_stop_trigger_path_keeps_missing_forward_prices_unlabeled():
    bars = [
        {"time": "20240102093000", "close": 10.0, "high": 10.0, "low": 10.0},
        {"time": "20240102093100", "close": 9.6, "high": 9.9, "low": 9.5},
        {"time": "20240102093200", "open": 9.7, "close": None, "high": None, "low": None},
        {"time": "20240102093300", "open": None, "close": None, "high": None, "low": None},
    ]

    result = build_stop_trigger_path_labels(bars, horizons=(2,), bar_interval_minutes=1)

    assert result["horizons"]["2"]["complete"] is False
    assert result["horizons"]["2"]["recovered_entry"] is None


def test_stop_trigger_path_does_not_use_close_when_next_bar_open_is_missing():
    bars = [
        {"time": "20240102093000", "open": 10.0, "close": 10.0, "high": 10.0, "low": 10.0},
        {"time": "20240102093100", "open": 10.0, "close": 9.6, "high": 9.9, "low": 9.5},
        {"time": "20240102093200", "open": None, "close": 9.8, "high": 9.9, "low": 9.6},
    ]

    result = build_stop_trigger_path_labels(bars, horizons=(1,), bar_interval_minutes=1)

    assert result["next_bar_fill_available"] is False
    assert result["next_bar_fill_return_pct"] is None


def test_stop_path_accepts_date_timestamp_and_rejects_partial_horizon_prices():
    bars = [
        {"date": 20260714093000, "open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0},
        {"date": 20260714093100, "open": 10.0, "high": 10.0, "low": 9.5, "close": 9.6},
        {"date": 20260714093200, "open": 9.6, "high": 9.7, "low": 9.4, "close": 9.5},
        {"date": 20260714093300, "open": 9.5, "high": None, "low": 9.3, "close": 9.4},
    ]

    result = build_stop_trigger_path_labels(
        bars,
        entry_price=10.0,
        horizons=(2,),
        bar_interval_minutes=1,
    )

    assert result["trigger_time"] == "20260714093100"
    assert result["next_bar_fill_available"] is True
    assert result["horizons"]["2"]["observed_bars"] == 2
    assert result["horizons"]["2"]["complete"] is False
    assert result["horizons"]["2"]["post_trigger_mae_pct"] is None


def test_stop_trigger_requires_trigger_bar_close_not_intrabar_low():
    bars = [
        {"time": "20240102093000", "open": 10.0, "close": 10.0, "high": 10.0, "low": 10.0},
        {"time": "20240102093100", "open": 10.0, "close": 9.8, "high": 10.0, "low": 9.0},
        {"time": "20240102093200", "open": 9.8, "close": 9.9, "high": 10.0, "low": 9.7},
    ]

    result = build_stop_trigger_path_labels(bars, bar_interval_minutes=1)

    assert result["triggered"] is False


def test_missing_immediate_bar_keeps_fill_and_horizon_incomplete():
    bars = [
        {"time": "20240102093000", "open": 10.0, "close": 10.0, "high": 10.0, "low": 10.0},
        {"time": "20240102093100", "open": 10.0, "close": 9.6, "high": 10.0, "low": 9.5},
        {"time": "20240102093300", "open": 9.5, "close": 9.4, "high": 9.6, "low": 9.3},
        {"time": "20240102093400", "open": 9.4, "close": 9.3, "high": 9.5, "low": 9.2},
    ]

    result = build_stop_trigger_path_labels(bars, horizons=(2,), bar_interval_minutes=1)

    assert result["triggered"] is True
    assert result["next_bar_fill_available"] is False
    assert result["horizons"]["2"]["complete"] is False
    assert result["horizons"]["2"]["observed_bars"] == 0


def test_detect_bar_interval_uses_dominant_contiguous_cadence():
    one_minute = [
        {"time": "20240102093000"},
        {"time": "20240102093100"},
        {"time": "20240102093300"},
        {"time": "20240102093400"},
    ]
    five_minute = [
        {"time": "20240102093500"},
        {"time": "20240102094000"},
        {"time": "20240102094500"},
    ]

    assert detect_bar_interval_minutes(one_minute) == 1
    assert detect_bar_interval_minutes(five_minute) == 5


def test_local_minute_archive_reads_stock_and_board_bars_without_extracting(tmp_path):
    stock_zip = tmp_path / "2024_1min.zip"
    with zipfile.ZipFile(stock_zip, "w") as archive:
        archive.writestr(
            "sz000001_2024.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024-01-02 09:30:00,sz000001,样本,10,10.1,10.2,9.9,100,1000\n",
        )
    board_zip = tmp_path / "20240102_1min.zip"
    with zipfile.ZipFile(board_zip, "w") as archive:
        archive.writestr(
            "880201.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024/01/02 09:31,880201,板块,100,101,102,99,200,2000\n",
        )

    stock = read_stock_day_bars(stock_zip, "000001", "2024-01-02")
    board = read_board_day_bars(board_zip, "880201")

    assert stock == [{"time": "20240102093000", "open": 10.0, "close": 10.1, "high": 10.2, "low": 9.9, "volume": 100.0, "amount": 1000.0}]
    assert board[0]["time"] == "20240102093100"
    assert board[0]["close"] == 101.0
    board_batch = read_board_day_bars_batch(board_zip, ["880201", "889999"])
    assert len(board_batch["880201"]) == 1
    assert board_batch["889999"] == []
    assert read_board_name_code_map(board_zip) == {"板块": "880201"}


def test_local_minute_archive_lists_board_dates_in_range(tmp_path):
    for name in ("20240102_1min.zip", "20240103_1min.zip", "20240201_1min.zip"):
        (tmp_path / name).write_bytes(b"")

    assert available_board_dates(tmp_path, "2024-01-02", "2024-01-31") == ["2024-01-02", "2024-01-03"]


def test_local_minute_archive_scans_daily_drawdown_and_next_day_return(tmp_path):
    archive_path = tmp_path / "2024_1min.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "sz000001_2024.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024-01-02 09:30:00,sz000001,样本,10,10,10,10,1,1\n"
            "2024-01-02 15:00:00,sz000001,样本,9.6,9.7,9.8,9.5,1,1\n"
            "2024-01-03 09:30:00,sz000001,样本,9.2,9.2,9.2,9.2,1,1\n"
            "2024-01-03 15:00:00,sz000001,样本,9.1,9.1,9.2,9.0,1,1\n",
        )

    rows = scan_stock_daily_paths(archive_path, "000001")

    assert rows[0]["mae_pct"] == -5.0
    assert rows[0]["mfe_pct"] == 0.0
    assert rows[0]["close_return_pct"] == -3.0
    assert rows[0]["close_position_pct"] == 40.0
    assert rows[0]["close_vs_vwap_pct"] == -1.5228
    assert rows[0]["late_amount_ratio"] == 1.0
    assert rows[0]["next_day_return_pct"] == -6.1856
    assert rows[0]["fixed_stop_path"]["triggered"] is True
    assert rows[0]["fixed_stop_path"]["trigger_time"] == "20240102150000"

    batch = scan_stock_daily_paths_batch(archive_path, ["000001", "999999"])
    assert len(batch["000001"]) == 2
    assert batch["999999"] == []


def test_batch_scan_builds_trigger_time_relative_and_money_flow_features(tmp_path):
    archive_path = tmp_path / "2024_1min.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "sz000001_2024.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024-01-02 09:30:00,sz000001,a,10,10,10,10,100,1000\n"
            "2024-01-02 09:31:00,sz000001,a,10,9.6,9.7,9.5,200,2000\n",
        )
        archive.writestr(
            "sz000002_2024.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024-01-02 09:30:00,sz000002,b,10,10,10,10,100,1000\n"
            "2024-01-02 09:31:00,sz000002,b,10,10,10.1,9.9,100,1000\n",
        )

    batch = scan_stock_daily_paths_batch(archive_path, ["000001", "000002"])
    row = batch["000001"][0]

    assert row["fixed_stop_path"]["triggered"] is True
    assert row["trigger_factor_features"]["relative_weakness"] is True
    assert row["trigger_factor_features"]["relative_vs_market_proxy_pct"] == -4.0
    assert row["trigger_factor_features"]["money_flow_deterioration"] is True
    assert row["trigger_factor_features"]["board_synchronous_weakness"] is None


def test_board_trigger_annotation_uses_only_board_bars_visible_at_trigger():
    batch = {
        "000001": [
            {
                "date": "2024-01-02",
                "fixed_stop_path": {"triggered": True, "trigger_time": "20240102093200"},
                "trigger_factor_features": {},
            }
        ]
    }
    board_bars = {
        "2024-01-02": {
            "880001": [
                {"time": "20240102093100", "open": 100.0, "close": 99.5},
                {"time": "20240102093200", "open": 99.5, "close": 98.5},
                {"time": "20240102093300", "open": 98.5, "close": 101.0},
            ]
        }
    }

    annotated = annotate_board_trigger_features(batch, board_bars, {"000001": ["880001"]})
    features = annotated["000001"][0]["trigger_factor_features"]

    assert features["board_synchronous_weakness"] is True
    assert features["board_return_at_trigger_pct"] == -1.5
    assert features["matched_board_count"] == 1
