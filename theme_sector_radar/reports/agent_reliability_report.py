"""
Agent 可靠性报告生成

生成 Agent 可靠性仪表盘的 Markdown 报告。
"""

import os
from typing import Any, Dict, List, Optional


def generate_agent_reliability_report(report_data: Dict[str, Any]) -> str:
    """
    生成 Agent 可靠性 Markdown 报告

    Args:
        report_data: agent_reliability.json 数据

    Returns:
        Markdown 报告字符串
    """
    lines = []

    lines.append("# Agent 可靠性仪表盘")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **日期范围**: {report_data.get('start_date', '')} ~ {report_data.get('end_date', '')}")
    lines.append(f"- **样本数量**: {report_data.get('total_samples', 0)}")
    lines.append(f"- **Agent 数量**: {len(report_data.get('agents', {}))}")
    lines.append("")

    # Agent 可靠性排名
    agents = report_data.get("agents", {})
    lines.append("## Agent 可靠性排名")
    lines.append("")
    lines.append("| Agent | Layer | Signal Profile | Decision Impact | 样本数 | 正向票 | 负向票 | 可靠性评分 | 可靠性标签 | 诊断 |")
    lines.append("|-------|-------|----------------|-----------------|--------|--------|--------|------------|------------|------|")

    for agent_id, stats in agents.items():
        dist = stats.get("vote_distribution", {})
        profile = stats.get("signal_profile", "broad_signal")
        decision_impact = stats.get("decision_impact", "participates")
        lines.append(
            f"| {agent_id} | {stats.get('layer', '')} | "
            f"{profile} | "
            f"{decision_impact} | "
            f"{stats.get('sample_count', 0)} | "
            f"{dist.get('positive', 0)} | "
            f"{dist.get('negative', 0)} | "
            f"{stats.get('reliability_score', 0):.2f} | "
            f"{stats.get('reliability_label', '')} | "
            f"{stats.get('diagnosis', '')[:40]} |"
        )
    lines.append("")

    # Signal Profile 说明
    lines.append("## Signal Profile 说明")
    lines.append("")
    lines.append("| Profile | 说明 |")
    lines.append("|---------|------|")
    lines.append("| broad_signal | 高覆盖普通信号，大部分样本都有投票，区分度中等 |")
    lines.append("| sparse_high_precision | 低覆盖高命中信号，少数样本出手但质量很高 |")
    lines.append("| sparse_event_signal | 低覆盖事件驱动信号，需后续验证命中率 |")
    lines.append("| low_information | 低信息 Agent，当前数据不足以产生有效信号 |")
    lines.append("| defensive_filter | 防守过滤 Agent，主要识别风险和数据问题 |")
    lines.append("")

    # Vote 表现
    lines.append("## Vote 表现")
    lines.append("")

    for agent_id, stats in agents.items():
        vote_perf = stats.get("vote_performance", {})
        if not vote_perf:
            continue

        lines.append(f"### {agent_id}")
        lines.append("")
        lines.append("| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |")
        lines.append("|------|--------|---------|---------|---------|------------|")

        for vote in ["positive", "neutral", "negative"]:
            vp = vote_perf.get(vote, {})
            if vp:
                lines.append(
                    f"| {vote} | "
                    f"{vp.get('sample_count', 0)} | "
                    f"{_fmt(vp.get('forward_1d_avg'))} | "
                    f"{_fmt(vp.get('forward_3d_avg'))} | "
                    f"{_fmt(vp.get('forward_5d_avg'))} | "
                    f"{_fmt_rate(vp.get('forward_5d_positive_ratio'))} |"
                )
        lines.append("")

    # Market Regime 分层
    regime_perf = report_data.get("regime_performance", {})
    if regime_perf:
        lines.append("## Market Regime 分层")
        lines.append("")

        for regime, regime_stats in regime_perf.items():
            lines.append(f"### {regime}")
            lines.append("")
            lines.append(f"样本数: {regime_stats.get('sample_count', 0)}")
            lines.append("")

            agent_regime = regime_stats.get("agents", {})
            if agent_regime:
                lines.append("| Agent | 样本数 | 5日均值 | 5日正收益率 |")
                lines.append("|-------|--------|---------|------------|")
                for agent_id, ars in agent_regime.items():
                    lines.append(
                        f"| {agent_id} | "
                        f"{ars.get('sample_count', 0)} | "
                        f"{_fmt(ars.get('forward_5d_avg'))} | "
                        f"{_fmt_rate(ars.get('forward_5d_positive_ratio'))} |"
                    )
                lines.append("")

    # 误判样本
    misids = report_data.get("misidentifications", {})

    if misids.get("positive_false_signal"):
        lines.append("## 误判样本")
        lines.append("")
        lines.append("### Positive False Signal")
        lines.append("")
        lines.append("Agent vote=positive，但 forward_5d 为负。")
        lines.append("")
        lines.append("| 日期 | 板块 | Agent | 5日收益 |")
        lines.append("|------|------|-------|---------|")
        for item in misids["positive_false_signal"][:10]:
            lines.append(
                f"| {item.get('signal_date', '')} | "
                f"{item.get('sector_name', '')} | "
                f"{item.get('agent_id', '')} | "
                f"{item.get('forward_5d_return', 0):.2f}% |"
            )
        lines.append("")

    if misids.get("negative_missed_signal"):
        lines.append("### Negative Missed Signal")
        lines.append("")
        lines.append("Agent vote=negative，但 forward_5d 为正。")
        lines.append("")
        lines.append("| 日期 | 板块 | Agent | 5日收益 |")
        lines.append("|------|------|-------|---------|")
        for item in misids["negative_missed_signal"][:10]:
            lines.append(
                f"| {item.get('signal_date', '')} | "
                f"{item.get('sector_name', '')} | "
                f"{item.get('agent_id', '')} | "
                f"{item.get('forward_5d_return', 0):.2f}% |"
            )
        lines.append("")

    if misids.get("neutral_missed_move"):
        lines.append("### Neutral Missed Move")
        lines.append("")
        lines.append("Agent vote=neutral，但 forward_5d 绝对值较大。")
        lines.append("")
        lines.append("| 日期 | 板块 | Agent | 5日收益 |")
        lines.append("|------|------|-------|---------|")
        for item in misids["neutral_missed_move"][:10]:
            lines.append(
                f"| {item.get('signal_date', '')} | "
                f"{item.get('sector_name', '')} | "
                f"{item.get('agent_id', '')} | "
                f"{item.get('forward_5d_return', 0):.2f}% |"
            )
        lines.append("")

    # 后续优化建议
    lines.append("## 后续优化建议")
    lines.append("")

    high_rel = [aid for aid, s in agents.items() if s.get("reliability_label") == "high_reliability"]
    low_rel = [aid for aid, s in agents.items() if s.get("reliability_label") == "low_reliability"]
    insuff = [aid for aid, s in agents.items() if s.get("reliability_label") == "insufficient_samples"]

    if high_rel:
        lines.append(f"**高可靠性 Agent**: {', '.join(high_rel)}")
        lines.append("- 这些 Agent 的 vote 与后续表现有较好的一致性，可继续保留")
        lines.append("")

    if low_rel:
        lines.append(f"**低可靠性 Agent**: {', '.join(low_rel)}")
        lines.append("- 这些 Agent 的区分度不足，需要关注是否需要调整")
        lines.append("")

    if insuff:
        lines.append(f"**样本不足 Agent**: {', '.join(insuff)}")
        lines.append("- 这些 Agent 需要更多数据验证")
        lines.append("")

    lines.append("**下一步建议**: 基于以上分析，持续跟踪 Agent 可靠性变化，关注 sparse_high_precision Agent 的命中率。")
    lines.append("")

    # 结尾
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)


def _fmt(value: Optional[float]) -> str:
    """格式化数值"""
    if value is None:
        return "-"
    return f"{value:.2f}%"


def _fmt_rate(value: Optional[float]) -> str:
    """格式化比率"""
    if value is None:
        return "-"
    return f"{value:.0%}"


def save_agent_reliability_report(output_dir: str, report_data: Dict[str, Any]):
    """保存 Agent 可靠性报告"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "agent_reliability.json")
    with open(json_path, "w", encoding="utf-8") as f:
        import json
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    # 保存 Markdown
    md_report = generate_agent_reliability_report(report_data)
    md_path = os.path.join(output_dir, "agent_reliability.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")
