"""
L2 资金量能分析 Agent

分析资金和量能状态。
"""

from typing import Any, Dict, List, Optional

from .opinion import AgentOpinion, LAYER_SPECIALIZED, VOTE_POSITIVE, VOTE_NEUTRAL, VOTE_NEGATIVE


class CapitalVolumeAgent:
    """
    L2 资金量能分析 Agent

    分析资金和量能状态。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        score_data: Dict[str, Any],
    ) -> AgentOpinion:
        """
        分析资金量能

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据

        Returns:
            AgentOpinion
        """
        # 提取资金流数据
        main_net_inflow = score_data.get("main_net_inflow", 0.0)
        turnover = score_data.get("turnover", 0.0)
        volume_or_heat_component = score_data.get("volume_or_heat_component", 0.0)

        # 判断资金流可用性
        capital_flow_available = main_net_inflow != 0.0 or turnover > 0

        # 确定标签
        label, vote = self._determine_label(
            main_net_inflow, turnover, volume_or_heat_component, capital_flow_available
        )

        # 生成证据
        evidence = []
        if main_net_inflow > 0:
            evidence.append(f"主力净流入: {main_net_inflow:.2f}")
        elif main_net_inflow < 0:
            evidence.append(f"主力净流出: {main_net_inflow:.2f}")

        if turnover > 0:
            evidence.append(f"成交额: {turnover:.2f}")

        if not capital_flow_available:
            evidence.append("资金流数据缺失")

        # 生成警告
        warnings = []
        if not capital_flow_available:
            warnings.append("资金流数据不可用，标签可能不准确")

        return AgentOpinion(
            agent_id="capital_volume",
            layer=LAYER_SPECIALIZED,
            label=label,
            score=self._calculate_score(label),
            confidence=0.7 if capital_flow_available else 0.4,
            evidence=evidence,
            warnings=warnings,
            vote=vote,
        )

    def _determine_label(
        self,
        main_net_inflow: float,
        turnover: float,
        volume_or_heat_component: float,
        capital_flow_available: bool,
    ) -> tuple:
        """
        确定标签

        Returns:
            (label, vote)
        """
        if not capital_flow_available:
            return "capital_volume_unknown", VOTE_NEUTRAL

        if main_net_inflow > 500_000_000:  # 5亿
            return "capital_volume_positive", VOTE_POSITIVE
        elif main_net_inflow > 0:
            return "capital_volume_neutral", VOTE_NEUTRAL
        elif main_net_inflow < -500_000_000:
            return "capital_volume_weak", VOTE_NEGATIVE
        else:
            return "capital_volume_divergent", VOTE_NEUTRAL

    def _calculate_score(self, label: str) -> float:
        """计算分数"""
        score_mapping = {
            "capital_volume_positive": 0.8,
            "capital_volume_neutral": 0.5,
            "capital_volume_divergent": 0.4,
            "capital_volume_weak": 0.2,
            "capital_volume_unknown": 0.3,
        }
        return score_mapping.get(label, 0.5)
