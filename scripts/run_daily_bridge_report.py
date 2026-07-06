#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 24 Step 3: run_daily_bridge_report.py

总桥接报告：合并 theme-sector-radar-dev 板块分析 + ai-hedge-fund Agent 个股排名。

用法:
  python scripts/run_daily_bridge_report.py --as-of 2026-07-03 --agent-preset full
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AIHEDGE_ROOT = PROJECT_ROOT.parent / "ai-hedge-fund"
SECTOR_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "agent_bridge"


def _field(row: dict, *keys, default="-"):
    for k in keys:
        v = row.get(k)
        if v is not None and v != "":
            return v
    return default


def load_stable_sectors(date: str) -> dict:
    """Load stable sector inputs."""
    industries = []
    concepts = []

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
                        "evidence_score": item.get("evidence_score", 0),
                        "risk_control_score": item.get("risk_control_score", 0),
                        "confidence_score": item.get("confidence_score", 0),
                    })
        except Exception:
            pass

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
                        "trend_score": float(row.get("trend_continuation_score", 0) or 0),
                        "burst_score": float(row.get("short_term_burst_score", 0) or 0),
                    })
        except Exception:
            pass

    return {"industries": industries, "concepts": concepts}


def run_phase24_scripts(date: str, preset: str, agent_mode: str = "simulate", llm_model: str = "") -> dict:
    """Run the Phase 24 scripts and return results."""
    # Step 1: Export top30
    print("  Step 1: Generating Top30 candidates...")
    top30_path = PROJECT_ROOT / "scripts" / "export_top30_candidates.py"
    proc1 = subprocess.run(
        [sys.executable, str(top30_path), "--as-of", date],
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(PROJECT_ROOT),
    )
    if proc1.returncode != 0:
        print(f"  ❌ Top30 export failed: {proc1.stderr}")
        return {"status": "failed", "error": proc1.stderr}

    print(proc1.stdout)

    # Step 2: Run ai-hedge-fund bridge
    print("  Step 2: Running ai-hedge-fund Agents...")
    request_path = OUTPUT_DIR / date / "aihf_request.json"
    output_path = OUTPUT_DIR / date / "aihf_stock_ranking.json"
    bridge_script = AIHEDGE_ROOT / "scripts" / "run_stock_agent_bridge.py"

    if not bridge_script.exists():
        print(f"  ❌ AIHF bridge script not found: {bridge_script}")
        return {"status": "failed", "error": f"Bridge script not found: {bridge_script}"}

    # Use ai-hedge-fund venv Python if available
    aihf_venv_python = AIHEDGE_ROOT / ".venv" / "Scripts" / "python.exe"
    python_cmd = str(aihf_venv_python) if aihf_venv_python.exists() else sys.executable

    cmd = [
        python_cmd, str(bridge_script),
        "--input", str(request_path),
        "--output", str(output_path),
        "--agent-preset", preset,
        "--mode", agent_mode,
        "--llm-enabled",
    ]
    if llm_model:
        cmd.extend(["--llm-model", llm_model])

    proc2 = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(AIHEDGE_ROOT),
        timeout=1800,  # 30 min for full preset
    )
    print(proc2.stdout)
    if proc2.stderr:
        print(f"  ⚠️ AIHF stderr: {proc2.stderr[:500]}")

    if not output_path.exists():
        print(f"  ❌ AIHF ranking not generated")
        return {"status": "failed", "error": "AIHF ranking not generated"}

    # Load results
    ranking = json.loads(output_path.read_text(encoding="utf-8"))
    return {"status": "ok", "ranking": ranking, "output_path": output_path}


def build_bridge_report(
    date: str,
    sector_data: dict,
    ranking: dict | None,
    bridge_output: dict,
) -> dict:
    """Build the merged bridge report."""
    top30_path = OUTPUT_DIR / date / "top30_candidates.json"
    top30 = json.loads(top30_path.read_text(encoding="utf-8")) if top30_path.exists() else {}

    report = {
        "schema_version": "1.0",
        "report_type": "daily_bridge_report",
        "as_of": date,
        "generated_at": datetime.now().isoformat(),
        "source": "theme-sector-radar-dev + ai-hedge-fund",
        "board_snapshot": top30.get("board_snapshot", {}),
        "industry_top": sector_data["industries"][:10],
        "concept_top": sector_data["concepts"][:10],
        "top30_candidates": top30.get("candidates", []),
        "agent_ranking": ranking.get("items", []) if ranking else [],
        "run_meta": ranking.get("run_meta", {}) if ranking else {},
        "data_sources": {
            "sector_input_source": "stable_full90 + stable_concept",
            "agent_preset": bridge_output.get("ranking", {}).get("agent_preset", "full"),
            "llm_enabled": True,
            "agent_count": bridge_output.get("ranking", {}).get("agent_count", 0),
        },
        "health": {
            "bridge_status": bridge_output.get("status", "unknown"),
            "agent_succeeded": len(ranking.get("items", []) if ranking else []),
            "agent_failed": 0,
            "agent_timed_out": 0,
        },
        "warnings": [],
        "disclaimer": "本报告仅供研究参考，不构成投资建议。",
    }

    if not ranking or not ranking.get("items"):
        report["warnings"].append("AIHF Agent ranking unavailable — showing board analysis only")

    return report


def generate_bridge_markdown(report: dict, date: str) -> str:
    """Generate Markdown bridge report."""
    lines = []
    lines.append(f"# 每日板块与个股 Agent 分析报告")
    lines.append(f"")
    lines.append(f"**日期**: {date}")
    lines.append(f"**生成时间**: {report.get('generated_at', '')}")
    lines.append(f"> **免责声明**: 本报告仅供研究参考，不构成投资建议。")
    lines.append(f"")

    # Summary
    lines.append(f"## 运行摘要")
    lines.append(f"")
    health = report.get("health", {})
    status = health.get("bridge_status", "unknown")
    icon = "✅" if status == "ok" else "⚠️" if status == "warn" else "❌"
    lines.append(f"  {icon} 桥接状态: {status.upper()}")
    lines.append(f"  Agent preset: {report.get('data_sources', {}).get('agent_preset', 'full')}")
    lines.append(f"  Agent 数量: {report.get('data_sources', {}).get('agent_count', 0)}")
    lines.append(f"  成功 Agent: {health.get('agent_succeeded', 0)}")
    lines.append(f"")

    # Board analysis
    lines.append(f"## 板块分析: theme-sector-radar-dev")
    lines.append(f"")

    # Industry Top10
    lines.append(f"### 行业 Top10")
    lines.append(f"")
    lines.append(f"  {'排名':>4} {'行业':<10} {'Agent标签':<28} {'Agent分':>8} {'机会分':>8} {'证据分':>8} {'风控分':>8} {'置信度':>8}")
    lines.append(f"  {'─'*72}")
    for i, s in enumerate(report.get("industry_top", [])[:10], 1):
        name = _field(s, "name", "sector_name")
        label = _field(s, "agent_label", "consensus_label")
        ranking = f"{s.get('ranking_score', 0):.2f}" if s.get("ranking_score") else "-"
        opp = f"{s.get('opportunity_score', 0):.2f}" if s.get("opportunity_score") else "-"
        evidence = f"{s.get('evidence_score', 0):.2f}" if s.get("evidence_score") else "-"
        risk = f"{s.get('risk_control_score', 0):.2f}" if s.get("risk_control_score") else "-"
        conf = f"{s.get('confidence_score', 0):.2f}" if s.get("confidence_score") else "-"
        lines.append(f"  {i:4d} {name:<10} {str(label):<28} {ranking:>8} {opp:>8} {evidence:>8} {risk:>8} {conf:>8}")
    lines.append(f"")

    # Concept Top10
    lines.append(f"### 概念 Top10")
    lines.append(f"")
    lines.append(f"  {'排名':>4} {'概念':<16} {'综合分':>8} {'趋势分':>8} {'短线分':>8} {'Agent标签':<16}")
    lines.append(f"  {'─'*60}")
    for i, s in enumerate(report.get("concept_top", [])[:10], 1):
        name = _field(s, "name", "sector_name")
        comp = f"{s.get('composite_score', 0):.2f}" if s.get("composite_score") else "-"
        trend = f"{s.get('trend_score', 0):.2f}" if s.get("trend_score") else "-"
        burst = f"{s.get('burst_score', 0):.2f}" if s.get("burst_score") else "-"
        agent = _field(s, "agent_label", "agent_consensus_label")
        lines.append(f"  {i:4d} {name:<16} {comp:>8} {trend:>8} {burst:>8} {str(agent):<16}")
    lines.append(f"")

    # Top30 candidates
    lines.append(f"## Top30 候选池")
    lines.append(f"")
    lines.append(f"> 以下候选池不带原始排名，仅作为 ai-hedge-fund 的个股分析输入。")
    lines.append(f"")
    candidates = report.get("top30_candidates", [])
    if candidates:
        lines.append(f"  共 {len(candidates)} 只候选股票")
        for i, c in enumerate(candidates[:15], 1):
            boards = ", ".join(c.get("boards", []))
            lines.append(f"  {i:3d}. {c.get('code','-')} {c.get('name','-'):<10} [{boards}]")
    else:
        lines.append(f"  (无候选池数据)")
    lines.append(f"")

    # Agent ranking
    ranking_items = report.get("agent_ranking", [])
    lines.append(f"## 个股分析: ai-hedge-fund")
    lines.append(f"")

    if ranking_items:
        lines.append(f"### Agent 股票排名 Top{min(30, len(ranking_items))}")
        lines.append(f"")
        lines.append(f"  {'排名':>4} {'代码':<8} {'名称':<10} {'来源池':<8} {'趋势分':>6} {'短线分':>6} {'Agent分':>6} {'风险调整':>6} {'风险':<8} {'看多':>3} {'中性':>3} {'看空':>3} {'贡献':>3} {'核心摘要'}")
        lines.append(f"  {'─'*100}")
        for item in ranking_items[:30]:
            src_pool = item.get("source_pool", "?")[:6]
            lines.append(
                f"  {item.get('rank',0):4d} {item.get('code','-'):<8} {item.get('name','-'):<10} "
                f"{src_pool:<8} "
                f"{item.get('trend_score',0):>6.1f} {item.get('burst_score',0):>6.1f} "
                f"{item.get('agent_score',0):>6.1f} {item.get('risk_adjusted_score',0):>6.1f} "
                f"{item.get('risk_level','-'):<8} "
                f"{item.get('bullish_count',0):>3} {item.get('neutral_count',0):>3} {item.get('bearish_count',0):>3} "
                f"{item.get('contributing_agents',0):>3} {item.get('summary','-')[:30]}"
            )
        lines.append(f"")

        # Stock detail for top 10
        lines.append(f"## 个股分析明细 Top{min(10, len(ranking_items))}")
        lines.append(f"")
        for i, item in enumerate(ranking_items[:10], 1):
            lines.append(f"### {i}. {item.get('code','-')} {item.get('name','-')}")
            lines.append(f"")
            lines.append(f"- **来源池**: {item.get('source_pool','-')}")
            lines.append(f"- **来源板块**: {', '.join(item.get('source_boards', []))}")
            lines.append(f"- **趋势分**: {item.get('trend_score',0):.1f}  **短线分**: {item.get('burst_score',0):.1f}")
            lines.append(f"- **Agent分**: {item.get('agent_score',0):.1f}  **风险调整分**: {item.get('risk_adjusted_score',0):.1f}")
            lines.append(f"- **风险等级**: {item.get('risk_level','-')}")
            lines.append(f"- **投票结构**: 看多 {item.get('bullish_count',0)} / 中性 {item.get('neutral_count',0)} / 看空 {item.get('bearish_count',0)}")
            lines.append(f"- **有效贡献 Agent**: {item.get('contributing_agents',0)}")
            # Top positive
            top_pos = item.get("top_positive_agents", [])
            if top_pos:
                lines.append(f"- **主要支持**:")
                for tp in top_pos[:3]:
                    lines.append(f"  - {tp['agent']}: {tp['signal']}, confidence={tp['confidence']:.2f}, weight={tp['weight']:.3f}")
            # Top negative
            top_neg = item.get("top_negative_agents", [])
            if top_neg:
                lines.append(f"- **主要风险**:")
                for tn in top_neg[:3]:
                    lines.append(f"  - {tn['agent']}: {tn['signal']}, confidence={tn['confidence']:.2f}, weight={tn['weight']:.3f}")
            # Fallback
            fb = item.get("fallback_agents", [])
            if fb:
                lines.append(f"- **数据不足/未贡献**: {', '.join(a['agent'] for a in fb[:3])}")
            lines.append(f"")
    else:
        lines.append(f"  ⚠️ 个股 Agent 排名不可用（AIHF 未执行或失败）")
        lines.append(f"")

    # Data sources
    lines.append(f"## 数据源与健康状态")
    lines.append(f"")
    ds = report.get("data_sources", {})
    lines.append(f"  板块评分来源: {ds.get('sector_input_source', '?')}")
    lines.append(f"  Agent preset: {ds.get('agent_preset', '?')}")
    lines.append(f"  LLM enabled: {ds.get('llm_enabled', '?')}")
    lines.append(f"  Agent 数量: {ds.get('agent_count', 0)}")
    lines.append(f"")

    # Warnings
    warnings = report.get("warnings", [])
    if warnings:
        lines.append(f"## 风险提示")
        lines.append(f"")
        for w in warnings:
            lines.append(f"  - {w}")
        lines.append(f"")

    return "\n".join(lines)


# ============================================================
# Main
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="Daily bridge report")
    parser.add_argument("--as-of", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--agent-preset", default="selected", choices=["selected", "selected_plus", "selected_v1", "core", "ashare", "master", "full"])
    parser.add_argument("--agent-mode", default="simulate", choices=["real", "simulate"],
                        help="real: use actual agent functions; simulate: simulated output")
    parser.add_argument("--skip-agent", action="store_true", help="Skip AIHF agent run")
    parser.add_argument("--llm-enabled", action="store_true", help="Enable LLM enhancement")
    parser.add_argument("--llm-model", default="", help="LLM model name (e.g., mimo-v2.5-pro)")
    args = parser.parse_args()

    date = args.as_of
    print(f"{'='*70}")
    print(f"  Phase 24 Bridge Report — {date}")
    print(f"{'='*70}")

    # Load stable sector inputs
    print()
    print("  Loading stable sector inputs...")
    sector_data = load_stable_sectors(date)
    print(f"    Industries: {len(sector_data['industries'])}")
    print(f"    Concepts: {len(sector_data['concepts'])}")

    # Run Phase 24 scripts
    print()
    ranking = None
    if args.skip_agent:
        print("  Skipping AIHF agent run (--skip-agent)")
        bridge_output = {"status": "skipped"}
        top30_path = OUTPUT_DIR / date / "top30_candidates.json"
        if top30_path.exists():
            top30 = json.loads(top30_path.read_text(encoding="utf-8"))
            ranking = {"items": [], "run_meta": {}}
    else:
        bridge_output = run_phase24_scripts(date, args.agent_preset, args.agent_mode, args.llm_model)
        ranking = bridge_output.get("ranking")
        if not ranking and bridge_output.get("status") == "ok":
            # Check if output file exists
            output_path = OUTPUT_DIR / date / "aihf_stock_ranking.json"
            if output_path.exists():
                ranking = json.loads(output_path.read_text(encoding="utf-8"))

    # Build report
    print()
    print("  Building bridge report...")
    report = build_bridge_report(date, sector_data, ranking, bridge_output)

    # Save JSON
    out_dir = OUTPUT_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "daily_bridge_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Save Markdown
    md_content = generate_bridge_markdown(report, date)
    md_path = out_dir / "daily_bridge_report.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Summary
    print()
    print(f"{'='*70}")
    print(f"  Bridge report complete: {date}")
    print(f"  Agents: {report.get('health', {}).get('agent_succeeded', 0)}")
    print(f"  Status: {report.get('health', {}).get('bridge_status', '?')}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
