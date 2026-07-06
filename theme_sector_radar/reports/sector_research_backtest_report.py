"""
Agent 组复盘评估报告生成

生成 Agent 组复盘评估的 Markdown 报告。
"""

import os
from typing import Any, Dict, List, Optional


def generate_backtest_markdown_report(report_data: Dict[str, Any]) -> str:
    """
    生成回测 Markdown 报告

    Args:
        report_data: 回测数据字典

    Returns:
        Markdown 报告字符串
    """
    lines = []

    # 标题
    lines.append("# Agent 组复盘评估报告")
    lines.append("")

    # 免责声明
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 回测参数
    lines.append("## 回测参数")
    lines.append("")
    lines.append(f"- **日期范围**: {report_data.get('start_date', '')} ~ {report_data.get('end_date', '')}")
    lines.append(f"- **板块类型**: {report_data.get('sector_type', '')}")

    input_summary = report_data.get("input_summary", {})
    lines.append(f"- **样本数量**: {input_summary.get('sample_count', 0)}")
    lines.append(f"- **研究报告数量**: {input_summary.get('research_report_count', 0)}")

    skipped_dates = input_summary.get("skipped_dates", [])
    if skipped_dates:
        lines.append(f"- **跳过日期数**: {len(skipped_dates)}")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **research_report_count**: {input_summary.get('research_report_count', 0)}")
    lines.append(f"- **sample_count**: {input_summary.get('sample_count', 0)}")

    # 统计可计算 forward returns 的样本数
    label_performance = report_data.get("label_performance", {})
    total_with_5d = sum(
        stats.get("sample_count", 0)
        for stats in label_performance.values()
        if stats.get("avg_forward_5d_return") is not None
    )
    total_with_10d = sum(
        stats.get("sample_count", 0)
        for stats in label_performance.values()
        if stats.get("avg_forward_10d_return") is not None
    )
    lines.append(f"- **可计算 forward_5d_return 样本数**: {total_with_5d}")
    lines.append(f"- **可计算 forward_10d_return 样本数**: {total_with_10d}")
    lines.append("")

    # 按标签表现
    lines.append("## 按标签表现")
    lines.append("")
    lines.append("| 标签 | 样本数 | 1日 | 3日 | 5日 | 10日 | 20日 | 5日正收益占比 | 10日正收益占比 |")
    lines.append("|------|--------|-----|-----|-----|------|------|--------------|--------------|")

    for label, stats in label_performance.items():
        lines.append(
            f"| {label} | "
            f"{stats.get('sample_count', 0)} | "
            f"{_format_return(stats.get('avg_forward_1d_return'))} | "
            f"{_format_return(stats.get('avg_forward_3d_return'))} | "
            f"{_format_return(stats.get('avg_forward_5d_return'))} | "
            f"{_format_return(stats.get('avg_forward_10d_return'))} | "
            f"{_format_return(stats.get('avg_forward_20d_return'))} | "
            f"{_format_rate(stats.get('positive_rate_5d'))} | "
            f"{_format_rate(stats.get('positive_rate_10d'))} |"
        )
    lines.append("")

    # 按 ranking_score 分桶表现
    lines.append("## 按 ranking_score 分桶表现")
    lines.append("")
    _add_bucket_table(lines, report_data.get("ranking_score_bucket_performance", {}))

    # 按 opportunity_score 分桶表现
    lines.append("## 按 opportunity_score 分桶表现")
    lines.append("")
    _add_bucket_table(lines, report_data.get("opportunity_score_bucket_performance", {}))

    # 按 confidence_score 分桶表现
    lines.append("## 按 confidence_score 分桶表现")
    lines.append("")
    _add_bucket_table(lines, report_data.get("confidence_score_bucket_performance", {}))

    # 典型样本
    lines.append("## 典型样本")
    lines.append("")

    sample_analysis = report_data.get("sample_analysis", {})

    # 后续表现较强样本
    best = sample_analysis.get("best_follow_through", [])
    if best:
        lines.append("### 后续表现较强样本")
        lines.append("")
        lines.append("| 日期 | 板块 | 标签 | 5日回报 | 10日回报 |")
        lines.append("|------|------|------|---------|----------|")
        for s in best:
            lines.append(
                f"| {s.get('date', '')} | "
                f"{s.get('sector_name', '')} | "
                f"{s.get('consensus_label', '')} | "
                f"{_format_return(s.get('forward_returns', {}).get('forward_5d_return'))} | "
                f"{_format_return(s.get('forward_returns', {}).get('forward_10d_return'))} |"
            )
        lines.append("")

    # 后续表现较弱样本
    worst = sample_analysis.get("worst_follow_through", [])
    if worst:
        lines.append("### 后续表现较弱样本")
        lines.append("")
        lines.append("| 日期 | 板块 | 标签 | 5日回报 | 10日回报 |")
        lines.append("|------|------|------|---------|----------|")
        for s in worst:
            lines.append(
                f"| {s.get('date', '')} | "
                f"{s.get('sector_name', '')} | "
                f"{s.get('consensus_label', '')} | "
                f"{_format_return(s.get('forward_returns', {}).get('forward_5d_return'))} | "
                f"{_format_return(s.get('forward_returns', {}).get('forward_10d_return'))} |"
            )
        lines.append("")

    # 可能误判样本
    false_positives = sample_analysis.get("false_positive_candidates", [])
    if false_positives:
        lines.append("### 可能误判样本")
        lines.append("")
        lines.append("这些样本被标记为 strong_consensus/trend_confirmed/rotation_candidate，但后续表现为负。")
        lines.append("")
        lines.append("| 日期 | 板块 | 标签 | 排序分 | 5日回报 |")
        lines.append("|------|------|------|--------|---------|")
        for s in false_positives[:5]:
            lines.append(
                f"| {s.get('date', '')} | "
                f"{s.get('sector_name', '')} | "
                f"{s.get('consensus_label', '')} | "
                f"{s.get('ranking_score', 0):.2f} | "
                f"{_format_return(s.get('forward_returns', {}).get('forward_5d_return'))} |"
            )
        lines.append("")

    # 可能漏判样本
    missed = sample_analysis.get("missed_opportunity_candidates", [])
    if missed:
        lines.append("### 可能漏判样本")
        lines.append("")
        lines.append("这些样本被标记为 weak_or_avoid/conflicted，但后续表现为正。")
        lines.append("")
        lines.append("| 日期 | 板块 | 标签 | 排序分 | 5日回报 |")
        lines.append("|------|------|------|--------|---------|")
        for s in missed[:5]:
            lines.append(
                f"| {s.get('date', '')} | "
                f"{s.get('sector_name', '')} | "
                f"{s.get('consensus_label', '')} | "
                f"{s.get('ranking_score', 0):.2f} | "
                f"{_format_return(s.get('forward_returns', {}).get('forward_5d_return'))} |"
            )
        lines.append("")

    # 复盘观察
    lines.append("## 复盘观察")
    lines.append("")

    # 生成复盘观察
    observations = _generate_observations(label_performance, sample_analysis)
    for obs in observations:
        lines.append(f"- {obs}")
    lines.append("")

    # 数据限制
    lines.append("## 数据限制")
    lines.append("")
    lines.append("- 样本天数不足时不能下结论")
    lines.append("- forward_20d 可能因为未来数据不足为空")
    lines.append("- 本报告不是交易策略收益回测")
    lines.append("")

    # 结尾声明
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)


def _format_return(value: Optional[float]) -> str:
    """格式化收益率"""
    if value is None:
        return "-"
    return f"{value:.2f}%"


def _format_rate(value: Optional[float]) -> str:
    """格式化比率"""
    if value is None:
        return "-"
    return f"{value:.1%}"


def _add_bucket_table(lines: List[str], bucket_data: Dict[str, Any]):
    """添加分桶表格"""
    lines.append("| 分桶 | 样本数 | 5日平均 | 10日平均 | 5日正收益占比 | 10日正收益占比 |")
    lines.append("|------|--------|---------|----------|--------------|--------------|")

    for bucket_name, stats in bucket_data.items():
        lines.append(
            f"| {bucket_name} | "
            f"{stats.get('sample_count', 0)} | "
            f"{_format_return(stats.get('avg_forward_5d_return'))} | "
            f"{_format_return(stats.get('avg_forward_10d_return'))} | "
            f"{_format_rate(stats.get('positive_rate_5d'))} | "
            f"{_format_rate(stats.get('positive_rate_10d'))} |"
        )
    lines.append("")


def _generate_observations(
    label_performance: Dict[str, Any],
    sample_analysis: Dict[str, Any],
) -> List[str]:
    """生成复盘观察"""
    observations = []

    # 检查样本是否充足
    total_samples = sum(stats.get("sample_count", 0) for stats in label_performance.values())
    if total_samples < 10:
        observations.append(f"当前样本数量较少 ({total_samples} 个)，复盘结论需要更多日期验证")

    # 检查标签表现
    for label, stats in label_performance.items():
        if stats.get("sample_count", 0) >= 3:
            avg_5d = stats.get("avg_forward_5d_return")
            if avg_5d is not None:
                if avg_5d > 0:
                    observations.append(f"{label} 标签样本后续 5 日平均回报为正 ({avg_5d:.2f}%)")
                else:
                    observations.append(f"{label} 标签样本后续 5 日平均回报为负 ({avg_5d:.2f}%)")

    # 检查误判和漏判
    false_positives = sample_analysis.get("false_positive_candidates", [])
    missed = sample_analysis.get("missed_opportunity_candidates", [])

    if false_positives:
        observations.append(f"存在 {len(false_positives)} 个可能误判样本 (标签偏强但后续为负)")
    if missed:
        observations.append(f"存在 {len(missed)} 个可能漏判样本 (标签偏弱但后续较强)")

    return observations


def save_backtest_report(output_dir: str, report_data: Dict[str, Any]):
    """
    保存回测报告

    Args:
        output_dir: 输出目录
        report_data: 回测数据字典
    """
    os.makedirs(output_dir, exist_ok=True)

    # 生成 Markdown 报告
    md_report = generate_backtest_markdown_report(report_data)
    md_path = os.path.join(output_dir, "research_backtest.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"Markdown report saved: {md_path}")
