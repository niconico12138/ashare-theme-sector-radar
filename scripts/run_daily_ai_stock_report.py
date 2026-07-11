#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 30: 最终每日运行入口

一键运行：生成每日 AI 板块与个股观察报告。

用法:
  python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03
  python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset core --agent-mode real
  python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset full --agent-mode real --full-limit 10
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AIHEDGE_ROOT = PROJECT_ROOT.parent / "ai-hedge-fund"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "daily_ai_stock_report"
_open_socket = socket.create_connection
_urllib_request = urllib.request


def check_dependency_details(as_of: str) -> dict[str, dict]:
    api_url = os.environ.get("MARKET_DATA_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
    sector_research_path = PROJECT_ROOT / "reports" / "full90" / "sector_research" / as_of / "sector_research.json"
    concept_rank_path = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank" / as_of / "concept_unified_rank.csv"
    results: dict[str, dict] = {}

    try:
        sock = _open_socket(("127.0.0.1", 7899), timeout=3)
        sock.close()
        results["stockdb"] = {"ok": True, "detail": "127.0.0.1:7899 reachable", "action": ""}
    except Exception as exc:
        results["stockdb"] = {
            "ok": False,
            "detail": f"127.0.0.1:7899 not reachable: {exc}",
            "action": "Set STOCKDB_EXE_PATH to stockdb.exe or start your local StockDB service",
        }

    try:
        resp = _urllib_request.urlopen(f"{api_url}/health", timeout=10)
        ok = resp.status == 200
        results["api"] = {
            "ok": ok,
            "detail": f"{api_url}/health returned {resp.status}",
            "action": "" if ok else "start market_data_service and verify /health",
        }
    except Exception as exc:
        results["api"] = {
            "ok": False,
            "detail": f"{api_url}/health unavailable: {exc}",
            "action": "start market_data_service and verify /health",
        }

    results["sector_research"] = {
        "ok": sector_research_path.exists(),
        "detail": str(sector_research_path),
        "action": "generate full90 sector_research for this date",
    }
    results["concept_rank"] = {
        "ok": concept_rank_path.exists(),
        "detail": str(concept_rank_path),
        "action": "generate full_concept unified_rank for this date",
    }
    for item in ("sector_research", "concept_rank"):
        if results[item]["ok"]:
            results[item]["action"] = ""
    return results


# ─── Pre-flight checks ──────────────────────────────────────


def check_dependencies(as_of: str) -> dict[str, bool]:
    results = {}
    # 1. StockDB
    try:
        sock = __import__("socket").create_connection(("127.0.0.1", 7899), timeout=3)
        sock.close()
        results["stockdb"] = True
    except Exception:
        results["stockdb"] = False
    # 2. API — use lightweight /health endpoint (fast, no slow sources)
    try:
        import urllib.request
        resp = urllib.request.urlopen(
            f"{os.environ.get('MARKET_DATA_SERVICE_URL', 'http://127.0.0.1:8000')}/health", timeout=10
        )
        results["api"] = resp.status == 200
    except Exception:
        results["api"] = False
    # 3. Stable board outputs
    results["sector_research"] = (
        PROJECT_ROOT / "reports" / "full90" / "sector_research" / as_of / "sector_research.json"
    ).exists()
    results["concept_rank"] = (
        PROJECT_ROOT / "reports" / "full_concept" / "unified_rank" / as_of / "concept_unified_rank.csv"
    ).exists()
    return results


# ─── Phase 34: Pure helper functions ─────────────────────────


def match_board_context(stock: dict, board_context: dict) -> dict:
    """Match stock's source_boards to industry/concept context."""
    boards = stock.get("source_boards") or stock.get("boards", [])
    board_type = stock.get("board_type", "")
    if board_type == "concept":
        for top in board_context.get("concept_top", []):
            if top["name"] in boards:
                return {
                    "matched": True, "board_type": "concept",
                    "board_name": top["name"],
                    "rank": top.get("rank", "-"),
                    "score": top.get("composite_score", 0),
                    "trend_score": top.get("trend_score", 0),
                    "burst_score": top.get("burst_score", 0),
                    "agent_label": top.get("agent_label", "-"),
                }
    for top in board_context.get("industry_top", []):
        if top["name"] in boards:
            return {
                "matched": True, "board_type": "industry",
                "board_name": top["name"],
                "rank": top.get("rank", "-"),
                "score": top.get("ranking_score", 0),
                "trend_score": 0, "burst_score": 0,
                "agent_label": top.get("agent_label", "-"),
            }
    return {"matched": False}


def build_candidate_pool_summary(candidate_pool: dict) -> dict:
    """Build summary stats from candidate pool."""
    candidates = candidate_pool.get("candidates", [])
    if not candidates:
        return {"total": 0, "trend": 0, "burst": 0, "both": 0,
                "source_distribution": {}, "board_top": []}
    trend = sum(1 for c in candidates if c.get("source_pool") == "trend")
    burst = sum(1 for c in candidates if c.get("source_pool") == "burst")
    both = sum(1 for c in candidates if c.get("source_pool") == "both")
    board_counts = {}
    for c in candidates:
        for b in c.get("boards", []):
            board_counts[b] = board_counts.get(b, 0) + 1
    board_top = sorted(board_counts.items(), key=lambda x: -x[1])[:10]
    return {
        "total": len(candidates), "trend": trend, "burst": burst, "both": both,
        "source_distribution": {"trend": trend, "burst": burst, "both": both},
        "board_top": [{"board": b, "count": cnt} for b, cnt in board_top],
    }


def load_candidate_pool_quality(date: str) -> dict | None:
    """Load candidate_pool_quality.json if it exists, otherwise return None."""
    quality_path = PROJECT_ROOT / "reports" / "agent_bridge" / date / "candidate_pool_quality.json"
    if not quality_path.exists():
        return None
    try:
        return json.loads(quality_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_board_resonance(date: str) -> dict | None:
    """Load board_resonance.json if it exists, otherwise return None."""
    resonance_path = PROJECT_ROOT / "reports" / "board_resonance" / date / "board_resonance.json"
    if not resonance_path.exists():
        return None
    try:
        return json.loads(resonance_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_board_resonance_feedback() -> dict | None:
    """Load board_resonance_calibration_eval.json if it exists."""
    feedback_path = PROJECT_ROOT / "reports" / "board_resonance" / "calibration" / "board_resonance_calibration_eval.json"
    if not feedback_path.exists():
        return None
    try:
        data = json.loads(feedback_path.read_text(encoding="utf-8"))
        return data.get("feedback_summary", {})
    except Exception:
        return None



def build_stock_agent_top10(items: list[dict], board_context: dict) -> list[dict]:
    """Enrich Top10 ranking items with board context and fixed stock-score fields."""
    enriched = []
    for i, item in enumerate(items[:10], 1):
        ctx = match_board_context(item, board_context)
        ir_contrib = False
        for fa in item.get("top_positive_agents", []):
            if fa.get("agent") == "industry_rotation":
                ir_contrib = True
                break
        for fb in item.get("fallback_agents", []):
            if fb.get("agent") == "industry_rotation":
                ir_contrib = False
                break
        enriched.append({
            "rank": i,
            "code": item.get("code", "-"),
            "name": item.get("name", "-"),
            "source_pool": item.get("source_pool", "-"),
            "source_boards": item.get("source_boards") or item.get("boards", []),
            "board_context_match": ctx,
            "trend_score": item.get("trend_score", 0),
            "burst_score": item.get("burst_score", 0),
            "relevance_score": item.get("relevance_score", 0),
            "quant_score": item.get("quant_score", 0),
            "final_score": item.get("final_score", 0),
            "agent_score": item.get("agent_score", 0),
            "risk_adjusted_score": item.get("risk_adjusted_score", 0),
            "risk_level": item.get("risk_level", "-"),
            "contributing_agents": item.get("contributing_agents", 0),
            "industry_rotation_contributed": ir_contrib,
            "top_positive_agents": item.get("top_positive_agents", []),
            "top_negative_agents": item.get("top_negative_agents", []),
            "fallback_agents": item.get("fallback_agents", []),
            "bullish_count": item.get("bullish_count", 0),
            "neutral_count": item.get("neutral_count", 0),
            "bearish_count": item.get("bearish_count", 0),
            "summary": item.get("summary", ""),
        })
    return enriched

def build_agent_execution_summary(run_meta: dict, items: list[dict]) -> dict:
    """Build agent execution stats from run_meta."""
    per_agent = run_meta.get("per_agent_status", run_meta.get("agent_execution", {}).get("per_agent_status", {}))
    requested = run_meta.get("requested_agents", [])
    succeeded = set(run_meta.get("succeeded_agents", []))
    fallback = set(run_meta.get("fallback_agents", []))
    failed = set(run_meta.get("failed_agents", []))

    agents = []
    for a in requested:
        stats = per_agent.get(a, {})
        agents.append({
            "agent": a,
            "called": stats.get("called", len(items)),
            "succeeded": stats.get("succeeded", 1 if a in succeeded else 0),
            "fallback": stats.get("fallback", 1 if a in fallback else 0),
            "failed": stats.get("failed", 1 if a in failed else 0),
        })
    return {"preset": run_meta.get("agent_preset", "?"), "agents": agents}


def build_data_risk_summary(deps: dict, as_of: str) -> dict:
    """Build data risk summary from dependencies check."""
    return {
        "stockdb_available": deps.get("stockdb", False),
        "api_available": deps.get("api", False),
        "sector_research_available": deps.get("sector_research", False),
        "concept_rank_available": deps.get("concept_rank", False),
        "as_of_date": as_of,
    }


# ─── Markdown builder ────────────────────────────────────────



def _fmt(value, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _pct01(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if 0 <= v <= 1:
        return f"{v:.3f}"
    return f"{v:.1f}"


def build_markdown_report(
    as_of: str, sector_data: dict, stock_ranking: dict | None,
    top_n: int, candidate_pool: dict = None, deps: dict = None,
    candidate_quality: dict = None, board_resonance: dict = None,
    board_resonance_feedback: dict = None,
) -> str:
    """Build the fixed daily board + stock report template."""
    lines = []
    lines.append("# 每日 AI 板块与个股观察报告")
    lines.append("")
    lines.append(f"**日期**: {as_of}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅供研究观察，不构成投资建议。")
    lines.append("")

    meta = stock_ranking.get("run_meta", {}) if stock_ranking else {}
    llm = meta.get("llm_status", {})
    lines.append("## 1. 运行摘要")
    lines.append("")
    lines.append(f"- **日期**: {as_of}")
    lines.append(f"- **Preset**: {meta.get('agent_preset', '?')}")
    lines.append(f"- **Agent 数量**: {meta.get('agent_count', '?')}")
    lines.append(f"- **LLM 状态**: configured={llm.get('configured', '?')}, available={llm.get('available', '?')}, model={llm.get('model', '?')}")
    lines.append("")

    lines.append("## 2. 板块主线摘要")
    lines.append("")
    lines.append("### 行业板块 Top10")
    lines.append("")
    lines.append("| 排名 | 行业 | Agent标签 | 排序分 | 机会分 | 证据分 | 风控分 | 置信度 | 趋势分 | 短线分 |")
    lines.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for i, s in enumerate(sector_data.get("industries", [])[:top_n], 1):
        lines.append(
            f"| {i} | {s.get('name','-')} | {s.get('agent_label','-')} | "
            f"{_fmt(s.get('ranking_score'), 2)} | {_fmt(s.get('opportunity_score'), 2)} | "
            f"{_fmt(s.get('evidence_score'), 2)} | {_fmt(s.get('risk_control_score'), 2)} | "
            f"{_fmt(s.get('confidence_score'), 2)} | {_fmt(s.get('trend_score'), 1)} | {_fmt(s.get('burst_score'), 1)} |"
        )
    lines.append("")

    lines.append("### 概念板块 Top10")
    lines.append("")
    lines.append("| 排名 | 概念 | 综合分 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Agent排序分 | Agent机会分 | 风控分 | Agent标签 |")
    lines.append("|---:|---|---:|---:|---|---:|---|---:|---:|---:|---|")
    for i, s in enumerate(sector_data.get("concepts", [])[:top_n], 1):
        lines.append(
            f"| {i} | {s.get('name','-')} | {_fmt(s.get('composite_score'), 2)} | "
            f"{_fmt(s.get('trend_score'), 2)} | {s.get('trend_level','-')} | "
            f"{_fmt(s.get('burst_score'), 2)} | {s.get('burst_level','-')} | "
            f"{_fmt(s.get('agent_ranking_score'), 2)} | {_fmt(s.get('agent_opportunity_score'), 2)} | "
            f"{_fmt(s.get('risk_control_score'), 2)} | {s.get('agent_label','-')} |"
        )
    lines.append("")

    pool = candidate_pool or {}
    cp_summary = build_candidate_pool_summary(pool)
    lines.append("## 3. 候选池摘要")
    lines.append("")
    lines.append(f"- 趋势池: {cp_summary.get('trend', 0)} 只")
    lines.append(f"- 短线池: {cp_summary.get('burst', 0)} 只")
    lines.append(f"- 同时入选: {cp_summary.get('both', 0)} 只")
    lines.append(f"- 合并去重: {cp_summary.get('total', 0)} 只")
    lines.append("- rank_hidden: true (不携带原始排序)")
    lines.append("- ST 过滤: 已执行")
    lines.append("- 主板过滤: 已执行")
    lines.append("")
    board_top = cp_summary.get("board_top", [])
    if board_top:
        lines.append("| 来源板块 | 候选股数量 |")
        lines.append("|---|---:|")
        for b in board_top[:10]:
            lines.append(f"| {b['board']} | {b['count']} |")
        lines.append("")

    # Candidate pool quality section (Phase 41)
    if candidate_quality:
        lines.append("## 候选池质量")
        lines.append("")
        basic_stats = candidate_quality.get("basic_stats", {})
        concentration = candidate_quality.get("board_concentration", {})
        risk_tags = candidate_quality.get("quality_risk_tags", [])

        lines.append(f"- **候选股总数**: {basic_stats.get('final_candidate_count', 0)}")
        lines.append(f"- **趋势池**: {basic_stats.get('trend_count', 0)} 只")
        lines.append(f"- **短线池**: {basic_stats.get('burst_count', 0)} 只")
        lines.append(f"- **同时入选**: {basic_stats.get('both_count', 0)} 只")
        lines.append(f"- **板块数**: {basic_stats.get('unique_board_count', 0)}")
        lines.append(f"- **Top1 板块占比**: {concentration.get('top1_board_ratio', 0):.1%}")
        lines.append(f"- **Top3 板块占比**: {concentration.get('top3_boards_ratio', 0):.1%}")
        lines.append(f"- **质量标签**: {', '.join(risk_tags)}")
        lines.append("")

        # Top boards
        top_boards = concentration.get("top_boards", [])
        if top_boards:
            lines.append("### 板块集中度")
            lines.append("")
            lines.append("| 板块 | 数量 | 占比 |")
            lines.append("|------|------|------|")
            for item in top_boards[:5]:
                lines.append(f"| {item.get('board', '')} | {item.get('count', 0)} | {item.get('ratio', 0):.1%} |")
            lines.append("")
    else:
        lines.append("## 候选池质量")
        lines.append("")
        lines.append("- ⚠️ 候选池质量数据不可用")
        lines.append("")

    # Board resonance section (Phase 43)
    if board_resonance:
        lines.append("## 板块共振")
        lines.append("")
        resonance_pairs = board_resonance.get("resonance_pairs", [])
        summary = board_resonance.get("summary", {})
        lines.append(f"- **共振组合数**: {summary.get('total_pairs', 0)}")
        lines.append(f"- **高置信度组合**: {summary.get('high_confidence_pairs', 0)}")
        lines.append(f"- **平均共振分**: {summary.get('avg_resonance_score', 0):.2f}")
        lines.append("")

        if resonance_pairs:
            lines.append("### 共振 Top10")
            lines.append("")
            lines.append("| Rank | 行业 | 概念 | 类型 | 共振分 | 加分 | 重叠股数 | 说明 |")
            lines.append("|------|------|------|------|--------|------|----------|------|")
            for pair in resonance_pairs[:10]:
                lines.append(
                    f"| {pair.get('rank', 0)} | "
                    f"{pair.get('industry', '')} | "
                    f"{pair.get('concept', '')} | "
                    f"{pair.get('resonance_type', '')} | "
                    f"{pair.get('resonance_score', 0):.2f} | "
                    f"+{pair.get('resonance_bonus', 0):.2f} | "
                    f"{pair.get('overlap_stock_count', 0)} | "
                    f"{pair.get('reason', '')[:30]} |"
                )
            lines.append("")
    else:
        lines.append("## 板块共振")
        lines.append("")
        lines.append("- ⚠️ 板块共振数据不可用")
        lines.append("")

    # Phase 46: Board resonance feedback section
    if board_resonance_feedback:
        lines.append("## 板块共振反馈")
        lines.append("")
        underestimated = board_resonance_feedback.get("underestimated_strong", [])
        overestimated = board_resonance_feedback.get("overestimated_unrelated", [])
        missing = board_resonance_feedback.get("missing_expected_strong", [])
        semantic = board_resonance_feedback.get("semantic_map_candidates", [])

        lines.append(f"- **强共振低估数量**: {len(underestimated)}")
        lines.append(f"- **无关组合高估数量**: {len(overestimated)}")
        lines.append(f"- **缺失强共振数量**: {len(missing)}")
        lines.append(f"- **建议补充语义映射**: {len(semantic)}")
        lines.append("")

        if underestimated:
            lines.append("### Top 低估样本")
            lines.append("")
            lines.append("| 行业 | 概念 | 期望 | 实际 | 分数 | 语义分 | 建议 |")
            lines.append("|------|------|------|------|------|--------|------|")
            for e in underestimated[:5]:
                lines.append(
                    f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                    f"{e.get('expected_level', '')} | {e.get('actual_level', '')} | "
                    f"{e.get('resonance_score', 0):.2f} | "
                    f"{e.get('semantic_match_score', 0):.0f} | "
                    f"{e.get('suggested_action', '')} |"
                )
            lines.append("")

        if overestimated:
            lines.append("### Top 高估样本")
            lines.append("")
            lines.append("| 行业 | 概念 | 期望 | 实际 | 分数 | 语义分 | 建议 |")
            lines.append("|------|------|------|------|------|--------|------|")
            for e in overestimated[:5]:
                lines.append(
                    f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                    f"{e.get('expected_level', '')} | {e.get('actual_level', '')} | "
                    f"{e.get('resonance_score', 0):.2f} | "
                    f"{e.get('semantic_match_score', 0):.0f} | "
                    f"{e.get('suggested_action', '')} |"
                )
            lines.append("")
    else:
        lines.append("## 板块共振反馈")
        lines.append("")
        lines.append("- ⚠️ 未生成校准反馈")
        lines.append("")

    ranking_items = stock_ranking.get("items", []) if stock_ranking else []
    bc = (stock_ranking or {}).get("board_context", {})
    enriched = build_stock_agent_top10(ranking_items, bc) if ranking_items else []

    # ─── v3: 计算综合排名分 ──────────────────────────────────
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from theme_sector_radar.scoring.board_composite_score import compute_board_score
        from theme_sector_radar.convergence_scoring import compute_final_score as v3_final_score
        for item in enriched:
            boards = item.get("source_boards", [])
            board_name = boards[0] if boards else ""
            # 从板块数据获取趋势/短线分
            bt = 0
            bb = 0
            for sec in (sector_data.get("industries", []) + sector_data.get("concepts", [])):
                if sec.get("name") == board_name:
                    bt = sec.get("trend_score", 0) or 0
                    bb = sec.get("burst_score", 0) or 0
                    break
            board_score, regime, _ = compute_board_score(bt, bb)

            quant = item.get("quant_score", 50)
            agent = item.get("agent_score", 50)
            risk_level = item.get("risk_level", "unknown")
            risk_map = {"low": 0, "medium": 3, "high": 8, "unknown": 1}
            risk_penalty = risk_map.get(risk_level, 1)

            # Agent投票推算趋势/短线分
            bullish = item.get("bullish_count", 0)
            bearish = item.get("bearish_count", 0)
            if bullish > bearish:
                ta = min(100, agent + (bullish - bearish) * 2)
                sa = min(100, agent + (bullish - bearish) * 1.5)
            elif bearish > bullish:
                ta = max(0, agent - (bearish - bullish) * 2)
                sa = max(0, agent - (bearish - bullish) * 1.5)
            else:
                ta = agent
                sa = agent

            r = v3_final_score(board_trend_score=bt, board_burst_score=bb,
                               trend_agent_score=ta, short_agent_score=sa,
                               quant_score=quant, risk_penalty=risk_penalty)
            item["v3_final_score"] = r["final_score"]
            item["v3_convergence_bonus"] = r["convergence_bonus"]
            item["v3_convergence_label"] = r["convergence_label"]
            item["v3_trend_agent"] = round(ta, 1)
            item["v3_short_agent"] = round(sa, 1)
            item["v3_board_score"] = board_score
            item["v3_regime"] = regime

        enriched.sort(key=lambda x: x.get("v3_final_score", 0), reverse=True)
        for i, item in enumerate(enriched, 1):
            item["v3_rank"] = i
    except (ImportError, Exception) as e:
        for item in enriched:
            item["v3_final_score"] = item.get("final_score", 0)
            item["v3_convergence_bonus"] = 0
            item["v3_convergence_label"] = "N/A"
            item["v3_rank"] = item.get("rank", 0)

    # ─── 快速决策表（放在最前面）─────────────────────────────
    lines.append(f"## 快速决策")
    lines.append("")
    lines.append("> 综合分 = 板块趋势×0.20 + Agent趋势×0.15 + 板块短线×0.20 + Agent短线×0.15 + 量化×0.30 + 共振加分")
    lines.append("")

    # 分类
    confirmed = [x for x in enriched if x.get("v3_convergence_bonus", 0) > 0 and x.get("v3_final_score", 0) >= 60]
    watch = [x for x in enriched if x.get("v3_convergence_bonus", 0) == 0 and x.get("v3_final_score", 0) >= 55]
    caution = [x for x in enriched if x.get("v3_final_score", 0) < 55]

    if confirmed:
        lines.append("### ✅ 重点关注（趋势+短线共振确认）")
        lines.append("")
        lines.append("| # | 代码 | 名称 | 板块 | 综合分 | 量化 | Agent | 风险 | 投票(多/空) | 理由 |")
        lines.append("|---:|---|---|---|---:|---:|---:|---|---:|---|")
        for item in confirmed[:5]:
            vote = f"{item.get('bullish_count',0)}/{item.get('bearish_count',0)}"
            reason = item.get("summary", "")[:40]
            risk_icon = "⚠️" if item.get("risk_level") == "high" else ""
            lines.append(
                f"| {item.get('v3_rank',0)} | {item.get('code','')} | {item.get('name','')} | "
                f"{','.join(item.get('source_boards',['-']))} | "
                f"**{item.get('v3_final_score',0):.1f}** | {item.get('quant_score',0):.0f} | "
                f"{item.get('agent_score',0):.0f} | {item.get('risk_level','-')[:3]}{risk_icon} | "
                f"{vote} | {reason} |"
            )
        lines.append("")

    if watch:
        lines.append("### 📋 观察（综合分尚可，待确认）")
        lines.append("")
        lines.append("| # | 代码 | 名称 | 板块 | 综合分 | 量化 | Agent | 风险 | 投票(多/空) | 理由 |")
        lines.append("|---:|---|---|---|---:|---:|---:|---|---:|---|")
        for item in watch[:5]:
            vote = f"{item.get('bullish_count',0)}/{item.get('bearish_count',0)}"
            reason = item.get("summary", "")[:40]
            risk_icon = "⚠️" if item.get("risk_level") == "high" else ""
            lines.append(
                f"| {item.get('v3_rank',0)} | {item.get('code','')} | {item.get('name','')} | "
                f"{','.join(item.get('source_boards',['-']))} | "
                f"{item.get('v3_final_score',0):.1f} | {item.get('quant_score',0):.0f} | "
                f"{item.get('agent_score',0):.0f} | {item.get('risk_level','-')[:3]}{risk_icon} | "
                f"{vote} | {reason} |"
            )
        lines.append("")

    if caution:
        lines.append("### ⚠️ 谨慎（综合分偏低或风险高）")
        lines.append("")
        lines.append("| # | 代码 | 名称 | 综合分 | Agent | 风险 | 原因 |")
        lines.append("|---:|---|---|---:|---:|---|---|")
        for item in caution[:5]:
            risk_icon = "⚠️" if item.get("risk_level") == "high" else ""
            reason = item.get("summary", "")[:50]
            lines.append(
                f"| {item.get('v3_rank',0)} | {item.get('code','')} | {item.get('name','')} | "
                f"{item.get('v3_final_score',0):.1f} | {item.get('agent_score',0):.0f} | "
                f"{item.get('risk_level','-')[:3]}{risk_icon} | {reason} |"
            )
        lines.append("")

    # ─── 板块摘要 ────────────────────────────────────────────
    lines.append("## 板块主线")
    lines.append("")
    lines.append("### 行业 Top10")
    lines.append("")
    lines.append("| # | 行业 | 标签 | 排序分 | 趋势 | 短线 |")
    lines.append("|---:|---|---|---:|---:|---:|")
    for i, s in enumerate(sector_data.get("industries", [])[:10], 1):
        lines.append(
            f"| {i} | {s.get('name','-')} | {s.get('agent_label','-')} | "
            f"{_fmt(s.get('ranking_score'), 2)} | {_fmt(s.get('trend_score'), 1)} | {_fmt(s.get('burst_score'), 1)} |"
        )
    lines.append("")

    # ─── 个股完整排名 ────────────────────────────────────────
    lines.append(f"## 个股完整排名（v3）")
    lines.append("")
    lines.append("| # | 代码 | 名称 | 板块 | 板块分 | 量化 | Agent | 趋势A | 短线A | 风险 | 多/中/空 | 共振 | 综合分 |")
    lines.append("|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|")
    for item in enriched:
        boards = ",".join(item.get("source_boards", [])) or "-"
        vote = f"{item.get('bullish_count',0)}/{item.get('neutral_count',0)}/{item.get('bearish_count',0)}"
        risk_icon = "⚠️" if item.get("risk_level") == "high" else ""
        bonus = item.get("v3_convergence_bonus", 0)
        bonus_str = f"+{int(bonus)}" if bonus > 0 else str(int(bonus))
        lines.append(
            f"| {item.get('v3_rank',0)} | {item.get('code','')} | {item.get('name','')} | {boards} | "
            f"{item.get('v3_board_score',0):.0f} | {item.get('quant_score',0):.0f} | "
            f"{item.get('agent_score',0):.0f} | {item.get('v3_trend_agent',0):.0f} | "
            f"{item.get('v3_short_agent',0):.0f} | {item.get('risk_level','-')[:3]}{risk_icon} | "
            f"{vote} | {bonus_str} | **{item.get('v3_final_score',0):.1f}** |"
        )
    lines.append("")

    # ─── 个股分析明细（精简版）────────────────────────────────
    lines.append(f"## 个股分析明细")
    lines.append("")
    for item in enriched[:top_n]:
        pos = item.get("top_positive_agents", [])
        neg = item.get("top_negative_agents", [])
        pos_str = ", ".join(f"{a['agent']}" for a in pos[:2]) if pos else "-"
        neg_str = ", ".join(f"{a['agent']}" for a in neg[:2]) if neg else "-"
        risk_icon = "⚠️" if item.get("risk_level") == "high" else ""
        bonus = item.get("v3_convergence_bonus", 0)
        bonus_str = f" +{int(bonus)}" if bonus > 0 else ""

        lines.append(f"**{item.get('v3_rank',0)}. {item.get('code','')} {item.get('name','')}** — 综合分 {item.get('v3_final_score',0):.1f}{bonus_str}")
        lines.append(f"- 板块: {','.join(item.get('source_boards',['-']))} (板块分{item.get('v3_board_score',0):.0f}) | 量化: {item.get('quant_score',0):.0f} | Agent: {item.get('agent_score',0):.0f} | 风险: {item.get('risk_level','-')}{risk_icon}")
        lines.append(f"- 投票: 看多{item.get('bullish_count',0)} / 中性{item.get('neutral_count',0)} / 看空{item.get('bearish_count',0)}")
        lines.append(f"- 支持: {pos_str} | 反对: {neg_str}")
        lines.append(f"- {item.get('summary','')}")
        lines.append("")

    # ─── Agent 运行统计 ──────────────────────────────────────
    agent_summary = build_agent_execution_summary(meta, ranking_items)
    lines.append("## Agent 运行统计")
    lines.append("")
    lines.append("| Agent | 调用 | 成功 | 降级 | 失败 |")
    lines.append("|---|---:|---:|---:|---:|")
    for a in agent_summary.get("agents", []):
        lines.append(f"| {a['agent']} | {a['called']} | {a['succeeded']} | {a['fallback']} | {a['failed']} |")
    lines.append("")

    # ─── 数据源 ──────────────────────────────────────────────
    risk = build_data_risk_summary(deps or {}, as_of)
    lines.append("## 数据源")
    lines.append("")
    lines.append(f"- StockDB: {'✅' if risk.get('stockdb_available') else '❌'} | "
                 f"API: {'✅' if risk.get('api_available') else '❌'} | "
                 f"板块评分: {'✅' if risk.get('sector_research_available') else '❌'} | "
                 f"概念排名: {'✅' if risk.get('concept_rank_available') else '❌'}")
    lines.append("")
    lines.append("> 本报告仅供研究观察，不构成投资建议。")

    return "\n".join(lines)

# ─── Main ────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="每日 AI 板块与个股观察报告")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--agent-preset", default="selected", choices=["selected", "core", "full"])
    parser.add_argument("--agent-mode", default="real", choices=["real", "simulate"])
    parser.add_argument("--full-limit", type=int, default=0)
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--llm-enabled", action="store_true", help="Enable LLM enhancement")
    parser.add_argument("--llm-smoke", action="store_true", help="Run LLM smoke test")
    parser.add_argument("--llm-model", default="", help="LLM model name")
    args = parser.parse_args()

    date = args.as_of
    out_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*70}")
    print(f"  每日 AI 板块与个股观察报告 — {date}")
    print(f"{'='*70}")
    print()

    # Pre-flight
    dependency_details = check_dependency_details(date)
    deps = {name: bool(detail.get("ok")) for name, detail in dependency_details.items()}
    missing = [k for k, v in deps.items() if not v]
    if missing:
        print(f"  ❌ 前置依赖不满足: {missing}")
        for name in missing:
            detail = dependency_details[name]
            print(f"    - {name}: {detail.get('detail', '')}")
            if detail.get("action"):
                print(f"      action: {detail['action']}")
        return 1

    # Load sector data
    import csv as _csv
    sector_data = {"industries": [], "concepts": []}
    industry_path = PROJECT_ROOT / "reports" / "full90" / "sector_research" / date / "sector_research.json"
    if industry_path.exists():
        data = json.loads(industry_path.read_text(encoding="utf-8"))
        sector_data["industries"] = [
            {"name": s.get("sector_name",""), "agent_label": s.get("consensus_label",""),
             "ranking_score": s.get("ranking_score",0), "opportunity_score": s.get("opportunity_score",0),
             "evidence_score": s.get("evidence_score",0), "risk_control_score": s.get("risk_control_score",0),
             "confidence_score": s.get("confidence_score",0),
             "trend_score": s.get("trend_continuation_score", s.get("trend_score", 0)),
             "burst_score": s.get("short_term_burst_score", s.get("burst_score", 0))}
            for s in data.get("research_results",[]) if s.get("sector_type") == "industry"
        ]

    # Fallback: 从 sector_scores.json 补充行业趋势/短线分
    # sector_scores.json 有10个行业带趋势/短线分，sector_research.json 有90个行业但没有这些分
    score_path = PROJECT_ROOT / "reports" / "sector_scores" / date / "sector_scores.json"
    if score_path.exists():
        try:
            with open(score_path, "r", encoding="utf-8") as f:
                score_data = json.load(f)
            # 建立 sector_scores.json 的趋势/短线分映射
            score_map = {}
            for s in score_data.get("scores", []):
                score_map[s.get("sector_name", "")] = {
                    "trend": float(s.get("trend_continuation_score", 0) or 0),
                    "burst": float(s.get("short_term_burst_score", 0) or 0),
                }
            # 补充行业数据
            for ind in sector_data["industries"]:
                sm = score_map.get(ind["name"], {})
                if sm:
                    ind["trend_score"] = sm["trend"]
                    ind["burst_score"] = sm["burst"]
            # 把 sector_scores.json 中有但 sector_research.json 中没有的行业也加进去
            existing_names = {ind["name"] for ind in sector_data["industries"]}
            for s in score_data.get("scores", []):
                if s.get("sector_type") == "industry" and s["sector_name"] not in existing_names:
                    interp = s.get("score_interpretation", {})
                    sector_data["industries"].append({
                        "name": s["sector_name"],
                        "agent_label": interp.get("profile", ""),
                        "ranking_score": float(s.get("sector_selection_score", 0) or 0),
                        "opportunity_score": 0, "evidence_score": 0,
                        "risk_control_score": 1.0, "confidence_score": 0.9,
                        "trend_score": float(s.get("trend_continuation_score", 0) or 0),
                        "burst_score": float(s.get("short_term_burst_score", 0) or 0),
                    })
            # 按 ranking_score 排序
            sector_data["industries"].sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
        except Exception:
            pass

    concept_path = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank" / date / "concept_unified_rank.csv"
    if concept_path.exists():
        with open(concept_path, "r", encoding="utf-8-sig") as f:
            for row in _csv.DictReader(f):
                sector_data["concepts"].append({
                    "name": row.get("sector_name",""), "agent_label": row.get("agent_consensus_label",""),
                    "composite_score": float(row.get("concept_final_rank_score",0) or 0),
                    "trend_score": float(row.get("trend_continuation_score",0) or 0),
                    "trend_level": row.get("trend_level_cn", row.get("trend_level", "")),
                    "burst_score": float(row.get("short_term_burst_score",0) or 0),
                    "burst_level": row.get("burst_level_cn", row.get("burst_level", "")),
                    "agent_ranking_score": float(row.get("agent_ranking_score",0) or 0),
                    "agent_opportunity_score": float(row.get("agent_opportunity_score",0) or 0),
                    "risk_control_score": float(row.get("risk_control_score",0) or 0),
                })

    # Fallback: 如果 CSV 为空，从 sector_scores.json 读取概念数据
    if not sector_data["concepts"]:
        score_path = PROJECT_ROOT / "reports" / "sector_scores" / date / "sector_scores.json"
        if score_path.exists():
            try:
                with open(score_path, "r", encoding="utf-8") as f:
                    score_data = json.load(f)
                for s in score_data.get("scores", []):
                    if s.get("sector_type") == "concept":
                        interp = s.get("score_interpretation", {})
                        sector_data["concepts"].append({
                            "name": s.get("sector_name", ""),
                            "agent_label": interp.get("profile", ""),
                            "composite_score": float(s.get("sector_selection_score", 0) or 0),
                            "trend_score": float(s.get("trend_continuation_score", 0) or 0),
                            "trend_level": s.get("trend_level_cn", s.get("trend_level", "")),
                            "burst_score": float(s.get("short_term_burst_score", 0) or 0),
                            "burst_level": s.get("burst_level_cn", s.get("burst_level", "")),
                            "agent_ranking_score": 0,
                            "agent_opportunity_score": 0,
                            "risk_control_score": 0,
                        })
            except Exception:
                pass

    # Run bridge
    print("  Running bridge report...")
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_bridge_report.py"),
           "--as-of", date, "--agent-preset", args.agent_preset, "--agent-mode", args.agent_mode]
    if args.full_limit > 0 and args.agent_preset == "full":
        cmd.extend(["--limit", str(args.full_limit)])
    if args.llm_enabled:
        cmd.append("--llm-enabled")
    if args.llm_smoke:
        cmd.append("--llm-smoke")
    if args.llm_model:
        cmd.extend(["--llm-model", args.llm_model])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                         cwd=str(PROJECT_ROOT), timeout=3600)

    # Load results
    bridge_dir = PROJECT_ROOT / "reports" / "agent_bridge" / date
    stock_ranking = None
    candidate_pool = {}
    if (bridge_dir / "aihf_stock_ranking.json").exists():
        stock_ranking = json.loads((bridge_dir / "aihf_stock_ranking.json").read_text(encoding="utf-8"))
    if (bridge_dir / "top30_candidates.json").exists():
        candidate_pool = json.loads((bridge_dir / "top30_candidates.json").read_text(encoding="utf-8"))

    # Write JSON
    output = {
        "as_of": date, "status": "ok", "generated_at": datetime.now().isoformat(),
        "board_summary": {"industry_top10": sector_data["industries"][:args.top_n],
                          "concept_top10": sector_data["concepts"][:args.top_n]},
        "candidate_pool": {"count": candidate_pool.get("candidate_count",0),
                           "rank_hidden": True, "path": str(bridge_dir / "top30_candidates.json")},
        "stock_agent_summary": {
            "preset": args.agent_preset, "mode": args.agent_mode,
            "ranking_top10": (stock_ranking or {}).get("items",[])[:args.top_n],
            "run_meta": (stock_ranking or {}).get("run_meta",{}),
        },
        "report_sections": {
            "run_summary": {"date": date, "preset": args.agent_preset,
                           "agent_count": (stock_ranking or {}).get("run_meta",{}).get("agent_count", 0)},
            "board_top10": {"industries": sector_data["industries"][:args.top_n],
                            "concepts": sector_data["concepts"][:args.top_n]},
            "candidate_pool_summary": build_candidate_pool_summary(candidate_pool),
            "candidate_pool_quality": load_candidate_pool_quality(date),
            "board_resonance": load_board_resonance(date),
            "board_resonance_feedback": load_board_resonance_feedback(),
            "stock_agent_top10": build_stock_agent_top10(
                (stock_ranking or {}).get("items",[])[:args.top_n],
                (stock_ranking or {}).get("board_context",{})),
            "agent_execution_summary": build_agent_execution_summary(
                (stock_ranking or {}).get("run_meta",{}), (stock_ranking or {}).get("items",[])),
            "data_risk_summary": build_data_risk_summary(deps, date),
        },
    }
    json_path = out_dir / "daily_ai_stock_report.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Write Markdown
    candidate_quality = load_candidate_pool_quality(date)
    board_resonance = load_board_resonance(date)
    board_resonance_feedback = load_board_resonance_feedback()
    md = build_markdown_report(date, sector_data, stock_ranking, args.top_n, candidate_pool, deps, candidate_quality, board_resonance, board_resonance_feedback)
    md_path = out_dir / "daily_ai_stock_report.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    meta = stock_ranking.get("run_meta", {}) if stock_ranking else {}
    print(f"\n  Status: {meta.get('agent_preset','?')} | Agents: {meta.get('agent_count','?')} | Candidates: {candidate_pool.get('candidate_count',0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

