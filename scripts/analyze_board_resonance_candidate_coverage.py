#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 46: Board Resonance Candidate Coverage Analysis

分析强共振是否进入候选池。

用法:
  python scripts/analyze_board_resonance_candidate_coverage.py --as-of 2026-07-06
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESONANCE_DIR = PROJECT_ROOT / "reports" / "board_resonance"
CANDIDATE_DIR = PROJECT_ROOT / "reports" / "agent_bridge"


def load_board_resonance(date: str) -> dict:
    """Load board_resonance.json for a given date."""
    path = RESONANCE_DIR / date / "board_resonance.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_top30_candidates(date: str) -> dict:
    """Load top30_candidates.json for a given date."""
    path = CANDIDATE_DIR / date / "top30_candidates.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def analyze_candidate_coverage(date: str) -> dict:
    """Analyze candidate coverage for resonance pairs."""
    resonance = load_board_resonance(date)
    candidates = load_top30_candidates(date)

    if not resonance or not candidates:
        return {"error": "Missing resonance or candidates data"}

    pairs = resonance.get("resonance_pairs", [])
    candidate_list = candidates.get("candidates", [])

    # Build candidate lookup by code
    candidate_codes = {c.get("code", "") for c in candidate_list}

    # Analyze high/medium resonance pairs
    high_pairs = [p for p in pairs if p.get("confidence") == "high"]
    medium_pairs = [p for p in pairs if p.get("confidence") == "medium"]
    semantic_pairs = [p for p in pairs if p.get("resonance_type") == "semantic_resonance"]

    # Check coverage
    high_covered = []
    high_not_covered = []
    for pair in high_pairs:
        overlap_stocks = {s.get("code", "") for s in pair.get("overlap_stocks", [])}
        covered_codes = overlap_stocks & candidate_codes
        if covered_codes:
            high_covered.append({
                "industry": pair.get("industry", ""),
                "concept": pair.get("concept", ""),
                "resonance_score": pair.get("resonance_score", 0),
                "overlap_count": pair.get("overlap_stock_count", 0),
                "covered_count": len(covered_codes),
                "covered_codes": list(covered_codes)[:5],
            })
        else:
            high_not_covered.append({
                "industry": pair.get("industry", ""),
                "concept": pair.get("concept", ""),
                "resonance_score": pair.get("resonance_score", 0),
                "overlap_count": pair.get("overlap_stock_count", 0),
                "reason": _infer_reason(pair, candidate_codes),
            })

    medium_covered = []
    medium_not_covered = []
    for pair in medium_pairs:
        overlap_stocks = {s.get("code", "") for s in pair.get("overlap_stocks", [])}
        covered_codes = overlap_stocks & candidate_codes
        if covered_codes:
            medium_covered.append({
                "industry": pair.get("industry", ""),
                "concept": pair.get("concept", ""),
                "resonance_score": pair.get("resonance_score", 0),
                "covered_count": len(covered_codes),
            })
        else:
            medium_not_covered.append({
                "industry": pair.get("industry", ""),
                "concept": pair.get("concept", ""),
                "resonance_score": pair.get("resonance_score", 0),
                "reason": _infer_reason(pair, candidate_codes),
            })

    # Count candidates by resonance source
    from_high = sum(1 for c in candidate_list if c.get("resonance_confidence") == "high")
    from_medium = sum(1 for c in candidate_list if c.get("resonance_confidence") == "medium")
    from_semantic = sum(1 for c in candidate_list if c.get("resonance_type") == "semantic_resonance")
    no_resonance = sum(1 for c in candidate_list if not c.get("resonance_type"))

    return {
        "analysis_date": datetime.now().isoformat(),
        "as_of_date": date,
        "summary": {
            "total_pairs": len(pairs),
            "high_confidence_pairs": len(high_pairs),
            "medium_confidence_pairs": len(medium_pairs),
            "semantic_resonance_pairs": len(semantic_pairs),
            "high_covered": len(high_covered),
            "high_not_covered": len(high_not_covered),
            "medium_covered": len(medium_covered),
            "medium_not_covered": len(medium_not_covered),
        },
        "candidate_resonance_distribution": {
            "from_high_confidence": from_high,
            "from_medium_confidence": from_medium,
            "from_semantic_resonance": from_semantic,
            "no_resonance": no_resonance,
        },
        "high_covered_pairs": high_covered,
        "high_not_covered_pairs": high_not_covered,
        "medium_covered_pairs": medium_covered,
        "medium_not_covered_pairs": medium_not_covered,
    }


def _infer_reason(pair: dict, candidate_codes: set) -> str:
    """Infer why a resonance pair has no candidates."""
    overlap_count = pair.get("overlap_stock_count", 0)
    overlap_stocks = pair.get("overlap_stocks", [])

    if overlap_count == 0:
        return "no_overlap_stocks"

    # Check if overlap stocks are filtered
    overlap_codes = {s.get("code", "") for s in overlap_stocks}
    non_main_board = sum(1 for c in overlap_codes if not c.startswith(("600", "601", "603", "605", "000", "001", "002", "003")))

    if non_main_board > 0:
        return "overlap_stocks_filtered_non_main_board"

    return "unknown"


def generate_markdown_report(result: dict) -> str:
    """Generate markdown report from analysis results."""
    lines = []
    lines.append("# Board Resonance Candidate Coverage Report")
    lines.append("")
    lines.append(f"**Analysis Date**: {result.get('analysis_date', '')}")
    lines.append(f"**As Of Date**: {result.get('as_of_date', '')}")
    lines.append("")

    # Summary
    summary = result.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total Resonance Pairs**: {summary.get('total_pairs', 0)}")
    lines.append(f"- **High Confidence Pairs**: {summary.get('high_confidence_pairs', 0)}")
    lines.append(f"- **Medium Confidence Pairs**: {summary.get('medium_confidence_pairs', 0)}")
    lines.append(f"- **Semantic Resonance Pairs**: {summary.get('semantic_resonance_pairs', 0)}")
    lines.append(f"- **High Covered**: {summary.get('high_covered', 0)}")
    lines.append(f"- **High Not Covered**: {summary.get('high_not_covered', 0)}")
    lines.append(f"- **Medium Covered**: {summary.get('medium_covered', 0)}")
    lines.append(f"- **Medium Not Covered**: {summary.get('medium_not_covered', 0)}")
    lines.append("")

    # Candidate resonance distribution
    dist = result.get("candidate_resonance_distribution", {})
    lines.append("## Candidate Resonance Distribution")
    lines.append("")
    lines.append(f"- **From High Confidence**: {dist.get('from_high_confidence', 0)}")
    lines.append(f"- **From Medium Confidence**: {dist.get('from_medium_confidence', 0)}")
    lines.append(f"- **From Semantic Resonance**: {dist.get('from_semantic_resonance', 0)}")
    lines.append(f"- **No Resonance**: {dist.get('no_resonance', 0)}")
    lines.append("")

    # High covered pairs
    high_covered = result.get("high_covered_pairs", [])
    if high_covered:
        lines.append("## High Confidence Covered")
        lines.append("")
        lines.append("| Industry | Concept | Score | Overlap | Covered |")
        lines.append("|----------|---------|-------|---------|---------|")
        for p in high_covered[:10]:
            lines.append(
                f"| {p.get('industry', '')} | {p.get('concept', '')} | "
                f"{p.get('resonance_score', 0):.2f} | "
                f"{p.get('overlap_count', 0)} | "
                f"{p.get('covered_count', 0)} |"
            )
        lines.append("")

    # High not covered pairs
    high_not_covered = result.get("high_not_covered_pairs", [])
    if high_not_covered:
        lines.append("## High Confidence Not Covered")
        lines.append("")
        lines.append("| Industry | Concept | Score | Overlap | Reason |")
        lines.append("|----------|---------|-------|---------|--------|")
        for p in high_not_covered[:10]:
            lines.append(
                f"| {p.get('industry', '')} | {p.get('concept', '')} | "
                f"{p.get('resonance_score', 0):.2f} | "
                f"{p.get('overlap_count', 0)} | "
                f"{p.get('reason', '')} |"
            )
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Board Resonance Candidate Coverage Analysis")
    parser.add_argument("--as-of", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"  Board Resonance Candidate Coverage Analysis")
    print(f"  Date: {args.as_of}")
    print(f"{'='*70}")
    print()

    # Run analysis
    result = analyze_candidate_coverage(args.as_of)

    if "error" in result:
        print(f"  ❌ {result['error']}")
        return 1

    # Save JSON
    out_dir = Path(args.output_dir) if args.output_dir else RESONANCE_DIR / args.as_of
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "candidate_coverage.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Save Markdown
    md_content = generate_markdown_report(result)
    md_path = out_dir / "candidate_coverage.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print()
    summary = result.get("summary", {})
    dist = result.get("candidate_resonance_distribution", {})
    print(f"  Summary:")
    print(f"    - High confidence pairs: {summary.get('high_confidence_pairs', 0)}")
    print(f"    - High covered: {summary.get('high_covered', 0)}")
    print(f"    - High not covered: {summary.get('high_not_covered', 0)}")
    print(f"    - Candidates from high confidence: {dist.get('from_high_confidence', 0)}")
    print(f"    - Candidates from semantic resonance: {dist.get('from_semantic_resonance', 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
