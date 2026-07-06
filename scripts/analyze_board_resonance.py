#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 43: Board Resonance Analysis

计算行业与概念板块的共振评分。

用法:
  python scripts/analyze_board_resonance.py --as-of 2026-07-06
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECTOR_RESEARCH_DIR = PROJECT_ROOT / "reports" / "full90" / "sector_research"
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "board_resonance"

# Add theme_sector_radar to path
sys.path.insert(0, str(PROJECT_ROOT))
from theme_sector_radar.agents.ranking_report.board_resonance_agent import calculate_board_resonance


def load_industry_top(date: str, top_n: int = 10) -> list[dict]:
    """Load industry top from sector_research.json."""
    path = SECTOR_RESEARCH_DIR / date / "sector_research.json"
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        results = data.get("research_results", [])
        # Filter industry type and take top N by ranking_score
        industries = [
            r for r in results
            if r.get("sector_type") == "industry"
        ]
        industries.sort(key=lambda x: x.get("ranking_score", 0), reverse=True)
        return industries[:top_n]
    except Exception:
        return []


def load_concept_top(date: str, top_n: int = 10) -> list[dict]:
    """Load concept top from concept_unified_rank.csv."""
    path = CONCEPT_RANK_DIR / date / "concept_unified_rank.csv"
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            concepts = []
            for row in reader:
                concepts.append({
                    "sector_name": row.get("sector_name", ""),
                    "sector_type": "concept",
                    "concept_final_rank_score": float(row.get("concept_final_rank_score", 0) or 0),
                    "trend_continuation_score": float(row.get("trend_continuation_score", 0) or 0),
                    "short_term_burst_score": float(row.get("short_term_burst_score", 0) or 0),
                    "agent_consensus_label": row.get("agent_consensus_label", ""),
                    "rank": int(row.get("rank", 0) or 0),
                })
            # Sort by composite score and take top N
            concepts.sort(key=lambda x: x.get("concept_final_rank_score", 0), reverse=True)
            return concepts[:top_n]
    except Exception:
        return []


def generate_markdown_report(result: dict) -> str:
    """Generate markdown report from resonance results."""
    lines = []
    lines.append("# Board Resonance Report")
    lines.append("")
    lines.append(f"**As Of Date**: {result.get('as_of', '')}")
    lines.append(f"**Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅供研究观察，不构成投资建议。")
    lines.append("")

    # Summary
    summary = result.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total Pairs**: {summary.get('total_pairs', 0)}")
    lines.append(f"- **High Confidence Pairs**: {summary.get('high_confidence_pairs', 0)}")
    lines.append(f"- **Average Resonance Score**: {summary.get('avg_resonance_score', 0):.2f}")
    lines.append("")

    # Summary
    summary = result.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total Pairs**: {summary.get('total_pairs', 0)}")
    lines.append(f"- **High Confidence Pairs**: {summary.get('high_confidence_pairs', 0)}")
    lines.append(f"- **Medium Confidence Pairs**: {summary.get('medium_confidence_pairs', 0)}")
    lines.append(f"- **Semantic Resonance Pairs**: {summary.get('semantic_resonance_pairs', 0)}")
    lines.append(f"- **Average Resonance Score**: {summary.get('avg_resonance_score', 0):.2f}")
    lines.append(f"- **Max Resonance Bonus**: {summary.get('max_resonance_bonus', 0):.2f}")
    lines.append("")

    # Resonance pairs
    pairs = result.get("resonance_pairs", [])
    if pairs:
        lines.append("## Resonance Top10")
        lines.append("")
        lines.append("| Rank | Industry | Concept | Type | Original | Resonance | Semantic | Overlap | Bonus | Adjusted | Confidence |")
        lines.append("|------|----------|---------|------|----------|-----------|----------|---------|-------|----------|------------|")

        for pair in pairs[:10]:
            # Calculate original score from concept data
            concept_data = pair.get("concept_data", {})
            original_score = float(concept_data.get("concept_final_rank_score", 0) or 0)
            adjusted_score = original_score + pair.get("resonance_bonus", 0)

            lines.append(
                f"| {pair.get('rank', 0)} | "
                f"{pair.get('industry', '')} | "
                f"{pair.get('concept', '')} | "
                f"{pair.get('resonance_type', '')} | "
                f"{original_score:.2f} | "
                f"{pair.get('resonance_score', 0):.2f} | "
                f"{pair.get('semantic_match_score', 0):.0f} | "
                f"{pair.get('overlap_stock_count', 0)} | "
                f"+{pair.get('resonance_bonus', 0):.2f} | "
                f"{adjusted_score:.2f} | "
                f"{pair.get('confidence', '')} |"
            )
        lines.append("")

        # Detailed top 5
        lines.append("## Detailed Top5")
        lines.append("")
        for pair in pairs[:5]:
            concept_data = pair.get("concept_data", {})
            original_score = float(concept_data.get("concept_final_rank_score", 0) or 0)
            adjusted_score = original_score + pair.get("resonance_bonus", 0)

            lines.append(f"### {pair.get('rank', 0)}. {pair.get('industry', '')} × {pair.get('concept', '')}")
            lines.append("")
            lines.append(f"- **Resonance Type**: {pair.get('resonance_type', '')}")
            lines.append(f"- **Resonance Score**: {pair.get('resonance_score', 0):.2f}")
            lines.append(f"- **Resonance Bonus**: +{pair.get('resonance_bonus', 0):.2f}")
            lines.append(f"- **Original Composite Score**: {original_score:.2f}")
            lines.append(f"- **Adjusted Score**: {adjusted_score:.2f}")
            lines.append(f"- **Overlap Stock Count**: {pair.get('overlap_stock_count', 0)}")
            lines.append(f"- **Industry Strength**: {pair.get('industry_strength', 0):.2f}")
            lines.append(f"- **Concept Strength**: {pair.get('concept_strength', 0):.2f}")
            lines.append(f"- **Semantic Match Score**: {pair.get('semantic_match_score', 0):.2f}")
            lines.append(f"- **Semantic Match Reason**: {pair.get('semantic_match_reason', '')}")
            lines.append(f"- **Confidence**: {pair.get('confidence', '')}")
            lines.append(f"- **Original Rank**: {pair.get('original_rank', 0)}")
            lines.append(f"- **Resonance Rank**: {pair.get('resonance_rank', 0)}")
            lines.append(f"- **Rank Delta**: {pair.get('rank_delta', 0)}")
            lines.append(f"- **Reason**: {pair.get('reason', '')}")
            lines.append("")

            # Score breakdown
            breakdown = pair.get("score_breakdown", {})
            if breakdown:
                lines.append("**Score Breakdown:**")
                lines.append("")
                lines.append(f"- Industry Strength: {breakdown.get('industry_strength_score', 0):.2f} (weight: {breakdown.get('weights', {}).get('industry', 0)})")
                lines.append(f"- Concept Strength: {breakdown.get('concept_strength_score', 0):.2f} (weight: {breakdown.get('weights', {}).get('concept', 0)})")
                lines.append(f"- Overlap: {breakdown.get('overlap_score', 0):.2f} (weight: {breakdown.get('weights', {}).get('overlap', 0)})")
                lines.append(f"- Semantic Match: {breakdown.get('semantic_match_score', 0):.2f} (weight: {breakdown.get('weights', {}).get('semantic', 0)})")
                lines.append(f"- Label Alignment: {breakdown.get('label_alignment_score', 0):.2f} (weight: {breakdown.get('weights', {}).get('label', 0)})")
                lines.append(f"- Risk Adjustment: {breakdown.get('risk_adjustment_score', 0):.2f} (weight: {breakdown.get('weights', {}).get('risk', 0)})")
                lines.append("")

            # Overlap stocks
            overlap_stocks = pair.get("overlap_stocks", [])
            if overlap_stocks:
                lines.append("**Overlap Stocks:**")
                lines.append("")
                for stock in overlap_stocks[:5]:
                    lines.append(f"- {stock.get('code', '')} {stock.get('name', '')}")
                lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Board Resonance Analysis")
    parser.add_argument("--as-of", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--top-n", type=int, default=10, help="Top N for industry and concept")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"  Board Resonance Analysis")
    print(f"  Date: {args.as_of}")
    print(f"{'='*70}")
    print()

    # Load data
    industry_top = load_industry_top(args.as_of, args.top_n)
    concept_top = load_concept_top(args.as_of, args.top_n)

    if not industry_top:
        print(f"  ❌ No industry data found for {args.as_of}")
        return 1
    if not concept_top:
        print(f"  ❌ No concept data found for {args.as_of}")
        return 1

    print(f"  Industry Top: {len(industry_top)} sectors")
    print(f"  Concept Top: {len(concept_top)} sectors")
    print()

    # Calculate resonance
    result = calculate_board_resonance(
        industry_top=industry_top,
        concept_top=concept_top,
        top_n=args.top_n,
    )

    # Save JSON
    out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR / args.as_of
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "board_resonance.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Save Markdown
    md_content = generate_markdown_report(result)
    md_path = out_dir / "board_resonance.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print()
    summary = result.get("summary", {})
    print(f"  Summary:")
    print(f"    - Total pairs: {summary.get('total_pairs', 0)}")
    print(f"    - High confidence pairs: {summary.get('high_confidence_pairs', 0)}")
    print(f"    - Average resonance score: {summary.get('avg_resonance_score', 0):.2f}")

    # Print top 5
    pairs = result.get("resonance_pairs", [])
    if pairs:
        print(f"    - Top 5 resonance pairs:")
        for pair in pairs[:5]:
            print(f"      {pair.get('rank', 0)}. {pair.get('industry', '')} × {pair.get('concept', '')}: "
                  f"score={pair.get('resonance_score', 0):.2f}, bonus=+{pair.get('resonance_bonus', 0):.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
