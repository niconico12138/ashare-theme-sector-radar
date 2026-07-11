"""
Factor Composite Shadow Score 模块 (shadow-only)

基于 factor_snapshot 中的因子值，计算综合影子评分。
只做 shadow-only 评分和验证，不改变 final_score、候选池排序、Agent 排名逻辑。

组合方式：
- trend_bucket (35%): ma20_slope_5, near_high_250, stock_trend_score
- momentum_bucket (15%): stock_short_score_v2, amount_ratio_20
- volatility_bucket (15%): contraction_score
- sector_bucket (15%): sector_trend_score, sector_burst_score
- risk_bucket (10%): drawdown_risk_score, risk_penalty_score (反向)
- agent_bucket (10%): agent_score, trend_agent_score, short_agent_score

规则：
- 每个 bucket 内只使用存在且 quality 不是 missing 的因子
- bucket 内按等权平均
- 如果 bucket 没有有效因子，该 bucket 返回 50，并打 tag
- risk_bucket 要反向处理：风险分越高，组合贡献越低
- 总分限制在 0-100
"""

from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_factor_score(factor_snapshot: dict, factor_id: str) -> tuple[float | None, str]:
    """从 factor_snapshot 中提取因子分数和质量。

    Returns:
        (score, quality) 如果因子不存在或 missing，返回 (None, "missing")
    """
    factors = factor_snapshot.get("factors", [])
    for f in factors:
        if f.get("factor_id") == factor_id:
            quality = f.get("quality", "missing")
            if quality == "missing":
                return None, "missing"
            return f.get("score"), quality
    return None, "missing"


def _calc_bucket_score(
    factor_snapshot: dict,
    factor_ids: list[str],
    bucket_name: str,
    reverse: bool = False,
) -> dict:
    """计算单个 bucket 的分数。

    Args:
        factor_snapshot: 因子快照
        factor_ids: 该 bucket 包含的因子 ID 列表
        bucket_name: bucket 名称（用于 tag）
        reverse: 是否反向处理（用于 risk_bucket）

    Returns:
        dict with score, used_factors, missing_factors, tag
    """
    used_factors: list[str] = []
    missing_factors: list[str] = []
    scores: list[float] = []

    for factor_id in factor_ids:
        score, quality = _extract_factor_score(factor_snapshot, factor_id)
        if score is not None:
            used_factors.append(factor_id)
            scores.append(score)
        else:
            missing_factors.append(factor_id)

    if not scores:
        # 没有有效因子，返回中性值
        return {
            "score": 50.0,
            "used_factors": [],
            "missing_factors": missing_factors,
            "tag": f"{bucket_name}_no_valid_factors",
        }

    # 等权平均
    avg_score = sum(scores) / len(scores)

    # 反向处理（用于 risk_bucket）
    if reverse:
        avg_score = 100.0 - avg_score

    return {
        "score": round(avg_score, 2),
        "used_factors": used_factors,
        "missing_factors": missing_factors,
        "tag": "",
    }


def compute_factor_composite_shadow_score(candidate: dict) -> dict:
    """计算 Factor Composite Shadow Score。

    Args:
        candidate: 候选股字典，必须包含 factor_snapshot

    Returns:
        dict with:
            factor_composite_shadow_score: 综合影子评分 (0-100)
            factor_composite_breakdown: 分项明细
            factor_composite_tags: 标签列表
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}

    # 检查 factor_snapshot 是否存在
    factor_snapshot = candidate.get("factor_snapshot")
    if not factor_snapshot:
        tags.append("factor_snapshot_missing")
        return {
            "factor_composite_shadow_score": 50.0,
            "factor_composite_breakdown": {},
            "factor_composite_tags": tags,
        }

    # ============================================================
    # 各 bucket 配置
    # ============================================================
    bucket_configs = [
        {
            "name": "trend",
            "weight": 0.35,
            "factors": ["ma20_slope_5", "near_high_250", "stock_trend_score"],
            "reverse": False,
        },
        {
            "name": "momentum",
            "weight": 0.15,
            "factors": ["stock_short_score_v2", "amount_ratio_20"],
            "reverse": False,
        },
        {
            "name": "volatility",
            "weight": 0.15,
            "factors": ["contraction_score"],
            "reverse": False,
        },
        {
            "name": "sector",
            "weight": 0.15,
            "factors": ["sector_trend_score", "sector_burst_score"],
            "reverse": False,
        },
        {
            "name": "risk",
            "weight": 0.10,
            "factors": ["drawdown_risk_score", "risk_penalty_score"],
            "reverse": True,  # 风险分越高，贡献越低
        },
        {
            "name": "agent",
            "weight": 0.10,
            "factors": ["agent_score", "trend_agent_score", "short_agent_score"],
            "reverse": False,
        },
    ]

    # ============================================================
    # 计算各 bucket 分数
    # ============================================================
    total_score = 0.0
    total_weight = 0.0

    for config in bucket_configs:
        bucket_result = _calc_bucket_score(
            factor_snapshot,
            config["factors"],
            config["name"],
            reverse=config["reverse"],
        )

        # 记录 breakdown
        breakdown[config["name"]] = {
            "score": bucket_result["score"],
            "weight": config["weight"],
            "weighted_score": round(bucket_result["score"] * config["weight"], 2),
            "used_factors": bucket_result["used_factors"],
            "missing_factors": bucket_result["missing_factors"],
        }

        # 添加 tag
        if bucket_result["tag"]:
            tags.append(bucket_result["tag"])

        # 累加总分
        total_score += bucket_result["score"] * config["weight"]
        total_weight += config["weight"]

    # ============================================================
    # 归一化总分
    # ============================================================
    if total_weight > 0:
        final_score = total_score / total_weight
    else:
        final_score = 50.0

    # 限制在 0-100
    final_score = max(0.0, min(100.0, final_score))

    return {
        "factor_composite_shadow_score": round(final_score, 2),
        "factor_composite_breakdown": breakdown,
        "factor_composite_tags": tags,
    }
