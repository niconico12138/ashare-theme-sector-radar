import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import run_daily


def test_build_steps_uses_longer_bridge_timeout():
    steps = run_daily.build_steps("2026-07-08", sys.executable, quick=False, skip_agent=False)

    bridge = [s for s in steps if s.name == "Bridge Report"][0]

    assert bridge.timeout_seconds >= 1200
    assert bridge.required_mode == "agent_only"


def test_run_step_handles_none_output_without_masking_return_code(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=1, stdout=None, stderr=None)

    monkeypatch.setattr(run_daily.subprocess, "run", fake_run)

    result = run_daily.run_step(
        run_daily.Step(
            name="AI Stock Report",
            cmd=[sys.executable, "-c", "raise SystemExit(1)"],
            timeout_seconds=1,
            required_mode="full_real",
        ),
        step_num=1,
        total=1,
    )

    assert result.ok is False
    assert result.returncode == 1
    assert result.stdout_tail == []
    assert result.stderr_tail == []
    assert result.error == ""


def test_preflight_classifies_missing_api_as_data_degraded(monkeypatch):
    monkeypatch.setattr(run_daily, "_check_tcp_port", lambda host, port, timeout=2.0: port == 7899)
    monkeypatch.setattr(run_daily, "_check_http_health", lambda url, timeout=5: (False, "connection refused"))
    monkeypatch.setattr(run_daily, "_check_llm_configured", lambda: True)

    preflight = run_daily.run_preflight("http://127.0.0.1:8000")

    assert preflight["run_mode"] == "data_degraded"
    assert preflight["stockdb_available"] is True
    assert preflight["api_available"] is False
    assert "api_unavailable" in preflight["degradation_flags"]


def test_preflight_flags_stale_market_data_date(monkeypatch):
    monkeypatch.setattr(run_daily, "_check_tcp_port", lambda host, port, timeout=2.0: True)
    monkeypatch.setattr(
        run_daily,
        "_check_http_health",
        lambda url, timeout=5: (True, json.dumps({"latest_daily_date": "20260707"})),
    )
    monkeypatch.setattr(run_daily, "_check_llm_configured", lambda: True)

    preflight = run_daily.run_preflight("http://127.0.0.1:8000", as_of="2026-07-08")

    assert preflight["data_freshness"]["latest_data_date"] == "2026-07-07"
    assert preflight["data_freshness"]["status"] == "stale"
    assert "data_stale" in preflight["degradation_flags"]


def test_write_daily_run_report_records_steps_and_preflight(tmp_path):
    preflight = {
        "run_mode": "data_degraded",
        "stockdb_available": True,
        "api_available": False,
        "llm_configured": True,
        "degradation_flags": ["api_unavailable"],
        "details": {"api": "connection refused"},
    }
    step_results = [
        run_daily.StepResult(
            name="Unified Pipeline",
            ok=False,
            returncode=None,
            duration_seconds=600.0,
            timeout_seconds=600,
            timed_out=True,
            stdout_tail=["starting"],
            stderr_tail=["connection refused"],
            error="",
        )
    ]

    paths = run_daily.write_daily_run_report(
        as_of="2026-07-08",
        started_at="2026-07-08T18:00:00",
        finished_at="2026-07-08T18:10:00",
        elapsed_seconds=600.0,
        preflight=preflight,
        step_results=step_results,
        output_root=tmp_path,
    )

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    markdown = paths["md"].read_text(encoding="utf-8")

    assert payload["preflight"]["run_mode"] == "data_degraded"
    assert payload["summary"]["failed"] == 1
    assert payload["steps"][0]["timed_out"] is True
    assert "api_unavailable" in markdown
    assert "Unified Pipeline" in markdown


def test_check_artifact_consistency_flags_fresh_stale_and_missing(tmp_path):
    as_of = "2026-07-08"
    started = datetime.now() - timedelta(minutes=10)
    old = started - timedelta(minutes=5)
    fresh = started + timedelta(minutes=1)

    unified_json = tmp_path / "reports" / "unified" / as_of / "unified_report.json"
    bridge_json = tmp_path / "reports" / "agent_bridge" / as_of / "daily_bridge_report.json"
    unified_json.parent.mkdir(parents=True)
    bridge_json.parent.mkdir(parents=True)
    unified_json.write_text("{}", encoding="utf-8")
    bridge_json.write_text("{}", encoding="utf-8")
    os.utime(unified_json, (fresh.timestamp(), fresh.timestamp()))
    os.utime(bridge_json, (old.timestamp(), old.timestamp()))

    checks = run_daily.check_artifact_consistency(
        as_of=as_of,
        started_at=started.isoformat(timespec="seconds"),
        quick=False,
        skip_agent=False,
        project_root=tmp_path,
    )

    by_path = {c["path"]: c for c in checks}
    assert by_path[f"reports/unified/{as_of}/unified_report.json"]["status"] == "fresh"
    assert by_path[f"reports/agent_bridge/{as_of}/daily_bridge_report.json"]["status"] == "stale"
    assert by_path[f"reports/agent_bridge/{as_of}/daily_bridge_report.md"]["status"] == "missing"


def test_write_daily_run_report_includes_artifact_checks(tmp_path):
    artifact_checks = [
        {
            "path": "reports/unified/2026-07-08/unified_report.json",
            "status": "stale",
            "exists": True,
            "fresh": False,
            "mtime": "2026-07-08T14:44:00",
        }
    ]

    paths = run_daily.write_daily_run_report(
        as_of="2026-07-08",
        started_at="2026-07-08T18:00:00",
        finished_at="2026-07-08T18:10:00",
        elapsed_seconds=600.0,
        preflight={"run_mode": "data_degraded", "degradation_flags": []},
        step_results=[],
        artifact_checks=artifact_checks,
        output_root=tmp_path,
    )

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    markdown = paths["md"].read_text(encoding="utf-8")

    assert payload["artifact_consistency"][0]["status"] == "stale"
    assert "Artifact Consistency" in markdown
    assert "stale" in markdown


def test_write_daily_run_report_includes_report_date_checks(tmp_path):
    report_date_checks = [
        {
            "path": "reports/unified/2026-07-08/unified_report.json",
            "status": "mismatch",
            "payload_date": "2026-07-07",
            "expected_date": "2026-07-08",
        }
    ]

    paths = run_daily.write_daily_run_report(
        as_of="2026-07-08",
        started_at="2026-07-08T18:00:00",
        finished_at="2026-07-08T18:10:00",
        elapsed_seconds=600.0,
        preflight={"run_mode": "data_degraded", "degradation_flags": []},
        step_results=[],
        report_date_checks=report_date_checks,
        output_root=tmp_path,
    )

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    markdown = paths["md"].read_text(encoding="utf-8")

    assert payload["report_date_consistency"][0]["status"] == "mismatch"
    assert "Report Date Consistency" in markdown
    assert "2026-07-07" in markdown


def test_summarize_artifact_checks_counts_problem_states():
    checks = [
        {"status": "fresh"},
        {"status": "stale"},
        {"status": "missing"},
        {"status": "missing"},
    ]

    summary = run_daily.summarize_artifact_checks(checks)

    assert summary == {"fresh": 1, "stale": 1, "missing": 2, "total": 4}


def test_main_can_fail_on_stale_artifacts(monkeypatch, tmp_path):
    step = run_daily.Step("Unified Pipeline", [sys.executable, "-c", "pass"])
    result = run_daily.StepResult(
        name=step.name,
        ok=True,
        returncode=0,
        duration_seconds=1.0,
        timeout_seconds=step.timeout_seconds,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_daily.py", "--as-of", "2026-07-08", "--quick", "--fail-on-stale-artifact"],
    )
    monkeypatch.setattr(
        run_daily,
        "run_preflight",
        lambda api_url, as_of=None: {
            "run_mode": "data_degraded",
            "stockdb_available": True,
            "api_available": True,
            "llm_configured": False,
            "degradation_flags": [],
        },
    )
    monkeypatch.setattr(run_daily, "build_steps", lambda date, py, quick=False, skip_agent=False: [step])
    monkeypatch.setattr(run_daily, "run_step", lambda step, step_num, total: result)
    monkeypatch.setattr(
        run_daily,
        "check_artifact_consistency",
        lambda *args, **kwargs: [{"path": "reports/unified/2026-07-08/unified_report.json", "status": "stale"}],
    )
    monkeypatch.setattr(
        run_daily,
        "write_daily_run_report",
        lambda *args, **kwargs: {"json": tmp_path / "daily.json", "md": tmp_path / "daily.md"},
    )

    try:
        run_daily.main()
    except SystemExit as exc:
        assert exc.code == 3
    else:
        raise AssertionError("main() should exit when stale artifacts are fatal")


def test_main_preflight_only_exits_before_running_steps(monkeypatch):
    called = {"build_steps": False}

    monkeypatch.setattr(sys, "argv", ["run_daily.py", "--as-of", "2026-07-08", "--preflight-only"])
    monkeypatch.setattr(
        run_daily,
        "run_preflight",
        lambda api_url, as_of=None: {
            "run_mode": "full_real",
            "stockdb_available": True,
            "api_available": True,
            "llm_configured": True,
            "degradation_flags": [],
        },
    )

    def fake_build_steps(*args, **kwargs):
        called["build_steps"] = True
        return []

    monkeypatch.setattr(run_daily, "build_steps", fake_build_steps)

    try:
        run_daily.main()
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("main() should exit in preflight-only mode")
    assert called["build_steps"] is False


def test_main_dry_run_lists_steps_without_running_them(monkeypatch, tmp_path):
    step = run_daily.Step("Unified Pipeline", [sys.executable, "-c", "pass"])

    monkeypatch.setattr(sys, "argv", ["run_daily.py", "--as-of", "2026-07-08", "--quick", "--dry-run"])
    monkeypatch.setattr(
        run_daily,
        "run_preflight",
        lambda api_url, as_of=None: {
            "run_mode": "data_degraded",
            "stockdb_available": True,
            "api_available": True,
            "llm_configured": False,
            "degradation_flags": [],
        },
    )
    monkeypatch.setattr(run_daily, "build_steps", lambda date, py, quick=False, skip_agent=False: [step])
    monkeypatch.setattr(run_daily, "run_step", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("run_step called")))
    monkeypatch.setattr(run_daily, "write_daily_run_report", lambda *args, **kwargs: {"json": tmp_path / "x.json", "md": tmp_path / "x.md"})

    try:
        run_daily.main()
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("main() should exit in dry-run mode")


def test_write_artifact_manifest_records_steps_and_artifacts(tmp_path):
    step = run_daily.Step("Unified Pipeline", [sys.executable, "unified_pipeline.py"], timeout_seconds=900)
    result = run_daily.StepResult(
        name="Unified Pipeline",
        ok=True,
        returncode=0,
        duration_seconds=12.0,
        timeout_seconds=900,
    )
    artifact_checks = [
        {
            "path": "reports/unified/2026-07-08/unified_report.json",
            "status": "fresh",
            "exists": True,
            "fresh": True,
            "mtime": "2026-07-08T18:01:00",
        }
    ]

    manifest_path = run_daily.write_artifact_manifest(
        as_of="2026-07-08",
        started_at="2026-07-08T18:00:00",
        finished_at="2026-07-08T18:02:00",
        preflight={"run_mode": "data_degraded"},
        steps=[step],
        step_results=[result],
        artifact_checks=artifact_checks,
        output_root=tmp_path,
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["as_of"] == "2026-07-08"
    assert payload["steps"][0]["cmd"] == [sys.executable, "unified_pipeline.py"]
    assert payload["step_results"][0]["ok"] is True
    assert payload["artifact_summary"]["fresh"] == 1
    assert payload["artifacts"][0]["status"] == "fresh"


def test_check_report_date_consistency_flags_payload_mismatch(tmp_path):
    as_of = "2026-07-08"
    report_path = tmp_path / "reports" / "unified" / as_of / "unified_report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps({"as_of": "2026-07-07"}), encoding="utf-8")

    checks = run_daily.check_report_date_consistency(as_of, project_root=tmp_path)

    by_path = {item["path"]: item for item in checks}
    unified = by_path[f"reports/unified/{as_of}/unified_report.json"]
    assert unified["status"] == "mismatch"
    assert unified["payload_date"] == "2026-07-07"
