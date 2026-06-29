"""
权重实验输入快照完整性测试

测试 input_snapshot 生成和哈希计算。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.experiments.weight_comparison import (
    calculate_file_hash,
    generate_input_snapshot,
)


class TestWeightSnapshotIntegrity:
    """测试权重实验输入快照完整性"""

    def test_fixture_generates_input_snapshot(self):
        """测试 fixture 实验生成 input_snapshot.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = generate_input_snapshot(
                as_of_date="2026-06-28",
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            assert os.path.exists(snapshot_path)
            assert snapshot_path.endswith("input_snapshot.json")

    def test_input_snapshot_hash_is_real(self):
        """测试 input_snapshot_hash 是真实文件 hash"""
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = generate_input_snapshot(
                as_of_date="2026-06-28",
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            hash_value = calculate_file_hash(snapshot_path)

            # 应该是 32 位 MD5 哈希
            assert len(hash_value) == 32
            assert hash_value != "file_not_found"

    def test_input_snapshot_hash_consistent(self):
        """测试 input_snapshot_hash 一致性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = generate_input_snapshot(
                as_of_date="2026-06-28",
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            hash1 = calculate_file_hash(snapshot_path)
            hash2 = calculate_file_hash(snapshot_path)

            assert hash1 == hash2

    def test_input_snapshot_has_required_fields(self):
        """测试 input_snapshot 包含必要字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = generate_input_snapshot(
                as_of_date="2026-06-28",
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)

            assert "as_of_date" in snapshot
            assert "generated_at" in snapshot
            assert "source" in snapshot
            assert "industry_sectors" in snapshot
            assert "concept_sectors" in snapshot

    def test_cache_mode_fails_without_cache(self):
        """测试 cache 模式找不到缓存时失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                generate_input_snapshot(
                    as_of_date="2020-01-01",  # 不存在的日期
                    output_dir=tmpdir,
                    offline_fixture=False,
                    use_cache=True,
                )
