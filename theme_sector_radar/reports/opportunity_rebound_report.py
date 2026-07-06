"""
Opportunity Rebound 归因报告生成

生成归因分析的 Markdown 报告。
"""

import os
from typing import Any, Dict, List, Optional


def generate_opportunity_rebound_report(report_data: Dict[str, Any]) -> str:
    """
    生成归因分析 Markdown 报告

    Args:
        report_data: 归因分析数据

    Returns:
        Markdown 报告字符串
    """
    lines = []

    # 标题
    lines.append("# Opportunity Score and Rebound Label 归因分析报告")
    lines.append("")

    # 免责声明
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    # 总览
    lines.append("## 总览")
    lines.append("")
    input_summary = report_data.get("input_summary", {})
    lines.append(f"- **日期范围**: {report_data.get('start_date', '')} ~ {report_data.get('end_date', '')}")
    lines.append(f"- **板块类型**: {report_data.get('sector_type', '')}")
    lines.append(f"- **样本数量**: {input_summary.get('sample_count', 0)}")
    lines.append(f"- **missed_opportunity 数量**: {report_data.get('missed_opportunity', {}).get('count', 0)}")
    lines.append(f"- **failed_rebound 数量**: {report_data.get('failed_rebound', {}).get('count', 0)}")
    lines.append("")

    # opportunity_score 分桶
    lines.append("## opportunity_score 分桶统计")
    lines.append("")
    buckets = report_data.get("opportunity_buckets", {})
    lines.append("| 分桶 | 样本数 | 5日均收益 | 10日均收益 | 5日正收益率 | 分数范围 |")
    lines.append("|------|--------|----------|-----------|-----------|---------|")
    for name, stats in buckets.items():
        score_range = "-"
        if stats.get("score_min") is not None:
            score_range = f"{stats['score_min']:.2f} ~ {stats['score_max']:.2f}"
        lines.append(
            f"| {name} | "
            f"{stats.get('sample_count', 0)} | "
            f"{_fmt(stats.get('avg_forward_5d_return'))} | "
            f"{_fmt(stats.get('avg_forward_10d_return'))} | "
            f"{_fmt_rate(stats.get('positive_rate_5d'))} | "
            f"{score_range} |"
        )
    lines.append("")

    # missed_opportunity 归因
    missed = report_data.get("missed_opportunity", {})
    lines.append("## missed_opportunity 归因")
    lines.append("")
    lines.append(f"共 {missed.get('count', 0)} 个样本被标记为弱标签但后续 5 日正收益 > 3%。")
    lines.append("")

    # 聚类摘要
    clusters = missed.get("clusters", {})
    if clusters:
        lines.append("### 聚类摘要")
        lines.append("")
        lines.append("| 聚类 | 样本数 | 5日均收益 | 说明 |")
        lines.append("|------|--------|----------|------|")
        cluster_desc = {
            "momentum_repair": "短期动量开始修复，但趋势尚未确认",
            "relative_strength_repair": "相对基准开始转强",
            "oversold_bounce": "前期明显下跌后出现修复",
            "data_quality_gap": "数据不足导致低估",
            "low_signal_noise": "确实难以提前识别",
        }
        for name, stats in clusters.items():
            lines.append(
                f"| {name} | "
                f"{stats.get('count', 0)} | "
                f"{_fmt(stats.get('avg_forward_5d_return'))} | "
                f"{cluster_desc.get(name, '')} |"
            )
        lines.append("")

    # Top missed 样本
    missed_samples = missed.get("samples", [])
    if missed_samples:
        lines.append("### Top missed 样本")
        lines.append("")
        lines.append("| 日期 | 板块 | 标签 | ranking | opportunity | 5日收益 | pre_5d | 聚类 |")
        lines.append("|------|------|------|---------|-------------|---------|--------|------|")
        for s in missed_samples[:10]:
            cluster = _assign_missed_cluster(s)
            lines.append(
                f"| {s.get('signal_date', '')} | "
                f"{s.get('sector_name', '')} | "
                f"{s.get('consensus_label', '')} | "
                f"{s.get('ranking_score', 0):.2f} | "
                f"{s.get('opportunity_score', 0):.2f} | "
                f"{_fmt(s.get('forward_5d_return'))} | "
                f"{_fmt(s.get('pre_5d_return'))} | "
                f"{cluster} |"
            )
        lines.append("")

    # failed_rebound 归因
    failed = report_data.get("failed_rebound", {})
    lines.append("## failed_rebound 归因")
    lines.append("")
    lines.append(f"共 {failed.get('count', 0)} 个 oversold_rebound_candidate 样本后续 5 日为负。")
    lines.append("")

    # 聚类摘要
    failed_clusters = failed.get("clusters", {})
    if failed_clusters:
        lines.append("### 聚类摘要")
        lines.append("")
        lines.append("| 聚类 | 样本数 | 5日均收益 | 说明 |")
        lines.append("|------|--------|----------|------|")
        failed_desc = {
            "no_momentum_repair": "没有真实动量修复",
            "persistent_weakness": "弱势延续",
            "conflict_or_veto": "存在冲突或 veto 风险",
            "market_drag": "市场环境拖累",
            "false_oversold": "只是弱，不是修复",
        }
        for name, stats in failed_clusters.items():
            lines.append(
                f"| {name} | "
                f"{stats.get('count', 0)} | "
                f"{_fmt(stats.get('avg_forward_5d_return'))} | "
                f"{failed_desc.get(name, '')} |"
            )
        lines.append("")

    # Top failed 样本
    failed_samples = failed.get("samples", [])
    if failed_samples:
        lines.append("### Top failed 样本")
        lines.append("")
        lines.append("| 日期 | 板块 | ranking | opportunity | 5日收益 | pre_5d | heat | 聚类 |")
        lines.append("|------|------|---------|-------------|---------|--------|------|------|")
        for s in failed_samples[:10]:
            cluster = _assign_failed_cluster(s)
            lines.append(
                f"| {s.get('signal_date', '')} | "
                f"{s.get('sector_name', '')} | "
                f"{s.get('ranking_score', 0):.2f} | "
                f"{s.get('opportunity_score', 0):.2f} | "
                f"{_fmt(s.get('forward_5d_return'))} | "
                f"{_fmt(s.get('pre_5d_return'))} | "
                f"{s.get('heat_label', '')} | "
                f"{cluster} |"
            )
        lines.append("")

    # opportunity_score 诊断
    diag = report_data.get("high_bucket_diagnosis", {})
    lines.append("## opportunity_score 诊断")
    lines.append("")
    lines.append(f"- **high 桶样本数**: {diag.get('high_bucket_count', 0)}")
    lines.append(f"- **near high (0.50~0.65) 样本数**: {diag.get('near_high_count', 0)}")
    lines.append(f"- **最高 opportunity_score**: {diag.get('max_opportunity_score', 0)}")
    lines.append("")

    dim_avg = diag.get("dimension_averages", {})
    if dim_avg:
        lines.append("### 维度平均分")
        lines.append("")
        lines.append("| 维度 | 平均分 | 权重 |")
        lines.append("|------|--------|------|")
        weights = {"technical": 0.30, "heat": 0.25, "rotation": 0.20, "market_context": 0.15}
        for dim, avg in dim_avg.items():
            lines.append(f"| {dim} | {avg} | {weights.get(dim, '-')} |")
        lines.append("")

    lines.append("### high 桶为空的原因分析")
    lines.append("")
    if diag.get("high_bucket_count", 0) == 0:
        max_score = diag.get("max_opportunity_score", 0)
        if max_score < 0.50:
            lines.append("- 所有维度分数普遍偏低，市场整体偏弱")
            lines.append("- 技术面和热度维度是主要拖累")
        elif max_score < 0.65:
            lines.append("- 部分样本接近 high 桶但未达到 0.65 阈值")
            lines.append("- 可考虑适当降低阈值或增加加分项")
        else:
            lines.append("- 个别样本接近 high 桶，但数量不足以形成统计意义")
    lines.append("")

    # 是否建议改规则
    lines.append("## 是否建议改规则")
    lines.append("")

    # 基于归因结果判断
    missed_count = missed.get("count", 0)
    failed_count = failed.get("count", 0)
    high_count = diag.get("high_bucket_count", 0)

    if missed_count > 5 and any(
        c.get("count", 0) > 2 for c in clusters.values() if isinstance(c, dict)
    ):
        lines.append("### 建议：暂不修改")
        lines.append("")
        lines.append("- missed_opportunity 主要集中在 low_signal_noise 和 weak_or_avoid")
        lines.append("- 这些样本的共同特征是信号确实不足，难以提前识别")
        lines.append("- 强行新增标签可能导致过拟合")
        lines.append("- 建议继续观察 1-2 个月，积累更多样本")
    else:
        lines.append("### 建议：暂不修改")
        lines.append("")
        lines.append("- 样本数量不足以下结论")
        lines.append("- 需要更多日期验证")

    lines.append("")
    lines.append("### 继续观察什么")
    lines.append("")
    lines.append("- momentum_repair 聚类是否稳定出现")
    lines.append("- oversold_rebound_candidate 收紧后是否改善")
    lines.append("- opportunity_score medium 桶表现是否优于 low 桶")
    lines.append("")

    # 数据限制
    lines.append("## 数据限制")
    lines.append("")
    lines.append("- 样本天数不足时不能下结论")
    lines.append("- forward_20d 可能因为未来数据不足为空")
    lines.append("- 本报告不是交易策略收益回测")
    lines.append("")

    # 结尾
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)


def _fmt(value: Optional[float]) -> str:
    """格式化收益率"""
    if value is None:
        return "-"
    return f"{value:.2f}%"


def _fmt_rate(value: Optional[float]) -> str:
    """格式化比率"""
    if value is None:
        return "-"
    return f"{value:.0%}"


def _assign_missed_cluster(sample: Dict[str, Any]) -> str:
    """为 missed sample 分配聚类"""
    pre_5d = sample.get("pre_5d_return")
    rebound = sample.get("rebound_from_recent_low")
    heat = sample.get("heat_label", "")
    data_q = sample.get("data_quality_label", "")
    mkt = sample.get("dimension_market_context", 0)

    if pre_5d is not None and pre_5d < -5 and rebound is not None and rebound > 3:
        return "oversold_bounce"
    elif pre_5d is not None and pre_5d > 0 and heat in ["heat_moderate", "heat_active"]:
        return "momentum_repair"
    elif mkt > 0.5 and pre_5d is not None and pre_5d > -2:
        return "relative_strength_repair"
    elif data_q in ["data_limited", "data_unreliable"]:
        return "data_quality_gap"
    return "low_signal_noise"


def _assign_failed_cluster(sample: Dict[str, Any]) -> str:
    """为 failed sample 分配聚类"""
    veto = sample.get("veto_triggered", False)
    conflict = sample.get("conflict_level", "none")
    pre_5d = sample.get("pre_5d_return")
    heat = sample.get("heat_label", "")
    tech = sample.get("technical_label", "")
    mkt = sample.get("dimension_market_context", 0)

    if veto or conflict != "none":
        return "conflict_or_veto"
    elif pre_5d is not None and pre_5d < -5 and heat in ["heat_weak", "heat_fading"]:
        return "no_momentum_repair"
    elif pre_5d is not None and pre_5d < -3 and tech in ["trend_weak"]:
        return "persistent_weakness"
    elif mkt < 0.3:
        return "market_drag"
    return "false_oversold"


def save_opportunity_rebound_report(output_dir: str, report_data: Dict[str, Any]):
    """
    保存归因分析报告

    Args:
        output_dir: 输出目录
        report_data: 归因分析数据
    """
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "opportunity_rebound_analysis.json")
    with open(json_path, "w", encoding="utf-8") as f:
        import json
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    # 保存 Markdown
    md_report = generate_opportunity_rebound_report(report_data)
    md_path = os.path.join(output_dir, "opportunity_rebound_analysis.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")
