"""
Runbook 文档测试

测试 runbook 文档存在性和内容。
"""

import os

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
