"""
运行脚本契约测试

测试 PowerShell 脚本存在性和内容。
"""

import os

import pytest


class TestRunScriptsContract:
    """测试运行脚本契约"""

    def test_run_daily_ps1_exists(self):
        """测试 run_daily.ps1 存在"""
        script_path = "scripts/run_daily.ps1"
        assert os.path.exists(script_path), f"脚本不存在: {script_path}"

    def test_run_daily_fixture_ps1_exists(self):
        """测试 run_daily_fixture.ps1 存在"""
        script_path = "scripts/run_daily_fixture.ps1"
        assert os.path.exists(script_path), f"脚本不存在: {script_path}"

    def test_run_daily_ps1_contains_cli(self):
        """测试 run_daily.ps1 包含 CLI 命令"""
        script_path = "scripts/run_daily.ps1"
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查包含 CLI 参数
        assert "theme_sector_radar.cli" in content or "theme_sector_radar" in content

    def test_run_daily_fixture_ps1_contains_offline_fixture(self):
        """测试 run_daily_fixture.ps1 包含 --offline-fixture"""
        script_path = "scripts/run_daily_fixture.ps1"
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "offline-fixture" in content

    def test_run_daily_fixture_ps1_contains_cli(self):
        """测试 run_daily_fixture.ps1 包含 CLI 命令"""
        script_path = "scripts/run_daily_fixture.ps1"
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查包含 CLI 参数
        assert "theme_sector_radar.cli" in content or "theme_sector_radar" in content
