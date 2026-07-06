"""
持续性强度智能体

分析板块多日持续性信号，判断信号是否具备持续性。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_SPECIALIZED


# 持续性标签解释
PERSISTENCE_LABEL_CN = {
    "persistence_confirmed": "持续性确认",
    "persistence_building": "持续性增强",
    "persistence_weak": "持续性偏弱",
    "persistence_deteriorating": "持续性转弱",
    "persistence_unknown": "持续性数据不足",
}


class PersistenceStrengthAgent:
    """
    持续性强度智能体

    基于多日研究索引和当前板块结果，判断当前板块信号是否具备持续性。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        current_result: Dict[str, Any],
        sector_timeline: List[Dict[str, Any]],
        daily_summary: Optional[Dict[str, Any]] = None,
        research_index: Optional[Dict[str, Any]] = None,
    ) -> AgentOpinion:
        """
        分析持续性强度

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            current_result: 当前板块研究结果
            sector_timeline: 该板块的历史 timeline
            daily_summary: 当日摘要
            research_index: 多日研究索引

        Returns:
            AgentOpinion
        """
        warnings = []
        evidence = []

        # 检查数据完整性
        if not sector_timeline or len(sector_timeline) < 2:
            return AgentOpinion(
                agent_id="persistence_strength",
                layer=LAYER_SPECIALIZED,
                label="persistence_unknown",
                score=0.0,
                confidence=0.3,
                evidence=["数据不足，无法判断持续性"],
                warnings=["缺少多日 timeline 数据"],
                vote="neutral",
                veto=False,
                veto_reason="",
            )

        # 提取持续性特征
        features = self._extract_features(sector_timeline, current_result)

        # 确定持续性标签
        persistence_label = self._determine_label(features)

        # 计算分数
        score = self._calculate_score(features)

        # 计算置信度
        confidence = self._calculate_confidence(features, len(sector_timeline))

        # 生成证据
        evidence = self._generate_evidence(features, persistence_label)

        # 确定投票
        vote = self._determine_vote(persistence_label, score)

        # 生成警告
        warnings = self._generate_warnings(features, len(sector_timeline))

        return AgentOpinion(
            agent_id="persistence_strength",
            layer=LAYER_SPECIALIZED,
            label=persistence_label,
            score=score,
            confidence=confidence,
            evidence=evidence,
            warnings=warnings,
            vote=vote,
            veto=False,
            veto_reason="",
        )

    def _extract_features(
        self,
        timeline: List[Dict[str, Any]],
        current_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从 timeline 提取持续性特征"""
        features = {
            "top_watch_streak": 0,
            "label_persistence_days": 0,
            "previous_label": "",
            "current_label": current_result.get("consensus_label", ""),
            "label_transition": "",
            "ranking_score_trend_3d": "unknown",
            "opportunity_score_trend_3d": "unknown",
            "confidence_score_trend_3d": "unknown",
            "conflict_persistence_days": 0,
            "risk_persistence_days": 0,
            "regime_persistence_days": 0,
        }

        if len(timeline) < 1:
            return features

        # top_watch_streak
        streak = 0
        for entry in reversed(timeline):
            if entry.get("is_top_watch", False):
                streak += 1
            else:
                break
        features["top_watch_streak"] = streak

        # label_persistence
        current_label = features["current_label"]
        label_days = 0
        for entry in reversed(timeline):
            if entry.get("consensus_label", "") == current_label:
                label_days += 1
            else:
                break
        features["label_persistence_days"] = label_days

        # previous_label 和 label_transition
        if len(timeline) >= 2:
            prev = timeline[-2]
            features["previous_label"] = prev.get("consensus_label", "")
            if features["previous_label"] != current_label:
                features["label_transition"] = f"{features['previous_label']} -> {current_label}"

        # ranking_score_trend_3d
        if len(timeline) >= 3:
            scores = [e.get("ranking_score", 0) for e in timeline[-3:]]
            features["ranking_score_trend_3d"] = self._compute_trend(scores)

        # opportunity_score_trend_3d
        if len(timeline) >= 3:
            scores = [e.get("opportunity_score", 0) for e in timeline[-3:]]
            features["opportunity_score_trend_3d"] = self._compute_trend(scores)

        # confidence_score_trend_3d
        if len(timeline) >= 3:
            scores = [e.get("confidence_score", 0) for e in timeline[-3:]]
            features["confidence_score_trend_3d"] = self._compute_trend(scores)

        # conflict_persistence_days
        conflict_days = 0
        for entry in reversed(timeline):
            if entry.get("conflict_level", "none") != "none":
                conflict_days += 1
            else:
                break
        features["conflict_persistence_days"] = conflict_days

        # risk_persistence_days
        risk_days = 0
        for entry in reversed(timeline):
            if entry.get("veto_triggered", False) or entry.get("risk_control_score", 1.0) < 0.5:
                risk_days += 1
            else:
                break
        features["risk_persistence_days"] = risk_days

        # regime_persistence_days
        current_regime = current_result.get("market_regime", {}).get("regime_composite_label", "")
        regime_days = 0
        for entry in reversed(timeline):
            if entry.get("market_regime", {}).get("regime_composite_label", "") == current_regime:
                regime_days += 1
            else:
                break
        features["regime_persistence_days"] = regime_days

        return features

    def _compute_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "unknown"

        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        avg_diff = sum(diffs) / len(diffs)

        if avg_diff > 0.05:
            return "rising"
        elif avg_diff < -0.05:
            return "falling"
        else:
            if max(diffs) - min(diffs) > 0.1:
                return "volatile"
            return "flat"

    def _determine_label(self, features: Dict[str, Any]) -> str:
        """确定持续性标签"""
        streak = features.get("top_watch_streak", 0)
        ranking_trend = features.get("ranking_score_trend_3d", "unknown")
        opportunity_trend = features.get("opportunity_score_trend_3d", "unknown")
        risk_days = features.get("risk_persistence_days", 0)
        conflict_days = features.get("conflict_persistence_days", 0)

        # 1. 数据不足
        if streak == 0 and ranking_trend == "unknown":
            return "persistence_unknown"

        # 2. 持续性确认：streak >= 3 且任一趋势上升
        if streak >= 3 and (ranking_trend == "rising" or opportunity_trend == "rising"):
            if risk_days == 0 and conflict_days <= 1:
                return "persistence_confirmed"

        # 3. 持续性增强：多种条件
        # 3a. streak >= 5 且无风险/冲突延续（即使 trend flat）
        if streak >= 5 and risk_days == 0 and conflict_days == 0:
            return "persistence_building"

        # 3b. streak >= 3 且任一趋势 rising（放宽条件）
        if streak >= 3 and (ranking_trend in ["rising", "flat"] or opportunity_trend in ["rising", "flat"]):
            if risk_days == 0:
                return "persistence_building"

        # 3c. streak == 2 且趋势 rising
        if streak == 2 and (ranking_trend == "rising" or opportunity_trend == "rising"):
            return "persistence_building"

        # 3d. 有利 label transition
        transition = features.get("label_transition", "")
        favorable_transitions = [
            "weak_or_avoid -> short_term_active_unconfirmed",
            "oversold_rebound_candidate -> short_term_active_unconfirmed",
            "low_signal_noise -> short_term_active_unconfirmed",
            "weak_or_avoid -> oversold_rebound_candidate",
        ]
        if transition in favorable_transitions:
            return "persistence_building"

        # 4. 持续性转弱
        if ranking_trend == "falling" and opportunity_trend == "falling":
            if risk_days > 0 or conflict_days > 0:
                return "persistence_deteriorating"

        # 5. 持续性偏弱
        if streak <= 1 and ranking_trend in ["flat", "falling", "unknown"]:
            return "persistence_weak"

        # 默认
        return "persistence_weak"

    def _calculate_score(self, features: Dict[str, Any]) -> float:
        """计算持续性分数 (0-1)"""
        score = 0.0

        # top_watch_streak component (0~0.35)
        streak = features.get("top_watch_streak", 0)
        if streak >= 5:
            score += 0.35
        elif streak >= 3:
            score += 0.25
        elif streak >= 2:
            score += 0.15
        elif streak >= 1:
            score += 0.05

        # score_trend component (0~0.25)
        ranking_trend = features.get("ranking_score_trend_3d", "unknown")
        opportunity_trend = features.get("opportunity_score_trend_3d", "unknown")
        if ranking_trend == "rising":
            score += 0.15
        elif ranking_trend == "flat":
            score += 0.05
        if opportunity_trend == "rising":
            score += 0.10
        elif opportunity_trend == "flat":
            score += 0.03

        # label_transition component (0~0.15)
        transition = features.get("label_transition", "")
        favorable_transitions = [
            "weak_or_avoid -> short_term_active_unconfirmed",
            "oversold_rebound_candidate -> short_term_active_unconfirmed",
            "low_signal_noise -> short_term_active_unconfirmed",
            "weak_or_avoid -> oversold_rebound_candidate",
        ]
        if transition in favorable_transitions:
            score += 0.15
        elif transition and " -> " in transition:
            score += 0.05

        # risk/conflict penalty (0~0.15)
        risk_days = features.get("risk_persistence_days", 0)
        conflict_days = features.get("conflict_persistence_days", 0)
        if risk_days > 0:
            score -= 0.10
        if conflict_days > 0:
            score -= 0.05

        # data completeness (0~0.10)
        timeline_days = features.get("label_persistence_days", 0)
        if timeline_days >= 5:
            score += 0.10
        elif timeline_days >= 3:
            score += 0.05

        return round(max(0.0, min(1.0, score)), 2)

    def _calculate_confidence(self, features: Dict[str, Any], timeline_count: int) -> float:
        """计算置信度"""
        confidence = 0.5

        # timeline 天数越多越高
        if timeline_count >= 10:
            confidence += 0.2
        elif timeline_count >= 5:
            confidence += 0.1

        # streak >= 3 且趋势一致时提高
        streak = features.get("top_watch_streak", 0)
        ranking_trend = features.get("ranking_score_trend_3d", "unknown")
        if streak >= 3 and ranking_trend == "rising":
            confidence += 0.15

        # 数据不足时降低
        if timeline_count < 3:
            confidence -= 0.2

        return round(max(0.0, min(1.0, confidence)), 2)

    def _generate_evidence(self, features: Dict[str, Any], label: str) -> List[str]:
        """生成证据"""
        evidence = []

        streak = features.get("top_watch_streak", 0)
        if streak > 0:
            evidence.append(f"连续出现在重点观察 {streak} 天")

        ranking_trend = features.get("ranking_score_trend_3d", "unknown")
        if ranking_trend != "unknown":
            evidence.append(f"排序分趋势: {ranking_trend}")

        opportunity_trend = features.get("opportunity_score_trend_3d", "unknown")
        if opportunity_trend != "unknown":
            evidence.append(f"正向观察强度趋势: {opportunity_trend}")

        transition = features.get("label_transition", "")
        if transition:
            evidence.append(f"标签转换: {transition}")

        return evidence

    def _generate_warnings(self, features: Dict[str, Any], timeline_count: int) -> List[str]:
        """生成警告"""
        warnings = []

        if timeline_count < 5:
            warnings.append("timeline 数据较少，持续性判断可能不准确")

        if features.get("conflict_persistence_days", 0) > 0:
            warnings.append("存在持续性分歧")

        if features.get("risk_persistence_days", 0) > 0:
            warnings.append("存在持续性风险")

        return warnings

    def _determine_vote(self, label: str, score: float) -> str:
        """确定投票方向"""
        if label == "persistence_confirmed":
            return "positive"
        elif label == "persistence_building" and score >= 0.55:
            return "positive"
        elif label == "persistence_deteriorating":
            return "negative"
        else:
            return "neutral"
