#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
show_daily_result.py — 每日运行结果输出模板

用法：
  python scripts/show_daily_result.py --as-of 2026-07-03
  python scripts/show_daily_result.py --as-of 2026-07-03 --top-n 10
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECTOR_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
UNIFIED_DIR = PROJECT_ROOT / "reports" / "unified"


def _field(row: dict, *keys, default="-"):
    """Safely get a field by trying multiple key names."""
    for k in keys:
        v = row.get(k)
        if v is not None and v != "":
            return v
    return default


def _f(val, fmt=".2f", default="-"):
    """Format a number safely."""
    if val is None or val == "-":
        return "-"
    try:
        return f"{float(val):{fmt}}"
    except (ValueError, TypeError):
        return str(val)


def _print_section(title: str, char: str = "=", width: int = 70):
    print(f"{char*3}")
    print(f"  {title}")
    print(f"{char*3}")


def load_sector_research(date: str) -> list[dict]:
    """Load industry sector research from full90."""
    path = SECTOR_RESEARCH_DIR / date / "sector_research.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        results = data.get("research_results", [])
        return [r for r in results if r.get("sector_type") == "industry"]
    except Exception:
        return []


def load_concept_rank(date: str) -> list[dict]:
    """Load concept unified rank from CSV."""
    path = CONCEPT_RANK_DIR / date / "concept_unified_rank.csv"
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            # Normalize column names for display
            for r in rows:
                r["_name"] = _field(r, "sector_name", "概念", "name", "concept")
                r["_comp"] = _field(r, "concept_final_rank_score", "综合分", "final_score", "composite_score")
                r["_trend"] = _field(r, "trend_continuation_score", "趋势分", "trend_score")
                r["_trend_level"] = _field(r, "trend_level_cn", "趋势等级", "trend_level")
                r["_burst"] = _field(r, "short_term_burst_score", "短线分", "burst_score")
                r["_burst_level"] = _field(r, "burst_level_cn", "短线等级", "burst_level")
                r["_agent"] = _field(r, "agent_consensus_label", "Agent标签", "agent_label")
                r["agent_ranking_score"] = r.get("agent_ranking_score", "-")
                r["agent_opportunity_score"] = r.get("agent_opportunity_score", "-")
                r["confidence_score"] = r.get("confidence_score", "-")
            return rows
    except Exception:
        return []


def load_unified_report(date: str) -> dict:
    """Load unified pipeline report."""
    path = UNIFIED_DIR / date / "unified_report.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ============================================================
# 输出函数
# ============================================================


def print_summary(report: dict, date: str):
    """Part 1: 运行摘要"""
    _print_section("运行摘要")
    src = report.get("data_source", {}).get("sector_input_source", "legacy_sector_scores")
    if src.startswith("mixed"):
        src_desc = "mixed (行业 full90 + 概念 unified_rank)"
    elif src.startswith("stable"):
        src_desc = src
    else:
        src_desc = f"legacy (reports/sector_scores/{date}/)"

    health = report.get("run_health", {})
    dq = report.get("data_quality", {})
    print(f"  日期: {date}")
    print(f"  板块评分来源: {src_desc}")
    status_icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(health.get("status", ""), "")
    print(f"  健康门禁: {status_icon} {health.get('status', 'unknown').upper()}")
    for r in health.get("reasons", []):
        print(f"    - {r}")
    dq_icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(dq.get("status", ""), "")
    print(f"  数据质量: {dq_icon} {dq.get('status', 'unknown').upper()}")
    print(f"  报告目录: reports/unified/{date}")
    print()


def print_industries(sectors: list[dict], top_n: int):
    """Part 2: 行业 Top N"""
    _print_section(f"行业 Top {min(top_n, len(sectors))} (sector_research.json)")
    print(f"  {'排名':>4} {'行业':<10} {'Agent标签':<28} {'Agent分':>8} {'机会分':>8} {'证据分':>8} {'风控分':>8} {'置信度':>8}")
    print(f"  {'─'*72}")
    for i, s in enumerate(sectors[:top_n], 1):
        name = _field(s, "sector_name", "name", "industry")
        label = _field(s, "consensus_label", "agent_label", "label", "diagnosis_label")
        ranking = _f(s.get("ranking_score"))
        opp = _f(s.get("opportunity_score"))
        evidence = _f(s.get("evidence_score"))
        risk = _f(s.get("risk_control_score"))
        conf = _f(s.get("confidence_score"))
        print(f"  {i:4d} {name:<10} {str(label):<28} {ranking:>8} {opp:>8} {evidence:>8} {risk:>8} {conf:>8}")
    print()


def print_concepts(rows: list[dict], top_n: int):
    """Part 3: 概念 Top N"""
    _print_section(f"概念 Top {min(top_n, len(rows))} (concept_unified_rank.csv)")
    print(f"  {'排名':>4} {'概念':<16} {'综合分':>8} {'趋势分':>8} {'趋势等级':<8} {'短线分':>8} {'短线等级':<8} {'Agent标签':<16} {'Agent分':>8} {'机会分':>8} {'置信度':>8}")
    print(f"  {'─'*88}")
    for i, r in enumerate(rows[:top_n], 1):
        name = str(r.get("_name", "-"))
        comp = _f(r.get("_comp"))
        trend = _f(r.get("_trend"))
        trend_level = str(r.get("_trend_level", "-"))
        burst = _f(r.get("_burst"))
        burst_level = str(r.get("_burst_level", "-"))
        agent = str(r.get("_agent", "-"))
        agent_score = _f(r.get("_agent_score", r.get("agent_ranking_score", "-")))
        opp = _f(r.get("_opp", r.get("agent_opportunity_score", "-")))
        conf = _f(r.get("confidence_score", "-"))
        print(f"  {i:4d} {name:<16} {comp:>8} {trend:>8} {trend_level:<8} {burst:>8} {burst_level:<8} {agent:<16} {agent_score:>8} {opp:>8} {conf:>8}")
    print()


def print_stocks(stocks: list[dict], label: str, top_n: int, sector_agent_map: dict):
    """Part 4/5: 趋势/短线观察池个股"""
    _print_section(f"{label} Top {min(top_n, len(stocks))}")
    print(f"  {'排名':>4} {'代码':<8} {'名称':<10} {'综合分':>8} {'量化分':>8} {'关联度':>8} {'趋势分':>8} {'短线分':>8} {'资金':>4} {'板块':<12} {'Agent':<12} {'Agent分':>8}")
    print(f"  {'─'*88}")
    for i, s in enumerate(stocks[:top_n], 1):
        bd = s.get("score_breakdown", {})
        ff = "✓" if bd.get("has_fund_flow") else "—"
        name = _field(s, "name", default="-")
        sector = _field(s, "sector_name", default="-")
        # Look up Agent from sector_agent_map
        agent_info = sector_agent_map.get(sector, {})
        agent = agent_info.get("agent_label", "-")
        agent_score = _f(agent_info.get("ranking_score", "-"), fmt=".2f")
        trend = _f(s.get("sector_trend_score", s.get("trend_score", "-")), fmt=".1f")
        burst = _f(s.get("sector_burst_score", s.get("burst_score", "-")), fmt=".1f")
        print(f"  {i:4d} {s.get('code','-'):<8} {name:<10} {s.get('final_score',0):>8.1f} "
              f"{s.get('quant_score',0):>8.1f} {s.get('relevance_score',0):>8.3f} "
              f"{trend:>8} {burst:>8} {ff:>4} {sector:<12} {str(agent):<12} {agent_score:>8}")
    print()


def print_data_sources(report: dict):
    """Part 6: 数据源与风险"""
    _print_section("数据源与风险")

    ds = report.get("data_source", {})
    csrc = ds.get("constituent_sources", {})
    qsrc = ds.get("quant_score_sources", {})
    ff = ds.get("fund_flow_source", "?")
    si = ds.get("stock_info_sources", {})
    health = report.get("run_health", {})
    dq = report.get("data_quality", {})

    print(f"  成分股来源: {json.dumps(csrc, ensure_ascii=False)}")
    print(f"  K线/量化来源: {json.dumps(qsrc, ensure_ascii=False)}")
    print(f"  资金流来源: {ff}")
    print(f"  股票基础信息: {json.dumps(si, ensure_ascii=False)}")

    # Coverage
    cov = dq.get("coverage", {})
    if cov:
        print(f"  数据质量覆盖率:")
        print(f"    成分股真实源: {cov.get('constituent_sources_real_ratio', 0):.1%}")
        print(f"    量化 http 增强: {cov.get('quant_http_ratio', 0):.1%}")
        print(f"    资金流可用: {cov.get('fund_flow_available_ratio', 0):.1%}")
        print(f"    股票基础信息: {cov.get('stock_info_known_ratio', 0):.1%}")

    # Risks
    reasons = health.get("reasons", [])
    if reasons:
        print(f"  风险提示:")
        for r in reasons:
            print(f"    - {r}")

    # dq warnings
    dq_warns = dq.get("warnings", [])
    if dq_warns:
        print(f"  数据质量警告:")
        for w in dq_warns:
            print(f"    - {w}")
    print()


# ============================================================
# 主入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="每日运行结果摘要")
    parser.add_argument("--as-of", required=True, help="日期 YYYY-MM-DD")
    parser.add_argument("--top-n", type=int, default=10, help="Top N 数量")
    args = parser.parse_args()

    date = args.as_of
    top_n = args.top_n

    # Load data
    report = load_unified_report(date)
    if not report:
        print(f"❌ 未找到 reports/unified/{date}/unified_report.json")
        print(f"   请先运行:")
        print(f"   python unified_pipeline.py --as-of {date} --mode quick")
        sys.exit(1)

    sectors = load_sector_research(date)
    concepts = load_concept_rank(date)

    # Build sector_agent_map: sector_name -> {agent_label, ranking_score, ...}
    sector_agent_map = {}
    for s in sectors:
        name = _field(s, "sector_name", "name", "industry")
        sector_agent_map[name] = {
            "agent_label": s.get("consensus_label", "-"),
            "ranking_score": s.get("ranking_score"),
            "opportunity_score": s.get("opportunity_score"),
            "evidence_score": s.get("evidence_score"),
            "risk_control_score": s.get("risk_control_score"),
            "confidence_score": s.get("confidence_score"),
            "confirm_level": s.get("confirm_level", "-"),
        }
    for r in concepts:
        name = r.get("_name", "-")
        if name not in sector_agent_map:
            sector_agent_map[name] = {}
        sector_agent_map[name].update({
            "agent_label": r.get("_agent", "-"),
            "agent_ranking_score": r.get("agent_ranking_score", "-"),
            "agent_opportunity_score": r.get("agent_opportunity_score", "-"),
            "confidence_score": r.get("confidence_score", "-"),
        })

    # Part 1: Summary
    print_summary(report, date)

    # Part 2: Industries
    if sectors:
        print_industries(sectors, top_n)
    else:
        print(f"  (无行业 sector_research.json 数据)")
        print()

    # Part 3: Concepts
    if concepts:
        print_concepts(concepts, top_n)
    else:
        print(f"  (无概念 concept_unified_rank.csv 数据)")
        print()

    # Part 4: Trend stocks
    trend_stocks = report.get("trend_top_stocks", [])
    if trend_stocks:
        print_stocks(trend_stocks, "趋势观察池个股", top_n, sector_agent_map)

    # Part 5: Burst stocks
    burst_stocks = report.get("burst_top_stocks", [])
    if burst_stocks:
        print_stocks(burst_stocks, "短线观察池个股", top_n, sector_agent_map)

    # Part 6: Data sources
    print_data_sources(report)


if __name__ == "__main__":
    main()
