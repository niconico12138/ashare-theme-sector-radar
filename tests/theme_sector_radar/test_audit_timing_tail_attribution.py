import json

from scripts.audit_timing_tail_attribution import run_tail_attribution


def _write_json(path, data):
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _v31_candidate(code, **overrides):
    row = {
        "code": code,
        "name": f"stock-{code}",
        "boards": ["test_board"],
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
        "cashout_failed_late_breakout_risk": 20,
        "market_regime_score": 55,
        "sector_breadth_quality_score": 65,
        "execution_vwap_slippage_risk": 20,
    }
    row.update(overrides)
    return row


def test_tail_attribution_reports_selected_tail_loss_buckets(tmp_path):
    candidate_root = tmp_path / "candidates"
    validation_root = tmp_path / "selection_validation"
    day = "2026-07-01"
    _write_json(
        candidate_root / day / "top30_candidates.intraday_backfilled.json",
        {
            "candidates": [
                _v31_candidate("600001", cashout_failed_late_breakout_risk=68),
                _v31_candidate("600002"),
                _v31_candidate("600003", lower_low_sequence_risk=40),
            ]
        },
    )
    _write_json(
        validation_root / day / "next_day_selection_validation.json",
        {
            "per_stock": [
                {"code": "600001", "next_return_pct": -6.2},
                {"code": "600002", "next_return_pct": 2.4},
                {"code": "600003", "next_return_pct": -8.0},
            ]
        },
    )

    result = run_tail_attribution(
        candidate_root=candidate_root,
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        selection_validation_root=validation_root,
        tail_loss_pct=-5.0,
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    report = result["report"]
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True
    assert report["does_not_modify_official_scores"] is True

    version = report["versions"]["v31_expanded_balanced_tail_guard"]
    assert version["selected_count"] == 2
    assert version["tail_loss_count"] == 1
    assert version["tail_bucket_counts"]["failed_breakout"] == 1
    assert version["tail_rows"][0]["code"] == "600001"
    assert version["tail_rows"][0]["dominant_risk_bucket"] == "failed_breakout"

    markdown = result["markdown_path"].read_text(encoding="utf-8")
    assert "Timing Tail Attribution" in markdown
    assert "failed_breakout" in markdown
