"""
板块历史数据分析测试

测试分析器功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.analysis.sector_history_analyzer import (
    SectorHistoryAnalyzer,
    save_analysis_report,
)
from theme_sector_radar.models import SectorType


class TestSectorHistoryAnalyzer:
    """测试板块历史数据分析器"""

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)
            assert analyzer.data_cache_dir == tmpdir

    def test_calculate_metrics_empty(self):
        """测试空数据指标计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)
            metrics = analyzer.calculate_metrics([])

            assert metrics["return_1d"] is None
            assert metrics["return_3d"] is None
            assert metrics["return_5d"] is None
            assert metrics["max_drawdown_5d"] is None
            assert metrics["consecutive_up_days"] == 0

    def test_calculate_metrics_with_data(self):
        """测试有数据的指标计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)

            records = [
                {"close": 100, "change_pct": 1.0},
                {"close": 102, "change_pct": 2.0},
                {"close": 101, "change_pct": -1.0},
                {"close": 103, "change_pct": 2.0},
                {"close": 105, "change_pct": 1.94},
                {"close": 107, "change_pct": 1.90},  # 需要 6 个数据点才能计算 5 日涨幅
            ]

            metrics = analyzer.calculate_metrics(records)

            assert metrics["return_1d"] is not None
            assert metrics["return_3d"] is not None
            assert metrics["return_5d"] is not None
            assert metrics["data_points"] == 6

    def test_calculate_return(self):
        """测试涨幅计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)

            closes = [100, 102, 101, 103, 105]

            # 1 日涨幅: (105-103)/103 * 100 = 1.94
            ret_1d = analyzer._calculate_return(closes, 1)
            assert ret_1d == 1.94

            # 3 日涨幅: (105-102)/102 * 100 = 2.94
            ret_3d = analyzer._calculate_return(closes, 3)
            assert ret_3d == 2.94

            # 5 日涨幅（数据不足，需要 6 个点）
            ret_5d = analyzer._calculate_return(closes, 5)
            assert ret_5d is None

    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)

            # 有回撤的数据
            closes = [100, 110, 105, 115, 110]

            drawdown = analyzer._calculate_max_drawdown(closes, 5)
            assert drawdown is not None
            assert drawdown > 0  # 应该有回撤

    def test_calculate_consecutive_up(self):
        """测试连续上涨天数计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)

            # 连续上涨
            change_pcts = [1.0, 2.0, 1.5, 0.5]
            consecutive = analyzer._calculate_consecutive_up(change_pcts)
            assert consecutive == 4

            # 中间有下跌
            change_pcts2 = [1.0, -0.5, 1.5, 0.5]
            consecutive2 = analyzer._calculate_consecutive_up(change_pcts2)
            assert consecutive2 == 2

    def test_list_available_sectors(self):
        """测试列出可用板块"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)

            # 创建测试数据
            industry_dir = os.path.join(tmpdir, "sector_history", "industry")
            os.makedirs(industry_dir)
            with open(os.path.join(industry_dir, "test1.json"), "w") as f:
                json.dump({"sector_name": "test1"}, f)
            with open(os.path.join(industry_dir, "test2.json"), "w") as f:
                json.dump({"sector_name": "test2"}, f)

            sectors = analyzer.list_available_sectors(SectorType.INDUSTRY)
            assert len(sectors) == 2
            assert "test1" in sectors
            assert "test2" in sectors

    def test_filter_candidates(self):
        """测试候选筛选"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorHistoryAnalyzer(data_cache_dir=tmpdir)

            results = [
                {
                    "sector_name": "A",
                    "metrics": {"return_5d": 5.0, "max_drawdown_5d": 3.0, "consecutive_up_days": 3, "data_points": 5},
                },
                {
                    "sector_name": "B",
                    "metrics": {"return_5d": -2.0, "max_drawdown_5d": 10.0, "consecutive_up_days": 0, "data_points": 5},
                },
                {
                    "sector_name": "C",
                    "metrics": {"return_5d": 3.0, "max_drawdown_5d": 25.0, "consecutive_up_days": 2, "data_points": 5},
                },
            ]

            # 筛选
            candidates = analyzer.filter_candidates(
                results,
                min_return_5d=0.0,
                max_drawdown_5d=20.0,
                min_consecutive_up=1,
            )

            # A 应该被选中（return_5d=5.0, drawdown=3.0, consecutive=3）
            # B 不应被选中（return_5d=-2.0 < 0）
            # C 不应被选中（drawdown=25.0 > 20）
            assert len(candidates) == 1
            assert candidates[0]["sector_name"] == "A"

    def test_save_analysis_report(self):
        """测试保存分析报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = {
                "sector_type": "industry",
                "start_date": "2026-06-23",
                "end_date": "2026-06-30",
                "generated_at": "2026-06-29T10:00:00",
                "total_sectors": 5,
                "top_by_return_5d": [],
                "top_by_max_drawdown": [],
                "top_by_consecutive_up": [],
                "candidates": [],
                "candidate_count": 0,
            }

            save_analysis_report(report, tmpdir)

            assert os.path.exists(os.path.join(tmpdir, "sector_analysis.json"))
            assert os.path.exists(os.path.join(tmpdir, "sector_analysis.md"))

    def test_analysis_md_has_required_sections(self):
        """测试分析 Markdown 包含必要章节"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from theme_sector_radar.analysis.sector_history_analyzer import _generate_analysis_md

            report = {
                "sector_type": "industry",
                "start_date": "2026-06-23",
                "end_date": "2026-06-30",
                "generated_at": "2026-06-29T10:00:00",
                "total_sectors": 5,
                "top_by_return_5d": [],
                "top_by_max_drawdown": [],
                "top_by_consecutive_up": [],
                "candidates": [],
                "candidate_count": 0,
            }

            md = _generate_analysis_md(report)

            assert "Sector History Analysis Report" in md
            assert "Top 10 by 5-Day Return" in md
            assert "Candidate Sectors" in md
            assert "Disclaimer" in md

    def test_analysis_md_no_stock_recommendation(self):
        """测试分析 Markdown 不包含个股推荐"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from theme_sector_radar.analysis.sector_history_analyzer import _generate_analysis_md

            report = {
                "sector_type": "industry",
                "start_date": "2026-06-23",
                "end_date": "2026-06-30",
                "generated_at": "2026-06-29T10:00:00",
                "total_sectors": 5,
                "top_by_return_5d": [],
                "top_by_max_drawdown": [],
                "top_by_consecutive_up": [],
                "candidates": [],
                "candidate_count": 0,
            }

            md = _generate_analysis_md(report)

            # 检查包含免责声明
            assert "does not constitute individual stock recommendations" in md.lower()
            assert "buy/sell advice" in md.lower()
