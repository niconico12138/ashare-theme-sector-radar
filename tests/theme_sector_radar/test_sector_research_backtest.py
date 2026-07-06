"""
Agent 组复盘评估测试

测试 sector_research_backtest.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest import SectorResearchBacktest


class TestSectorResearchBacktest:
    """测试 Agent 组复盘评估"""

    def test_compute_forward_returns(self):
        """测试计算后续表现"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟历史数据
            history_dir = os.path.join(tmpdir, "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": "2026-06-25", "收盘价": 100.0, "前收盘": 99.0},
                    {"日期": "2026-06-26", "收盘价": 102.0, "前收盘": 100.0},
                    {"日期": "2026-06-27", "收盘价": 101.0, "前收盘": 102.0},
                    {"日期": "2026-06-28", "收盘价": 103.0, "前收盘": 101.0},
                    {"日期": "2026-06-29", "收盘价": 105.0, "前收盘": 103.0},
                    {"日期": "2026-06-30", "收盘价": 107.0, "前收盘": 105.0},
                ],
            }
            with open(os.path.join(history_dir, "测试板块.json"), "w") as f:
                json.dump(history_data, f)

            backtest = SectorResearchBacktest(history_root=tmpdir)
            result = backtest._compute_forward_returns("测试板块", "2026-06-25", "2026-06-30", "industry")

            assert result["forward_1d_return"] is not None
            assert result["forward_5d_return"] is not None

    def test_missing_future_data_returns_none(self):
        """测试未来数据不足时返回 None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建模拟历史数据（只有 signal_date 之前的数据）
            history_dir = os.path.join(tmpdir, "industry")
            os.makedirs(history_dir)

            history_data = {
                "records": [
                    {"日期": "2026-06-25", "收盘价": 100.0, "前收盘": 99.0},
                    {"日期": "2026-06-26", "收盘价": 102.0, "前收盘": 100.0},
                ],
            }
            with open(os.path.join(history_dir, "测试板块.json"), "w") as f:
                json.dump(history_data, f)

            backtest = SectorResearchBacktest(history_root=tmpdir)
            result = backtest._compute_forward_returns("测试板块", "2026-06-26", "2026-06-29", "industry")

            assert result["forward_1d_return"] is None
            assert result["forward_5d_return"] is None

    def test_label_performance_aggregation(self):
        """测试按 consensus_label 聚合"""
        backtest = SectorResearchBacktest()

        samples = [
            {"consensus_label": "strong_consensus", "forward_returns": {"forward_1d_return": 1.0, "forward_3d_return": 3.0, "forward_5d_return": 5.0, "forward_10d_return": None, "forward_20d_return": None}},
            {"consensus_label": "strong_consensus", "forward_returns": {"forward_1d_return": 0.5, "forward_3d_return": 2.0, "forward_5d_return": 3.0, "forward_10d_return": None, "forward_20d_return": None}},
            {"consensus_label": "weak_or_avoid", "forward_returns": {"forward_1d_return": -0.5, "forward_3d_return": -1.0, "forward_5d_return": -1.0, "forward_10d_return": None, "forward_20d_return": None}},
        ]

        result = backtest._aggregate_by_label(samples)

        assert "strong_consensus" in result
        assert "weak_or_avoid" in result
        assert result["strong_consensus"]["sample_count"] == 2
        assert result["weak_or_avoid"]["sample_count"] == 1

    def test_score_bucket_performance(self):
        """测试分桶聚合"""
        backtest = SectorResearchBacktest()

        samples = [
            {"ranking_score": 0.8, "forward_returns": {"forward_1d_return": 1.0, "forward_3d_return": 3.0, "forward_5d_return": 5.0, "forward_10d_return": None, "forward_20d_return": None}},
            {"ranking_score": 0.5, "forward_returns": {"forward_1d_return": 0.5, "forward_3d_return": 2.0, "forward_5d_return": 2.0, "forward_10d_return": None, "forward_20d_return": None}},
            {"ranking_score": 0.3, "forward_returns": {"forward_1d_return": -0.5, "forward_3d_return": -1.0, "forward_5d_return": -1.0, "forward_10d_return": None, "forward_20d_return": None}},
        ]

        result = backtest._aggregate_by_bucket(samples, "ranking_score")

        assert "high" in result
        assert "medium" in result
        assert "low" in result
        assert result["high"]["sample_count"] == 1
        assert result["medium"]["sample_count"] == 1
        assert result["low"]["sample_count"] == 1

    def test_false_positive_candidates(self):
        """测试识别可能误判样本"""
        backtest = SectorResearchBacktest()

        samples = [
            {"consensus_label": "strong_consensus", "forward_returns": {"forward_5d_return": -2.0}},
            {"consensus_label": "rotation_candidate", "forward_returns": {"forward_5d_return": -1.0}},
            {"consensus_label": "weak_or_avoid", "forward_returns": {"forward_5d_return": 5.0}},
        ]

        result = backtest._analyze_samples(samples)

        assert len(result["false_positive_candidates"]) == 2
        assert result["false_positive_candidates"][0]["consensus_label"] == "strong_consensus"

    def test_missed_opportunity_candidates(self):
        """测试识别可能漏判样本"""
        backtest = SectorResearchBacktest()

        samples = [
            {"consensus_label": "weak_or_avoid", "forward_returns": {"forward_5d_return": 5.0}},
            {"consensus_label": "conflicted", "forward_returns": {"forward_5d_return": 4.0}},
            {"consensus_label": "strong_consensus", "forward_returns": {"forward_5d_return": 3.0}},
        ]

        result = backtest._analyze_samples(samples)

        assert len(result["missed_opportunity_candidates"]) == 2
        assert result["missed_opportunity_candidates"][0]["consensus_label"] == "weak_or_avoid"

    def test_skipped_dates_when_research_report_missing(self):
        """测试缺少某日 sector_research.json 时记录 skipped_dates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建空的 sector_research 目录
            os.makedirs(os.path.join(tmpdir, "sector_research"))

            backtest = SectorResearchBacktest(history_root=tmpdir)
            result = backtest.run_backtest(
                start_date="2026-06-25",
                end_date="2026-06-29",
                sector_type="industry",
                report_root=tmpdir,
            )

            assert len(result["input_summary"]["skipped_dates"]) == 5
            assert result["input_summary"]["sample_count"] == 0
