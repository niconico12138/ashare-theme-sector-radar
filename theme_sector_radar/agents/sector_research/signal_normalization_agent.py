"""
L1 信号标准化 Agent

统一不同 Agent 的标签和分数口径，便于后续投票。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_DATA_EVIDENCE


class SignalNormalizationAgent:
    """
    L1 信号标准化 Agent

    统一不同 Agent 的标签和分数口径，便于后续投票。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def normalize(
        self,
        opinions: List[AgentOpinion],
    ) -> List[AgentOpinion]:
        """
        标准化 Agent 意见

        Args:
            opinions: Agent 意见列表

        Returns:
            标准化后的 Agent 意见列表
        """
        normalized = []

        for opinion in opinions:
            # 标准化标签
            normalized_label = self._normalize_label(opinion.label)

            # 标准化分数
            normalized_score = self._normalize_score(opinion.score, opinion.layer)

            # 创建标准化后的意见
            normalized_opinion = AgentOpinion(
                agent_id=opinion.agent_id,
                layer=opinion.layer,
                label=normalized_label,
                score=normalized_score,
                confidence=opinion.confidence,
                evidence=opinion.evidence,
                warnings=opinion.warnings,
                vote=opinion.vote,
                veto=opinion.veto,
                veto_reason=opinion.veto_reason,
                metadata=opinion.metadata,
            )

            normalized.append(normalized_opinion)

        return normalized

    def _normalize_label(self, label: str) -> str:
        """标准化标签"""
        # 标签映射
        label_mapping = {
            "trend_confirmed": "positive",
            "trend_forming": "moderate",
            "trend_weak": "negative",
            "trend_unreliable": "negative",
            "heat_active": "positive",
            "heat_moderate": "moderate",
            "heat_fading": "negative",
            "heat_weak": "negative",
            "rotation_rising": "positive",
            "rotation_improving": "moderate",
            "rotation_weakening": "negative",
            "rotation_lagging": "negative",
            "risk_low": "positive",
            "risk_moderate": "moderate",
            "risk_high": "negative",
            "risk_extreme": "negative",
            "data_reliable": "positive",
            "data_usable": "moderate",
            "data_limited": "negative",
            "data_unreliable": "negative",
        }

        return label_mapping.get(label, label)

    def _normalize_score(self, score: float, layer: str) -> float:
        """标准化分数"""
        # 不同层的分数范围可能不同，这里统一到 0-1
        return max(0.0, min(1.0, score))
