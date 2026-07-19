#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 24 Step 1: export_top30_candidates.py

生成 Top30 个股候选池，供 ai-hedge-fund 24 Agent 分析。
不含原始排名；保留 trend_score、burst_score、relevance_score、quant_score、final_score 作为解释字段。

用法:
  python scripts/export_top30_candidates.py --as-of 2026-07-03
  python scripts/export_top30_candidates.py --as-of 2026-07-03 --stock-limit 30
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# New scoring modules
from theme_sector_radar.scoring.stock_short_score import compute_stock_short_score
from theme_sector_radar.scoring.stock_trend_score import compute_stock_trend_score
from theme_sector_radar.scoring.sector_leader_score import compute_sector_leader_scores
from theme_sector_radar.scoring.trade_risk import compute_trade_risk
from theme_sector_radar.scoring.decision_score import compute_decision_score
from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk
from theme_sector_radar.scoring.shadow_decision_score import compute_shadow_decision_score_v2
from theme_sector_radar.scoring.stock_short_score_v2 import compute_stock_short_score_v2
from theme_sector_radar.scoring.shadow_decision_score_v3 import compute_shadow_decision_score_v3
from theme_sector_radar.scoring.shadow_decision_score_v4 import compute_shadow_decision_score_v4
from theme_sector_radar.scoring.defensive_shadow_score import compute_defensive_shadow_score
from theme_sector_radar.scoring.regime_router_shadow_score_v5 import compute_regime_router_shadow_score_v5
from theme_sector_radar.factors.snapshot import build_factor_snapshot
from theme_sector_radar.scoring.factor_composite_shadow_score import compute_factor_composite_shadow_score
from theme_sector_radar.scoring.factor_composite_shadow_score_v2 import compute_factor_composite_shadow_score_v2
from theme_sector_radar.scoring.display_score_shadow import compute_display_score_shadow
SECTOR_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
UNIFIED_DIR = PROJECT_ROOT / "reports" / "unified"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "agent_bridge"
RESONANCE_DIR = PROJECT_ROOT / "reports" / "board_resonance"

STOCK_LIMIT = 30
AGENT_STOCK_LIMIT = 10


def _build_board_context(date: str) -> dict:
    """Build board_context for aihf_request.json from stable sector inputs."""
    industry_top = []
    concept_top = []

    # Load industry from sector_research.json
    industry_path = SECTOR_RESEARCH_DIR / date / "sector_research.json"
    if industry_path.exists():
        try:
            data = json.loads(industry_path.read_text(encoding="utf-8"))
            for item in data.get("research_results", [])[:10]:
                industry_top.append({
                    "name": item.get("sector_name", ""),
                    "rank": len(industry_top) + 1,
                    "ranking_score": item.get("ranking_score", 0),
                    "opportunity_score": item.get("opportunity_score", 0),
                    "confidence_score": item.get("confidence_score", 0),
                    "agent_label": item.get("consensus_label", ""),
                })
        except Exception:
            pass

    # Load concepts from concept_unified_rank.csv
    concept_path = CONCEPT_RANK_DIR / date / "concept_unified_rank.csv"
    if concept_path.exists():
        try:
            with open(concept_path, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    concept_top.append({
                        "name": row.get("sector_name", ""),
                        "rank": len(concept_top) + 1,
                        "composite_score": float(row.get("concept_final_rank_score", 0) or 0),
                        "trend_score": float(row.get("trend_continuation_score", 0) or 0),
                        "burst_score": float(row.get("short_term_burst_score", 0) or 0),
                        "agent_label": row.get("agent_consensus_label", ""),
                    })
                    if len(concept_top) >= 10:
                        break
        except Exception:
            pass

    return {"industry_top": industry_top, "concept_top": concept_top}
POOL_LIMIT = 15


def load_board_resonance(date: str) -> dict | None:
    """Load board_resonance.json if it exists."""
    resonance_path = RESONANCE_DIR / date / "board_resonance.json"
    if not resonance_path.exists():
        return None
    try:
        return json.loads(resonance_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_stock_resonance_lookup(resonance_pairs: list[dict]) -> dict[str, dict]:
    """Build a lookup dict mapping stock code to its resonance info."""
    stock_lookup = {}
    for pair in resonance_pairs:
        industry = pair.get("industry", "")
        concept = pair.get("concept", "")
        resonance_type = pair.get("resonance_type", "")
        resonance_score = pair.get("resonance_score", 0)
        resonance_bonus = pair.get("resonance_bonus", 0)
        semantic_score = pair.get("semantic_match_score", 0)
        confidence = pair.get("confidence", "")
        rank_delta = pair.get("rank_delta", 0)
        reason = pair.get("reason", "")
        score_breakdown = pair.get("score_breakdown", {})

        for stock in pair.get("overlap_stocks", []):
            code = stock.get("code", "")
            if code and code not in stock_lookup:
                stock_lookup[code] = {
                    "source_resonance_pair": f"{industry} × {concept}",
                    "stock_resonance_score": resonance_score,
                    "stock_resonance_bonus": resonance_bonus,
                    "resonance_type": resonance_type,
                    "resonance_industry": industry,
                    "resonance_concept": concept,
                    # Phase 44 新增字段
                    "semantic_match_score": semantic_score,
                    "resonance_confidence": confidence,
                    "resonance_rank_delta": rank_delta,
                    "resonance_reason": reason,
                    "resonance_score_breakdown": score_breakdown,
                }
    return stock_lookup


def _field(row: dict, *keys, default="-"):
    for k in keys:
        v = row.get(k)
        if v is not None and v != "":
            return v
    return default


def _is_valid_code(code: str) -> bool:
    """Check if stock code is valid (6-digit numeric)."""
    if not code or not isinstance(code, str):
        return False
    code = code.strip()
    return len(code) == 6 and code.isdigit()


def _is_st(name: str) -> bool:
    """Check if stock name indicates ST status."""
    if not name:
        return False
    upper = name.upper()
    return "ST" in upper or "*ST" in upper


def _is_main_board_code(code: str) -> bool:
    """Return True for Shanghai/Shenzhen main-board A-share codes."""
    if not _is_valid_code(code):
        return False
    main_board_prefixes = ("600", "601", "603", "605", "000", "001", "002", "003")
    return code.startswith(main_board_prefixes)


def load_stable_sectors(date: str) -> dict:
    """Load stable sector inputs and build agent maps."""
    industries = []
    concepts = []

    # Industry from sector_research.json
    industry_path = SECTOR_RESEARCH_DIR / date / "sector_research.json"
    if industry_path.exists():
        try:
            data = json.loads(industry_path.read_text(encoding="utf-8"))
            for item in data.get("research_results", []):
                if item.get("sector_type") == "industry":
                    industries.append({
                        "name": item.get("sector_name", ""),
                        "type": "industry",
                        "agent_label": item.get("consensus_label", ""),
                        "ranking_score": item.get("ranking_score", 0),
                        "opportunity_score": item.get("opportunity_score", 0),
                    })
        except Exception:
            pass

    # Concepts from concept_unified_rank.csv
    concept_path = CONCEPT_RANK_DIR / date / "concept_unified_rank.csv"
    if concept_path.exists():
        try:
            with open(concept_path, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    concepts.append({
                        "name": row.get("sector_name", ""),
                        "type": "concept",
                        "agent_label": row.get("agent_consensus_label", ""),
                        "composite_score": float(row.get("concept_final_rank_score", 0) or 0),
                    })
        except Exception:
            pass

    return {"industries": industries, "concepts": concepts}


def load_unified_candidates(date: str, pool_limit: int = POOL_LIMIT) -> tuple[list[dict], dict]:
    """Load candidate stocks from unified pipeline report.

    Returns:
        (candidates, funnel) where funnel tracks filtering statistics
    """
    report_path = UNIFIED_DIR / date / "unified_report.json"
    if not report_path.exists():
        return [], {"trend_requested": 0, "trend_actual": 0, "burst_requested": 0, "burst_actual": 0, "merged_unique": 0}

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return [], {"trend_requested": 0, "trend_actual": 0, "burst_requested": 0, "burst_actual": 0, "merged_unique": 0}

    formal = report.get("formal_candidate_selection")
    formal_mode = report.get("candidate_chain") == "direction_linkage_v2"
    if formal_mode:
        if (
            isinstance(formal, dict)
            and formal.get("status") == "active_for_paper_research"
            and isinstance(formal.get("selected"), list)
        ):
            raw_trend = formal["selected"]
        else:
            raw_trend = []
        raw_burst = []
    else:
        # Legacy compatibility path.
        raw_trend = report.get(
            "trend_candidates_all", report.get("trend_top_stocks", [])
        )
        raw_burst = report.get(
            "burst_candidates_all", report.get("burst_top_stocks", [])
        )

    # Track detailed funnel statistics
    funnel = {
        "raw": {
            "trend_candidates_all": len(raw_trend),
            "burst_candidates_all": len(raw_burst),
        },
        "trend_pool": {
            "raw": len(raw_trend),
            "filtered_invalid_code": 0,
            "filtered_empty_name": 0,
            "filtered_st": 0,
            "filtered_non_main_board": 0,
            "eligible": 0,
            "selected_initial": 0,
            "backfilled": 0,
            "selected_final": 0,
        },
        "burst_pool": {
            "raw": len(raw_burst),
            "filtered_invalid_code": 0,
            "filtered_empty_name": 0,
            "filtered_st": 0,
            "filtered_non_main_board": 0,
            "eligible": 0,
            "selected_initial": 0,
            "backfilled": 0,
            "selected_final": 0,
        },
        "merge": {
            "before_dedup": 0,
            "duplicates_removed": 0,
            "after_dedup": 0,
            "cross_pool_backfilled": 0,
            "final_count": 0,
        },
        "top_loss_reasons": [],
    }

    def _is_valid_code(code: str) -> bool:
        """Check if stock code is valid (6-digit numeric)."""
        if not code or not isinstance(code, str):
            return False
        code = code.strip()
        return len(code) == 6 and code.isdigit()

    def _is_main_board_code(code: str) -> bool:
        """Return True for Shanghai/Shenzhen main-board A-share codes."""
        if not _is_valid_code(code):
            return False
        main_board_prefixes = ("600", "601", "603", "605", "000", "001", "002", "003")
        return code.startswith(main_board_prefixes)

    def _is_st(name: str) -> bool:
        """Check if stock name indicates ST status."""
        if not name:
            return False
        upper = name.upper()
        return "ST" in upper or "*ST" in upper

    def _filter_stock(stock: dict, pool_stats: dict) -> bool:
        """Filter a single stock. Returns True if eligible, False if filtered."""
        code = stock.get("code", "")
        if not _is_valid_code(code):
            pool_stats["filtered_invalid_code"] += 1
            return False
        if not _is_main_board_code(code):
            pool_stats["filtered_non_main_board"] += 1
            return False
        name = stock.get("name", "").strip()
        if not name:
            pool_stats["filtered_empty_name"] += 1
            return False
        if _is_st(name):
            pool_stats["filtered_st"] += 1
            return False
        return True

    def _score(stock: dict, primary: str, alias: str) -> float:
        value = stock.get(primary, stock.get(alias, 0))
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _create_entry(stock: dict, source_pool: str) -> dict:
        """Create a candidate entry from stock data."""
        linkage_selection_score = _score(
            stock, "linkage_selection_score", "linkage_selection_score"
        )
        final_score = _score(stock, "final_score", "final_score")
        return {
            "code": stock.get("code", ""),
            "name": stock.get("name", "").strip(),
            "sector_name": stock.get("sector_name", ""),
            "sector_type": stock.get("sector_type", "concept"),
            "source": "unified_pipeline",
            "source_pool": source_pool,
            "trend_score": _score(stock, "trend_score", "sector_trend_score"),
            "burst_score": _score(stock, "burst_score", "sector_burst_score"),
            "relevance_score": _score(stock, "relevance_score", "relevance_score"),
            "quant_score": _score(stock, "quant_score", "quant_score"),
            "final_score": final_score,
            "linkage_selection_score": linkage_selection_score,
            "sector_direction_score": _score(
                stock, "sector_direction_score", "direction_score_shadow"
            ),
            "active_selection_score": (
                linkage_selection_score if formal_mode else final_score
            ),
            "candidate_chain": (
                "direction_linkage_v2" if formal_mode else "legacy"
            ),
        }

    # ─── Step 1: Filter each pool independently ───
    eligible_trend = []
    for stock in raw_trend:
        if _filter_stock(stock, funnel["trend_pool"]):
            eligible_trend.append(_create_entry(stock, "trend"))
    funnel["trend_pool"]["eligible"] = len(eligible_trend)

    eligible_burst = []
    for stock in raw_burst:
        if _filter_stock(stock, funnel["burst_pool"]):
            eligible_burst.append(_create_entry(stock, "burst"))
    funnel["burst_pool"]["eligible"] = len(eligible_burst)

    # ─── Step 2: Sort each pool by final_score and take top pool_limit ───
    eligible_trend.sort(
        key=lambda x: x.get("active_selection_score", 0), reverse=True
    )
    eligible_burst.sort(
        key=lambda x: x.get("active_selection_score", 0), reverse=True
    )

    selected_trend = eligible_trend[:pool_limit]
    funnel["trend_pool"]["selected_initial"] = len(selected_trend)

    selected_burst = eligible_burst[:pool_limit]
    funnel["burst_pool"]["selected_initial"] = len(selected_burst)

    # ─── Step 3: Backfill if pool is under pool_limit ───
    # For trend pool: try to backfill from burst pool's eligible stocks
    if len(selected_trend) < pool_limit:
        needed = pool_limit - len(selected_trend)
        trend_codes = {s["code"] for s in selected_trend}
        # Backfill from burst pool (that are not already in trend)
        backfill_candidates = [s for s in eligible_burst if s["code"] not in trend_codes]
        backfill_candidates.sort(
            key=lambda x: x.get("active_selection_score", 0), reverse=True
        )
        backfill = backfill_candidates[:needed]
        for s in backfill:
            s["source_pool"] = "both"  # Mark as cross-pool
            selected_trend.append(s)
        funnel["trend_pool"]["backfilled"] = len(backfill)
        funnel["merge"]["cross_pool_backfilled"] += len(backfill)

    # For burst pool: try to backfill from trend pool's eligible stocks
    if len(selected_burst) < pool_limit:
        needed = pool_limit - len(selected_burst)
        burst_codes = {s["code"] for s in selected_burst}
        # Backfill from trend pool (that are not already in burst)
        backfill_candidates = [s for s in eligible_trend if s["code"] not in burst_codes]
        backfill_candidates.sort(
            key=lambda x: x.get("active_selection_score", 0), reverse=True
        )
        backfill = backfill_candidates[:needed]
        for s in backfill:
            s["source_pool"] = "both"  # Mark as cross-pool
            selected_burst.append(s)
        funnel["burst_pool"]["backfilled"] = len(backfill)
        funnel["merge"]["cross_pool_backfilled"] += len(backfill)

    funnel["trend_pool"]["selected_final"] = len(selected_trend)
    funnel["burst_pool"]["selected_final"] = len(selected_burst)

    # ─── Step 4: Merge and dedup ───
    by_code = {}
    all_selected = selected_trend + selected_burst
    funnel["merge"]["before_dedup"] = len(all_selected)

    for entry in all_selected:
        code = entry["code"]
        if code in by_code:
            # Dedup: keep the one with higher final_score, merge source_pool
            existing = by_code[code]
            if entry.get("source_pool") != existing.get("source_pool"):
                existing["source_pool"] = "both"
            existing["trend_score"] = max(existing.get("trend_score", 0), entry.get("trend_score", 0))
            existing["burst_score"] = max(existing.get("burst_score", 0), entry.get("burst_score", 0))
            existing["relevance_score"] = max(existing.get("relevance_score", 0), entry.get("relevance_score", 0))
            existing["quant_score"] = max(existing.get("quant_score", 0), entry.get("quant_score", 0))
            existing["final_score"] = max(existing.get("final_score", 0), entry.get("final_score", 0))
            existing["active_selection_score"] = max(
                existing.get("active_selection_score", 0),
                entry.get("active_selection_score", 0),
            )
            funnel["merge"]["duplicates_removed"] += 1
        else:
            by_code[code] = entry

    funnel["merge"]["after_dedup"] = len(by_code)
    funnel["merge"]["final_count"] = len(by_code)

    # Build top_loss_reasons
    trend_losses = [
        {"reason": "non_main_board", "count": funnel["trend_pool"]["filtered_non_main_board"]},
        {"reason": "invalid_code", "count": funnel["trend_pool"]["filtered_invalid_code"]},
        {"reason": "st_filtered", "count": funnel["trend_pool"]["filtered_st"]},
        {"reason": "empty_name", "count": funnel["trend_pool"]["filtered_empty_name"]},
    ]
    burst_losses = [
        {"reason": "non_main_board", "count": funnel["burst_pool"]["filtered_non_main_board"]},
        {"reason": "invalid_code", "count": funnel["burst_pool"]["filtered_invalid_code"]},
        {"reason": "st_filtered", "count": funnel["burst_pool"]["filtered_st"]},
        {"reason": "empty_name", "count": funnel["burst_pool"]["filtered_empty_name"]},
    ]
    # Merge losses
    loss_counts = {}
    for loss in trend_losses + burst_losses:
        reason = loss["reason"]
        loss_counts[reason] = loss_counts.get(reason, 0) + loss["count"]
    funnel["top_loss_reasons"] = [
        {"reason": r, "count": c}
        for r, c in sorted(loss_counts.items(), key=lambda x: -x[1])
        if c > 0
    ]

    return list(by_code.values()), funnel


def collect_stock_info(candidates: list[dict], http_client=None) -> list[dict]:
    """Enrich candidates with basic info from HTTP API (batch)."""
    if not http_client:
        return candidates

    codes = [c["code"] for c in candidates]
    try:
        batch = http_client.get_stock_info_batch(codes)
        if batch and batch.get("items"):
            items = batch["items"]
            for c in candidates:
                info = items.get(c["code"], {})
                if info:
                    c["exchange"] = info.get("exchange", "")
                    c["market"] = info.get("market", "")
    except Exception:
        pass  # Graceful degradation

    return candidates


def build_board_snapshot(sector_data: dict) -> dict:
    """Build board_snapshot for top30 JSON."""
    industry_top = [
        {"name": s["name"], "agent_label": s["agent_label"]}
        for s in sector_data["industries"][:10]
    ]
    concept_top = [
        {"name": s["name"], "agent_label": s["agent_label"]}
        for s in sector_data["concepts"][:10]
    ]
    return {"industry_top": industry_top, "concept_top": concept_top}


def build_candidate_entry(
    stock: dict,
    sector_data: dict,
    rank: int,
    stock_resonance: dict | None = None,
) -> dict:
    """Build a single candidate entry for top30 JSON."""
    sector_name = stock.get("sector_name", "")
    sector_type = stock.get("sector_type", "")
    code = stock.get("code", "")

    # Build agent map for lookup
    agent_map = {}
    for s in sector_data["industries"] + sector_data["concepts"]:
        agent_map[s["name"]] = s

    agent_info = agent_map.get(sector_name, {})

    # Determine candidate reasons
    reasons = []
    if rank <= 30:
        reasons.append("concept_top10" if sector_type == "concept" else "industry_top10")
    reasons.append("trend_candidate")

    # Determine source pool
    trend_score = stock.get("trend_score", stock.get("sector_trend_score", 0))
    burst_score = stock.get("burst_score", stock.get("sector_burst_score", 0))
    relevance_score = stock.get("relevance_score", 0)
    quant_score = stock.get("quant_score", 0)
    final_score = stock.get("final_score", 0)
    source_pool = stock.get("source_pool")
    if not source_pool:
        if trend_score > 0 and burst_score > 0:
            source_pool = "both"
        elif trend_score > 0:
            source_pool = "trend"
        else:
            source_pool = "burst"

    # Phase 43: Add resonance fields
    resonance_info = (stock_resonance or {}).get(code, {})

    return {
        "code": stock["code"],
        "name": stock["name"],
        "boards": [sector_name] if sector_name else [],
        "board_types": [sector_type] if sector_type else [],
        "source_pool": source_pool,
        "trend_score": trend_score,
        "burst_score": burst_score,
        "relevance_score": relevance_score,
        "quant_score": quant_score,
        "final_score": final_score,
        "candidate_chain": stock.get("candidate_chain", "legacy"),
        "linkage_selection_score": stock.get("linkage_selection_score", 0),
        "sector_direction_score": stock.get("sector_direction_score", 0),
        "active_selection_score": stock.get(
            "active_selection_score", final_score
        ),
        "agent_label": agent_info.get("agent_label", ""),
        "candidate_reasons": reasons,
        "data_sources": ["market_data_service", "stable_sector_inputs"],
        # Phase 43 resonance fields
        "source_resonance_pair": resonance_info.get("source_resonance_pair", ""),
        "stock_resonance_score": resonance_info.get("stock_resonance_score", 0),
        "stock_resonance_bonus": resonance_info.get("stock_resonance_bonus", 0),
        "resonance_type": resonance_info.get("resonance_type", ""),
        "resonance_industry": resonance_info.get("resonance_industry", ""),
        "resonance_concept": resonance_info.get("resonance_concept", ""),
        # Phase 44 新增字段
        "semantic_match_score": resonance_info.get("semantic_match_score", 0),
        "resonance_confidence": resonance_info.get("resonance_confidence", ""),
        "resonance_rank_delta": resonance_info.get("resonance_rank_delta", 0),
        "resonance_reason": resonance_info.get("resonance_reason", ""),
        "resonance_score_breakdown": resonance_info.get("resonance_score_breakdown", {}),
    }


def enrich_candidates_with_scoring(
    candidates: list[dict],
    bars_map: dict[str, list[dict]] | None = None,
) -> list[dict]:
    """Enrich candidates with stock-level scoring, leader identification, risk, and decision score.

    This adds:
    - stock_short_score, stock_short_breakdown, stock_short_tags
    - stock_trend_score, stock_trend_breakdown, stock_trend_tags
    - sector_leader_score, sector_role, leader_tags
    - risk_penalty_score, risk_tags, trade_eligibility, invalid_reason
    - decision_score, decision_breakdown
    - factor_snapshot (with bars factors if bars_map provided)

    Args:
        candidates: List of candidate dicts
        bars_map: Optional dict mapping stock code to bars data.
                  If provided, bar-based factors will be calculated.
                  Phase 2: reserved for future use.

    No bars are fetched — all scoring uses available fields with fallbacks.
    """
    if not candidates:
        return candidates

    for c in candidates:
        # 1. Stock short score (no bars, uses existing fields)
        short_result = compute_stock_short_score(c, bars=None, sector_context=None)
        c["stock_short_score"] = short_result["stock_short_score"]
        c["stock_short_breakdown"] = short_result["stock_short_breakdown"]
        c["stock_short_tags"] = short_result["stock_short_tags"]

        # 2. Stock trend score (no bars, uses existing fields)
        trend_result = compute_stock_trend_score(c, bars=None)
        c["stock_trend_score"] = trend_result["stock_trend_score"]
        c["stock_trend_breakdown"] = trend_result["stock_trend_breakdown"]
        c["stock_trend_tags"] = trend_result["stock_trend_tags"]

    # 3. Sector leader scores (needs all candidates for intra-sector ranking)
    candidates = compute_sector_leader_scores(candidates)

    # 4. Trade risk + decision score (per-stock, after leader scores)
    for c in candidates:
        risk_result = compute_trade_risk(c)
        c["risk_penalty_score"] = risk_result["risk_penalty_score"]
        c["risk_tags"] = risk_result["risk_tags"]
        c["trade_eligibility"] = risk_result["trade_eligibility"]
        c["invalid_reason"] = risk_result["invalid_reason"]

        # 5. Decision score
        decision_result = compute_decision_score(c)
        c["decision_score"] = decision_result["decision_score"]
        c["decision_breakdown"] = decision_result["decision_breakdown"]

        # 6. Risk decomposition (shadow experiment)
        decomp_result = decompose_trade_risk(c)
        c["hard_risk_penalty"] = decomp_result["hard_risk_penalty"]
        c["trade_risk_penalty"] = decomp_result["trade_risk_penalty"]
        c["volatility_elasticity_score"] = decomp_result["volatility_elasticity_score"]
        c["drawdown_risk_score"] = decomp_result["drawdown_risk_score"]
        c["risk_quality_tags"] = decomp_result["risk_quality_tags"]
        c["risk_decomposition_tags"] = decomp_result["risk_decomposition_tags"]
        c["risk_decomposition_breakdown"] = decomp_result["risk_decomposition_breakdown"]

        # 7. Shadow decision score v2 (shadow experiment)
        shadow_result = compute_shadow_decision_score_v2(c)
        c["shadow_decision_score_v2"] = shadow_result["shadow_decision_score_v2"]
        c["shadow_decision_breakdown_v2"] = shadow_result["shadow_decision_breakdown_v2"]
        c["shadow_decision_tags_v2"] = shadow_result["shadow_decision_tags_v2"]

        # 8. Stock short score v2 (shadow experiment)
        short_v2_result = compute_stock_short_score_v2(c)
        c["stock_short_score_v2"] = short_v2_result["stock_short_score_v2"]
        c["stock_short_breakdown_v2"] = short_v2_result["stock_short_breakdown_v2"]
        c["stock_short_v2_tags"] = short_v2_result["stock_short_v2_tags"]

        # 9. Shadow decision score v3 (shadow experiment)
        shadow_v3_result = compute_shadow_decision_score_v3(c)
        c["shadow_decision_score_v3"] = shadow_v3_result["shadow_decision_score_v3"]
        c["shadow_decision_breakdown_v3"] = shadow_v3_result["shadow_decision_breakdown_v3"]
        c["shadow_decision_v3_tags"] = shadow_v3_result["shadow_decision_v3_tags"]

        # 10. Shadow decision score v4 (shadow experiment, regime-aware)
        shadow_v4_result = compute_shadow_decision_score_v4(c)
        c["shadow_decision_score_v4"] = shadow_v4_result["shadow_decision_score_v4"]
        c["shadow_decision_breakdown_v4"] = shadow_v4_result["shadow_decision_breakdown_v4"]
        c["shadow_decision_v4_tags"] = shadow_v4_result["shadow_decision_v4_tags"]
        c["shadow_decision_v4_regime_profile"] = shadow_v4_result["shadow_decision_v4_regime_profile"]

        # 11. Defensive shadow score (shadow experiment, for bearish/mixed markets)
        def_result = compute_defensive_shadow_score(c)
        c["defensive_shadow_score"] = def_result["defensive_shadow_score"]
        c["defensive_shadow_breakdown"] = def_result["defensive_shadow_breakdown"]
        c["defensive_shadow_tags"] = def_result["defensive_shadow_tags"]

        # 12. Regime router shadow score V5 (shadow experiment)
        v5_result = compute_regime_router_shadow_score_v5(c)
        c["regime_router_shadow_score_v5"] = v5_result["regime_router_shadow_score_v5"]
        c["regime_router_shadow_breakdown_v5"] = v5_result["regime_router_shadow_breakdown_v5"]
        c["regime_router_shadow_tags_v5"] = v5_result["regime_router_shadow_tags_v5"]
        c["regime_router_selected_profile"] = v5_result["regime_router_selected_profile"]
        c["bull_regime_shadow_score"] = v5_result["bull_regime_shadow_score"]
        c["bull_regime_shadow_breakdown"] = v5_result["bull_regime_shadow_breakdown"]

    # 13. Build factor snapshot (Phase 2: support bars calculation)
    for c in candidates:
        code = c.get("code", "")
        # Get bars for this stock if available
        bars = bars_map.get(code) if bars_map else None
        c["factor_snapshot"] = build_factor_snapshot(c, as_of=None, bars=bars)

    # 14. Compute factor composite shadow score (Phase 3: shadow-only)
    for c in candidates:
        composite_result = compute_factor_composite_shadow_score(c)
        c["factor_composite_shadow_score"] = composite_result["factor_composite_shadow_score"]
        c["factor_composite_breakdown"] = composite_result["factor_composite_breakdown"]
        c["factor_composite_tags"] = composite_result["factor_composite_tags"]

    # 15. Compute factor composite shadow score v2 (Phase 10: shadow-only experiment)
    for c in candidates:
        composite_v2_result = compute_factor_composite_shadow_score_v2(c)
        c["factor_composite_shadow_score_v2"] = composite_v2_result["factor_composite_shadow_score_v2"]
        c["factor_composite_breakdown_v2"] = composite_v2_result["factor_composite_breakdown_v2"]
        c["factor_composite_tags_v2"] = composite_v2_result["factor_composite_tags_v2"]

    # 16. Compute display score shadow (Phase 12: shadow-only)
    for c in candidates:
        display_result = compute_display_score_shadow(c)
        c["display_score_shadow_90_10"] = display_result["display_score_shadow_90_10"]
        c["display_score_shadow_80_20"] = display_result["display_score_shadow_80_20"]
        c["display_score_shadow_70_30"] = display_result["display_score_shadow_70_30"]
        c["display_score_shadow_breakdown"] = display_result["display_score_shadow_breakdown"]
        c["display_score_shadow_tags"] = display_result["display_score_shadow_tags"]

    return candidates


def export_top30(date: str, stock_limit: int = STOCK_LIMIT) -> Path:
    """Main function: generate top30_candidates.json."""
    print(f"  Generating Top30 candidates for {date}...")

    sector_data = load_stable_sectors(date)
    if not sector_data["industries"] and not sector_data["concepts"]:
        print(f"  ❌ No stable sector data found for {date}")
        return None

    candidates, funnel = load_unified_candidates(date)
    if not candidates:
        print(f"  ⚠️ No unified candidates found, using sector constituent stocks")
        # Fallback: use sector constituent stocks
        candidates = _collect_from_sectors(sector_data)

    # Load board resonance (Phase 43)
    board_resonance = load_board_resonance(date)
    resonance_pairs = board_resonance.get("resonance_pairs", []) if board_resonance else []

    # Build resonance lookup for stocks
    stock_resonance = _build_stock_resonance_lookup(resonance_pairs)

    # Dedup, filter, sort
    candidates = candidates[:stock_limit]

    # Build selection funnel output
    selection_funnel = {
        "raw": funnel.get("raw", {}),
        "trend_pool": funnel.get("trend_pool", {}),
        "burst_pool": funnel.get("burst_pool", {}),
        "merge": funnel.get("merge", {}),
        "top_loss_reasons": funnel.get("top_loss_reasons", []),
    }

    # Build output
    output = {
        "schema_version": "1.0",
        "as_of": date,
        "source": "theme-sector-radar-dev",
        "candidate_count": len(candidates),
        "rank_hidden": True,
        "selection_policy": {
            "industry_top_n": 10,
            "concept_top_n": 10,
            "stock_limit": stock_limit,
            "trend_pool_limit": POOL_LIMIT,
            "burst_pool_limit": POOL_LIMIT,
            "dedupe": True,
            "exclude_st": True,
            "exclude_invalid_code": True,
            "main_board_only": True,
            "exclude_non_main_board": True,
        },
        "selection_funnel": selection_funnel,
        "board_snapshot": build_board_snapshot(sector_data),
        "board_resonance_summary": {
            "total_pairs": len(resonance_pairs),
            "high_confidence_pairs": sum(1 for p in resonance_pairs if p.get("confidence") == "high"),
        },
        "candidates": [
            build_candidate_entry(c, sector_data, i + 1, stock_resonance)
            for i, c in enumerate(candidates)
        ],
    }

    # Enrich built candidates with stock-level scoring, leader, risk, decision
    output["candidates"] = enrich_candidates_with_scoring(output["candidates"])

    # Save
    out_dir = OUTPUT_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "top30_candidates.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  ✅ Top30 candidates saved: {out_path}")
    print(f"  📋 Candidate count: {len(candidates)}")
    print(f"  📊 Selection funnel:")
    raw = funnel.get("raw", {})
    trend_pool = funnel.get("trend_pool", {})
    burst_pool = funnel.get("burst_pool", {})
    merge = funnel.get("merge", {})
    print(f"    - Raw candidates: trend={raw.get('trend_candidates_all', 0)}, burst={raw.get('burst_candidates_all', 0)}")
    print(f"    - Trend pool: eligible={trend_pool.get('eligible', 0)}, selected={trend_pool.get('selected_final', 0)} (backfilled={trend_pool.get('backfilled', 0)})")
    print(f"    - Burst pool: eligible={burst_pool.get('eligible', 0)}, selected={burst_pool.get('selected_final', 0)} (backfilled={burst_pool.get('backfilled', 0)})")
    print(f"    - Merge: before_dedup={merge.get('before_dedup', 0)}, after_dedup={merge.get('after_dedup', 0)}, final={merge.get('final_count', 0)}")
    if trend_pool.get("filtered_non_main_board", 0) > 0 or burst_pool.get("filtered_non_main_board", 0) > 0:
        total_main_board = trend_pool.get("filtered_non_main_board", 0) + burst_pool.get("filtered_non_main_board", 0)
        print(f"    - Non-main-board filtered: {total_main_board}")
    if trend_pool.get("filtered_st", 0) > 0 or burst_pool.get("filtered_st", 0) > 0:
        total_st = trend_pool.get("filtered_st", 0) + burst_pool.get("filtered_st", 0)
        print(f"    - ST filtered: {total_st}")
    return out_path


def merge_agent_scores_into_candidates(
    top30_path: Path,
    ranking_path: Path,
) -> bool:
    """Merge agent_score fields from aihf_stock_ranking.json into top30_candidates.json.

    This enables the scoring calibration pipeline to evaluate agent_score as a
    score layer.  Only ``agent_score``, ``risk_adjusted_score``, and ``risk_level``
    are copied — the ``rank`` field from the ranking is **never** exposed, and
    the ``rank_hidden`` constraint on the candidates file is preserved.

    Returns ``True`` on success, ``False`` when either file is missing or
    parsing fails.
    """
    if not top30_path.exists() or not ranking_path.exists():
        return False

    try:
        ranking_data = json.loads(ranking_path.read_text(encoding="utf-8"))
        ranking_items = ranking_data.get("items", [])

        # Build code -> agent fields lookup
        ranking_lookup: dict[str, dict] = {}
        for item in ranking_items:
            code = str(item.get("code", "")).strip()
            if code:
                ranking_lookup[code] = {
                    "agent_score": item.get("agent_score"),
                    "risk_adjusted_score": item.get("risk_adjusted_score"),
                    "risk_level": item.get("risk_level"),
                }

        top30_data = json.loads(top30_path.read_text(encoding="utf-8"))
        candidates = top30_data.get("candidates", [])

        merged_count = 0
        for candidate in candidates:
            code = str(candidate.get("code", "")).strip()
            if code in ranking_lookup:
                agent_data = ranking_lookup[code]
                candidate["agent_score"] = agent_data.get("agent_score")
                candidate["risk_adjusted_score"] = agent_data.get("risk_adjusted_score")
                candidate["risk_level"] = agent_data.get("risk_level")
                candidate["agent_score_available"] = True
                candidate["agent_analysis_status"] = "analyzed"
                merged_count += 1
            else:
                candidate["agent_score_available"] = False
                if candidate.get("agent_analysis_status") != "skipped_by_agent_stock_limit":
                    candidate["agent_analysis_status"] = "missing_agent_ranking"

        # Metadata — does NOT include raw rank
        top30_data["agent_score_merged"] = True
        top30_data["agent_score_merge_count"] = merged_count
        top30_data["agent_score_source"] = str(ranking_path)

        top30_path.write_text(
            json.dumps(top30_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"  ✅ Merged agent scores into {top30_path}")
        print(f"    - Candidates: {len(candidates)}")
        print(f"    - Merged: {merged_count}")
        print(f"    - Source: {ranking_path}")
        return True

    except Exception as exc:
        print(f"  ❌ Failed to merge agent scores: {exc}")
        return False


def _collect_from_sectors(sector_data: dict) -> list[dict]:
    """Fallback: collect stocks from sector constituent data."""
    # This is a simplified fallback - actual implementation should
    # read from local sector constituent data
    return []


def generate_aihf_request(
    top30_path: Path,
    date: str,
    agent_preset: str = "full",
    agent_stock_limit: int | None = AGENT_STOCK_LIMIT,
) -> Path:
    """Generate aihf_request.json from top30 candidates."""
    top30 = json.loads(top30_path.read_text(encoding="utf-8"))
    candidates = top30.get("candidates", [])

    selected_candidates = _select_agent_candidates(candidates, agent_stock_limit)
    selected_codes = {str(c.get("code", "")).strip() for c in selected_candidates}
    skipped_count = max(0, len(candidates) - len(selected_candidates))

    top30["agent_analysis_policy"] = {
        "source_candidate_count": len(candidates),
        "agent_stock_limit": agent_stock_limit if agent_stock_limit and agent_stock_limit > 0 else len(candidates),
        "agent_analyzed_count": len(selected_candidates),
        "agent_skipped_count": skipped_count,
        "selection_method": "balanced_trend_burst_then_final_score",
    }
    for c in candidates:
        code = str(c.get("code", "")).strip()
        c["agent_analysis_status"] = (
            "pending_agent_analysis" if code in selected_codes else "skipped_by_agent_stock_limit"
        )
    top30_path.write_text(json.dumps(top30, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build board_context from stable sector inputs
    board_context = _build_board_context(date)

    request = {
        "schema_version": "1.0",
        "as_of": date,
        "mode": "stock_agent_ranking",
        "agent_preset": agent_preset,
        "llm_enabled": True,
        "source_candidate_count": len(candidates),
        "agent_stock_limit": agent_stock_limit if agent_stock_limit and agent_stock_limit > 0 else len(candidates),
        "agent_analyzed_count": len(selected_candidates),
        "agent_skipped_count": skipped_count,
        "selection_method": "balanced_trend_burst_then_final_score",
        "board_context": board_context,
        "stocks": [
            {
                "code": c["code"],
                "name": c["name"],
                "boards": c.get("boards", []),
                "board_types": c.get("board_types", []),
                "source_pool": c.get("source_pool", "unknown"),
                "trend_score": c.get("trend_score", 0),
                "burst_score": c.get("burst_score", 0),
                "relevance_score": c.get("relevance_score", 0),
                "quant_score": c.get("quant_score", 0),
                "final_score": c.get("final_score", 0),
                "agent_label": c.get("agent_label", ""),
                # New scoring fields for agent context
                "stock_short_score": c.get("stock_short_score", 0),
                "stock_trend_score": c.get("stock_trend_score", 0),
                "sector_leader_score": c.get("sector_leader_score", 0),
                "decision_score": c.get("decision_score", 0),
                "trade_eligibility": c.get("trade_eligibility", "unknown"),
                "risk_tags": c.get("risk_tags", []),
                # Shadow experiment fields
                "hard_risk_penalty": c.get("hard_risk_penalty", 0),
                "trade_risk_penalty": c.get("trade_risk_penalty", 0),
                "volatility_elasticity_score": c.get("volatility_elasticity_score", 50),
                "drawdown_risk_score": c.get("drawdown_risk_score", 0),
                "risk_quality_tags": c.get("risk_quality_tags", []),
                "shadow_decision_score_v2": c.get("shadow_decision_score_v2", 0),
                "stock_short_score_v2": c.get("stock_short_score_v2", 0),
                "shadow_decision_score_v3": c.get("shadow_decision_score_v3", 0),
                "shadow_decision_score_v4": c.get("shadow_decision_score_v4", 0),
                "shadow_decision_v4_regime_profile": c.get("shadow_decision_v4_regime_profile", "default"),
                "defensive_shadow_score": c.get("defensive_shadow_score", 0),
                "bull_regime_shadow_score": c.get("bull_regime_shadow_score", 0),
                "regime_router_shadow_score_v5": c.get("regime_router_shadow_score_v5", 0),
                "regime_router_selected_profile": c.get("regime_router_selected_profile", "default"),
                # Factor snapshot (Phase 1: pass-through, nullable)
                "factor_snapshot": c.get("factor_snapshot", None),
                # Factor composite shadow score (Phase 3: shadow-only)
                "factor_composite_shadow_score": c.get("factor_composite_shadow_score", 50.0),
                "factor_composite_breakdown": c.get("factor_composite_breakdown", {}),
                "factor_composite_tags": c.get("factor_composite_tags", []),
                # Factor composite shadow score v2 (Phase 10: shadow-only experiment)
                "factor_composite_shadow_score_v2": c.get("factor_composite_shadow_score_v2", 50.0),
                "factor_composite_breakdown_v2": c.get("factor_composite_breakdown_v2", {}),
                "factor_composite_tags_v2": c.get("factor_composite_tags_v2", []),
                # Display score shadow (Phase 12: shadow-only)
                "display_score_shadow_90_10": c.get("display_score_shadow_90_10", None),
                "display_score_shadow_80_20": c.get("display_score_shadow_80_20", None),
                "display_score_shadow_70_30": c.get("display_score_shadow_70_30", None),
                "display_score_shadow_breakdown": c.get("display_score_shadow_breakdown", {}),
                "display_score_shadow_tags": c.get("display_score_shadow_tags", []),
            }
            for c in selected_candidates
        ],
    }

    out_path = top30_path.parent / "aihf_request.json"
    out_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ AIHF request saved: {out_path}")
    print(f"  🤖 AIHF stocks: {len(selected_candidates)}/{len(candidates)}")
    return out_path


def _select_agent_candidates(candidates: list[dict], agent_stock_limit: int | None) -> list[dict]:
    """Select a balanced subset for expensive agent analysis.

    The top30 file keeps the full candidate pool.  This selector only limits
    the AIHF request, preserving both trend and short-term burst representation.
    """
    if not agent_stock_limit or agent_stock_limit <= 0 or len(candidates) <= agent_stock_limit:
        return list(candidates)

    limit = min(agent_stock_limit, len(candidates))
    trend_quota = limit // 2
    burst_quota = limit - trend_quota

    def sort_key(c: dict) -> float:
        try:
            if c.get("candidate_chain") == "direction_linkage_v2":
                return float(c.get("active_selection_score", 0) or 0)
            return float(c.get("final_score", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    trend_pool = [c for c in candidates if c.get("source_pool") in ("trend", "both")]
    burst_pool = [c for c in candidates if c.get("source_pool") in ("burst", "both")]
    trend_pool.sort(key=sort_key, reverse=True)
    burst_pool.sort(key=sort_key, reverse=True)

    selected: list[dict] = []
    seen: set[str] = set()

    def add_many(pool: list[dict], quota: int) -> None:
        for c in pool:
            if len([s for s in selected if s.get("source_pool") == c.get("source_pool")]) >= quota:
                break
            code = str(c.get("code", "")).strip()
            if code and code not in seen:
                selected.append(c)
                seen.add(code)

    add_many(trend_pool, trend_quota)
    add_many(burst_pool, burst_quota)

    if len(selected) < limit:
        fallback = sorted(candidates, key=sort_key, reverse=True)
        for c in fallback:
            code = str(c.get("code", "")).strip()
            if code and code not in seen:
                selected.append(c)
                seen.add(code)
                if len(selected) >= limit:
                    break

    return selected[:limit]



def _sample_candidates() -> list[dict]:
    """Return deterministic demo candidates for open-source sample mode."""
    base = [
        {"code": "600001", "name": "Sample Alpha", "sector_name": "AI Infrastructure", "sector_type": "concept", "source_pool": "trend", "trend_score": 76.0, "burst_score": 58.0, "relevance_score": 82.0, "quant_score": 64.0, "final_score": 78.0, "market_regime": "broad_up", "change_pct": 2.4, "amount": 120000000, "turnover_rate": 2.1},
        {"code": "600002", "name": "Sample Beta", "sector_name": "Advanced Manufacturing", "sector_type": "industry", "source_pool": "burst", "trend_score": 61.0, "burst_score": 74.0, "relevance_score": 77.0, "quant_score": 60.0, "final_score": 73.0, "market_regime": "mixed", "change_pct": 1.6, "amount": 98000000, "turnover_rate": 1.7},
        {"code": "000001", "name": "Sample Gamma", "sector_name": "Dividend Defense", "sector_type": "industry", "source_pool": "both", "trend_score": 59.0, "burst_score": 52.0, "relevance_score": 70.0, "quant_score": 68.0, "final_score": 69.0, "market_regime": "broad_down", "change_pct": -0.4, "amount": 150000000, "turnover_rate": 1.2},
        {"code": "000002", "name": "Sample Delta", "sector_name": "Energy Storage", "sector_type": "concept", "source_pool": "trend", "trend_score": 66.0, "burst_score": 62.0, "relevance_score": 74.0, "quant_score": 59.0, "final_score": 67.0, "market_regime": "mixed", "change_pct": 0.8, "amount": 86000000, "turnover_rate": 1.5},
        {"code": "002001", "name": "Sample Epsilon", "sector_name": "Semiconductor Materials", "sector_type": "concept", "source_pool": "burst", "trend_score": 63.0, "burst_score": 69.0, "relevance_score": 72.0, "quant_score": 57.0, "final_score": 65.0, "market_regime": "broad_up", "change_pct": 3.2, "amount": 102000000, "turnover_rate": 2.4},
    ]
    return [dict(item, boards=[item["sector_name"]], board_types=[item["sector_type"]]) for item in base]


def export_sample_top30(date: str = "2026-06-28", stock_limit: int = STOCK_LIMIT, agent_stock_limit: int | None = AGENT_STOCK_LIMIT) -> Path:
    """Generate a minimal top30/aihf_request demo without StockDB, reports, or API keys."""
    candidates = _sample_candidates()[:stock_limit]
    candidates = enrich_candidates_with_scoring(candidates)
    out_dir = OUTPUT_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "schema_version": "1.0",
        "as_of": date,
        "source": "theme-sector-radar-dev-sample",
        "sample_mode": True,
        "candidate_count": len(candidates),
        "rank_hidden": True,
        "production_change_allowed": False,
        "disclaimer": "Research sample only. Not investment advice or stock recommendation.",
        "selection_policy": {
            "sample_fixture": True,
            "stock_limit": stock_limit,
            "exclude_st": True,
            "main_board_only": True,
        },
        "shadow_score_policy": {
            "v5_status": "review_ready_shadow_only",
            "production_enabled": False,
            "review_ready_means": "human_review_required_not_auto_production",
        },
        "board_snapshot": {
            "industry_top": [{"name": "Advanced Manufacturing", "type": "industry"}],
            "concept_top": [{"name": "AI Infrastructure", "type": "concept"}],
        },
        "candidates": candidates,
    }

    top30_path = out_dir / "top30_candidates.json"
    top30_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    selected = _select_agent_candidates(candidates, agent_stock_limit)
    request = {
        "schema_version": "1.0",
        "as_of": date,
        "mode": "stock_agent_ranking_sample",
        "sample_mode": True,
        "llm_enabled": False,
        "source_candidate_count": len(candidates),
        "agent_stock_limit": agent_stock_limit if agent_stock_limit and agent_stock_limit > 0 else len(candidates),
        "agent_analyzed_count": len(selected),
        "agent_skipped_count": max(0, len(candidates) - len(selected)),
        "disclaimer": "Research sample only. Not investment advice or stock recommendation.",
        "stocks": selected,
    }
    (out_dir / "aihf_request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Sample Top30 candidates saved: {top30_path}")
    return top30_path

# ============================================================
# CLI
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="Export Top30 candidates for ai-hedge-fund")
    parser.add_argument("--sample", action="store_true", help="Run deterministic sample mode without StockDB or historical reports")
    parser.add_argument("--as-of", default=None, help="Date YYYY-MM-DD")
    parser.add_argument("--stock-limit", type=int, default=STOCK_LIMIT, help="Max stocks")
    parser.add_argument("--agent-stock-limit", type=int, default=AGENT_STOCK_LIMIT, help="Max stocks sent to AIHF agents")
    args = parser.parse_args()

    if args.sample:
        export_sample_top30(args.as_of or "2026-06-28", args.stock_limit, args.agent_stock_limit)
        return

    if not args.as_of:
        parser.error("--as-of is required unless --sample is used")

    top30_path = export_top30(args.as_of, args.stock_limit)
    if top30_path:
        generate_aihf_request(top30_path, args.as_of, agent_stock_limit=args.agent_stock_limit)


if __name__ == "__main__":
    main()



