"""
板块综合研判日报生成

生成适合每日盘后使用的研究日报。
"""

import json
import os
from typing import Any, Dict, List, Optional


# 中文标签解释（简洁版）
LABEL_CN = {
    "strong_consensus": "多维共识较强",
    "trend_confirmed": "趋势确认",
    "trend_confirmed_but_strength_limited": "趋势有确认但强度有限",
    "short_term_active_unconfirmed": "短线活跃但趋势未确认",
    "rotation_candidate": "轮动观察候选",
    "defensive_watch": "防御观察",
    "conflicted": "信号分歧",
    "oversold_rebound_candidate": "弱修复观察",
    "low_signal_noise": "低信号噪声",
    "weak_continuation": "偏弱延续",
    "weak_or_avoid": "正向观察强度有限",
    "insufficient_data": "数据不足",
    "early_repair_watch": "早期修复观察",
    "data_limited_neutral": "数据有限中性",
    "defensive_stable_watch": "防御稳定观察",
    "persistence_confirmed": "持续性确认",
    "persistence_building": "持续性增强",
    "persistence_weak": "持续性偏弱",
    "persistence_deteriorating": "持续性转弱",
    "persistence_unknown": "持续性数据不足",
    "catalyst_observed": "观察到外部事件",
    "catalyst_sparse": "事件稀少或置信度低",
    "no_catalyst_observed": "未观察到匹配事件",
    "catalyst_unknown": "事件数据不足",
}

# regime 中文解释
REGIME_CN = {
    "choppy_market": "震荡分化",
    "risk_off": "风险收缩",
    "risk_on": "风险偏活跃",
    "weak_rebound": "弱修复环境",
    "unknown_regime": "市场状态不足",
}

# 标签分组
LABEL_GROUPS = {
    "综合观察候选": ["strong_consensus", "trend_confirmed", "trend_confirmed_but_strength_limited", "rotation_candidate", "defensive_watch"],
    "短线活跃": ["short_term_active_unconfirmed"],
    "修复观察": ["oversold_rebound_candidate", "early_repair_watch"],
    "分歧观察": ["conflicted"],
    "低信号噪声": ["low_signal_noise", "data_limited_neutral"],
    "偏弱延续": ["weak_continuation", "weak_or_avoid", "defensive_stable_watch"],
    "数据不足": ["insufficient_data"],
}


def generate_sector_research_markdown_report(
    report_data: Dict[str, Any],
    multi_window_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    生成板块综合研判日报

    Args:
        report_data: sector_research.json 数据
        multi_window_data: multi_window_consensus.json 数据 (可选)

    Returns:
        Markdown 报告字符串
    """
    lines = []
    research_results = report_data.get("research_results", [])

    # 提取 regime 信息
    regime_data = None
    for item in research_results:
        if item.get("market_regime"):
            regime_data = item["market_regime"]
            break

    # ========== 1. 今日摘要 ==========
    lines.append("# 板块综合研判日报")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。")
    lines.append("")

    lines.append("## 今日摘要")
    lines.append("")
    lines.append(f"- **日期**: {report_data.get('as_of_date', '')}")
    lines.append(f"- **板块类型**: {report_data.get('sector_type', '')}")
    lines.append(f"- **样本数量**: {len(research_results)}")

    if regime_data:
        composite = regime_data.get("regime_composite_label", "unknown_regime")
        lines.append(f"- **市场状态**: {REGIME_CN.get(composite, composite)}")

        # 从 breadth 获取温度和广度
        breadth_regime = regime_data.get("breadth_regime", "unknown")
        temp_regime = regime_data.get("market_temperature_regime", "unknown")
        lines.append(f"- **市场温度**: {temp_regime}")
        lines.append(f"- **广度**: {breadth_regime}")

    # 数据质量摘要
    insufficient_count = sum(1 for r in research_results if r.get("consensus_label") == "insufficient_data")
    veto_count = sum(1 for r in research_results if r.get("veto", {}).get("veto_triggered", False))
    conflict_count = sum(1 for r in research_results if r.get("conflict_level", "none") != "none")

    lines.append(f"- **数据不足板块**: {insufficient_count}")
    lines.append(f"- **Veto 触发**: {veto_count}")
    lines.append(f"- **存在分歧**: {conflict_count}")
    lines.append("")

    # ========== 2. 今日重点观察 ==========
    lines.append("## 今日重点观察")
    lines.append("")

    # 筛选候选：ranking_score 较高、非 insufficient_data、未 veto、risk_control 过低
    candidates = [
        r for r in research_results
        if r.get("consensus_label") != "insufficient_data"
        and not r.get("veto", {}).get("veto_triggered", False)
        and r.get("risk_control_score", 0) >= 0.4
    ]
    candidates.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)

    if candidates:
        lines.append("| 板块 | 标签 | 排序分 | 正向观察强度 | 标签可信度 | 主要观察点 |")
        lines.append("|------|------|--------|-------------|------------|------------|")
        for item in candidates[:5]:
            label = item.get("consensus_label", "")
            label_cn = LABEL_CN.get(label, label)
            watch = item.get("watch_points", ["-"])[0] if item.get("watch_points") else "-"
            lines.append(
                f"| {item.get('sector_name', '')} | "
                f"{label_cn} | "
                f"{item.get('ranking_score', 0):.2f} | "
                f"{item.get('opportunity_score', 0):.2f} | "
                f"{item.get('confidence_score', 0):.2f} | "
                f"{watch[:30]} |"
            )
        lines.append("")
    else:
        lines.append("**今日未出现高一致性观察对象。**")
        lines.append("")

    # ========== 3. 标签分组概览 ==========
    lines.append("## 标签分组概览")
    lines.append("")

    for group_name, group_labels in LABEL_GROUPS.items():
        group_items = [r for r in research_results if r.get("consensus_label") in group_labels]
        if not group_items:
            continue

        lines.append(f"### {group_name}（{len(group_items)} 个）")
        lines.append("")

        # 组内最高 ranking_score
        best = max(group_items, key=lambda x: x.get("ranking_score", 0))
        lines.append(f"组内最高排序分: **{best.get('ranking_score', 0):.2f}** ({best.get('sector_name', '')})")
        lines.append("")

        # 板块列表
        names = [r.get("sector_name", "") for r in group_items[:10]]
        lines.append(f"板块: {', '.join(names)}")
        lines.append("")

    # ========== 4. 市场状态（解释层） ==========
    if regime_data and regime_data.get("regime_composite_label") != "unknown_regime":
        lines.append("## 市场状态（解释层）")
        lines.append("")
        lines.append("> 市场状态仅用于解释和复盘，不参与投票、Veto 或评分决策。")
        lines.append("")

        composite = regime_data.get("regime_composite_label", "unknown_regime")
        lines.append(f"- **综合市场状态**: {REGIME_CN.get(composite, composite)}")
        lines.append(f"- **基准趋势**: {regime_data.get('benchmark_trend', 'unknown')}")
        lines.append(f"- **市场温度**: {regime_data.get('market_temperature_regime', 'unknown')}")
        lines.append(f"- **广度**: {regime_data.get('breadth_regime', 'unknown')}")
        lines.append(f"- **波动率**: {regime_data.get('volatility_regime', 'unknown')}")
        lines.append("")

        # regime 解释
        for item in research_results:
            interp = item.get("regime_interpretation", {})
            if interp and interp.get("summary"):
                lines.append(f"**概述**: {interp['summary']}")
                label_ctx = interp.get("label_context", "")
                if label_ctx:
                    lines.append(f"")
                    lines.append(f"**标签与市场状态交互**: {label_ctx}")
                lines.append("")
                break

    # ========== 5. Agent 分歧与风险摘要 ==========
    lines.append("## Agent 分歧与风险摘要")
    lines.append("")

    # 投票分布
    total_pos = sum(r.get("agent_votes", {}).get("positive_votes", 0) for r in research_results)
    total_neu = sum(r.get("agent_votes", {}).get("neutral_votes", 0) for r in research_results)
    total_neg = sum(r.get("agent_votes", {}).get("negative_votes", 0) for r in research_results)
    total_veto = sum(r.get("agent_votes", {}).get("veto_votes", 0) for r in research_results)

    lines.append(f"- **正向票数**: {total_pos}")
    lines.append(f"- **中性票数**: {total_neu}")
    lines.append(f"- **负向票数**: {total_neg}")
    lines.append(f"- **Veto 票数**: {total_veto}")
    lines.append(f"- **Veto 触发板块数**: {veto_count}")
    lines.append(f"- **存在分歧板块数**: {conflict_count}")
    lines.append("")

    # 高风险板块
    high_risk = [r for r in research_results if r.get("risk_control_score", 1) < 0.3]
    if high_risk:
        lines.append("**高风险板块**:")
        for r in high_risk[:5]:
            lines.append(f"- {r.get('sector_name', '')}: risk_control_score={r.get('risk_control_score', 0):.2f}")
        lines.append("")

    # 数据不足板块
    if insufficient_count > 0:
        insufficient = [r for r in research_results if r.get("consensus_label") == "insufficient_data"]
        lines.append("**数据不足板块**:")
        for r in insufficient[:5]:
            lines.append(f"- {r.get('sector_name', '')}")
        lines.append("")

    # ========== 6. 板块详情 (Top 10) ==========
    lines.append("## 板块详情 (Top 10)")
    lines.append("")
    lines.append("> 仅展示排序分最高的 10 个板块（排除 insufficient_data 和 veto 触发的板块）。")
    lines.append("")

    # 筛选可展示的板块
    display_items = [
        r for r in research_results
        if r.get("consensus_label") != "insufficient_data"
        and not r.get("veto", {}).get("veto_triggered", False)
    ]

    for i, item in enumerate(display_items[:10], 1):
        sector_name = item.get("sector_name", "")
        label = item.get("consensus_label", "")
        label_cn = LABEL_CN.get(label, label)

        lines.append(f"### {i}. {sector_name}")
        lines.append("")
        lines.append(f"- **共识标签**: {label_cn}")
        lines.append(f"- **排序分**: {item.get('ranking_score', 0):.2f}")
        lines.append(f"- **正向观察强度**: {item.get('opportunity_score', 0):.2f}")
        lines.append(f"- **标签可信度**: {item.get('confidence_score', 0):.2f}")
        lines.append(f"- **证据充分度**: {item.get('evidence_score', 0):.2f}")
        lines.append(f"- **风险可控度**: {item.get('risk_control_score', 0):.2f}")

        # market_regime
        mr = item.get("market_regime", {})
        if mr and mr.get("regime_composite_label"):
            regime_label = mr.get("regime_composite_label", "")
            lines.append(f"- **市场状态**: {REGIME_CN.get(regime_label, regime_label)}")

        # persistence_strength opinion
        for op in item.get("agent_opinions", []):
            if op.get("agent_id") == "persistence_strength":
                pers_label = op.get("label", "")
                pers_label_cn = LABEL_CN.get(pers_label, pers_label)
                lines.append(f"- **持续性**: {pers_label_cn} (score: {op.get('score', 0):.2f})")
                # evidence
                for ev in op.get("evidence", [])[:2]:
                    lines.append(f"  - {ev}")
                break

        # catalyst_event opinion
        for op in item.get("agent_opinions", []):
            if op.get("agent_id") == "catalyst_event":
                cat_label = op.get("label", "")
                cat_label_cn = LABEL_CN.get(cat_label, cat_label)
                matched_count = op.get("metadata", {}).get("matched_event_count", 0)
                lines.append(f"- **外部催化事件**: {cat_label_cn} ({matched_count} 条事件，report-only)")
                for ev in op.get("evidence", [])[:3]:
                    lines.append(f"  - {ev}")
                lines.append(f"  - 说明: 外部事件仅作为复盘解释，不参与当前评分和标签决策")
                break

        # 观察要点
        watch_points = item.get("watch_points", [])
        if watch_points:
            lines.append(f"- **主要观察点**: {watch_points[0]}")

        # 风险提示
        veto_reasons = item.get("veto_reasons", [])
        if veto_reasons:
            lines.append(f"- **风险提示**: {'; '.join(veto_reasons[:2])}")

        # Agent 投票
        agent_votes = item.get("agent_votes", {})
        if agent_votes:
            pos = agent_votes.get("positive_votes", 0)
            neu = agent_votes.get("neutral_votes", 0)
            neg = agent_votes.get("negative_votes", 0)
            lines.append(f"- **Agent 投票**: +{pos} / ={neu} / -{neg}")

        # Veto
        veto = item.get("veto", {})
        if veto.get("veto_triggered", False):
            lines.append(f"- **Veto**: 已触发")

        # 分歧说明
        conflict_points = item.get("conflict_points", [])
        if conflict_points:
            lines.append(f"- **分歧说明**: {'; '.join(conflict_points[:2])}")

        # 数据质量
        dq = item.get("views", {}).get("data_quality", {})
        if dq.get("data_quality_label"):
            lines.append(f"- **数据质量**: {dq.get('data_quality_label', '')}")

        lines.append("")

    # ========== 7. 数据与方法说明 ==========
    lines.append("## 数据与方法说明")
    lines.append("")
    lines.append("- 本报告用于板块研究、观察和复盘，不作为操作依据")
    lines.append("- Agent 组采用 L1-L4 分层架构（数据证据层 → 专项分析层 → 冲突一致性层 → 决策层）")
    lines.append("- market_regime 只作解释层，不参与当前标签和排序分决策")
    lines.append("- confidence_score 表示当前标签可信度，不等于 opportunity_score（正向观察强度）")
    lines.append("- ranking_score 是 Agent 层排序辅助（含主观判断惩罚/加分），不是确定性判断")
    lines.append("")
    lines.append("**分数语义说明**:")
    lines.append("| 分数 | 含义 | 范围 |")
    lines.append("|------|------|------|")
    lines.append("| ranking_score | Agent 层综合排序分（含共识标签惩罚） | 0-1 |")
    lines.append("| opportunity_score | 正向观察强度（技术+热度+轮动+市场+叙事加权） | 0-1 |")
    lines.append("| confidence_score | 当前共识标签可信度（≠机会强度） | 0-1 |")
    lines.append("| evidence_score | 证据充分度（数据质量+市场环境） | 0-1 |")
    lines.append("| risk_control_score | 风险可控度（越高越可控） | 0-1 |")
    lines.append("")
    lines.append("**Agent 参与决策说明**:")
    lines.append("- participates: 正常参与投票（technical_trend / short_term_heat / rotation_analysis / risk_control / data_quality / market_context / persistence_strength）")
    lines.append("- report_only: 仅展示不参与投票（catalyst_event — 外部事件仅作复盘解释）")
    lines.append("- excluded: 信息量不足，投票不计入统计（narrative — 纯规则映射，不接外部数据）")
    lines.append("")
    lines.append("- 数据来源: sector_history / sector_scores / multi_window_consensus")
    lines.append("")

    # 结尾声明
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*")

    return "\n".join(lines)


def generate_daily_summary(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成 daily_summary 字段

    Args:
        report_data: sector_research.json 数据

    Returns:
        daily_summary 字典
    """
    research_results = report_data.get("research_results", [])

    # regime
    regime_label = "unknown_regime"
    for item in research_results:
        mr = item.get("market_regime", {})
        if mr and mr.get("regime_composite_label"):
            regime_label = mr["regime_composite_label"]
            break

    # 统计
    total_count = len(research_results)
    insufficient_count = sum(1 for r in research_results if r.get("consensus_label") == "insufficient_data")
    veto_count = sum(1 for r in research_results if r.get("veto", {}).get("veto_triggered", False))
    conflict_count = sum(1 for r in research_results if r.get("conflict_level", "none") != "none")

    # 标签分布
    label_counts = {}
    for r in research_results:
        label = r.get("consensus_label", "")
        label_counts[label] = label_counts.get(label, 0) + 1

    # focus: ranking_score >= 0.4 且非 insufficient_data 且未 veto
    focus_items = [
        r for r in research_results
        if r.get("consensus_label") != "insufficient_data"
        and not r.get("veto", {}).get("veto_triggered", False)
        and r.get("ranking_score", 0) >= 0.4
    ]
    focus_items.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)

    low_signal_count = sum(
        1 for r in research_results
        if r.get("consensus_label") in ["low_signal_noise", "data_limited_neutral"]
    )

    # summary_text
    regime_cn = REGIME_CN.get(regime_label, regime_label)
    if focus_items:
        top_names = [r.get("sector_name", "") for r in focus_items[:3]]
        summary_text = f"今日市场处于{regime_cn}环境，{len(focus_items)} 个板块进入重点观察范围，重点关注: {', '.join(top_names)}。"
    else:
        summary_text = f"今日市场处于{regime_cn}环境，板块信号以低信号和分歧观察为主，未出现高一致性观察对象。"

    return {
        "as_of_date": report_data.get("as_of_date", ""),
        "sector_type": report_data.get("sector_type", ""),
        "market_regime": regime_label,
        "total_count": total_count,
        "focus_count": len(focus_items),
        "conflicted_count": conflict_count,
        "low_signal_count": low_signal_count,
        "insufficient_data_count": insufficient_count,
        "veto_count": veto_count,
        "top_watch_names": [r.get("sector_name", "") for r in focus_items[:5]],
        "summary_text": summary_text,
    }


def save_sector_research_report(
    output_dir: str,
    report_data: Dict[str, Any],
    multi_window_data: Optional[Dict[str, Any]] = None,
):
    """
    保存板块综合研判报告

    Args:
        output_dir: 输出目录
        report_data: sector_research.json 数据
        multi_window_data: multi_window_consensus.json 数据 (可选)
    """
    os.makedirs(output_dir, exist_ok=True)

    # 生成 Markdown 报告
    md_report = generate_sector_research_markdown_report(report_data, multi_window_data)
    md_path = os.path.join(output_dir, "sector_research.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"Markdown report saved: {md_path}")
