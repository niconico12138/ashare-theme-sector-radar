"""
板块综合研判日报可读性测试

测试日报格式、daily_summary 和可读性。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.sector_research_report import (
    generate_sector_research_markdown_report,
    generate_daily_summary,
    save_sector_research_report,
)


class TestReportReadability:
    """测试日报可读性"""

    def _create_mock_report_data(self) -> dict:
        """创建模拟报告数据"""
        return {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "report_type": "sector_research",
            "version": "phase35",
            "inputs": {
                "trend_weight_profile": "trend_confirmation",
                "windows": [5, 10, 20],
                "benchmark": "hs300",
            },
            "research_results": [
                {
                    "sector_name": "半导体",
                    "sector_type": "industry",
                    "consensus_label": "rotation_candidate",
                    "confirm_level": "medium",
                    "evidence_score": 0.70,
                    "opportunity_score": 0.47,
                    "risk_control_score": 1.0,
                    "confidence_score": 0.70,
                    "ranking_score": 0.66,
                    "market_regime": {"regime_composite_label": "choppy_market"},
                    "regime_interpretation": {"summary": "震荡分化环境。", "label_context": "标签仅作解释。"},
                    "views": {
                        "technical": {"technical_label": "trend_conflicted", "technical_score": 0.47},
                        "heat": {"heat_label": "heat_fading", "heat_score": 0.49},
                        "rotation": {"rotation_label": "rotation_rising", "rotation_score": 0.80},
                        "risk": {"risk_label": "risk_low", "risk_score": 1.0},
                        "data_quality": {"data_quality_label": "data_reliable", "data_quality_score": 1.0},
                        "market_context": {"market_context_label": "underperforming_benchmark", "market_context_score": 0.0},
                        "narrative": {"narrative_label": "technology_growth"},
                    },
                    "main_reasons": ["轮动候选，正在升温"],
                    "conflict_points": ["窗口分歧"],
                    "watch_points": ["观察持续性"],
                    "data_warnings": [],
                    "veto": {"veto_triggered": False},
                    "agent_votes": {"positive_votes": 3, "neutral_votes": 2, "negative_votes": 2},
                    "conflict_level": "none",
                },
                {
                    "sector_name": "医疗服务",
                    "sector_type": "industry",
                    "consensus_label": "weak_or_avoid",
                    "confirm_level": "low",
                    "evidence_score": 0.63,
                    "opportunity_score": 0.29,
                    "risk_control_score": 1.0,
                    "confidence_score": 0.65,
                    "ranking_score": 0.28,
                    "market_regime": {"regime_composite_label": "choppy_market"},
                    "views": {
                        "technical": {"technical_label": "trend_weak", "technical_score": 0.18},
                        "heat": {"heat_label": "heat_fading", "heat_score": 0.43},
                        "rotation": {"rotation_label": "rotation_weakening", "rotation_score": 0.40},
                        "risk": {"risk_label": "risk_low", "risk_score": 1.0},
                        "data_quality": {"data_quality_label": "data_usable", "data_quality_score": 0.90},
                        "market_context": {"market_context_label": "underperforming_benchmark", "market_context_score": 0.0},
                        "narrative": {"narrative_label": "healthcare_defensive_recovery"},
                    },
                    "main_reasons": ["多维度偏弱"],
                    "conflict_points": [],
                    "watch_points": ["多维度偏弱"],
                    "data_warnings": [],
                    "veto": {"veto_triggered": False},
                    "agent_votes": {"positive_votes": 1, "neutral_votes": 4, "negative_votes": 2},
                    "conflict_level": "none",
                },
            ],
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

    def test_report_has_summary_section(self):
        """测试报告包含今日摘要"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)
        assert "## 今日摘要" in report
        assert "## 今日重点观察" in report
        assert "## 标签分组概览" in report
        assert "## 板块详情" in report
        assert "## 数据与方法说明" in report

    def test_report_has_chinese_labels(self):
        """测试报告使用中文标签"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)
        assert "轮动观察候选" in report
        assert "正向观察强度有限" in report

    def test_report_has_regime_section(self):
        """测试报告包含市场状态章节"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)
        assert "市场状态（解释层）" in report
        assert "震荡分化" in report

    def test_daily_summary_fields(self):
        """测试 daily_summary 包含所有必要字段"""
        report_data = self._create_mock_report_data()
        summary = generate_daily_summary(report_data)
        assert summary["as_of_date"] == "2026-06-29"
        assert summary["sector_type"] == "industry"
        assert summary["market_regime"] == "choppy_market"
        assert summary["total_count"] == 2
        assert summary["focus_count"] >= 1
        assert "summary_text" in summary
        assert "top_watch_names" in summary

    def test_no_trade_advice_words(self):
        """测试报告不包含交易建议词"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)
        trade_words = [
            "buy", "sell", "hold", "买入", "卖出", "持有", "推荐",
            "建仓", "加仓", "减仓", "止盈", "止损", "目标价",
        ]
        for word in trade_words:
            assert word not in report.lower(), f"报告中包含交易建议词: {word}"

    def test_save_report(self):
        """测试保存报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_data = self._create_mock_report_data()
            save_sector_research_report(tmpdir, report_data)
            assert os.path.exists(os.path.join(tmpdir, "sector_research.md"))

    def test_report_has_data_method_section(self):
        """测试报告包含数据与方法说明"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)
        assert "## 数据与方法说明" in report
        assert "confidence_score" in report
        assert "ranking_score" in report

    def test_report_no_overconfident_words(self):
        """测试报告不包含过度确定性表达"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)
        overconfident_words = ["必然", "一定", "肯定", "确定上涨", "可以买", "必须回避", "强烈建议"]
        for word in overconfident_words:
            assert word not in report, f"报告包含过度确定性表达: {word}"
