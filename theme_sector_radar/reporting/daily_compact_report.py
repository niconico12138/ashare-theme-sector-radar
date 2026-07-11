"""
Daily Compact Report 模块

生成简洁的 Markdown 日报，用于快速浏览。
所有模式均为 watch_only，不含交易建议。
"""

from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_daily_compact_markdown(summary: dict, top_n: int = 5) -> str:
    """构建简洁的 Markdown 日报。

    Args:
        summary: daily decision summary 字典
        top_n: 每个池最多展示的股票数量

    Returns:
        Markdown 格式的简报内容
    """
    lines = []
    as_of = summary.get("as_of", "N/A")

    # 标题
    lines.append(f"# 每日简报 {as_of}\n")

    # 1. 今日状态
    lines.append("## 1. 今日状态\n")
    run_status = summary.get("run_status", {})
    health_status = run_status.get("run_health", "unknown")
    dq_status = run_status.get("data_quality", "unknown")
    allow_observation = run_status.get("allow_observation", False)

    health_icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(health_status, "❓")
    dq_icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(dq_status, "❓")

    lines.append(f"- 运行状态: {health_icon} {health_status}")
    lines.append(f"- 数据质量: {dq_icon} {dq_status}")
    lines.append(f"- 观察模式: watch_only")
    lines.append(f"- 市场环境: {run_status.get('market_regime', 'unknown')}")

    # Selection quality
    selection_quality = summary.get("selection_quality", {})
    pool_quality = selection_quality.get("pool_quality", "unknown")
    eligible_count = selection_quality.get("eligible_count", 0)
    blocked_count = selection_quality.get("blocked_count", 0)

    quality_icon = {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(pool_quality, "❓")
    lines.append(f"- 候选池质量: {quality_icon} {pool_quality}")
    lines.append(f"- 可观察数量: {eligible_count}")
    lines.append(f"- 阻断数量: {blocked_count}")
    lines.append(f"- 今日观察: {'可观察' if allow_observation else '暂停观察'}")
    lines.append("")

    # 2. 核心板块
    lines.append("## 2. 核心板块\n")

    # 行业 Top N
    sector_focus = summary.get("sector_focus", {})
    industries = sector_focus.get("industries", [])
    lines.append(f"### 行业 Top {min(top_n, len(industries) if industries else top_n)}\n")
    if industries:
        lines.append("| 排名 | 行业 | 分数 | 标签 | 置信度 |")
        lines.append("|---|---|---:|---|---:|")
        for s in industries[:top_n]:
            lines.append(f"| {s['rank']} | {s['name']} | {s['score']:.2f} | {s['label']} | {s['confidence']:.2f} |")
    else:
        lines.append("暂无数据")
    lines.append("")

    # 概念 Top N
    concepts = sector_focus.get("concepts", [])
    lines.append(f"### 概念 Top {min(top_n, len(concepts) if concepts else top_n)}\n")
    if concepts:
        lines.append("| 排名 | 概念 | 综合分 | 趋势分 | 短线分 | 标签 |")
        lines.append("|---|---|---:|---:|---:|---|")
        for c in concepts[:top_n]:
            lines.append(f"| {c['rank']} | {c['name']} | {c['score']:.2f} | {c['trend_score']:.2f} | {c['burst_score']:.2f} | {c['label']} |")
    else:
        lines.append("暂无数据")
    lines.append("")

    # 3. 核心个股池
    lines.append("## 3. 核心个股池\n")

    stock_pools = summary.get("stock_pools", {})

    # 精简观察池 eligible_watchlist
    eligible_watchlist = stock_pools.get("eligible_watchlist", [])
    lines.append(f"### 精简观察池 Top {min(top_n, len(eligible_watchlist) if eligible_watchlist else top_n)}\n")
    if eligible_watchlist:
        lines.append("| 排名 | 代码 | 名称 | 板块 | 类型 | selection | adj | Δ | 板块支持 | 调整 | final | v2 | 入池原因 | 状态 |")
        lines.append("|---|---|---|---|---|---:|---:|---:|---|---|---:|---:|---|---|")
        for i, s in enumerate(eligible_watchlist[:top_n], 1):
            # 处理 None 值：None -> "-"
            final_score = s.get("final_score")
            v2_score = s.get("v2_score")
            final_str = f"{final_score:.2f}" if final_score is not None else "-"
            v2_str = f"{v2_score:.2f}" if v2_score is not None else "-"
            sector_str = s.get("sector_name", "") or "-"
            selection_str = f"{s.get('selection_score', 0):.1f}"
            adj_str = f"{s.get('selection_score_adjusted', 0):.1f}" if s.get("selection_score_adjusted") is not None else "-"
            delta = s.get("sector_support_adjustment_delta", 0)
            delta_str = f"{delta:+.1f}" if delta != 0 else "-"
            opp_type = s.get("opportunity_type", "-")
            reason_codes = s.get("reason_codes", [])
            reason_str = ", ".join(reason_codes[:3]) if reason_codes else "-"
            # 板块支持状态
            sector_support = s.get("sector_support", "unknown")
            sector_support_score = s.get("sector_support_score")
            if sector_support_score is not None:
                sector_support_str = f"{sector_support}({sector_support_score:.1f})"
            else:
                sector_support_str = sector_support
            # 调整策略
            policy = s.get("sector_support_adjustment_policy", "display_only")
            policy_short = {"enable_adjustment": "enable", "display_only": "display", "disable_adjustment": "disabled"}.get(policy, policy)
            lines.append(f"| {i} | {s['code']} | {s['name']} | {sector_str} | {opp_type} | {selection_str} | {adj_str} | {delta_str} | {sector_support_str} | {policy_short} | {final_str} | {v2_str} | {reason_str} | {s.get('action_state', 'watch_only')} |")
    else:
        lines.append("暂无数据")
    lines.append("")

    # V2 潜力观察 Top N
    v2_potential = stock_pools.get("v2_potential", [])
    lines.append(f"### V2 潜力观察 Top {min(top_n, len(v2_potential) if v2_potential else top_n)}\n")
    lines.append("说明：final 低但 v2 高，仅用于独立观察。\n")
    lines.append("V2 潜力观察样本仅用于独立观察；历史同类样本在 5d/10d 维度表现较好，但不代表未来结果。\n")
    if v2_potential:
        lines.append("| 排名 | 代码 | 名称 | final | v2 | 类型 | 入池原因 | 状态 |")
        lines.append("|---|---|---|---:|---:|---|---|---|")
        for s in v2_potential[:top_n]:
            final_score = s.get("final_score")
            v2_score = s.get("v2_score")
            final_str = f"{final_score:.2f}" if final_score is not None else "-"
            v2_str = f"{v2_score:.2f}" if v2_score is not None else "-"
            opp_type = s.get("opportunity_type", "-")
            reason_codes = s.get("reason_codes", [])
            reason_str = ", ".join(reason_codes[:3]) if reason_codes else "-"
            lines.append(f"| {s['rank']} | {s['code']} | {s['name']} | {final_str} | {v2_str} | {opp_type} | {reason_str} | {s['action_state']} |")
    else:
        lines.append("暂无数据")
    lines.append("")

    # 4. 复核与降级
    lines.append("## 4. 复核与降级\n")

    # V2 分歧复核
    divergence_review = stock_pools.get("divergence_review", [])
    lines.append("### V2 分歧复核\n")
    lines.append("说明：final 高但 v2 低，仅提示人工复核。\n")
    if divergence_review:
        lines.append("| 排名 | 代码 | 名称 | final | v2 | 状态 |")
        lines.append("|---|---|---|---:|---:|---|")
        for s in divergence_review[:top_n]:
            final_score = s.get("final_score")
            v2_score = s.get("v2_score")
            final_str = f"{final_score:.2f}" if final_score is not None else "-"
            v2_str = f"{v2_score:.2f}" if v2_score is not None else "-"
            lines.append(f"| {s['rank']} | {s['code']} | {s['name']} | {final_str} | {v2_str} | {s['action_state']} |")
    else:
        lines.append("暂无数据")
    lines.append("")

    # 风险与数据质量
    lines.append("### 风险与数据质量\n")
    risk_summary = summary.get("risk_summary", {})
    dq_warnings = risk_summary.get("data_quality_warnings", [])
    health_reasons = risk_summary.get("run_health_reasons", [])

    if dq_warnings:
        lines.append("**数据质量警告:**")
        for w in dq_warnings:
            lines.append(f"- {w}")
        lines.append("")

    if health_reasons:
        lines.append("**运行健康原因:**")
        for r in health_reasons:
            lines.append(f"- {r}")
        lines.append("")

    if not dq_warnings and not health_reasons:
        lines.append("暂无风险警告")
        lines.append("")

    # 固定边界
    lines.append("---")
    lines.append("本简报仅用于研究观察与流程自动化，不构成任何交易建议；所有候选均为 watch_only 状态。")

    return "\n".join(lines)
