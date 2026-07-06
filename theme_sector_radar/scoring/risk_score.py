"""
风险评分

计算风险扣分、风险等级和风险标志。
所有风险扣分使用正数表示。
"""

from typing import Any, Dict, List, Tuple

from ..config import get_config
from ..models import RiskLevel, SectorSnapshot


def detect_overheat(
    snapshot: SectorSnapshot,
    config: Dict[str, Any] = None
) -> Tuple[bool, float, str]:
    """
    检测过热风险

    返回: (is_overheat, penalty, reason)
    penalty 为正数，表示扣分值
    """
    if config is None:
        config = get_config()

    thresholds = config.get("risk_thresholds", {})
    penalty_config = config.get("risk_penalty", {})

    is_overheat = False
    penalty = 0.0
    reasons = []

    # 短期涨幅过大
    if snapshot.price_change_pct >= thresholds.get("overheat_short_term_gain", 15.0):
        is_overheat = True
        penalty += abs(penalty_config.get("overheat_max", -20)) * 0.6
        reasons.append(f"短期涨幅过大 ({snapshot.price_change_pct:.1f}%)")

    # 成交额异常放大
    if snapshot.turnover >= 20_000_000_000:  # 200亿
        is_overheat = True
        penalty += abs(penalty_config.get("overheat_max", -20)) * 0.4
        reasons.append(f"成交额异常放大 ({snapshot.turnover/1e8:.0f}亿)")

    # 综合过热
    if is_overheat:
        penalty = min(penalty, abs(penalty_config.get("overheat_max", -20)))
        reason = "过热: " + "; ".join(reasons)
        return True, penalty, reason

    return False, 0.0, ""


def detect_divergence(
    snapshot: SectorSnapshot,
    config: Dict[str, Any] = None
) -> Tuple[bool, float, str]:
    """
    检测分歧风险

    返回: (is_divergent, penalty, reason)
    penalty 为正数，表示扣分值
    """
    if config is None:
        config = get_config()

    thresholds = config.get("risk_thresholds", {})
    penalty_config = config.get("risk_penalty", {})

    is_divergent = False
    penalty = 0.0
    reasons = []

    constituents = snapshot.constituents
    if constituents:
        total = len(constituents)
        advancing = sum(1 for c in constituents if c.change_pct > 0)
        advance_ratio = advancing / total if total > 0 else 0

        # 上涨家数不足但板块指数上涨
        if snapshot.price_change_pct > 0 and advance_ratio < thresholds.get("divergence_advance_ratio", 0.4):
            is_divergent = True
            penalty += abs(penalty_config.get("divergence_max", -15)) * 0.5
            reasons.append(f"上涨家数不足 ({advance_ratio:.0%})")

        # 少数核心股硬拉
        core_count = sum(1 for c in constituents if c.is_core)
        core_advancing = sum(1 for c in constituents if c.is_core and c.change_pct > 0)
        if core_count > 0 and core_advancing / core_count > 0.8 and advance_ratio < 0.5:
            is_divergent = True
            penalty += abs(penalty_config.get("divergence_max", -15)) * 0.3
            reasons.append("少数核心股硬拉")

    # 资金流与价格背离
    if snapshot.price_change_pct > 0 and snapshot.main_net_inflow < 0:
        is_divergent = True
        penalty += abs(penalty_config.get("divergence_max", -15)) * 0.4
        reasons.append("资金流与价格背离")

    if is_divergent:
        penalty = min(penalty, abs(penalty_config.get("divergence_max", -15)))
        reason = "分歧: " + "; ".join(reasons)
        return True, penalty, reason

    return False, 0.0, ""


def assess_data_quality_risk(
    snapshot: SectorSnapshot,
    config: Dict[str, Any] = None
) -> Tuple[bool, float, str]:
    """
    评估数据质量风险

    返回: (is_low_quality, penalty, reason)
    penalty 为正数，表示扣分值
    """
    if config is None:
        config = get_config()

    penalty_config = config.get("risk_penalty", {})

    is_low_quality = False
    penalty = 0.0
    reasons = []

    # 数据质量分低
    if snapshot.data_quality_score < 40:
        is_low_quality = True
        penalty += abs(penalty_config.get("data_quality_max", -10)) * 0.7
        reasons.append(f"数据质量分过低 ({snapshot.data_quality_score:.0f})")
    elif snapshot.data_quality_score < 60:
        is_low_quality = True
        penalty += abs(penalty_config.get("data_quality_max", -10)) * 0.4
        reasons.append(f"数据质量分偏低 ({snapshot.data_quality_score:.0f})")

    # 数据源不足
    has_sector_index_source = any(
        (source.startswith("sector_history/ths_") and source.endswith("_index"))
        or source == "akshare/ths_industry"
        or source in {"akshare/eastmoney_industry", "akshare/eastmoney_concept"}
        for source in snapshot.data_sources
    )
    has_price_index_data = (
        has_sector_index_source
        and snapshot.price_change_available
        and bool(snapshot.updated_at)
    )

    if len(snapshot.data_sources) < 2 and not has_price_index_data:
        is_low_quality = True
        penalty += abs(penalty_config.get("data_quality_max", -10)) * 0.3
        reasons.append(f"数据源不足 ({len(snapshot.data_sources)}个)")


    if is_low_quality:
        penalty = min(penalty, abs(penalty_config.get("data_quality_max", -10)))
        reason = "数据质量: " + "; ".join(reasons)
        return True, penalty, reason

    return False, 0.0, ""


def calculate_risk_penalty(
    snapshot: SectorSnapshot,
    config: Dict[str, Any] = None
) -> Tuple[float, RiskLevel, List[str], List[str]]:
    """
    计算总风险扣分

    返回: (risk_penalty, risk_level, risk_flags, risk_reasons)
    risk_penalty 为正数，表示总扣分值
    """
    breakdown = calculate_risk_breakdown(snapshot, config)
    return breakdown["total_penalty"], breakdown["risk_level"], breakdown["risk_flags"], breakdown["risk_reasons"]


def calculate_risk_breakdown(
    snapshot: SectorSnapshot,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    计算风险 breakdown

    Returns:
        包含各风险维度扣分的字典，所有扣分为正数
    """
    if config is None:
        config = get_config()

    total_penalty = 0.0
    risk_flags = []
    risk_reasons = []

    # 过热检测
    is_overheat, overheat_penalty, overheat_reason = detect_overheat(snapshot, config)
    if is_overheat:
        total_penalty += overheat_penalty
        risk_flags.append("overheat")
        risk_reasons.append(overheat_reason)

    # 分歧检测
    is_divergent, divergence_penalty, divergence_reason = detect_divergence(snapshot, config)
    if is_divergent:
        total_penalty += divergence_penalty
        risk_flags.append("divergence")
        risk_reasons.append(divergence_reason)

    # 数据质量风险
    is_low_quality, quality_penalty, quality_reason = assess_data_quality_risk(snapshot, config)
    if is_low_quality:
        total_penalty += quality_penalty
        risk_flags.append("data_quality_low")
        risk_reasons.append(quality_reason)

    # 确定风险等级（基于扣分大小）
    if total_penalty >= 15:
        risk_level = RiskLevel.HIGH
    elif total_penalty >= 8:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    # 限制总扣分范围
    total_penalty = min(total_penalty, 30.0)

    return {
        "overheat_penalty": round(overheat_penalty if is_overheat else 0.0, 2),
        "divergence_penalty": round(divergence_penalty if is_divergent else 0.0, 2),
        "data_quality_penalty": round(quality_penalty if is_low_quality else 0.0, 2),
        "total_penalty": round(total_penalty, 2),
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "risk_reasons": risk_reasons,
    }
