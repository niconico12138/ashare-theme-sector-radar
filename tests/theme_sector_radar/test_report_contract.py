"""
报告契约测试

测试 JSON 和 Markdown 报告生成。
"""

import json

import pytest

from theme_sector_radar.models import (
    FocusLevel,
    MarketTemperature,
    ResonanceResult,
    SectorScore,
    SectorType,
)
from theme_sector_radar.reports.json_report import generate_json_report
from theme_sector_radar.reports.markdown_report import generate_markdown_report


class TestJsonReport:
    """测试 JSON 报告"""

    def _create_report_data(self):
        """创建测试报告数据"""
        market_temp = MarketTemperature(
            score=70.0,
            label="warm",
            description="市场情绪偏暖",
        )

        industry_top = [
            SectorScore(
                sector_id="BK0428",
                name="半导体",
                type=SectorType.INDUSTRY,
                score=85.0,
                positive_score=90.0,
                risk_penalty=-5.0,
                focus_level=FocusLevel.FOCUS,
            ),
        ]

        concept_top = [
            SectorScore(
                sector_id="BK1036",
                name="ChatGPT概念",
                type=SectorType.CONCEPT,
                score=82.0,
                positive_score=88.0,
                risk_penalty=-6.0,
                focus_level=FocusLevel.WATCH,
            ),
        ]

        overlap = [
            ResonanceResult(
                industry="半导体",
                concept="ChatGPT概念",
                resonance_score=75.0,
            ),
        ]

        return market_temp, industry_top, concept_top, overlap

    def test_json_report_required_fields(self):
        """测试 JSON 报告必含字段"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()

        report = generate_json_report(
            as_of_date="2026-06-28",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
        )

        required_fields = [
            "report_type",
            "version",
            "as_of_date",
            "updated_at",
            "data_sources",
            "data_quality_score",
            "market_temperature",
            "industry_top",
            "concept_top",
            "overlap",
            "risk_summary",
            "data_quality",
            "disclaimer",
        ]

        for field in required_fields:
            assert field in report, f"Missing field: {field}"

    def test_json_report_no_stock_recommendation(self):
        """测试 JSON 报告不含个股推荐"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()

        report = generate_json_report(
            as_of_date="2026-06-28",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
        )

        json_str = json.dumps(report, ensure_ascii=False)

        # 不得出现 buy/sell/hold 个股建议
        assert "buy" not in json_str.lower()
        assert "sell" not in json_str.lower()
        assert "hold" not in json_str.lower()
        assert "买入" not in json_str
        assert "卖出" not in json_str
        assert "持有" not in json_str

    def test_json_report_disclaimer(self):
        """测试 JSON 报告声明"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()

        report = generate_json_report(
            as_of_date="2026-06-28",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
        )

        assert "不构成个股推荐" in report["disclaimer"]
        assert "买卖建议" in report["disclaimer"]
        assert "自动交易指令" in report["disclaimer"]


class TestMarkdownReport:
    """测试 Markdown 报告"""

    def _create_report_data(self):
        """创建测试报告数据"""
        market_temp = MarketTemperature(
            score=70.0,
            label="warm",
            description="市场情绪偏暖",
        )

        industry_top = [
            SectorScore(
                sector_id="BK0428",
                name="半导体",
                type=SectorType.INDUSTRY,
                score=85.0,
                positive_score=90.0,
                risk_penalty=-5.0,
                focus_level=FocusLevel.FOCUS,
            ),
        ]

        concept_top = [
            SectorScore(
                sector_id="BK1036",
                name="ChatGPT概念",
                type=SectorType.CONCEPT,
                score=82.0,
                positive_score=88.0,
                risk_penalty=-6.0,
                focus_level=FocusLevel.WATCH,
            ),
        ]

        overlap = [
            ResonanceResult(
                industry="半导体",
                concept="ChatGPT概念",
                resonance_score=75.0,
            ),
        ]

        return market_temp, industry_top, concept_top, overlap

    def test_markdown_report_sections(self):
        """测试 Markdown 报告章节"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()

        report = generate_markdown_report(
            as_of_date="2026-06-28",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
        )

        required_sections = [
            "市场短线温度",
            "行业板块 Top N",
            "概念板块 Top N",
            "行业 + 概念共振",
            "高分板块成分股",
            "风险提示",
            "数据质量",
            "声明",
        ]

        for section in required_sections:
            assert section in report, f"Missing section: {section}"

    def test_markdown_report_disclaimer(self):
        """测试 Markdown 报告声明"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()

        report = generate_markdown_report(
            as_of_date="2026-06-28",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
        )

        assert "不构成个股推荐、买卖建议或自动交易指令" in report

    def test_markdown_report_no_stock_recommendation(self):
        """测试 Markdown 报告不含个股推荐"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()

        report = generate_markdown_report(
            as_of_date="2026-06-28",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
        )

        # 不得出现 buy/sell/hold 个股建议
        assert "buy" not in report.lower()
        assert "sell" not in report.lower()
        assert "hold" not in report.lower()
        assert "买入" not in report
        assert "卖出" not in report
        assert "持有" not in report
