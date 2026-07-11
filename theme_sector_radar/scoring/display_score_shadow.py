"""
Display Score Shadow 模块 (shadow-only)

基于 factor_composite_shadow_score_v2，新增 display_score_shadow 字段。
用于影子排序和报告评估，不替代 final_score，不改变候选池正式排序。

计算方式：
- display_score_shadow_90_10 = final_score * 0.90 + v2 * 0.10
- display_score_shadow_80_20 = final_score * 0.80 + v2 * 0.20
- display_score_shadow_70_30 = final_score * 0.70 + v2 * 0.30

规则：
- 缺 final_score 时返回 None，并打 tag missing_final_score
- 缺 v2 时使用 50 中性值，并打 tag missing_v2_neutral
- 所有分数限制在 0-100
- 不改变 final_score
- 不改变候选顺序
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


def compute_display_score_shadow(candidate: dict) -> dict:
    """计算 Display Score Shadow。

    Args:
        candidate: 候选股字典，必须包含 final_score 和 factor_composite_shadow_score_v2

    Returns:
        dict with:
            display_score_shadow_90_10: final * 0.90 + v2 * 0.10
            display_score_shadow_80_20: final * 0.80 + v2 * 0.20
            display_score_shadow_70_30: final * 0.70 + v2 * 0.30
            display_score_shadow_breakdown: 分项明细
            display_score_shadow_tags: 标签列表
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}

    # 获取 final_score
    final_score = candidate.get("final_score")
    if final_score is None:
        tags.append("missing_final_score")
        return {
            "display_score_shadow_90_10": None,
            "display_score_shadow_80_20": None,
            "display_score_shadow_70_30": None,
            "display_score_shadow_breakdown": breakdown,
            "display_score_shadow_tags": tags,
        }

    final_score = _safe_float(final_score)

    # 获取 v2
    v2_score = candidate.get("factor_composite_shadow_score_v2")
    if v2_score is None:
        tags.append("missing_v2_neutral")
        v2_score = 50.0  # 使用中性值
    else:
        v2_score = _safe_float(v2_score)

    # 计算三种 blend
    score_90_10 = final_score * 0.90 + v2_score * 0.10
    score_80_20 = final_score * 0.80 + v2_score * 0.20
    score_70_30 = final_score * 0.70 + v2_score * 0.30

    # 限制在 0-100
    score_90_10 = max(0.0, min(100.0, score_90_10))
    score_80_20 = max(0.0, min(100.0, score_80_20))
    score_70_30 = max(0.0, min(100.0, score_70_30))

    # 记录 breakdown
    breakdown = {
        "final_score": round(final_score, 2),
        "v2_score": round(v2_score, 2),
        "weights_90_10": {"final": 0.90, "v2": 0.10},
        "weights_80_20": {"final": 0.80, "v2": 0.20},
        "weights_70_30": {"final": 0.70, "v2": 0.30},
    }

    return {
        "display_score_shadow_90_10": round(score_90_10, 2),
        "display_score_shadow_80_20": round(score_80_20, 2),
        "display_score_shadow_70_30": round(score_70_30, 2),
        "display_score_shadow_breakdown": breakdown,
        "display_score_shadow_tags": tags,
    }
