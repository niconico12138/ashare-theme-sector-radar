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
SECTOR_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
UNIFIED_DIR = PROJECT_ROOT / "reports" / "unified"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "agent_bridge"
RESONANCE_DIR = PROJECT_ROOT / "reports" / "board_resonance"

STOCK_LIMIT = 30


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

    # Get complete candidate lists (Phase 39: read from trend_candidates_all/burst_candidates_all)
    # Fall back to trend_top_stocks/burst_top_stocks if complete lists not available
    raw_trend = report.get("trend_candidates_all", report.get("trend_top_stocks", []))
    raw_burst = report.get("burst_candidates_all", report.get("burst_top_stocks", []))

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
            "final_score": _score(stock, "final_score", "final_score"),
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
    eligible_trend.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    eligible_burst.sort(key=lambda x: x.get("final_score", 0), reverse=True)

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
        backfill_candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)
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
        backfill_candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)
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


def _collect_from_sectors(sector_data: dict) -> list[dict]:
    """Fallback: collect stocks from sector constituent data."""
    # This is a simplified fallback - actual implementation should
    # read from local sector constituent data
    return []


def generate_aihf_request(
    top30_path: Path,
    date: str,
    agent_preset: str = "full",
) -> Path:
    """Generate aihf_request.json from top30 candidates."""
    top30 = json.loads(top30_path.read_text(encoding="utf-8"))

    # Build board_context from stable sector inputs
    board_context = _build_board_context(date)

    request = {
        "schema_version": "1.0",
        "as_of": date,
        "mode": "stock_agent_ranking",
        "agent_preset": agent_preset,
        "llm_enabled": True,
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
            }
            for c in top30["candidates"]
        ],
    }

    out_path = top30_path.parent / "aihf_request.json"
    out_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ AIHF request saved: {out_path}")
    return out_path


# ============================================================
# CLI
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="Export Top30 candidates for ai-hedge-fund")
    parser.add_argument("--as-of", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--stock-limit", type=int, default=STOCK_LIMIT, help="Max stocks")
    args = parser.parse_args()

    top30_path = export_top30(args.as_of, args.stock_limit)
    if top30_path:
        generate_aihf_request(top30_path, args.as_of)


if __name__ == "__main__":
    main()






