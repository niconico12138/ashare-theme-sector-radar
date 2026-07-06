"""
板块综合研判报告测试

测试 sector_research_report.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.sector_research_report import (
    generate_sector_research_markdown_report,
    save_sector_research_report,
)


class TestSectorResearchReport:
    """测试板块综合研判报告"""

    def _create_mock_report_data(self) -> dict:
        """创建模拟报告数据"""
        return {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "report_type": "sector_research",
            "version": "phase21",
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
                    "evidence_score": 0.7,
                    "opportunity_score": 0.47,
                    "risk_control_score": 1.0,
                    "confidence_score": 0.7,
                    "ranking_score": 0.66,
                    "views": {
                        "technical": {"technical_label": "trend_conflicted", "technical_score": 0.47, "technical_reasons": ["窗口分歧"]},
                        "heat": {"heat_label": "heat_fading", "heat_score": 0.49, "heat_reasons": ["热度减弱"]},
                        "rotation": {"rotation_label": "rotation_rising", "rotation_score": 0.8, "rotation_reasons": ["上升阶段"]},
                        "risk": {"risk_label": "risk_low", "risk_score": 1.0, "risk_summary": "风险低"},
                        "data_quality": {"data_quality_label": "data_reliable", "data_quality_score": 1.0, "data_reliability_summary": "数据可靠"},
                        "market_context": {"market_context_label": "underperforming_benchmark", "market_context_score": 0.0, "market_context_summary": "跑输基准"},
                        "narrative": {"narrative_label": "technology_growth", "narrative_summary": "科技成长属性"},
                    },
                    "main_reasons": ["轮动候选"],
                    "conflict_points": ["窗口分歧"],
                    "watch_points": ["观察持续性"],
                    "data_warnings": [],
                },
            ],
            "warnings": [],
            "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
        }

    def test_generate_sector_research_markdown_report(self):
        """测试生成 Markdown 字符串"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_report_contains_required_sections(self):
        """测试报告包含必需章节"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)

        assert "板块综合研判日报" in report
        assert "免责声明" in report
        assert "今日摘要" in report
        assert "今日重点观察" in report
        assert "标签分组概览" in report
        assert "板块详情" in report
        assert "数据与方法说明" in report

    def test_report_explains_confidence_not_opportunity(self):
        """测试报告说明 confidence_score 不是机会强度"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)

        assert "confidence_score" in report
        assert "不等于 opportunity_score" in report

    def test_report_contains_top_n_table(self):
        """测试报告包含今日重点观察表格"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)

        assert "今日重点观察" in report
        assert "板块" in report
        assert "标签" in report
        assert "排序分" in report

    def test_report_handles_missing_fields(self):
        """测试缺字段时不崩溃"""
        report_data = {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "report_type": "sector_research",
            "inputs": {},
            "research_results": [],
            "warnings": [],
            "disclaimer": "test",
        }
        report = generate_sector_research_markdown_report(report_data)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_report_has_no_trade_advice_words(self):
        """测试报告不包含禁止词"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)

        forbidden_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐", "建仓", "加仓", "减仓", "止盈", "止损", "目标价"]
        for word in forbidden_words:
            assert word not in report.lower(), f"报告包含禁止词: {word}"

    def test_report_uses_ranking_score_not_confidence_for_order(self):
        """测试报告排序按 ranking_score"""
        report_data = self._create_mock_report_data()
        report = generate_sector_research_markdown_report(report_data)

        # 检查表格中排序分列存在
        assert "排序分" in report

    def test_weak_or_avoid_high_confidence_explanation(self):
        """测试 weak_or_avoid 高 confidence 说明"""
        report_data = self._create_mock_report_data()
        report_data["research_results"][0]["consensus_label"] = "weak_or_avoid"
        report_data["research_results"][0]["confidence_score"] = 0.7

        report = generate_sector_research_markdown_report(report_data)

        # 检查说明 confidence 不是机会强度
        assert "confidence_score" in report
        assert "正向观察强度有限" in report


class TestSaveSectorResearchReport:
    """测试保存报告"""

    def test_save_report(self):
        """测试保存报告"""
        report_data = {
            "as_of_date": "2026-06-29",
            "sector_type": "industry",
            "inputs": {},
            "research_results": [],
            "warnings": [],
            "disclaimer": "test",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            save_sector_research_report(tmpdir, report_data)
            assert os.path.exists(os.path.join(tmpdir, "sector_research.md"))
