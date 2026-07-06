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
        """测试 JSON 报告不含个股操作结论"""
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

        assert "不作为个股操作依据" in report["disclaimer"]
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

        assert "不作为个股操作依据或自动交易指令" in report

    def test_markdown_report_no_stock_recommendation(self):
        """测试 Markdown 报告不含个股操作结论"""
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


class TestMarkdownReportTHSFallback:
    """测试 Markdown 报告 THS Fallback 说明"""

    def _create_report_data(self):
        """创建测试报告数据"""
        market_temp = MarketTemperature(
            score=70.0,
            label="warm",
            description="市场情绪偏暖",
        )

        industry_top = [
            SectorScore(
                sector_id="ths_industry_半导体",
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
                sector_id="ths_concept_ChatGPT概念",
                name="ChatGPT概念",
                type=SectorType.CONCEPT,
                score=82.0,
                positive_score=88.0,
                risk_penalty=-6.0,
                focus_level=FocusLevel.WATCH,
            ),
        ]

        overlap = []

        return market_temp, industry_top, concept_top, overlap

    def _create_provider_status(self, fallback_used=True):
        """创建 provider status"""
        from theme_sector_radar.models import ProviderStatus

        if fallback_used:
            return ProviderStatus(
                industry_sectors="ok",
                concept_sectors="ok",
                effective_provider="ths",
                industry_source="akshare/ths_industry",
                concept_source="akshare/ths_concept",
                fallback_used=True,
                fallback_provider="ths",
                fallback_reason="东方财富行业接口失败: ConnectionError",
                industry_count=90,
                concept_count=373,
                em_industry_error="ConnectionError: Remote end closed connection",
                em_concept_error="ConnectionError: Remote end closed connection",
            )
        else:
            return ProviderStatus(
                industry_sectors="ok",
                concept_sectors="ok",
                effective_provider="akshare",
                industry_source="akshare/eastmoney_industry",
                concept_source="akshare/eastmoney_concept",
                fallback_used=False,
            )

    def test_markdown_report_ths_fallback_section(self):
        """测试 Markdown 报告包含 THS fallback 说明"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()
        provider_status = self._create_provider_status(fallback_used=True)

        report = generate_markdown_report(
            as_of_date="2026-06-29",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
            provider_status=provider_status,
        )

        # 验证包含 THS fallback 说明
        assert "数据来源" in report
        assert "东方财富接口不可用" in report
        assert "同花顺" in report
        assert "降级原因" in report
        assert "东方财富行业接口错误" in report

    def test_markdown_report_no_fallback_no_section(self):
        """测试无 fallback 时 Markdown 报告不显示降级说明"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()
        provider_status = self._create_provider_status(fallback_used=False)

        report = generate_markdown_report(
            as_of_date="2026-06-29",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
            provider_status=provider_status,
        )

        # 无 fallback 时，不应显示降级说明
        assert "东方财富接口不可用" not in report
        assert "降级原因" not in report

    def test_markdown_report_ths_concept_limitation(self):
        """测试 Markdown 报告说明 THS 概念板块数据限制"""
        market_temp, industry_top, concept_top, overlap = self._create_report_data()
        provider_status = self._create_provider_status(fallback_used=True)

        report = generate_markdown_report(
            as_of_date="2026-06-29",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
            provider_status=provider_status,
        )

        # 验证包含 THS 概念板块数据限制说明
        assert "同花顺概念板块列表暂不包含涨跌幅数据" in report
        assert "概念板块评分可能偏低" in report


class TestJsonReportProviderStatus:
    """测试 JSON 报告包含 provider_status"""

    def test_json_report_includes_provider_status(self):
        """测试 JSON 报告包含 provider_status 字段"""
        from theme_sector_radar.models import ProviderStatus

        market_temp = MarketTemperature(
            score=70.0,
            label="warm",
            description="市场情绪偏暖",
        )

        industry_top = [
            SectorScore(
                sector_id="ths_industry_半导体",
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
                sector_id="ths_concept_ChatGPT概念",
                name="ChatGPT概念",
                type=SectorType.CONCEPT,
                score=82.0,
                positive_score=88.0,
                risk_penalty=-6.0,
                focus_level=FocusLevel.WATCH,
            ),
        ]

        overlap = []

        provider_status = ProviderStatus(
            industry_sectors="ok",
            concept_sectors="ok",
            effective_provider="ths",
            industry_source="akshare/ths_industry",
            concept_source="akshare/ths_concept",
            fallback_used=True,
            fallback_provider="ths",
            fallback_reason="东方财富行业接口失败: ConnectionError",
            industry_count=90,
            concept_count=373,
            em_industry_error="ConnectionError: Remote end closed connection",
            em_concept_error="ConnectionError: Remote end closed connection",
            concept_price_change_available=False,
        )

        report = generate_json_report(
            as_of_date="2026-06-29",
            market_temperature=market_temp,
            industry_top=industry_top,
            concept_top=concept_top,
            overlap=overlap,
            provider_status=provider_status,
        )

        # 验证包含 provider_status
        assert "provider_status" in report
        ps = report["provider_status"]
        assert ps["effective_provider"] == "ths"
        assert ps["industry_source"] == "akshare/ths_industry"
        assert ps["concept_source"] == "akshare/ths_concept"
        assert ps["fallback_used"] is True
        assert ps["fallback_provider"] == "ths"
        assert "ConnectionError" in ps["fallback_reason"]
        assert ps["industry_count"] == 90
        assert ps["concept_count"] == 373
        assert ps["concept_price_change_available"] is False

    def test_json_report_concept_price_change_available_field(self):
        """测试 JSON 报告包含 concept_price_change_available 字段"""
        from theme_sector_radar.models import ProviderStatus

        market_temp = MarketTemperature(score=50.0, label="neutral")

        provider_status = ProviderStatus(
            effective_provider="ths",
            concept_price_change_available=False,
        )

        report = generate_json_report(
            as_of_date="2026-06-29",
            market_temperature=market_temp,
            industry_top=[],
            concept_top=[],
            overlap=[],
            provider_status=provider_status,
        )

        assert report["provider_status"]["concept_price_change_available"] is False


class TestConceptScorePriceChangeUnavailable:
    """测试概念评分在涨跌幅不可用时的行为"""

    def test_heat_burst_score_without_price_change(self):
        """测试涨跌幅不可用时热度爆发得分"""
        from theme_sector_radar.models import SectorSnapshot, SectorType
        from theme_sector_radar.scoring.concept_score import calculate_heat_burst_score

        # 涨跌幅不可用时，热度爆发得分应只有成交额部分（0-10）
        snapshot = SectorSnapshot(
            sector_id="test",
            name="test",
            type=SectorType.CONCEPT,
            price_change_pct=0.0,
            turnover=0.0,
            price_change_available=False,
        )
        score = calculate_heat_burst_score(snapshot)
        # 涨幅部分为 0，成交额部分为 2（最低），总分 2.0
        assert score <= 10.0  # 不能超过 10（只有成交额部分）

    def test_catalyst_score_without_price_change(self):
        """测试涨跌幅不可用时催化剂得分"""
        from theme_sector_radar.models import SectorSnapshot, SectorType
        from theme_sector_radar.scoring.concept_score import calculate_catalyst_score

        snapshot = SectorSnapshot(
            sector_id="test",
            name="test",
            type=SectorType.CONCEPT,
            price_change_pct=5.0,  # 即使有值，如果标记为不可用也不应使用
            price_change_available=False,
        )
        score = calculate_catalyst_score(snapshot)
        # 涨跌幅不可用时，返回中性默认分 3.0
        assert score == 3.0

    def test_concept_phase_without_price_change(self):
        """测试涨跌幅不可用时阶段判断"""
        from theme_sector_radar.models import SectorSnapshot, SectorType
        from theme_sector_radar.scoring.concept_score import calculate_concept_phase
        from theme_sector_radar.models import ConceptPhase

        snapshot = SectorSnapshot(
            sector_id="test",
            name="test",
            type=SectorType.CONCEPT,
            price_change_pct=5.0,
            price_change_available=False,
        )
        phase = calculate_concept_phase(snapshot)
        # 涨跌幅不可用时，返回 DIVERGENCE
        assert phase == ConceptPhase.DIVERGENCE

    def test_score_breakdown_includes_price_change_available(self):
        """测试评分 breakdown 包含 price_change_available 字段"""
        from theme_sector_radar.models import SectorSnapshot, SectorType
        from theme_sector_radar.scoring.concept_score import calculate_concept_score_breakdown

        snapshot = SectorSnapshot(
            sector_id="test",
            name="test",
            type=SectorType.CONCEPT,
            price_change_pct=0.0,
            price_change_available=False,
        )
        breakdown = calculate_concept_score_breakdown(snapshot)
        assert "price_change_available" in breakdown
        assert breakdown["price_change_available"] is False
        assert "data_quality_warning" in breakdown

    def test_focus_level_downgraded_without_price_change(self):
        """测试涨跌幅不可用时 focus 等级降级"""
        from theme_sector_radar.scoring.focus_level import calculate_focus_level
        from theme_sector_radar.models import FocusLevel, RiskLevel

        # 即使正向评分很高，涨跌幅不可用时也不能输出 FOCUS
        focus_level, reasons = calculate_focus_level(
            positive_score=90.0,
            risk_penalty=5.0,
            risk_level=RiskLevel.LOW,
            data_quality_score=80.0,
            price_change_available=False,
        )
        assert focus_level != FocusLevel.FOCUS
        assert any("涨跌幅" in r for r in reasons)
