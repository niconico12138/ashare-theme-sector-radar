"""
权重对比实验测试

测试权重对比实验功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.experiments.weight_comparison import (
    calculate_file_hash,
    compare_results,
    generate_comparison_report,
    generate_comparison_md,
    generate_recommendation,
    generate_input_snapshot,
    load_weight_config,
)


class TestWeightComparisonExperiment:
    """测试权重对比实验"""

    def test_calculate_file_hash(self):
        """测试文件哈希计算"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            hash1 = calculate_file_hash(temp_path)
            hash2 = calculate_file_hash(temp_path)

            # 同一文件哈希应该相同
            assert hash1 == hash2
            assert len(hash1) == 32  # MD5 哈希长度
        finally:
            os.unlink(temp_path)

    def test_calculate_file_hash_nonexistent(self):
        """测试不存在文件的哈希抛出异常"""
        with pytest.raises(FileNotFoundError):
            calculate_file_hash("nonexistent_file.txt")

    def test_load_weight_config(self):
        """测试加载权重配置"""
        config = load_weight_config("config/experiments/weights_baseline.json")

        assert "industry_weights" in config
        assert "concept_weights" in config
        assert "name" in config

    def test_generate_input_snapshot(self):
        """测试生成 input_snapshot"""
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = generate_input_snapshot(
                as_of_date="2026-06-28",
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            assert os.path.exists(snapshot_path)

            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)

            assert "industry_sectors" in snapshot
            assert "concept_sectors" in snapshot

    def test_compare_results(self):
        """测试结果对比"""
        baseline = {
            "industry_top": [
                {"name": "A", "score": 90, "focus_level": "focus", "risk_level": "low"},
                {"name": "B", "score": 85, "focus_level": "watch", "risk_level": "low"},
            ],
            "concept_top": [
                {"name": "X", "score": 80, "focus_level": "focus", "risk_level": "low"},
            ],
        }

        alternative = {
            "industry_top": [
                {"name": "A", "score": 88, "focus_level": "watch", "risk_level": "low"},
                {"name": "C", "score": 82, "focus_level": "focus", "risk_level": "low"},
            ],
            "concept_top": [
                {"name": "X", "score": 82, "focus_level": "focus", "risk_level": "low"},
                {"name": "Y", "score": 78, "focus_level": "watch", "risk_level": "low"},
            ],
        }

        diff = compare_results(baseline, alternative, "test_alt")

        assert diff["industry_top_changes"]["overlap_count"] == 1
        assert "B" in diff["industry_top_changes"]["only_in_baseline"]
        assert "C" in diff["industry_top_changes"]["only_in_alternative"]

    def test_generate_recommendation_fixture(self):
        """测试生成推荐（fixture 模式）"""
        recommendation = generate_recommendation(
            baseline={},
            capital_focused={},
            trend_focused={},
            is_fixture=True,
        )

        assert recommendation["recommendation"] == "need_more_data"

    def test_generate_comparison_report(self):
        """测试生成对比报告"""
        report = generate_comparison_report(
            as_of_date="2026-06-28",
            input_snapshot_path="test_snapshot.json",
            input_snapshot_hash="abc123def456",
            input_snapshot_source="fixture",
            weight_configs=[],
            results={},
            diff={},
            recommendation={"recommendation": "need_more_data", "reasons": []},
        )

        assert report["as_of_date"] == "2026-06-28"
        assert "input_snapshot_hash" in report
        assert report["input_snapshot_source"] == "fixture"

    def test_generate_comparison_md(self):
        """测试生成对比报告 Markdown"""
        report = {
            "as_of_date": "2026-06-28",
            "generated_at": "2026-06-29T10:00:00",
            "input_snapshot_path": "test.json",
            "input_snapshot_hash": "abc123def456",
            "input_snapshot_source": "fixture",
            "weight_configs": [
                {"name": "baseline", "description": "baseline", "industry_weights": {"capital_flow": 0.25, "trend_strength": 0.25}},
            ],
            "results": {
                "baseline": {"industry_top": [{"name": "A"}], "concept_top": [{"name": "X"}]},
                "capital_focused": {"industry_top": [{"name": "A"}], "concept_top": [{"name": "X"}]},
                "trend_focused": {"industry_top": [{"name": "A"}], "concept_top": [{"name": "X"}]},
            },
            "diff": {
                "industry_top_changes": {"overlap_rate": 1.0},
                "concept_top_changes": {"overlap_rate": 1.0},
                "focus_level_changes": [],
                "risk_level_changes": [],
            },
            "recommendation": {"recommendation": "need_more_data", "reasons": ["test"]},
        }

        md = generate_comparison_md(report)

        assert "权重实验对比报告" in md
        assert "实验输入" in md
        assert "权重方案" in md
        assert "行业 Top N 对比" in md
