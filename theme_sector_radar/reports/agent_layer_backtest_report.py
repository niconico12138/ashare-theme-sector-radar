"""
分层 Agent 回测报告生成

生成分层 Agent 回测的 Markdown 报告。
"""

import json
import os
from typing import Any, Dict, List


def generate_agent_layer_backtest_markdown_report(report_data: Dict[str, Any]) -> str:
    """
    生成分层 Agent 回测 Markdown 报告

    Args:
        report_data: 回测数据字典

    Returns:
        Markdown 报告字符串
    """
    lines = []

    # 标题
    lines.append("# 分层 Agent 回测报告")
    lines.append("")

    # 免责声明
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 输入摘要
    lines.append("## 输入摘要")
    lines.append("")
    input_summary = report_data.get("input_summary", {})
    lines.append(f"- **日期范围**: {report_data.get('start_date', '')} ~ {report_data.get('end_date', '')}")
    lines.append(f"- **板块类型**: {report_data.get('sector_type', '')}")
    lines.append(f"- **研究报告数量**: {input_summary.get('research_report_count', 0)}")
    lines.append(f"- **样本数量**: {input_summary.get('sample_count', 0)}")
    lines.append(f"- **跳过日期数**: {len(input_summary.get('skipped_dates', []))}")
    lines.append("")

    # Layer Performance
    lines.append("## 层级表现")
    lines.append("")
    lines.append("| 层级 | 样本数 | 5日均值 | 5日正收益占比 |")
    lines.append("|------|--------|---------|--------------|")

    layer_perf = report_data.get("layer_performance", {})
    for layer, stats in layer_perf.items():
        avg_5d = stats.get("avg_forward_5d_return")
        pos_5d = stats.get("positive_rate_5d")
        lines.append(
            f"| {layer} | {stats.get('sample_count', 0)} | "
            f"{avg_5d:.2f}% | {pos_5d:.1%} |"
            if avg_5d is not None else f"| {layer} | {stats.get('sample_count', 0)} | N/A | N/A |"
        )
    lines.append("")

    # Agent Performance
    lines.append("## Agent 表现")
    lines.append("")
    lines.append("| Agent | 样本数 | 5日均值 | 5日正收益占比 |")
    lines.append("|-------|--------|---------|--------------|")

    agent_perf = report_data.get("agent_performance", {})
    for agent, stats in sorted(agent_perf.items(), key=lambda x: x[1].get("sample_count", 0), reverse=True):
        avg_5d = stats.get("avg_forward_5d_return")
        pos_5d = stats.get("positive_rate_5d")
        lines.append(
            f"| {agent} | {stats.get('sample_count', 0)} | "
            f"{avg_5d:.2f}% | {pos_5d:.1%} |"
            if avg_5d is not None else f"| {agent} | {stats.get('sample_count', 0)} | N/A | N/A |"
        )
    lines.append("")

    # Vote Performance
    lines.append("## 投票表现")
    lines.append("")
    lines.append("| 投票类型 | 样本数 | 5日均值 | 5日正收益占比 |")
    lines.append("|----------|--------|---------|--------------|")

    vote_perf = report_data.get("vote_performance", {})
    for vote_type, stats in vote_perf.items():
        avg_5d = stats.get("avg_forward_5d_return")
        pos_5d = stats.get("positive_rate_5d")
        lines.append(
            f"| {vote_type} | {stats.get('sample_count', 0)} | "
            f"{avg_5d:.2f}% | {pos_5d:.1%} |"
            if avg_5d is not None else f"| {vote_type} | {stats.get('sample_count', 0)} | N/A | N/A |"
        )
    lines.append("")

    # Conflict Performance
    lines.append("## 冲突表现")
    lines.append("")
    lines.append("| 冲突类型 | 样本数 | 5日均值 | 5日正收益占比 |")
    lines.append("|----------|--------|---------|--------------|")

    conflict_perf = report_data.get("conflict_performance", {})
    for conflict_type, stats in conflict_perf.items():
        avg_5d = stats.get("avg_forward_5d_return")
        pos_5d = stats.get("positive_rate_5d")
        lines.append(
            f"| {conflict_type} | {stats.get('sample_count', 0)} | "
            f"{avg_5d:.2f}% | {pos_5d:.1%} |"
            if avg_5d is not None else f"| {conflict_type} | {stats.get('sample_count', 0)} | N/A | N/A |"
        )
    lines.append("")

    # Veto Performance
    lines.append("## Veto 表现")
    lines.append("")
    lines.append("| Veto 状态 | 样本数 | 5日均值 | 5日正收益占比 |")
    lines.append("|-----------|--------|---------|--------------|")

    veto_perf = report_data.get("veto_performance", {})
    for veto_type, stats in veto_perf.items():
        avg_5d = stats.get("avg_forward_5d_return")
        pos_5d = stats.get("positive_rate_5d")
        lines.append(
            f"| {veto_type} | {stats.get('sample_count', 0)} | "
            f"{avg_5d:.2f}% | {pos_5d:.1%} |"
            if avg_5d is not None else f"| {veto_type} | {stats.get('sample_count', 0)} | N/A | N/A |"
        )
    lines.append("")

    # Confidence Calibration
    lines.append("## 置信度校准")
    lines.append("")
    lines.append("| 置信度分桶 | 样本数 | 5日均值 | 5日正收益占比 |")
    lines.append("|------------|--------|---------|--------------|")

    conf_perf = report_data.get("confidence_calibration_performance", {})
    for bucket, stats in conf_perf.items():
        avg_5d = stats.get("avg_forward_5d_return")
        pos_5d = stats.get("positive_rate_5d")
        lines.append(
            f"| {bucket} | {stats.get('sample_count', 0)} | "
            f"{avg_5d:.2f}% | {pos_5d:.1%} |"
            if avg_5d is not None else f"| {bucket} | {stats.get('sample_count', 0)} | N/A | N/A |"
        )
    lines.append("")

    # False Positive by Agent
    lines.append("## 误判样本 (False Positive)")
    lines.append("")
    false_positives = report_data.get("false_positive_by_agent", [])
    if false_positives:
        lines.append("| 信号日期 | 板块 | 标签 | 排序分 | 5日回报 |")
        lines.append("|----------|------|------|--------|---------|")
        for fp in false_positives[:10]:
            lines.append(
                f"| {fp.get('signal_date', '')} | {fp.get('sector_name', '')} | "
                f"{fp.get('consensus_label', '')} | {fp.get('ranking_score', 0):.2f} | "
                f"{fp.get('forward_5d_return', 0):.2f}% |"
            )
    else:
        lines.append("无误判样本")
    lines.append("")

    # Missed Opportunity by Agent
    lines.append("## 漏判样本 (Missed Opportunity)")
    lines.append("")
    missed = report_data.get("missed_opportunity_by_agent", [])
    if missed:
        lines.append("| 信号日期 | 板块 | 标签 | 排序分 | 5日回报 |")
        lines.append("|----------|------|------|--------|---------|")
        for m in missed[:10]:
            lines.append(
                f"| {m.get('signal_date', '')} | {m.get('sector_name', '')} | "
                f"{m.get('consensus_label', '')} | {m.get('ranking_score', 0):.2f} | "
                f"{m.get('forward_5d_return', 0):.2f}% |"
            )
    else:
        lines.append("无漏判样本")
    lines.append("")

    # 结论
    lines.append("## 结论")
    lines.append("")
    lines.append("- 本报告统计结果仅用于研究复盘，不作为操作依据")
    lines.append("- 统计结果反映历史后验表现，不代表未来收益")
    lines.append("- 如样本数不足，结论需要更多数据验证")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)


def save_agent_layer_backtest_report(
    output_dir: str,
    report_data: Dict[str, Any],
):
    """
    保存分层 Agent 回测报告

    Args:
        output_dir: 输出目录
        report_data: 回测数据字典
    """
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "agent_layer_backtest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

    # 保存 Markdown
    md_report = generate_agent_layer_backtest_markdown_report(report_data)
    md_path = os.path.join(output_dir, "agent_layer_backtest.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"Agent layer backtest reports saved: {output_dir}")
