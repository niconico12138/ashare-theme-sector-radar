"""
Market Regime 解释层

为 sector research 报告提供市场状态解释信息。
不参与 vote、veto、scoring 决策。
"""

from typing import Any, Dict, List, Optional


# regime 解释模板
REGIME_SUMMARY = {
    "risk_on": "市场处于风险偏好环境，多数板块上涨，趋势确认度较高。",
    "risk_off": "市场处于风险规避环境，多数板块下跌，趋势确认度较低。",
    "weak_rebound": "市场处于弱势反弹环境，部分板块修复但整体偏弱。",
    "choppy_market": "市场处于震荡分化环境，板块信号可能不连续。",
    "unknown_regime": "市场状态不确定，数据不足。",
}

# regime x label 交互解释
REGIME_LABEL_INTERACTION = {
    "choppy_market": {
        "low_signal_noise": "震荡环境下低信号标签可能包含轮动噪声，需结合短线热度和风险维度观察。",
        "oversold_rebound_candidate": "震荡环境下反弹候选需关注是否有真实动量修复。",
        "conflicted": "震荡环境下冲突标签一致性较好，可作为避险参考。",
        "weak_or_avoid": "震荡环境下弱标签表现可能分化，需结合市场广度判断。",
        "short_term_active_unconfirmed": "震荡环境下短线活跃信号可能有轮动机会，但需关注持续性。",
        "default": "当前标签在震荡环境下仅作分层解释，不改变原始标签。",
    },
    "risk_off": {
        "low_signal_noise": "风险规避环境下低信号标签需谨慎，市场整体偏弱。",
        "oversold_rebound_candidate": "风险规避环境下反弹候选成功率较低。",
        "conflicted": "风险规避环境下冲突标签可能反映真实分歧。",
        "weak_or_avoid": "风险规避环境下弱标签表现通常偏弱。",
        "default": "当前标签在风险规避环境下仅作分层解释，不改变原始标签。",
    },
    "risk_on": {
        "low_signal_noise": "风险偏好环境下低信号标签可能被市场带动上涨。",
        "oversold_rebound_candidate": "风险偏好环境下反弹候选成功率较高。",
        "conflicted": "风险偏好环境下冲突标签可能被忽视，需关注风险。",
        "weak_or_avoid": "风险偏好环境下弱标签也可能有正向表现。",
        "default": "当前标签在风险偏好环境下仅作分层解释，不改变原始标签。",
    },
    "weak_rebound": {
        "low_signal_noise": "弱势反弹环境下低信号标签需关注是否有真实修复。",
        "oversold_rebound_candidate": "弱势反弹环境下反弹候选需关注修复持续性。",
        "default": "当前标签在弱势反弹环境下仅作分层解释，不改变原始标签。",
    },
}

# regime 观察要点
REGIME_WATCH_POINTS = {
    "choppy_market": [
        "市场广度分化，板块信号可能不连续",
        "低信号标签在震荡环境下需要结合后续持续性验证",
    ],
    "risk_off": [
        "市场整体偏弱，标签表现可能普遍偏弱",
        "关注是否有超跌修复信号",
    ],
    "risk_on": [
        "市场整体偏强，标签表现可能普遍偏好",
        "关注是否有过热风险",
    ],
    "weak_rebound": [
        "市场弱势反弹，板块修复可能不持续",
        "关注反弹是否进入确认阶段",
    ],
}

# regime 警告
REGIME_WARNINGS = {
    "choppy_market": ["市场状态样本量仍有限，解释仅用于复盘观察"],
    "risk_off": ["风险规避环境下需关注系统性风险"],
    "risk_on": ["风险偏好环境下需关注过热风险"],
    "weak_rebound": ["弱势反弹可能不持续，需关注后续确认"],
}


class MarketRegimeContext:
    """
    Market Regime 解释层

    为 sector research 报告提供市场状态解释信息。
    不参与 vote、veto、scoring 决策。
    """

    def __init__(self):
        """初始化"""
        pass

    def generate_regime_context(
        self,
        signal_date: str,
        theme_sector_radar_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成市场状态上下文

        Args:
            signal_date: 信号日期
            theme_sector_radar_data: 当日 theme_sector_radar.json 数据

        Returns:
            市场状态上下文
        """
        if not theme_sector_radar_data:
            return self._empty_context()

        # 提取 breadth 数据
        breadth = theme_sector_radar_data.get("market_breadth", {})
        mt = theme_sector_radar_data.get("market_temperature", {})

        # 计算 regime 维度
        benchmark_trend = self._infer_benchmark_trend(breadth)
        market_temp_regime = self._infer_temperature_regime(mt, breadth)
        breadth_regime = breadth.get("breadth_label", "breadth_unknown")
        volatility_regime = "normal_volatility"  # 默认

        # 计算 composite regime
        composite = self._compute_composite(
            benchmark_trend, market_temp_regime, breadth_regime, volatility_regime
        )

        return {
            "regime_composite_label": composite,
            "benchmark_trend": benchmark_trend,
            "market_temperature_regime": market_temp_regime,
            "breadth_regime": breadth_regime,
            "volatility_regime": volatility_regime,
            "source": "theme_sector_radar.market_breadth",
            "decision_impact": "report_only",
        }

    def generate_regime_interpretation(
        self,
        regime_context: Dict[str, Any],
        consensus_label: str,
    ) -> Dict[str, Any]:
        """
        生成 regime 解释

        Args:
            regime_context: 市场状态上下文
            consensus_label: 当前板块的共识标签

        Returns:
            regime 解释
        """
        composite = regime_context.get("regime_composite_label", "unknown_regime")

        # summary
        summary = REGIME_SUMMARY.get(composite, REGIME_SUMMARY["unknown_regime"])

        # label_context
        interactions = REGIME_LABEL_INTERACTION.get(composite, {})
        label_context = interactions.get(consensus_label, interactions.get("default", ""))

        # watch_points
        watch_points = REGIME_WATCH_POINTS.get(composite, [])

        # warnings
        warnings = REGIME_WARNINGS.get(composite, [])

        return {
            "summary": summary,
            "label_context": label_context,
            "watch_points": watch_points,
            "warnings": warnings,
        }

    def _infer_benchmark_trend(self, breadth: Dict[str, Any]) -> str:
        """从 breadth 推断 benchmark 趋势"""
        avg_change = breadth.get("average_industry_change_pct", 0)
        up_ratio = breadth.get("industry_up_ratio", 0)

        if up_ratio >= 0.6 and avg_change > 0.5:
            return "benchmark_uptrend"
        elif up_ratio <= 0.3 and avg_change < -0.5:
            return "benchmark_downtrend"
        else:
            return "benchmark_sideways"

    def _infer_temperature_regime(
        self, mt: Dict[str, Any], breadth: Dict[str, Any]
    ) -> str:
        """推断市场温度 regime"""
        score = mt.get("score", 50)
        label = mt.get("label", "neutral")

        if score >= 70 or label == "hot":
            return "market_hot"
        elif score >= 55 or label == "warm":
            return "market_warm"
        elif score >= 40 or label == "neutral":
            return "market_cool"
        else:
            return "market_cold"

    def _compute_composite(
        self,
        benchmark_trend: str,
        market_temp: str,
        breadth: str,
        volatility: str,
    ) -> str:
        """计算综合 regime 标签"""
        if (benchmark_trend == "benchmark_uptrend" and
            market_temp in ["market_hot", "market_warm"] and
            breadth in ["broad_rising"]):
            return "risk_on"

        if (benchmark_trend == "benchmark_downtrend" and
            market_temp in ["market_cold"] and
            breadth in ["broad_falling"]):
            return "risk_off"

        if (benchmark_trend == "benchmark_sideways" and
            market_temp in ["market_cool", "market_cold"] and
            breadth in ["mixed_breadth", "narrow_rising"]):
            return "weak_rebound"

        return "choppy_market"

    def _empty_context(self) -> Dict[str, Any]:
        """返回空的 regime 上下文"""
        return {
            "regime_composite_label": "unknown_regime",
            "benchmark_trend": "benchmark_unknown",
            "market_temperature_regime": "market_unknown",
            "breadth_regime": "breadth_unknown",
            "volatility_regime": "volatility_unknown",
            "source": "unavailable",
            "decision_impact": "report_only",
        }
