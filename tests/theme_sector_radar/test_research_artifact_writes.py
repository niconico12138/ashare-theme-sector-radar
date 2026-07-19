from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_WRITERS = (
    "scripts/backfill_intraday_factors.py",
    "scripts/audit_timing_concentration_risk.py",
    "scripts/audit_timing_factor_exit.py",
    "scripts/audit_timing_strategy_overfit.py",
    "scripts/audit_timing_tail_attribution.py",
    "scripts/run_local_stop_loss_path_validation.py",
    "scripts/run_local_stop_loss_sample.py",
    "scripts/run_timing_combination_experiment.py",
)


@pytest.mark.parametrize("relative_path", RESEARCH_WRITERS)
def test_research_artifact_writers_archive_previous_content_and_emit_strict_json(relative_path):
    source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    assert "write_text_preserving_previous" in source
    assert "allow_nan=False" in source
