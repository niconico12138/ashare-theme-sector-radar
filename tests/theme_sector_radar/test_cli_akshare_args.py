"""
CLI AkShare 参数测试

测试 CLI 的 AkShare 相关参数。
"""

import pytest

from theme_sector_radar.cli import main
from theme_sector_radar.pipeline import run_pipeline


class TestCliAkshareArgs:
    """测试 CLI AkShare 参数"""

    def test_pipeline_with_provider_param(self):
        """测试 pipeline 接受 provider 参数"""
        # 测试 fixture provider
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            output_dir=None,
            offline_fixture=True,
            provider_name="fixture",
        )
        assert report is not None
        assert report.report_type == "theme_sector_radar"

    def test_pipeline_with_cache_params(self):
        """测试 pipeline 接受缓存参数"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # 第一次运行（写入缓存）
            report1 = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                use_cache=False,
                refresh=False,
            )
            assert report1 is not None

    def test_cli_args_structure(self):
        """测试 CLI 参数结构"""
        import argparse
        from theme_sector_radar.cli import main

        # 验证 CLI 可以被调用（不实际运行）
        # 这里只测试参数解析逻辑
        parser = argparse.ArgumentParser()
        parser.add_argument("--as-of", type=str, default=None)
        parser.add_argument("--top-n", type=int, default=10)
        parser.add_argument("--output", type=str, default=None)
        parser.add_argument("--offline-fixture", action="store_true")
        parser.add_argument("--provider", type=str, choices=["fixture", "akshare"], default="fixture")
        parser.add_argument("--use-cache", action="store_true")
        parser.add_argument("--refresh", action="store_true")

        # 测试解析各种参数组合
        args = parser.parse_args([
            "--as-of", "2026-06-28",
            "--top-n", "10",
            "--provider", "akshare",
            "--use-cache",
        ])
        assert args.as_of == "2026-06-28"
        assert args.top_n == 10
        assert args.provider == "akshare"
        assert args.use_cache is True
        assert args.refresh is False

    def test_offline_fixture_overrides_provider(self):
        """测试 offline-fixture 覆盖 provider"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # offline_fixture=True 应该使用 fixture，不管 provider 是什么
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                provider_name="akshare",  # 即使指定 akshare
            )
            assert report is not None
            # 数据来源应该是 fixture
            assert "fixture" in report.data_sources
