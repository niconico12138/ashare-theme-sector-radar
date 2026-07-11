"""Tests for shadow-only factor value backtesting."""

from pathlib import Path

import pytest

from theme_sector_radar.backtest.factor_value import (
    DEFAULT_FACTOR_SPECS,
    evaluate_factor_value,
    evaluate_formula_value,
    load_factor_backtest_dataset,
    run_shadow_score_validation,
)


def _write_json(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def test_load_factor_backtest_dataset_matches_candidates_and_forward_returns(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.json",
        '{"candidates":[{"code":"600001","liquidity_score":80},{"code":"600002","liquidity_score":20}]}',
    )
    _write_json(
        returns_root / "2026-07-01" / "forward_returns.json",
        '{"forward_returns":{"600001":{"1d":2.0,"5d":5.0},"600002":{"1d":-1.0,"5d":-2.0}}}',
    )

    dataset = load_factor_backtest_dataset(
        dates=["2026-07-01"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=("1d", "5d"),
    )

    assert dataset.coverage["candidate_count"] == 2
    assert dataset.coverage["usable_sample_count"] == 2
    assert dataset.samples[0].sample_id == "2026-07-01:600001"
    assert dataset.samples[0].returns["5d"] == 5.0


def test_evaluate_factor_value_scores_directional_value():
    samples = []
    for idx, score in enumerate([90, 80, 70, 30, 20, 10], start=1):
        samples.append(
            {
                "sample_id": f"s{idx}",
                "candidate": {"code": f"60000{idx}", "momentum_score": score},
                "returns": {"5d": score / 10 - 5},
            }
        )

    result = evaluate_factor_value(
        samples,
        factor_id="momentum_score",
        horizons=("5d",),
        min_samples=3,
    )

    horizon = result["horizon_results"]["5d"]
    assert horizon["sample_count"] == 6
    assert horizon["rank_ic"] == pytest.approx(1.0)
    assert horizon["top_bottom_spread"] > 0
    assert result["value_label"] == "strong_positive"


def test_evaluate_factor_value_detects_inverse_factor():
    samples = []
    for idx, score in enumerate([90, 80, 70, 30, 20, 10], start=1):
        samples.append(
            {
                "sample_id": f"s{idx}",
                "candidate": {"code": f"60000{idx}", "risk_score": score},
                "returns": {"5d": 5 - score / 10},
            }
        )

    result = evaluate_factor_value(samples, "risk_score", horizons=("5d",), min_samples=3)

    assert result["horizon_results"]["5d"]["rank_ic"] == pytest.approx(-1.0)
    assert result["value_label"] == "strong_inverse"
    assert result["suggested_usage"] == "risk_filter_or_penalty"


def test_evaluate_formula_value_uses_safe_arithmetic_only():
    samples = [
        {"sample_id": "a", "candidate": {"x": 80, "y": 20}, "returns": {"1d": 3.0}},
        {"sample_id": "b", "candidate": {"x": 20, "y": 80}, "returns": {"1d": -1.0}},
        {"sample_id": "c", "candidate": {"x": 60, "y": 40}, "returns": {"1d": 1.0}},
    ]

    result = evaluate_formula_value(
        samples,
        formula_name="quality_minus_risk",
        formula="x - 0.5 * y",
        horizons=("1d",),
        min_samples=3,
    )

    assert result["factor_id"] == "formula:quality_minus_risk"
    assert result["horizon_results"]["1d"]["rank_ic"] > 0

    with pytest.raises(ValueError):
        evaluate_formula_value(samples, "unsafe", "__import__('os').system('echo bad')", horizons=("1d",))


def test_default_factor_specs_include_existing_factor_library_fields():
    ids = {spec.factor_id for spec in DEFAULT_FACTOR_SPECS}
    assert {"final_score", "factor_composite_shadow_score_v2", "sector_support_score", "liquidity_score", "chasing_risk_score"}.issubset(ids)


def test_run_factor_backtest_script_writes_reports(tmp_path, monkeypatch):
    from scripts.run_factor_backtest import main

    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "factor_backtest"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.json",
        '{"candidates":[{"code":"600001","liquidity_score":90},{"code":"600002","liquidity_score":10},{"code":"600003","liquidity_score":50}]}',
    )
    _write_json(
        returns_root / "2026-07-01" / "forward_returns.json",
        '{"forward_returns":{"600001":{"1d":3.0},"600002":{"1d":-2.0},"600003":{"1d":1.0}}}',
    )

    exit_code = main([
        "--start-date", "2026-07-01",
        "--end-date", "2026-07-01",
        "--candidate-root", str(candidate_root),
        "--returns-root", str(returns_root),
        "--output-dir", str(output_dir),
        "--horizons", "1d",
        "--min-samples", "3",
    ])

    report_dir = output_dir / "2026-07-01_to_2026-07-01"
    assert exit_code == 0
    assert (report_dir / "factor_value_backtest.json").exists()
    assert (report_dir / "factor_value_backtest.md").exists()


def test_loader_falls_back_when_first_forward_return_file_has_no_usable_returns(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-02" / "top30_candidates.json",
        '{"candidates":[{"code":"600001","liquidity_score":80}]}',
    )
    _write_json(
        returns_root / "2026-07-02" / "forward_returns.json",
        '{"forward_returns":{"600001":{"1d":null}}}',
    )
    _write_json(
        returns_root / "2026-07-02.json",
        '{"items":[{"code":"600001","1d":2.5}]}',
    )

    dataset = load_factor_backtest_dataset(
        dates=["2026-07-02"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=("1d",),
    )

    assert dataset.coverage["usable_sample_count"] == 1
    assert dataset.samples[0].returns["1d"] == 2.5


def test_parse_horizons_accepts_comma_or_whitespace_forms():
    from scripts.run_factor_backtest import parse_horizons

    assert parse_horizons("1d,3d,5d") == ("1d", "3d", "5d")
    assert parse_horizons("1d 3d 5d") == ("1d", "3d", "5d")
    assert parse_horizons("1d, 3d 5d") == ("1d", "3d", "5d")


def test_parse_horizons_restores_powershell_day_suffix_loss():
    from scripts.run_factor_backtest import parse_horizons

    assert parse_horizons("1,3,5,10") == ("1d", "3d", "5d", "10d")


def test_default_factor_specs_cover_observed_factor_registry_fields():
    from theme_sector_radar.backtest.factor_value import DEFAULT_FACTOR_SPECS

    ids = {spec.factor_id for spec in DEFAULT_FACTOR_SPECS}
    assert {
        "ma20_slope_5",
        "stock_trend_score",
        "stock_short_score",
        "risk_adjusted_watch_score_shadow",
        "short_burst_risk_adjusted_score_shadow",
        "optimized_watch_score_v2_shadow",
        "relative_strength_20",
        "relative_strength_60",
        "risk_adjusted_return_20",
        "volume_stability_score",
        "trend_persistence_score",
        "sector_peer_rank_score",
        "short_emotion_heat_score",
        "sector_burst_breadth_score",
        "limit_attention_score",
        "intraday_reversal_risk_score",
        "close_strength_score",
        "volume_burst_quality_score",
        "single_name_overheat_score",
        "next_day_cashout_risk_score",
        "short_burst_emotion_score_v1",
        "short_burst_emotion_score_v2",
        "market_short_emotion_score",
        "limit_up_breadth_score",
        "limit_up_failure_risk",
        "leader_continuation_score",
        "short_burst_environment_score",
        "crowding_heat_score",
        "news_heat_score",
        "policy_catalyst_score",
        "earnings_catalyst_score",
        "event_freshness_score",
        "event_continuation_score",
        "negative_news_risk_score",
        "rumor_hype_risk_score",
        "short_burst_news_emotion_score_shadow",
        "intraday_close_position_score",
        "intraday_high_pullback_risk_score",
        "intraday_volume_price_confirm_score",
        "intraday_sector_breadth_score",
        "intraday_late_strength_score",
        "short_burst_intraday_emotion_score_shadow",
        "late_return_30m_score",
        "late_vwap_support_score",
        "late_volume_share_score",
        "late_high_near_close_score",
        "high_to_close_drawdown_score",
        "morning_spike_fade_score",
        "afternoon_fade_score",
        "max_gain_giveback_ratio",
        "close_vs_vwap_score",
        "late_price_above_vwap_ratio",
        "vwap_slope_score",
        "vwap_reclaim_score",
        "volume_without_price_progress_risk",
        "late_volume_efficiency_score",
        "amount_acceleration_score",
        "volume_spike_exhaustion_score",
        "opening_drive_score",
        "morning_strength_persist_score",
        "morning_pullback_repair_score",
        "open_to_midday_resilience_score",
        "sector_intraday_breadth_change",
        "sector_late_breadth_score",
        "leader_follower_sync_score",
        "stock_vs_sector_intraday_alpha",
        "risk_penalty_score",
        "amount_ratio_20",
        "contraction_score",
        "near_high_250",
        "regime_router_shadow_score_v5",
        "agent_score",
        "sector_trend_score",
        "sector_burst_score",
    }.issubset(ids)


def test_loader_prefers_analysis_backfilled_candidates(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-03" / "top30_candidates.json",
        '{"candidates":[{"code":"600001","selection_score":10}]}',
    )
    _write_json(
        candidate_root / "2026-07-03" / "top30_candidates.analysis_backfilled.json",
        '{"candidates":[{"code":"600001","selection_score":88}]}',
    )
    _write_json(
        returns_root / "2026-07-03.json",
        '{"items":[{"code":"600001","1d":1.0}]}',
    )

    dataset = load_factor_backtest_dataset(
        dates=["2026-07-03"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=("1d",),
    )

    assert dataset.samples[0].candidate["selection_score"] == 88


def test_loader_prefers_intraday_backfilled_candidates(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-03" / "top30_candidates.analysis_backfilled.json",
        '{"candidates":[{"code":"600001","selection_score":88}]}',
    )
    _write_json(
        candidate_root / "2026-07-03" / "top30_candidates.intraday_backfilled.json",
        '{"candidates":[{"code":"600001","selection_score":99,"intraday_close_position_score":77}]}',
    )
    _write_json(
        returns_root / "2026-07-03" / "forward_returns.json",
        '{"forward_returns":{"600001":{"1d":1.2}}}',
    )

    dataset = load_factor_backtest_dataset(["2026-07-03"], candidate_root, returns_root, ("1d",))

    assert dataset.samples[0].candidate["selection_score"] == 99
    assert dataset.samples[0].candidate["intraday_close_position_score"] == 77


def test_loader_prefers_news_emotion_backfilled_candidates(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-03" / "top30_candidates.intraday_backfilled.json",
        '{"candidates":[{"code":"600001","selection_score":99,"intraday_close_position_score":77}]}',
    )
    _write_json(
        candidate_root / "2026-07-03" / "top30_candidates.news_emotion_backfilled.json",
        '{"candidates":[{"code":"600001","selection_score":101,"short_burst_news_emotion_score_shadow":66}]}',
    )
    _write_json(
        returns_root / "2026-07-03" / "forward_returns.json",
        '{"forward_returns":{"600001":{"1d":1.2}}}',
    )

    dataset = load_factor_backtest_dataset(["2026-07-03"], candidate_root, returns_root, ("1d",))

    assert dataset.samples[0].candidate["selection_score"] == 101
    assert dataset.samples[0].candidate["short_burst_news_emotion_score_shadow"] == 66


def test_shadow_score_validation_promotes_shadow_candidate_when_rollingly_better(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    dates = ["2026-07-08", "2026-07-09", "2026-07-10"]
    for date in dates:
        _write_json(
            candidate_root / date / "top30_candidates.analysis_backfilled.json",
            """
            {
              "candidates": [
                {"code":"600001","optimized_watch_score":60,"optimized_watch_score_v2_shadow":90},
                {"code":"600002","optimized_watch_score":90,"optimized_watch_score_v2_shadow":60},
                {"code":"600003","optimized_watch_score":50,"optimized_watch_score_v2_shadow":50}
              ]
            }
            """,
        )
        _write_json(
            returns_root / f"{date}.json",
            '{"items":[{"code":"600001","5d":5.0},{"code":"600002","5d":-2.0},{"code":"600003","5d":1.0}]}',
        )

    result = run_shadow_score_validation(
        end_date="2026-07-10",
        candidate_root=candidate_root,
        returns_root=returns_root,
        windows=(1, 2, 3),
        horizons=("5d",),
        min_samples=3,
        min_ic_improvement=0.1,
        min_pass_windows=2,
    )

    assert result["recommendation"] == "promote_shadow_candidate"
    assert result["summary"]["pass_window_count"] >= 2
    assert all(item["shadow_rank_ic"] > item["baseline_rank_ic"] for item in result["window_results"])


def test_run_shadow_score_validation_script_writes_reports(tmp_path):
    from scripts.run_shadow_score_validation import main

    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "shadow_validation"
    _write_json(
        candidate_root / "2026-07-10" / "top30_candidates.analysis_backfilled.json",
        """
        {
          "candidates": [
            {"code":"600001","optimized_watch_score":60,"optimized_watch_score_v2_shadow":90},
            {"code":"600002","optimized_watch_score":90,"optimized_watch_score_v2_shadow":60},
            {"code":"600003","optimized_watch_score":50,"optimized_watch_score_v2_shadow":50}
          ]
        }
        """,
    )
    _write_json(
        returns_root / "2026-07-10.json",
        '{"items":[{"code":"600001","5d":5.0},{"code":"600002","5d":-2.0},{"code":"600003","5d":1.0}]}',
    )

    exit_code = main([
        "--end-date", "2026-07-10",
        "--windows", "1",
        "--candidate-root", str(candidate_root),
        "--returns-root", str(returns_root),
        "--output-dir", str(output_dir),
        "--horizons", "5d",
        "--min-samples", "3",
        "--min-pass-windows", "1",
    ])

    assert exit_code == 0
    assert (output_dir / "2026-07-10" / "shadow_score_validation.json").exists()
    assert (output_dir / "2026-07-10" / "shadow_score_validation.md").exists()
