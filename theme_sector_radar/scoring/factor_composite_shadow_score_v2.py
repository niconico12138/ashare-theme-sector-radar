"""
Factor Composite Shadow Score V2 模块 (shadow-only)

基于第九阶段归因结果，新增 v2 评分。
v2 只做 shadow-only 实验评分，不替换 v1，不改变 final_score、候选池排序。

v2 权重：
- trend_bucket (30%): stock_trend_score, ma20_slope_5, near_high_250
- risk_bucket (50%): drawdown_risk_score (higher_is_better), risk_penalty_score (lower_is_better)
- neutral_residual (20%): 固定 50 分

死桶处理：
- 不使用 momentum / volatility / sector / agent bucket
- 这些 bucket 恒定为 50，无分布
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


def _calc_bucket_score_v2(
    factor_snapshot: dict,
    factor_ids: list[str],
    bucket_name: str,
    reverse: bool = False,
) -> dict:
    """计算单个 bucket 的分数（v2 版本）。

    Args:
        factor_snapshot: 因子快照
        factor_ids: 该 bucket 包含的因子 ID 列表
        bucket_name: bucket 名称（用于 tag）
        reverse: 是否反向处理

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
            "tag": f"v2_{bucket_name}_no_valid_factors",
        }

    # 等权平均
    avg_score = sum(scores) / len(scores)

    # 反向处理（用于 lower_is_better 因子）
    if reverse:
        avg_score = 100.0 - avg_score

    return {
        "score": round(avg_score, 2),
        "used_factors": used_factors,
        "missing_factors": missing_factors,
        "tag": "",
    }


def compute_factor_composite_shadow_score_v2(candidate: dict) -> dict:
    """计算 Factor Composite Shadow Score V2。

    v2 基于归因结果优化：
    - 降低 trend 权重（从 35% 到 30%）
    - 提高 risk 权重（从 10% 到 50%）
    - 剔除恒定 bucket（momentum, volatility, sector, agent）
    - drawdown_risk_score 按 higher_is_better 处理
    - risk_penalty_score 按 lower_is_better 处理

    Args:
        candidate: 候选股字典，必须包含 factor_snapshot

    Returns:
        dict with:
            factor_composite_shadow_score_v2: v2 综合影子评分 (0-100)
            factor_composite_breakdown_v2: v2 分项明细
            factor_composite_tags_v2: v2 标签列表
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}

    # 检查 factor_snapshot 是否存在
    factor_snapshot = candidate.get("factor_snapshot")
    if not factor_snapshot:
        tags.append("v2_missing_factor_snapshot")
        return {
            "factor_composite_shadow_score_v2": 50.0,
            "factor_composite_breakdown_v2": {},
            "factor_composite_tags_v2": tags,
        }

    # ============================================================
    # 死桶处理：跳过 momentum / volatility / sector / agent
    # ============================================================
    dead_buckets = ["momentum", "volatility", "sector", "agent"]
    for bucket in dead_buckets:
        tags.append(f"v2_skip_dead_bucket_{bucket}")

    # ============================================================
    # v2 bucket 配置
    # ============================================================
    bucket_configs = [
        {
            "name": "trend",
            "weight": 0.30,
            "factors": ["stock_trend_score", "ma20_slope_5", "near_high_250"],
            "reverse": False,  # higher_is_better
        },
        {
            "name": "risk",
            "weight": 0.50,
            "factors": ["drawdown_risk_score", "risk_penalty_score"],
            "reverse": False,  # 特殊处理：drawdown_risk_score higher_is_better, risk_penalty_score lower_is_better
        },
        {
            "name": "neutral_residual",
            "weight": 0.20,
            "factors": [],  # 固定 50 分
            "reverse": False,
        },
    ]

    # ============================================================
    # 计算各 bucket 分数
    # ============================================================
    total_score = 0.0
    total_weight = 0.0

    for config in bucket_configs:
        bucket_name = config["name"]

        if bucket_name == "neutral_residual":
            # 固定 50 分
            bucket_score = 50.0
            used_factors = []
            missing_factors = []
            tag = ""
        elif bucket_name == "risk":
            # 特殊处理 risk bucket
            # drawdown_risk_score: lower_is_better (风险分越低越好)
            # risk_penalty_score: lower_is_better (风险分越低越好)
            drawdown_score, drawdown_quality = _extract_factor_score(factor_snapshot, "drawdown_risk_score")
            risk_penalty_score, risk_penalty_quality = _extract_factor_score(factor_snapshot, "risk_penalty_score")

            used_factors = []
            missing_factors = []
            scores = []

            if drawdown_score is not None:
                used_factors.append("drawdown_risk_score")
                scores.append(100.0 - drawdown_score)  # lower_is_better, 反向处理
            else:
                missing_factors.append("drawdown_risk_score")

            if risk_penalty_score is not None:
                used_factors.append("risk_penalty_score")
                scores.append(100.0 - risk_penalty_score)  # lower_is_better, 反向处理
            else:
                missing_factors.append("risk_penalty_score")

            if scores:
                bucket_score = sum(scores) / len(scores)
                tag = ""
            else:
                bucket_score = 50.0
                tag = "v2_risk_no_valid_factors"
        else:
            # trend bucket
            bucket_result = _calc_bucket_score_v2(
                factor_snapshot,
                config["factors"],
                bucket_name,
                reverse=config["reverse"],
            )
            bucket_score = bucket_result["score"]
            used_factors = bucket_result["used_factors"]
            missing_factors = bucket_result["missing_factors"]
            tag = bucket_result["tag"]

        # 记录 breakdown
        breakdown[bucket_name] = {
            "score": bucket_score,
            "weight": config["weight"],
            "weighted_score": round(bucket_score * config["weight"], 2),
            "used_factors": used_factors,
            "missing_factors": missing_factors,
        }

        # 添加 tag
        if tag:
            tags.append(tag)

        # 累加总分
        total_score += bucket_score * config["weight"]
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
        "factor_composite_shadow_score_v2": round(final_score, 2),
        "factor_composite_breakdown_v2": breakdown,
        "factor_composite_tags_v2": tags,
    }
