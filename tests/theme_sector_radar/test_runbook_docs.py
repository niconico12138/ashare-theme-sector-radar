"""
Runbook 文档测试

测试 runbook 文档存在性和内容。
"""

import os
from pathlib import Path

import pytest


class TestRunbookDocs:
    """测试 Runbook 文档"""

    def test_daily_workflow_exists(self):
        """测试 daily_workflow.md 存在"""
        doc_path = "docs/runbooks/daily_workflow.md"
        assert os.path.exists(doc_path), f"文档不存在: {doc_path}"

    def test_windows_task_scheduler_exists(self):
        """测试 windows_task_scheduler.md 存在"""
        doc_path = "docs/runbooks/windows_task_scheduler.md"
        assert os.path.exists(doc_path), f"文档不存在: {doc_path}"

    def test_troubleshooting_exists(self):
        """测试 troubleshooting.md 存在"""
        doc_path = "docs/runbooks/troubleshooting.md"
        assert os.path.exists(doc_path), f"文档不存在: {doc_path}"

    def test_windows_task_scheduler_no_auto_create(self):
        """测试 windows_task_scheduler.md 明确不自动创建任务计划"""
        doc_path = "docs/runbooks/windows_task_scheduler.md"
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "不会自动创建" in content or "不会自动" in content

    def test_troubleshooting_has_proxy_error(self):
        """测试 troubleshooting.md 包含 ProxyError"""
        doc_path = "docs/runbooks/troubleshooting.md"
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "ProxyError" in content

    def test_troubleshooting_has_fixture_smoke_test(self):
        """测试 troubleshooting.md 包含 fixture smoke test"""
        doc_path = "docs/runbooks/troubleshooting.md"
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "fixture" in content.lower() and "smoke" in content.lower()

    def test_research_plans_reference_current_runnable_entrypoints(self):
        root = Path("docs/superpowers/plans")
        risk = (root / "2026-07-13-risk-first-dual-exit-validation.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "--candidate-source-root",
            "--bar-interval 1m",
            "--bar-interval 5m",
            "--trading-calendar-path",
            "--selection-validation-root",
            "--entry-bars-manifest",
            "--expected-entry-bars-manifest-sha256",
        ):
            assert required in risk
        task_five = risk.split("### Task 5:", maxsplit=1)[1]
        assert "$env:TEMP" in task_five
        assert "reports\\timing_factor_exit" not in task_five

        stop = (root / "2026-07-13-stop-loss-negative-sample-research.md").read_text(
            encoding="utf-8"
        )
        assert "scripts/run_local_stop_loss_sample.py" in stop
        assert "tests/theme_sector_radar/test_run_local_stop_loss_sample.py" in stop
        for required in ("--stock-archive", "--codes-json", "--output-dir", "--as-of"):
            assert required in stop
        stop_task_four = stop.split("### Task 4:", maxsplit=1)[1]
        assert "scripts/run_local_stop_loss_sample.py" in stop_task_four
        assert "--candidate-root" not in stop_task_four
        assert "--selection-validation-root" not in stop_task_four

        nonstationary = (
            root / "2026-07-13-nonstationary-entry-exit-research.md"
        ).read_text(encoding="utf-8")
        assert "scripts/audit_timing_nonstationary_entry_exit_decision.py" in nonstationary
        assert (
            "tests/theme_sector_radar/test_audit_timing_nonstationary_entry_exit_decision.py"
            in nonstationary
        )
        for entrypoint in (
            "scripts/audit_timing_nonstationary_entry.py",
            "scripts/audit_timing_nonstationary_profit_exit.py",
            "scripts/audit_timing_nonstationary_stop_exit.py",
            "scripts/audit_timing_nonstationary_entry_exit_decision.py",
        ):
            assert entrypoint in nonstationary
        for required in (
            "--candidate-root",
            "--candidate-source-root",
            "--selection-validation-root",
            "--entry-records-path",
            "--records-path",
            "--trading-calendar-path",
            "--timeframe 1m",
            "--timeframe 5m",
            "--entry-1m-report",
            "--entry-5m-report",
            "--profit-1m-2-report",
            "--profit-1m-3-report",
            "--profit-5m-2-report",
            "--profit-5m-3-report",
            "--stop-1m-report",
            "--stop-5m-report",
            "--expected-entry-1m-sha256",
            "--expected-entry-5m-sha256",
            "--expected-profit-1m-2-sha256",
            "--expected-profit-1m-3-sha256",
            "--expected-profit-5m-2-sha256",
            "--expected-profit-5m-3-sha256",
            "--expected-stop-1m-sha256",
            "--expected-stop-5m-sha256",
            "--expected-calendar-path",
            "--expected-calendar-sha256",
            "--expected-records-manifest",
            "--expected-records-manifest-sha256",
        ):
            assert required in nonstationary
