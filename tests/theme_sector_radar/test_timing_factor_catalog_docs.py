from pathlib import Path

from theme_sector_radar.timing.factor_catalog import TIMING_FACTOR_CATEGORIES


def test_timing_factor_catalog_runbook_lists_categories_and_testing_strategy():
    text = Path("docs/runbooks/timing_factor_catalog.md").read_text(encoding="utf-8")

    for category in TIMING_FACTOR_CATEGORIES:
        assert f"`{category}`" in text
    assert "Testing Strategy" in text
    assert "Expansion Order" in text
    assert "Intraday Bar Granularity" in text
    assert "`5m`" in text
    assert "`1m`" in text
    assert "evaluate_intraday_buy_trigger" in text
    assert "evaluate_intraday_exit_sequence" in text
    assert "run_intraday_trigger_experiment" in text
    assert "Recommended Research Flow" in text
    assert "paper-only" in text
    assert "does not emit executable trading signals" in text
