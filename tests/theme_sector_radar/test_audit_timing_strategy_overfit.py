import json

from scripts.audit_timing_strategy_overfit import run_overfit_audit


def _write_json(path, data):
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _passing_candidate(code, market_score=65):
    return {
        "code": code,
        "boards": ["test_board"],
        "open_to_midday_resilience_score": 70,
        "midday_hold_score": 70,
        "vwap_above_ratio_score": 70,
        "late_high_near_close_score": 90,
        "high_to_close_drawdown_score": 5,
        "lower_low_sequence_risk": 10,
        "stock_vs_market_intraday_alpha_score": 80,
        "relative_resilience_score": 80,
        "optimized_watch_score": 82,
        "optimized_watch_score_v2_shadow": 84,
        "late_amount_surge_score": 30,
        "high_area_acceptance_score": 85,
        "afternoon_recovery_score": 35,
        "execution_tradeability_score": 72,
        "execution_turnover_depth_score": 78,
        "cashout_failed_late_breakout_risk": 20,
        "market_regime_score": market_score,
    }


def test_run_overfit_audit_writes_paper_only_report(tmp_path):
    candidate_root = tmp_path / "candidates_5m"
    validation_root = tmp_path / "selection_validation"
    for day, ret in [("2026-07-01", 3.0), ("2026-07-02", 2.0), ("2026-07-03", -1.0)]:
        _write_json(
            candidate_root / day / "top30_candidates.intraday_backfilled.json",
            {"candidates": [_passing_candidate(f"600{day[-2:]}")]},
        )
        _write_json(
            validation_root / day / "next_day_selection_validation.json",
            {"per_stock": [{"code": f"600{day[-2:]}", "next_return_pct": ret}]},
        )

    result = run_overfit_audit(
        candidate_root_5m=candidate_root,
        candidate_root_1m=None,
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        selection_validation_root=validation_root,
        min_selected=1,
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    report = result["report"]
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True
    assert report["does_not_modify_official_scores"] is True
    assert report["datasets"]["5m"]["summary"]["labeled_sample_count"] == 3
    assert report["datasets"]["5m"]["summary"]["rows_with_v29_operational_fields"] == 3
    assert report["v29_overfit_judgement"]["risk_level"] in {"medium", "high"}
    markdown = result["markdown_path"].read_text(encoding="utf-8")
    assert "V29 Overfit Audit" in markdown
    assert "Threshold Perturbation" in markdown
