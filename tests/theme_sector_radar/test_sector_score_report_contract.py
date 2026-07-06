"""
板块综合评分报告契约测试

测试 sector_score_report.py 模块的各项功能。
"""

import json

import pytest

from theme_sector_radar.reports.sector_score_report import (
    generate_sector_score_report,
    save_sector_score_report,
)


class TestSectorScoreReport:
    """测试板块综合评分报告"""

    def _create_mock_report_data(self) -> dict:
        """创建模拟报告数据"""
        return {
            "report_type": "sector_scores",
            "version": "0.1.0",
            "as_of_date": "2026-06-29",
            "updated_at": "2026-06-29T10:00:00",
            "scores": [
                {
                    "sector_name": "测试板块1",
                    "sector_type": "industry",
                    "sector_selection_score": 82.5,
                    "selection_level": "strong_watch",
                    "rotation_phase": "leading",
                    "benchmark_mode": "sector_median",
                    "radar_score": 75.0,
                    "history_days": 5,
                    "score_breakdown": {
                        "radar_score_component": 22.0,
                        "momentum_component": 18.0,
                        "relative_strength_component": 12.0,
                        "persistence_component": 12.0,
                        "drawdown_component": 8.0,
                        "volatility_component": 4.0,
                        "data_quality_component": 9.0,
                        "risk_penalty": 2.5,
                        "positive_score": 85.0,
                        "final_score": 82.5,
                    },
                    "strength_reasons": ["日报雷达分较高", "近期涨幅靠前"],
                    "risk_reasons": ["短期涨幅较大，注意回撤"],
                    "watch_points": ["观察后续是否继续跑赢行业中位数"],
                    "data_warnings": [],
                }
            ],
            "metadata": {
                "sector_type": "industry",
                "history_start_date": "2026-06-23",
                "history_end_date": "2026-06-29",
                "top_n": 20,
            },
            "disclaimer": "本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。",
        }

    def test_report_generation(self):
        """测试报告生成"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_report_contains_title(self):
        """测试报告包含标题"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert "板块综合评分" in report

    def test_report_contains_disclaimer(self):
        """测试报告包含免责声明"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert "免责声明" in report
        assert "不作为个股操作依据" in report

    def test_report_contains_weights(self):
        """测试报告包含权重说明"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert "评分权重" in report
        assert "radar_score_component" in report
        assert "momentum_component" in report

    def test_report_contains_level_rules(self):
        """测试报告包含等级规则"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert "等级规则" in report
        assert "strong_watch" in report
        assert "watch" in report
        assert "neutral" in report
        assert "cooling" in report
        assert "avoid" in report

    def test_report_contains_scores_table(self):
        """测试报告包含评分表"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert "Top" in report
        assert "综合评分" in report
        assert "测试板块1" in report

    def test_report_contains_score_details(self):
        """测试报告包含评分明细"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert "评分详情" in report
        # 新版报告使用"趋势 breakdown"和"短线 breakdown"
        assert "趋势" in report
        assert "短线" in report

    def test_report_contains_rotation_stats(self):
        """测试报告包含轮动统计"""
        # 新版报告不再包含轮动阶段统计，但包含双评分说明
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        assert "双评分说明" in report

    def test_report_no_stock_recommendation(self):
        """测试报告不含个股操作结论"""
        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)
        # 检查不含 buy/sell/hold 个股建议
        assert "buy" not in report.lower()
        assert "sell" not in report.lower()
        assert "买入" not in report
        assert "卖出" not in report
        # 注意: "持有" 可能出现在"中长期趋势观察价值较高"等描述中，这是允许的

    def test_save_report(self):
        """测试保存报告"""
        import tempfile
        import os

        report_data = self._create_mock_report_data()
        report = generate_sector_score_report(report_data)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_report.md")
            save_sector_score_report(report, filepath)
            assert os.path.exists(filepath)

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == report
