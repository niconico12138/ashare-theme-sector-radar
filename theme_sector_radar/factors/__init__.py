"""
统一因子 Schema 模块。

提供因子元数据注册、归一化、快照构建和读取工具。
"""

from theme_sector_radar.factors.schema import FactorValue, FactorSnapshot
from theme_sector_radar.factors.registry import FACTOR_REGISTRY, get_factor_metadata
from theme_sector_radar.factors.normalizer import normalize_factor
from theme_sector_radar.factors.snapshot import build_factor_snapshot
from theme_sector_radar.factors.calculators import calculate_bar_factors
from theme_sector_radar.factors.access import get_factor_value, coerce_float

__all__ = [
    "FactorValue",
    "FactorSnapshot",
    "FACTOR_REGISTRY",
    "get_factor_metadata",
    "normalize_factor",
    "build_factor_snapshot",
    "calculate_bar_factors",
    "get_factor_value",
    "coerce_float",
]
