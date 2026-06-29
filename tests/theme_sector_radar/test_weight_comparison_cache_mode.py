"""
权重对比 Cache 模式测试

测试 cache 模式行为。
"""

import pytest

from theme_sector_radar.experiments.weight_comparison import generate_input_snapshot


class TestWeightComparisonCacheMode:
    """测试权重对比 Cache 模式"""

    def test_cache_mode_does_not_access_network(self):
        """测试 cache 模式不访问网络"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                # 尝试使用不存在的缓存
                generate_input_snapshot(
                    as_of_date="2020-01-01",
                    output_dir=tmpdir,
                    offline_fixture=False,
                    use_cache=True,
                )

    def test_cache_mode_requires_existing_cache(self):
        """测试 cache 模式需要已存在的缓存"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # cache 模式应该失败，因为没有缓存
            with pytest.raises(FileNotFoundError) as exc_info:
                generate_input_snapshot(
                    as_of_date="2020-01-01",
                    output_dir=tmpdir,
                    offline_fixture=False,
                    use_cache=True,
                )

            assert "缓存快照" in str(exc_info.value)
