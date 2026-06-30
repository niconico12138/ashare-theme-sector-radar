"""
板块历史数据分析器

计算行业/概念板块的历史指标和筛选候选板块。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import SectorType


class SectorHistoryAnalyzer:
    """板块历史数据分析器"""

    def __init__(self, data_cache_dir: str = "data_cache"):
        """
        初始化分析器

        Args:
            data_cache_dir: 数据缓存目录
        """
        self.data_cache_dir = data_cache_dir

    def load_sector_history(
        self,
        sector_type: SectorType,
        sector_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        加载板块历史数据

        Args:
            sector_type: 板块类型
            sector_name: 板块名称

        Returns:
            板块历史数据，不存在返回 None
        """
        type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
        file_path = os.path.join(self.data_cache_dir, "sector_history", type_dir, f"{sector_name}.json")

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_available_sectors(
        self,
        sector_type: SectorType,
    ) -> List[str]:
        """
        列出可用的板块

        Args:
            sector_type: 板块类型

        Returns:
            板块名称列表
        """
        type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
        dir_path = os.path.join(self.data_cache_dir, "sector_history", type_dir)

        if not os.path.exists(dir_path):
            return []

        sectors = []
        for filename in os.listdir(dir_path):
            if filename.endswith(".json"):
                sectors.append(filename[:-5])  # 移除 .json 后缀

        return sorted(sectors)

    def calculate_metrics(
        self,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        计算历史指标

        Args:
            records: 历史记录列表

        Returns:
            指标字典
        """
        if not records:
            return self._empty_metrics()

        # 提取收盘价和涨跌幅
        closes = []
        change_pcts = []
        for record in records:
            close = record.get("收盘", record.get("close", None))
            change_pct = record.get("涨跌幅", record.get("change_pct", None))

            if close is not None:
                try:
                    closes.append(float(close))
                except (ValueError, TypeError):
                    pass

            if change_pct is not None:
                try:
                    change_pcts.append(float(change_pct))
                except (ValueError, TypeError):
                    pass

        if not closes and not change_pcts:
            return self._empty_metrics()

        metrics = {}

        # 计算 1/3/5 日涨幅
        metrics["return_1d"] = self._calculate_return(closes, 1)
        metrics["return_3d"] = self._calculate_return(closes, 3)
        metrics["return_5d"] = self._calculate_return(closes, 5)

        # 计算 5 日最大回撤
        metrics["max_drawdown_5d"] = self._calculate_max_drawdown(closes, 5)

        # 计算连续上涨天数
        metrics["consecutive_up_days"] = self._calculate_consecutive_up(change_pcts)

        # 计算平均涨跌幅
        if change_pcts:
            metrics["avg_change_pct"] = round(sum(change_pcts) / len(change_pcts), 2)
        else:
            metrics["avg_change_pct"] = 0.0

        # 计算波动率
        metrics["volatility"] = self._calculate_volatility(change_pcts)

        # 数据点数量
        metrics["data_points"] = len(records)

        return metrics

    def _calculate_return(
        self,
        closes: List[float],
        days: int,
    ) -> Optional[float]:
        """
        计算 N 日涨幅

        Args:
            closes: 收盘价列表（从旧到新）
            days: 天数

        Returns:
            涨幅百分比，数据不足返回 None
        """
        if len(closes) < days + 1:
            return None

        # 从后往前取
        current = closes[-1]
        previous = closes[-(days + 1)]

        if previous == 0:
            return None

        return round((current - previous) / previous * 100, 2)

    def _calculate_max_drawdown(
        self,
        closes: List[float],
        window: int,
    ) -> Optional[float]:
        """
        计算 N 日最大回撤

        Args:
            closes: 收盘价列表（从旧到新）
            window: 窗口大小

        Returns:
            最大回撤百分比，数据不足返回 None
        """
        if len(closes) < window:
            return None

        max_drawdown = 0.0

        # 滑动窗口计算
        for i in range(len(closes) - window + 1):
            window_data = closes[i:i + window]
            peak = max(window_data)
            trough = min(window_data)

            if peak > 0:
                drawdown = (peak - trough) / peak * 100
                max_drawdown = max(max_drawdown, drawdown)

        return round(max_drawdown, 2)

    def _calculate_consecutive_up(
        self,
        change_pcts: List[float],
    ) -> int:
        """
        计算连续上涨天数

        Args:
            change_pcts: 涨跌幅列表（从旧到新）

        Returns:
            连续上涨天数
        """
        consecutive = 0

        # 从后往前计算
        for pct in reversed(change_pcts):
            if pct > 0:
                consecutive += 1
            else:
                break

        return consecutive

    def _calculate_volatility(
        self,
        change_pcts: List[float],
    ) -> float:
        """
        计算波动率（标准差）

        Args:
            change_pcts: 涨跌幅列表

        Returns:
            波动率
        """
        if len(change_pcts) < 2:
            return 0.0

        mean = sum(change_pcts) / len(change_pcts)
        variance = sum((x - mean) ** 2 for x in change_pcts) / len(change_pcts)

        return round(variance ** 0.5, 2)

    def _empty_metrics(self) -> Dict[str, Any]:
        """返回空指标"""
        return {
            "return_1d": None,
            "return_3d": None,
            "return_5d": None,
            "max_drawdown_5d": None,
            "consecutive_up_days": 0,
            "avg_change_pct": 0.0,
            "volatility": 0.0,
            "data_points": 0,
        }

    def analyze_sector(
        self,
        sector_type: SectorType,
        sector_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        分析单个板块

        Args:
            sector_type: 板块类型
            sector_name: 板块名称

        Returns:
            分析结果字典
        """
        history = self.load_sector_history(sector_type, sector_name)
        if history is None:
            return None

        metrics = self.calculate_metrics(history.get("records", []))

        return {
            "sector_name": sector_name,
            "sector_type": sector_type.value,
            "source": history.get("source", "unknown"),
            "start_date": history.get("start_date", ""),
            "end_date": history.get("end_date", ""),
            "metrics": metrics,
            "price_change_available": history.get("price_change_available", False),
        }

    def analyze_all_sectors(
        self,
        sector_type: SectorType,
    ) -> List[Dict[str, Any]]:
        """
        分析所有板块

        Args:
            sector_type: 板块类型

        Returns:
            分析结果列表
        """
        sectors = self.list_available_sectors(sector_type)
        results = []

        for sector_name in sectors:
            result = self.analyze_sector(sector_type, sector_name)
            if result is not None:
                results.append(result)

        return results

    def rank_sectors(
        self,
        results: List[Dict[str, Any]],
        sort_by: str = "return_5d",
        ascending: bool = False,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        排序板块

        Args:
            results: 分析结果列表
            sort_by: 排序字段
            ascending: 是否升序
            top_n: 返回数量

        Returns:
            排序后的结果列表
        """
        # 过滤掉指标为 None 的结果
        valid_results = [
            r for r in results
            if r["metrics"].get(sort_by) is not None
        ]

        # 排序
        valid_results.sort(
            key=lambda x: x["metrics"].get(sort_by, 0),
            reverse=not ascending
        )

        return valid_results[:top_n]

    def filter_candidates(
        self,
        results: List[Dict[str, Any]],
        min_return_5d: float = 0.0,
        max_drawdown_5d: float = 20.0,
        min_consecutive_up: int = 0,
        min_data_points: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        筛选候选板块

        Args:
            results: 分析结果列表
            min_return_5d: 最小 5 日涨幅
            max_drawdown_5d: 最大 5 日回撤
            min_consecutive_up: 最小连续上涨天数
            min_data_points: 最小数据点数量

        Returns:
            筛选后的结果列表
        """
        candidates = []

        for result in results:
            metrics = result.get("metrics", {})

            # 检查数据点数量
            if metrics.get("data_points", 0) < min_data_points:
                continue

            # 检查 5 日涨幅
            return_5d = metrics.get("return_5d")
            if return_5d is not None and return_5d < min_return_5d:
                continue

            # 检查 5 日最大回撤
            max_drawdown = metrics.get("max_drawdown_5d")
            if max_drawdown is not None and max_drawdown > max_drawdown_5d:
                continue

            # 检查连续上涨天数
            consecutive_up = metrics.get("consecutive_up_days", 0)
            if consecutive_up < min_consecutive_up:
                continue

            candidates.append(result)

        return candidates

    def generate_report(
        self,
        sector_type: SectorType,
        start_date: str,
        end_date: str,
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """
        生成分析报告

        Args:
            sector_type: 板块类型
            start_date: 开始日期
            end_date: 结束日期
            top_n: Top N 数量

        Returns:
            分析报告字典
        """
        # 分析所有板块
        results = self.analyze_all_sectors(sector_type)

        # 排序
        ranked_by_return = self.rank_sectors(results, sort_by="return_5d", top_n=top_n)
        ranked_by_drawdown = self.rank_sectors(results, sort_by="max_drawdown_5d", ascending=True, top_n=top_n)
        ranked_by_consecutive = self.rank_sectors(results, sort_by="consecutive_up_days", top_n=top_n)

        # 筛选候选
        candidates = self.filter_candidates(results)

        return {
            "sector_type": sector_type.value,
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.now().isoformat(),
            "total_sectors": len(results),
            "top_by_return_5d": ranked_by_return,
            "top_by_max_drawdown": ranked_by_drawdown,
            "top_by_consecutive_up": ranked_by_consecutive,
            "candidates": candidates,
            "candidate_count": len(candidates),
        }


def save_analysis_report(
    report: Dict[str, Any],
    output_dir: str,
):
    """
    保存分析报告

    Args:
        report: 分析报告
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "sector_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 生成 Markdown
    md_content = _generate_analysis_md(report)
    md_path = os.path.join(output_dir, "sector_analysis.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)


def _generate_analysis_md(report: Dict[str, Any]) -> str:
    """生成分析报告 Markdown"""
    lines = []

    lines.append("# Sector History Analysis Report")
    lines.append("")
    lines.append(f"- **Sector Type**: {report['sector_type']}")
    lines.append(f"- **Date Range**: {report['start_date']} ~ {report['end_date']}")
    lines.append(f"- **Generated**: {report['generated_at']}")
    lines.append(f"- **Total Sectors**: {report['total_sectors']}")
    lines.append(f"- **Candidates**: {report['candidate_count']}")
    lines.append("")

    # Top by 5-day return
    lines.append("## Top 10 by 5-Day Return")
    lines.append("")
    lines.append("| Rank | Sector | Return 5D | Return 3D | Return 1D | Max Drawdown | Consecutive Up |")
    lines.append("|------|--------|-----------|-----------|-----------|--------------|----------------|")

    for i, sector in enumerate(report["top_by_return_5d"][:10], 1):
        metrics = sector["metrics"]
        lines.append(
            f"| {i} | {sector['sector_name']} | "
            f"{metrics.get('return_5d', '-')}% | "
            f"{metrics.get('return_3d', '-')}% | "
            f"{metrics.get('return_1d', '-')}% | "
            f"{metrics.get('max_drawdown_5d', '-')}% | "
            f"{metrics.get('consecutive_up_days', 0)} |"
        )
    lines.append("")

    # Top by max drawdown (lowest)
    lines.append("## Top 10 by Lowest Max Drawdown")
    lines.append("")
    lines.append("| Rank | Sector | Max Drawdown | Return 5D | Consecutive Up |")
    lines.append("|------|--------|--------------|-----------|----------------|")

    for i, sector in enumerate(report["top_by_max_drawdown"][:10], 1):
        metrics = sector["metrics"]
        lines.append(
            f"| {i} | {sector['sector_name']} | "
            f"{metrics.get('max_drawdown_5d', '-')}% | "
            f"{metrics.get('return_5d', '-')}% | "
            f"{metrics.get('consecutive_up_days', 0)} |"
        )
    lines.append("")

    # Top by consecutive up days
    lines.append("## Top 10 by Consecutive Up Days")
    lines.append("")
    lines.append("| Rank | Sector | Consecutive Up | Return 5D | Max Drawdown |")
    lines.append("|------|--------|----------------|-----------|--------------|")

    for i, sector in enumerate(report["top_by_consecutive_up"][:10], 1):
        metrics = sector["metrics"]
        lines.append(
            f"| {i} | {sector['sector_name']} | "
            f"{metrics.get('consecutive_up_days', 0)} | "
            f"{metrics.get('return_5d', '-')}% | "
            f"{metrics.get('max_drawdown_5d', '-')}% |"
        )
    lines.append("")

    # Candidates
    lines.append("## Candidate Sectors")
    lines.append("")
    lines.append(f"Total candidates: {report['candidate_count']}")
    lines.append("")
    if report["candidates"]:
        lines.append("| Sector | Return 5D | Max Drawdown | Consecutive Up | Avg Change |")
        lines.append("|--------|-----------|--------------|----------------|------------|")
        for sector in report["candidates"][:20]:
            metrics = sector["metrics"]
            lines.append(
                f"| {sector['sector_name']} | "
                f"{metrics.get('return_5d', '-')}% | "
                f"{metrics.get('max_drawdown_5d', '-')}% | "
                f"{metrics.get('consecutive_up_days', 0)} | "
                f"{metrics.get('avg_change_pct', 0)}% |"
            )
    lines.append("")

    # Disclaimer
    lines.append("## Disclaimer")
    lines.append("")
    lines.append("**This report is for sector strength analysis and research review only. It does not constitute individual stock recommendations, buy/sell advice, or automated trading instructions.**")
    lines.append("")

    return "\n".join(lines)
