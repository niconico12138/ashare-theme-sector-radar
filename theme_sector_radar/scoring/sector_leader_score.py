"""
板块核心股识别模块

按板块分组，综合 change_pct、amount、stock_short_score、stock_trend_score、
final_score 对候选股进行排名，识别板块 leader / core / follower / laggard。
"""

from __future__ import annotations

from typing import Any
from collections import defaultdict


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_sector_key(stock: dict) -> str:
    """Get the sector grouping key for a stock."""
    boards = stock.get("boards", [])
    if boards:
        return boards[0]
    return stock.get("sector_name", "unknown")


def compute_sector_leader_scores(candidates: list[dict]) -> list[dict]:
    """Compute sector leader scores for each candidate.

    Groups candidates by sector (boards[0] or sector_name), ranks within each
    sector, and assigns sector_leader_score, sector_role, leader_tags.

    Args:
        candidates: List of candidate dicts. Each should have at minimum:
            - code, name
            - boards (list) or sector_name
            - change_pct (or pct_change)
            - amount
            - stock_short_score (optional, from compute_stock_short_score)
            - stock_trend_score (optional, from compute_stock_trend_score)
            - final_score (optional)

    Returns:
        Same list with sector_leader_score, sector_role, leader_tags added.
    """
    if not candidates:
        return candidates

    # Group by sector
    sector_groups: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        key = _get_sector_key(c)
        sector_groups[key].append(c)

    # Score within each sector
    for sector_name, stocks in sector_groups.items():
        if len(stocks) == 1:
            # Single stock in sector
            s = stocks[0]
            s["sector_leader_score"] = 50.0
            s["sector_role"] = "unknown"
            s["leader_tags"] = ["single_stock_in_sector"]
            continue

        # Compute composite ranking score for each stock
        scored = []
        for s in stocks:
            change_pct = _safe_float(s.get("change_pct", s.get("pct_change", 0)))
            amount = _safe_float(s.get("amount", 0))
            short_score = _safe_float(s.get("stock_short_score", 50))
            trend_score = _safe_float(s.get("stock_trend_score", 50))
            final_score = _safe_float(s.get("final_score", 0))

            # Weighted composite
            composite = (
                change_pct * 2.0          # short-term momentum
                + short_score * 0.3       # individual short score
                + trend_score * 0.3       # individual trend score
                + final_score * 0.2       # existing final score
            )
            scored.append((s, composite, change_pct, amount, short_score, trend_score))

        # Sort by composite descending
        scored.sort(key=lambda x: x[1], reverse=True)
        n = len(scored)

        # Determine roles based on rank position
        for rank_idx, (s, composite, change_pct, amount, short_score, trend_score) in enumerate(scored):
            # Leader score: percentile-based within sector (0-100)
            if n > 1:
                leader_score = round(100.0 * (n - rank_idx - 1) / (n - 1), 2)
            else:
                leader_score = 50.0

            # Determine role
            role, tags = _determine_role(
                rank_idx, n, change_pct, amount, short_score, trend_score
            )

            s["sector_leader_score"] = leader_score
            s["sector_role"] = role
            s["leader_tags"] = tags

    return candidates


def _determine_role(
    rank_idx: int,
    group_size: int,
    change_pct: float,
    amount: float,
    short_score: float,
    trend_score: float,
) -> tuple[str, list[str]]:
    """Determine the sector role based on rank and metrics."""
    tags: list[str] = []
    pct = rank_idx / group_size if group_size > 1 else 0.0

    if pct < 0.2:
        # Top 20%
        role = "leader"
        tags.append("top_performer_in_sector")
        if short_score > 70:
            tags.append("short_momentum_leader")
        if trend_score > 70:
            tags.append("trend_leader")
    elif pct < 0.5:
        # 20-50%
        role = "mid_cap_core"
        tags.append("mid_tier_core")
        if change_pct > 3:
            tags.append("strong_momentum")
    elif pct < 0.75:
        # 50-75%
        if short_score > 60 or change_pct > 2:
            role = "elastic_leader"
            tags.append("elastic_potential")
        else:
            role = "follower"
            tags.append("following_sector_move")
    else:
        # Bottom 25%
        if change_pct < -1:
            role = "laggard"
            tags.append("underperforming")
        else:
            role = "follower"
            tags.append("weakest_in_sector")

    return role, tags
