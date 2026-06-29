"""
行业板块评分

行业板块总分 100 分:
- 趋势强度: 25分
- 资金流: 25分
- 板块宽度: 20分
- 持续性: 15分
- 市场适配: 10分
- 数据质量: 5分
"""

from typing import Any, Dict, List

from ..config import get_config
from ..models import SectorSnapshot


def calculate_trend_strength_score(snapshot: SectorSnapshot) -> float:
    """
    计算趋势强度得分 (0-25)

    考虑因素:
    - 当日涨跌幅
    - 成交额
    """
    score = 0.0

    # 涨跌幅得分 (0-15)
    change = snapshot.price_change_pct
    if change >= 5.0:
        score += 15.0
    elif change >= 3.0:
        score += 12.0
    elif change >= 1.0:
        score += 8.0
    elif change >= 0:
        score += 4.0
    else:
        score += 0.0

    # 成交额得分 (0-10)
    turnover = snapshot.turnover
    if turnover >= 10_000_000_000:  # 100亿
        score += 10.0
    elif turnover >= 5_000_000_000:  # 50亿
        score += 8.0
    elif turnover >= 1_000_000_000:  # 10亿
        score += 5.0
    else:
        score += 2.0

    return min(score, 25.0)


def calculate_capital_flow_score(snapshot: SectorSnapshot) -> float:
    """
    计算资金流得分 (0-25)

    考虑因素:
    - 主力净流入
    - 净流入占成交额比例
    """
    score = 0.0

    # 主力净流入得分 (0-15)
    inflow = snapshot.main_net_inflow
    if inflow >= 1_000_000_000:  # 10亿
        score += 15.0
    elif inflow >= 500_000_000:  # 5亿
        score += 12.0
    elif inflow >= 100_000_000:  # 1亿
        score += 8.0
    elif inflow >= 0:
        score += 4.0
    else:
        score += 0.0

    # 净流入占成交额比例得分 (0-10)
    if snapshot.turnover > 0:
        ratio = inflow / snapshot.turnover
        if ratio >= 0.1:
            score += 10.0
        elif ratio >= 0.05:
            score += 7.0
        elif ratio >= 0:
            score += 4.0
        else:
            score += 0.0
    else:
        score += 2.0

    return min(score, 25.0)


def calculate_sector_breadth_score(snapshot: SectorSnapshot) -> float:
    """
    计算板块宽度得分 (0-20)

    考虑因素:
    - 上涨家数比例
    - 核心成分股数量
    """
    score = 0.0

    constituents = snapshot.constituents
    if not constituents:
        return 5.0  # 无数据时给基础分

    total = len(constituents)
    advancing = sum(1 for c in constituents if c.change_pct > 0)
    core_count = sum(1 for c in constituents if c.is_core)

    # 上涨家数比例得分 (0-12)
    advance_ratio = advancing / total if total > 0 else 0
    if advance_ratio >= 0.8:
        score += 12.0
    elif advance_ratio >= 0.6:
        score += 9.0
    elif advance_ratio >= 0.4:
        score += 6.0
    else:
        score += 2.0

    # 核心成分股数量得分 (0-8)
    if core_count >= 5:
        score += 8.0
    elif core_count >= 3:
        score += 5.0
    elif core_count >= 1:
        score += 3.0
    else:
        score += 0.0

    return min(score, 20.0)


def calculate_continuity_score(snapshot: SectorSnapshot) -> float:
    """
    计算持续性得分 (0-15)

    第一版简化处理，基于成交额和涨跌幅的稳定性
    """
    score = 8.0  # 默认中等持续性

    # 高成交额 + 正涨幅 = 高持续性
    if snapshot.turnover >= 5_000_000_000 and snapshot.price_change_pct > 0:
        score = 12.0
    elif snapshot.turnover >= 1_000_000_000 and snapshot.price_change_pct > 0:
        score = 10.0
    elif snapshot.price_change_pct < 0:
        score = 5.0

    return min(score, 15.0)


def calculate_market_fit_score(
    snapshot: SectorSnapshot,
    market_temperature: float = 50.0
) -> float:
    """
    计算市场适配得分 (0-10)

    市场温度高时奖励进攻板块，市场弱时惩罚高波动题材
    """
    score = 5.0  # 默认适配

    # 高温市场 + 正涨幅板块 = 高适配
    if market_temperature >= 70 and snapshot.price_change_pct > 0:
        score = 8.0
    elif market_temperature >= 70 and snapshot.price_change_pct < 0:
        score = 3.0
    elif market_temperature < 30 and snapshot.price_change_pct > 2:
        score = 6.0  # 弱市中的强势板块
    elif market_temperature < 30 and snapshot.price_change_pct < 0:
        score = 2.0

    return min(score, 10.0)


def calculate_data_quality_score(snapshot: SectorSnapshot) -> float:
    """
    计算数据质量得分 (0-5)
    """
    score = 3.0  # 默认

    if snapshot.data_quality_score >= 80:
        score = 5.0
    elif snapshot.data_quality_score >= 60:
        score = 4.0
    elif snapshot.data_quality_score >= 40:
        score = 3.0
    else:
        score = 1.0

    return min(score, 5.0)


def calculate_industry_score(
    snapshot: SectorSnapshot,
    market_temperature: float = 50.0,
    config: Dict[str, Any] = None
) -> float:
    """
    计算行业板块总分 (0-100)

    各维度得分范围:
    - trend_strength: 0-25
    - capital_flow: 0-25
    - sector_breadth: 0-20
    - continuity: 0-15
    - market_fit: 0-10
    - data_quality: 0-5
    """
    breakdown = calculate_industry_score_breakdown(snapshot, market_temperature, config)
    return breakdown["final_score"]


def calculate_industry_score_breakdown(
    snapshot: SectorSnapshot,
    market_temperature: float = 50.0,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    计算行业板块评分 breakdown

    Returns:
        包含各维度得分的字典
    """
    if config is None:
        config = get_config()

    # 计算各维度得分 (各维度已定义最大值)
    trend_score = calculate_trend_strength_score(snapshot)  # 0-25
    flow_score = calculate_capital_flow_score(snapshot)  # 0-25
    breadth_score = calculate_sector_breadth_score(snapshot)  # 0-20
    continuity_score = calculate_continuity_score(snapshot)  # 0-15
    market_fit_score = calculate_market_fit_score(snapshot, market_temperature)  # 0-10
    data_quality_score_val = calculate_data_quality_score(snapshot)  # 0-5

    # 正向总分
    positive_score = (
        trend_score +
        flow_score +
        breadth_score +
        continuity_score +
        market_fit_score +
        data_quality_score_val
    )

    return {
        "trend_strength": round(trend_score, 2),
        "fund_flow": round(flow_score, 2),
        "breadth": round(breadth_score, 2),
        "persistence": round(continuity_score, 2),
        "market_fit": round(market_fit_score, 2),
        "data_quality": round(data_quality_score_val, 2),
        "positive_score": round(positive_score, 2),
        "final_score": round(min(positive_score, 100.0), 2),
    }
