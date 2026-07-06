"""
CatalystEventAgent 信号验证测试

测试 catalyst_event_backtest.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.catalyst_event_backtest import CatalystEventBacktest
from theme_sector_radar.reports.catalyst_event_backtest_report import (
    generate_catalyst_event_backtest_report,
    save_catalyst_event_backtest_report,
)


class TestCatalystEventBacktest:
    """测试 CatalystEventBacktest"""

    def _create_mock_data(self, tmpdir: str):
        """创建模拟数据"""
        # 创建 sector_history
        history_dir = os.path.join(tmpdir, "sector_history", "industry")
        os.makedirs(history_dir)

        for name in ["白酒", "电池"]:
            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(15, 30)
                ],
            }
            with open(os.path.join(history_dir, f"{name}.json"), "w") as f:
                json.dump(history_data, f)

        # 创建 sector_research
        for date in ["2026-06-24", "2026-06-25"]:
            report_dir = os.path.join(tmpdir, "sector_research", date)
            os.makedirs(report_dir)

            data = {
                "as_of_date": date,
                "research_results": [
                    {
                        "sector_name": "白酒",
                        "consensus_label": "weak_or_avoid",
                        "ranking_score": 0.3,
                        "opportunity_score": 0.2,
                        "confidence_score": 0.6,
                        "market_regime": {"regime_composite_label": "choppy_market"},
                        "agent_opinions": [
                            {
                                "agent_id": "catalyst_event",
                                "label": "catalyst_observed",
                                "score": 0.4,
                                "vote": "neutral",
                                "metadata": {"decision_impact": "report_only", "matched_event_count": 2, "source_ids": ["fixture"]},
                            },
                            {
                                "agent_id": "short_term_heat",
                                "vote": "positive",
                            },
                            {
                                "agent_id": "persistence_strength",
                                "vote": "neutral",
                            },
                        ],
                    },
                ],
            }
            with open(os.path.join(report_dir, "sector_research.json"), "w") as f:
                json.dump(data, f)

        # 创建 catalyst events cache (使用正确的路径)
        for date in ["2026-06-24", "2026-06-25"]:
            cache_dir = os.path.join(tmpdir, "data_cache", "catalyst_events", date)
            os.makedirs(cache_dir)
            events_data = {
                "as_of_date": date,
                "events": [
                    {
                        "event_id": f"fixture_{date}",
                        "source": "fixture",
                        "title": "Test event",
                        "confidence": 0.8,
                        "freshness": "same_day",
                    },
                ],
            }
            with open(os.path.join(cache_dir, "events.json"), "w") as f:
                json.dump(events_data, f)

    def test_run_backtest_basic(self):
        """测试基本回测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            backtest = CatalystEventBacktest(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            assert result["total_samples"] > 0
            assert result["cache_coverage"] > 0

    def test_catalyst_label_performance(self):
        """测试 catalyst_label 统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            backtest = CatalystEventBacktest(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            label_perf = result.get("catalyst_label_performance", {})
            assert "catalyst_observed" in label_perf

    def test_missing_cache_not_fail(self):
        """测试 missing cache 不失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 只创建 sector_research，不创建 catalyst cache
            report_dir = os.path.join(tmpdir, "sector_research", "2026-06-24")
            os.makedirs(report_dir)
            data = {
                "as_of_date": "2026-06-24",
                "research_results": [{
                    "sector_name": "白酒",
                    "consensus_label": "weak_or_avoid",
                    "ranking_score": 0.3,
                    "opportunity_score": 0.2,
                    "confidence_score": 0.6,
                    "market_regime": {"regime_composite_label": "choppy_market"},
                    "agent_opinions": [],
                }],
            }
            with open(os.path.join(report_dir, "sector_research.json"), "w") as f:
                json.dump(data, f)

            backtest = CatalystEventBacktest(
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-24",
                report_root=tmpdir,
            )

            assert result["total_samples"] > 0
            assert result["cache_coverage"] == 0

    def test_fixture标记(self):
        """测试 fixture 数据标记"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            backtest = CatalystEventBacktest(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            data_status = result.get("data_status_counts", {})
            assert data_status.get("fixture", 0) > 0

    def test_recommendation_field(self):
        """测试 recommendation 字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            backtest = CatalystEventBacktest(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            rec = result.get("recommendation", {})
            assert "recommend_vote_calibration" in rec
            assert "recommended_mode" in rec

    def test_report_generation(self):
        """测试报告生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            backtest = CatalystEventBacktest(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            md = generate_catalyst_event_backtest_report(result)
            assert "CatalystEventAgent 信号验证报告" in md
            assert "Catalyst Label 表现" in md

    def test_no_trade_advice_words(self):
        """测试不包含交易建议词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            backtest = CatalystEventBacktest(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            md = generate_catalyst_event_backtest_report(result)
            trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
            for word in trade_words:
                assert word not in md.lower(), f"报告包含交易建议词: {word}"

    def test_save_report(self):
        """测试保存报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            backtest = CatalystEventBacktest(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "data_cache", "catalyst_events"),
            )
            result = backtest.run_backtest(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            output_dir = os.path.join(tmpdir, "output")
            save_catalyst_event_backtest_report(output_dir, result)

            assert os.path.exists(os.path.join(output_dir, "catalyst_event_backtest.json"))
            assert os.path.exists(os.path.join(output_dir, "catalyst_event_backtest.md"))
