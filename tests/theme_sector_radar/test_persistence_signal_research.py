"""
持续性信号研究测试

测试 persistence_signal_research.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.persistence_signal_research import PersistenceSignalResearch
from theme_sector_radar.reports.persistence_signal_report import (
    generate_persistence_signal_report,
    save_persistence_signal_report,
)


class TestPersistenceSignalResearch:
    """测试 PersistenceSignalResearch"""

    def _create_mock_data(self, tmpdir: str):
        """创建模拟数据"""
        # 创建 sector_history
        history_dir = os.path.join(tmpdir, "sector_history", "industry")
        os.makedirs(history_dir)

        for name in ["半导体", "电子化学品"]:
            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(10, 30)
                ],
            }
            with open(os.path.join(history_dir, f"{name}.json"), "w") as f:
                json.dump(history_data, f)

        # 创建 sector_research（5 天数据，确保有足够样本）
        labels = ["low_signal_noise", "low_signal_noise", "short_term_active_unconfirmed",
                  "short_term_active_unconfirmed", "oversold_rebound_candidate"]
        for i, date in enumerate(["2026-06-18", "2026-06-19", "2026-06-20", "2026-06-21", "2026-06-22"]):
            report_dir = os.path.join(tmpdir, "sector_research", date)
            os.makedirs(report_dir)

            data = {
                "as_of_date": date,
                "daily_summary": {
                    "market_regime": "choppy_market",
                    "top_watch_names": ["半导体"] if i < 3 else [],
                },
                "research_results": [
                    {
                        "sector_name": "半导体",
                        "consensus_label": labels[i],
                        "ranking_score": 0.3 + i * 0.05,
                        "opportunity_score": 0.2 + i * 0.03,
                        "confidence_score": 0.6,
                    },
                ],
            }
            with open(os.path.join(report_dir, "sector_research.json"), "w") as f:
                json.dump(data, f)

    def test_run_analysis_basic(self):
        """测试基本分析"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-20",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            assert result["total_samples"] > 0
            assert result["sectors_covered"] > 0

    def test_top_watch_streak(self):
        """测试 top_watch_streak 计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-20",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            streak = result.get("streak_performance", {})
            assert len(streak) > 0

    def test_label_persistence(self):
        """测试 label_persistence 计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-18",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            label_perf = result.get("label_persistence_performance", {})
            # 至少有 low_signal_noise persistence
            assert len(label_perf) > 0

    def test_label_transition(self):
        """测试 label_transition 识别"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-18",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            transitions = result.get("label_transition_performance", {})
            # 半导体有标签变化
            assert len(transitions) > 0

    def test_trend_performance(self):
        """测试趋势性能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-20",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            trends = result.get("trend_performance", {})
            assert len(trends) > 0

    def test_recommendation_field(self):
        """测试 recommend_persistence_agent 字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-20",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            rec = result.get("recommendation", {})
            assert "recommend_persistence_agent" in rec
            assert "reason" in rec

    def test_report_generation(self):
        """测试报告生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-20",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            md = generate_persistence_signal_report(result)
            assert "持续性信号研究报告" in md
            assert "Top Watch 连续性" in md

    def test_no_trade_advice_words(self):
        """测试不包含交易建议词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-20",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            md = generate_persistence_signal_report(result)
            trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
            for word in trade_words:
                assert word not in md.lower(), f"报告包含交易建议词: {word}"

    def test_save_report(self):
        """测试保存报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            research = PersistenceSignalResearch(history_root=os.path.join(tmpdir, "sector_history"))
            result = research.run_analysis(
                start_date="2026-06-20",
                end_date="2026-06-22",
                report_root=tmpdir,
            )

            output_dir = os.path.join(tmpdir, "output")
            save_persistence_signal_report(output_dir, result)

            assert os.path.exists(os.path.join(output_dir, "persistence_signal_analysis.json"))
            assert os.path.exists(os.path.join(output_dir, "persistence_signal_analysis.md"))
