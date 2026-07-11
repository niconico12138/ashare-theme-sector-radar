"""
通用因子归一化模块

提供 normalize_factor 函数，将原始值归一化到 0-100 分数区间。
支持 already_scored / higher_is_better / lower_is_better / neutral 四种方向。
"""

from __future__ import annotations

from typing import Any

from theme_sector_radar.factors.registry import FactorMetadata


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_factor(
    raw_value: float | None,
    metadata: FactorMetadata,
    value_min: float = 0.0,
    value_max: float = 100.0,
) -> tuple[float, str]:
    """将原始值归一化到 0-100 分数区间。

    Args:
        raw_value: 原始值
        metadata: 因子元数据
        value_min: 原始值最小值（用于线性缩放）
        value_max: 原始值最大值（用于线性缩放）

    Returns:
        (score, quality) 归一化分数和质量标记
    """
    # 缺失值处理
    if raw_value is None:
        return 50.0, "missing"

    value = _safe_float(raw_value)

    # already_scored: 直接裁剪到 0-100
    if metadata.direction == "already_scored":
        score = max(0.0, min(100.0, value))
        return score, "good"

    # higher_is_better: 线性缩放到 0-100
    if metadata.direction == "higher_is_better":
        if value_max <= value_min:
            # 无法缩放，返回中性值
            return 50.0, "approximate"
        # 线性缩放
        score = (value - value_min) / (value_max - value_min) * 100.0
        score = max(0.0, min(100.0, score))
        return score, "good"

    # lower_is_better: 反向缩放到 0-100
    if metadata.direction == "lower_is_better":
        if value_max <= value_min:
            return 50.0, "approximate"
        # 反向线性缩放
        score = (value_max - value) / (value_max - value_min) * 100.0
        score = max(0.0, min(100.0, score))
        return score, "good"

    # neutral: 默认 50
    return 50.0, "good"
