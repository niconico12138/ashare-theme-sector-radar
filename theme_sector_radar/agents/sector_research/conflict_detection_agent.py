"""
L3 冲突检测 Agent

检测 Agent 之间的冲突。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_CONFLICT_CONSISTENCY


class ConflictDetectionAgent:
    """
    L3 冲突检测 Agent

    检测 Agent 之间的冲突。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def detect(
        self,
        opinions: List[AgentOpinion],
    ) -> AgentOpinion:
        """
        检测冲突

        Args:
            opinions: Agent 意见列表

        Returns:
            冲突检测结果
        """
        conflicts = []

        # 检测趋势-热度冲突
        trend_opinions = [o for o in opinions if "trend" in o.agent_id]
        heat_opinions = [o for o in opinions if "heat" in o.agent_id]

        for trend_op in trend_opinions:
            for heat_op in heat_opinions:
                if self._detect_trend_heat_conflict(trend_op, heat_op):
                    conflicts.append({
                        "type": "trend_heat_conflict",
                        "description": "趋势弱但短线热",
                        "agents": [trend_op.agent_id, heat_op.agent_id],
                    })

        # 检测轮动-趋势冲突
        rotation_opinions = [o for o in opinions if "rotation" in o.agent_id]
        for rotation_op in rotation_opinions:
            for trend_op in trend_opinions:
                if self._detect_rotation_trend_conflict(rotation_op, trend_op):
                    conflicts.append({
                        "type": "rotation_trend_conflict",
                        "description": "轮动升温但趋势未确认",
                        "agents": [rotation_op.agent_id, trend_op.agent_id],
                    })

        # 检测风险-机会冲突
        risk_opinions = [o for o in opinions if "risk" in o.agent_id]
        for risk_op in risk_opinions:
            for trend_op in trend_opinions:
                if self._detect_risk_opportunity_conflict(risk_op, trend_op):
                    conflicts.append({
                        "type": "risk_opportunity_conflict",
                        "description": "机会强但风险高",
                        "agents": [risk_op.agent_id, trend_op.agent_id],
                    })

        # 检测数据-置信度冲突
        data_opinions = [o for o in opinions if "data" in o.agent_id or "evidence" in o.agent_id]
        for data_op in data_opinions:
            if self._detect_data_confidence_conflict(data_op, opinions):
                conflicts.append({
                    "type": "data_confidence_conflict",
                    "description": "数据质量不足但结论置信度高",
                    "agents": [data_op.agent_id],
                })

        # 确定冲突级别
        if len(conflicts) >= 3:
            conflict_level = "high"
        elif len(conflicts) >= 1:
            conflict_level = "medium"
        else:
            conflict_level = "none"

        # 生成证据
        evidence = [c["description"] for c in conflicts]

        # 生成摘要
        conflict_summary = f"发现 {len(conflicts)} 个冲突" if conflicts else "无冲突"

        return AgentOpinion(
            agent_id="conflict_detection",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label=conflict_level,
            score=1.0 - (len(conflicts) * 0.2),  # 冲突越多，分数越低
            confidence=0.8,
            evidence=evidence,
            vote="negative" if len(conflicts) >= 2 else "neutral",
            metadata={
                "conflict_level": conflict_level,
                "conflicts": conflicts,
                "conflict_summary": conflict_summary,
            },
        )

    def _detect_trend_heat_conflict(
        self,
        trend_op: AgentOpinion,
        heat_op: AgentOpinion,
    ) -> bool:
        """检测趋势-热度冲突"""
        trend_label = trend_op.label
        heat_label = heat_op.label

        # 趋势弱且短线弱但投票方向相反
        if trend_op.vote == "negative" and heat_op.vote == "positive":
            return True
        if trend_op.vote == "positive" and heat_op.vote == "negative":
            return True

        return False

    def _detect_rotation_trend_conflict(
        self,
        rotation_op: AgentOpinion,
        trend_op: AgentOpinion,
    ) -> bool:
        """检测轮动-趋势冲突"""
        # 轮动上升但趋势投票为负
        if rotation_op.vote == "positive" and trend_op.vote == "negative":
            return True
        if rotation_op.vote == "negative" and trend_op.vote == "positive":
            return True

        return False

    def _detect_risk_opportunity_conflict(
        self,
        risk_op: AgentOpinion,
        trend_op: AgentOpinion,
    ) -> bool:
        """检测风险-机会冲突"""
        # 风险投票为负但趋势投票为正，且风险分数很低
        if risk_op.vote == "negative" and trend_op.vote == "positive":
            if risk_op.score < 0.4:
                return True

        return False

    def _detect_data_confidence_conflict(
        self,
        data_op: AgentOpinion,
        all_opinions: List[AgentOpinion],
    ) -> bool:
        """检测数据-置信度冲突"""
        # 数据投票为负但多数其他 Agent 投票为正
        if data_op.vote == "negative":
            positive_count = sum(1 for o in all_opinions if o.vote == "positive" and o.agent_id != data_op.agent_id)
            if positive_count >= 3:
                return True

        return False
