"""
板块综合评分报告生成

生成板块综合评分的 Markdown 报告，支持双评分模式。
"""

from typing import Any, Dict, List



TREND_LEVEL_CN = {
    "strong_watch": "重点观察",
    "watch": "观察",
    "neutral": "中性",
    "cooling": "降温",
    "avoid": "偏弱",
}

BURST_LEVEL_CN = {
    "burst_hot": "短线强势",
    "burst_watch": "短线活跃",
    "burst_neutral": "短线中性",
    "burst_fading": "短线降温",
    "burst_avoid": "短线偏弱",
}


def _trend_level_cn(score: Dict[str, Any]) -> str:
    level = score.get("trend_level") or score.get("selection_level") or ""
    return score.get("trend_level_cn") or score.get("selection_level_cn") or TREND_LEVEL_CN.get(level, level)


def _burst_level_cn(score: Dict[str, Any]) -> str:
    level = score.get("burst_level", "")
    return score.get("burst_level_cn") or BURST_LEVEL_CN.get(level, level)

def generate_sector_score_report(report_data: Dict[str, Any]) -> str:
    """
    生成板块综合评分 Markdown 报告

    Args:
        report_data: 报告数据字典

    Returns:
        Markdown 报告字符串
    """
    lines = []

    # 标题
    lines.append("# 板块综合评分")
    lines.append("")

    # 报告信息
    lines.append(f"**分析日期**: {report_data.get('as_of_date', '')}")
    lines.append(f"**更新时间**: {report_data.get('updated_at', '')}")
    lines.append("")

    # 免责声明
    lines.append("> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。")
    lines.append("")

    # 数据来源说明
    lines.append("## 数据来源")
    lines.append("")
    metadata = report_data.get("metadata", {})
    lines.append(f"- **板块类型**: {metadata.get('sector_type', 'industry')}")
    lines.append(f"- **历史数据范围**: {metadata.get('history_start_date', 'N/A')} ~ {metadata.get('history_end_date', 'N/A')}")
    lines.append(f"- **基准模式**: sector_median (行业样本中位数)")

    # 历史数据来源说明
    history_source = metadata.get("history_source", "none")
    if history_source == "sector_history_cache":
        lines.append(f"- **历史数据来源**: sector_history_cache (完整板块指数历史)")
    elif history_source == "raw_snapshot_fallback":
        lines.append(f"- **历史数据来源**: raw_snapshot_fallback (日报快照历史)")
        lines.append("  - ⚠️ raw_snapshot_fallback 只代表日报快照历史，不等同完整板块指数历史")
        lines.append("  - 数据可能缺少部分字段，评分可靠性降低")
    else:
        lines.append(f"- **历史数据来源**: 无可用历史数据")

    # 历史数据警告
    history_warnings = metadata.get("history_warnings", [])
    if history_warnings:
        lines.append("")
        lines.append("**历史数据警告**:")
        for warning in history_warnings[:5]:  # 最多显示 5 条
            lines.append(f"- {warning}")

    # 市场基准说明
    benchmark_id = metadata.get("benchmark_id")
    benchmark_name = metadata.get("benchmark_name")
    benchmark_status = metadata.get("benchmark_status", "none")

    if benchmark_id and benchmark_name:
        lines.append("")
        lines.append(f"**市场基准**: {benchmark_name} ({benchmark_id})")
        if benchmark_status == "ok":
            lines.append(f"  - 使用真实市场基准计算相对强度")
        elif benchmark_status == "degraded":
            lines.append(f"  - ⚠️ 基准数据部分可用，使用 sector_median fallback")
        else:
            lines.append(f"  - ⚠️ 基准数据不可用，使用 sector_median fallback")
    else:
        lines.append("")
        lines.append("**市场基准**: 无 (使用 sector_median)")

    lines.append("")

    # 双评分说明
    lines.append("## 双评分说明")
    lines.append("")
    lines.append("本报告包含两个并列评分：")
    lines.append("")
    lines.append("1. **趋势持续分 (trend_continuation_score)**: 判断板块是否已经形成持续趋势")
    lines.append("   - 更看重 5/10 日动量、连续性、相对强弱、回撤控制、波动稳定")
    lines.append("   - 适合判断趋势是否持续")
    lines.append("")
    lines.append("2. **短线爆发分 (short_term_burst_score)**: 判断板块是否正在短线爆发")
    lines.append("   - 更看重当日雷达、1日涨幅、资金流、热度变化")
    lines.append("   - 适合捕捉短线机会")
    lines.append("")
    lines.append("**Profile 解读**:")
    lines.append("- **trend_and_burst_aligned**: 趋势和短线都强，双重确认")
    lines.append("- **trend_only**: 趋势强但短线不热，中长期趋势观察价值较高")
    lines.append("- **burst_without_trend_confirmation**: 短线强但趋势未确认，需谨慎")
    lines.append("- **weak_or_cooling**: 趋势和短线都弱，正向观察强度有限")
    lines.append("")

    # 趋势权重方案说明
    trend_weight_profile = metadata.get("trend_weight_profile", "baseline")
    lines.append("## 趋势权重方案")
    lines.append("")
    if trend_weight_profile == "trend_confirmation":
        lines.append("**当前使用的权重方案**: trend_confirmation (趋势确认型)")
        lines.append("")
        lines.append("| 组件 | 权重 | 说明 |")
        lines.append("|------|------|------|")
        lines.append("| radar_score_component | 15 分 | 日报雷达分 |")
        lines.append("| momentum_component | 25 分 | 动量 |")
        lines.append("| relative_strength_component | 20 分 | 相对强度 |")
        lines.append("| persistence_component | 20 分 | 持续性 |")
        lines.append("| drawdown_component | 8 分 | 回撤 |")
        lines.append("| volatility_component | 4 分 | 波动率 |")
        lines.append("| data_quality_component | 8 分 | 数据质量 |")
        lines.append("| risk_penalty | 0-20 分 | 风险扣分 |")
        lines.append("")
        lines.append("**趋势确认型权重特点**: 更重视动量、相对强度和持续性，降低雷达分和数据质量权重，适合判断趋势是否真正形成。")
    else:
        lines.append("**当前使用的权重方案**: baseline (默认)")
        lines.append("")
        lines.append("| 组件 | 权重 | 说明 |")
        lines.append("|------|------|------|")
        lines.append("| radar_score_component | 25 分 | 日报雷达分 |")
        lines.append("| momentum_component | 20 分 | 动量 |")
        lines.append("| relative_strength_component | 15 分 | 相对强度 |")
        lines.append("| persistence_component | 15 分 | 持续性 |")
        lines.append("| drawdown_component | 10 分 | 回撤 |")
        lines.append("| volatility_component | 5 分 | 波动率 |")
        lines.append("| data_quality_component | 10 分 | 数据质量 |")
        lines.append("| risk_penalty | 0-20 分 | 风险扣分 |")
        lines.append("")
        lines.append("**默认权重特点**: 均衡考虑各维度，日报雷达分权重较高。")
    lines.append("")

    # 趋势窗口说明
    trend_window = metadata.get("trend_window", 10)
    trend_window_desc = metadata.get("trend_window_description", f"{trend_window} 个交易日窗口")
    lines.append("## 趋势窗口")
    lines.append("")
    lines.append(f"**趋势窗口**: {trend_window_desc}")
    lines.append("")
    lines.append(f"趋势持续评分使用最近 {trend_window} 个有效交易日计算动量、持续性、回撤等指标。")
    lines.append("")
    lines.append("**注意**: 如果历史数据不足窗口大小，趋势分可靠性会下降。")
    lines.append("")

    # 短线爆发评分权重
    lines.append("## 短线爆发评分权重")
    lines.append("")
    lines.append("| 组件 | 权重 | 说明 |")
    lines.append("|------|------|------|")
    lines.append("| radar_today_component | 30 分 | 当日雷达分 |")
    lines.append("| one_day_change_component | 20 分 | 单日涨幅 |")
    lines.append("| three_day_momentum_component | 15 分 | 3日动量 |")
    lines.append("| volume_or_heat_component | 10 分 | 成交额或热度 |")
    lines.append("| rank_jump_component | 10 分 | 排名跳升 |")
    lines.append("| data_quality_component | 10 分 | 数据质量 |")
    lines.append("| burst_risk_penalty | 0-20 分 | 风险扣分 |")
    lines.append("")

    # 等级规则
    lines.append("## 等级规则")
    lines.append("")
    lines.append("### 趋势持续等级")
    lines.append("")
    lines.append("| 等级 | 分数范围 | 说明 |")
    lines.append("|------|----------|------|")
    lines.append("| 重点观察 | strong_watch | >= 80 | 趋势强劲，可列入重点观察样本 |")
    lines.append("| 观察 | watch | >= 65 | 趋势良好，可继续观察 |")
    lines.append("| 中性 | neutral | >= 50 | 表现中性，可作为备选观察 |")
    lines.append("| 降温 | cooling | >= 35 | 板块降温，谨慎观察 |")
    lines.append("| 偏弱 | avoid | < 35 | 板块弱势，正向观察强度有限 |")
    lines.append("")
    lines.append("### 短线爆发等级")
    lines.append("")
    lines.append("| 等级 | 分数范围 | 说明 |")
    lines.append("|------|----------|------|")
    lines.append("| 短线强势 | burst_hot | >= 80 | 短线爆发强劲 |")
    lines.append("| 短线活跃 | burst_watch | >= 65 | 短线表现活跃 |")
    lines.append("| 短线中性 | burst_neutral | >= 50 | 短线表现中性 |")
    lines.append("| 短线降温 | burst_fading | >= 35 | 短线动能减弱 |")
    lines.append("| 短线偏弱 | burst_avoid | < 35 | 短线表现偏弱 |")
    lines.append("")

    # Top N 趋势持续评分表
    scores = report_data.get("scores", [])
    lines.append(f"## 趋势持续 Top {len(scores)}")
    lines.append("")
    lines.append("| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |")
    lines.append("|------|------|--------|----------|--------|----------|---------|")

    for i, score in enumerate(scores, 1):
        interpretation = score.get("score_interpretation", {})
        profile = interpretation.get("profile", "N/A")
        lines.append(
            f"| {i} | {score.get('sector_name', '')} | "
            f"{score.get('trend_continuation_score', 0):.1f} | "
            f"{_trend_level_cn(score)} | "
            f"{score.get('short_term_burst_score', 0):.1f} | "
            f"{_burst_level_cn(score)} | "
            f"{profile} |"
        )
    lines.append("")

    # 短线爆发 Top N
    # 按短线爆发分排序
    burst_sorted = sorted(scores, key=lambda x: x.get("short_term_burst_score", 0), reverse=True)
    lines.append(f"## 短线爆发 Top {len(burst_sorted)}")
    lines.append("")
    lines.append("| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |")
    lines.append("|------|------|--------|----------|--------|----------|---------|")

    for i, score in enumerate(burst_sorted, 1):
        interpretation = score.get("score_interpretation", {})
        profile = interpretation.get("profile", "N/A")
        lines.append(
            f"| {i} | {score.get('sector_name', '')} | "
            f"{score.get('short_term_burst_score', 0):.1f} | "
            f"{_burst_level_cn(score)} | "
            f"{score.get('trend_continuation_score', 0):.1f} | "
            f"{_trend_level_cn(score)} | "
            f"{profile} |"
        )
    lines.append("")

    # 分歧板块
    lines.append("## 分歧板块")
    lines.append("")

    # 找出 burst 高但 trend 低的板块
    burst_high_trend_low = [
        s for s in scores
        if s.get("short_term_burst_score", 0) >= 65 and s.get("trend_continuation_score", 0) < 50
    ]

    # 找出 trend 高但 burst 低的板块
    trend_high_burst_low = [
        s for s in scores
        if s.get("trend_continuation_score", 0) >= 65 and s.get("short_term_burst_score", 0) < 50
    ]

    if burst_high_trend_low:
        lines.append("### 短线强但趋势未确认")
        lines.append("")
        lines.append("| 板块 | 短线分 | 趋势分 | 说明 |")
        lines.append("|------|--------|--------|------|")
        for s in burst_high_trend_low[:5]:
            interpretation = s.get("score_interpretation", {})
            lines.append(
                f"| {s.get('sector_name', '')} | "
                f"{s.get('short_term_burst_score', 0):.1f} | "
                f"{s.get('trend_continuation_score', 0):.1f} | "
                f"{interpretation.get('summary', '')} |"
            )
        lines.append("")

    if trend_high_burst_low:
        lines.append("### 趋势强但短线不热")
        lines.append("")
        lines.append("| 板块 | 趋势分 | 短线分 | 说明 |")
        lines.append("|------|--------|--------|------|")
        for s in trend_high_burst_low[:5]:
            interpretation = s.get("score_interpretation", {})
            lines.append(
                f"| {s.get('sector_name', '')} | "
                f"{s.get('trend_continuation_score', 0):.1f} | "
                f"{s.get('short_term_burst_score', 0):.1f} | "
                f"{interpretation.get('summary', '')} |"
            )
        lines.append("")

    if not burst_high_trend_low and not trend_high_burst_low:
        lines.append("当前无明显分歧板块。")
        lines.append("")

    # 风险提示
    lines.append("## 风险提示")
    lines.append("")
    lines.append("- 短线爆发不等于趋势确认")
    lines.append("- 仅用于复盘观察，仅用于复盘观察")
    lines.append("- 短线爆发需要观察次日是否持续")
    lines.append("")

    # 评分详情
    lines.append("## 评分详情")
    lines.append("")

    for i, score in enumerate(scores[:5], 1):
        lines.append(f"### {i}. {score.get('sector_name', '')}")
        lines.append("")

        # 趋势持续评分
        lines.append("**趋势持续评分**:")
        lines.append(f"- 趋势分: {score.get('trend_continuation_score', 0):.1f}")
        lines.append(f"- 趋势等级: {_trend_level_cn(score)}")

        trend_breakdown = score.get("trend_breakdown", {})
        if trend_breakdown:
            lines.append("- 趋势 breakdown:")
            for key, value in trend_breakdown.items():
                if key not in ["positive_score", "final_score"]:
                    lines.append(f"  - {key}: {value:.1f}")
        lines.append("")

        # 短线爆发评分
        lines.append("**短线爆发评分**:")
        lines.append(f"- 短线分: {score.get('short_term_burst_score', 0):.1f}")
        lines.append(f"- 短线等级: {_burst_level_cn(score)}")

        burst_breakdown = score.get("burst_breakdown", {})
        if burst_breakdown:
            lines.append("- 短线 breakdown:")
            for key, value in burst_breakdown.items():
                if key not in ["positive_score", "final_score"]:
                    lines.append(f"  - {key}: {value:.1f}")
        lines.append("")

        # 解读
        interpretation = score.get("score_interpretation", {})
        if interpretation:
            lines.append("**解读**:")
            lines.append(f"- Profile: {interpretation.get('profile', 'N/A')}")
            lines.append(f"- Summary: {interpretation.get('summary', 'N/A')}")
            watch_points = interpretation.get("watch_points", [])
            if watch_points:
                lines.append("- Watch points:")
                for wp in watch_points:
                    lines.append(f"  - {wp}")
        lines.append("")

    # 数据质量
    lines.append("## 数据质量")
    lines.append("")
    lines.append(f"- **整体数据质量分**: {report_data.get('data_quality_score', 0):.0f}/100")
    low_quality = [
        s.get("sector_name") for s in scores
        if s.get("data_quality_score", 100) < 60
    ]
    if low_quality:
        lines.append(f"- **数据质量偏低板块**: {', '.join(low_quality)}")
    lines.append("")

    # 声明
    lines.append("## 声明")
    lines.append("")
    lines.append("本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。")
    lines.append("")

    return "\n".join(lines)


def save_sector_score_report(report: str, filepath: str):
    """保存板块综合评分报告"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
