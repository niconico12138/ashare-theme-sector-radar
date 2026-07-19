#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据补齐与验证脚本

补齐 reports/unified → top30_candidates → selection_validation 链路，
扩大多日历史验证样本。

用法:
  python scripts/backfill_historical_unified_and_validation.py \
    --start-date 2026-06-01 --end-date 2026-07-08 \
    --source stockdb-sdk --force

  # dry-run
  python scripts/backfill_historical_unified_and_validation.py \
    --start-date 2026-06-01 --end-date 2026-07-08 --dry-run

  # 小批量试跑
  python scripts/backfill_historical_unified_and_validation.py \
    --start-date 2026-06-01 --end-date 2026-07-08 --max-dates 3 --force
"""

from __future__ import annotations

import argparse
import json
import re
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

OUTPUT_DIR = PROJECT_ROOT / "reports" / "selection_validation"
DATE_RE = re.compile(r"^2026-\d{2}-\d{2}$")


# ======================================================================
# DATE SCANNING
# ======================================================================

def scan_available_dates(start_date: str, end_date: str) -> list[dict]:
    """Scan reports/ for valid YYYY-MM-DD dates and check what exists."""
    sector_dir = PROJECT_ROOT / "reports" / "sector_scores"
    theme_dir = PROJECT_ROOT / "reports" / "theme_sector_radar"
    unified_dir = PROJECT_ROOT / "reports" / "unified"
    bridge_dir = PROJECT_ROOT / "reports" / "agent_bridge"
    validation_dir = OUTPUT_DIR
    sector_research_dir = PROJECT_ROOT / "reports" / "full90" / "sector_research"
    concept_rank_dir = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"

    # Collect all valid dates from sector_scores and theme_sector_radar
    all_dates: set[str] = set()
    for d in [sector_dir, theme_dir]:
        if d.exists():
            for item in d.iterdir():
                if item.is_dir() and DATE_RE.match(item.name):
                    if start_date <= item.name <= end_date:
                        all_dates.add(item.name)

    plan = []
    for date in sorted(all_dates):
        has_sector = (sector_dir / date).exists()
        has_theme = (theme_dir / date).exists()
        has_unified = (unified_dir / date / "unified_report.json").exists()
        has_top30 = (bridge_dir / date / "top30_candidates.json").exists()
        has_validation = (validation_dir / date / "next_day_selection_validation.json").exists()
        # Export requires sector_research + concept_unified_rank
        has_sector_research = (sector_research_dir / date / "sector_research.json").exists()
        has_concept_rank = (concept_rank_dir / date / "concept_unified_rank.csv").exists()
        can_export = has_sector_research and has_concept_rank

        # Check if unified report has actual data
        unified_ok = False
        if has_unified:
            try:
                ur = json.loads((unified_dir / date / "unified_report.json").read_text(encoding="utf-8"))
                trend = ur.get("trend_candidates_all", ur.get("trend_top_stocks", []))
                burst = ur.get("burst_candidates_all", ur.get("burst_top_stocks", []))
                unified_ok = len(trend) > 0 or len(burst) > 0
            except Exception:
                unified_ok = False

        should_run_unified = (has_sector or has_theme) and not unified_ok
        should_run_export = unified_ok and can_export and not has_top30
        should_run_validation = has_top30 and not has_validation

        plan.append({
            "date": date,
            "has_sector_scores": has_sector,
            "has_theme_snapshot": has_theme,
            "has_unified_report": unified_ok,
            "has_top30_candidates": has_top30,
            "has_validation": has_validation,
            "has_sector_research": has_sector_research,
            "can_export": can_export,
            "should_run_unified": should_run_unified,
            "should_run_export": should_run_export,
            "should_run_validation": should_run_validation,
        })

    return plan


# ======================================================================
# STEP RUNNERS
# ======================================================================

def _run_cmd(cmd: list[str], timeout: int = 180, label: str = "") -> tuple[bool, str, str]:
    """Run a command, return (success, stdout_snippet, stderr_snippet)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, cwd=str(PROJECT_ROOT),
        )
        stdout = result.stdout[-500:] if result.stdout else ""
        stderr = result.stderr[-500:] if result.stderr else ""
        return result.returncode == 0, stdout.strip(), stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", f"TIMEOUT after {timeout}s"
    except Exception as exc:
        return False, "", str(exc)


def run_unified(date: str) -> dict:
    """Run unified_pipeline.py for a single date."""
    cmd = [sys.executable, "unified_pipeline.py", "--as-of", date, "--mode", "quick"]
    ok, stdout, stderr = _run_cmd(cmd, timeout=300, label="unified")

    # Verify output
    unified_path = PROJECT_ROOT / "reports" / "unified" / date / "unified_report.json"
    output_ok = False
    candidate_count = 0
    if unified_path.exists():
        try:
            ur = json.loads(unified_path.read_text(encoding="utf-8"))
            trend = ur.get("trend_candidates_all", ur.get("trend_top_stocks", []))
            burst = ur.get("burst_candidates_all", ur.get("burst_top_stocks", []))
            candidate_count = len(trend) + len(burst)
            output_ok = candidate_count > 0
        except Exception:
            pass

    return {
        "success": ok and output_ok,
        "cmd_success": ok,
        "output_exists": output_ok,
        "candidate_count": candidate_count,
        "stdout_snippet": stdout[:300],
        "stderr_snippet": stderr[:300],
    }


def run_export(date: str, stock_limit: int, agent_stock_limit: int) -> dict:
    """Run export_top30_candidates.py for a single date."""
    cmd = [
        sys.executable, "scripts/export_top30_candidates.py",
        "--as-of", date,
        "--stock-limit", str(stock_limit),
        "--agent-stock-limit", str(agent_stock_limit),
    ]
    ok, stdout, stderr = _run_cmd(cmd, timeout=120, label="export")

    # Verify output
    top30_path = PROJECT_ROOT / "reports" / "agent_bridge" / date / "top30_candidates.json"
    output_ok = False
    candidate_count = 0
    if top30_path.exists():
        try:
            t30 = json.loads(top30_path.read_text(encoding="utf-8"))
            candidate_count = len(t30.get("candidates", []))
            output_ok = candidate_count > 0
        except Exception:
            pass

    return {
        "success": ok and output_ok,
        "cmd_success": ok,
        "output_exists": output_ok,
        "candidate_count": candidate_count,
        "stdout_snippet": stdout[:300],
        "stderr_snippet": stderr[:300],
    }


def run_validation(date: str, source: str, horizon: int) -> dict:
    """Run evaluate_next_day_selection.py for a single date."""
    candidate_path = PROJECT_ROOT / "reports" / "agent_bridge" / date / "top30_candidates.json"
    ranking_path = PROJECT_ROOT / "reports" / "agent_bridge" / date / "aihf_stock_ranking.json"

    cmd = [
        sys.executable, "scripts/evaluate_next_day_selection.py",
        "--as-of", date,
        "--candidate-path", str(candidate_path),
        "--ranking-path", str(ranking_path),
        "--source", source,
        "--horizon", str(horizon),
        "--force",
    ]
    ok, stdout, stderr = _run_cmd(cmd, timeout=120, label="validation")

    # Verify output
    val_path = OUTPUT_DIR / date / "next_day_selection_validation.json"
    output_ok = val_path.exists()
    data_available = 0
    market_regime = "unknown"
    avg_return = None
    if output_ok:
        try:
            vr = json.loads(val_path.read_text(encoding="utf-8"))
            data_available = vr.get("coverage", {}).get("data_available", 0)
            # Compute market regime
            per_stock = vr.get("per_stock", [])
            returns = [s["next_return_pct"] for s in per_stock
                       if s.get("data_available") and s.get("next_return_pct") is not None]
            if returns:
                avg_ret = sum(returns) / len(returns)
                avg_return = round(avg_ret, 4)
                if avg_ret > 1.0:
                    market_regime = "broad_up"
                elif avg_ret < -1.0:
                    market_regime = "broad_down"
                else:
                    market_regime = "mixed"
        except Exception:
            pass

    return {
        "success": ok and output_ok,
        "cmd_success": ok,
        "output_exists": output_ok,
        "data_available": data_available,
        "market_regime": market_regime,
        "avg_candidate_return": avg_return,
        "stdout_snippet": stdout[:300],
        "stderr_snippet": stderr[:300],
    }


# ======================================================================
# BACKFILL REPORT
# ======================================================================

def generate_backfill_report(
    plan: list[dict],
    results: dict[str, dict],
    run_config: dict,
) -> dict:
    """Generate backfill summary report."""
    date_status = []
    failures = []
    valid_dates = []

    for entry in plan:
        date = entry["date"]
        r = results.get(date, {})

        unified_status = "skipped_exists" if entry["has_unified_report"] else (
            "ok" if r.get("unified", {}).get("success") else (
                "failed" if r.get("unified") else "not_needed"
            )
        )
        export_status = "ok" if r.get("export", {}).get("success") else (
            "skipped_exists" if entry["has_top30_candidates"] else (
                "skipped_no_data" if entry["has_unified_report"] and not entry.get("can_export", True) else (
                    "failed" if r.get("export") else "not_needed"
                )
            )
        )
        validation_status = "ok" if r.get("validation", {}).get("success") else (
            "skipped_exists" if entry["has_validation"] else (
                "failed" if r.get("validation") else "not_needed"
            )
        )

        candidate_count = r.get("export", {}).get("candidate_count") or (
            0 if not entry["has_top30_candidates"] else None
        )
        request_count = None  # aihf_request count not tracked separately
        data_available = r.get("validation", {}).get("data_available", 0)
        market_regime = r.get("validation", {}).get("market_regime")
        avg_return = r.get("validation", {}).get("avg_candidate_return")

        row = {
            "date": date,
            "unified_status": unified_status,
            "export_status": export_status,
            "validation_status": validation_status,
            "candidate_count": candidate_count,
            "data_available": data_available,
            "market_regime": market_regime,
            "avg_candidate_return": avg_return,
        }
        date_status.append(row)

        if validation_status == "ok":
            valid_dates.append(date)

        # Record failures
        for step in ["unified", "export", "validation"]:
            step_result = r.get(step, {})
            if step_result and not step_result.get("success", True):
                failures.append({
                    "date": date,
                    "step": step,
                    "error": step_result.get("stderr_snippet", "unknown error"),
                })

    return {
        "run_config": run_config,
        "date_status_table": date_status,
        "unified_generation_summary": {
            "total_dates": sum(1 for e in plan if e["should_run_unified"]),
            "succeeded": sum(1 for d, r in results.items() if r.get("unified", {}).get("success")),
            "failed": sum(1 for d, r in results.items()
                          if r.get("unified") and not r["unified"].get("success")),
        },
        "export_top30_summary": {
            "total_dates": sum(1 for e in plan if e["should_run_export"]),
            "succeeded": sum(1 for d, r in results.items() if r.get("export", {}).get("success")),
            "failed": sum(1 for d, r in results.items()
                          if r.get("export") and not r["export"].get("success")),
        },
        "validation_summary": {
            "total_dates": sum(1 for e in plan if e["should_run_validation"]),
            "succeeded": sum(1 for d, r in results.items() if r.get("validation", {}).get("success")),
            "failed": sum(1 for d, r in results.items()
                          if r.get("validation") and not r["validation"].get("success")),
        },
        "failures": failures,
        "final_valid_date_count": len(valid_dates),
        "valid_dates": valid_dates,
        "cautions": [
            "Historical recompute uses current scoring rules on past dates.",
            "This is not a live backtest — candidate generation may differ from actual historical runs.",
            "Sample size is still limited; do not change scoring weights from this report alone.",
            "Agent ranking is not re-run; agent incremental signals are based on existing rankings where available.",
        ],
    }


def generate_backfill_markdown(report: dict) -> str:
    """Generate markdown backfill report."""
    lines = []
    rc = report.get("run_config", {})
    lines.append(f"# Historical Backfill Report — {rc.get('start_date', '?')} to {rc.get('end_date', '?')}")
    lines.append(f"")
    lines.append(f"> Historical recompute validates current rules on past dates. Not a live backtest.")
    lines.append(f"")

    # 1. Run Config
    lines.append(f"## 1. Run Config")
    lines.append(f"")
    for k, v in rc.items():
        lines.append(f"- {k}: {v}")
    lines.append(f"")

    # 2. Date Status
    lines.append(f"## 2. Date Status")
    lines.append(f"")
    lines.append(f"| {'Date':<12} {'Unified':<16} {'Export':<12} {'Validation':<14} {'N':>4} {'Avail':>6} {'Regime':<12} {'AvgRet%':>8} |")
    lines.append(f"|{'─'*14}|{'─'*18}|{'─'*14}|{'─'*16}|{'─'*6}|{'─'*8}|{'─'*14}|{'─'*10}|")
    for row in report.get("date_status_table", []):
        n = row.get("candidate_count") or "-"
        avail = row.get("data_available") or "-"
        regime = row.get("market_regime") or "-"
        ret = f"{row['avg_candidate_return']:.2f}" if row.get("avg_candidate_return") is not None else "N/A"
        lines.append(
            f"| {row['date']:<12} {row['unified_status']:<16} {row['export_status']:<12} "
            f"{row['validation_status']:<14} {n:>4} {avail:>6} {regime:<12} {ret:>8} |"
        )
    lines.append(f"")

    # 3-5. Summaries
    for title, key in [("Unified Generation", "unified_generation_summary"),
                        ("Export Top30", "export_top30_summary"),
                        ("Validation", "validation_summary")]:
        s = report.get(key, {})
        lines.append(f"## {['','3','4','5'][['','unified_generation_summary','export_top30_summary','validation_summary'].index(key)]}. {title} Summary")
        lines.append(f"")
        lines.append(f"- Total dates needing run: {s.get('total_dates', 0)}")
        lines.append(f"- Succeeded: {s.get('succeeded', 0)}")
        lines.append(f"- Failed: {s.get('failed', 0)}")
        lines.append(f"")

    # 6. Failures
    failures = report.get("failures", [])
    lines.append(f"## 6. Failures")
    lines.append(f"")
    if failures:
        for f in failures:
            lines.append(f"- **{f['date']}** [{f['step']}]: {f['error'][:100]}")
    else:
        lines.append(f"- No failures")
    lines.append(f"")

    # 7. Final
    lines.append(f"## 7. Final Valid Date Count: {report.get('final_valid_date_count', 0)}")
    lines.append(f"")

    # 8. Cautions
    lines.append(f"## 8. Cautions")
    lines.append(f"")
    for c in report.get("cautions", []):
        lines.append(f"- {c}")
    lines.append(f"")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Backfill historical unified + validation")
    parser.add_argument("--start-date", default="2026-06-01")
    parser.add_argument("--end-date", default="2026-07-08")
    parser.add_argument("--dates", nargs="*", default=None)
    parser.add_argument("--source", default="stockdb-sdk")
    parser.add_argument("--stock-limit", type=int, default=30)
    parser.add_argument("--agent-stock-limit", type=int, default=10)
    parser.add_argument("--skip-agent-refresh", action="store_true", default=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-dates", type=int, default=None)
    parser.add_argument("--horizon", type=int, default=1)
    args = parser.parse_args()

    # Build plan
    if args.dates:
        dates = args.dates
        plan = scan_available_dates(min(dates), max(dates))
        plan = [p for p in plan if p["date"] in dates]
    else:
        plan = scan_available_dates(args.start_date, args.end_date)
        dates = [p["date"] for p in plan]

    if args.max_dates:
        plan = plan[:args.max_dates]
        dates = [p["date"] for p in plan]

    print(f"{'='*60}")
    print(f"  Historical Backfill")
    print(f"  Range: {args.start_date} to {args.end_date}")
    print(f"  Dates found: {len(plan)}")
    print(f"  Force: {args.force}")
    print(f"  Dry-run: {args.dry_run}")
    print(f"{'='*60}")

    # Print plan
    need_unified = sum(1 for p in plan if p["should_run_unified"])
    need_export = sum(1 for p in plan if p["should_run_export"])
    need_validation = sum(1 for p in plan if p["should_run_validation"])
    already_done = sum(1 for p in plan if p["has_validation"])

    print(f"\n  📋 Plan:")
    print(f"    - Need unified: {need_unified}")
    print(f"    - Need export: {need_export}")
    print(f"    - Need validation: {need_validation}")
    print(f"    - Already validated: {already_done}")

    if args.dry_run:
        print(f"\n  🏃 DRY RUN — no execution")
        for p in plan:
            flags = []
            if p["should_run_unified"]:
                flags.append("unified")
            if p["should_run_export"]:
                flags.append("export")
            elif p["has_unified_report"] and not p["can_export"]:
                flags.append("skip(no_sector_research)")
            if p["should_run_validation"]:
                flags.append("validation")
            if not flags:
                flags.append("skip (all done)")
            print(f"    {p['date']}: {', '.join(flags)}")

        # Save plan as backfill report
        run_config = {
            "start_date": args.start_date,
            "end_date": args.end_date,
            "source": args.source,
            "dry_run": True,
        }
        report = {
            "run_config": run_config,
            "date_status_table": [
                {"date": p["date"], "unified_status": "planned" if p["should_run_unified"] else "exists",
                 "export_status": "planned" if p["should_run_export"] else "exists",
                 "validation_status": "planned" if p["should_run_validation"] else "exists"}
                for p in plan
            ],
            "failures": [],
            "final_valid_date_count": 0,
            "valid_dates": [],
            "cautions": ["Dry run only — no execution performed."],
        }
        out_dir = OUTPUT_DIR / "backfill" / f"{args.start_date}_to_{args.end_date}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "historical_backfill_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  ✅ Dry-run plan saved to {out_dir}")
        return

    # Execute
    results: dict[str, dict] = {}
    for i, entry in enumerate(plan):
        date = entry["date"]
        print(f"\n{'─'*60}")
        print(f"  [{i+1}/{len(plan)}] {date}")
        print(f"{'─'*60}")

        results[date] = {}

        # Step 1: Unified
        if entry["should_run_unified"]:
            print(f"  📦 Running unified_pipeline...")
            r = run_unified(date)
            results[date]["unified"] = r
            status = "✅" if r["success"] else "❌"
            print(f"  {status} unified: success={r['success']}, candidates={r['candidate_count']}")
        elif entry["has_unified_report"]:
            print(f"  ⏭️  Unified exists, skipping")

        # Step 2: Export
        if entry["should_run_export"]:
            print(f"  📤 Running export_top30...")
            r = run_export(date, args.stock_limit, args.agent_stock_limit)
            results[date]["export"] = r
            status = "✅" if r["success"] else "❌"
            print(f"  {status} export: success={r['success']}, candidates={r['candidate_count']}")
        elif entry["has_top30_candidates"]:
            print(f"  ⏭️  Top30 exists, skipping")
        elif entry["has_unified_report"] and not entry.get("can_export", True):
            print(f"  ⏭️  No sector_research data, export skipped")

        # Step 3: Validation
        if entry["should_run_validation"]:
            print(f"  📈 Running validation...")
            r = run_validation(date, args.source, args.horizon)
            results[date]["validation"] = r
            status = "✅" if r["success"] else "❌"
            print(f"  {status} validation: success={r['success']}, avail={r['data_available']}, regime={r['market_regime']}")
        elif entry["has_validation"]:
            print(f"  ⏭️  Validation exists, skipping")

    # Generate backfill report
    run_config = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "source": args.source,
        "stock_limit": args.stock_limit,
        "agent_stock_limit": args.agent_stock_limit,
        "horizon": args.horizon,
        "force": args.force,
    }
    backfill_report = generate_backfill_report(plan, results, run_config)

    out_dir = OUTPUT_DIR / "backfill" / f"{args.start_date}_to_{args.end_date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    report_json = out_dir / "historical_backfill_report.json"
    report_json.write_text(json.dumps(backfill_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Backfill report: {report_json}")

    report_md = generate_backfill_markdown(backfill_report)
    md_path = out_dir / "historical_backfill_report.md"
    md_path.write_text(report_md, encoding="utf-8")
    print(f"✅ Backfill markdown: {md_path}")

    # Step 6: Run aggregate
    valid_dates = backfill_report.get("valid_dates", [])
    if valid_dates:
        print(f"\n{'='*60}")
        print(f"  Building aggregate from {len(valid_dates)} valid dates...")
        print(f"{'='*60}")
        agg_cmd = [
            sys.executable, "scripts/run_selection_validation_batch.py",
            "--dates"] + valid_dates + [
            "--mode", "existing-artifacts",
            "--source", args.source,
            "--horizon", str(args.horizon),
            "--agent-stock-limit", str(args.agent_stock_limit),
            "--skip-agent-refresh",
            "--force",
        ]
        ok, stdout, stderr = _run_cmd(agg_cmd, timeout=120, label="aggregate")
        if ok:
            print(f"  ✅ Aggregate generated")
        else:
            print(f"  ❌ Aggregate failed: {stderr[:200]}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Backfill Complete")
    print(f"  Valid dates: {len(valid_dates)}")
    print(f"  Failures: {len(backfill_report.get('failures', []))}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
