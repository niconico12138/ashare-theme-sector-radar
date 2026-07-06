"""
Agent Reliability 测试

测试 Agent 可靠性评估模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.backtest.agent_reliability import AgentReliability
from theme_sector_radar.reports.agent_reliability_report import (
    generate_agent_reliability_report,
    save_agent_reliability_report,
)


class TestAgentReliability:
    """测试 AgentReliability"""

    def _create_mock_data(self, tmpdir: str):
        """创建模拟数据"""
        # 创建 sector_history
        history_dir = os.path.join(tmpdir, "sector_history", "industry")
        os.makedirs(history_dir)

        for name in ["半导体", "电子化学品"]:
            history_data = {
                "records": [
                    {"日期": f"2026-06-{d:02d}", "收盘价": 100.0 + d, "前收盘": 99.0 + d}
                    for d in range(20, 30)
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
                        "sector_name": "半导体",
                        "consensus_label": "trend_confirmed",
                        "ranking_score": 0.65,
                        "opportunity_score": 0.50,
                        "confidence_score": 0.70,
                        "market_regime": {"regime_composite_label": "choppy_market"},
                        "agent_opinions": [
                            {
                                "agent_id": "technical_trend",
                                "layer": "L2_specialized",
                                "vote": "positive",
                                "confidence": 0.8,
                            },
                            {
                                "agent_id": "short_term_heat",
                                "layer": "L2_specialized",
                                "vote": "neutral",
                                "confidence": 0.6,
                            },
                        ],
                    },
                ],
            }
            with open(os.path.join(report_dir, "sector_research.json"), "w") as f:
                json.dump(data, f)

    def test_run_analysis_basic(self):
        """测试基本分析"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            assert result["total_samples"] > 0
            assert len(result["agents"]) > 0

    def test_agent_reliability_score_range(self):
        """测试可靠性评分范围"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            for agent_id, stats in result["agents"].items():
                score = stats.get("reliability_score", 0)
                assert 0 <= score <= 1, f"Agent {agent_id} reliability_score out of range: {score}"

    def test_reliability_label合法(self):
        """测试可靠性标签合法"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            valid_labels = ["high_reliability", "moderate_reliability", "low_reliability", "insufficient_samples"]
            for agent_id, stats in result["agents"].items():
                label = stats.get("reliability_label", "")
                assert label in valid_labels, f"Agent {agent_id} has invalid label: {label}"

    def test_vote_distribution(self):
        """测试 vote 分布"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            for agent_id, stats in result["agents"].items():
                dist = stats.get("vote_distribution", {})
                total = sum(dist.values())
                assert total == stats["sample_count"], f"Agent {agent_id} vote distribution mismatch"

    def test_misidentifications(self):
        """测试误判识别"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            misids = result.get("misidentifications", {})
            assert "positive_false_signal" in misids
            assert "negative_missed_signal" in misids
            assert "neutral_missed_move" in misids

    def test_regime_performance(self):
        """测试 regime 分层"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            regime_perf = result.get("regime_performance", {})
            assert len(regime_perf) > 0

    def test_report_generation(self):
        """测试报告生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            md = generate_agent_reliability_report(result)
            assert "Agent 可靠性仪表盘" in md
            assert "可靠性排名" in md

    def test_no_trade_advice_words(self):
        """测试不包含交易建议词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            md = generate_agent_reliability_report(result)
            trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
            for word in trade_words:
                assert word not in md.lower(), f"报告包含交易建议词: {word}"

    def test_save_report(self):
        """测试保存报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            analysis = AgentReliability(history_root=os.path.join(tmpdir, "sector_history"))
            result = analysis.run_analysis(
                start_date="2026-06-24",
                end_date="2026-06-25",
                report_root=tmpdir,
            )

            output_dir = os.path.join(tmpdir, "output")
            save_agent_reliability_report(output_dir, result)

            assert os.path.exists(os.path.join(output_dir, "agent_reliability.json"))
            assert os.path.exists(os.path.join(output_dir, "agent_reliability.md"))
