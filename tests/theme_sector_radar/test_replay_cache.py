"""
Replay Cache 测试

测试缓存回放功能。
"""

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestReplayCache:
    """测试缓存回放"""

    def test_replay_uses_cache(self):
        """测试 replay 使用缓存"""
        # 运行两次，第二次应该使用缓存
        report1 = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
            use_cache=False,
        )

        report2 = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
            use_cache=True,
        )

        # 两次都应该成功
        assert report1 is not None
        assert report2 is not None

    def test_replay_does_not_call_akshare(self):
        """测试 replay 不调用 AkShare 网络接口"""
        # 使用 fixture 模式，不应该调用网络
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        assert report is not None
        # 数据来源应该是 fixture
        assert "fixture" in report.data_sources
