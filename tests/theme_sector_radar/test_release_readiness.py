"""
发布前验收测试

测试 smoke test 和 degraded fixture 配置。
"""

import os

import pytest


class TestReleaseReadiness:
    """测试发布前验收"""

    def test_run_daily_fixture_uses_full_profile(self):
        """测试 run_daily_fixture.ps1 默认使用 full profile"""
        script_path = "scripts/run_daily_fixture.ps1"
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'FixtureProfile = "full"' in content

    def test_run_daily_fixture_no_network(self):
        """测试 run_daily_fixture.ps1 不访问网络"""
        script_path = "scripts/run_daily_fixture.ps1"
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "--offline-fixture" in content

    def test_run_daily_degraded_fixture_exists(self):
        """测试 degraded fixture 脚本存在"""
        script_path = "scripts/run_daily_degraded_fixture.ps1"
        assert os.path.exists(script_path), f"脚本不存在: {script_path}"

    def test_run_daily_degraded_fixture_uses_minimal(self):
        """测试 degraded fixture 脚本使用 minimal profile"""
        script_path = "scripts/run_daily_degraded_fixture.ps1"
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'FixtureProfile = "minimal"' in content
