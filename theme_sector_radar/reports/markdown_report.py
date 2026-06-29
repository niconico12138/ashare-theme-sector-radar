"""
Markdown 报告生成

生成面向人工复盘的 Markdown 报告。
"""

from typing import Any, Dict, List

from ..models import (
    MarketTemperature,
    ResonanceResult,
    SectorScore,
)


def generate_markdown_report(
    as_of_date: str,
    market_temperature: MarketTemperature,
    industry_top: List[SectorScore],
    concept_top: List[SectorScore],
    overlap: List[ResonanceResult],
    data_quality_score: float = 85.0,
    status: str = "ok",
    cache_info: dict = None,
    fund_flow_coverage: dict = None,
    constituent_coverage: dict = None,
    industry_count: int = 0,
    concept_count: int = 0,
    rotation_summary: dict = None,
    comparison: dict = None,
) -> str:
    """
    生成 Markdown 报告

    Args:
        as_of_date: 分析日期
        market_temperature: 市场温度
        industry_top: 行业 Top N
        concept_top: 概念 Top N
        overlap: 共振列表
        data_quality_score: 数据质量分
        status: 报告状态
        cache_info: 缓存信息
        fund_flow_coverage: 资金流覆盖率
        constituent_coverage: 成分股覆盖率
        industry_count: 行业板块数量
        concept_count: 概念板块数量

    Returns:
        Markdown 报告字符串
    """
    lines = []

    # 标题
    lines.append("# A股行业/概念板块雷达")
    lines.append("")
    lines.append(f"**分析日期**: {as_of_date}")

    # 报告状态
    if status != "ok":
        status_emoji = "⚠️" if status == "degraded" else "❌"
        lines.append(f"\n{status_emoji} **报告状态**: {status}")

    lines.append("")

    # 市场短线温度
    lines.append("## 市场短线温度")
    lines.append("")
    lines.append(f"- **温度**: {market_temperature.label} ({market_temperature.score:.0f}/100)")
    lines.append(f"- **描述**: {market_temperature.description}")
    lines.append(f"- **上涨家数**: {market_temperature.advance_count}")
    lines.append(f"- **下跌家数**: {market_temperature.decline_count}")
    lines.append(f"- **涨停数**: {market_temperature.limit_up_count}")
    lines.append(f"- **跌停数**: {market_temperature.limit_down_count}")
    lines.append(f"- **数据质量**: {data_quality_score:.0f}/100")
    lines.append("")

    # 数据完整性
    lines.append("## 数据完整性")
    lines.append("")

    # 行业板块数量
    industry_min = 20
    industry_status = "✅" if industry_count >= industry_min else "⚠️"
    lines.append(f"- **行业板块数量**: {industry_count}/{industry_min} {industry_status}")

    # 概念板块数量
    concept_min = 20
    concept_status = "✅" if concept_count >= concept_min else "⚠️"
    lines.append(f"- **概念板块数量**: {concept_count}/{concept_min} {concept_status}")

    # 资金流匹配率
    if fund_flow_coverage:
        total_matched = fund_flow_coverage.get("industry_matched", 0) + fund_flow_coverage.get("concept_matched", 0)
        total_unmatched = fund_flow_coverage.get("unmatched", 0)
        total_sectors = total_matched + total_unmatched
        if total_sectors > 0:
            match_rate = (total_matched / total_sectors) * 100
            lines.append(f"- **资金流匹配率**: {match_rate:.0f}%")
        else:
            lines.append("- **资金流匹配率**: N/A")

    # 成分股覆盖率
    if constituent_coverage:
        coverage_rate = constituent_coverage.get("coverage_rate", 0)
        lines.append(f"- **成分股覆盖率**: {coverage_rate:.0f}%")

    # 缓存 fallback
    if cache_info and cache_info.get("is_fallback"):
        source_date = cache_info.get("source_as_of_date", "未知")
        lines.append(f"- **缓存 fallback**: 是 (来源日期: {source_date})")
    else:
        lines.append("- **缓存 fallback**: 否")

    lines.append("")

    # 行业板块 Top N
    lines.append("## 行业板块 Top N")
    lines.append("")
    if industry_top:
        lines.append("| 排名 | 板块 | 分数 | 关注等级 | 阶段 | 风险 | 核心原因 |")
        lines.append("|------|------|------|----------|------|------|----------|")

        for i, score in enumerate(industry_top, 1):
            reasons = "; ".join(score.downgrade_reasons[:2]) if score.downgrade_reasons else "-"
            lines.append(
                f"| {i} | {score.name} | {score.score:.1f} | "
                f"{score.focus_level.value} | - | "
                f"{score.risk_level.value} | {reasons} |"
            )
    else:
        lines.append("*无行业板块数据*")
    lines.append("")

    # 概念板块 Top N
    lines.append("## 概念板块 Top N")
    lines.append("")
    if concept_top:
        lines.append("| 排名 | 板块 | 分数 | 关注等级 | 阶段 | 风险 | 核心原因 |")
        lines.append("|------|------|------|----------|------|------|----------|")

        for i, score in enumerate(concept_top, 1):
            reasons = "; ".join(score.downgrade_reasons[:2]) if score.downgrade_reasons else "-"
            lines.append(
                f"| {i} | {score.name} | {score.score:.1f} | "
                f"{score.focus_level.value} | {score.phase.value} | "
                f"{score.risk_level.value} | {reasons} |"
            )
    else:
        lines.append("*无概念板块数据*")
    lines.append("")

    # 行业 + 概念共振
    lines.append("## 行业 + 概念共振")
    lines.append("")
    if overlap:
        lines.append("| 排名 | 行业 | 概念 | 共振分 | 共同核心数 | 资金方向 | 关注等级 |")
        lines.append("|------|------|------|--------|------------|----------|----------|")

        for i, res in enumerate(overlap[:10], 1):
            lines.append(
                f"| {i} | {res.industry} | {res.concept} | "
                f"{res.resonance_score:.1f} | {res.common_core_count} | "
                f"{res.flow_alignment.value} | {res.focus_level.value} |"
            )
    else:
        lines.append("暂无显著共振板块。")
    lines.append("")

    # 高分板块成分股
    lines.append("## 高分板块成分股")
    lines.append("")
    lines.append("仅列成分股用于验证板块强度，不输出个股推荐。")
    lines.append("")

    top_sectors = industry_top[:3] + concept_top[:3]
    has_constituents = False
    for score in top_sectors:
        if score.constituents:
            has_constituents = True
            lines.append(f"### {score.name}")
            lines.append("")
            lines.append("| 代码 | 名称 | 涨跌幅 | 核心股 |")
            lines.append("|------|------|--------|--------|")
            for c in score.constituents[:5]:
                core_mark = "是" if c.is_core else ""
                lines.append(f"| {c.code} | {c.name} | {c.change_pct:.1f}% | {core_mark} |")
            lines.append("")

    if not has_constituents:
        lines.append("*暂无成分股数据*")
        lines.append("")

    # 板块轮动变化
    if rotation_summary:
        lines.append("## 板块轮动变化")
        lines.append("")

        # 对比日期
        compare_to_date = comparison.get("compare_to_date") if comparison else None
        if compare_to_date:
            lines.append(f"**对比日期**: {compare_to_date}")
            lines.append("")

        # 行业轮动
        industry_rotation = rotation_summary.get("industry", {})
        if industry_rotation:
            lines.append("### 行业板块轮动")
            lines.append("")

            # 新晋 Top N
            new_entries = industry_rotation.get("new_entries", [])
            if new_entries:
                lines.append("**新晋 Top N**:")
                for name in new_entries:
                    lines.append(f"- {name}")
                lines.append("")

            # 快速升温
            rising_fast = industry_rotation.get("rising_fast", [])
            if rising_fast:
                lines.append("**快速升温**:")
                for name in rising_fast:
                    lines.append(f"- {name}")
                lines.append("")

            # 连续强势
            persistent = industry_rotation.get("persistent_strength", [])
            if persistent:
                lines.append("**连续强势**:")
                for name in persistent:
                    lines.append(f"- {name}")
                lines.append("")

            # 掉出 Top N
            dropped = industry_rotation.get("dropped_out", [])
            if dropped:
                lines.append("**掉出 Top N**:")
                for name in dropped:
                    lines.append(f"- {name}")
                lines.append("")

        # 概念轮动
        concept_rotation = rotation_summary.get("concept", {})
        if concept_rotation:
            lines.append("### 概念板块轮动")
            lines.append("")

            # 新晋 Top N
            new_entries = concept_rotation.get("new_entries", [])
            if new_entries:
                lines.append("**新晋 Top N**:")
                for name in new_entries:
                    lines.append(f"- {name}")
                lines.append("")

            # 快速升温
            rising_fast = concept_rotation.get("rising_fast", [])
            if rising_fast:
                lines.append("**快速升温**:")
                for name in rising_fast:
                    lines.append(f"- {name}")
                lines.append("")

            # 连续强势
            persistent = concept_rotation.get("persistent_strength", [])
            if persistent:
                lines.append("**连续强势**:")
                for name in persistent:
                    lines.append(f"- {name}")
                lines.append("")

            # 掉出 Top N
            dropped = concept_rotation.get("dropped_out", [])
            if dropped:
                lines.append("**掉出 Top N**:")
                for name in dropped:
                    lines.append(f"- {name}")
                lines.append("")

        lines.append("*以上轮动变化仅用于复盘观察，不构成推荐。*")
        lines.append("")

    # 风险提示
    lines.append("## 风险提示")
    lines.append("")
    high_risk = [s for s in industry_top + concept_top if s.risk_level.value == "high"]
    if high_risk:
        lines.append("**高风险板块**:")
        for s in high_risk:
            lines.append(f"- {s.name}: {'; '.join(s.risk_flags)}")
    else:
        lines.append("当前无高风险板块。")
    lines.append("")

    # 数据质量
    lines.append("## 数据质量")
    lines.append("")
    lines.append(f"- **整体数据质量分**: {data_quality_score:.0f}/100")
    low_quality = [
        s.name for s in industry_top + concept_top if s.data_quality_score < 60
    ]
    if low_quality:
        lines.append(f"- **数据质量偏低板块**: {', '.join(low_quality)}")
    lines.append("")

    # 声明
    lines.append("## 声明")
    lines.append("")
    lines.append("本报告仅用于板块强弱筛选和研究复盘，不构成个股推荐、买卖建议或自动交易指令。")
    lines.append("")

    return "\n".join(lines)


def save_markdown_report(report: str, filepath: str):
    """保存 Markdown 报告"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
