"""Markdown reporting for joint decision summaries."""

from __future__ import annotations

from typing import Any


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def render_joint_decision_markdown(summary: dict[str, Any], top_n: int = 10) -> str:
    as_of = summary.get("as_of", "N/A")
    status = summary.get("system_status", {})
    lines: list[str] = [
        f"# Joint Decision {as_of}",
        "",
        "## 1. System Status",
        "",
        f"- Decision mode: {summary.get('decision_mode', 'watch_only')}",
        f"- Run health: {status.get('run_health', 'unknown')}",
        f"- Data quality: {status.get('data_quality', 'unknown')}",
        f"- Allow observation: {status.get('allow_observation', False)}",
        "",
        "## 2. Sector Decision",
        "",
    ]

    sectors = summary.get("sector_decision", {})
    _append_sector_table(lines, "Primary Watch", sectors.get("primary_watch", []), top_n)
    _append_sector_table(lines, "Short Burst Watch", sectors.get("short_burst_watch", []), top_n)
    _append_sector_table(lines, "Review", sectors.get("review", []), top_n)
    _append_sector_table(lines, "Avoid", sectors.get("avoid", []), top_n)

    lines.extend(["", "## 3. Stock Decision", ""])
    stocks = summary.get("stock_decision", {})
    _append_stock_table(lines, "Core Watch", stocks.get("core_watch", []), top_n)
    _append_stock_table(lines, "V2 Opportunity", stocks.get("v2_opportunity", []), top_n)
    _append_stock_table(lines, "Short Burst", stocks.get("short_burst", []), top_n)
    _append_stock_table(lines, "Divergence Review", stocks.get("divergence_review", []), top_n)
    _append_stock_table(lines, "Blocked", stocks.get("blocked", []), top_n)

    risk = summary.get("risk_review", {})
    lines.extend(["", "## 4. Risk Review", ""])
    if risk.get("blockers"):
        lines.append(f"- Blockers: {', '.join(risk['blockers'])}")
    else:
        lines.append("- Blockers: -")
    if risk.get("warnings"):
        lines.append(f"- Warnings: {', '.join(risk['warnings'][:10])}")
    else:
        lines.append("- Warnings: -")

    lines.extend([
        "",
        "---",
        "All outputs are watch_only. No price levels or execution actions are generated.",
    ])
    return "\n".join(lines) + "\n"


def _append_sector_table(lines: list[str], title: str, items: list[dict[str, Any]], top_n: int) -> None:
    lines.append(f"### {title}")
    lines.append("")
    if not items:
        lines.append("No data.")
        lines.append("")
        return
    lines.append("| Rank | Sector | Bucket | Score | Label | Reasons |")
    lines.append("|---:|---|---|---:|---|---|")
    for idx, item in enumerate(items[:top_n], 1):
        reasons = ", ".join(item.get("reason_codes", [])[:3]) or "-"
        lines.append(
            f"| {idx} | {item.get('sector_name', '-')} | {item.get('decision_bucket', '-')} | "
            f"{_fmt(item.get('ranking_score'))} | {item.get('consensus_label', '-')} | {reasons} |"
        )
    lines.append("")


def _append_stock_table(lines: list[str], title: str, items: list[dict[str, Any]], top_n: int) -> None:
    lines.append(f"### {title}")
    lines.append("")
    if not items:
        lines.append("No data.")
        lines.append("")
        return
    lines.append("| Rank | Code | Name | Sector | Type | Final | V2 | Agent | State |")
    lines.append("|---:|---|---|---|---|---:|---:|---|---|")
    for idx, item in enumerate(items[:top_n], 1):
        lines.append(
            f"| {idx} | {item.get('code', '-')} | {item.get('name', '-')} | "
            f"{item.get('sector_name', '-')} | {item.get('opportunity_type', '-')} | "
            f"{_fmt(item.get('final_score'))} | {_fmt(item.get('v2_score'))} | "
            f"{item.get('agent_review_state', 'missing')} | {item.get('action_state', 'watch_only')} |"
        )
    lines.append("")
