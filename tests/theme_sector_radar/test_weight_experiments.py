"""
评分权重实验测试

测试权重配置和实验对比。
"""

import json
import os

import pytest


class TestWeightExperiments:
    """测试评分权重实验"""

    def test_baseline_weights_exist(self):
        """测试 baseline 权重配置存在"""
        config_path = "config/experiments/weights_baseline.json"
        assert os.path.exists(config_path), f"配置不存在: {config_path}"

    def test_baseline_weights_parseable(self):
        """测试 baseline 权重配置可解析"""
        config_path = "config/experiments/weights_baseline.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "industry_weights" in config
        assert "concept_weights" in config

    def test_baseline_weights_sum_to_one(self):
        """测试 baseline 权重之和为 1"""
        config_path = "config/experiments/weights_baseline.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        industry_sum = sum(config["industry_weights"].values())
        concept_sum = sum(config["concept_weights"].values())

        assert abs(industry_sum - 1.0) < 0.01, f"industry weights sum: {industry_sum}"
        assert abs(concept_sum - 1.0) < 0.01, f"concept weights sum: {concept_sum}"

    def test_alternative_weights_exist(self):
        """测试 alternative 权重配置存在"""
        assert os.path.exists("config/experiments/weights_capital_focused.json")
        assert os.path.exists("config/experiments/weights_trend_focused.json")

    def test_alternative_weights_differ_from_baseline(self):
        """测试 alternative 权重与 baseline 不同"""
        with open("config/experiments/weights_baseline.json", "r", encoding="utf-8") as f:
            baseline = json.load(f)

        with open("config/experiments/weights_capital_focused.json", "r", encoding="utf-8") as f:
            capital = json.load(f)

        # capital_focused 的 capital_flow 权重应该更高
        assert capital["industry_weights"]["capital_flow"] > baseline["industry_weights"]["capital_flow"]
