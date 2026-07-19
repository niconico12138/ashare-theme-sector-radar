from theme_sector_radar.timing.factor_exit import evaluate_factor_exit_triggers


def test_factor_exit_v1_fixed_takes_profit_before_close():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0},
        {"time": "10:00", "price": 10.4, "high": 10.6, "low": 10.2, "close": 10.4},
        {"time": "14:30", "price": 10.2, "high": 10.3, "low": 10.1, "close": 10.2},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)
    fixed = report["strategies"]["exit_v1_fixed"]

    assert fixed["triggered"] is True
    assert fixed["trigger_type"] == "take_profit"
    assert fixed["trigger_time"] == "10:00"
    assert fixed["trigger_return_pct"] == 5.0
    assert fixed["close_return_pct"] == 2.0
    assert fixed["saved_vs_close_pct"] == 3.0
    assert fixed["exit_research_only"] is True
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True


def test_factor_exit_v1_fixed_stop_requires_bar_close_confirmation():
    bars = [
        {"time": "20260714093000", "open": 10.0, "high": 10.0, "low": 9.5, "close": 9.8, "price": 9.8},
        {"time": "20260714093100", "open": 9.8, "high": 9.8, "low": 9.5, "close": 9.6, "price": 9.6},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)

    fixed = report["strategies"]["exit_v1_fixed"]
    assert fixed["triggered"] is True
    assert fixed["trigger_type"] == "stop_loss"
    assert fixed["trigger_time"] == "20260714093100"
    assert fixed["trigger_return_pct"] == -4.0


def test_factor_exit_v2_protects_profit_when_price_breaks_vwap():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0, "vwap": 10.0},
        {"time": "10:00", "price": 10.7, "high": 10.8, "low": 10.5, "close": 10.7, "vwap": 10.3},
        {"time": "14:30", "price": 10.3, "high": 10.4, "low": 10.2, "close": 10.3, "vwap": 10.4},
        {"time": "15:00", "price": 10.1, "high": 10.2, "low": 10.0, "close": 10.1, "vwap": 10.35},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)
    protect = report["strategies"]["exit_v2_factor_protect"]

    assert protect["triggered"] is True
    assert protect["trigger_type"] == "take_profit_protect"
    assert protect["trigger_time"] == "14:30"
    assert protect["trigger_return_pct"] == 3.0
    assert "price_below_vwap" in protect["trigger_factors"]
    assert protect["close_return_pct"] == 1.0
    assert protect["saved_vs_close_pct"] == 2.0


def test_factor_exit_v2_derives_vwap_from_amount_and_volume():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.0, "low": 9.9, "close": 10.0, "amount": 1000.0, "volume": 100.0},
        {"time": "10:00", "price": 11.0, "high": 11.0, "low": 10.8, "close": 11.0, "amount": 1100.0, "volume": 100.0},
        {"time": "10:30", "price": 10.4, "high": 10.6, "low": 10.3, "close": 10.4, "amount": 8320.0, "volume": 800.0},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0, protect_peak_giveback_pct=5.0)
    protect = report["strategies"]["exit_v2_factor_protect"]

    assert protect["triggered"] is True
    assert protect["trigger_time"] == "10:30"
    assert "price_below_vwap" in protect["trigger_factors"]


def test_factor_exit_v4_ignores_unconfirmed_volume_stall():
    bars = [
        {
            "time": "09:30",
            "price": 10.0,
            "high": 10.0,
            "low": 9.9,
            "close": 10.0,
            "volume_without_price_progress_risk": 0.0,
        },
        {
            "time": "10:00",
            "price": 10.4,
            "high": 10.45,
            "low": 10.3,
            "close": 10.4,
            "volume_without_price_progress_risk": 20.0,
        },
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)

    assert report["strategies"]["exit_v2_factor_protect"]["triggered"] is True
    assert report["strategies"]["exit_v4_confirmed_factor_protect"]["triggered"] is False


def test_factor_exit_v4_confirms_vwap_break():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.0, "low": 9.9, "close": 10.0, "vwap": 10.0},
        {"time": "10:00", "price": 10.8, "high": 10.9, "low": 10.7, "close": 10.8, "vwap": 10.4},
        {"time": "10:30", "price": 10.3, "high": 10.4, "low": 10.2, "close": 10.3, "vwap": 10.5},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)
    confirmed = report["strategies"]["exit_v4_confirmed_factor_protect"]

    assert confirmed["triggered"] is True
    assert confirmed["trigger_type"] == "take_profit_confirmed_protect"
    assert "price_below_vwap" in confirmed["trigger_factors"]


def test_factor_exit_v2_protects_profit_after_peak_giveback_without_vwap():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0},
        {"time": "10:00", "price": 10.8, "high": 10.8, "low": 10.5, "close": 10.8},
        {"time": "14:00", "price": 10.5, "high": 10.5, "low": 10.3, "close": 10.5},
        {"time": "15:00", "price": 10.2, "high": 10.2, "low": 10.1, "close": 10.2},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)
    protect = report["strategies"]["exit_v2_factor_protect"]

    assert protect["triggered"] is True
    assert protect["trigger_type"] == "take_profit_protect"
    assert protect["trigger_time"] == "14:00"
    assert protect["trigger_return_pct"] == 5.0
    assert "peak_giveback_from_profit" in protect["trigger_factors"]


def test_factor_exit_v2_peak_giveback_threshold_can_be_relaxed():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0},
        {"time": "10:00", "price": 10.8, "high": 10.8, "low": 10.5, "close": 10.8},
        {"time": "14:00", "price": 10.5, "high": 10.5, "low": 10.3, "close": 10.5},
        {"time": "15:00", "price": 10.2, "high": 10.2, "low": 10.1, "close": 10.2},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0, protect_peak_giveback_pct=4.0)

    assert report["strategies"]["exit_v2_factor_protect"]["triggered"] is False


def test_factor_exit_v3_risk_exits_after_stop_and_trend_break():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0, "vwap": 10.0},
        {"time": "10:30", "price": 9.8, "high": 9.9, "low": 9.7, "close": 9.8, "vwap": 9.95},
        {"time": "14:30", "price": 9.6, "high": 9.7, "low": 9.5, "close": 9.6, "vwap": 9.9},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)
    risk = report["strategies"]["exit_v3_factor_risk"]

    assert risk["triggered"] is True
    assert risk["trigger_type"] == "stop_loss_factor"
    assert risk["trigger_time"] == "14:30"
    assert risk["trigger_return_pct"] == -4.0
    assert "price_below_vwap" in risk["trigger_factors"]
    assert "lower_low_sequence" in risk["trigger_factors"]


def test_factor_exit_exposes_independent_paper_profit_and_loss_candidates():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0, "vwap": 10.0},
        {"time": "10:30", "price": 9.8, "high": 9.9, "low": 9.7, "close": 9.8, "vwap": 9.95},
        {"time": "14:30", "price": 9.6, "high": 9.7, "low": 9.5, "close": 9.6, "vwap": 9.9},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)
    strategies = report["strategies"]
    protect = strategies["exit_v4_confirmed_factor_protect"]
    risk = strategies["exit_v5_factor_risk_confirmed"]

    assert protect["paper_candidate_kind"] == "take_profit_protect"
    assert risk["paper_candidate_kind"] == "stop_loss_risk"
    assert risk["triggered"] is True
    assert risk["trigger_type"] == "stop_loss_confirmed_risk"
    assert set(risk["trigger_factors"]) == {"price_below_vwap", "lower_low_sequence"}


def test_factor_exit_reports_untriggered_strategy_with_close_return():
    bars = [
        {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0, "vwap": 10.0},
        {"time": "15:00", "price": 10.2, "high": 10.3, "low": 10.0, "close": 10.2, "vwap": 10.1},
    ]

    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)

    assert report["strategies"]["exit_v2_factor_protect"]["triggered"] is False
    assert report["strategies"]["exit_v2_factor_protect"]["close_return_pct"] == 2.0
    assert report["strategies"]["exit_v2_factor_protect"]["missed_upside_pct"] == 0.0
