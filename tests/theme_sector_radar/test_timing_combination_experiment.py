from theme_sector_radar.timing.combination_experiment import (
    FactorCondition,
    StrategyVersion,
    build_default_strategy_versions,
    evaluate_strategy_versions,
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


def test_default_strategy_versions_are_paper_only_factor_combinations():
    versions = build_default_strategy_versions()

    assert len(versions) >= 15
    assert all(version.version_id for version in versions)
    all_fields = {condition.factor_id for version in versions for condition in version.conditions}
    assert "open_to_midday_resilience_score" in all_fields
    assert "vwap_above_ratio_score" in all_fields
    assert "high_to_close_drawdown_score" in all_fields
