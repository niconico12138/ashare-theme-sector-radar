"""
批量生成多日 Agent 组研判报告

批量生成多日 multi_window_consensus 和 sector_research。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


class ResearchRangeGenerator:
    """
    批量生成多日 Agent 组研判报告
    """

    def __init__(
        self,
        history_root: str = "data_cache/sector_history",
        report_root: str = "reports",
    ):
        """
        初始化生成器

        Args:
            history_root: 历史数据根目录
            report_root: 报告根目录
        """
        self.history_root = history_root
        self.report_root = report_root

    def run_range(
        self,
        start_date: str,
        end_date: str,
        sector_type: str = "industry",
        history_start_date: str = "2026-05-20",
        history_end_date: str = "2026-06-30",
        top_n: int = 20,
        score_mode: str = "dual",
        benchmark: str = "hs300",
        trend_weight_profile: str = "trend_confirmation",
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        运行批量生成

        Args:
            start_date: 开始日期
            end_date: 结束日期
            sector_type: 板块类型
            history_start_date: 历史数据开始日期
            history_end_date: 历史数据结束日期
            top_n: Top N 数量
            score_mode: 评分模式
            benchmark: 基准
            trend_weight_profile: 趋势权重方案
            refresh: 是否强制刷新

        Returns:
            批量运行结果
        """
        generated_dates = []
        skipped_dates = []
        failed_dates = []
        reused_dates = []

        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

        while current_date <= end_date_dt:
            signal_date = current_date.strftime("%Y-%m-%d")

            # 检查是否已有 sector_research.json
            research_path = os.path.join(
                self.report_root, "sector_research", signal_date, "sector_research.json"
            )

            if os.path.exists(research_path) and not refresh:
                reused_dates.append(signal_date)
                print(f"  {signal_date}: Reused existing report")
                current_date += timedelta(days=1)
                continue

            # 检查 theme_sector_radar.json 是否存在
            theme_report_path = os.path.join(
                self.report_root, "theme_sector_radar", signal_date, "theme_sector_radar.json"
            )
            if not os.path.exists(theme_report_path):
                failed_dates.append({
                    "date": signal_date,
                    "reason": "missing_theme_sector_radar_json"
                })
                print(f"  {signal_date}: Failed (missing theme_sector_radar.json)")
                current_date += timedelta(days=1)
                continue

            # 检查历史数据是否足够
            history_end = signal_date  # 关键：避免 lookahead bias
            if not self._check_history_sufficient(signal_date, history_start_date, sector_type):
                skipped_dates.append({
                    "date": signal_date,
                    "reason": "insufficient_history_before_signal_date"
                })
                print(f"  {signal_date}: Skipped (insufficient history)")
                current_date += timedelta(days=1)
                continue

            try:
                # 生成 multi_window_consensus
                self._generate_multi_window_consensus(
                    signal_date=signal_date,
                    sector_type=sector_type,
                    history_start_date=history_start_date,
                    history_end_date=history_end,
                    top_n=top_n,
                    score_mode=score_mode,
                    benchmark=benchmark,
                    trend_weight_profile=trend_weight_profile,
                )

                # 生成 sector_research
                self._generate_sector_research(
                    signal_date=signal_date,
                    sector_type=sector_type,
                    history_start_date=history_start_date,
                    history_end_date=history_end,
                    top_n=top_n,
                    score_mode=score_mode,
                    benchmark=benchmark,
                    trend_weight_profile=trend_weight_profile,
                )

                generated_dates.append(signal_date)
                print(f"  {signal_date}: Generated")

            except Exception as e:
                failed_dates.append({
                    "date": signal_date,
                    "reason": str(e)[:200]
                })
                print(f"  {signal_date}: Failed ({str(e)[:100]})")

            current_date += timedelta(days=1)

        # 构建结果
        result = {
            "report_type": "sector_research_range_run",
            "start_date": start_date,
            "end_date": end_date,
            "sector_type": sector_type,
            "generated_dates": generated_dates,
            "skipped_dates": skipped_dates,
            "failed_dates": failed_dates,
            "reused_dates": reused_dates,
            "parameters": {
                "history_start_date": history_start_date,
                "history_end_date": history_end_date,
                "benchmark": benchmark,
                "trend_weight_profile": trend_weight_profile,
                "top_n": top_n,
                "score_mode": score_mode,
                "refresh": refresh,
            },
            "outputs": {
                "sector_consensus_root": os.path.join(self.report_root, "sector_consensus"),
                "sector_research_root": os.path.join(self.report_root, "sector_research"),
            },
            "warnings": [],
        }

        return result

    def _check_history_sufficient(
        self,
        signal_date: str,
        history_start_date: str,
        sector_type: str,
        min_days: int = 10,
    ) -> bool:
        """
        检查历史数据是否足够

        Args:
            signal_date: 信号日期
            history_start_date: 历史数据开始日期
            sector_type: 板块类型
            min_days: 最小天数

        Returns:
            是否足够
        """
        if not history_start_date:
            return True

        # 检查是否有 sector_history 文件
        sector_type_dir = os.path.join(self.history_root, sector_type)
        if not os.path.exists(sector_type_dir):
            return False

        # 检查文件数量
        files = [f for f in os.listdir(sector_type_dir) if f.endswith(".json")]
        if len(files) == 0:
            return False

        # 检查第一个文件的日期范围
        first_file = os.path.join(sector_type_dir, files[0])
        try:
            with open(first_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            records = data.get("records", [])
            if not records:
                return False

            # 检查是否有足够日期在 signal_date 之前
            dates_before_signal = [
                r.get("日期", "") for r in records
                if r.get("日期", "") <= signal_date
            ]

            return len(dates_before_signal) >= min_days

        except Exception:
            return False

    def _generate_multi_window_consensus(
        self,
        signal_date: str,
        sector_type: str,
        history_start_date: str,
        history_end_date: str,
        top_n: int,
        score_mode: str,
        benchmark: str,
        trend_weight_profile: str,
    ):
        """
        生成 multi_window_consensus
        """
        from ..cli import _run_multi_window_consensus
        import argparse

        # 创建参数
        args = argparse.Namespace(
            as_of=signal_date,
            sector_type=sector_type,
            history_start_date=history_start_date,
            history_end_date=history_end_date,
            history_lookback_days=10,
            history_root=self.history_root,
            top_n=top_n,
            score_mode=score_mode,
            trend_weight_profile=trend_weight_profile,
            benchmark=benchmark,
            benchmark_root="data_cache/benchmarks",
            benchmark_refresh=False,
            score_output="reports/sector_scores",
            report_root=self.report_root,
            cache_root="data_cache",
        )

        try:
            _run_multi_window_consensus(args)
        except SystemExit:
            # sys.exit(1) 被调用，表示报告未找到
            raise FileNotFoundError(f"Report not found for {signal_date}")

    def _generate_sector_research(
        self,
        signal_date: str,
        sector_type: str,
        history_start_date: str,
        history_end_date: str,
        top_n: int,
        score_mode: str,
        benchmark: str,
        trend_weight_profile: str,
    ):
        """
        生成 sector_research
        """
        from ..cli import _run_research_agents
        import argparse

        # 创建参数
        args = argparse.Namespace(
            as_of=signal_date,
            sector_type=sector_type,
            history_start_date=history_start_date,
            history_end_date=history_end_date,
            history_lookback_days=10,
            history_root=self.history_root,
            top_n=top_n,
            score_mode=score_mode,
            trend_weight_profile=trend_weight_profile,
            benchmark=benchmark,
            benchmark_root="data_cache/benchmarks",
            benchmark_refresh=False,
            score_output="reports/sector_scores",
            report_root=self.report_root,
            cache_root="data_cache",
        )

        try:
            _run_research_agents(args)
        except SystemExit:
            # sys.exit(1) 被调用，表示报告未找到
            raise FileNotFoundError(f"Report not found for {signal_date}")


def save_range_run_summary(
    output_dir: str,
    summary_data: Dict[str, Any],
):
    """
    保存批量运行摘要

    Args:
        output_dir: 输出目录
        summary_data: 摘要数据
    """
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "range_run_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2, default=str)

    # 生成 Markdown
    md_report = generate_range_run_summary_markdown(summary_data)
    md_path = os.path.join(output_dir, "range_run_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"Range run summary saved: {output_dir}")


def generate_range_run_summary_markdown(summary_data: Dict[str, Any]) -> str:
    """
    生成批量运行摘要 Markdown

    Args:
        summary_data: 摘要数据

    Returns:
        Markdown 字符串
    """
    lines = []

    lines.append("# 批量生成摘要报告")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    lines.append("## 参数")
    lines.append("")
    lines.append(f"- **日期范围**: {summary_data.get('start_date', '')} ~ {summary_data.get('end_date', '')}")
    lines.append(f"- **板块类型**: {summary_data.get('sector_type', '')}")

    params = summary_data.get("parameters", {})
    lines.append(f"- **历史数据开始日期**: {params.get('history_start_date', '')}")
    lines.append(f"- **基准**: {params.get('benchmark', '')}")
    lines.append(f"- **趋势权重方案**: {params.get('trend_weight_profile', '')}")
    lines.append(f"- **Top N**: {params.get('top_n', 20)}")
    lines.append("")

    lines.append("## 运行结果")
    lines.append("")
    lines.append(f"- **生成日期数**: {len(summary_data.get('generated_dates', []))}")
    lines.append(f"- **复用日期数**: {len(summary_data.get('reused_dates', []))}")
    lines.append(f"- **跳过日期数**: {len(summary_data.get('skipped_dates', []))}")
    lines.append(f"- **失败日期数**: {len(summary_data.get('failed_dates', []))}")
    lines.append("")

    # 跳过日期
    skipped = summary_data.get("skipped_dates", [])
    if skipped:
        lines.append("## 跳过日期")
        lines.append("")
        lines.append("| 日期 | 原因 |")
        lines.append("|------|------|")
        for item in skipped:
            lines.append(f"| {item.get('date', '')} | {item.get('reason', '')} |")
        lines.append("")

    # 失败日期
    failed = summary_data.get("failed_dates", [])
    if failed:
        lines.append("## 失败日期")
        lines.append("")
        lines.append("| 日期 | 原因 |")
        lines.append("|------|------|")
        for item in failed:
            lines.append(f"| {item.get('date', '')} | {item.get('reason', '')[:50]}... |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)
