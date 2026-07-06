"""
风险控制智能体

从风险角度分析板块，输出风险标签和分数。
"""

from typing import Any, Dict, List


class RiskControlAgent:
    """
    风险控制智能体

    基于风险扣分和数据质量判断风险状态。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        score_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析风险控制

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据

        Returns:
            风险控制分析结果
        """
        # 提取输入
        risk_penalty = score_data.get("risk_penalty", 0.0)
        trend_window_status = score_data.get("trend_window_status", "ok")
        data_warnings = score_data.get("data_warnings", [])

        # 确定风险标签
        risk_label = self._determine_label(risk_penalty)

        # 计算风险分数 (越高越可控)
        risk_score = self._calculate_score(risk_penalty)

        # 生成风险标志
        risk_flags = self._generate_flags(trend_window_status, data_warnings)

        # 生成风险摘要
        risk_summary = self._generate_summary(risk_label, risk_penalty, risk_flags)

        # 确定投票（基于风险状态、veto、conflict 等多维度）
        vote = self._determine_vote(risk_label, risk_score, risk_flags, score_data)

        return {
            "risk_label": risk_label,
            "risk_score": risk_score,
            "risk_flags": risk_flags,
            "risk_summary": risk_summary,
            "vote": vote,
        }

    def _determine_label(self, risk_penalty: float) -> str:
        """确定风险标签"""
        if risk_penalty <= 3:
            return "risk_low"
        elif risk_penalty <= 8:
            return "risk_moderate"
        elif risk_penalty <= 15:
            return "risk_high"
        else:
            return "risk_extreme"

    def _calculate_score(self, risk_penalty: float) -> float:
        """计算风险分数 (0-1，越高越可控)"""
        # risk_penalty 越高，分数越低
        score = 1.0 - (risk_penalty / 20.0)
        return round(max(0.0, min(1.0, score)), 2)

    def _generate_flags(
        self,
        trend_window_status: str,
        data_warnings: List[str],
    ) -> List[str]:
        """生成风险标志"""
        flags = []

        if trend_window_status != "ok":
            flags.append("history_unreliable")

        if data_warnings:
            flags.append("data_warning_present")

        return flags

    def _generate_summary(
        self,
        risk_label: str,
        risk_penalty: float,
        risk_flags: List[str],
    ) -> str:
        """生成风险摘要"""
        summaries = {
            "risk_low": "风险较低，板块表现相对稳定",
            "risk_moderate": "风险适中，需关注波动",
            "risk_high": "风险较高，建议谨慎",
            "risk_extreme": "风险极高，建议回避",
        }

        summary = summaries.get(risk_label, "风险状态未知")

        if risk_flags:
            summary += f" (存在 {', '.join(risk_flags)} 风险标志)"

        return summary

    def _determine_vote(
        self,
        risk_label: str,
        risk_score: float,
        risk_flags: List[str],
        score_data: Dict[str, Any],
    ) -> str:
        """
        确定投票方向

        基于风险状态、veto、conflict 等多维度判断。

        - positive: 风险低且无风险标志
        - neutral: 风险中性或信息不足
        - negative: 风险高、有风险标志、veto 触发、conflict 明显
        """
        # 1. 高风险/极端风险 → negative
        if risk_label in ["risk_high", "risk_extreme"]:
            return "negative"

        # 2. 有风险标志 → negative
        if risk_flags:
            return "negative"

        # 3. veto 触发 → negative
        veto_triggered = score_data.get("veto_triggered", False)
        if veto_triggered:
            return "negative"

        # 4. conflict 明显 → negative
        conflict_level = score_data.get("conflict_level", "none")
        if conflict_level == "high":
            return "negative"

        # 5. 风险低且无问题 → positive
        if risk_label == "risk_low" and risk_score >= 0.7:
            return "positive"

        # 6. 其他情况 → neutral
        return "neutral"
