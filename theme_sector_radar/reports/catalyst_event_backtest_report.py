"""
CatalystEventAgent 信号验证报告

生成催化事件回测的 Markdown 报告。
"""

import os
from typing import Any, Dict, List, Optional


def generate_catalyst_event_backtest_report(report_data: Dict[str, Any]) -> str:
    """生成催化事件回测 Markdown 报告"""
    lines = []

    lines.append("# CatalystEventAgent 信号验证报告")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **日期范围**: {report_data.get('start_date', '')} ~ {report_data.get('end_date', '')}")
    lines.append(f"- **样本数**: {report_data.get('total_samples', 0)}")
    lines.append(f"- **cache 覆盖率**: {report_data.get('cache_coverage', 0):.0%}")
    lines.append("")

    # 数据状态
    data_status = report_data.get("data_status_counts", {})
    lines.append("### 数据状态")
    lines.append("")
    for status, count in data_status.items():
        lines.append(f"- {status}: {count}")
    lines.append("")

    # Catalyst Label 表现
    lines.append("## Catalyst Label 表现")
    lines.append("")
    lines.append("| Label | 样本数 | 5日均值 | 5日正收益率 |")
    lines.append("|--------|--------|---------|------------|")
    for label, stats in report_data.get("catalyst_label_performance", {}).items():
        lines.append(
            f"| {label} | "
            f"{stats.get('sample_count', 0)} | "
            f"{_fmt(stats.get('avg_forward_5d'))} | "
            f"{_fmt_rate(stats.get('positive_rate'))} |"
        )
    lines.append("")

    # 事件数量与表现
    lines.append("## 事件数量与表现")
    lines.append("")
    lines.append("| 事件数 | 样本数 | 5日均值 | 5日正收益率 |")
    lines.append("|--------|--------|---------|------------|")
    for bucket, stats in report_data.get("event_count_performance", {}).items():
        lines.append(
            f"| {bucket} | "
            f"{stats.get('sample_count', 0)} | "
            f"{_fmt(stats.get('avg_forward_5d'))} | "
            f"{_fmt_rate(stats.get('positive_rate'))} |"
        )
    lines.append("")

    # 与 ShortTermHeat 叠加
    lines.append("## 与 ShortTermHeat 叠加")
    lines.append("")
    heat = report_data.get("heat_overlap", {})
    if heat:
        lines.append("| 组合 | 样本数 | 5日均值 | 5日正收益率 |")
        lines.append("|------|--------|---------|------------|")
        for group, stats in heat.items():
            lines.append(
                f"| {group} | "
                f"{stats.get('sample_count', 0)} | "
                f"{_fmt(stats.get('avg_forward_5d'))} | "
                f"{_fmt_rate(stats.get('positive_rate'))} |"
            )
    else:
        lines.append("无足够数据")
    lines.append("")

    # 数据限制
    lines.append("## 数据限制")
    lines.append("")
    rec = report_data.get("recommendation", {})
    if rec.get("data_limitations"):
        for lim in rec["data_limitations"]:
            lines.append(f"- {lim}")
    if rec.get("reasons"):
        for reason in rec["reasons"]:
            lines.append(f"- {reason}")
    lines.append("")

    # 结论
    lines.append("## 结论")
    lines.append("")
    if rec.get("recommend_vote_calibration"):
        lines.append("**建议**: Phase 47 可考虑 selective vote calibration")
    else:
        lines.append("**建议**: 保持 report-only，继续观察")
    lines.append("")
    lines.append(f"- **建议模式**: {rec.get('recommended_mode', '')}")
    lines.append(f"- **下一步**: {rec.get('recommended_next_phase', '')}")
    lines.append("")
    if rec.get("risks"):
        lines.append("**风险提示**:")
        for risk in rec["risks"]:
            lines.append(f"- {risk}")
    lines.append("")

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


def save_catalyst_event_backtest_report(output_dir: str, report_data: Dict[str, Any]):
    """保存催化事件回测报告"""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "catalyst_event_backtest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        import json
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    md_report = generate_catalyst_event_backtest_report(report_data)
    md_path = os.path.join(output_dir, "catalyst_event_backtest.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")
