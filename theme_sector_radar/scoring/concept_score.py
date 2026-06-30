"""
概念板块评分

概念板块总分 100 分:
- 热度爆发: 25分
- 资金确认: 20分
- 成分股联动: 20分
- 阶段判断: 20分
- 催化剂: 10分
- 数据质量: 5分
"""

from typing import Any, Dict, List

from ..config import get_config
from ..models import ConceptPhase, SectorSnapshot


def calculate_heat_burst_score(snapshot: SectorSnapshot) -> float:
    """
    计算热度爆发得分 (0-25)

    考虑因素:
    - 当日涨幅
    - 成交额突增

    注意: 当 price_change_available=False 时，涨幅部分得分为 0，仅保留成交额得分
    """
    score = 0.0

    # 涨幅得分 (0-15) - 仅当涨跌幅可用时计算
    if snapshot.price_change_available:
        change = snapshot.price_change_pct
        if change >= 8.0:
            score += 15.0
        elif change >= 5.0:
            score += 12.0
        elif change >= 3.0:
            score += 9.0
        elif change >= 1.0:
            score += 5.0
        else:
            score += 1.0
    # else: 涨跌幅不可用，涨幅部分得分为 0

    # 成交额突增得分 (0-10)
    turnover = snapshot.turnover
    if turnover >= 20_000_000_000:  # 200亿
        score += 10.0
    elif turnover >= 10_000_000_000:  # 100亿
        score += 8.0
    elif turnover >= 5_000_000_000:  # 50亿
        score += 5.0
    else:
        score += 2.0

    return min(score, 25.0)


def calculate_capital_confirm_score(snapshot: SectorSnapshot) -> float:
    """
    计算资金确认得分 (0-20)

    考虑因素:
    - 主力净流入
    - 资金集中度
    """
    score = 0.0

    # 主力净流入得分 (0-12)
    inflow = snapshot.main_net_inflow
    if inflow >= 2_000_000_000:  # 20亿
        score += 12.0
    elif inflow >= 1_000_000_000:  # 10亿
        score += 10.0
    elif inflow >= 500_000_000:  # 5亿
        score += 7.0
    elif inflow >= 0:
        score += 3.0
    else:
        score += 0.0

    # 资金集中度得分 (0-8)
    if snapshot.turnover > 0:
        ratio = inflow / snapshot.turnover
        if ratio >= 0.15:
            score += 8.0
        elif ratio >= 0.1:
            score += 6.0
        elif ratio >= 0.05:
            score += 4.0
        else:
            score += 1.0
    else:
        score += 2.0

    return min(score, 20.0)


def calculate_constituent_synergy_score(snapshot: SectorSnapshot) -> float:
    """
    计算成分股联动得分 (0-20)

    考虑因素:
    - 上涨家数
    - 大涨家数
    - 核心股带队
    """
    score = 0.0

    constituents = snapshot.constituents
    if not constituents:
        return 5.0

    total = len(constituents)
    advancing = sum(1 for c in constituents if c.change_pct > 0)
    surging = sum(1 for c in constituents if c.change_pct >= 5.0)
    core_surging = sum(1 for c in constituents if c.is_core and c.change_pct > 0)

    # 上涨家数比例得分 (0-8)
    advance_ratio = advancing / total if total > 0 else 0
    if advance_ratio >= 0.9:
        score += 8.0
    elif advance_ratio >= 0.7:
        score += 6.0
    elif advance_ratio >= 0.5:
        score += 4.0
    else:
        score += 1.0

    # 大涨家数得分 (0-6)
    if surging >= 5:
        score += 6.0
    elif surging >= 3:
        score += 4.0
    elif surging >= 1:
        score += 2.0
    else:
        score += 0.0

    # 核心股带队得分 (0-6)
    if core_surging >= 3:
        score += 6.0
    elif core_surging >= 2:
        score += 4.0
    elif core_surging >= 1:
        score += 2.0
    else:
        score += 0.0

    return min(score, 20.0)


def calculate_phase_judgment_score(phase: ConceptPhase) -> float:
    """
    计算阶段判断得分 (0-20)

    阶段评分:
    - 加速阶段: 最高分
    - 发酵阶段: 次高分
    - 启动阶段: 中等分
    - 分歧阶段: 低分
    - 退潮阶段: 最低分
    """
    phase_scores = {
        ConceptPhase.ACCELERATION: 18.0,
        ConceptPhase.FERMENTATION: 15.0,
        ConceptPhase.STARTUP: 12.0,
        ConceptPhase.DIVERGENCE: 8.0,
        ConceptPhase.RETREAT: 3.0,
    }
    return phase_scores.get(phase, 10.0)


def calculate_catalyst_score(snapshot: SectorSnapshot) -> float:
    """
    计算催化剂得分 (0-10)

    第一版简化处理，基于涨幅和成交额

    注意: 当 price_change_available=False 时，返回中性默认分 3.0
    """
    # 涨跌幅不可用时，返回中性默认分
    if not snapshot.price_change_available:
        return 3.0

    score = 5.0  # 默认

    if snapshot.price_change_pct >= 5 and snapshot.turnover >= 10_000_000_000:
        score = 8.0
    elif snapshot.price_change_pct >= 3:
        score = 6.0
    elif snapshot.price_change_pct < 0:
        score = 3.0

    return min(score, 10.0)


def calculate_concept_data_quality_score(snapshot: SectorSnapshot) -> float:
    """
    计算数据质量得分 (0-5)
    """
    score = 3.0

    if snapshot.data_quality_score >= 80:
        score = 5.0
    elif snapshot.data_quality_score >= 60:
        score = 4.0
    elif snapshot.data_quality_score >= 40:
        score = 3.0
    else:
        score = 1.0

    return min(score, 5.0)


def calculate_concept_phase(snapshot: SectorSnapshot) -> ConceptPhase:
    """
    计算概念阶段

    基于涨幅和成交额判断阶段

    注意: 当 price_change_available=False 时，返回 DIVERGENCE（数据不足）
    """
    # 涨跌幅不可用时，返回 DIVERGENCE（数据不足）
    if not snapshot.price_change_available:
        return ConceptPhase.DIVERGENCE

    change = snapshot.price_change_pct
    turnover = snapshot.turnover

    if change >= 5 and turnover >= 10_000_000_000:
        return ConceptPhase.ACCELERATION
    elif change >= 3 and turnover >= 5_000_000_000:
        return ConceptPhase.FERMENTATION
    elif change >= 1:
        return ConceptPhase.STARTUP
    elif change >= -2:
        return ConceptPhase.DIVERGENCE
    else:
        return ConceptPhase.RETREAT


def calculate_concept_score(
    snapshot: SectorSnapshot,
    phase: ConceptPhase = None,
    config: Dict[str, Any] = None
) -> float:
    """
    计算概念板块总分 (0-100)

    各维度得分范围:
    - heat_burst: 0-25
    - capital_confirm: 0-20
    - constituent_synergy: 0-20
    - phase_judgment: 0-20
    - catalyst: 0-10
    - data_quality: 0-5
    """
    breakdown = calculate_concept_score_breakdown(snapshot, phase, config)
    return breakdown["final_score"]


def calculate_concept_score_breakdown(
    snapshot: SectorSnapshot,
    phase: ConceptPhase = None,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    计算概念板块评分 breakdown

    Returns:
        包含各维度得分的字典
    """
    if config is None:
        config = get_config()

    # 计算阶段
    if phase is None:
        phase = calculate_concept_phase(snapshot)

    # 计算各维度得分 (各维度已定义最大值)
    heat_score = calculate_heat_burst_score(snapshot)  # 0-25
    capital_score = calculate_capital_confirm_score(snapshot)  # 0-20
    synergy_score = calculate_constituent_synergy_score(snapshot)  # 0-20
    phase_score_val = calculate_phase_judgment_score(phase)  # 0-20
    catalyst_score = calculate_catalyst_score(snapshot)  # 0-10
    data_quality_score_val = calculate_concept_data_quality_score(snapshot)  # 0-5

    # 正向总分
    positive_score = (
        heat_score +
        capital_score +
        synergy_score +
        phase_score_val +
        catalyst_score +
        data_quality_score_val
    )

    result = {
        "heat_burst": round(heat_score, 2),
        "fund_confirmation": round(capital_score, 2),
        "constituent_linkage": round(synergy_score, 2),
        "phase_score": round(phase_score_val, 2),
        "catalyst": round(catalyst_score, 2),
        "data_quality": round(data_quality_score_val, 2),
        "positive_score": round(positive_score, 2),
        "final_score": round(min(positive_score, 100.0), 2),
        "price_change_available": snapshot.price_change_available,
    }

    # 如果涨跌幅不可用，添加警告
    if not snapshot.price_change_available:
        result["data_quality_warning"] = "THS 概念缺少涨跌幅数据，热度爆发和催化剂评分偏保守"
        result["max_possible_score_without_price"] = round(
            10 + capital_score + synergy_score + phase_score_val + 3 + data_quality_score_val, 2
        )

    return result
