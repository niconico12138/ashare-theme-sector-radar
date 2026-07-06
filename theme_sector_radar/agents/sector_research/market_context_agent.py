"""
市场环境智能体

从市场环境角度分析板块，输出市场环境标签和分数。
"""

from typing import Any, Dict, List


class MarketContextAgent:
    """
    市场环境智能体

    基于市场温度和基准表现判断市场环境。
    """

    def __init__(self):
        """初始化 Agent"""
        pass

    def analyze(
        self,
        sector_name: str,
        sector_type: str,
        score_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析市场环境

        Args:
            sector_name: 板块名称
            sector_type: 板块类型
            score_data: 评分数据
            market_data: 市场数据

        Returns:
            市场环境分析结果
        """
        # 提取输入
        benchmark_status = market_data.get("benchmark_status", "none")
        relative_strength_component = score_data.get("relative_strength_component", 0.0)

        # 确定市场环境标签
        market_context_label = self._determine_label(
            benchmark_status,
            relative_strength_component,
        )

        # 计算市场环境分数
        market_context_score = self._calculate_score(
            benchmark_status,
            relative_strength_component,
        )

        # 生成市场环境摘要
        market_context_summary = self._generate_summary(
            market_context_label,
            benchmark_status,
            relative_strength_component,
        )

        # 生成观察要点
        market_watch_points = self._generate_watch_points(market_context_label)

        # 确定投票（基于市场环境和 regime 信息）
        vote = self._determine_vote(market_context_label, score_data, market_data)

        return {
            "market_context_label": market_context_label,
            "market_context_score": market_context_score,
            "market_context_summary": market_context_summary,
            "market_watch_points": market_watch_points,
            "vote": vote,
        }

    def _determine_label(
        self,
        benchmark_status: str,
        relative_strength_component: float,
    ) -> str:
        """确定市场环境标签"""
        if benchmark_status != "ok":
            return "benchmark_unavailable"

        if relative_strength_component >= 12:
            return "outperforming_benchmark"
        elif relative_strength_component >= 8:
            return "neutral_vs_benchmark"
        else:
            return "underperforming_benchmark"

    def _calculate_score(
        self,
        benchmark_status: str,
        relative_strength_component: float,
    ) -> float:
        """计算市场环境分数 (0-1)"""
        if benchmark_status != "ok":
            return 0.3

        # relative_strength_component 范围 0-15
        base_score = relative_strength_component / 15.0
        return round(max(0.0, min(1.0, base_score)), 2)

    def _generate_summary(
        self,
        market_context_label: str,
        benchmark_status: str,
        relative_strength_component: float,
    ) -> str:
        """生成市场环境摘要"""
        summaries = {
            "outperforming_benchmark": "板块跑赢市场基准",
            "neutral_vs_benchmark": "板块与市场基准持平",
            "underperforming_benchmark": "板块跑输市场基准",
            "benchmark_unavailable": "市场基准不可用",
        }

        summary = summaries.get(market_context_label, "市场环境未知")

        if benchmark_status == "ok":
            summary += f" (相对强度: {relative_strength_component:.1f}/15)"

        return summary

    def _generate_watch_points(self, market_context_label: str) -> List[str]:
        """生成市场环境观察要点"""
        points = []

        if market_context_label == "outperforming_benchmark":
            points.append("板块跑赢市场基准，表现相对强势")
        elif market_context_label == "neutral_vs_benchmark":
            points.append("板块与市场基准持平")
        elif market_context_label == "underperforming_benchmark":
            points.append("板块跑输市场基准，表现相对较弱")
        elif market_context_label == "benchmark_unavailable":
            points.append("市场基准不可用，无法判断相对表现")

        return points

    def _determine_vote(
        self,
        market_context_label: str,
        score_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> str:
        """
        确定投票方向

        基于市场环境和 regime 信息判断。

        - positive: risk_on 或 choppy_market 且信号不差
        - neutral: choppy_market / weak_rebound 且信号分化
        - negative: risk_off / broad_falling / cold
        """
        # 1. outperforming → positive
        if market_context_label == "outperforming_benchmark":
            return "positive"

        # 2. 获取 regime 信息
        regime = market_data.get("regime_composite_label", "unknown_regime")
        breadth = market_data.get("breadth_regime", "breadth_unknown")
        temperature = market_data.get("market_temperature_regime", "market_unknown")

        # 3. risk_on → positive
        if regime == "risk_on":
            return "positive"

        # 4. risk_off → negative
        if regime == "risk_off":
            return "negative"

        # 5. broad_falling → negative
        if breadth == "broad_falling":
            return "negative"

        # 6. cold → negative
        if temperature == "market_cold":
            return "negative"

        # 7. choppy_market 且信号不差 → neutral
        if regime == "choppy_market":
            if market_context_label == "neutral_vs_benchmark":
                return "neutral"
            elif market_context_label == "underperforming_benchmark":
                return "negative"

        # 8. weak_rebound → neutral
        if regime == "weak_rebound":
            return "neutral"

        # 9. 默认 neutral
        return "neutral"
