from theme_sector_radar.timing.combination_experiment import (
    FactorCondition,
    StrategyVersion,
    build_default_strategy_versions,
    evaluate_strategy_versions,
    evaluate_strategy_stability,
)


def _sample(code, forward_return_pct, **factors):
    row = {"code": code, "forward_return_pct": forward_return_pct}
    row.update(factors)
    return row


def test_combination_experiment_filters_by_quality_and_risk_conditions():
    samples = [
        _sample("600001", 3.0, open_to_midday_resilience_score=80, high_to_close_drawdown_score=8),
        _sample("600002", 1.0, open_to_midday_resilience_score=72, high_to_close_drawdown_score=12),
        _sample("600003", -2.0, open_to_midday_resilience_score=65, high_to_close_drawdown_score=28),
        _sample("600004", -1.0, open_to_midday_resilience_score=40, high_to_close_drawdown_score=6),
    ]
    version = StrategyVersion(
        version_id="unit_quality_risk",
        description="quality plus risk filter",
        conditions=(
            FactorCondition("open_to_midday_resilience_score", ">=", 70),
            FactorCondition("high_to_close_drawdown_score", "<=", 15),
        ),
    )

    report = evaluate_strategy_versions(samples, [version], min_selected=1)
    result = report["versions"][0]

    assert result["selected_count"] == 2
    assert result["rejected_count"] == 2
    assert result["selected_avg_return_pct"] == 2.0
    assert result["rejected_avg_return_pct"] == -1.5
    assert result["spread_vs_rejected_pct"] == 3.5
    assert result["selected_win_rate"] == 1.0
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True


def test_combination_experiment_ranks_best_version_by_return_and_spread():
    samples = [
        _sample("600001", 4.0, open_to_midday_resilience_score=82, midpoint=80),
        _sample("600002", 2.0, open_to_midday_resilience_score=78, midpoint=45),
        _sample("600003", -1.0, open_to_midday_resilience_score=40, midpoint=30),
        _sample("600004", -2.0, open_to_midday_resilience_score=35, midpoint=25),
    ]
    broad = StrategyVersion(
        "broad",
        "broad threshold",
        (FactorCondition("open_to_midday_resilience_score", ">=", 70),),
    )
    strict = StrategyVersion(
        "strict",
        "stricter threshold",
        (FactorCondition("midpoint", ">=", 70),),
    )

    report = evaluate_strategy_versions(samples, [broad, strict], min_selected=1)

    assert report["best_version"]["version_id"] == "strict"
    assert report["versions"][0]["version_id"] == "strict"
    assert report["versions"][0]["research_score"] > report["versions"][1]["research_score"]


def test_combination_experiment_penalizes_large_tail_losses():
    samples = [
        _sample("600001", 4.0, broad=80, strict=80),
        _sample("600002", 3.0, broad=80, strict=20),
        _sample("600003", -8.0, broad=80, strict=20),
        _sample("600004", -1.0, broad=20, strict=20),
    ]
    tail_heavy = StrategyVersion("tail_heavy", "contains tail loss", (FactorCondition("broad", ">=", 70),))
    clean = StrategyVersion("clean", "avoids tail loss", (FactorCondition("strict", ">=", 70),))

    report = evaluate_strategy_versions(samples, [tail_heavy, clean], min_selected=1)

    assert report["best_version"]["version_id"] == "clean"
    tail_result = next(item for item in report["versions"] if item["version_id"] == "tail_heavy")
    assert tail_result["selected_tail_loss_count"] == 1
    assert tail_result["selected_tail_loss_rate"] == 0.3333


def test_strategy_stability_reports_period_sensitivity():
    samples = [
        _sample("600001", 3.0, _sample_date="2026-06-01", quality=80),
        _sample("600002", 2.0, _sample_date="2026-06-02", quality=80),
        _sample("600003", -6.0, _sample_date="2026-06-03", quality=80),
        _sample("600004", -1.0, _sample_date="2026-06-04", quality=20),
        _sample("600005", 4.0, _sample_date="2026-06-05", quality=80),
        _sample("600006", 1.0, _sample_date="2026-06-06", quality=80),
    ]
    version = StrategyVersion("quality", "quality filter", (FactorCondition("quality", ">=", 70),))

    stability = evaluate_strategy_stability(samples, [version], min_selected=1, period_count=3)
    result = stability["versions"][0]

    assert stability["summary"]["period_count"] == 3
    assert result["version_id"] == "quality"
    assert result["periods"][0]["selected_count"] == 2
    assert result["periods"][1]["selected_tail_loss_count"] == 1
    assert result["worst_period_avg_return_pct"] == -6.0
    assert result["positive_period_rate"] == 0.6667
    assert result["active_period_rate"] == 1.0
    assert result["min_period_selected_count"] == 1


def test_strategy_stability_exposes_inactive_periods():
    samples = [
        _sample("600001", 3.0, _sample_date="2026-06-01", quality=80),
        _sample("600002", 2.0, _sample_date="2026-06-02", quality=80),
        _sample("600003", -1.0, _sample_date="2026-06-03", quality=20),
    ]
    version = StrategyVersion("quality", "quality filter", (FactorCondition("quality", ">=", 70),))

    stability = evaluate_strategy_stability(samples, [version], min_selected=1, period_count=3)
    result = stability["versions"][0]

    assert result["periods"][2]["selected_count"] == 0
    assert result["active_period_rate"] == 0.6667
    assert result["min_period_selected_count"] == 0


def test_default_strategy_versions_are_paper_only_factor_combinations():
    versions = build_default_strategy_versions()

    assert len(versions) >= 32
    assert all(version.version_id for version in versions)
    version_ids = {version.version_id for version in versions}
    assert "v31_expanded_balanced_tail_guard" in version_ids
    assert "v32_expanded_defensive_breakdown_guard" in version_ids
    all_fields = {condition.factor_id for version in versions for condition in version.conditions}
    assert "open_to_midday_resilience_score" in all_fields
    assert "vwap_above_ratio_score" in all_fields
    assert "high_to_close_drawdown_score" in all_fields
    assert "risk_adjusted_watch_score_shadow" in all_fields
    assert "optimized_watch_score" in all_fields
    assert "sector_breadth_quality_score" in all_fields
    assert "execution_turnover_depth_score" in all_fields
    assert "execution_tradeability_score" in all_fields
    assert "cashout_failed_late_breakout_risk" in all_fields
    assert "failed_breakout_risk" in all_fields
    assert "late_breakdown_risk" in all_fields
    assert not {
        "final_score",
        "v2_score",
        "selection_score",
        "selection_score_adjusted",
    } & all_fields
