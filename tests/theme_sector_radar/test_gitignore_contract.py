"""
.gitignore 契约测试

测试 .gitignore 包含必要的忽略规则。
"""

import os

import pytest


class TestGitignoreContract:
    """测试 .gitignore 契约"""

    def test_gitignore_exists(self):
        """测试 .gitignore 存在"""
        assert os.path.exists(".gitignore"), ".gitignore 不存在"

    def test_gitignore_ignores_daily_local_json(self):
        """测试 .gitignore 忽略 daily.local.json"""
        with open(".gitignore", "r", encoding="utf-8") as f:
            content = f.read()

        assert "daily.local.json" in content

    def test_gitignore_ignores_logs(self):
        """测试 .gitignore 忽略 logs/"""
        with open(".gitignore", "r", encoding="utf-8") as f:
            content = f.read()

        assert "logs/" in content

    def test_gitignore_ignores_data_cache(self):
        """测试 .gitignore 忽略 data_cache/"""
        with open(".gitignore", "r", encoding="utf-8") as f:
            content = f.read()

        assert "data_cache/" in content

    def test_gitignore_ignores_pycache(self):
        """测试 .gitignore 忽略 __pycache__/"""
        with open(".gitignore", "r", encoding="utf-8") as f:
            content = f.read()

        assert "__pycache__/" in content
