"""
README 契约测试

测试 README 包含必要的内容。
"""

import os

import pytest


class TestReadmeContract:
    """测试 README 契约"""

    def test_readme_exists(self):
        """测试 README.md 存在"""
        assert os.path.exists("README.md"), "README.md 不存在"

    def test_readme_has_boundary(self):
        """测试 README 包含边界说明"""
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()

        # 检查包含不做个股推荐的说明
        assert "不做个股推荐" in content or "不输出个股推荐" in content

    def test_readme_has_fixture_smoke_test(self):
        """测试 README 包含 fixture smoke test 命令"""
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()

        assert "run_daily_fixture.ps1" in content or "offline-fixture" in content

    def test_readme_has_akshare_daily(self):
        """测试 README 包含 AkShare daily 命令"""
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()

        assert "provider akshare" in content or "run_daily.ps1" in content

    def test_readme_has_output_path(self):
        """测试 README 包含输出路径说明"""
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()

        assert "reports/theme_sector_radar" in content
        assert "run_log.json" in content
