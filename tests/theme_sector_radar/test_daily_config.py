"""
Daily 配置测试

测试配置文件解析和字段完整性。
"""

import json
import os

import pytest


class TestDailyConfig:
    """测试 Daily 配置"""

    def test_daily_example_json_exists(self):
        """测试 daily.example.json 存在"""
        config_path = "config/daily.example.json"
        assert os.path.exists(config_path), f"配置文件不存在: {config_path}"

    def test_daily_example_json_parseable(self):
        """测试 daily.example.json 可解析"""
        config_path = "config/daily.example.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert isinstance(config, dict)

    def test_daily_example_json_has_required_fields(self):
        """测试 daily.example.json 包含必要字段"""
        config_path = "config/daily.example.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        required_fields = [
            "as_of",
            "provider",
            "refresh",
            "fallback_cache_days",
            "lookback_days",
            "report_root",
            "top_n",
            "offline_fixture",
            "fixture_profile",
            "log_root",
        ]

        for field in required_fields:
            assert field in config, f"缺少必要字段: {field}"

    def test_daily_example_json_values(self):
        """测试 daily.example.json 字段值"""
        config_path = "config/daily.example.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["as_of"] == "auto"
        assert config["provider"] == "akshare"
        assert config["refresh"] is True
        assert config["fallback_cache_days"] == 7
        assert config["lookback_days"] == 5
        assert config["top_n"] == 10
        assert config["offline_fixture"] is False
