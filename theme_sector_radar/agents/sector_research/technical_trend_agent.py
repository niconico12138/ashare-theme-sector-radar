"""
技术面趋势智能体

从技术面角度分析板块趋势，输出技术面标签和分数。
"""

from typing import Any, Dict, List


class TechnicalTrendAgent:
    """
    技术面趋势智能体

    基于多窗口共识和趋势指标判断技术面状态。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        score_data: Dict[str, Any],
        consensus_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析技术面趋势

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据
            consensus_data: 多窗口共识数据

        Returns:
            技术面分析结果
        """
        # 提取输入
        multi_window_label = consensus_data.get("multi_window_label", "")
        consensus_score = consensus_data.get("consensus_score", 0.0)
        window_scores = consensus_data.get("window_scores", {})

        # 确定技术面标签
        technical_label = self._determine_label(multi_window_label, consensus_score)

        # 计算技术面分数
        technical_score = self._calculate_score(
            consensus_score,
            multi_window_label,
            window_scores,
        )

        # 生成原因
        technical_reasons = self._generate_reasons(
            technical_label,
            consensus_score,
            multi_window_label,
        )

        # 生成冲突
        technical_conflicts = self._generate_conflicts(
            multi_window_label,
            window_scores,
        )

        # 生成观察要点
        technical_watch_points = self._generate_watch_points(
            technical_label,
            consensus_score,
        )

        # 确定投票
        vote = self._determine_vote(technical_label, consensus_score)

        return {
            "technical_label": technical_label,
            "technical_score": technical_score,
            "technical_reasons": technical_reasons,
            "technical_conflicts": technical_conflicts,
            "technical_watch_points": technical_watch_points,
            "vote": vote,
        }

    def _determine_label(self, multi_window_label: str, consensus_score: float) -> str:
        """确定技术面标签"""
        if multi_window_label == "multi_window_confirmed" and consensus_score >= 50:
            return "trend_confirmed"
        elif multi_window_label == "conflicted_windows":
            return "trend_conflicted"
        elif multi_window_label == "short_mid_strong_long_weak":
            return "trend_forming"
        elif multi_window_label == "weak_all_windows":
            return "trend_weak"
        elif multi_window_label == "insufficient_history":
            return "trend_unreliable"
        elif multi_window_label == "short_active_only":
            return "trend_short_active"
        elif multi_window_label == "long_stable_short_cooling":
            return "trend_long_stable"
        else:
            return "trend_neutral"

    def _calculate_score(
        self,
        consensus_score: float,
        multi_window_label: str,
        window_scores: Dict[str, float],
    ) -> float:
        """计算技术面分数 (0-1)"""
        # 基础分数
        base_score = consensus_score / 100.0

        # 根据标签调整
        if multi_window_label == "multi_window_confirmed":
            base_score += 0.15
        elif multi_window_label == "conflicted_windows":
            base_score -= 0.10
        elif multi_window_label == "weak_all_windows":
            base_score -= 0.20
        elif multi_window_label == "insufficient_history":
            base_score = min(base_score, 0.30)

        # Clamp 到 0-1
        return round(max(0.0, min(1.0, base_score)), 2)

    def _generate_reasons(
        self,
        technical_label: str,
        consensus_score: float,
        multi_window_label: str,
    ) -> List[str]:
        """生成技术面原因"""
        reasons = []

        if technical_label == "trend_confirmed":
            reasons.append("多窗口趋势确认，技术面较强")
        elif technical_label == "trend_conflicted":
            reasons.append("窗口之间存在分歧")
        elif technical_label == "trend_forming":
            reasons.append("短中期趋势正在形成")
        elif technical_label == "trend_weak":
            reasons.append("全窗口偏弱")
        elif technical_label == "trend_unreliable":
            reasons.append("历史数据不足，技术面不可靠")
        elif technical_label == "trend_short_active":
            reasons.append("短线活跃但趋势未确认")
        elif technical_label == "trend_long_stable":
            reasons.append("中期趋势稳定但短线降温")

        if consensus_score >= 65:
            reasons.append("共识分数较高")
        elif consensus_score < 40:
            reasons.append("共识分数偏低")

        return reasons

    def _generate_conflicts(
        self,
        multi_window_label: str,
        window_scores: Dict[str, float],
    ) -> List[str]:
        """生成技术面冲突"""
        conflicts = []

        if multi_window_label == "conflicted_windows":
            conflicts.append("窗口之间分歧较大，技术面信号不一致")

        return conflicts

    def _generate_watch_points(
        self,
        technical_label: str,
        consensus_score: float,
    ) -> List[str]:
        """生成技术面观察要点"""
        points = []

        if technical_label == "trend_confirmed":
            points.append("趋势确认，可作为重点观察对象")
        elif technical_label == "trend_forming":
            points.append("趋势正在形成，观察是否确认")
        elif technical_label == "trend_weak":
            points.append("趋势偏弱，建议回避或等待反转信号")
        elif technical_label == "trend_unreliable":
            points.append("数据不足，建议积累更多数据后再评估")
        elif technical_label == "trend_short_active":
            points.append("短线活跃，观察趋势是否跟进")
        elif technical_label == "trend_long_stable":
            points.append("中期稳定，观察短线是否重新启动")

        return points

    def _determine_vote(self, technical_label: str, consensus_score: float) -> str:
        """确定投票方向"""
        if technical_label in ["trend_confirmed"] and consensus_score >= 50:
            return "positive"
        elif technical_label in ["trend_forming", "trend_short_active", "trend_long_stable"]:
            return "neutral"
        elif technical_label in ["trend_weak", "trend_unreliable"]:
            return "negative"
        else:
            return "neutral"
