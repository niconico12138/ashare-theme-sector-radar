"""
轮动分析智能体

从轮动角度分析板块，输出轮动标签和分数。
"""

from typing import Any, Dict, List


class RotationAnalysisAgent:
    """
    轮动分析智能体

    基于轮动阶段和多窗口共识判断轮动状态。
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
        分析轮动状态

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据
            consensus_data: 多窗口共识数据

        Returns:
            轮动分析结果
        """
        # 提取输入
        rotation_phase = score_data.get("rotation_phase", "")
        multi_window_label = consensus_data.get("multi_window_label", "")

        # 确定轮动标签
        rotation_label = self._determine_label(rotation_phase, multi_window_label)

        # 计算轮动分数
        rotation_score = self._calculate_score(rotation_phase, multi_window_label)

        # 生成原因
        rotation_reasons = self._generate_reasons(rotation_label, rotation_phase)

        # 生成观察要点
        rotation_watch_points = self._generate_watch_points(rotation_label)

        # 确定投票
        vote = self._determine_vote(rotation_label)

        return {
            "rotation_label": rotation_label,
            "rotation_score": rotation_score,
            "rotation_reasons": rotation_reasons,
            "rotation_watch_points": rotation_watch_points,
            "vote": vote,
        }

    def _determine_label(self, rotation_phase: str, multi_window_label: str) -> str:
        """确定轮动标签"""
        if multi_window_label == "weak_all_windows":
            return "rotation_weak"

        if rotation_phase == "leading":
            return "rotation_rising"
        elif rotation_phase == "improving":
            return "rotation_improving"
        elif rotation_phase == "weakening":
            return "rotation_weakening"
        elif rotation_phase == "lagging":
            return "rotation_lagging"
        else:
            return "rotation_neutral"

    def _calculate_score(self, rotation_phase: str, multi_window_label: str) -> float:
        """计算轮动分数 (0-1)"""
        base_score = {
            "leading": 0.8,
            "improving": 0.6,
            "weakening": 0.4,
            "lagging": 0.2,
        }.get(rotation_phase, 0.5)

        # 根据 multi_window_label 调整
        if multi_window_label == "multi_window_confirmed":
            base_score += 0.1
        elif multi_window_label == "weak_all_windows":
            base_score -= 0.2

        return round(max(0.0, min(1.0, base_score)), 2)

    def _generate_reasons(self, rotation_label: str, rotation_phase: str) -> List[str]:
        """生成轮动原因"""
        reasons = []

        if rotation_label == "rotation_rising":
            reasons.append("板块处于上升阶段")
        elif rotation_label == "rotation_improving":
            reasons.append("板块正在改善")
        elif rotation_label == "rotation_weakening":
            reasons.append("板块正在弱化")
        elif rotation_label == "rotation_lagging":
            reasons.append("板块处于落后阶段")
        elif rotation_label == "rotation_weak":
            reasons.append("全窗口偏弱")
        else:
            reasons.append("轮动状态中性")

        return reasons

    def _generate_watch_points(self, rotation_label: str) -> List[str]:
        """生成轮动观察要点"""
        points = []

        if rotation_label == "rotation_rising":
            points.append("板块处于上升阶段，观察持续性")
        elif rotation_label == "rotation_improving":
            points.append("板块正在改善，观察是否确认")
        elif rotation_label == "rotation_weakening":
            points.append("板块正在弱化，谨慎观察")
        elif rotation_label == "rotation_lagging":
            points.append("板块处于落后阶段，建议回避")
        elif rotation_label == "rotation_weak":
            points.append("全窗口偏弱，建议回避")

        return points

    def _determine_vote(self, rotation_label: str) -> str:
        """确定投票方向"""
        if rotation_label in ["rotation_rising", "rotation_improving"]:
            return "positive"
        elif rotation_label in ["rotation_neutral"]:
            return "neutral"
        elif rotation_label in ["rotation_weakening", "rotation_lagging", "rotation_weak"]:
            return "negative"
        return "neutral"
