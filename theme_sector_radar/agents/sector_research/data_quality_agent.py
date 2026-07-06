"""
数据质量智能体

从数据质量角度分析板块，输出数据质量标签和分数。
"""

from typing import Any, Dict, List


class DataQualityAgent:
    """
    数据质量智能体

    基于历史数据覆盖率和状态判断数据质量。
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
        分析数据质量

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据

        Returns:
            数据质量分析结果
        """
        # 提取输入
        history_coverage_ratio = score_data.get("history_coverage_ratio", 0.0)
        trend_window_status = score_data.get("trend_window_status", "")
        actual_history_days = score_data.get("actual_history_days", 0)

        # 确定数据质量标签
        data_quality_label = self._determine_label(
            history_coverage_ratio,
            trend_window_status,
        )

        # 计算数据质量分数
        data_quality_score = self._calculate_score(
            history_coverage_ratio,
            trend_window_status,
        )

        # 生成数据警告
        data_quality_warnings = self._generate_warnings(
            history_coverage_ratio,
            trend_window_status,
            actual_history_days,
        )

        # 生成可靠性摘要
        data_reliability_summary = self._generate_summary(
            data_quality_label,
            history_coverage_ratio,
            actual_history_days,
        )

        # 确定投票（基于数据质量多维度判断）
        vote = self._determine_vote(data_quality_label, history_coverage_ratio, trend_window_status, data_quality_warnings)

        return {
            "data_quality_label": data_quality_label,
            "data_quality_score": data_quality_score,
            "data_quality_warnings": data_quality_warnings,
            "data_reliability_summary": data_reliability_summary,
            "vote": vote,
        }

    def _determine_label(
        self,
        history_coverage_ratio: float,
        trend_window_status: str,
    ) -> str:
        """确定数据质量标签"""
        if trend_window_status != "ok":
            return "data_unreliable"

        if history_coverage_ratio >= 1.0:
            return "data_reliable"
        elif history_coverage_ratio >= 0.8:
            return "data_usable"
        else:
            return "data_limited"

    def _calculate_score(
        self,
        history_coverage_ratio: float,
        trend_window_status: str,
    ) -> float:
        """计算数据质量分数 (0-1)"""
        if trend_window_status != "ok":
            return 0.2

        base_score = history_coverage_ratio
        return round(max(0.0, min(1.0, base_score)), 2)

    def _generate_warnings(
        self,
        history_coverage_ratio: float,
        trend_window_status: str,
        actual_history_days: int,
    ) -> List[str]:
        """生成数据警告"""
        warnings = []

        if trend_window_status != "ok":
            warnings.append(f"趋势窗口状态异常: {trend_window_status}")

        if history_coverage_ratio < 0.8:
            warnings.append(f"历史数据覆盖率不足: {history_coverage_ratio:.0%}")

        if actual_history_days < 10:
            warnings.append(f"历史数据天数较少: {actual_history_days} 天")

        return warnings

    def _generate_summary(
        self,
        data_quality_label: str,
        history_coverage_ratio: float,
        actual_history_days: int,
    ) -> str:
        """生成数据质量摘要"""
        summaries = {
            "data_reliable": "数据质量可靠，历史数据完整",
            "data_usable": "数据可用，但覆盖率略有不足",
            "data_limited": "数据有限，评分可靠性降低",
            "data_unreliable": "数据不可靠，趋势窗口状态异常",
        }

        summary = summaries.get(data_quality_label, "数据质量未知")
        summary += f" (覆盖率: {history_coverage_ratio:.0%}, 实际天数: {actual_history_days})"

        return summary

    def _determine_vote(
        self,
        data_quality_label: str,
        history_coverage_ratio: float,
        trend_window_status: str,
        data_quality_warnings: List[str],
    ) -> str:
        """
        确定投票方向

        基于数据质量多维度判断。

        - positive: 数据可靠、覆盖率高、无关键警告
        - neutral: 数据可用、覆盖率中等、有轻微警告
        - negative: 数据不可靠、覆盖率低、有严重警告
        """
        # 1. 数据不可靠 → negative
        if data_quality_label == "data_unreliable":
            return "negative"

        # 2. 趋势窗口异常 → negative
        if trend_window_status != "ok":
            return "negative"

        # 3. 覆盖率极低 → negative
        if history_coverage_ratio < 0.5:
            return "negative"

        # 4. 有严重警告 → negative
        critical_warnings = [w for w in data_quality_warnings if "异常" in w or "不可靠" in w]
        if critical_warnings:
            return "negative"

        # 5. 数据可靠且覆盖率 >= 0.9 → positive
        if data_quality_label == "data_reliable" and history_coverage_ratio >= 0.9:
            return "positive"

        # 6. 数据可用且覆盖率 >= 0.7 → neutral
        if data_quality_label == "data_usable" and history_coverage_ratio >= 0.7:
            return "neutral"

        # 7. 数据有限 → neutral
        if data_quality_label == "data_limited":
            return "neutral"

        # 8. 默认 neutral
        return "neutral"
