"""
多窗口趋势共识 Agent

合并同一板块在 5日、10日、20日窗口下的趋势评分，输出多窗口趋势共识结果。

标签规则：
- multi_window_confirmed: 5/10/20 均 >= 50 且 coverage ok
- short_mid_strong_long_weak: 5/10 >= 45，20 < 45
- short_active_only: 5 >= 50，10/20 < 45
- long_stable_short_cooling: 20 >= 50，5 < 45
- weak_all_windows: 5/10/20 均 < 45
- conflicted_windows: 不符合以上规则或窗口差异 >= 25
- insufficient_history: 任一窗口 status != ok 或 coverage < 1.0
"""

from typing import Any, Dict, List, Optional, Tuple


# 标签定义
MULTI_WINDOW_LABELS = {
    "multi_window_confirmed": "多窗口均不弱，趋势跨窗口确认",
    "short_mid_strong_long_weak": "短中期相对较强，但中期确认不足",
    "short_active_only": "只有短窗口活跃，趋势未确认",
    "long_stable_short_cooling": "中期相对稳定，但短线降温",
    "weak_all_windows": "全窗口偏弱",
    "conflicted_windows": "窗口之间分歧较大，暂不形成明确共识",
    "insufficient_history": "历史数据不足，不能确认趋势共识",
}

# 共识强度阈值
CONSENSUS_STRENGTH_THRESHOLDS = {
    "strong": 65.0,
    "medium": 50.0,
    "weak": 35.0,
    "very_weak": 0.0,
}

# 窗口权重
WINDOW_WEIGHTS = {
    "5": 0.25,
    "10": 0.35,
    "20": 0.40,
}


class MultiWindowConsensusAgent:
    """
    多窗口趋势共识 Agent

    合并同一板块在 5日、10日、20日窗口下的趋势评分，
    输出多窗口趋势共识结果。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def _check_insufficient_history(
        self,
        windows: Dict[str, Dict[str, Any]],
    ) -> bool:
        """
        检查历史数据是否不足

        Args:
            windows: 窗口数据字典

        Returns:
            是否历史数据不足
        """
        for window_key in ["5", "10", "20"]:
            window_data = windows.get(window_key, {})
            status = window_data.get("trend_window_status", "insufficient_history")
            coverage = window_data.get("history_coverage_ratio", 0.0)

            if status != "ok" or coverage < 1.0:
                return True

        return False

    def _calculate_consensus_score(
        self,
        windows: Dict[str, Dict[str, float]],
    ) -> float:
        """
        计算共识分数 (加权平均)

        Args:
            windows: 窗口分数字典

        Returns:
            共识分数
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for window_key, weight in WINDOW_WEIGHTS.items():
            score = windows.get(window_key, 0.0)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight > 0:
            return round(weighted_sum / total_weight, 2)
        return 0.0

    def _get_consensus_strength(self, consensus_score: float) -> str:
        """
        获取共识强度

        Args:
            consensus_score: 共识分数

        Returns:
            共识强度
        """
        for strength, threshold in CONSENSUS_STRENGTH_THRESHOLDS.items():
            if consensus_score >= threshold:
                return strength
        return "very_weak"

    def _determine_label(
        self,
        window_scores: Dict[str, float],
        windows: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        确定多窗口标签

        Args:
            window_scores: 窗口分数字典
            windows: 窗口数据字典

        Returns:
            多窗口标签
        """
        # 检查历史数据是否不足
        if self._check_insufficient_history(windows):
            return "insufficient_history"

        # 获取各窗口分数
        score_5 = window_scores.get("5", 0.0)
        score_10 = window_scores.get("10", 0.0)
        score_20 = window_scores.get("20", 0.0)

        # 计算窗口差异
        all_scores = [score_5, score_10, score_20]
        max_score = max(all_scores)
        min_score = min(all_scores)
        score_range = max_score - min_score

        # multi_window_confirmed: 5/10/20 均 >= 50
        if score_5 >= 50 and score_10 >= 50 and score_20 >= 50:
            return "multi_window_confirmed"

        # short_mid_strong_long_weak: 5/10 >= 45，20 < 45
        if score_5 >= 45 and score_10 >= 45 and score_20 < 45:
            return "short_mid_strong_long_weak"

        # short_active_only: 5 >= 50，10/20 < 45
        if score_5 >= 50 and score_10 < 45 and score_20 < 45:
            return "short_active_only"

        # long_stable_short_cooling: 20 >= 50，5 < 45
        if score_20 >= 50 and score_5 < 45:
            return "long_stable_short_cooling"

        # weak_all_windows: 5/10/20 均 < 45
        if score_5 < 45 and score_10 < 45 and score_20 < 45:
            return "weak_all_windows"

        # conflicted_windows: 窗口差异 >= 25 或不符合以上规则
        if score_range >= 25:
            return "conflicted_windows"

        return "conflicted_windows"

    def _generate_window_conflicts(
        self,
        window_scores: Dict[str, float],
        window_levels: Dict[str, str],
    ) -> List[str]:
        """
        生成窗口冲突说明

        Args:
            window_scores: 窗口分数字典
            window_levels: 窗口等级字典

        Returns:
            冲突说明列表
        """
        conflicts = []

        score_5 = window_scores.get("5", 0.0)
        score_10 = window_scores.get("10", 0.0)
        score_20 = window_scores.get("20", 0.0)

        # 检查 20日与5/10日的差异
        if score_20 < score_5 - 10 and score_20 < score_10 - 10:
            conflicts.append("20日趋势分明显弱于5日和10日")

        if score_5 > score_20 + 15:
            conflicts.append("短中期动量强于中期趋势")

        # 检查等级不一致
        levels = [window_levels.get("5", ""), window_levels.get("10", ""), window_levels.get("20", "")]
        if len(set(levels)) > 1:
            conflicts.append("各窗口趋势等级不一致")

        return conflicts

    def _generate_watch_points(
        self,
        label: str,
        window_scores: Dict[str, float],
        window_levels: Dict[str, str],
    ) -> List[str]:
        """
        生成观察要点

        Args:
            label: 多窗口标签
            window_scores: 窗口分数字典
            window_levels: 窗口等级字典

        Returns:
            观察要点列表
        """
        points = []

        if label == "multi_window_confirmed":
            points.append("趋势跨窗口确认，可作为重点观察对象")
            points.append("关注资金流入和成交量是否持续放大")

        elif label == "short_mid_strong_long_weak":
            points.append("观察20日趋势分是否继续抬升")
            points.append("若短窗口继续强而20日不跟随，说明趋势确认不足")

        elif label == "short_active_only":
            points.append("只有短窗口活跃，趋势未确认")
            points.append("观察10日和20日趋势分是否跟进")

        elif label == "long_stable_short_cooling":
            points.append("中期趋势仍在，但短线降温")
            points.append("观察短线是否重新启动")

        elif label == "weak_all_windows":
            points.append("全窗口偏弱，建议回避或等待反转信号")

        elif label == "conflicted_windows":
            points.append("窗口之间分歧较大，暂不形成明确结论")
            points.append("观察后续走势是否收敛")

        elif label == "insufficient_history":
            points.append("历史数据不足，不能确认趋势共识")
            points.append("建议积累更多数据后再评估")

        return points

    def _generate_data_warnings(
        self,
        windows: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """
        生成数据警告

        Args:
            windows: 窗口数据字典

        Returns:
            警告列表
        """
        warnings = []

        for window_key in ["5", "10", "20"]:
            window_data = windows.get(window_key, {})
            status = window_data.get("trend_window_status", "")
            coverage = window_data.get("history_coverage_ratio", 0.0)
            actual_days = window_data.get("actual_history_days", 0)

            if status != "ok":
                warnings.append(f"{window_key}日窗口历史数据不足 (status={status})")
            elif coverage < 1.0:
                warnings.append(f"{window_key}日窗口覆盖率不足 ({coverage:.0%}, 实际{actual_days}天)")

        return warnings

    def analyze_sector(
        self,
        sector_name: str,
        sector_type: str,
        windows: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        分析单个板块的多窗口共识

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            windows: 窗口数据字典

        Returns:
            共识分析结果
        """
        # 提取各窗口分数和等级
        window_scores = {}
        window_levels = {}

        for window_key in ["5", "10", "20"]:
            window_data = windows.get(window_key, {})
            window_scores[window_key] = window_data.get("trend_continuation_score", 0.0)
            window_levels[window_key] = window_data.get("trend_level", "")

        # 计算共识分数
        consensus_score = self._calculate_consensus_score(window_scores)

        # 确定共识强度
        consensus_strength = self._get_consensus_strength(consensus_score)

        # 确定多窗口标签
        label = self._determine_label(window_scores, windows)

        # 生成窗口冲突说明
        window_conflicts = self._generate_window_conflicts(window_scores, window_levels)

        # 生成观察要点
        watch_points = self._generate_watch_points(label, window_scores, window_levels)

        # 生成数据警告
        data_warnings = self._generate_data_warnings(windows)

        return {
            "sector_name": sector_name,
            "sector_type": sector_type,
            "multi_window_label": label,
            "consensus_score": consensus_score,
            "consensus_strength": consensus_strength,
            "window_scores": window_scores,
            "window_levels": window_levels,
            "window_conflicts": window_conflicts,
            "watch_points": watch_points,
            "data_warnings": data_warnings,
        }

    def analyze_sectors(
        self,
        sectors_data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        批量分析板块多窗口共识

        Args:
            sectors_data: 板块数据列表

        Returns:
            共识分析结果列表
        """
        results = []

        for sector_data in sectors_data:
            sector_name = sector_data.get("sector_name", "")
            sector_type = sector_data.get("sector_type", "industry")
            windows = sector_data.get("windows", {})

            result = self.analyze_sector(sector_name, sector_type, windows)
            results.append(result)

        # 按共识分数排序
        results.sort(key=lambda x: x["consensus_score"], reverse=True)

        return results
