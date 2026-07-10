from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


def test_daily_orchestrator_runbook_documents_operational_flags_and_exit_codes():
    content = (ROOT / "docs" / "runbooks" / "daily_orchestrator.md").read_text(encoding="utf-8")

    for flag in ["--preflight-only", "--dry-run", "--fail-on-stale-artifact", "--resume"]:
        assert flag in content

    for exit_code in ["0", "1", "2", "3"]:
        assert f"| {exit_code} |" in content


def test_daily_orchestrator_runbook_documents_scoring_calibration_inputs():
    content = (ROOT / "docs" / "runbooks" / "daily_orchestrator.md").read_text(encoding="utf-8")

    assert "build_forward_returns.py" in content
    assert "evaluate_scoring_calibration.py" in content
    assert "aggregate_scoring_calibration.py" in content
    assert "run_scoring_calibration_batch.py" in content
    assert "--source stockdb-sdk" in content
    assert "forward_returns.json" in content
    assert "reports/scoring_calibration/aggregate" in content
    assert "reports/scoring_calibration/batch" in content
    assert "reports/scoring_calibration/DATE/scoring_calibration.json" in content

