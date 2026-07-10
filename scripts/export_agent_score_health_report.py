#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Score Calibration Health Report

Generates a consolidated health report from scoring_calibration_summary.json,
combining all agent_score diagnostic sections into a single human-readable document.

Usage:
  python scripts/export_agent_score_health_report.py \\
    --summary-path reports/scoring_calibration/aggregate/2026-06-29_to_2026-07-08/scoring_calibration_summary.json \\
    --output-dir reports/scoring_calibration/agent_score_health
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def determine_overall_status(summary: dict) -> str:
    """Determine overall health status from summary data."""
    pipeline_warnings = summary.get("pipeline_warnings", [])
    if pipeline_warnings:
        return "risk"

    # Check execution quality — fallback_only triggers risk
    exec_rollup = summary.get("agent_execution_quality_rollup", {})
    fallback_dates = exec_rollup.get("fallback_only_dates", [])
    if fallback_dates:
        return "risk"

    agent_rec = summary.get("layers", {}).get("agent_score", {}).get("recommendation", {})
    if agent_rec.get("type") == "insufficient_evidence":
        return "monitor"

    presence = summary.get("agent_score_presence_effect", {})
    market_adj = summary.get("agent_score_market_adjusted", {})
    has_presence = presence.get("interpretation", {}).get("has_presence_signal", False)
    has_alpha = market_adj.get("interpretation", {}).get("has_positive_alpha_signal", False)

    if has_presence and has_alpha:
        return "healthy"

    return "monitor"


def build_headline_findings(summary: dict) -> list[str]:
    """Extract key headline findings from summary."""
    findings = []

    # Recommendation
    agent_rec = summary.get("layers", {}).get("agent_score", {}).get("recommendation", {})
    findings.append(f"Agent score recommendation: {agent_rec.get('type', 'unknown')}")

    # Coverage quality
    cov_rollup = summary.get("agent_score_coverage_quality_rollup", {})
    avg_cov = cov_rollup.get("avg_coverage_ratio", 0)
    findings.append(f"Average agent_score coverage: {avg_cov:.1%}")

    poor_dates = cov_rollup.get("poor_dates", [])
    partial_dates = cov_rollup.get("partial_dates", [])
    if poor_dates:
        findings.append(f"Poor coverage dates: {', '.join(poor_dates)}")
    if partial_dates:
        findings.append(f"Partial coverage dates: {', '.join(partial_dates)}")

    # Execution quality
    exec_rollup = summary.get("agent_execution_quality_rollup", {})
    if exec_rollup and exec_rollup.get("dates_checked", 0) > 0:
        fallback_dates = exec_rollup.get("fallback_only_dates", [])
        degraded_dates = exec_rollup.get("degraded_dates", [])
        if fallback_dates:
            findings.append(f"Fallback-only execution dates: {', '.join(fallback_dates)}")
        if degraded_dates:
            findings.append(f"Degraded execution dates: {', '.join(degraded_dates)}")
        healthy_exec = exec_rollup.get("healthy_dates", [])
        findings.append(f"Healthy execution dates: {len(healthy_exec)}/{exec_rollup.get('dates_checked', 0)}")

    # Presence effect
    presence = summary.get("agent_score_presence_effect", {})
    spread = presence.get("spread", {})
    spread_avg = spread.get("avg_adjusted_return_pct")
    if spread_avg is not None:
        findings.append(f"Presence effect spread: {spread_avg:+.2f}% (present vs missing)")
    has_presence = presence.get("interpretation", {}).get("has_presence_signal", False)
    findings.append(f"Presence signal: {'Yes' if has_presence else 'No'}")

    # Market-adjusted
    market_adj = summary.get("agent_score_market_adjusted", {})
    has_alpha = market_adj.get("interpretation", {}).get("has_positive_alpha_signal", False)
    findings.append(f"Market-adjusted alpha: {'Yes' if has_alpha else 'No'}")

    # Pipeline warnings
    pipeline_warnings = summary.get("pipeline_warnings", [])
    if pipeline_warnings:
        findings.append(f"Pipeline warnings: {len(pipeline_warnings)} active")

    # Data quality
    dq = summary.get("agent_score_data_quality", {})
    excluded = dq.get("excluded_from_agent_score_interpretation", [])
    if excluded:
        findings.append(f"Excluded dates (low AIHF coverage): {', '.join(excluded)}")

    return findings


def build_recommended_actions(summary: dict) -> list[str]:
    """Generate recommended actions based on summary data."""
    actions = []

    # Check for poor coverage dates
    cov_rollup = summary.get("agent_score_coverage_quality_rollup", {})
    poor_dates = cov_rollup.get("poor_dates", [])
    if poor_dates:
        actions.append(
            f"Re-run AIHF bridge for poor coverage dates: {', '.join(poor_dates)}. "
            f"These dates have low agent_score coverage which limits calibration quality."
        )

    # Check for excluded dates
    dq = summary.get("agent_score_data_quality", {})
    excluded = dq.get("excluded_from_agent_score_interpretation", [])
    if excluded:
        actions.append(
            f"Address excluded dates ({', '.join(excluded)}): "
            f"AIHF ranking coverage is below threshold. Consider re-running bridge."
        )

    # Always recommend accumulating more data
    actions.append(
        "Accumulate more trading days before drawing conclusions about agent_score alpha. "
        "Current sample sizes are insufficient for robust statistical inference."
    )

    # Weight change guidance
    actions.append(
        "Do not change scoring weights yet. Agent score presence shows positive separation "
        "but market-adjusted alpha is not yet robust enough for weight adjustments."
    )

    # Outlier context
    outlier_ctx = summary.get("agent_score_outlier_context", {}).get("outlier_dates", {})
    if outlier_ctx:
        outlier_dates = list(outlier_ctx.keys())
        actions.append(
            f"Investigate outlier dates ({', '.join(outlier_dates)}): "
            f"Verify whether returns are market-driven or agent-score-driven."
        )

    return actions


def build_health_report(summary: dict, source_path: str) -> dict:
    """Build the complete health report dict."""
    overall_status = determine_overall_status(summary)

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "source_summary_path": source_path,
        "overall_status": overall_status,
        "headline_findings": build_headline_findings(summary),
        "agent_score_recommendation": summary.get("layers", {}).get("agent_score", {}).get("recommendation", {}),
        "data_quality": summary.get("agent_score_data_quality", {}),
        "coverage_quality": summary.get("agent_score_coverage_quality_rollup", {}),
        "presence_effect": summary.get("agent_score_presence_effect", {}),
        "market_adjusted": summary.get("agent_score_market_adjusted", {}),
        "date_influence": summary.get("agent_score_date_influence", {}),
        "outlier_context": summary.get("agent_score_outlier_context", {}),
        "execution_quality": summary.get("agent_execution_quality_rollup", {}),
        "pipeline_warnings": summary.get("pipeline_warnings", []),
        "recommended_actions": build_recommended_actions(summary),
    }


def generate_markdown(report: dict) -> str:
    """Render the health report as Markdown."""
    lines = [
        "# Agent Score Calibration Health",
        "",
        f"**Generated At**: {report.get('generated_at', '')}",
        f"**Source**: {report.get('source_summary_path', '')}",
        "",
        "## Overall Status",
        "",
    ]

    status = report.get("overall_status", "unknown")
    status_icon = {"healthy": "✅", "monitor": "⚠️", "risk": "🔴", "insufficient_evidence": "⚠️"}.get(status, "❓")
    lines.append(f"**Status**: {status_icon} **{status.upper()}**")
    lines.append("")

    # Headline findings
    lines.append("## Headline Findings")
    lines.append("")
    for finding in report.get("headline_findings", []):
        lines.append(f"- {finding}")
    lines.append("")

    # Data Quality
    dq = report.get("data_quality", {})
    if dq:
        lines.append("## Data Quality")
        lines.append("")
        lines.append(f"- **Bridge dates checked**: {dq.get('bridge_dates_checked', 0)}")
        healthy = dq.get("healthy_dates", [])
        partial = dq.get("partial_dates", [])
        stale = dq.get("stale_or_mismatched_dates", [])
        excluded = dq.get("excluded_from_agent_score_interpretation", [])
        lines.append(f"- **Healthy**: {len(healthy)} ({', '.join(healthy) if healthy else '-'})")
        lines.append(f"- **Partial**: {len(partial)} ({', '.join(partial) if partial else '-'})")
        lines.append(f"- **Stale/Mismatched**: {len(stale)} ({', '.join(stale) if stale else '-'})")
        lines.append(f"- **Excluded from interpretation**: {len(excluded)} ({', '.join(excluded) if excluded else '-'})")
        lines.append("")

    # Coverage Quality
    cov = report.get("coverage_quality", {})
    if cov and cov.get("dates_checked", 0) > 0:
        lines.append("## Coverage Quality")
        lines.append("")
        lines.append(f"- **Dates checked**: {cov.get('dates_checked', 0)}")
        lines.append(f"- **Healthy**: {len(cov.get('healthy_dates', []))}")
        lines.append(f"- **Partial**: {len(cov.get('partial_dates', []))}")
        lines.append(f"- **Poor**: {len(cov.get('poor_dates', []))}")
        lines.append(f"- **Avg coverage ratio**: {cov.get('avg_coverage_ratio', 0):.1%}")
        lines.append("")

    # Presence Effect
    pe = report.get("presence_effect", {})
    if pe and pe.get("present", {}).get("sample_count", 0) > 0:
        lines.append("## Presence Effect")
        lines.append("")
        present = pe.get("present", {})
        missing = pe.get("missing", {})
        spread = pe.get("spread", {})
        lines.append("| Group | Samples | Avg Adjusted Return | Hit Rate Above Date Mean |")
        lines.append("|-------|---------|--------------------|-----------------------|")
        p_avg = present.get("avg_adjusted_return_pct")
        p_hr = present.get("hit_rate_above_date_mean")
        m_avg = missing.get("avg_adjusted_return_pct")
        m_hr = missing.get("hit_rate_above_date_mean")
        p_avg_str = f"{p_avg:+.2f}%" if p_avg is not None else "-"
        p_hr_str = f"{p_hr:.1%}" if p_hr is not None else "-"
        m_avg_str = f"{m_avg:+.2f}%" if m_avg is not None else "-"
        m_hr_str = f"{m_hr:.1%}" if m_hr is not None else "-"
        lines.append(f"| **Present** | {present.get('sample_count', 0)} | {p_avg_str} | {p_hr_str} |")
        lines.append(f"| **Missing** | {missing.get('sample_count', 0)} | {m_avg_str} | {m_hr_str} |")
        s_avg = spread.get("avg_adjusted_return_pct")
        s_hr = spread.get("hit_rate_diff")
        s_avg_str = f"{s_avg:+.2f}%" if s_avg is not None else "-"
        s_hr_str = f"{s_hr:+.1%}" if s_hr is not None else "-"
        lines.append(f"| **Spread** | | {s_avg_str} | {s_hr_str} |")
        lines.append("")
        has_signal = pe.get("interpretation", {}).get("has_presence_signal", False)
        lines.append(f"**Presence signal**: {'Yes' if has_signal else 'No'}")
        lines.append("")

    # Market-Adjusted View
    ma = report.get("market_adjusted", {})
    if ma and ma.get("date_baselines"):
        lines.append("## Market-Adjusted View")
        lines.append("")
        lines.append(f"- **Method**: {ma.get('method', 'unknown')}")
        lines.append("")
        buckets = ma.get("buckets", {})
        if buckets:
            lines.append("| Bucket | Samples | Avg Adjusted Return | Hit Rate Above Date Mean |")
            lines.append("|--------|---------|--------------------|-----------------------|")
            for bname in ("80+", "60-80", "40-60", "<40", "missing"):
                bd = buckets.get(bname, {})
                sc = bd.get("sample_count", 0)
                avg = bd.get("avg_adjusted_return_pct")
                hr = bd.get("hit_rate_above_date_mean")
                avg_str = f"{avg:+.2f}%" if avg is not None else "-"
                hr_str = f"{hr:.1%}" if hr is not None else "-"
                lines.append(f"| {bname} | {sc} | {avg_str} | {hr_str} |")
            lines.append("")
        has_alpha = ma.get("interpretation", {}).get("has_positive_alpha_signal", False)
        lines.append(f"**Positive alpha signal**: {'Yes' if has_alpha else 'No'}")
        lines.append("")

    # Date Influence
    di = report.get("date_influence", {})
    if di and di.get("date_count_with_samples", 0) > 0:
        lines.append("## Date Influence")
        lines.append("")
        lines.append(f"- **Total samples**: {di.get('total_samples', 0)}")
        lines.append(f"- **Top positive date**: {di.get('top_positive_date', '-')}")
        lines.append(f"- **Top negative date**: {di.get('top_negative_date', '-')}")
        conc = di.get("concentration", {})
        lines.append(f"- **Largest date sample share**: {conc.get('largest_date_sample_share', 0):.1%}")
        lines.append(f"- **Largest positive return contribution share**: {conc.get('largest_positive_return_contribution_share', 0):.1%}")
        di_warnings = di.get("warnings", [])
        if di_warnings:
            lines.append("")
            lines.append("### Date Influence Warnings")
            lines.append("")
            lines.append("| Date | Type | Message |")
            lines.append("|------|------|---------|")
            for w in di_warnings:
                lines.append(f"| {w.get('date', '')} | {w.get('type', '')} | {w.get('message', '')} |")
        lines.append("")

    # Outlier Context
    oc = report.get("outlier_context", {}).get("outlier_dates", {})
    if oc:
        lines.append("## Outlier Context")
        lines.append("")
        lines.append("| Date | Interpretation | Avg Return | Hit Rate | Top Contributors | Sectors |")
        lines.append("|------|---------------|------------|----------|-----------------|---------|")
        for date in sorted(oc.keys()):
            ctx = oc[date]
            interp = ctx.get("interpretation", "unknown")
            avg = ctx.get("avg_return_pct")
            avg_str = f"{avg:.2f}%" if avg is not None else "-"
            hit = ctx.get("hit_rate")
            hit_str = f"{hit:.1%}" if hit is not None else "-"
            contribs = ctx.get("top_return_contributors", [])
            contrib_str = ", ".join(f"{c['code']}({c['forward_return_1d']:+.1f}%)" for c in contribs[:3]) if contribs else "-"
            sd = ctx.get("sector_distribution", {})
            sd_sorted = sorted(sd.items(), key=lambda x: x[1], reverse=True)[:3]
            sector_str = ", ".join(f"{s}:{n}" for s, n in sd_sorted) if sd_sorted else "-"
            lines.append(f"| {date} | {interp} | {avg_str} | {hit_str} | {contrib_str} | {sector_str} |")
        lines.append("")

    # Agent Execution Quality
    exec_rollup = report.get("execution_quality", {})
    if exec_rollup and exec_rollup.get("dates_checked", 0) > 0:
        lines.append("## Agent Execution Quality")
        lines.append("")
        lines.append(f"- **Dates checked**: {exec_rollup.get('dates_checked', 0)}")
        healthy = exec_rollup.get("healthy_dates", [])
        degraded = exec_rollup.get("degraded_dates", [])
        fallback = exec_rollup.get("fallback_only_dates", [])
        lines.append(f"- **Healthy**: {len(healthy)} ({', '.join(healthy) if healthy else '-'})")
        lines.append(f"- **Degraded**: {len(degraded)} ({', '.join(degraded) if degraded else '-'})")
        lines.append(f"- **Fallback-only**: {len(fallback)} ({', '.join(fallback) if fallback else '-'})")
        lines.append(f"- **Default score total**: {exec_rollup.get('default_score_total', 0)}")
        lines.append("")

    # Pipeline Warnings
    pw = report.get("pipeline_warnings", [])
    if pw:
        lines.append("## Pipeline Warnings")
        lines.append("")
        for w in pw:
            severity = w.get("severity", "warn").upper()
            lines.append(f"- [{severity}] **{w.get('type', 'unknown')}**: {w.get('message', '')}")
        lines.append("")

    # Recommended Actions
    lines.append("## Recommended Actions")
    lines.append("")
    for i, action in enumerate(report.get("recommended_actions", []), 1):
        lines.append(f"{i}. {action}")
    lines.append("")

    # Disclaimer
    lines.append("---")
    lines.append("")
    lines.append("**No scoring weight changes are recommended yet.**")
    lines.append("This report is for diagnostic and research purposes only. It does not constitute investment advice.")
    lines.append("")

    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Agent Score Calibration Health Report")
    parser.add_argument(
        "--summary-path",
        required=True,
        help="Path to scoring_calibration_summary.json",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for health report",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary_path = Path(args.summary_path)
    output_dir = Path(args.output_dir)

    if not summary_path.exists():
        print(f"ERROR: Summary file not found: {summary_path}", file=sys.stderr)
        return 2

    summary = load_summary(summary_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_health_report(summary, str(summary_path))

    json_path = output_dir / "agent_score_health_report.json"
    md_path = output_dir / "agent_score_health_report.md"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(generate_markdown(report), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print()
    print(f"Overall status: {report.get('overall_status', 'unknown').upper()}")
    print(f"Headline findings: {len(report.get('headline_findings', []))}")
    print(f"Recommended actions: {len(report.get('recommended_actions', []))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
