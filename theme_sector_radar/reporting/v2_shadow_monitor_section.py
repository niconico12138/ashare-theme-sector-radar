"""
V2 Shadow Monitor 报告小节模块

生成 V2 Shadow Monitor 的 Markdown 小节，用于日报展示。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_v2_shadow_monitor(monitor_path: Path) -> dict | None:
    """加载 V2 Shadow Monitor 数据。"""
    if not monitor_path.exists():
        return None
    try:
        return json.loads(monitor_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_v2_shadow_monitor_markdown(monitor: dict | None) -> str:
    """构建 V2 Shadow Monitor 的 Markdown 小节。

    Args:
        monitor: V2 Shadow Monitor 数据，如果为 None 则显示暂无数据

    Returns:
        Markdown 格式的小节内容
    """
    lines = []
    lines.append("## V2 Shadow Monitor\n")

    if monitor is None:
        lines.append("V2 Shadow Monitor 暂无数据。\n")
        lines.append("如需生成，请运行：\n")
        lines.append("```bash\npython scripts/update_factor_v2_shadow_monitor.py --start 2026-04-01 --end 2026-07-10\n```\n")
        return "\n".join(lines)

    # 状态灯
    status = monitor.get("monitor_status", {})
    status_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status.get("status"), "⚪")
    lines.append(f"**状态灯**: {status_icon} {status.get('status', 'unknown')}")
    lines.append(f"- {status.get('reason', '')}\n")

    # 最新快照
    latest = monitor.get("latest_snapshot", {})
    if latest:
        lines.append("### 最新快照\n")
        lines.append(f"- 日期: {latest.get('date', 'N/A')}")
        lines.append(f"- v2 覆盖率: {latest.get('v2_coverage', 0):.1f}%")
        lines.append(f"- v2 均值: {latest.get('v2_mean', 'N/A')}")
        lines.append(f"- v2 标准差: {latest.get('v2_std', 'N/A')}")
        lines.append(f"- v2 vs final_score 相关性: {latest.get('v2_final_correlation', 'N/A')}")
        lines.append(f"- 当前定位: 独立机会发现 + 分歧复核")
        lines.append("")

    # 历史表现
    hist = monitor.get("historical_performance", {})
    if hist and hist.get("sample_days", 0) > 0:
        lines.append("### 历史表现\n")
        lines.append(f"- 回溯天数: {monitor.get('lookback_days', 'N/A')}")
        lines.append(f"- 有效天数: {hist.get('sample_days', 'N/A')}")
        lines.append(f"- v2 Rank IC 均值: {hist.get('v2_ic_mean', 'N/A')}")
        lines.append(f"- v2 IC Win Rate: {hist.get('v2_ic_win_rate', 'N/A')}%")
        lines.append(f"- v2 Top5 平均收益: {hist.get('v2_top5_return', 'N/A')}%")
        lines.append(f"- v2 Bottom5 平均收益: {hist.get('v2_bottom5_return', 'N/A')}%")
        lines.append(f"- v2 Spread: {hist.get('v2_spread', 'N/A')}%")
        lines.append("")
        lines.append("历史分歧复盘显示 low_final_high_v2 具备独立观察价值；详见 v2_disagreement_history 报告。")
        lines.append("")
    else:
        lines.append("### 历史表现\n")
        lines.append("暂无历史表现数据\n")

    # 分歧样本
    divergence = monitor.get("divergence_samples", [])
    if divergence:
        lines.append("### 分歧样本\n")

        # low_final_high_v2 - V2 潜力观察名单
        low_final_high_v2 = [s for s in divergence if s.get("reason") == "low_final_high_v2"][:5]
        if low_final_high_v2:
            lines.append("**V2 潜力观察名单** (final 低但 v2 高，历史复盘显示具备独立观察价值):")
            for s in low_final_high_v2:
                lines.append(f"- {s['code']} {s['name']}: final={s['final_score']}, v2={s['factor_composite_shadow_score_v2']}")
            lines.append("")

        # high_final_low_v2 - V2 分歧复核名单
        high_final_low_v2 = [s for s in divergence if s.get("reason") == "high_final_low_v2"][:5]
        if high_final_low_v2:
            lines.append("**V2 分歧复核名单** (final 高但 v2 低，仅提示人工复核):")
            for s in high_final_low_v2:
                lines.append(f"- {s['code']} {s['name']}: final={s['final_score']}, v2={s['factor_composite_shadow_score_v2']}")
            lines.append("")

        # high_v2 - V2 高分观察名单
        high_v2 = [s for s in divergence if s.get("reason") == "high_v2_risk_confirmed"][:5]
        if high_v2:
            lines.append("**V2 高分观察名单** (v2 高分候选):")
            for s in high_v2:
                lines.append(f"- {s['code']} {s['name']}: v2={s['factor_composite_shadow_score_v2']}")
            lines.append("")

    # 使用边界
    lines.append("### 使用边界\n")
    lines.append("V2 Shadow Monitor 仅用于独立机会发现与分歧复核，不参与正式排序，不构成买卖建议。")
    lines.append("final_score 与 v2 分歧时，仅表示需要人工复核或纳入观察，不自动纳入或剔除。\n")

    return "\n".join(lines)
