import json

from scripts.run_timing_combination_experiment import run_timing_combination_experiment


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_run_timing_combination_experiment_writes_report(tmp_path):
    candidate_root = tmp_path / "candidates"
    date = "2026-07-07"
    _write_json(
        candidate_root / date / "top30_candidates.intraday_backfilled.json",
        {
            "candidates": [
                {
                    "code": "600001",
                    "open_to_midday_resilience_score": 80,
                    "midday_hold_score": 70,
                    "vwap_above_ratio_score": 70,
                    "midday_vwap_support_score": 70,
                    "late_high_near_close_score": 90,
                    "high_area_acceptance_score": 85,
                    "high_to_close_drawdown_score": 5,
                    "late_breakdown_risk": 1,
                    "lower_low_sequence_risk": 10,
                    "volume_without_price_progress_risk": 5,
                },
                {
                    "code": "600002",
                    "open_to_midday_resilience_score": 40,
                    "midday_hold_score": 35,
                    "vwap_above_ratio_score": 30,
                    "midday_vwap_support_score": 35,
                    "late_high_near_close_score": 45,
                    "high_area_acceptance_score": 42,
                    "high_to_close_drawdown_score": 40,
                    "late_breakdown_risk": 20,
                    "lower_low_sequence_risk": 65,
                    "volume_without_price_progress_risk": 35,
                },
            ]
        },
    )
    _write_json(
        tmp_path / "selection_validation" / date / "next_day_selection_validation.json",
        {
            "per_stock": [
                {"code": "600001", "next_return_pct": 3.0},
                {"code": "600002", "next_return_pct": -1.0},
            ]
        },
    )

    result = run_timing_combination_experiment(
        candidate_root=candidate_root,
        output_dir=tmp_path / "out",
        as_of="2026-07-10",
        snapshot_label="unit",
        start=date,
        end=date,
        selection_validation_root=tmp_path / "selection_validation",
        min_selected=1,
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    report = result["report"]
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True
    assert report["summary"]["labeled_sample_count"] == 2
    assert report["best_version"]["selected_avg_return_pct"] == 3.0
    assert "selected_tail_loss_count" in report["best_version"]
    assert report["stability"]["summary"]["date_count"] == 1
    assert "stability_adjusted_score" in report["best_version"]
    markdown = result["markdown_path"].read_text(encoding="utf-8")
    assert "Tail losses" in markdown
    assert "Stability Check" in markdown
    assert "Stability adjusted" in markdown
