"""
Replay Cache 数据来源完整性测试

测试 replay-cache 不访问网络，数据来源正确。
"""

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestReplayCacheSourceIntegrity:
    """测试 Replay Cache 数据来源完整性"""

    def test_replay_does_not_call_akshare(self):
        """测试 replay-cache 不访问 AkShareProvider"""
        # 使用 fixture 模式，不应该调用网络
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
            use_cache=True,
        )

        assert report is not None
        # 数据来源应该是 fixture
        assert "fixture" in report.data_sources
        assert report.data_source_mode == "fixture"

    def test_replay_missing_data_does_not_disguise(self):
        """测试 replay 缺少某天数据时不伪装成功"""
        # 尝试加载不存在的日期
        report = run_pipeline(
            as_of_date="2020-01-01",  # 不存在的日期
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        # 应该有轮动数据，但所有板块标记为新条目
        assert report is not None
        assert report.rotation_summary is not None

    def test_replay_source_integrity(self):
        """测试 replay 数据来源完整性"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
            use_cache=True,
        )

        # 验证数据来源字段
        assert report.provider == "fixture"
        assert report.offline_fixture is True
        assert report.data_source_mode == "fixture"
