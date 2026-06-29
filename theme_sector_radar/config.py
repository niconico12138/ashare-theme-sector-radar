"""
配置管理

定义 Theme Sector Radar 的配置参数。
"""

from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    # Top N 配置
    "top_n": 10,

    # 最小数量门槛
    "industry_min_count": 20,
    "concept_min_count": 20,

    # 缓存 fallback 配置
    "fallback_cache_days": 7,

    # 重试配置
    "retries": 3,
    "retry_delay": 1.0,

    # 评分权重
    "industry_weights": {
        "trend_strength": 0.25,
        "capital_flow": 0.25,
        "sector_breadth": 0.20,
        "continuity": 0.15,
        "market_fit": 0.10,
        "data_quality": 0.05,
    },
    "concept_weights": {
        "heat_burst": 0.25,
        "capital_confirm": 0.20,
        "constituent_synergy": 0.20,
        "phase_judgment": 0.20,
        "catalyst": 0.10,
        "data_quality": 0.05,
    },

    # 风险阈值
    "risk_thresholds": {
        "overheat_short_term_gain": 15.0,
        "overheat_deviation": 10.0,
        "overheat_volume_ratio": 3.0,
        "divergence_advance_ratio": 0.4,
        "divergence_price_flow_gap": 0.3,
        "data_quality_min_sources": 2,
        "data_quality_freshness_hours": 24,
    },

    # 风险扣分
    "risk_penalty": {
        "overheat_min": -5,
        "overheat_max": -20,
        "divergence_min": -5,
        "divergence_max": -15,
        "data_quality_min": -5,
        "data_quality_max": -10,
    },

    # 关注等级阈值
    "focus_level_thresholds": {
        "focus_min_score": 80,
        "watch_min_score": 65,
        "caution_min_score": 45,
    },

    # 共振权重
    "resonance_weights": {
        "constituent_overlap": 0.30,
        "dual_top_n": 0.25,
        "flow_alignment": 0.25,
        "common_core_count": 0.20,
    },

    # 核心成分股数量阈值
    "core_constituent_threshold": 5,
}


def get_config() -> Dict[str, Any]:
    """获取默认配置"""
    return DEFAULT_CONFIG.copy()


def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return DEFAULT_CONFIG.get(key, default)
