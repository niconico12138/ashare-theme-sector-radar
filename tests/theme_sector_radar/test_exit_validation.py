from theme_sector_radar.timing.exit_validation import validate_dual_exit_records


def _record(date, code, board, version, *, triggered, fill_return, forward_return):
    return {
        "as_of": date,
        "code": code,
        "boards": [board],
        "timing_version_id": version,
        "forward_return_pct": forward_return,
        "path_stats": {"max_favorable_excursion_pct": 6.0, "max_adverse_excursion_pct": -4.0},
        "paper_exit_candidates": {
            "paper_take_profit_protect_candidate": {
                "triggered": triggered,
                "fill_available": triggered,
                "simulated_exit_return_pct": fill_return,
                "trigger_factors": ["price_below_vwap"],
            },
            "paper_stop_loss_risk_candidate": {
                "triggered": False,
                "fill_available": False,
                "simulated_exit_return_pct": None,
                "trigger_factors": [],
            },
        },
    }


def test_validate_dual_exit_records_reports_walk_forward_and_concentration():
    records = [
        _record("2026-01-02", "600001", "gas", "v31", triggered=True, fill_return=3.0, forward_return=-6.0),
        _record("2026-01-03", "600002", "gas", "v31", triggered=True, fill_return=2.0, forward_return=-4.0),
        _record("2026-01-04", "600003", "robot", "v32", triggered=True, fill_return=1.0, forward_return=5.0),
        _record("2026-01-05", "600004", "robot", "v32", triggered=False, fill_return=None, forward_return=1.0),
    ]

    report = validate_dual_exit_records(records, fold_count=3, min_labeled_triggers=1, tail_loss_pct=-5.0)

    candidate = report["candidates"]["paper_take_profit_protect_candidate"]
    assert report["paper_trading_only"] is True
    assert candidate["summary"]["trigger_count"] == 3
    assert candidate["summary"]["forward_tail_avoided_count"] == 1
    assert candidate["walk_forward"]["fold_count"] == 3
    assert candidate["concentration"]["top_board_share"] == 0.6667
    assert candidate["by_version"]["v31"]["trigger_count"] == 2
    assert candidate["by_trigger_factor"]["price_below_vwap"]["trigger_count"] == 3


def test_validate_dual_exit_records_marks_small_fold_as_insufficient():
    report = validate_dual_exit_records(
        [_record("2026-01-02", "600001", "gas", "v31", triggered=True, fill_return=3.0, forward_return=-6.0)],
        fold_count=3,
        min_labeled_triggers=2,
    )

    folds = report["candidates"]["paper_take_profit_protect_candidate"]["walk_forward"]["folds"]
    assert folds[0]["status"] == "insufficient_sample"


def test_exit_concentration_uses_trigger_record_denominator_for_multi_board_membership():
    records = [
        _record("2026-01-02", "600001", "gas", "v31", triggered=True, fill_return=3.0, forward_return=-6.0),
        _record("2026-01-03", "600002", "gas", "v31", triggered=True, fill_return=2.0, forward_return=-4.0),
        _record("2026-01-04", "600003", "robot", "v32", triggered=True, fill_return=1.0, forward_return=5.0),
    ]
    records[0]["boards"] = ["gas", "robot"]
    records[2]["boards"] = []

    report = validate_dual_exit_records(records, min_labeled_triggers=1)
    concentration = report["candidates"]["paper_take_profit_protect_candidate"]["concentration"]

    assert concentration["top_board_share"] == 0.6667
    assert concentration["board_coverage_rate"] == 0.6667


def test_exit_validation_excludes_nonfinite_fill_returns():
    report = validate_dual_exit_records(
        [_record("2026-01-02", "600001", "gas", "v31", triggered=True, fill_return=float("nan"), forward_return=1.0)],
        min_labeled_triggers=1,
    )

    summary = report["candidates"]["paper_take_profit_protect_candidate"]["summary"]
    assert summary["labeled_trigger_count"] == 0
    assert summary["avg_simulated_exit_return_pct"] is None


def test_exit_concentration_deduplicates_same_entry_across_strategy_versions():
    first = _record("2026-01-02", "600001", "gas", "v31", triggered=True, fill_return=3.0, forward_return=-6.0)
    second = _record("2026-01-02", "600001", "gas", "v32", triggered=True, fill_return=3.0, forward_return=-6.0)

    report = validate_dual_exit_records([first, second], min_labeled_triggers=1)
    candidate = report["candidates"]["paper_take_profit_protect_candidate"]
    concentration = candidate["concentration"]

    assert report["summary"]["record_count"] == 2
    assert report["summary"]["deduplicated_entry_count"] == 1
    assert candidate["summary"]["trigger_count"] == 1
    assert candidate["summary"]["labeled_trigger_count"] == 1
    assert concentration["trigger_count"] == 1
    assert concentration["top_date_share"] == 1.0
    assert concentration["top_code_share"] == 1.0


def test_exit_validation_rejects_same_entry_with_different_path_hashes():
    first = _record("2026-01-02", "600001", "gas", "v31", triggered=True, fill_return=3.0, forward_return=-6.0)
    first.update(
        signal_date="2026-01-02",
        entry_date="2026-01-05",
        entry_bars_sha256="a" * 64,
        execution_assumptions={"bar_interval": "1m"},
    )
    second = dict(first)
    second["timing_version_id"] = "v32"
    second["entry_bars_sha256"] = "b" * 64

    import pytest

    with pytest.raises(ValueError, match="duplicate entry policy/path conflict"):
        validate_dual_exit_records([first, second], min_labeled_triggers=1)
