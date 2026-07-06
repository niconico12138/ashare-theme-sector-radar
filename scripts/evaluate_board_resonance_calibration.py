#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 45: Board Resonance Calibration Evaluation

对 BoardResonanceAgent 输出进行离线评估。

用法:
  python scripts/evaluate_board_resonance_calibration.py \
    --dates 2026-07-01,2026-07-02,2026-07-03,2026-07-06
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
CONFIG_DIR = PROJECT_ROOT / "theme_sector_radar" / "config"
RESONANCE_DIR = PROJECT_ROOT / "reports" / "board_resonance"
OUTPUT_DIR = RESONANCE_DIR / "calibration"


def load_calibration_set() -> dict:
    """Load calibration set JSON."""
    path = CONFIG_DIR / "board_resonance_calibration_set.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


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


def _level_to_numeric(level: str) -> int:
    """Map level string to numeric value."""
    mapping = {"strong": 3, "medium": 2, "weak": 1, "unrelated": 0}
    return mapping.get(level, 0)


def _confidence_to_numeric(confidence: str) -> int:
    """Map confidence string to numeric value."""
    mapping = {"high": 3, "medium": 2, "low": 1}
    return mapping.get(confidence, 0)


def _get_suggested_action(evaluation: dict) -> str:
    """Determine suggested action for a mismatch evaluation."""
    expected = evaluation.get("expected_level", "")
    actual = evaluation.get("actual_level", "")
    actual_numeric = evaluation.get("actual_numeric", 0)
    expected_numeric = evaluation.get("expected_numeric", 0)

    # Get score breakdown from evaluation
    breakdown = evaluation.get("score_breakdown", {})
    semantic_score = breakdown.get("semantic_match_score", 0)
    overlap_score = breakdown.get("overlap_score", 0)
    risk_score = breakdown.get("risk_adjustment_score", 0)

    if expected == "strong" and actual_numeric < expected_numeric:
        # Expected strong but actual low
        if semantic_score < 70:
            return "review_semantic_mapping"
        if overlap_score == 0 and semantic_score >= 70:
            return "accept_semantic_resonance_or_review_overlap"
        if risk_score < 60:
            return "review_risk_rule"
        return "review_threshold"

    if expected == "unrelated" and actual_numeric > 0:
        # Expected unrelated but actual medium/high
        if semantic_score > 0:
            return "remove_or_weaken_semantic_mapping"
        if overlap_score > 50:
            return "review_constituent_overlap"
        return "review_threshold"

    if expected == "medium" and actual == "missing":
        return "review_top_pairs_generation_or_mapping"

    return "no_action"


def _build_feedback_summary(
    evaluations: list[dict],
    mismatch_strong: list[dict],
    mismatch_unrelated: list[dict],
) -> dict:
    """Build feedback summary from evaluations."""
    # Underestimated strong (expected strong but actual low)
    underestimated_strong = []
    for e in evaluations:
        if e.get("expected_level") == "strong" and e.get("actual_numeric", 0) < e.get("expected_numeric", 0):
            underestimated_strong.append({
                "industry": e.get("industry", ""),
                "concept": e.get("concept", ""),
                "expected_level": e.get("expected_level", ""),
                "actual_level": e.get("actual_level", ""),
                "resonance_score": e.get("actual_score", 0),
                "semantic_match_score": e.get("score_breakdown", {}).get("semantic_match_score", 0),
                "overlap_score": e.get("score_breakdown", {}).get("overlap_score", 0),
                "risk_adjustment_score": e.get("score_breakdown", {}).get("risk_adjustment_score", 0),
                "confidence": e.get("actual_level", ""),
                "suggested_action": _get_suggested_action(e),
            })

    # Overestimated unrelated (expected unrelated but actual medium/high)
    overestimated_unrelated = []
    for e in evaluations:
        if e.get("expected_level") == "unrelated" and e.get("actual_numeric", 0) > 0:
            overestimated_unrelated.append({
                "industry": e.get("industry", ""),
                "concept": e.get("concept", ""),
                "expected_level": e.get("expected_level", ""),
                "actual_level": e.get("actual_level", ""),
                "resonance_score": e.get("actual_score", 0),
                "semantic_match_score": e.get("score_breakdown", {}).get("semantic_match_score", 0),
                "overlap_score": e.get("score_breakdown", {}).get("overlap_score", 0),
                "risk_adjustment_score": e.get("score_breakdown", {}).get("risk_adjustment_score", 0),
                "confidence": e.get("actual_level", ""),
                "suggested_action": _get_suggested_action(e),
            })

    # Missing expected strong
    missing_expected_strong = []
    for e in evaluations:
        if e.get("expected_level") == "strong" and e.get("missing", False):
            missing_expected_strong.append({
                "industry": e.get("industry", ""),
                "concept": e.get("concept", ""),
                "expected_level": e.get("expected_level", ""),
                "actual_level": "missing",
                "reason": e.get("reason", ""),
            })

    # Semantic map candidates (need mapping review)
    semantic_map_candidates = []
    for e in evaluations:
        if e.get("expected_level") == "strong" and e.get("actual_numeric", 0) < e.get("expected_numeric", 0):
            breakdown = e.get("score_breakdown", {})
            if breakdown.get("semantic_match_score", 0) < 70:
                semantic_map_candidates.append({
                    "industry": e.get("industry", ""),
                    "concept": e.get("concept", ""),
                    "current_semantic_score": breakdown.get("semantic_match_score", 0),
                    "suggested_action": "add_to_board_resonance_map",
                })

    # Threshold review candidates
    threshold_review_candidates = []
    for e in evaluations:
        if e.get("expected_level") == "strong" and e.get("actual_level") == "medium":
            threshold_review_candidates.append({
                "industry": e.get("industry", ""),
                "concept": e.get("concept", ""),
                "resonance_score": e.get("actual_score", 0),
                "current_threshold": "high >= 65",
                "suggested_action": "consider_lowering_high_threshold",
            })

    # Risk rule review candidates
    risk_rule_review_candidates = []
    for e in evaluations:
        if e.get("expected_level") == "strong" and e.get("actual_numeric", 0) < e.get("expected_numeric", 0):
            breakdown = e.get("score_breakdown", {})
            if breakdown.get("risk_adjustment_score", 100) < 60:
                risk_rule_review_candidates.append({
                    "industry": e.get("industry", ""),
                    "concept": e.get("concept", ""),
                    "risk_adjustment_score": breakdown.get("risk_adjustment_score", 0),
                    "suggested_action": "review_risk_rule_for_this_pair",
                })

    return {
        "underestimated_strong": underestimated_strong,
        "overestimated_unrelated": overestimated_unrelated,
        "missing_expected_strong": missing_expected_strong,
        "semantic_map_candidates": semantic_map_candidates,
        "threshold_review_candidates": threshold_review_candidates,
        "risk_rule_review_candidates": risk_rule_review_candidates,
    }


def evaluate_calibration(dates: list[str]) -> dict:
    """Evaluate calibration set against board resonance results."""
    calibration_set = load_calibration_set()
    if not calibration_set:
        return {"error": "Calibration set not found or empty"}

    labels = calibration_set.get("labels", [])

    # Build lookup for each date
    date_results = {}
    for date in dates:
        resonance = load_board_resonance(date)
        pairs = resonance.get("resonance_pairs", [])

        # Build lookup by (industry, concept)
        lookup = {}
        for pair in pairs:
            key = (pair.get("industry", ""), pair.get("concept", ""))
            lookup[key] = pair
        date_results[date] = lookup

    # Evaluate each label
    evaluations = []
    for label in labels:
        industry = label.get("industry", "")
        concept = label.get("concept", "")
        expected_level = label.get("expected_level", "unrelated")
        expected_types = label.get("expected_types", [])
        reason = label.get("reason", "")

        expected_numeric = _level_to_numeric(expected_level)

        # Find actual results across dates
        actual_results = []
        for date in dates:
            lookup = date_results.get(date, {})
            pair = lookup.get((industry, concept))
            if pair:
                actual_results.append({
                    "date": date,
                    "confidence": pair.get("confidence", ""),
                    "confidence_numeric": _confidence_to_numeric(pair.get("confidence", "")),
                    "resonance_score": pair.get("resonance_score", 0),
                    "resonance_type": pair.get("resonance_type", ""),
                    "semantic_match_score": pair.get("semantic_match_score", 0),
                })

        # Determine actual level (use first available date)
        if actual_results:
            # Use the highest confidence across dates
            best = max(actual_results, key=lambda x: x["confidence_numeric"])
            actual_level_numeric = best["confidence_numeric"]
            actual_level = best["confidence"]
            actual_score = best["resonance_score"]
            actual_type = best["resonance_type"]
        else:
            actual_level_numeric = 0
            actual_level = "missing"
            actual_score = 0
            actual_type = "missing"

        # Calculate match
        exact_match = actual_level_numeric == expected_numeric
        within_one = abs(actual_level_numeric - expected_numeric) <= 1

        evaluations.append({
            "industry": industry,
            "concept": concept,
            "expected_level": expected_level,
            "expected_numeric": expected_numeric,
            "actual_level": actual_level,
            "actual_numeric": actual_level_numeric,
            "actual_score": actual_score,
            "actual_type": actual_type,
            "exact_match": exact_match,
            "within_one": within_one,
            "missing": actual_level == "missing",
            "reason": reason,
            "expected_types": expected_types,
            "dates_available": [r["date"] for r in actual_results],
        })

    # Calculate metrics
    total = len(evaluations)
    exact_match_count = sum(1 for e in evaluations if e["exact_match"])
    within_one_count = sum(1 for e in evaluations if e["within_one"])
    missing_count = sum(1 for e in evaluations if e["missing"])

    # Overestimated: actual > expected
    overestimated = []
    for e in evaluations:
        if not e["missing"] and e["actual_numeric"] > e["expected_numeric"]:
            overestimated.append(e)

    # Underestimated: actual < expected
    underestimated = []
    for e in evaluations:
        if not e["missing"] and e["actual_numeric"] < e["expected_numeric"]:
            underestimated.append(e)

    # Mismatch samples
    mismatch_strong = [e for e in evaluations if e["expected_level"] == "strong" and not e["exact_match"]]
    mismatch_unrelated = [e for e in evaluations if e["expected_level"] == "unrelated" and e["actual_numeric"] > 0]

    # Score distribution
    strong_scores = [e["actual_score"] for e in evaluations if e["expected_level"] == "strong" and not e["missing"]]
    medium_scores = [e["actual_score"] for e in evaluations if e["expected_level"] == "medium" and not e["missing"]]
    weak_scores = [e["actual_score"] for e in evaluations if e["expected_level"] in ("weak", "unrelated") and not e["missing"]]

    def _stats(scores):
        if not scores:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}
        return {
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "avg": round(sum(scores) / len(scores), 2),
            "count": len(scores),
        }

    return {
        "evaluation_date": datetime.now().isoformat(),
        "dates_evaluated": dates,
        "calibration_set_version": calibration_set.get("version", ""),
        "total_labels": total,
        "metrics": {
            "exact_match_count": exact_match_count,
            "exact_match_rate": round(exact_match_count / total, 3) if total > 0 else 0,
            "within_one_level_count": within_one_count,
            "within_one_accuracy": round(within_one_count / total, 3) if total > 0 else 0,
            "overestimated_count": len(overestimated),
            "underestimated_count": len(underestimated),
            "missing_count": missing_count,
        },
        "mismatch_samples": {
            "strong_expected_not_high": [e for e in mismatch_strong if e["actual_level"] != "high"],
            "unrelated_actual_medium_or_high": mismatch_unrelated,
        },
        "score_distribution": {
            "strong_expected": _stats(strong_scores),
            "medium_expected": _stats(medium_scores),
            "weak_unrelated_expected": _stats(weak_scores),
        },
        "evaluations": evaluations,
        # Phase 46: feedback_summary
        "feedback_summary": _build_feedback_summary(evaluations, mismatch_strong, mismatch_unrelated),
    }


def generate_markdown_report(result: dict) -> str:
    """Generate markdown report from evaluation results."""
    lines = []
    lines.append("# Board Resonance Calibration Evaluation Report")
    lines.append("")
    lines.append(f"**Evaluation Date**: {result.get('evaluation_date', '')}")
    lines.append(f"**Dates Evaluated**: {', '.join(result.get('dates_evaluated', []))}")
    lines.append(f"**Calibration Set Version**: {result.get('calibration_set_version', '')}")
    lines.append(f"**Total Labels**: {result.get('total_labels', 0)}")
    lines.append("")

    # Metrics
    metrics = result.get("metrics", {})
    lines.append("## Evaluation Metrics")
    lines.append("")
    lines.append(f"- **Exact Match Count**: {metrics.get('exact_match_count', 0)}")
    lines.append(f"- **Exact Match Rate**: {metrics.get('exact_match_rate', 0):.1%}")
    lines.append(f"- **Within-One-Level Count**: {metrics.get('within_one_level_count', 0)}")
    lines.append(f"- **Within-One Accuracy**: {metrics.get('within_one_accuracy', 0):.1%}")
    lines.append(f"- **Overestimated Count**: {metrics.get('overestimated_count', 0)}")
    lines.append(f"- **Underestimated Count**: {metrics.get('underestimated_count', 0)}")
    lines.append(f"- **Missing Count**: {metrics.get('missing_count', 0)}")
    lines.append("")

    # Score distribution
    dist = result.get("score_distribution", {})
    lines.append("## Score Distribution")
    lines.append("")
    lines.append("### Strong Expected")
    strong = dist.get("strong_expected", {})
    lines.append(f"- Count: {strong.get('count', 0)}")
    lines.append(f"- Min: {strong.get('min', 0):.2f}")
    lines.append(f"- Max: {strong.get('max', 0):.2f}")
    lines.append(f"- Avg: {strong.get('avg', 0):.2f}")
    lines.append("")

    lines.append("### Medium Expected")
    medium = dist.get("medium_expected", {})
    lines.append(f"- Count: {medium.get('count', 0)}")
    lines.append(f"- Min: {medium.get('min', 0):.2f}")
    lines.append(f"- Max: {medium.get('max', 0):.2f}")
    lines.append(f"- Avg: {medium.get('avg', 0):.2f}")
    lines.append("")

    lines.append("### Weak/Unrelated Expected")
    weak = dist.get("weak_unrelated_expected", {})
    lines.append(f"- Count: {weak.get('count', 0)}")
    lines.append(f"- Min: {weak.get('min', 0):.2f}")
    lines.append(f"- Max: {weak.get('max', 0):.2f}")
    lines.append(f"- Avg: {weak.get('avg', 0):.2f}")
    lines.append("")

    # Mismatch samples
    mismatch = result.get("mismatch_samples", {})
    lines.append("## Mismatch Samples")
    lines.append("")

    strong_mismatch = mismatch.get("strong_expected_not_high", [])
    if strong_mismatch:
        lines.append("### Strong Expected but Not High")
        lines.append("")
        lines.append("| Industry | Concept | Expected | Actual | Score | Type |")
        lines.append("|----------|---------|----------|--------|-------|------|")
        for e in strong_mismatch[:10]:
            lines.append(
                f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                f"{e.get('expected_level', '')} | {e.get('actual_level', '')} | "
                f"{e.get('actual_score', 0):.2f} | {e.get('actual_type', '')} |"
            )
        lines.append("")

    unrelated_mismatch = mismatch.get("unrelated_actual_medium_or_high", [])
    if unrelated_mismatch:
        lines.append("### Unrelated Expected but Actual Medium/High")
        lines.append("")
        lines.append("| Industry | Concept | Expected | Actual | Score | Type |")
        lines.append("|----------|---------|----------|--------|-------|------|")
        for e in unrelated_mismatch[:10]:
            lines.append(
                f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                f"{e.get('expected_level', '')} | {e.get('actual_level', '')} | "
                f"{e.get('actual_score', 0):.2f} | {e.get('actual_type', '')} |"
            )
        lines.append("")

    # Phase 46: Feedback Summary
    feedback = result.get("feedback_summary", {})
    if feedback:
        lines.append("## Feedback Summary")
        lines.append("")

        # Underestimated strong
        underestimated = feedback.get("underestimated_strong", [])
        lines.append(f"### Underestimated Strong ({len(underestimated)} samples)")
        lines.append("")
        if underestimated:
            lines.append("| Industry | Concept | Expected | Actual | Score | Semantic | Overlap | Risk | Action |")
            lines.append("|----------|---------|----------|--------|-------|----------|---------|------|--------|")
            for e in underestimated[:10]:
                lines.append(
                    f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                    f"{e.get('expected_level', '')} | {e.get('actual_level', '')} | "
                    f"{e.get('resonance_score', 0):.2f} | "
                    f"{e.get('semantic_match_score', 0):.0f} | "
                    f"{e.get('overlap_score', 0):.0f} | "
                    f"{e.get('risk_adjustment_score', 0):.0f} | "
                    f"{e.get('suggested_action', '')} |"
                )
        lines.append("")

        # Overestimated unrelated
        overestimated = feedback.get("overestimated_unrelated", [])
        lines.append(f"### Overestimated Unrelated ({len(overestimated)} samples)")
        lines.append("")
        if overestimated:
            lines.append("| Industry | Concept | Expected | Actual | Score | Semantic | Overlap | Risk | Action |")
            lines.append("|----------|---------|----------|--------|-------|----------|---------|------|--------|")
            for e in overestimated[:10]:
                lines.append(
                    f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                    f"{e.get('expected_level', '')} | {e.get('actual_level', '')} | "
                    f"{e.get('resonance_score', 0):.2f} | "
                    f"{e.get('semantic_match_score', 0):.0f} | "
                    f"{e.get('overlap_score', 0):.0f} | "
                    f"{e.get('risk_adjustment_score', 0):.0f} | "
                    f"{e.get('suggested_action', '')} |"
                )
        lines.append("")

        # Missing expected strong
        missing = feedback.get("missing_expected_strong", [])
        lines.append(f"### Missing Expected Strong ({len(missing)} samples)")
        lines.append("")
        if missing:
            lines.append("| Industry | Concept | Expected | Reason |")
            lines.append("|----------|---------|----------|--------|")
            for e in missing[:10]:
                lines.append(
                    f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                    f"{e.get('expected_level', '')} | {e.get('reason', '')[:40]} |"
                )
        lines.append("")

        # Semantic map candidates
        semantic = feedback.get("semantic_map_candidates", [])
        lines.append(f"### Semantic Map Candidates ({len(semantic)} pairs)")
        lines.append("")
        if semantic:
            lines.append("| Industry | Concept | Current Score | Action |")
            lines.append("|----------|---------|---------------|--------|")
            for e in semantic[:10]:
                lines.append(
                    f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                    f"{e.get('current_semantic_score', 0):.0f} | "
                    f"{e.get('suggested_action', '')} |"
                )
        lines.append("")

        # Threshold review candidates
        threshold = feedback.get("threshold_review_candidates", [])
        lines.append(f"### Threshold Review Candidates ({len(threshold)} pairs)")
        lines.append("")
        if threshold:
            lines.append("| Industry | Concept | Score | Current | Action |")
            lines.append("|----------|---------|-------|---------|--------|")
            for e in threshold[:10]:
                lines.append(
                    f"| {e.get('industry', '')} | {e.get('concept', '')} | "
                    f"{e.get('resonance_score', 0):.2f} | "
                    f"{e.get('current_threshold', '')} | "
                    f"{e.get('suggested_action', '')} |"
                )
        lines.append("")

    # All evaluations
    lines.append("## All Evaluations")
    lines.append("")
    lines.append("| Industry | Concept | Expected | Actual | Score | Match | Missing |")
    lines.append("|----------|---------|----------|--------|-------|-------|---------|")
    for e in result.get("evaluations", []):
        match_icon = "✅" if e.get("exact_match") else "❌"
        missing_icon = "⚠️" if e.get("missing") else ""
        lines.append(
            f"| {e.get('industry', '')} | {e.get('concept', '')} | "
            f"{e.get('expected_level', '')} | {e.get('actual_level', '')} | "
            f"{e.get('actual_score', 0):.2f} | {match_icon} | {missing_icon} |"
        )
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Board Resonance Calibration Evaluation")
    parser.add_argument("--dates", required=True, help="Comma-separated dates (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if not dates:
        print("  ❌ No dates provided")
        return 1

    print(f"{'='*70}")
    print(f"  Board Resonance Calibration Evaluation")
    print(f"  Dates: {', '.join(dates)}")
    print(f"{'='*70}")
    print()

    # Run evaluation
    result = evaluate_calibration(dates)

    if "error" in result:
        print(f"  ❌ {result['error']}")
        return 1

    # Save JSON
    out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "board_resonance_calibration_eval.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Save Markdown
    md_content = generate_markdown_report(result)
    md_path = out_dir / "board_resonance_calibration_eval.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print()
    metrics = result.get("metrics", {})
    print(f"  Summary:")
    print(f"    - Total labels: {result.get('total_labels', 0)}")
    print(f"    - Exact match: {metrics.get('exact_match_count', 0)} ({metrics.get('exact_match_rate', 0):.1%})")
    print(f"    - Within-one accuracy: {metrics.get('within_one_level_count', 0)} ({metrics.get('within_one_accuracy', 0):.1%})")
    print(f"    - Overestimated: {metrics.get('overestimated_count', 0)}")
    print(f"    - Underestimated: {metrics.get('underestimated_count', 0)}")
    print(f"    - Missing: {metrics.get('missing_count', 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
