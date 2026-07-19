import json

from scripts.audit_timing_concentration_risk import _audit_version, run_concentration_risk_audit
from theme_sector_radar.timing.combination_experiment import build_default_strategy_versions


def _write_json(path, data):
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _v31_candidate(code, boards, **overrides):
    row = {
        "code": code,
        "name": f"stock-{code}",
        "boards": boards,
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
    }
    row.update(overrides)
    return row


def test_concentration_risk_audit_flags_same_day_board_tail_cluster(tmp_path):
    candidate_root = tmp_path / "candidates"
    validation_root = tmp_path / "selection_validation"
    day = "2026-07-01"
    _write_json(
        candidate_root / day / "top30_candidates.intraday_backfilled.json",
        {
            "candidates": [
                _v31_candidate("600001", ["gas"]),
                _v31_candidate("600002", ["gas"]),
                _v31_candidate("600003", ["robot"]),
                _v31_candidate("600004", ["gas"], lower_low_sequence_risk=40),
            ]
        },
    )
    _write_json(
        validation_root / day / "next_day_selection_validation.json",
        {
            "per_stock": [
                {"code": "600001", "next_return_pct": -6.0},
                {"code": "600002", "next_return_pct": 2.0},
                {"code": "600003", "next_return_pct": 1.0},
                {"code": "600004", "next_return_pct": -8.0},
            ]
        },
    )

    result = run_concentration_risk_audit(
        candidate_root=candidate_root,
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        selection_validation_root=validation_root,
        concentration_threshold=2,
        tail_loss_pct=-5.0,
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    report = result["report"]
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True
    assert report["does_not_modify_official_scores"] is True

    version = report["versions"]["v31_expanded_balanced_tail_guard"]
    assert version["selected_count"] == 3
    assert version["tail_loss_count"] == 1
    assert version["concentrated_group_count"] == 1
    assert version["concentrated_tail_loss_count"] == 1
    assert version["top_concentrated_groups"][0]["group_key"] == "2026-07-01|gas"
    assert version["top_concentrated_groups"][0]["selected_count"] == 2
    assert version["top_concentrated_groups"][0]["tail_loss_count"] == 1

    markdown = result["markdown_path"].read_text(encoding="utf-8")
    assert "Timing Concentration Risk Audit" in markdown
    assert "2026-07-01|gas" in markdown


def test_concentration_aggregate_counts_unique_entries_across_multiple_boards():
    version = next(item for item in build_default_strategy_versions() if item.version_id == "v31_expanded_balanced_tail_guard")
    rows = [
        {**_v31_candidate("600001", ["gas", "transport"]), "_sample_date": "2026-07-01", "forward_return_pct": -6.0},
        {**_v31_candidate("600002", ["gas", "transport"]), "_sample_date": "2026-07-01", "forward_return_pct": 2.0},
    ]

    report = _audit_version(rows, version, concentration_threshold=2, tail_loss_pct=-5.0)

    assert report["concentrated_group_count"] == 2
    assert report["concentrated_selected_count"] == 2
    assert report["concentrated_tail_loss_count"] == 1
    assert report["concentrated_tail_loss_share"] == 1.0
