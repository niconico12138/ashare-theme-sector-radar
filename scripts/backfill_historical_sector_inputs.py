#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史 sector_inputs 回填脚本

从 reports/sector_scores/ 构造 export_top30_candidates.py 需要的:
- reports/full90/sector_research/<date>/sector_research.json
- reports/full_concept/unified_rank/<date>/concept_unified_rank.csv

用法:
  python scripts/backfill_historical_sector_inputs.py \
    --start-date 2026-06-01 --end-date 2026-06-28 --force

  python scripts/backfill_historical_sector_inputs.py \
    --start-date 2026-06-01 --end-date 2026-06-28 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECTOR_SCORES_DIR = PROJECT_ROOT / "reports" / "sector_scores"
SECTOR_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
BACKFILL_OUTPUT_DIR = PROJECT_ROOT / "reports" / "selection_validation" / "backfill_sector_inputs"

DATE_RE = re.compile(r"^2026-\d{2}-\d{2}$")

# Profile → consensus_label mapping
PROFILE_TO_LABEL = {
    "trend_and_burst_confirmed": "trend_confirmed",
    "trend_confirmed": "trend_confirmed",
    "trend_confirmed_but_strength_limited": "trend_confirmed_but_strength_limited",
    "short_burst_only": "defensive_watch",
    "defensive_stable_watch": "defensive_stable_watch",
    "defensive_watch": "defensive_watch",
    "weak_or_cooling": "weak_or_avoid",
    "weak_or_unclear": "weak_or_avoid",
    "neutral": "conflicted",
    "conflicted": "conflicted",
}


# ======================================================================
# DATE SCANNING
# ======================================================================

def scan_dates(start_date: str, end_date: str) -> list[dict]:
    """Scan sector_scores for valid YYYY-MM-DD dates."""
    dates = []
    if not SECTOR_SCORES_DIR.exists():
        return dates

    for item in sorted(SECTOR_SCORES_DIR.iterdir()):
        if not item.is_dir():
            continue
        if not DATE_RE.match(item.name):
            continue
        if not (start_date <= item.name <= end_date):
            continue

        scores_path = item / "sector_scores.json"
        has_scores = scores_path.exists()

        research_path = SECTOR_RESEARCH_DIR / item.name / "sector_research.json"
        has_research = research_path.exists()

        concept_path = CONCEPT_RANK_DIR / item.name / "concept_unified_rank.csv"
        has_concept = concept_path.exists()

        # Check if scores has concepts
        has_concept_in_scores = False
        if has_scores:
            try:
                data = json.loads(scores_path.read_text(encoding="utf-8"))
                has_concept_in_scores = any(
                    s.get("sector_type") == "concept" for s in data.get("scores", [])
                )
            except Exception:
                pass

        should_build_research = has_scores and not has_research
        should_build_concept = has_scores and not has_concept

        dates.append({
            "date": item.name,
            "has_sector_scores": has_scores,
            "has_existing_research": has_research,
            "has_existing_concept": has_concept,
            "has_concept_in_scores": has_concept_in_scores,
            "should_build_research": should_build_research,
            "should_build_concept": should_build_concept,
        })

    return dates


# ======================================================================
# SECTOR_RESEARCH BUILDER
# ======================================================================

def _derive_consensus_label(score_entry: dict) -> str:
    """Derive consensus_label from sector_score entry."""
    profile = score_entry.get("score_interpretation", {}).get("profile", "")
    if profile in PROFILE_TO_LABEL:
        return PROFILE_TO_LABEL[profile]

    # Fallback: derive from scores
    trend = _safe_float(score_entry.get("trend_continuation_score", 0))
    burst = _safe_float(score_entry.get("short_term_burst_score", 0))
    selection = _safe_float(score_entry.get("sector_selection_score", 0))

    if trend > 70 and burst > 60:
        return "trend_confirmed"
    elif trend > 60:
        return "trend_confirmed_but_strength_limited"
    elif burst > 70:
        return "defensive_watch"
    elif selection < 40:
        return "weak_or_avoid"
    else:
        return "conflicted"


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def build_sector_research(date: str, scores_data: dict) -> dict:
    """Build sector_research.json from sector_scores.json."""
    results = []
    for score in scores_data.get("scores", []):
        sector_type = score.get("sector_type", "industry")
        # Only include industry for sector_research (matching original format)
        if sector_type != "industry":
            continue

        # Normalize scores to 0-1 range (sector_scores uses 0-100)
        selection_score = _safe_float(score.get("sector_selection_score", 0))
        trend_score = _safe_float(score.get("trend_continuation_score", 0))
        burst_score = _safe_float(score.get("short_term_burst_score", 0))

        ranking_score = round(min(1.0, selection_score / 100.0), 3)
        opportunity_score = round(min(1.0, (burst_score * 0.4 + trend_score * 0.6) / 100.0), 3)
        evidence_score = round(min(1.0, trend_score / 100.0), 3)

        # Risk control: 100 - risk_penalty, or derive from data quality
        risk_penalty = 0
        breakdown = score.get("trend_breakdown", {})
        if isinstance(breakdown, dict):
            risk_penalty = _safe_float(breakdown.get("risk_penalty", 0))
        risk_control_score = round(min(1.0, max(0.0, (100 - risk_penalty) / 100.0)), 3)

        # Confidence from history coverage
        history_coverage = _safe_float(score.get("history_coverage_ratio", 0.5))
        actual_days = _safe_float(score.get("actual_history_days", 10))
        confidence_score = round(min(1.0, history_coverage * min(1.0, actual_days / 20.0)), 3)

        consensus_label = _derive_consensus_label(score)

        results.append({
            "sector_name": score.get("sector_name", ""),
            "sector_type": sector_type,
            "consensus_label": consensus_label,
            "confirm_level": "high" if consensus_label == "trend_confirmed" else "medium",
            "evidence_score": evidence_score,
            "opportunity_score": opportunity_score,
            "risk_control_score": risk_control_score,
            "confidence_score": confidence_score,
            "calibrated_confidence_score": confidence_score,
            "ranking_score": ranking_score,
            "score_interpretation": score.get("score_interpretation", {}),
            "source_fields": {
                "sector_selection_score": selection_score,
                "trend_continuation_score": trend_score,
                "short_term_burst_score": burst_score,
                "history_days": score.get("history_days"),
                "actual_history_days": score.get("actual_history_days"),
                "history_coverage_ratio": score.get("history_coverage_ratio"),
            },
        })

    # Sort by ranking_score descending
    results.sort(key=lambda x: x["ranking_score"], reverse=True)

    return {
        "as_of_date": date,
        "sector_type": "industry",
        "report_type": "sector_research",
        "version": "historical_backfill_v1",
        "source": "sector_scores_backfill",
        "inputs": {
            "sector_scores_date": date,
            "backfill_timestamp": datetime.now().isoformat(),
        },
        "research_results": results,
        "warnings": [],
        "disclaimer": "Historical backfill from sector_scores. Not equivalent to live research output.",
    }


# ======================================================================
# CONCEPT_UNIFIED_RANK BUILDER
# ======================================================================

def build_concept_rank(date: str, scores_data: dict) -> list[dict]:
    """Build concept_unified_rank entries from sector_scores.json."""
    concepts = []
    for score in scores_data.get("scores", []):
        if score.get("sector_type") != "concept":
            continue

        selection_score = _safe_float(score.get("sector_selection_score", 0))
        trend_score = _safe_float(score.get("trend_continuation_score", 0))
        burst_score = _safe_float(score.get("short_term_burst_score", 0))

        concept_final_rank_score = round(selection_score, 2)
        consensus_label = _derive_consensus_label(score)

        history_days = score.get("history_days", 20)
        actual_days = score.get("actual_history_days", 10)
        coverage = _safe_float(score.get("history_coverage_ratio", 0.5))

        concepts.append({
            "sector_name": score.get("sector_name", ""),
            "concept_final_rank_score": concept_final_rank_score,
            "trend_continuation_score": round(trend_score, 2),
            "short_term_burst_score": round(burst_score, 2),
            "agent_consensus_label": consensus_label,
            "agent_ranking_score": round(min(100, selection_score * 1.0), 1),
            "agent_opportunity_score": round(min(100, (burst_score * 0.4 + trend_score * 0.6)), 1),
            "risk_control_score": 100.0,
            "confidence_score": round(min(1.0, coverage * min(1.0, actual_days / 20.0)), 2),
            "evidence_score": round(trend_score, 1),
            "history_days": history_days,
            "actual_history_days": actual_days,
            "trend_window_status": score.get("trend_window_status", "ok"),
        })

    concepts.sort(key=lambda x: x["concept_final_rank_score"], reverse=True)
    return concepts


def write_concept_csv(path: Path, concepts: list[dict]) -> None:
    """Write concept_unified_rank.csv."""
    fieldnames = [
        "rank", "sector_name", "concept_final_rank_score",
        "trend_continuation_score", "trend_level_cn",
        "short_term_burst_score", "burst_level_cn",
        "agent_consensus_label", "agent_ranking_score", "agent_opportunity_score",
        "risk_control_score", "confidence_score", "evidence_score",
        "history_days", "actual_history_days", "trend_window_status",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, c in enumerate(concepts, 1):
            row = dict(c)
            row["rank"] = i
            # Add level_cn fields
            trend_score = _safe_float(c.get("trend_continuation_score", 0))
            burst_score = _safe_float(c.get("short_term_burst_score", 0))
            row["trend_level_cn"] = _trend_level_cn(trend_score)
            row["burst_level_cn"] = _burst_level_cn(burst_score)
            writer.writerow(row)


def _trend_level_cn(score: float) -> str:
    if score >= 80:
        return "重点观察"
    elif score >= 60:
        return "趋势向好"
    elif score >= 40:
        return "中性"
    else:
        return "弱势"


def _burst_level_cn(score: float) -> str:
    if score >= 80:
        return "短线活跃"
    elif score >= 60:
        return "短线偏强"
    elif score >= 40:
        return "短线中性"
    else:
        return "短线降温"


# ======================================================================
# COMPATIBILITY CHECK
# ======================================================================

def check_compatibility(date: str) -> dict:
    """Verify generated files can be read by load_stable_sectors."""
    result = {"date": date, "research_ok": False, "concept_ok": False, "errors": []}

    # Check sector_research.json
    research_path = SECTOR_RESEARCH_DIR / date / "sector_research.json"
    if research_path.exists():
        try:
            data = json.loads(research_path.read_text(encoding="utf-8"))
            industries = [
                r for r in data.get("research_results", [])
                if r.get("sector_type") == "industry"
            ]
            if industries:
                result["research_ok"] = True
                result["industry_count"] = len(industries)
            else:
                result["errors"].append("no industry entries in research_results")
        except Exception as e:
            result["errors"].append(f"research parse error: {e}")
    else:
        result["errors"].append("sector_research.json missing")

    # Check concept_unified_rank.csv
    concept_path = CONCEPT_RANK_DIR / date / "concept_unified_rank.csv"
    if concept_path.exists():
        try:
            with open(concept_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                result["concept_ok"] = True
                result["concept_count"] = len(rows)
        except Exception as e:
            result["errors"].append(f"concept csv parse error: {e}")
    else:
        result["errors"].append("concept_unified_rank.csv missing")

    return result


# ======================================================================
# REPORT
# ======================================================================

def build_report(
    plan: list[dict],
    results: dict[str, dict],
    run_config: dict,
) -> dict:
    """Build backfill summary report."""
    date_status = []
    failures = []
    warnings = []
    research_count = 0
    concept_count = 0
    compat_results = []

    for entry in plan:
        date = entry["date"]
        r = results.get(date, {})

        research_status = "ok" if r.get("research_ok") else (
            "skipped_exists" if entry["has_existing_research"] else (
                "skipped_no_data" if not entry["has_sector_scores"] else "failed"
            )
        )
        concept_status = "ok" if r.get("concept_ok") else (
            "skipped_exists" if entry["has_existing_concept"] else (
                "skipped_no_concept" if not entry["has_concept_in_scores"] else "failed"
            )
        )

        if research_status == "ok":
            research_count += 1
        if concept_status == "ok":
            concept_count += 1

        date_status.append({
            "date": date,
            "research_status": research_status,
            "concept_status": concept_status,
            "has_concept_in_scores": entry["has_concept_in_scores"],
        })

        if r.get("errors"):
            failures.append({"date": date, "errors": r["errors"]})
        if r.get("warnings"):
            warnings.extend([{"date": date, "warning": w} for w in r["warnings"]])

        # Compatibility check
        if research_status == "ok" or entry["has_existing_research"]:
            compat = check_compatibility(date)
            compat_results.append(compat)

    compat_ok = sum(1 for c in compat_results if c["research_ok"])
    compat_total = len(compat_results)

    return {
        "run_config": run_config,
        "date_plan": [
            {"date": e["date"], "has_scores": e["has_sector_scores"],
             "should_build_research": e["should_build_research"],
             "should_build_concept": e["should_build_concept"]}
            for e in plan
        ],
        "build_summary": {
            "total_dates": len(plan),
            "research_built": research_count,
            "concept_built": concept_count,
        },
        "per_date_status": date_status,
        "generated_sector_research_count": research_count,
        "generated_concept_rank_count": concept_count,
        "compatibility_check_summary": {
            "total_checked": compat_total,
            "research_ok": compat_ok,
            "all_ok": compat_ok == compat_total and compat_total > 0,
        },
        "failures": failures,
        "warnings": warnings,
        "next_steps": [
            "Run backfill_historical_unified_and_validation.py to generate unified reports + top30 + validation",
            "Then run run_selection_validation_batch.py to build aggregate",
        ],
    }


def generate_markdown(report: dict) -> str:
    """Generate markdown report."""
    lines = []
    rc = report.get("run_config", {})
    lines.append(f"# Sector Inputs Backfill Report — {rc.get('start_date', '?')} to {rc.get('end_date', '?')}")
    lines.append(f"")

    # 1. Run Config
    lines.append(f"## 1. Run Config")
    lines.append(f"")
    for k, v in rc.items():
        lines.append(f"- {k}: {v}")
    lines.append(f"")

    # 2. Date Plan
    lines.append(f"## 2. Date Plan")
    lines.append(f"")
    lines.append(f"| {'Date':<12} {'Has Scores':>10} {'Build Research':>14} {'Build Concept':>13} |")
    lines.append(f"|{'─'*14}|{'─'*12}|{'─'*16}|{'─'*15}|")
    for entry in report.get("date_plan", []):
        lines.append(
            f"| {entry['date']:<12} {str(entry['has_scores']):>10} "
            f"{str(entry['should_build_research']):>14} {str(entry['should_build_concept']):>13} |"
        )
    lines.append(f"")

    # 3. Build Summary
    bs = report.get("build_summary", {})
    lines.append(f"## 3. Build Summary")
    lines.append(f"")
    lines.append(f"- Total dates: {bs.get('total_dates', 0)}")
    lines.append(f"- sector_research built: {report.get('generated_sector_research_count', 0)}")
    lines.append(f"- concept_unified_rank built: {report.get('generated_concept_rank_count', 0)}")
    lines.append(f"")

    # 4. Per-Date Status
    lines.append(f"## 4. Per-Date Status")
    lines.append(f"")
    lines.append(f"| {'Date':<12} {'Research':<16} {'Concept':<16} {'Has Concept Data':>16} |")
    lines.append(f"|{'─'*14}|{'─'*18}|{'─'*18}|{'─'*18}|")
    for row in report.get("per_date_status", []):
        lines.append(
            f"| {row['date']:<12} {row['research_status']:<16} {row['concept_status']:<16} "
            f"{str(row['has_concept_in_scores']):>16} |"
        )
    lines.append(f"")

    # 5. Compatibility
    cc = report.get("compatibility_check_summary", {})
    lines.append(f"## 5. Compatibility Check")
    lines.append(f"")
    lines.append(f"- Checked: {cc.get('total_checked', 0)} dates")
    lines.append(f"- Research OK: {cc.get('research_ok', 0)}")
    lines.append(f"- All OK: {cc.get('all_ok', False)}")
    lines.append(f"")

    # 6. Failures
    failures = report.get("failures", [])
    lines.append(f"## 6. Failures")
    lines.append(f"")
    if failures:
        for f in failures:
            for err in f["errors"]:
                lines.append(f"- **{f['date']}**: {err}")
    else:
        lines.append(f"- No failures")
    lines.append(f"")

    # 7. Next Steps
    lines.append(f"## 7. Next Steps")
    lines.append(f"")
    for step in report.get("next_steps", []):
        lines.append(f"- {step}")
    lines.append(f"")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Backfill historical sector inputs")
    parser.add_argument("--start-date", default="2026-06-01")
    parser.add_argument("--end-date", default="2026-06-28")
    parser.add_argument("--dates", nargs="*", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-dates", type=int, default=None)
    parser.add_argument("--min-sector-score", type=float, default=0)
    parser.add_argument("--industry-top-n", type=int, default=10)
    parser.add_argument("--concept-top-n", type=int, default=20)
    args = parser.parse_args()

    # Scan dates
    if args.dates:
        plan = []
        for d in args.dates:
            scanned = scan_dates(d, d)
            if scanned:
                plan.append(scanned[0])
            else:
                # Create minimal plan entry
                plan.append({
                    "date": d,
                    "has_sector_scores": False,
                    "has_existing_research": False,
                    "has_existing_concept": False,
                    "has_concept_in_scores": False,
                    "should_build_research": False,
                    "should_build_concept": False,
                })
    else:
        plan = scan_dates(args.start_date, args.end_date)

    if args.max_dates:
        plan = plan[:args.max_dates]

    print(f"{'='*60}")
    print(f"  Historical Sector Inputs Backfill")
    print(f"  Range: {args.start_date} to {args.end_date}")
    print(f"  Dates found: {len(plan)}")
    print(f"  Force: {args.force}")
    print(f"  Dry-run: {args.dry_run}")
    print(f"{'='*60}")

    # Print plan
    need_research = sum(1 for p in plan if p["should_build_research"])
    need_concept = sum(1 for p in plan if p["should_build_concept"])
    print(f"\n  📋 Plan:")
    print(f"    - Need sector_research: {need_research}")
    print(f"    - Need concept_rank: {need_concept}")

    if args.dry_run:
        print(f"\n  🏃 DRY RUN — no files written")
        for p in plan:
            flags = []
            if p["should_build_research"]:
                flags.append("research")
            elif p["has_existing_research"]:
                flags.append("skip(research exists)")
            if p["should_build_concept"]:
                flags.append("concept")
            elif p["has_existing_concept"]:
                flags.append("skip(concept exists)")
            elif not p["has_concept_in_scores"]:
                flags.append("skip(no concept data)")
            if not p["has_sector_scores"]:
                flags.append("skip(no scores)")
            if not flags:
                flags.append("skip (all done)")
            print(f"    {p['date']}: {', '.join(flags)}")
        return

    # Execute
    results: dict[str, dict] = {}
    for i, entry in enumerate(plan):
        date = entry["date"]
        print(f"\n{'─'*60}")
        print(f"  [{i+1}/{len(plan)}] {date}")
        print(f"{'─'*60}")

        results[date] = {"errors": [], "warnings": []}

        if not entry["has_sector_scores"]:
            print(f"  ⏭️  No sector_scores, skipping")
            continue

        # Load sector_scores
        scores_path = SECTOR_SCORES_DIR / date / "sector_scores.json"
        try:
            scores_data = json.loads(scores_path.read_text(encoding="utf-8"))
        except Exception as e:
            results[date]["errors"].append(f"Failed to load sector_scores: {e}")
            print(f"  ❌ Failed to load sector_scores: {e}")
            continue

        # Build sector_research
        if entry["should_build_research"]:
            print(f"  📦 Building sector_research.json...")
            research = build_sector_research(date, scores_data)
            industry_count = len(research.get("research_results", []))

            if industry_count == 0:
                results[date]["warnings"].append("No industry sectors found")
                print(f"  ⚠️  No industry sectors found")

            # Apply min-sector-score filter
            if args.min_sector_score > 0:
                before = len(research["research_results"])
                research["research_results"] = [
                    r for r in research["research_results"]
                    if r["ranking_score"] * 100 >= args.min_sector_score
                ]
                after = len(research["research_results"])
                if before != after:
                    print(f"  🔍 Filtered: {before} → {after} (min_score={args.min_sector_score})")

            # Apply top-n
            if args.industry_top_n and len(research["research_results"]) > args.industry_top_n:
                research["research_results"] = research["research_results"][:args.industry_top_n]
                print(f"  📊 Trimmed to top {args.industry_top_n}")

            # Save
            out_dir = SECTOR_RESEARCH_DIR / date
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "sector_research.json"
            out_path.write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")

            # Generate markdown summary
            md_lines = [f"# Sector Research (Backfill) — {date}", ""]
            md_lines.append(f"Source: sector_scores.json (historical_backfill_v1)")
            md_lines.append(f"Industries: {len(research['research_results'])}")
            md_lines.append("")
            for j, r in enumerate(research["research_results"][:10], 1):
                md_lines.append(f"{j}. {r['sector_name']} — {r['consensus_label']} (rank={r['ranking_score']:.3f})")
            (out_dir / "sector_research.md").write_text("\n".join(md_lines), encoding="utf-8")

            results[date]["research_ok"] = True
            print(f"  ✅ sector_research.json: {industry_count} industries")
        elif entry["has_existing_research"]:
            print(f"  ⏭️  sector_research exists, skipping")
            results[date]["research_ok"] = True
        else:
            print(f"  ⏭️  No sector_scores, skipping research")

        # Build concept rank
        if entry["should_build_concept"]:
            concepts = build_concept_rank(date, scores_data)
            if concepts:
                print(f"  📦 Building concept_unified_rank.csv ({len(concepts)} concepts)...")
                # Apply top-n
                if args.concept_top_n and len(concepts) > args.concept_top_n:
                    concepts = concepts[:args.concept_top_n]

                out_dir = CONCEPT_RANK_DIR / date
                out_dir.mkdir(parents=True, exist_ok=True)

                csv_path = out_dir / "concept_unified_rank.csv"
                write_concept_csv(csv_path, concepts)

                json_path = out_dir / "concept_unified_rank.json"
                json_path.write_text(json.dumps({
                    "as_of_date": date,
                    "concept_count": len(concepts),
                    "concepts": concepts,
                    "source": "sector_scores_backfill",
                }, ensure_ascii=False, indent=2), encoding="utf-8")

                md_lines = [f"# Concept Unified Rank (Backfill) — {date}", ""]
                md_lines.append(f"Concepts: {len(concepts)}")
                md_lines.append("")
                for j, c in enumerate(concepts[:10], 1):
                    md_lines.append(f"{j}. {c['sector_name']} — score={c['concept_final_rank_score']}")
                (out_dir / "concept_unified_rank.md").write_text("\n".join(md_lines), encoding="utf-8")

                results[date]["concept_ok"] = True
                print(f"  ✅ concept_unified_rank.csv: {len(concepts)} concepts")
            else:
                results[date]["warnings"].append("No concept sectors in sector_scores")
                results[date]["concept_ok"] = True  # Not an error, just no data
                print(f"  ⚠️  No concept sectors, writing empty CSV")

                # Write empty CSV with headers
                out_dir = CONCEPT_RANK_DIR / date
                out_dir.mkdir(parents=True, exist_ok=True)
                csv_path = out_dir / "concept_unified_rank.csv"
                fieldnames = [
                    "rank", "sector_name", "concept_final_rank_score",
                    "trend_continuation_score", "trend_level_cn",
                    "short_term_burst_score", "burst_level_cn",
                    "agent_consensus_label", "agent_ranking_score", "agent_opportunity_score",
                    "risk_control_score", "confidence_score", "evidence_score",
                    "history_days", "actual_history_days", "trend_window_status",
                ]
                with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
        elif entry["has_existing_concept"]:
            print(f"  ⏭️  concept_unified_rank exists, skipping")
            results[date]["concept_ok"] = True
        else:
            print(f"  ⏭️  No concept data, skipping")

    # Build report
    run_config = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "force": args.force,
        "min_sector_score": args.min_sector_score,
        "industry_top_n": args.industry_top_n,
        "concept_top_n": args.concept_top_n,
    }
    report = build_report(plan, results, run_config)

    # Save report
    out_dir = BACKFILL_OUTPUT_DIR / f"{args.start_date}_to_{args.end_date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "sector_inputs_backfill_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Report JSON: {json_path}")

    md_path = out_dir / "sector_inputs_backfill_report.md"
    md_path.write_text(generate_markdown(report), encoding="utf-8")
    print(f"✅ Report Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Backfill Complete")
    print(f"  sector_research built: {report['generated_sector_research_count']}")
    print(f"  concept_unified_rank built: {report['generated_concept_rank_count']}")
    print(f"  compatibility: {report['compatibility_check_summary']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
