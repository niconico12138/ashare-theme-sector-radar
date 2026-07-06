"""
数据模型定义

定义 Theme Sector Radar 的核心数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SectorType(str, Enum):
    """板块类型"""
    INDUSTRY = "industry"
    CONCEPT = "concept"


class FocusLevel(str, Enum):
    """关注等级"""
    FOCUS = "focus"
    WATCH = "watch"
    CORE_ONLY = "core_only"
    CAUTION = "caution"
    AVOID = "avoid"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConceptPhase(str, Enum):
    """概念阶段"""
    STARTUP = "startup"
    FERMENTATION = "fermentation"
    ACCELERATION = "acceleration"
    DIVERGENCE = "divergence"
    RETREAT = "retreat"


class AgentStatus(str, Enum):
    """Agent 状态"""
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


class FlowAlignment(str, Enum):
    """资金流向对齐"""
    BOTH_INFLOW = "both_inflow"
    BOTH_OUTFLOW = "both_outflow"
    INDUSTRY_INFLOW = "industry_inflow"
    CONCEPT_INFLOW = "concept_inflow"
    MISALIGNED = "misaligned"


class ConstituentSnapshot(BaseModel):
    """成分股快照"""
    code: str
    name: str
    change_pct: float = 0.0
    turnover: float = 0.0
    is_core: bool = False


class SectorSnapshot(BaseModel):
    """板块快照"""
    sector_id: str
    name: str
    type: SectorType
    price_change_pct: float = 0.0
    turnover: float = 0.0
    main_net_inflow: float = 0.0
    constituents: List[ConstituentSnapshot] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    updated_at: str = ""
    data_quality_score: float = 0.0
    price_change_available: bool = True  # 涨跌幅是否可用


class AgentOutput(BaseModel):
    """Agent 输出"""
    agent_id: str
    status: AgentStatus = AgentStatus.OK
    data: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    updated_at: str = ""
    data_quality_score: float = 0.0


class SectorScore(BaseModel):
    """板块评分"""
    sector_id: str
    name: str
    type: SectorType
    score: float = 0.0
    positive_score: float = 0.0
    risk_penalty: float = 0.0
    focus_level: FocusLevel = FocusLevel.WATCH
    phase: ConceptPhase = ConceptPhase.STARTUP
    risk_level: RiskLevel = RiskLevel.LOW
    risk_flags: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    downgrade_reasons: List[str] = Field(default_factory=list)
    watch_points: List[str] = Field(default_factory=list)
    constituents: List[ConstituentSnapshot] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    updated_at: str = ""
    data_quality_score: float = 0.0
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    previous_rank: Optional[int] = None
    rank_change: Optional[int] = None


class ResonanceResult(BaseModel):
    """共振结果"""
    industry: str
    concept: str
    resonance_score: float = 0.0
    overlap_constituent_count: int = 0
    common_core_count: int = 0
    flow_alignment: FlowAlignment = FlowAlignment.MISALIGNED
    both_top_n: bool = False
    focus_level: FocusLevel = FocusLevel.WATCH
    constituents: List[ConstituentSnapshot] = Field(default_factory=list)


class MarketTemperature(BaseModel):
    """市场温度"""
    score: float = 50.0
    label: str = "neutral"
    description: str = ""
    advance_count: int = 0
    decline_count: int = 0
    limit_up_count: int = 0
    limit_down_count: int = 0


class RadarContext(BaseModel):
    """雷达上下文"""
    as_of_date: str
    config: Dict[str, Any] = Field(default_factory=dict)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    normalized_data: Dict[str, Any] = Field(default_factory=dict)
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    updated_at: str = ""
    data_quality_score: float = 0.0


class ProviderStatus(BaseModel):
    """数据提供者状态"""
    industry_sectors: str = "ok"
    concept_sectors: str = "ok"
    fund_flow: str = "ok"
    constituents: str = "ok"
    # 数据来源追踪字段
    effective_provider: str = "akshare"  # akshare / ths / mixed / fixture
    industry_source: str = ""  # akshare/eastmoney_industry / akshare/ths_industry
    concept_source: str = ""  # akshare/eastmoney_concept / akshare/ths_concept
    fallback_used: bool = False  # 是否使用了 fallback
    fallback_provider: str = ""  # fallback 提供者 (ths)
    fallback_reason: str = ""  # fallback 原因 (EM 失败原因摘要)
    industry_count: int = 0  # 行业板块实际获取数量
    concept_count: int = 0  # 概念板块实际获取数量
    em_industry_error: str = ""  # EM 行业接口错误信息
    em_concept_error: str = ""  # EM 概念接口错误信息
    concept_price_change_available: bool = True  # 概念涨跌幅是否可用


class DataCompleteness(BaseModel):
    """数据完整性"""
    industry_count: int = 0
    concept_count: int = 0
    industry_min_count: int = 20
    concept_min_count: int = 20


class RadarReport(BaseModel):
    """最终报告"""
    report_type: str = "theme_sector_radar"
    version: str = "0.1.0"
    as_of_date: str
    updated_at: str = ""
    data_sources: List[str] = Field(default_factory=list)
    data_quality_score: float = 0.0
    market_temperature: MarketTemperature = Field(default_factory=MarketTemperature)
    industry_top: List[SectorScore] = Field(default_factory=list)
    concept_top: List[SectorScore] = Field(default_factory=list)
    overlap: List[ResonanceResult] = Field(default_factory=list)
    risk_summary: Dict[str, Any] = Field(default_factory=dict)
    data_quality: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。"
    status: str = "ok"
    provider_status: ProviderStatus = Field(default_factory=ProviderStatus)
    data_completeness: DataCompleteness = Field(default_factory=DataCompleteness)
    cache_fallback: Dict[str, Any] = Field(default_factory=dict)
    fund_flow_coverage: Dict[str, Any] = Field(default_factory=dict)
    constituent_coverage: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    rotation_summary: Dict[str, Any] = Field(default_factory=dict)
    comparison: Dict[str, Any] = Field(default_factory=dict)
    # 数据来源追踪字段
    run_mode: str = "normal"  # daily / replay / normal
    provider: str = "fixture"  # fixture / akshare
    offline_fixture: bool = False
    fixture_profile: Optional[str] = None
    data_source_mode: str = "fixture"  # fixture / akshare_refresh / cache_replay / cache_fallback
    report_dir: str = ""
    generated_by_command: str = ""
    # Phase 13: unified pipeline integration
    unified_observation_pool: Optional[Dict[str, Any]] = None
    unified_data_source: Optional[Dict[str, Any]] = None
    unified_run_health: Optional[Dict[str, Any]] = None
    unified_pipeline_error: Optional[str] = None
