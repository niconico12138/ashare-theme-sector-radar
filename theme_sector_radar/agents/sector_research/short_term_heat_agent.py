"""
短线热度智能体

从短线热度角度分析板块，输出热度标签和分数。
"""

from typing import Any, Dict, List


class ShortTermHeatAgent:
    """
    短线热度智能体

    基于短线爆发分和趋势分判断短线热度状态。
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
        分析短线热度

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据

        Returns:
            短线热度分析结果
        """
        # 提取输入
        short_term_burst_score = score_data.get("short_term_burst_score", 0.0)
        burst_level = score_data.get("burst_level", "")
        trend_continuation_score = score_data.get("trend_continuation_score", 0.0)

        # 确定热度标签
        heat_label = self._determine_label(short_term_burst_score)

        # 计算热度分数
        heat_score = self._calculate_score(short_term_burst_score)

        # 生成原因
        heat_reasons = self._generate_reasons(
            heat_label,
            short_term_burst_score,
        )

        # 生成冲突
        heat_conflicts = self._generate_conflicts(
            short_term_burst_score,
            trend_continuation_score,
        )

        # 生成观察要点
        heat_watch_points = self._generate_watch_points(
            heat_label,
            short_term_burst_score,
        )

        # 确定投票
        vote = self._determine_vote(heat_label)

        return {
            "heat_label": heat_label,
            "heat_score": heat_score,
            "heat_reasons": heat_reasons,
            "heat_conflicts": heat_conflicts,
            "heat_watch_points": heat_watch_points,
            "vote": vote,
        }

    def _determine_label(self, short_term_burst_score: float) -> str:
        """确定热度标签"""
        if short_term_burst_score >= 65:
            return "heat_active"
        elif short_term_burst_score >= 50:
            return "heat_moderate"
        elif short_term_burst_score >= 35:
            return "heat_fading"
        else:
            return "heat_weak"

    def _calculate_score(self, short_term_burst_score: float) -> float:
        """计算热度分数 (0-1)"""
        return round(short_term_burst_score / 100.0, 2)

    def _generate_reasons(
        self,
        heat_label: str,
        short_term_burst_score: float,
    ) -> List[str]:
        """生成热度原因"""
        reasons = []

        if heat_label == "heat_active":
            reasons.append("短线热度活跃")
        elif heat_label == "heat_moderate":
            reasons.append("短线热度适中")
        elif heat_label == "heat_fading":
            reasons.append("短线热度减弱")
        elif heat_label == "heat_weak":
            reasons.append("短线热度偏弱")

        return reasons

    def _generate_conflicts(
        self,
        short_term_burst_score: float,
        trend_continuation_score: float,
    ) -> List[str]:
        """生成热度冲突"""
        conflicts = []

        # burst 高但 trend 低
        if short_term_burst_score >= 65 and trend_continuation_score < 50:
            conflicts.append("短线热度强但趋势未确认")

        # trend 高但 burst 低
        if trend_continuation_score >= 65 and short_term_burst_score < 50:
            conflicts.append("趋势较稳但短线降温")

        return conflicts

    def _generate_watch_points(
        self,
        heat_label: str,
        short_term_burst_score: float,
    ) -> List[str]:
        """生成热度观察要点"""
        points = []

        if heat_label == "heat_active":
            points.append("短线热度活跃，观察是否持续")
        elif heat_label == "heat_moderate":
            points.append("短线热度适中，可适度关注")
        elif heat_label == "heat_fading":
            points.append("短线热度减弱，谨慎观察")
        elif heat_label == "heat_weak":
            points.append("短线热度偏弱，建议回避")

        return points

    def _determine_vote(self, heat_label: str) -> str:
        """确定投票方向"""
        if heat_label in ["heat_active"]:
            return "positive"
        elif heat_label in ["heat_moderate"]:
            return "neutral"
        elif heat_label in ["heat_fading", "heat_weak"]:
            return "negative"
        return "neutral"
