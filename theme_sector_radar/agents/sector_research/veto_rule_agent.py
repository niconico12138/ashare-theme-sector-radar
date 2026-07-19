"""
L3 Veto 规则 Agent

实现 veto 机制。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_CONFLICT_CONSISTENCY


class VetoRuleAgent:
    """
    L3 Veto 规则 Agent

    实现 veto 机制。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def apply_veto(
        self,
        opinions: List[AgentOpinion],
        score_data: Dict[str, Any],
        conflict_level: str = "none",
    ) -> AgentOpinion:
        """
        应用 veto 规则

        Args:
            opinions: Agent 意见列表
            score_data: 评分数据
            conflict_level: 冲突级别

        Returns:
            Veto 结果
        """
        veto_triggered = False
        veto_reasons = []
        ranking_penalty = 0.0
        label_constraints = []

        # 1. 数据不足 veto
        history_coverage = score_data.get("history_coverage_ratio", 1.0)
        trend_window_status = score_data.get("trend_window_status", "ok")
        actual_history_days = score_data.get("actual_history_days", 20)
        if (
            history_coverage < 0.3
            or actual_history_days < 5
            or trend_window_status not in {"ok", "partial_history"}
        ):
            veto_triggered = True
            veto_reasons.append("数据不足，无法确认趋势")
            ranking_penalty += 0.3

        # 2. 高风险 veto
        risk_level = score_data.get("risk_level", "")
        if risk_level in ["risk_high", "risk_extreme"]:
            veto_triggered = True
            veto_reasons.append(f"风险等级过高: {risk_level}")
            ranking_penalty += 0.2

        # 3. 数据不可靠 veto (from data quality agent)
        data_quality_label = score_data.get("data_quality_label", "")
        if data_quality_label == "data_unreliable":
            veto_triggered = True
            veto_reasons.append("数据质量不可靠")
            ranking_penalty += 0.25

        # 生成证据
        evidence = []
        if veto_triggered:
            evidence.append(f"veto 触发: {'; '.join(veto_reasons)}")
        else:
            evidence.append("未触发 veto")

        return AgentOpinion(
            agent_id="veto_rule",
            layer=LAYER_CONFLICT_CONSISTENCY,
            label="veto_applied" if veto_triggered else "veto_not_applied",
            score=1.0 - ranking_penalty,
            confidence=0.9,
            evidence=evidence,
            veto=veto_triggered,
            veto_reason="; ".join(veto_reasons) if veto_reasons else "",
            metadata={
                "veto_triggered": veto_triggered,
                "veto_reasons": veto_reasons,
                "ranking_penalty": ranking_penalty,
                "label_constraints": label_constraints,
            },
        )
