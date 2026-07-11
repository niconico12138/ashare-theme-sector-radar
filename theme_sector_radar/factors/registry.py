"""
因子元数据注册表

定义首批 13 个因子的元数据信息。
每个因子包含：factor_id, display_name, category, source_project, direction, lookback_days, enabled, description
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FactorMetadata:
    """因子元数据定义。

    Attributes:
        factor_id: 因子唯一标识符
        display_name: 中文显示名
        category: 因子类别
        source_project: 来源项目/模块
        direction: 评分方向
        lookback_days: 回溯天数
        enabled: 是否启用
        description: 因子描述
    """

    factor_id: str
    display_name: str
    category: str  # trend/momentum/volatility/volume/risk/reversal/sector/agent/composite
    source_project: str
    direction: str  # higher_is_better/lower_is_better/neutral/already_scored
    lookback_days: int | None
    enabled: bool
    description: str


# 批量定义因子元数据
FACTOR_REGISTRY: dict[str, FactorMetadata] = {}


def _register(factor: FactorMetadata) -> None:
    """注册一个因子。"""
    FACTOR_REGISTRY[factor.factor_id] = factor


# ============================================================
# 趋势类因子 (trend)
# ============================================================

_register(FactorMetadata(
    factor_id="ma20_slope_5",
    display_name="MA20斜率(5日)",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=5,
    enabled=True,
    description="MA20 均线在最近5个交易日的斜率百分比，衡量中期趋势方向",
))

_register(FactorMetadata(
    factor_id="stock_trend_score",
    display_name="个股趋势分",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="个股维度中长线趋势评分(0-100)，基于MA均线体系、突破前高、回撤控制、量价配合",
))

# ============================================================
# 动量类因子 (momentum)
# ============================================================

_register(FactorMetadata(
    factor_id="stock_short_score",
    display_name="个股短线分",
    category="momentum",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="个股维度短线动量评分(0-100)，区别于板块级burst_score",
))

_register(FactorMetadata(
    factor_id="stock_short_score_v2",
    display_name="个股短线分V2",
    category="momentum",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="个股短线动量评分V2(shadow实验)，改进短线评分逻辑",
))

# ============================================================
# 风险类因子 (risk)
# ============================================================

_register(FactorMetadata(
    factor_id="drawdown_risk_score",
    display_name="回撤风险分",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="lower_is_better",
    lookback_days=10,
    enabled=True,
    description="真实回撤风险评分(0-50)，包括冲高回落、超涨、趋势走弱等信号",
))

_register(FactorMetadata(
    factor_id="risk_penalty_score",
    display_name="风险惩罚分",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="lower_is_better",
    lookback_days=None,
    enabled=True,
    description="综合风险惩罚评分，包括ST、退市、流动性、数据缺失等硬风险",
))

# ============================================================
# 影子评分因子 (agent)
# ============================================================

_register(FactorMetadata(
    factor_id="regime_router_shadow_score_v5",
    display_name="Regime路由影子分V5",
    category="agent",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="Regime Router Shadow Score V5(shadow-only)，根据市场regime选择合适的影子评分",
))

# ============================================================
# 板块类因子 (sector)
# ============================================================

_register(FactorMetadata(
    factor_id="sector_trend_score",
    display_name="板块趋势分",
    category="sector",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=20,
    enabled=True,
    description="板块维度趋势评分(0-100)，衡量板块整体趋势强度",
))

_register(FactorMetadata(
    factor_id="sector_burst_score",
    display_name="板块短线分",
    category="sector",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=5,
    enabled=True,
    description="板块维度短线爆发评分(0-100)，衡量板块短期热度",
))

# ============================================================
# 综合评分因子 (composite)
# ============================================================

_register(FactorMetadata(
    factor_id="final_score",
    display_name="最终综合分",
    category="composite",
    source_project="theme-sector-radar-dev",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="综合多个维度的最终评分，用于候选池排序",
))

# ============================================================
# Agent 评分因子 (agent)
# ============================================================

_register(FactorMetadata(
    factor_id="agent_score",
    display_name="Agent综合分",
    category="agent",
    source_project="ai-hedge-fund",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="AI Agent 综合评分，由 24 Agent 分析后产出",
))

_register(FactorMetadata(
    factor_id="trend_agent_score",
    display_name="趋势Agent分",
    category="agent",
    source_project="ai-hedge-fund",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="趋势类 Agent 评分",
))

_register(FactorMetadata(
    factor_id="short_agent_score",
    display_name="短线Agent分",
    category="agent",
    source_project="ai-hedge-fund",
    direction="already_scored",
    lookback_days=None,
    enabled=True,
    description="短线动量类 Agent 评分",
))

# ============================================================
# Bars 因子 (trend/volatility/volume) - 第二阶段新增
# ============================================================

_register(FactorMetadata(
    factor_id="near_high_250",
    display_name="距250日新高",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=250,
    enabled=True,
    description="当前价格距离250日（约一年）最高价的百分比，衡量长期趋势位置",
))

_register(FactorMetadata(
    factor_id="contraction_score",
    display_name="收缩评分",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="ATR/价格比和振幅收缩程度的综合评分，收缩后往往有方向选择",
))

_register(FactorMetadata(
    factor_id="atr10_atr50",
    display_name="ATR10/ATR50",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="neutral",
    lookback_days=50,
    enabled=True,
    description="10日ATR与50日ATR的比值，衡量短期波动相对于长期波动的变化",
))

_register(FactorMetadata(
    factor_id="range10_range20",
    display_name="振幅10/振幅20",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="neutral",
    lookback_days=20,
    enabled=True,
    description="10日振幅与20日振幅的比值，衡量短期振幅相对于中期振幅的变化",
))

_register(FactorMetadata(
    factor_id="range20_range60",
    display_name="振幅20/振幅60",
    category="volatility",
    source_project="theme-sector-radar-dev",
    direction="neutral",
    lookback_days=60,
    enabled=True,
    description="20日振幅与60日振幅的比值，衡量中期振幅相对于长期振幅的变化",
))

_register(FactorMetadata(
    factor_id="amount_ratio_20",
    display_name="成交额比(20日)",
    category="volume",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="最近5日平均成交额与20日平均成交额的比值，衡量近期资金活跃度变化",
))

# ============================================================
# 个股增强因子 (stock_quality) - 第二十一阶段-B 新增
# ============================================================

_register(FactorMetadata(
    factor_id="liquidity_score",
    display_name="流动性评分",
    category="liquidity",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="基于近20日成交额水平的流动性评分，分数越高表示流动性越好",
))

_register(FactorMetadata(
    factor_id="chasing_risk_score",
    display_name="追高风险评分",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="lower_is_better",
    lookback_days=10,
    enabled=True,
    description="基于短期涨幅和价格位置的追高风险评分，分数越高表示短期过热风险越高",
))

_register(FactorMetadata(
    factor_id="drawdown_depth_20",
    display_name="20日回撤深度",
    category="risk",
    source_project="theme-sector-radar-dev",
    direction="lower_is_better",
    lookback_days=20,
    enabled=True,
    description="当前价格相对近20日高点的回撤幅度",
))

_register(FactorMetadata(
    factor_id="breakout_distance_20",
    display_name="距20日突破距离",
    category="trend",
    source_project="theme-sector-radar-dev",
    direction="neutral",
    lookback_days=20,
    enabled=True,
    description="当前价格距离近20日高点的百分比距离，仅用于观察结构，不作为交易触发",
))

_register(FactorMetadata(
    factor_id="sector_support_score",
    display_name="板块支持评分",
    category="sector",
    source_project="theme-sector-radar-dev",
    direction="higher_is_better",
    lookback_days=20,
    enabled=True,
    description="个股所属板块对个股观察的支持程度",
))


def get_factor_metadata(factor_id: str) -> FactorMetadata | None:
    """获取因子元数据。

    Args:
        factor_id: 因子唯一标识符

    Returns:
        FactorMetadata 或 None（如果因子不存在）
    """
    return FACTOR_REGISTRY.get(factor_id)


def list_enabled_factors() -> list[FactorMetadata]:
    """列出所有启用的因子。"""
    return [f for f in FACTOR_REGISTRY.values() if f.enabled]
