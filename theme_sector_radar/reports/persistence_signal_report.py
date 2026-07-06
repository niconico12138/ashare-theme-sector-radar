"""
持续性信号研究报告生成

生成持续性信号研究的 Markdown 报告。
"""

import os
from typing import Any, Dict, List, Optional


def generate_persistence_signal_report(report_data: Dict[str, Any]) -> str:
    """生成持续性信号研究 Markdown 报告"""
    lines = []

    lines.append("# 持续性信号研究报告")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **日期范围**: {report_data.get('start_date', '')} ~ {report_data.get('end_date', '')}")
    lines.append(f"- **样本数**: {report_data.get('total_samples', 0)}")
    lines.append(f"- **覆盖板块数**: {report_data.get('sectors_covered', 0)}")
    lines.append("")

    # Top Watch 连续性
    lines.append("## Top Watch 连续性")
    lines.append("")
    streak = report_data.get("streak_performance", {})
    if streak:
        lines.append("| Streak | 样本数 | 5日均值 | 5日正收益率 |")
        lines.append("|--------|--------|---------|------------|")
        for bucket in ["1_day", "2_days", "3_days", "5_plus_days"]:
            stats = streak.get(bucket, {})
            if stats.get("sample_count", 0) > 0:
                lines.append(
                    f"| {bucket} | "
                    f"{stats.get('sample_count', 0)} | "
                    f"{_fmt(stats.get('avg_forward_5d'))} | "
                    f"{_fmt_rate(stats.get('positive_rate'))} |"
                )
        lines.append("")

    # 标签持续性
    label_perf = report_data.get("label_persistence_performance", {})
    if label_perf:
        lines.append("## 标签持续性")
        lines.append("")
        lines.append("| 标签 | 持续天数 | 样本数 | 5日均值 | 5日正收益率 |")
        lines.append("|------|----------|--------|---------|------------|")
        for key, stats in sorted(label_perf.items(), key=lambda x: -x[1].get("sample_count", 0)):
            parts = key.rsplit("_persistence_", 1)
            if len(parts) == 2:
                lines.append(
                    f"| {parts[0]} | {parts[1]} | "
                    f"{stats.get('sample_count', 0)} | "
                    f"{_fmt(stats.get('avg_forward_5d'))} | "
                    f"{_fmt_rate(stats.get('positive_rate'))} |"
                )
        lines.append("")

    # 标签转换路径
    transitions = report_data.get("label_transition_performance", {})
    if transitions:
        lines.append("## 标签转换路径")
        lines.append("")
        lines.append("| 转换路径 | 样本数 | 5日均值 | 5日正收益率 |")
        lines.append("|----------|--------|---------|------------|")
        for key, stats in sorted(transitions.items(), key=lambda x: -x[1].get("sample_count", 0)):
            lines.append(
                f"| {key} | "
                f"{stats.get('sample_count', 0)} | "
                f"{_fmt(stats.get('avg_forward_5d'))} | "
                f"{_fmt_rate(stats.get('positive_rate'))} |"
            )
        lines.append("")

    # 分数趋势
    trends = report_data.get("trend_performance", {})
    if trends:
        lines.append("## 分数趋势")
        lines.append("")
        for trend_field, trend_stats in trends.items():
            if not trend_stats:
                continue
            field_name = trend_field.replace("_trend_3d", "").replace("_", " ")
            lines.append(f"### {field_name}")
            lines.append("")
            lines.append("| 趋势 | 样本数 | 5日均值 | 5日正收益率 |")
            lines.append("|------|--------|---------|------------|")
            for trend, stats in trend_stats.items():
                lines.append(
                    f"| {trend} | "
                    f"{stats.get('sample_count', 0)} | "
                    f"{_fmt(stats.get('avg_forward_5d'))} | "
                    f"{_fmt_rate(stats.get('positive_rate'))} |"
                )
            lines.append("")

    # Regime 下的持续性
    regime_persist = report_data.get("regime_persistence", {})
    if regime_persist:
        lines.append("## Regime 下的持续性")
        lines.append("")
        lines.append("| Regime | Streak | 样本数 | 5日均值 | 5日正收益率 |")
        lines.append("|--------|--------|--------|---------|------------|")
        for regime, groups in regime_persist.items():
            for streak_bucket, stats in groups.items():
                lines.append(
                    f"| {regime} | {streak_bucket} | "
                    f"{stats.get('sample_count', 0)} | "
                    f"{_fmt(stats.get('avg_forward_5d'))} | "
                    f"{_fmt_rate(stats.get('positive_rate'))} |"
                )
        lines.append("")

    # 与 ShortTermHeat 的叠加
    heat_overlap = report_data.get("heat_overlap", {})
    if heat_overlap:
        lines.append("## 与 ShortTermHeat 的叠加")
        lines.append("")
        lines.append("| 分组 | 样本数 | 5日均值 | 5日正收益率 |")
        lines.append("|------|--------|---------|------------|")
        for group, stats in heat_overlap.items():
            lines.append(
                f"| {group} | "
                f"{stats.get('sample_count', 0)} | "
                f"{_fmt(stats.get('avg_forward_5d'))} | "
                f"{_fmt_rate(stats.get('positive_rate'))} |"
            )
        lines.append("")

    # 是否建议新增 PersistenceStrengthAgent
    rec = report_data.get("recommendation", {})
    lines.append("## 是否建议新增 PersistenceStrengthAgent")
    lines.append("")
    if rec.get("recommend_persistence_agent"):
        lines.append("**建议：新增**")
    else:
        lines.append("**建议：暂不新增**")
    lines.append("")
    lines.append(f"- **理由**: {rec.get('reason', '')}")
    lines.append(f"- **streak 有解释力**: {rec.get('streak_has_value', False)}")
    lines.append(f"- **trend 有解释力**: {rec.get('trend_has_value', False)}")
    lines.append(f"- **下一步**: {rec.get('next_phase', '')}")
    lines.append("")
    if rec.get("risks"):
        lines.append("**风险提示**:")
        for risk in rec.get("risks", []):
            lines.append(f"- {risk}")
        lines.append("")

    # 结尾
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}%"


def _fmt_rate(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.0%}"


def save_persistence_signal_report(output_dir: str, report_data: Dict[str, Any]):
    """保存持续性信号研究报告"""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "persistence_signal_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        import json
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    md_report = generate_persistence_signal_report(report_data)
    md_path = os.path.join(output_dir, "persistence_signal_analysis.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")
