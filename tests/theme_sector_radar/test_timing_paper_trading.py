from theme_sector_radar.timing.paper_trading import _next_bar_fill_price, build_timing_paper_trading_records


def _candidate(code, boards=None, **overrides):
    row = {
        "code": code,
        "name": f"stock-{code}",
        "boards": boards or ["gas"],
        "open_to_midday_resilience_score": 70,
        "midday_hold_score": 70,
        "vwap_above_ratio_score": 70,
        "late_high_near_close_score": 90,
        "high_to_close_drawdown_score": 12,
        "lower_low_sequence_risk": 20,
        "stock_vs_market_intraday_alpha_score": 75,
        "relative_resilience_score": 75,
        "optimized_watch_score": 80,
        "late_amount_surge_score": 40,
        "failed_breakout_risk": 20,
        "execution_tradeability_score": 60,
        "late_breakdown_risk": 0,
    }
    row.update(overrides)
    return row


def _bars():
    times = ["0930"]
    times.extend(f"{hour:02d}{minute:02d}" for hour in (9, 10, 11) for minute in range(60) if (hour, minute) >= (9, 31) and (hour, minute) <= (11, 30))
    times.extend(f"{hour:02d}{minute:02d}" for hour in (13, 14, 15) for minute in range(60) if (hour, minute) >= (13, 1) and (hour, minute) <= (15, 0))
    rows = [
        {
            "time": f"20260714{value}00",
            "open": 10.0,
            "high": 10.0,
            "low": 10.0,
            "close": 10.0,
            "price": 10.0,
            "vwap": 10.0,
            "volume": 100.0,
            "amount": 1000.0,
        }
        for value in times
    ]
    updates = {
        "20260714100000": {"open": 10.1, "high": 10.8, "low": 10.1, "close": 10.6, "price": 10.6},
        "20260714143000": {"open": 10.4, "high": 10.7, "low": 9.6, "close": 9.8, "price": 9.8},
        "20260714150000": {"open": 9.8, "high": 10.0, "low": 9.7, "close": 9.9, "price": 9.9},
    }
    for row in rows:
        row.update(updates.get(row["time"], {}))
    return rows


def test_paper_trading_records_include_v31_v32_risk_tags_and_path_stats():
    candidates = [
        _candidate("600001"),
        _candidate("600002"),
        _candidate("600003", boards=["robot"], lower_low_sequence_risk=40),
    ]

    report = build_timing_paper_trading_records(
        candidates,
        minute_bars_by_code={"600001": _bars(), "600002": _bars(), "600003": _bars()},
        entry_date_by_code={"600001": "2026-07-14", "600002": "2026-07-14", "600003": "2026-07-14"},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard", "v32_expanded_defensive_breakdown_guard"],
        concentration_threshold=2,
        bar_interval="1m",
    )

    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True
    assert report["does_not_modify_official_scores"] is True
    assert report["summary"]["record_count"] == 4
    assert report["summary"]["labeled_record_count"] == 4
    assert report["summary"]["causal_entry_valid_count"] == 4
    assert report["summary"]["version_counts"]["v31_expanded_balanced_tail_guard"] == 2
    assert report["summary"]["version_counts"]["v32_expanded_defensive_breakdown_guard"] == 2

    first = report["records"][0]
    assert first["timing_version_id"] == "v31_expanded_balanced_tail_guard"
    assert first["paper_action_state"] == "watch_only"
    assert first["forward_return_pct"] == -1.0
    assert "same_day_board_concentration" in first["paper_risk_tags"]
    assert first["path_stats"]["max_favorable_excursion_pct"] == 8.0
    assert first["path_stats"]["max_adverse_excursion_pct"] == -4.0
    assert first["path_stats"]["close_return_pct"] == -1.0
    assert first["exit_research"]["stop_loss_hit_3pct"] is True
    assert first["exit_research"]["take_profit_hit_5pct"] is True
    assert first["exit_research"]["paper_research_only"] is True
    assert first["factor_exit_triggers"]["strategies"]["exit_v1_fixed"]["triggered"] is True
    assert first["factor_exit_triggers"]["strategies"]["exit_v1_fixed"]["trigger_type"] == "take_profit"
    assert first["factor_exit_triggers"]["paper_trading_only"] is True


def test_paper_concentration_deduplicates_versions_of_same_entry():
    report = build_timing_paper_trading_records(
        [_candidate("600001")],
        minute_bars_by_code={"600001": _bars()},
        entry_date_by_code={"600001": "2026-07-14"},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard", "v32_expanded_defensive_breakdown_guard"],
        concentration_threshold=2,
        bar_interval="1m",
    )

    assert report["summary"]["record_count"] == 2
    assert all("same_day_board_concentration" not in record["paper_risk_tags"] for record in report["records"])
    assert all(record["concentration_snapshot"]["max_same_day_board_trigger_count"] == 1 for record in report["records"])


def test_paper_trading_records_separate_selection_label_from_causal_hold_return():
    report = build_timing_paper_trading_records(
        [_candidate("600001", forward_return_pct=-6.25)],
        minute_bars_by_code={"600001": _bars()},
        entry_date_by_code={"600001": "2026-07-14"},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        bar_interval="1m",
    )

    assert report["summary"]["labeled_record_count"] == 1
    assert report["records"][0]["selection_forward_return_pct"] == -6.25
    assert report["records"][0]["forward_return_pct"] == -1.0


def test_paper_trading_records_reject_incomplete_next_session_path():
    report = build_timing_paper_trading_records(
        [_candidate("600001", forward_return_pct=5.0)],
        minute_bars_by_code={"600001": _bars()[:10]},
        entry_date_by_code={"600001": "2026-07-14"},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        bar_interval="1m",
    )

    record = report["records"][0]
    assert record["entry_date"] == "2026-07-14"
    assert record["causal_entry_valid"] is False
    assert record["forward_return_pct"] is None
    assert record["entry_bars"] == []
    assert "selection_forward_return_pct" not in record


def test_paper_trading_records_capture_next_bar_paper_exit_fill_and_data_quality():
    bars = _bars()
    updates = {
        "20260714100000": {"open": 10.7, "high": 10.9, "low": 10.6, "close": 10.8, "price": 10.8, "vwap": 10.4},
        "20260714143000": {"open": 10.4, "high": 10.5, "low": 10.2, "close": 10.3, "price": 10.3, "vwap": 10.5},
        "20260714143100": {"open": 10.2, "high": 10.3, "low": 10.1, "close": 10.2, "price": 10.2, "vwap": 10.4},
    }
    for row in bars:
        row.update(updates.get(row["time"], {}))

    report = build_timing_paper_trading_records(
        [_candidate("600001")],
        minute_bars_by_code={"600001": bars},
        entry_date_by_code={"600001": "2026-07-14"},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        bar_interval="1m",
    )

    record = report["records"][0]
    candidate = record["paper_exit_candidates"]["paper_take_profit_protect_candidate"]
    baseline = record["paper_exit_candidates"]["paper_fixed_exit_baseline"]
    assert candidate["strategy_id"] == "exit_v4_confirmed_factor_protect"
    assert candidate["fill_available"] is True
    assert candidate["simulated_exit_price"] == 10.2
    assert candidate["simulated_exit_return_pct"] == 2.0
    assert baseline["strategy_id"] == "exit_v1_fixed"
    assert record["exit_data_quality"] == {
        "bar_count": 241,
        "chronological": True,
        "missing_price_bar_count": 0,
        "complete_a_share_session": True,
        "paper_research_only": True,
    }
    assert record["execution_assumptions"]["fill_model"] == "next_contiguous_bar_open_when_available"


def test_next_bar_exit_fill_rejects_missing_intraday_bar():
    bars = [
        {"time": "20260714093100", "open": 10.0, "close": 10.0},
        {"time": "20260714093300", "open": 9.8, "close": 9.7},
    ]

    assert _next_bar_fill_price(bars, "20260714093100", "1m") is None


def test_next_bar_exit_fill_rejects_missing_open_even_when_close_exists():
    bars = [
        {"time": "20260714093100", "open": 10.0, "close": 9.6},
        {"time": "20260714093200", "open": None, "close": 9.8},
    ]

    assert _next_bar_fill_price(bars, "20260714093100", "1m") is None


def test_next_bar_exit_fill_accepts_a_share_lunch_transition():
    one_minute = [
        {"time": "20260714113000", "open": 10.0, "close": 10.0},
        {"time": "20260714130100", "open": 9.9, "close": 9.9},
    ]
    five_minute = [
        {"time": "20260714113000", "open": 10.0, "close": 10.0},
        {"time": "20260714130500", "open": 9.8, "close": 9.8},
    ]

    assert _next_bar_fill_price(one_minute, "20260714113000", "1m") == 9.9
    assert _next_bar_fill_price(five_minute, "20260714113000", "5m") == 9.8


def test_paper_trading_records_skip_non_matching_candidates():
    report = build_timing_paper_trading_records(
        [_candidate("600003", lower_low_sequence_risk=40)],
        minute_bars_by_code={"600003": _bars()},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
    )

    assert report["summary"]["record_count"] == 0
    assert report["records"] == []


def test_full_day_signal_cannot_reuse_signal_day_bars_as_entry_path():
    signal_day_bars = [
        {"time": "20260713093000", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "price": 10.2},
        {"time": "20260713150000", "open": 10.2, "high": 10.3, "low": 9.5, "close": 9.8, "price": 9.8},
    ]

    report = build_timing_paper_trading_records(
        [_candidate("600001", forward_return_pct=-3.0)],
        minute_bars_by_code={"600001": signal_day_bars},
        entry_date_by_code={"600001": "2026-07-13"},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        bar_interval="1m",
    )

    record = report["records"][0]
    assert record["causal_entry_valid"] is False
    assert record["path_stats"]["bar_count"] == 0
    assert record["forward_return_pct"] is None
    assert all(not item["triggered"] for item in record["paper_exit_candidates"].values())


def test_next_session_open_is_causal_entry_and_hold_return_label():
    next_day_bars = _bars()

    report = build_timing_paper_trading_records(
        [_candidate("600001", forward_return_pct=-6.25)],
        minute_bars_by_code={"600001": next_day_bars},
        entry_date_by_code={"600001": "2026-07-14"},
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        bar_interval="1m",
    )

    record = report["records"][0]
    assert record["signal_date"] == "2026-07-13"
    assert record["entry_date"] == "2026-07-14"
    assert record["causal_entry_valid"] is True
    assert record["path_stats"]["entry_reference_price"] == 10.0
    assert len(record["entry_bars"]) == 241
    assert record["entry_bars"][0]["time"] == "20260714093000"
    assert record["entry_bars"][-1]["time"] == "20260714150000"
    assert record["selection_forward_return_pct"] == -6.25
    assert record["forward_return_pct"] == -1.0
