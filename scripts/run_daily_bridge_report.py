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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.export_top30_candidates import merge_agent_scores_into_candidates  # noqa: E402
AIHEDGE_ROOT = PROJECT_ROOT.parent / "ai-hedge-fund"
SECTOR_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "agent_bridge"
FORWARD_RETURNS_DIR = PROJECT_ROOT / "reports" / "forward_returns"
DEFAULT_STOCK_LIMIT = 30
DEFAULT_AGENT_STOCK_LIMIT = 10


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

    # Fallback: 如果 CSV 为空，从 sector_scores.json 读取概念数据
    if not concepts:
        score_path = PROJECT_ROOT / "reports" / "sector_scores" / date / "sector_scores.json"
        if score_path.exists():
            try:
                with open(score_path, "r", encoding="utf-8") as f:
                    score_data = json.load(f)
                for s in score_data.get("scores", []):
                    if s.get("sector_type") == "concept":
                        concepts.append({
                            "name": s.get("sector_name", ""),
                            "type": "concept",
                            "agent_label": s.get("score_interpretation", {}).get("profile", ""),
                            "composite_score": float(s.get("sector_selection_score", 0) or 0),
                            "trend_score": float(s.get("trend_continuation_score", 0) or 0),
                            "burst_score": float(s.get("short_term_burst_score", 0) or 0),
                        })
            except Exception:
                pass

    return {"industries": industries, "concepts": concepts}


def run_candidate_pool_quality_analysis(date: str) -> Path | None:
    script_path = PROJECT_ROOT / "scripts" / "analyze_candidate_pool_quality.py"
    if not script_path.exists():
        return None
    proc = subprocess.run(
        [sys.executable, str(script_path), "--as-of", date],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    if proc.returncode != 0:
        print(f"  [WARN] candidate pool quality analysis failed: {proc.stderr[:500]}")
        return None
    return OUTPUT_DIR / date / "candidate_pool_quality.json"


def find_forward_returns_file(date: str) -> Path | None:
    candidates = [
        OUTPUT_DIR / date / "forward_returns.json",
        FORWARD_RETURNS_DIR / date / "forward_returns.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def compute_aihf_input_coverage(date: str) -> dict:
    """Compare top30_candidates.json codes with aihf_stock_ranking.json codes.

    Returns a dict with coverage metrics and risk assessment.
    """
    top30_path = OUTPUT_DIR / date / "top30_candidates.json"
    ranking_path = OUTPUT_DIR / date / "aihf_stock_ranking.json"

    result = {
        "aihf_input_candidate_count": 0,
        "top30_candidate_count": 0,
        "agent_stock_limit": 0,
        "agent_analyzed_expected_count": 0,
        "agent_input_limited": False,
        "agent_skipped_count": 0,
        "aihf_input_coverage_ratio": 0.0,
        "excluded_candidate_codes": [],
        "truncation_applied": False,
        "coverage_status": "missing_data",
        "rerun_aihf_bridge_recommended": False,
        "coverage_risk_reason": "",
    }

    if not top30_path.exists():
        result["coverage_risk_reason"] = "top30_candidates.json not found"
        return result

    try:
        top30 = json.loads(top30_path.read_text(encoding="utf-8"))
        candidates = top30.get("candidates", [])
        result["top30_candidate_count"] = len(candidates)
        policy = top30.get("agent_analysis_policy", {})
        expected_codes = {
            str(c.get("code", "")).strip()
            for c in candidates
            if c.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed")
        }
        if not expected_codes:
            expected_codes = {str(c.get("code", "")).strip() for c in candidates if c.get("code")}
        result["agent_stock_limit"] = int(policy.get("agent_stock_limit") or len(expected_codes) or len(candidates))
        result["agent_analyzed_expected_count"] = int(policy.get("agent_analyzed_count") or len(expected_codes))
        result["agent_skipped_count"] = int(policy.get("agent_skipped_count") or 0)
        result["agent_input_limited"] = result["agent_skipped_count"] > 0
        result["aihf_input_candidate_count"] = len(expected_codes)
    except Exception:
        result["coverage_risk_reason"] = "failed to parse top30_candidates.json"
        return result

    if not ranking_path.exists():
        result["coverage_risk_reason"] = "aihf_stock_ranking.json not found"
        return result

    try:
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        items = ranking.get("items", [])
        rank_codes = {str(i.get("code", "")).strip() for i in items if i.get("code")}
        cand_codes = {
            str(c.get("code", "")).strip()
            for c in candidates
            if c.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed")
        }
        if not cand_codes:
            cand_codes = {str(c.get("code", "")).strip() for c in candidates if c.get("code")}

        excluded = sorted(cand_codes - rank_codes)
        result["excluded_candidate_codes"] = excluded
        result["truncation_applied"] = len(excluded) > 0

        if cand_codes:
            ratio = len(cand_codes & rank_codes) / len(cand_codes)
            result["aihf_input_coverage_ratio"] = round(ratio, 4)

            # Risk assessment
            if ratio < 0.5:
                result["coverage_status"] = "stale_or_mismatched_ranking"
                result["rerun_aihf_bridge_recommended"] = True
                result["coverage_risk_reason"] = (
                    f"ranking coverage below 50% ({result['aihf_input_coverage_ratio']:.1%}), "
                    f"likely stale or generated from a different candidate pool"
                )
            elif ratio < 0.8:
                result["coverage_status"] = "partial"
                result["rerun_aihf_bridge_recommended"] = False
                result["coverage_risk_reason"] = (
                    f"ranking covers {result['aihf_input_coverage_ratio']:.1%} of candidates, "
                    f"{len(excluded)} candidates excluded"
                )
            else:
                result["coverage_status"] = "healthy"
                result["rerun_aihf_bridge_recommended"] = False
                result["coverage_risk_reason"] = ""
    except Exception:
        result["coverage_risk_reason"] = "failed to parse aihf_stock_ranking.json"

    return result


def compute_agent_score_coverage_quality(date: str) -> dict:
    """Compute agent_score coverage quality for a single date's candidates.

    Returns a dict with coverage metrics and quality status.
    """
    top30_path = OUTPUT_DIR / date / "top30_candidates.json"

    result = {
        "candidate_count": 0,
        "agent_analyzed_expected_count": 0,
        "agent_skipped_count": 0,
        "agent_input_limited": False,
        "agent_score_present_count": 0,
        "agent_score_missing_count": 0,
        "coverage_ratio": 0.0,
        "missing_codes": [],
        "quality_status": "unknown",
        "notes": [],
    }

    if not top30_path.exists():
        result["notes"].append("top30_candidates.json not found")
        return result

    try:
        top30 = json.loads(top30_path.read_text(encoding="utf-8"))
        candidates = top30.get("candidates", [])
        policy = top30.get("agent_analysis_policy", {})
        expected_codes = {
            str(c.get("code", "")).strip()
            for c in candidates
            if c.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed", "missing_agent_ranking")
        }
        if not expected_codes:
            expected_codes = {str(c.get("code", "")).strip() for c in candidates if c.get("code")}
        result["candidate_count"] = len(candidates)
        result["agent_analyzed_expected_count"] = int(policy.get("agent_analyzed_count") or len(expected_codes))
        result["agent_skipped_count"] = int(policy.get("agent_skipped_count") or 0)
        result["agent_input_limited"] = result["agent_skipped_count"] > 0

        present = 0
        missing_codes = []
        for c in candidates:
            code = str(c.get("code", "")).strip()
            if code not in expected_codes:
                continue
            has_score = (
                c.get("agent_score") is not None
                or c.get("risk_adjusted_score") is not None
                or c.get("ranking_score") is not None
            )
            if has_score:
                present += 1
            elif code:
                missing_codes.append(code)

        result["agent_score_present_count"] = present
        result["agent_score_missing_count"] = len(missing_codes)
        result["missing_codes"] = sorted(missing_codes)

        denominator = len(expected_codes)
        if denominator > 0:
            result["coverage_ratio"] = round(present / denominator, 4)

        # Quality status
        ratio = result["coverage_ratio"]
        if ratio >= 0.8:
            result["quality_status"] = "healthy"
        elif ratio >= 0.5:
            result["quality_status"] = "partial"
        else:
            result["quality_status"] = "poor"
            result["notes"].append(
                "Low agent_score coverage may indicate candidate pool quality risk."
            )

    except Exception as exc:
        result["notes"].append(f"failed to parse top30_candidates.json: {exc}")

    return result


def compute_agent_execution_quality(date: str) -> dict:
    """Diagnose agent execution quality from aihf_stock_ranking.json.

    Checks whether agents actually ran or fell back to defaults.
    """
    ranking_path = OUTPUT_DIR / date / "aihf_stock_ranking.json"

    result = {
        "analyzed_stock_count": 0,
        "succeeded_agent_count": 0,
        "failed_agent_count": 0,
        "fallback_agent_count": 0,
        "default_score_count": 0,
        "default_score_ratio": 0.0,
        "contributing_agent_count_min": 0,
        "contributing_agent_count_max": 0,
        "quality_status": "unknown",
        "notes": [],
    }

    if not ranking_path.exists():
        result["notes"].append("aihf_stock_ranking.json not found")
        return result

    try:
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        items = ranking.get("items", [])
        meta = ranking.get("run_meta", {})

        result["analyzed_stock_count"] = len(items)
        result["succeeded_agent_count"] = len(meta.get("succeeded_agents", []))
        result["failed_agent_count"] = len(meta.get("failed_agents", []))
        result["fallback_agent_count"] = len(meta.get("fallback_agents", []))

        if not items:
            result["quality_status"] = "unknown"
            result["notes"].append("No items in ranking")
            return result

        # Per-stock analysis
        default_count = 0
        contrib_counts = []
        for item in items:
            agent_score = item.get("agent_score")
            contributing = item.get("contributing_agents", 0)
            contrib_counts.append(contributing)
            if agent_score == 50.0 and contributing == 0:
                default_count += 1

        result["default_score_count"] = default_count
        result["default_score_ratio"] = round(default_count / len(items), 4) if items else 0.0
        result["contributing_agent_count_min"] = min(contrib_counts) if contrib_counts else 0
        result["contributing_agent_count_max"] = max(contrib_counts) if contrib_counts else 0

        # Quality status
        failed = result["failed_agent_count"]
        default_ratio = result["default_score_ratio"]
        all_default = default_ratio == 1.0
        no_contrib = result["contributing_agent_count_max"] == 0

        if failed == 0 and default_ratio == 0:
            result["quality_status"] = "healthy"
        elif all_default and no_contrib:
            result["quality_status"] = "fallback_only"
            result["notes"].append("All agent_score values are default (50.0) with no contributing agents.")
        elif default_ratio > 0 or failed > 0:
            result["quality_status"] = "degraded"
            result["notes"].append(f"{default_count}/{len(items)} stocks have default agent_score.")
        else:
            result["quality_status"] = "healthy"

    except Exception as exc:
        result["notes"].append(f"failed to parse aihf_stock_ranking.json: {exc}")

    return result


def run_forward_returns_builder(
    date: str,
    trading_calendar_path: Path | None = None,
    expected_calendar_sha256: str | None = None,
) -> Path | None:
    script_path = PROJECT_ROOT / "scripts" / "build_forward_returns.py"
    candidate_path = OUTPUT_DIR / date / "top30_candidates.json"
    if not script_path.exists() or not candidate_path.exists():
        return None
    if trading_calendar_path is None or not expected_calendar_sha256:
        print("  [WARN] forward returns skipped: versioned trading calendar is required")
        return None
    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--as-of",
            date,
            "--candidate-path",
            str(candidate_path),
            "--trading-calendar-path",
            str(trading_calendar_path),
            "--expected-calendar-sha256",
            expected_calendar_sha256,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    if proc.returncode != 0:
        print(f"  [WARN] forward returns build failed: {proc.stderr[:500]}")
        return None
    return FORWARD_RETURNS_DIR / date / "forward_returns.json"


def run_scoring_calibration(date: str) -> Path | None:
    returns_path = find_forward_returns_file(date)
    if not returns_path:
        return None
    script_path = PROJECT_ROOT / "scripts" / "evaluate_scoring_calibration.py"
    candidate_path = OUTPUT_DIR / date / "top30_candidates.json"
    if not script_path.exists() or not candidate_path.exists():
        return None
    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--as-of",
            date,
            "--candidate-path",
            str(candidate_path),
            "--returns-json",
            str(returns_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    if proc.returncode != 0:
        print(f"  [WARN] scoring calibration failed: {proc.stderr[:500]}")
        return None
    return PROJECT_ROOT / "reports" / "scoring_calibration" / date / "scoring_calibration.json"


def run_phase24_scripts(
    date: str,
    preset: str,
    agent_mode: str = "simulate",
    llm_model: str = "",
    resume: bool = False,
    force_aihf: bool = False,
    stock_limit: int = DEFAULT_STOCK_LIMIT,
    agent_stock_limit: int = DEFAULT_AGENT_STOCK_LIMIT,
    trading_calendar_path: Path | None = None,
    expected_calendar_sha256: str | None = None,
) -> dict:
    """Run the Phase 24 scripts and return results."""
    out_dir = OUTPUT_DIR / date
    top30_existing = out_dir / "top30_candidates.json"
    ranking_existing = out_dir / "aihf_stock_ranking.json"

    # ── Resume path: reuse existing artifacts but still merge + refresh calibration ──
    if resume and not force_aihf and top30_existing.exists() and ranking_existing.exists():
        print("  [resume] Reusing existing top30 + ranking artifacts")
        ranking = json.loads(ranking_existing.read_text(encoding="utf-8"))

        # Merge agent scores even in resume mode
        print("  [resume] Step 2.5: Merging agent scores into candidates...")
        if top30_existing.exists():
            merge_ok = merge_agent_scores_into_candidates(top30_existing, ranking_existing)
            if merge_ok:
                print("    ✅ Agent scores merged (resume)")
            else:
                print("    ⚠️ Agent score merge failed (resume), continuing...")

        # Refresh scoring calibration if forward returns exist
        returns_path = find_forward_returns_file(date)
        if returns_path:
            print("  [resume] Step 2.6: Refreshing scoring calibration...")
            calibration_path = run_scoring_calibration(date)
        else:
            calibration_path = None

        return {
            "status": "ok",
            "ranking": ranking,
            "output_path": ranking_existing,
            "resume_used": True,
            "cache_hits": ["top30_candidates.json", "aihf_stock_ranking.json"],
            "scoring_calibration_path": str(calibration_path) if calibration_path else "",
            "aihf_coverage": compute_aihf_input_coverage(date),
            "stock_limit": stock_limit,
            "agent_stock_limit": agent_stock_limit,
        }

    # ── Normal path ────────────────────────────────────────────────────────

    # Step 1: Export top30
    print("  Step 1: Generating Top30 candidates...")
    top30_path = PROJECT_ROOT / "scripts" / "export_top30_candidates.py"
    proc1 = subprocess.run(
        [
            sys.executable,
            str(top30_path),
            "--as-of",
            date,
            "--stock-limit",
            str(stock_limit),
            "--agent-stock-limit",
            str(agent_stock_limit),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(PROJECT_ROOT),
    )
    if proc1.returncode != 0:
        print(f"  ❌ Top30 export failed: {proc1.stderr}")
        return {"status": "failed", "error": proc1.stderr}

    print(proc1.stdout)
    quality_path = run_candidate_pool_quality_analysis(date)
    if trading_calendar_path is not None and expected_calendar_sha256:
        forward_returns_path = run_forward_returns_builder(
            date,
            trading_calendar_path=trading_calendar_path,
            expected_calendar_sha256=expected_calendar_sha256,
        )
    else:
        forward_returns_path = run_forward_returns_builder(date)
    # NOTE: scoring calibration is deferred to Step 2.6 (after merge)

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
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(AIHEDGE_ROOT),
        timeout=3600,  # 30 stocks with real agents can exceed 30 min
    )
    print(proc2.stdout)
    if proc2.stderr:
        print(f"  ⚠️ AIHF stderr: {proc2.stderr[:500]}")

    if not output_path.exists():
        print(f"  ❌ AIHF ranking not generated")
        return {"status": "failed", "error": "AIHF ranking not generated"}

    # Step 2.5: Merge agent scores back into top30_candidates.json
    print("  Step 2.5: Merging agent scores into candidates...")
    top30_candidates_path = OUTPUT_DIR / date / "top30_candidates.json"
    if top30_candidates_path.exists():
        merge_ok = merge_agent_scores_into_candidates(top30_candidates_path, output_path)
        if merge_ok:
            print("    ✅ Agent scores merged successfully")
        else:
            print("    ⚠️ Agent score merge failed, continuing...")

    # Step 2.6: Scoring calibration (AFTER merge so agent_score is available)
    print("  Step 2.6: Running scoring calibration...")
    calibration_path = run_scoring_calibration(date)

    # Load results
    ranking = json.loads(output_path.read_text(encoding="utf-8"))
    return {
        "status": "ok",
        "ranking": ranking,
        "output_path": output_path,
        "resume_used": False,
        "cache_hits": [],
        "candidate_pool_quality_path": str(quality_path) if quality_path else "",
        "forward_returns_path": str(forward_returns_path) if forward_returns_path else "",
        "scoring_calibration_path": str(calibration_path) if calibration_path else "",
        "aihf_coverage": compute_aihf_input_coverage(date),
        "stock_limit": stock_limit,
        "agent_stock_limit": agent_stock_limit,
    }


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
        "execution": {
            "resume_used": bool(bridge_output.get("resume_used")),
            "cache_hits": bridge_output.get("cache_hits", []),
            "candidate_pool_quality_path": bridge_output.get("candidate_pool_quality_path", ""),
            "forward_returns_path": bridge_output.get("forward_returns_path", ""),
            "scoring_calibration_path": bridge_output.get("scoring_calibration_path", ""),
            "stock_limit": bridge_output.get("stock_limit", DEFAULT_STOCK_LIMIT),
            "agent_stock_limit": bridge_output.get("agent_stock_limit", DEFAULT_AGENT_STOCK_LIMIT),
        },
        "aihf_coverage": bridge_output.get("aihf_coverage", {}),
        "agent_score_coverage_quality": compute_agent_score_coverage_quality(date),
        "agent_execution_quality": compute_agent_execution_quality(date),
        "pipeline_warnings": [],
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

    # Pipeline warnings from coverage quality
    cov_qual = report.get("agent_score_coverage_quality", {})
    if cov_qual.get("quality_status") == "poor":
        report["pipeline_warnings"].append({
            "type": "poor_agent_score_coverage",
            "severity": "warn",
            "message": (
                f"Agent score coverage is poor ({cov_qual.get('coverage_ratio', 0):.1%}). "
                f"Candidate pool quality may be at risk."
            ),
            "coverage_ratio": cov_qual.get("coverage_ratio", 0),
            "missing_count": cov_qual.get("agent_score_missing_count", 0),
        })

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

    # Key findings summary
    industry_top = report.get("industry_top", [])
    concept_top = report.get("concept_top", [])
    candidates = report.get("top30_candidates", [])
    agent_ranking = report.get("agent_ranking", [])

    if industry_top:
        lines.append(f"## 今日关键发现")
        lines.append(f"")
        # Top industry
        top_ind = industry_top[0]
        lines.append(f"**最强板块**: {_field(top_ind, 'name')} ({_field(top_ind, 'agent_label')})")
        # Top stock
        if agent_ranking:
            top_stock = agent_ranking[0]
            lines.append(f"**最强个股**: {top_stock.get('code', '')} {top_stock.get('name', '')} (Agent分: {top_stock.get('agent_score', 0):.1f})")
        # Candidate count
        lines.append(f"**候选池**: {len(candidates)} 只")
        # Agent success rate
        succeeded = health.get('agent_succeeded', 0)
        total_agents = report.get('data_sources', {}).get('agent_count', 0)
        if total_agents > 0:
            lines.append(f"**Agent 成功率**: {succeeded}/{total_agents} ({succeeded/total_agents*100:.0f}%)")
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

    # Top30 candidates - enhanced with new scoring fields
    lines.append(f"## Top30 候选池")
    lines.append(f"")
    lines.append(f"> 以下候选池不带原始排名，仅作为 ai-hedge-fund 的个股分析输入。")
    lines.append(f"")
    candidates = report.get("top30_candidates", [])
    if candidates:
        lines.append(f"  共 {len(candidates)} 只候选股票")
        lines.append(f"")

        # Group by trade_eligibility
        eligibility_groups: dict[str, list] = {}
        for c in candidates:
            elig = c.get("trade_eligibility", "unknown")
            eligibility_groups.setdefault(elig, []).append(c)

        # Display order: focus, watch, backup, avoid, skipped, unknown
        display_order = ["focus", "watch", "backup", "avoid", "skipped_by_agent_stock_limit", "unknown"]
        group_labels = {
            "focus": "重点观察",
            "watch": "观察",
            "backup": "备选",
            "avoid": "回避",
            "skipped_by_agent_stock_limit": "未送Agent(跳过)",
            "unknown": "未分类",
        }

        for elig in display_order:
            group = eligibility_groups.get(elig, [])
            if not group:
                continue
            label = group_labels.get(elig, elig)
            lines.append(f"### {label} ({len(group)} 只)")
            lines.append(f"")
            lines.append(
                f"  {'代码':<8} {'名称':<10} {'板块趋势分':>8} {'板块短线分':>8} "
                f"{'个股短线分':>8} {'个股趋势分':>8} {'龙头分':>8} {'决策分':>8} "
                f"{'风险标签':<16}"
            )
            lines.append(f"  {'─'*100}")
            for c in group:
                boards = ", ".join(c.get("boards", []))
                risk_tags_str = ", ".join(c.get("risk_tags", [])[:2])
                lines.append(
                    f"  {c.get('code','-'):<8} {c.get('name','-'):<10} "
                    f"{c.get('trend_score',0):>8.1f} {c.get('burst_score',0):>8.1f} "
                    f"{c.get('stock_short_score',0):>8.1f} {c.get('stock_trend_score',0):>8.1f} "
                    f"{c.get('sector_leader_score',0):>8.1f} {c.get('decision_score',0):>8.1f} "
                    f"{risk_tags_str:<16}"
                )
            lines.append(f"")
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

    # AIHF coverage
    cov = report.get("aihf_coverage", {})
    if cov:
        lines.append(f"## AIHF Input Coverage")
        lines.append(f"")
        lines.append(f"  Top30 候选数: {cov.get('top30_candidate_count', 0)}")
        lines.append(f"  AIHF 输入数: {cov.get('aihf_input_candidate_count', 0)}")
        lines.append(f"  Ranking 覆盖率: {cov.get('aihf_input_coverage_ratio', 0):.1%}")
        if cov.get("truncation_applied"):
            excluded = cov.get("excluded_candidate_codes", [])
            lines.append(f"  ⚠️ 未覆盖候选 ({len(excluded)}): {', '.join(excluded)}")
        lines.append(f"")

        # Coverage risk assessment
        status = cov.get("coverage_status", "")
        if status:
            status_icon = {
                "healthy": "✅",
                "partial": "⚠️",
                "stale_or_mismatched_ranking": "🔴",
            }.get(status, "❓")
            rerun = cov.get("rerun_aihf_bridge_recommended", False)
            reason = cov.get("coverage_risk_reason", "")

            lines.append(f"## AIHF Coverage Risk")
            lines.append(f"")
            lines.append(f"  {status_icon} **Status**: {status}")
            lines.append(f"  **Coverage**: {cov.get('aihf_input_coverage_ratio', 0):.1%}")
            lines.append(f"  **Rerun recommended**: {'Yes' if rerun else 'No'}")
            if reason:
                lines.append(f"  **Reason**: {reason}")
            excluded = cov.get("excluded_candidate_codes", [])
            if excluded:
                lines.append(f"  **Excluded candidates**: {len(excluded)}")
            lines.append(f"")

    # Agent Score Coverage Quality
    cov_qual = report.get("agent_score_coverage_quality", {})
    if cov_qual and cov_qual.get("candidate_count", 0) > 0:
        lines.append(f"## Agent Score Coverage Quality")
        lines.append(f"")
        status = cov_qual.get("quality_status", "unknown")
        status_icon = {"healthy": "✅", "partial": "⚠️", "poor": "🔴"}.get(status, "❓")
        lines.append(f"  {status_icon} **Status**: {status}")
        lines.append(f"  **Coverage**: {cov_qual.get('agent_score_present_count', 0)}/{cov_qual.get('candidate_count', 0)} ({cov_qual.get('coverage_ratio', 0):.1%})")
        missing = cov_qual.get("missing_codes", [])
        if missing:
            lines.append(f"  **Missing agent_score** ({len(missing)}): {', '.join(missing)}")
        for note in cov_qual.get("notes", []):
            lines.append(f"  > ⚠️ {note}")
        lines.append(f"")

    # Agent Execution Quality
    exec_qual = report.get("agent_execution_quality", {})
    if exec_qual and exec_qual.get("analyzed_stock_count", 0) > 0:
        lines.append(f"## Agent Execution Quality")
        lines.append(f"")
        status = exec_qual.get("quality_status", "unknown")
        status_icon = {"healthy": "✅", "degraded": "⚠️", "fallback_only": "🔴"}.get(status, "❓")
        lines.append(f"  {status_icon} **Status**: {status}")
        lines.append(f"  **Stocks analyzed**: {exec_qual.get('analyzed_stock_count', 0)}")
        lines.append(f"  **Agents succeeded**: {exec_qual.get('succeeded_agent_count', 0)}")
        lines.append(f"  **Agents failed**: {exec_qual.get('failed_agent_count', 0)}")
        lines.append(f"  **Default score stocks**: {exec_qual.get('default_score_count', 0)} ({exec_qual.get('default_score_ratio', 0):.1%})")
        for note in exec_qual.get("notes", []):
            lines.append(f"  > ⚠️ {note}")
        lines.append(f"")

    # Warnings
    warnings = report.get("warnings", [])
    if warnings:
        lines.append(f"## 风险提示")
        lines.append(f"")
        for w in warnings:
            lines.append(f"  - {w}")
        lines.append(f"")

    # Pipeline warnings
    pipeline_warnings = report.get("pipeline_warnings", [])
    if pipeline_warnings:
        lines.append(f"## Pipeline Warnings")
        lines.append(f"")
        for pw in pipeline_warnings:
            severity = pw.get("severity", "warn").upper()
            lines.append(f"  [{severity}] {pw.get('type', 'unknown')}: {pw.get('message', '')}")
        lines.append(f"")

    # Agent Score Health Check
    health_check = report.get("agent_score_health_check", {})
    if health_check and health_check.get("status") == "ok":
        lines.append(f"## Agent Score Health Check")
        lines.append(f"")
        overall = health_check.get("overall_status", "unknown")
        overall_icon = {"healthy": "✅", "monitor": "⚠️", "risk": "🔴"}.get(overall, "❓")
        lines.append(f"  {overall_icon} **Overall Status**: {overall}")
        lines.append(f"  **Coverage Status**: {health_check.get('coverage_status', 'unknown')}")
        lines.append(f"  **Execution Quality**: {health_check.get('execution_quality_status', 'unknown')}")
        lines.append(f"  **Pipeline Warnings**: {health_check.get('pipeline_warnings_count', 0)}")
        if health_check.get("health_report_path"):
            lines.append(f"  **Health Report**: {health_check['health_report_path']}")
        lines.append(f"")

    return "\n".join(lines)


def _run_agent_score_health_check(date: str) -> dict:
    """Run the agent score health check pipeline for a single date.

    Steps:
    1. analyze_agent_score_merge_coverage.py --dates <date> --apply
    2. summarize_scoring_calibration.py
    3. export_agent_score_health_report.py

    Returns a dict with health check results.
    """
    result = {
        "status": "ok",
        "health_report_path": "",
        "overall_status": "unknown",
        "pipeline_warnings_count": 0,
        "coverage_status": "unknown",
        "execution_quality_status": "unknown",
    }

    # Step 1: Merge coverage analysis
    print("    Step 1: Analyzing merge coverage...")
    merge_script = PROJECT_ROOT / "scripts" / "analyze_agent_score_merge_coverage.py"
    if merge_script.exists():
        proc = subprocess.run(
            [sys.executable, str(merge_script), "--dates", date, "--apply"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        if proc.returncode == 0:
            print(f"    ✅ Merge coverage analyzed")
        else:
            print(f"    ⚠️ Merge coverage analysis failed: {proc.stderr[:200]}")

    # Step 2: Find aggregate path for calibration
    aggregate_dir = PROJECT_ROOT / "reports" / "scoring_calibration" / "aggregate"
    aggregate_path = None
    if aggregate_dir.exists():
        for d in sorted(aggregate_dir.iterdir()):
            if d.is_dir() and (d / "aggregate_scoring_calibration.json").exists():
                aggregate_path = d / "aggregate_scoring_calibration.json"

    # Step 3: Run summary
    if aggregate_path:
        print("    Step 2: Generating scoring summary...")
        summary_script = PROJECT_ROOT / "scripts" / "summarize_scoring_calibration.py"
        if summary_script.exists():
            proc = subprocess.run(
                [
                    sys.executable, str(summary_script),
                    "--aggregate-path", str(aggregate_path),
                    "--bridge-root", str(OUTPUT_DIR),
                    "--min-aihf-coverage", "0.5",
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(PROJECT_ROOT),
            )
            if proc.returncode == 0:
                print(f"    ✅ Summary generated")
            else:
                print(f"    ⚠️ Summary failed: {proc.stderr[:200]}")

        # Step 4: Generate health report
        summary_json = aggregate_path.parent / "scoring_calibration_summary.json"
        if summary_json.exists():
            print("    Step 3: Generating health report...")
            health_script = PROJECT_ROOT / "scripts" / "export_agent_score_health_report.py"
            health_output = PROJECT_ROOT / "reports" / "scoring_calibration" / "agent_score_health"
            if health_script.exists():
                proc = subprocess.run(
                    [
                        sys.executable, str(health_script),
                        "--summary-path", str(summary_json),
                        "--output-dir", str(health_output),
                    ],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    cwd=str(PROJECT_ROOT),
                )
                if proc.returncode == 0:
                    print(f"    ✅ Health report generated")
                    health_json = health_output / "agent_score_health_report.json"
                    if health_json.exists():
                        health_data = json.loads(health_json.read_text(encoding="utf-8"))
                        result["overall_status"] = health_data.get("overall_status", "unknown")
                        result["health_report_path"] = str(health_json)
                        result["pipeline_warnings_count"] = len(health_data.get("pipeline_warnings", []))

                        coverage_quality = health_data.get("coverage_quality", {})
                        if coverage_quality.get("poor_dates"):
                            result["coverage_status"] = "poor"
                        elif coverage_quality.get("partial_dates"):
                            result["coverage_status"] = "partial"
                        elif coverage_quality.get("healthy_dates"):
                            result["coverage_status"] = "healthy"

                        execution_quality = health_data.get("execution_quality", {})
                        if execution_quality.get("fallback_only_dates"):
                            result["execution_quality_status"] = "fallback_only"
                        elif execution_quality.get("degraded_dates"):
                            result["execution_quality_status"] = "degraded"
                        elif execution_quality.get("healthy_dates"):
                            result["execution_quality_status"] = "healthy"

                        # Extract coverage and execution status from headline findings
                        findings = health_data.get("headline_findings", [])
                        for f in findings:
                            if "coverage" in f.lower() and "healthy" in f.lower():
                                result["coverage_status"] = "healthy"
                            elif "execution" in f.lower() and "healthy" in f.lower():
                                result["execution_quality_status"] = "healthy"
                else:
                    print(f"    ⚠️ Health report failed: {proc.stderr[:200]}")
    else:
        print("    ⚠️ No aggregate calibration found, skipping summary/health")

    return result


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
    parser.add_argument("--resume", action="store_true", help="Reuse existing top30/ranking intermediate artifacts when available")
    parser.add_argument("--force-aihf", action="store_true", help="Force re-run AIHF bridge even if ranking exists (keeps top30 unchanged)")
    parser.add_argument("--run-agent-score-health", action="store_true", help="Run agent score health check after bridge completes")
    parser.add_argument("--stock-limit", type=int, default=DEFAULT_STOCK_LIMIT, help="Candidate pool size kept in top30_candidates.json")
    parser.add_argument("--agent-stock-limit", type=int, default=DEFAULT_AGENT_STOCK_LIMIT, help="Max stocks sent to AIHF agents")
    parser.add_argument("--llm-enabled", action="store_true", help="Enable LLM enhancement")
    parser.add_argument("--llm-model", default="", help="LLM model name (e.g., mimo-v2.5-pro)")
    parser.add_argument("--trading-calendar-path", type=Path, default=None)
    parser.add_argument("--expected-calendar-sha256", default=None)
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
        bridge_output = run_phase24_scripts(
            date,
            args.agent_preset,
            args.agent_mode,
            args.llm_model,
            resume=args.resume,
            force_aihf=args.force_aihf,
            stock_limit=args.stock_limit,
            agent_stock_limit=args.agent_stock_limit,
            trading_calendar_path=args.trading_calendar_path,
            expected_calendar_sha256=args.expected_calendar_sha256,
        )
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

    # Agent score health check (optional)
    if args.run_agent_score_health:
        print()
        print("  Running agent score health check...")
        health_result = _run_agent_score_health_check(date)
        report["agent_score_health_check"] = health_result

        # Re-save JSON with health check result
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        # Re-save Markdown with health check section
        md_content = generate_bridge_markdown(report, date)
        md_path.write_text(md_content, encoding="utf-8")

        health_status = health_result.get("overall_status", "unknown")
        health_icon = {"healthy": "✅", "monitor": "⚠️", "risk": "🔴"}.get(health_status, "❓")
        print(f"  {health_icon} Agent score health: {health_status}")
        if health_status == "risk":
            print(f"  ⚠️ WARN: Health check returned RISK — review recommended but pipeline continues")

    # Summary
    print()
    print(f"{'='*70}")
    print(f"  Bridge report complete: {date}")
    print(f"  Agents: {report.get('health', {}).get('agent_succeeded', 0)}")
    print(f"  Status: {report.get('health', {}).get('bridge_status', '?')}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
