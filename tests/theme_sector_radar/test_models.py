"""
模型契约测试

测试关键字段存在，枚举合法，JSON 可序列化。
"""

import json

import pytest

from theme_sector_radar.models import (
    AgentOutput,
    AgentStatus,
    ConceptPhase,
    ConstituentSnapshot,
    FocusLevel,
    FlowAlignment,
    MarketTemperature,
    RadarContext,
    RadarReport,
    ResonanceResult,
    RiskLevel,
    SectorScore,
    SectorSnapshot,
    SectorType,
)


class TestEnums:
    """测试枚举类型"""

    def test_sector_type_values(self):
        """测试 SectorType 枚举值"""
        assert SectorType.INDUSTRY.value == "industry"
        assert SectorType.CONCEPT.value == "concept"

    def test_focus_level_values(self):
        """测试 FocusLevel 枚举值"""
        assert FocusLevel.FOCUS.value == "focus"
        assert FocusLevel.WATCH.value == "watch"
        assert FocusLevel.CORE_ONLY.value == "core_only"
        assert FocusLevel.CAUTION.value == "caution"
        assert FocusLevel.AVOID.value == "avoid"

    def test_risk_level_values(self):
        """测试 RiskLevel 枚举值"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"

    def test_concept_phase_values(self):
        """测试 ConceptPhase 枚举值"""
        assert ConceptPhase.STARTUP.value == "startup"
        assert ConceptPhase.FERMENTATION.value == "fermentation"
        assert ConceptPhase.ACCELERATION.value == "acceleration"
        assert ConceptPhase.DIVERGENCE.value == "divergence"
        assert ConceptPhase.RETREAT.value == "retreat"


class TestConstituentSnapshot:
    """测试成分股快照"""

    def test_creation(self):
        """测试创建"""
        snapshot = ConstituentSnapshot(
            code="688981",
            name="中芯国际",
            change_pct=5.2,
            turnover=1234567890,
            is_core=True,
        )
        assert snapshot.code == "688981"
        assert snapshot.name == "中芯国际"
        assert snapshot.change_pct == 5.2
        assert snapshot.is_core is True

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        snapshot = ConstituentSnapshot(
            code="688981",
            name="中芯国际",
            change_pct=5.2,
        )
        json_str = json.dumps(snapshot.model_dump(), ensure_ascii=False)
        assert "688981" in json_str
        assert "中芯国际" in json_str


class TestSectorSnapshot:
    """测试板块快照"""

    def test_creation(self):
        """测试创建"""
        snapshot = SectorSnapshot(
            sector_id="BK0428",
            name="半导体",
            type=SectorType.INDUSTRY,
            price_change_pct=3.21,
            turnover=12345678900,
            main_net_inflow=1234560000,
            data_sources=["akshare"],
            data_quality_score=88.0,
        )
        assert snapshot.sector_id == "BK0428"
        assert snapshot.type == SectorType.INDUSTRY

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        snapshot = SectorSnapshot(
            sector_id="BK0428",
            name="半导体",
            type=SectorType.INDUSTRY,
        )
        json_str = json.dumps(snapshot.model_dump(), ensure_ascii=False)
        assert "BK0428" in json_str


class TestSectorScore:
    """测试板块评分"""

    def test_creation(self):
        """测试创建"""
        score = SectorScore(
            sector_id="BK0428",
            name="半导体",
            type=SectorType.INDUSTRY,
            score=82.4,
            positive_score=91.0,
            risk_penalty=-8.6,
            focus_level=FocusLevel.FOCUS,
            risk_level=RiskLevel.MEDIUM,
        )
        assert score.score == 82.4
        assert score.focus_level == FocusLevel.FOCUS

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        score = SectorScore(
            sector_id="BK0428",
            name="半导体",
            type=SectorType.INDUSTRY,
        )
        json_str = json.dumps(score.model_dump(), ensure_ascii=False)
        assert "BK0428" in json_str


class TestResonanceResult:
    """测试共振结果"""

    def test_creation(self):
        """测试创建"""
        result = ResonanceResult(
            industry="半导体",
            concept="先进封装",
            resonance_score=86.0,
            overlap_constituent_count=12,
            common_core_count=4,
            flow_alignment=FlowAlignment.BOTH_INFLOW,
            both_top_n=True,
            focus_level=FocusLevel.FOCUS,
        )
        assert result.resonance_score == 86.0
        assert result.flow_alignment == FlowAlignment.BOTH_INFLOW

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        result = ResonanceResult(
            industry="半导体",
            concept="先进封装",
        )
        json_str = json.dumps(result.model_dump(), ensure_ascii=False)
        assert "半导体" in json_str


class TestMarketTemperature:
    """测试市场温度"""

    def test_creation(self):
        """测试创建"""
        temp = MarketTemperature(
            score=75.0,
            label="hot",
            description="市场情绪偏热",
        )
        assert temp.score == 75.0
        assert temp.label == "hot"


class TestRadarReport:
    """测试最终报告"""

    def test_creation(self):
        """测试创建"""
        report = RadarReport(
            as_of_date="2026-06-28",
            data_quality_score=86.5,
        )
        assert report.report_type == "theme_sector_radar"
        assert report.version == "0.1.0"
        assert report.as_of_date == "2026-06-28"

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        report = RadarReport(
            as_of_date="2026-06-28",
        )
        json_str = json.dumps(report.model_dump(), ensure_ascii=False)
        assert "theme_sector_radar" in json_str
        assert "0.1.0" in json_str

    def test_disclaimer_exists(self):
        """测试声明存在"""
        report = RadarReport(
            as_of_date="2026-06-28",
        )
        assert "不构成个股推荐" in report.disclaimer
        assert "买卖建议" in report.disclaimer
        assert "自动交易指令" in report.disclaimer
