"""
最终共识确认智能体

综合多个维度的分析结果，输出最终共识确认结论。
支持 L1-L4 分层架构。
"""

from typing import Any, Dict, List

from .opinion import AgentOpinion, LAYER_DECISION


# 共识标签定义
CONSENSUS_LABELS = {
    "strong_consensus": "技术、短线、轮动、市场环境多方一致",
    "trend_confirmed": "趋势确认，但短线热度不一定强",
    "trend_confirmed_but_strength_limited": "排名靠前但绝对分数不高",
    "short_term_active_unconfirmed": "短线活跃，但趋势未确认",
    "rotation_candidate": "轮动候选，正在升温但未充分确认",
    "defensive_watch": "偏防御观察，强度有限但风险相对可控",
    "conflicted": "多维信号冲突，需要继续观察",
    "weak_continuation": "多窗口弱、短线弱、风险不占优，偏弱延续",
    "oversold_rebound_candidate": "整体偏弱，但存在短线修复/反弹观察信号，需满足修复条件",
    "early_repair_watch": "趋势弱但短线中性/修复，风险可控，观察修复信号",
    "data_limited_neutral": "数据质量不够但没有明显风险，中性观察",
    "defensive_stable_watch": "风险可控、波动低，但进攻性不足",
    "low_signal_noise": "没有足够强信号，标签价值较低",
    "weak_or_avoid": "趋势弱、风险高或多维评分偏低",
    "insufficient_data": "数据不足，不能确认",
}

# 共识强度阈值
CONFIRM_LEVEL_THRESHOLDS = {
    "high": 0.75,
    "medium": 0.55,
    "low": 0.35,
    "very_low": 0.0,
}

# 维度权重
DIMENSION_WEIGHTS = {
    "technical": 0.25,
    "heat": 0.15,
    "rotation": 0.15,
    "risk": 0.15,
    "data_quality": 0.15,
    "market_context": 0.10,
    "narrative": 0.05,
}


class ConsensusDecisionAgent:
    """
    最终共识确认智能体

    综合多个维度的分析结果，输出最终共识确认结论。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        technical_view: Dict[str, Any],
        heat_view: Dict[str, Any],
        rotation_view: Dict[str, Any],
        risk_view: Dict[str, Any],
        data_quality_view: Dict[str, Any],
        market_context_view: Dict[str, Any],
        narrative_view: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        综合分析

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            technical_view: 技术面视图
            heat_view: 短线热度视图
            rotation_view: 轮动视图
            risk_view: 风险视图
            data_quality_view: 数据质量视图
            market_context_view: 市场环境视图
            narrative_view: 产业叙事视图

        Returns:
            综合分析结果
        """
        # 提取各维度分数
        dimension_scores = {
            "technical": technical_view.get("technical_score", 0.0),
            "heat": heat_view.get("heat_score", 0.0),
            "rotation": rotation_view.get("rotation_score", 0.0),
            "risk": risk_view.get("risk_score", 0.0),
            "data_quality": data_quality_view.get("data_quality_score", 0.0),
            "market_context": market_context_view.get("market_context_score", 0.0),
            "narrative": 0.5,  # 叙事维度固定 0.5
        }

        # 计算四个分数
        evidence_score = self._calculate_evidence_score(dimension_scores)
        opportunity_score = self._calculate_opportunity_score(dimension_scores)
        risk_control_score = dimension_scores.get("risk", 0.0)
        confidence_score = self._calculate_confidence_score(dimension_scores, technical_view, heat_view)

        # 确定共识标签
        consensus_label = self._determine_label(
            technical_view,
            heat_view,
            rotation_view,
            risk_view,
            data_quality_view,
            narrative_view,
            opportunity_score,
            risk_control_score,
            heat_view.get("heat_score", 0.0),
        )

        # 计算排序分数
        ranking_score = self._calculate_ranking_score(
            opportunity_score,
            evidence_score,
            risk_control_score,
            dimension_scores.get("market_context", 0.0),
            consensus_label,
            technical_view.get("technical_label", ""),
            "",  # multi_window_label 需要从外部传入
            risk_view.get("risk_label", ""),
        )

        # 确定确认等级
        confirm_level = self._determine_confirm_level(confidence_score)

        # 生成主要原因
        main_reasons = self._generate_main_reasons(
            consensus_label,
            technical_view,
            heat_view,
        )

        # 生成冲突点
        conflict_points = self._generate_conflict_points(
            technical_view,
            heat_view,
            rotation_view,
            risk_view,
        )

        # 生成观察要点
        watch_points = self._generate_watch_points(consensus_label, opportunity_score)

        # 生成数据警告
        data_warnings = data_quality_view.get("data_quality_warnings", [])

        return {
            "consensus_label": consensus_label,
            "confirm_level": confirm_level,
            "evidence_score": evidence_score,
            "opportunity_score": opportunity_score,
            "risk_control_score": risk_control_score,
            "confidence_score": confidence_score,
            "ranking_score": ranking_score,
            "dimension_scores": dimension_scores,
            "main_reasons": main_reasons,
            "conflict_points": conflict_points,
            "watch_points": watch_points,
            "data_warnings": data_warnings,
        }

    def _calculate_evidence_score(self, dimension_scores: Dict[str, float]) -> float:
        """计算证据充分度 (0-1)"""
        # 主要受数据质量和多窗口一致性影响
        data_quality = dimension_scores.get("data_quality", 0.0)
        market_context = dimension_scores.get("market_context", 0.0)

        # 基础分数来自数据质量
        base_score = data_quality * 0.7 + market_context * 0.3
        return round(max(0.0, min(1.0, base_score)), 2)

    def _calculate_opportunity_score(self, dimension_scores: Dict[str, float]) -> float:
        """计算正向机会度 (0-1)"""
        # 主要受技术面、热度、轮动影响
        technical = dimension_scores.get("technical", 0.0)
        heat = dimension_scores.get("heat", 0.0)
        rotation = dimension_scores.get("rotation", 0.0)
        market_context = dimension_scores.get("market_context", 0.0)
        narrative = dimension_scores.get("narrative", 0.0)

        # 加权平均
        weights = [0.30, 0.25, 0.20, 0.15, 0.10]
        scores = [technical, heat, rotation, market_context, narrative]

        total = sum(s * w for s, w in zip(scores, weights))
        return round(max(0.0, min(1.0, total)), 2)

    def _calculate_confidence_score(
        self,
        dimension_scores: Dict[str, float],
        technical_view: Dict[str, Any],
        heat_view: Dict[str, Any],
    ) -> float:
        """计算置信度分数 (0-1)"""
        # confidence_score 衡量 label 判断可信度，不是机会强度
        # 主要受数据质量和维度一致性影响

        data_quality = dimension_scores.get("data_quality", 0.0)
        technical_score = dimension_scores.get("technical", 0.0)
        heat_score = dimension_scores.get("heat", 0.0)

        # 基础分数
        base_score = data_quality * 0.5

        # 维度一致性加分
        technical_label = technical_view.get("technical_label", "")
        heat_label = heat_view.get("heat_label", "")

        # 如果技术面和热度不冲突，加分
        if technical_label not in ["trend_conflicted", "trend_unreliable"]:
            base_score += 0.2

        # 如果热度不弱，加分
        if heat_label not in ["heat_weak"]:
            base_score += 0.1

        # 如果技术面和热度分数差距不大，加分
        if abs(technical_score - heat_score) < 0.3:
            base_score += 0.1

        return round(max(0.0, min(1.0, base_score)), 2)

    def _calculate_ranking_score(
        self,
        opportunity_score: float,
        evidence_score: float,
        risk_control_score: float,
        market_context_score: float,
        consensus_label: str,
        technical_label: str = "",
        multi_window_label: str = "",
        risk_label: str = "",
    ) -> float:
        """
        计算排序分数 (0-1)

        新公式：
        base_ranking_score =
          opportunity_score * 0.45
        + evidence_score * 0.20
        + risk_control_score * 0.25
        + market_context_score * 0.10

        惩罚项：
        - conflicted: * 0.65
        - rotation_candidate (technical != trend_confirmed): * 0.75
        - weak_continuation/weak_or_avoid/low_signal_noise: * 0.50
        - insufficient_data: * 0.20
        - risk_high/risk_extreme: * 0.70
        - conflicted_windows: * 0.75

        加分项：
        - multi_window_confirmed: +0.05
        - trend_confirmed + risk_low/moderate: +0.05
        - opportunity >= 0.65 and evidence >= 0.70: +0.05
        """
        # 基础分数
        base_score = (
            opportunity_score * 0.45 +
            evidence_score * 0.20 +
            risk_control_score * 0.25 +
            market_context_score * 0.10
        )

        # 惩罚项
        if consensus_label == "conflicted":
            base_score *= 0.75
        elif consensus_label == "insufficient_data":
            base_score *= 0.20
        elif consensus_label in ["weak_or_avoid"]:
            base_score *= 0.60
        elif consensus_label in ["weak_continuation", "low_signal_noise"]:
            base_score *= 0.70

        if risk_label in ["risk_high", "risk_extreme"]:
            base_score *= 0.75

        if multi_window_label == "conflicted_windows":
            base_score *= 0.80

        # 加分项
        if multi_window_label == "multi_window_confirmed":
            base_score += 0.08
        if technical_label == "trend_confirmed" and risk_label in ["risk_low", "risk_moderate"]:
            base_score += 0.06
        if opportunity_score >= 0.50 and evidence_score >= 0.60:
            base_score += 0.05
        if consensus_label in ["strong_consensus", "trend_confirmed"]:
            base_score += 0.05

        return round(max(0.0, min(1.0, base_score)), 2)

    def _determine_label(
        self,
        technical_view: Dict[str, Any],
        heat_view: Dict[str, Any],
        rotation_view: Dict[str, Any],
        risk_view: Dict[str, Any],
        data_quality_view: Dict[str, Any],
        narrative_view: Dict[str, Any],
        opportunity_score: float,
        risk_control_score: float = 0.0,
        heat_score: float = 0.0,
    ) -> str:
        """确定共识标签"""
        technical_label = technical_view.get("technical_label", "")
        heat_label = heat_view.get("heat_label", "")
        rotation_label = rotation_view.get("rotation_label", "")
        risk_label = risk_view.get("risk_label", "")
        data_quality_label = data_quality_view.get("data_quality_label", "")
        narrative_label = narrative_view.get("narrative_label", "")

        # 1. 数据不可用 -> insufficient_data
        if data_quality_label == "data_unreliable":
            return "insufficient_data"

        # 2. 技术面冲突且无强热度/轮动 -> conflicted
        if (technical_label == "trend_conflicted" and
            heat_label not in ["heat_active"] and
            rotation_label not in ["rotation_rising", "rotation_new_entry"]):
            return "conflicted"

        # 3. 技术确认 + 热度适中 + 风险低 + 机会度高 -> strong_consensus
        if (technical_label == "trend_confirmed" and
            heat_label in ["heat_active", "heat_moderate"] and
            risk_label in ["risk_low", "risk_moderate"] and
            opportunity_score >= 0.65):
            return "strong_consensus"

        # 4. 技术确认 + 热度弱 -> trend_confirmed
        if technical_label == "trend_confirmed":
            return "trend_confirmed"

        # 5. 技术趋势形成 -> trend_confirmed_but_strength_limited
        if technical_label == "trend_forming":
            return "trend_confirmed_but_strength_limited"

        # 6. 短线活跃但趋势弱 -> short_term_active_unconfirmed
        if heat_label == "heat_active" and technical_label in ["trend_weak", "trend_unreliable"]:
            return "short_term_active_unconfirmed"

        # 7. 轮动候选 (收紧条件)
        # 需要明确的轮动信号 + 技术面不冲突 + 机会度高 + 风险可控
        if (rotation_label in ["rotation_rising", "rotation_new_entry"] and
            technical_label not in ["trend_weak", "trend_unreliable", "trend_conflicted"] and
            opportunity_score >= 0.50 and
            risk_control_score >= 0.55):
            return "rotation_candidate"

        # 8. 防御观察
        if (narrative_label in ["healthcare_defensive_recovery", "financial_stability"] and
            risk_label in ["risk_low", "risk_moderate"] and
            technical_view.get("technical_score", 0.0) >= 0.35):
            return "defensive_watch"

        # 9. 弱势修复观察 (oversold_rebound_candidate) — 收紧条件
        # 需要：短线活跃+风险可控+机会分不低+数据可用+非高风险
        if (heat_label in ["heat_active", "heat_moderate"] and
            risk_control_score >= 0.55 and
            opportunity_score >= 0.30 and
            risk_label not in ["risk_high", "risk_extreme"] and
            data_quality_label not in ["data_unreliable"] and
            technical_label not in ["trend_confirmed"] and
            heat_label != "heat_fading"):
            return "oversold_rebound_candidate"

        # 10. 早期修复观察 (early_repair_watch)
        # 趋势弱但短线中性/修复，风险可控
        if (technical_label in ["trend_weak", "trend_unreliable"] and
            heat_label in ["heat_moderate", "heat_active"] and
            risk_control_score >= 0.55 and
            risk_label not in ["risk_high", "risk_extreme"]):
            return "early_repair_watch"

        # 11. 偏弱延续 (weak_continuation)
        # 多窗口弱、短线弱、风险不占优
        if (technical_label in ["trend_weak", "trend_unreliable"] and
            heat_label in ["heat_weak", "heat_fading"] and
            opportunity_score < 0.30 and
            risk_control_score < 0.65):
            return "weak_continuation"

        # 12. 数据有限中性 (data_limited_neutral)
        # 数据质量不够但没有明显风险
        if (data_quality_label in ["data_limited"] and
            risk_label in ["risk_low", "risk_moderate"] and
            opportunity_score < 0.35):
            return "data_limited_neutral"

        # 13. 防御稳定观察 (defensive_stable_watch)
        # 风险可控、波动低，但进攻性不足
        if (risk_label in ["risk_low"] and
            heat_label in ["heat_weak", "heat_fading"] and
            technical_label in ["trend_neutral", "trend_weak"] and
            opportunity_score < 0.35):
            return "defensive_stable_watch"

        # 14. 低信号噪音 (low_signal_noise) — 收窄兜底范围
        # 仅在信号确实不足时使用
        if (opportunity_score < 0.25 and
            technical_label in ["trend_weak", "trend_unreliable", "trend_neutral"] and
            heat_label in ["heat_weak", "heat_fading"] and
            risk_label not in ["risk_high", "risk_extreme"]):
            return "low_signal_noise"

        # 15. 默认 weak_or_avoid
        return "weak_or_avoid"

    def _determine_confirm_level(self, confidence_score: float) -> str:
        """确定确认等级"""
        for level, threshold in CONFIRM_LEVEL_THRESHOLDS.items():
            if confidence_score >= threshold:
                return level
        return "very_low"

    def _generate_main_reasons(
        self,
        consensus_label: str,
        technical_view: Dict[str, Any],
        heat_view: Dict[str, Any],
    ) -> List[str]:
        """生成主要原因"""
        reasons = []

        if consensus_label == "strong_consensus":
            reasons.append("多维度信号一致，技术面和热度均较强")
        elif consensus_label == "trend_confirmed":
            reasons.append("技术面趋势确认")
        elif consensus_label == "trend_confirmed_but_strength_limited":
            reasons.append("趋势正在形成但强度有限")
        elif consensus_label == "short_term_active_unconfirmed":
            reasons.append("短线活跃但趋势未确认")
        elif consensus_label == "rotation_candidate":
            reasons.append("轮动候选，正在升温")
        elif consensus_label == "defensive_watch":
            reasons.append("防御属性，风险可控")
        elif consensus_label == "conflicted":
            reasons.append("多维信号存在分歧")
        elif consensus_label == "weak_continuation":
            reasons.append("多窗口弱、短线弱，偏弱延续")
        elif consensus_label == "oversold_rebound_candidate":
            reasons.append("短线活跃且风险可控，存在修复观察信号")
        elif consensus_label == "early_repair_watch":
            reasons.append("趋势弱但短线中性/修复，风险可控")
        elif consensus_label == "data_limited_neutral":
            reasons.append("数据有限但无明显风险，中性观察")
        elif consensus_label == "defensive_stable_watch":
            reasons.append("风险可控但进攻性不足，防御性观察")
        elif consensus_label == "low_signal_noise":
            reasons.append("多维信号不明确，标签价值较低")
        elif consensus_label == "weak_or_avoid":
            reasons.append("多维度偏弱")

        return reasons

    def _generate_conflict_points(
        self,
        technical_view: Dict[str, Any],
        heat_view: Dict[str, Any],
        rotation_view: Dict[str, Any],
        risk_view: Dict[str, Any],
    ) -> List[str]:
        """生成冲突点"""
        conflicts = []

        conflicts.extend(technical_view.get("technical_conflicts", []))
        conflicts.extend(heat_view.get("heat_conflicts", []))

        return conflicts

    def _generate_watch_points(self, consensus_label: str, opportunity_score: float = 0.0) -> List[str]:
        """生成观察要点"""
        points = []

        if consensus_label == "strong_consensus":
            points.append("当前多维度确认，可作为重点观察对象")
        elif consensus_label == "trend_confirmed":
            points.append("当前趋势确认，可适度关注")
        elif consensus_label == "trend_confirmed_but_strength_limited":
            points.append("当前趋势形成中，观察是否确认")
        elif consensus_label == "short_term_active_unconfirmed":
            points.append("当前短线活跃，观察趋势是否跟进")
        elif consensus_label == "rotation_candidate":
            points.append("当前轮动候选，观察是否持续升温")
        elif consensus_label == "defensive_watch":
            points.append("当前防御属性，可适度关注")
        elif consensus_label == "conflicted":
            points.append("当前信号冲突，等待更多确认")
        elif consensus_label == "weak_continuation":
            points.append("当前偏弱延续，等待反转信号")
        elif consensus_label == "oversold_rebound_candidate":
            points.append("当前短线活跃且风险可控，观察修复持续性")
        elif consensus_label == "early_repair_watch":
            points.append("当前趋势弱但短线有修复迹象，观察是否确认")
        elif consensus_label == "data_limited_neutral":
            points.append("当前数据有限，中性观察")
        elif consensus_label == "defensive_stable_watch":
            points.append("当前风险可控但进攻性不足，防御性观察")
        elif consensus_label == "low_signal_noise":
            points.append("当前信号不明确，标签价值较低")
        elif consensus_label == "weak_or_avoid":
            if opportunity_score < 0.3:
                points.append("当前正向观察强度有限，信号偏弱")
            else:
                points.append("当前多维度偏弱，但仍有部分正向信号")

        return points
