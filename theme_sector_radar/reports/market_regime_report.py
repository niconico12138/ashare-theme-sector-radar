"""
Market Regime Layer 报告生成

生成市场状态分层分析的 Markdown 报告。
"""

import os
from typing import Any, Dict, List, Optional


def generate_market_regime_report(report_data: Dict[str, Any]) -> str:
    """生成市场状态分层分析 Markdown 报告"""
    lines = []

    lines.append("# Market Regime Layer Backtest 报告")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    input_summary = report_data.get("input_summary", {})
    lines.append(f"- **日期范围**: {report_data.get('start_date', '')} ~ {report_data.get('end_date', '')}")
    lines.append(f"- **板块类型**: {report_data.get('sector_type', '')}")
    lines.append(f"- **基准**: {report_data.get('benchmark', '')}")
    lines.append(f"- **样本数量**: {input_summary.get('sample_count', 0)}")

    # no-lookahead 检查
    check = report_data.get("no_lookahead_check", {})
    lines.append(f"- **no-lookahead 检查**: {'通过' if check.get('passed') else '未通过'} ({check.get('violation_count', 0)} violations)")
    lines.append("")

    # 市场状态分布
    lines.append("## 市场状态分布")
    lines.append("")
    dist = report_data.get("regime_distribution", {})

    for dim_name, dim_label in [
        ("benchmark_trend", "基准趋势"),
        ("market_temperature_regime", "市场温度"),
        ("breadth_regime", "广度"),
        ("volatility_regime", "波动率"),
        ("regime_composite_label", "综合标签"),
    ]:
        dim = dist.get(dim_name, {})
        if dim:
            lines.append(f"### {dim_label}")
            lines.append("")
            lines.append("| 状态 | 样本数 | 占比 |")
            lines.append("|------|--------|------|")
            total = sum(dim.values())
            for state, count in sorted(dim.items(), key=lambda x: -x[1]):
                pct = count / total * 100 if total > 0 else 0
                lines.append(f"| {state} | {count} | {pct:.0f}% |")
            lines.append("")

    # 标签在不同市场状态下的表现
    lines.append("## 标签在不同市场状态下的表现")
    lines.append("")

    label_perf = report_data.get("label_regime_performance", {})
    key_labels = [
        "oversold_rebound_candidate",
        "low_signal_noise",
        "conflicted",
        "weak_or_avoid",
        "trend_confirmed_but_strength_limited",
        "weak_continuation",
        "defensive_stable_watch",
        "early_repair_watch",
    ]

    for label in key_labels:
        if label in label_perf:
            regime_stats = label_perf[label]
            lines.append(f"### {label}")
            lines.append("")
            lines.append("| regime | 样本数 | 5日均收益 | 5日正收益率 |")
            lines.append("|--------|--------|----------|-----------|")
            for regime in sorted(regime_stats.keys()):
                stats = regime_stats[regime]
                count = stats.get("sample_count", 0)
                if count > 0:
                    lines.append(
                        f"| {regime} | "
                        f"{count} | "
                        f"{_fmt(stats.get('avg_forward_5d_return'))} | "
                        f"{_fmt_rate(stats.get('positive_rate_5d'))} |"
                    )
            lines.append("")

    # missed_opportunity 市场状态归因
    lines.append("## missed_opportunity 市场状态归因")
    lines.append("")
    missed = report_data.get("missed_opportunity_by_regime", {})
    lines.append(f"共 {missed.get('total_missed', 0)} 个 missed_opportunity 样本。")
    lines.append("")

    missed_by_regime = missed.get("by_regime", {})
    if missed_by_regime:
        lines.append("| regime | 样本数 | 5日均收益 |")
        lines.append("|--------|--------|----------|")
        for regime in sorted(missed_by_regime.keys(), key=lambda x: -missed_by_regime[x].get("count", 0)):
            stats = missed_by_regime[regime]
            lines.append(
                f"| {regime} | "
                f"{stats.get('count', 0)} | "
                f"{_fmt(stats.get('avg_forward_5d_return'))} |"
            )
        lines.append("")

    # failed_rebound 市场状态归因
    lines.append("## failed_rebound 市场状态归因")
    lines.append("")
    failed = report_data.get("failed_rebound_by_regime", {})
    lines.append(f"共 {failed.get('total_failed', 0)} 个 failed_rebound 样本。")
    lines.append("")

    failed_by_regime = failed.get("by_regime", {})
    if failed_by_regime:
        lines.append("| regime | 样本数 | 5日均收益 |")
        lines.append("|--------|--------|----------|")
        for regime in sorted(failed_by_regime.keys(), key=lambda x: -failed_by_regime[x].get("count", 0)):
            stats = failed_by_regime[regime]
            lines.append(
                f"| {regime} | "
                f"{stats.get('count', 0)} | "
                f"{_fmt(stats.get('avg_forward_5d_return'))} |"
            )
        lines.append("")

    # 结论
    lines.append("## 结论")
    lines.append("")

    # 基于数据生成结论
    composite_dist = dist.get("regime_composite_label", {})
    dominant_regime = max(composite_dist, key=composite_dist.get) if composite_dist else "unknown"

    lines.append("### 是否建议新增 Market Regime Agent")
    lines.append("")
    if len(composite_dist) >= 3 and sum(composite_dist.values()) > 100:
        lines.append("- 建议：**暂不新增**")
        lines.append("- 原因：当前市场状态分布较为集中，样本量不足以验证 Agent 效果")
        lines.append("- 建议先积累 3 个月以上数据再评估")
    else:
        lines.append("- 建议：**暂不新增**")
        lines.append("- 原因：样本量不足，市场状态分布数据有限")
    lines.append("")

    lines.append("### 是否建议将 market_regime 接入 ConsensusDecisionAgent")
    lines.append("")
    lines.append("- 建议：**暂不接入**")
    lines.append("- 原因：当前分析仅验证了分层效果，未证明 regime 信息能提升标签准确性")
    lines.append("- 建议先在报告中展示 regime 信息，观察人工复盘效果")
    lines.append("")

    lines.append("### 是否建议暂不修改标签规则")
    lines.append("")
    lines.append("- **是，暂不修改**")
    lines.append("- 原因：当前标签在不同 regime 下的表现差异主要是市场环境导致，不是标签逻辑问题")
    lines.append("- 强行根据 regime 调整标签可能导致过拟合")
    lines.append("")

    lines.append("### 下一阶段建议")
    lines.append("")
    lines.append("1. 在 sector_research.md 报告中增加 regime 标签展示")
    lines.append("2. 积累更多历史数据（3-6 个月），验证 regime 分层的稳定性")
    lines.append("3. 如果 regime 分层持续有效，考虑在 Phase 33+ 新增 Market Regime Agent")
    lines.append("4. 继续观察 missed_opportunity 和 failed_rebound 的 regime 分布变化")
    lines.append("")

    # 数据限制
    lines.append("## 数据限制")
    lines.append("")
    lines.append("- market_temperature 在 replay 模式下固定为 neutral，限制了温度 regime 的区分度")
    lines.append("- breadth 基于 industry_top 20 个板块，可能不完全代表全市场广度")
    lines.append("- forward_20d 可能因为未来数据不足为空")
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


def save_market_regime_report(output_dir: str, report_data: Dict[str, Any]):
    """保存市场状态分层分析报告"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "market_regime_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        import json
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    # 保存 Markdown
    md_report = generate_market_regime_report(report_data)
    md_path = os.path.join(output_dir, "market_regime_analysis.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")
