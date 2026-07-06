"""
Market Regime Analysis 测试

测试市场状态分层分析模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.market_regime_analysis import MarketRegimeAnalysis


class TestMarketRegimeAnalysis:
    """测试 MarketRegimeAnalysis"""

    def test_benchmark_trend_uptrend(self):
        """测试基准趋势分类 - uptrend"""
        analysis = MarketRegimeAnalysis()

        records = [
            {"date": "2026-06-20", "close": 4800, "pct_change": 0.5},
            {"date": "2026-06-21", "close": 4820, "pct_change": 0.4},
            {"date": "2026-06-22", "close": 4850, "pct_change": 0.6},
            {"date": "2026-06-23", "close": 4880, "pct_change": 0.6},
            {"date": "2026-06-24", "close": 4920, "pct_change": 0.8},
        ]

        result = analysis._compute_benchmark_trend(records)
        assert result == "benchmark_uptrend"

    def test_benchmark_trend_downtrend(self):
        """测试基准趋势分类 - downtrend"""
        analysis = MarketRegimeAnalysis()

        records = [
            {"date": "2026-06-20", "close": 5000, "pct_change": -0.5},
            {"date": "2026-06-21", "close": 4970, "pct_change": -0.6},
            {"date": "2026-06-22", "close": 4930, "pct_change": -0.8},
            {"date": "2026-06-23", "close": 4880, "pct_change": -1.0},
            {"date": "2026-06-24", "close": 4830, "pct_change": -1.0},
        ]

        result = analysis._compute_benchmark_trend(records)
        assert result == "benchmark_downtrend"

    def test_benchmark_trend_sideways(self):
        """测试基准趋势分类 - sideways"""
        analysis = MarketRegimeAnalysis()

        records = [
            {"date": "2026-06-20", "close": 4900, "pct_change": 0.1},
            {"date": "2026-06-21", "close": 4905, "pct_change": 0.1},
            {"date": "2026-06-22", "close": 4898, "pct_change": -0.1},
            {"date": "2026-06-23", "close": 4902, "pct_change": 0.1},
            {"date": "2026-06-24", "close": 4900, "pct_change": 0.0},
        ]

        result = analysis._compute_benchmark_trend(records)
        assert result == "benchmark_sideways"

    def test_benchmark_trend_unknown(self):
        """测试基准趋势分类 - unknown"""
        analysis = MarketRegimeAnalysis()

        records = [
            {"date": "2026-06-24", "close": 4900, "pct_change": 0.1},
        ]

        result = analysis._compute_benchmark_trend(records)
        assert result == "benchmark_unknown"

    def test_breadth_regime_broad_rising(self):
        """测试广度分类 - broad_rising"""
        analysis = MarketRegimeAnalysis()

        replay_data = {
            "industry_top": [
                {"score": 80, "price_change_pct": 2.0},
                {"score": 75, "price_change_pct": 1.5},
                {"score": 70, "price_change_pct": 1.0},
                {"score": 65, "price_change_pct": 0.5},
                {"score": 60, "price_change_pct": 0.3},
            ]
        }

        result = analysis._compute_breadth_regime(replay_data)
        assert result == "broad_rising"

    def test_breadth_regime_broad_falling(self):
        """测试广度分类 - broad_falling"""
        analysis = MarketRegimeAnalysis()

        replay_data = {
            "industry_top": [
                {"score": 30, "price_change_pct": -2.0},
                {"score": 25, "price_change_pct": -1.5},
                {"score": 20, "price_change_pct": -1.0},
                {"score": 15, "price_change_pct": -0.5},
                {"score": 10, "price_change_pct": -0.3},
            ]
        }

        result = analysis._compute_breadth_regime(replay_data)
        assert result == "broad_falling"

    def test_breadth_regime_mixed(self):
        """测试广度分类 - mixed_breadth"""
        analysis = MarketRegimeAnalysis()

        replay_data = {
            "industry_top": [
                {"score": 80, "price_change_pct": 2.0},
                {"score": 75, "price_change_pct": 1.5},
                {"score": 30, "price_change_pct": -2.0},
                {"score": 25, "price_change_pct": -1.5},
                {"score": 50, "price_change_pct": 0.0},
            ]
        }

        result = analysis._compute_breadth_regime(replay_data)
        assert result == "mixed_breadth"

    def test_volatility_regime_high(self):
        """测试波动率分类 - high"""
        analysis = MarketRegimeAnalysis()

        records = [
            {"date": f"2026-06-{i:02d}", "close": 4900 + i * 10, "pct_change": 3.0}
            for i in range(1, 11)
        ]

        result = analysis._compute_volatility_regime(records)
        assert result == "high_volatility"

    def test_volatility_regime_low(self):
        """测试波动率分类 - low"""
        analysis = MarketRegimeAnalysis()

        records = [
            {"date": f"2026-06-{i:02d}", "close": 4900 + i * 2, "pct_change": 0.3}
            for i in range(1, 11)
        ]

        result = analysis._compute_volatility_regime(records)
        assert result == "low_volatility"

    def test_composite_regime_risk_on(self):
        """测试综合标签 - risk_on"""
        analysis = MarketRegimeAnalysis()

        result = analysis._compute_composite_regime(
            "benchmark_uptrend", "market_hot", "broad_rising", "normal_volatility"
        )
        assert result == "risk_on"

    def test_composite_regime_risk_off(self):
        """测试综合标签 - risk_off"""
        analysis = MarketRegimeAnalysis()

        result = analysis._compute_composite_regime(
            "benchmark_downtrend", "market_cold", "broad_falling", "normal_volatility"
        )
        assert result == "risk_off"

    def test_no_lookahead(self):
        """测试 no-lookahead"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建基准数据
            bench_dir = os.path.join(tmpdir, "benchmarks", "hs300")
            os.makedirs(bench_dir)
            bench_data = {
                "records": [
                    {"date": f"2026-06-{i:02d}", "close": 4900 + i * 5, "pct_change": 0.1 * i}
                    for i in range(1, 26)
                ]
            }
            with open(os.path.join(bench_dir, "20260601_to_20260625.json"), "w") as f:
                json.dump(bench_data, f)

            # 创建研究报告
            research_dir = os.path.join(tmpdir, "sector_research", "2026-06-10")
            os.makedirs(research_dir)
            research_data = {
                "research_results": [{
                    "sector_name": "测试板块",
                    "sector_type": "industry",
                    "consensus_label": "weak_or_avoid",
                    "ranking_score": 0.2,
                    "opportunity_score": 0.15,
                    "confidence_score": 0.6,
                    "evidence_score": 0.5,
                    "risk_control_score": 0.7,
                }]
            }
            with open(os.path.join(research_dir, "sector_research.json"), "w") as f:
                json.dump(research_data, f)

            # 创建 replay 报告
            replay_dir = os.path.join(tmpdir, "theme_sector_radar", "2026-06-10")
            os.makedirs(replay_dir)
            replay_data = {
                "market_temperature": {"score": 50, "label": "neutral"},
                "industry_top": [{"score": 50, "price_change_pct": None}],
            }
            with open(os.path.join(replay_dir, "theme_sector_radar.json"), "w") as f:
                json.dump(replay_data, f)

            analysis = MarketRegimeAnalysis(
                history_root=tmpdir,
                benchmark_root=os.path.join(tmpdir, "benchmarks"),
            )
            result = analysis.run_analysis(
                start_date="2026-06-10",
                end_date="2026-06-10",
                sector_type="industry",
                report_root=tmpdir,
            )

            assert result["no_lookahead_check"]["passed"] is True

    def test_label_x_regime_aggregation(self):
        """测试 label x regime 聚合"""
        analysis = MarketRegimeAnalysis()

        samples = [
            {
                "consensus_label": "weak_or_avoid",
                "regime_composite_label": "risk_off",
                "forward_returns": {"forward_5d_return": -2.0},
            },
            {
                "consensus_label": "weak_or_avoid",
                "regime_composite_label": "risk_on",
                "forward_returns": {"forward_5d_return": 3.0},
            },
            {
                "consensus_label": "low_signal_noise",
                "regime_composite_label": "risk_off",
                "forward_returns": {"forward_5d_return": 1.0},
            },
        ]

        result = analysis._aggregate_label_x_regime(samples)
        assert "weak_or_avoid" in result
        assert "risk_off" in result["weak_or_avoid"]
        assert result["weak_or_avoid"]["risk_off"]["sample_count"] == 1
        assert result["weak_or_avoid"]["risk_on"]["sample_count"] == 1

    def test_report_no_trade_advice(self):
        """测试报告不包含交易建议词"""
        from theme_sector_radar.reports.market_regime_report import generate_market_regime_report

        report_data = {
            "start_date": "2026-06-01",
            "end_date": "2026-06-29",
            "sector_type": "industry",
            "benchmark": "hs300",
            "input_summary": {"sample_count": 100},
            "regime_distribution": {"regime_composite_label": {"risk_on": 50, "risk_off": 50}},
            "label_regime_performance": {},
            "score_bucket_regime_performance": {},
            "missed_opportunity_by_regime": {"total_missed": 0, "by_regime": {}},
            "failed_rebound_by_regime": {"total_failed": 0, "by_regime": {}},
            "no_lookahead_check": {"passed": True, "violation_count": 0, "total_samples": 100},
        }

        report = generate_market_regime_report(report_data)
        trade_words = [
            "buy", "sell", "hold", "买入", "卖出", "持有", "推荐",
            "建仓", "加仓", "减仓", "止盈", "止损", "目标价",
        ]
        for word in trade_words:
            assert word not in report.lower(), f"报告中包含交易建议词: {word}"
