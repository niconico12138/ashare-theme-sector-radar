"""Tests for Agent Score Calibration Health Report."""

import json

import pytest

from scripts.export_agent_score_health_report import (
    build_headline_findings,
    build_health_report,
    build_recommended_actions,
    determine_overall_status,
    generate_markdown,
    main,
)


def _make_summary(
    pipeline_warnings=None,
    recommendation_type="insufficient_evidence",
    has_presence_signal=False,
    has_alpha_signal=False,
    poor_dates=None,
    excluded_dates=None,
    presence_spread=None,
):
    """Helper to build a minimal summary dict."""
    return {
        "layers": {
            "agent_score": {
                "recommendation": {
                    "type": recommendation_type,
                    "reason": "test",
                    "notes": [],
                },
            },
        },
        "agent_score_data_quality": {
            "bridge_dates_checked": 7,
            "healthy_dates": ["2026-06-29"],
            "partial_dates": [],
            "stale_or_mismatched_dates": [],
            "excluded_from_agent_score_interpretation": excluded_dates or [],
        },
        "agent_score_coverage_quality_rollup": {
            "dates_checked": 7,
            "healthy_dates": ["2026-06-29"],
            "partial_dates": [],
            "poor_dates": poor_dates or [],
            "avg_coverage_ratio": 0.82,
            "warnings": [],
        },
        "agent_score_presence_effect": {
            "present": {"sample_count": 65, "avg_adjusted_return_pct": 0.24, "hit_rate_above_date_mean": 0.37},
            "missing": {"sample_count": 6, "avg_adjusted_return_pct": -2.55, "hit_rate_above_date_mean": 0.33},
            "spread": {"avg_adjusted_return_pct": presence_spread or 2.79, "hit_rate_diff": 0.04},
            "interpretation": {"has_presence_signal": has_presence_signal, "notes": []},
        },
        "agent_score_market_adjusted": {
            "method": "date_mean_adjusted_1d",
            "date_baselines": {"2026-07-02": {"candidate_mean_1d_return": 7.05, "candidate_count": 8}},
            "buckets": {},
            "interpretation": {"has_positive_alpha_signal": has_alpha_signal, "notes": []},
        },
        "agent_score_date_influence": {
            "date_count_with_samples": 5,
            "total_samples": 71,
            "top_positive_date": "2026-07-02",
            "top_negative_date": "2026-07-07",
            "concentration": {"largest_date_sample_share": 0.28, "largest_positive_return_contribution_share": 0.56},
            "warnings": [],
        },
        "agent_score_outlier_context": {"outlier_dates": {}},
        "pipeline_warnings": pipeline_warnings or [],
    }


# ---------------------------------------------------------------------------
# determine_overall_status
# ---------------------------------------------------------------------------


def test_overall_status_risk_with_warnings():
    summary = _make_summary(pipeline_warnings=[{"type": "test", "severity": "warn", "message": "test"}])
    assert determine_overall_status(summary) == "risk"


def test_overall_status_monitor_insufficient_evidence():
    summary = _make_summary(recommendation_type="insufficient_evidence")
    assert determine_overall_status(summary) == "monitor"


def test_overall_status_healthy_with_presence_and_alpha():
    summary = _make_summary(
        recommendation_type="keep_candidate",
        has_presence_signal=True,
        has_alpha_signal=True,
    )
    assert determine_overall_status(summary) == "healthy"


def test_overall_status_monitor_without_alpha():
    summary = _make_summary(recommendation_type="keep_candidate", has_presence_signal=True, has_alpha_signal=False)
    assert determine_overall_status(summary) == "monitor"


# ---------------------------------------------------------------------------
# build_headline_findings
# ---------------------------------------------------------------------------


def test_headline_findings_includes_key_metrics():
    summary = _make_summary(
        poor_dates=["2026-07-01"],
        has_presence_signal=True,
        excluded_dates=["2026-07-01"],
    )
    findings = build_headline_findings(summary)
    assert any("insufficient_evidence" in f for f in findings)
    assert any("coverage" in f.lower() for f in findings)
    assert any("2026-07-01" in f for f in findings)
    assert any("presence" in f.lower() for f in findings)
    assert any("excluded" in f.lower() for f in findings)


# ---------------------------------------------------------------------------
# build_recommended_actions
# ---------------------------------------------------------------------------


def test_recommended_actions_include_rerun_poor_dates():
    summary = _make_summary(poor_dates=["2026-07-01"])
    actions = build_recommended_actions(summary)
    assert any("2026-07-01" in a for a in actions)
    assert any("rerun" in a.lower() or "re-run" in a.lower() for a in actions)


def test_recommended_actions_include_no_weight_change():
    summary = _make_summary()
    actions = build_recommended_actions(summary)
    assert any("weight" in a.lower() for a in actions)


def test_recommended_actions_include_accumulate_data():
    summary = _make_summary()
    actions = build_recommended_actions(summary)
    assert any("accumulate" in a.lower() or "more trading" in a.lower() for a in actions)


# ---------------------------------------------------------------------------
# build_health_report
# ---------------------------------------------------------------------------


def test_health_report_structure():
    summary = _make_summary()
    report = build_health_report(summary, "test/path.json")
    assert report["schema_version"] == "1.0"
    assert report["overall_status"] == "monitor"
    assert "headline_findings" in report
    assert "recommended_actions" in report
    assert "pipeline_warnings" in report
    assert report["source_summary_path"] == "test/path.json"


# ---------------------------------------------------------------------------
# generate_markdown
# ---------------------------------------------------------------------------


def test_markdown_contains_required_sections():
    summary = _make_summary(
        poor_dates=["2026-07-01"],
        has_presence_signal=True,
        pipeline_warnings=[{"type": "poor_agent_score_coverage_dates", "severity": "warn", "dates": ["2026-07-01"], "message": "test"}],
    )
    report = build_health_report(summary, "test/path.json")
    md = generate_markdown(report)
    assert "Agent Score Calibration Health" in md
    assert "Overall Status" in md
    assert "Headline Findings" in md
    assert "Data Quality" in md
    assert "Coverage Quality" in md
    assert "Presence Effect" in md
    assert "Market-Adjusted View" in md
    assert "Date Influence" in md
    assert "Pipeline Warnings" in md
    assert "Recommended Actions" in md
    assert "No scoring weight changes are recommended yet." in md


def test_markdown_risk_status():
    summary = _make_summary(pipeline_warnings=[{"type": "test", "severity": "warn", "message": "test"}])
    report = build_health_report(summary, "test/path.json")
    md = generate_markdown(report)
    assert "RISK" in md


def test_markdown_includes_poor_dates_in_actions():
    summary = _make_summary(poor_dates=["2026-07-01"])
    report = build_health_report(summary, "test/path.json")
    md = generate_markdown(report)
    assert "2026-07-01" in md


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_writes_json_and_md(tmp_path):
    summary = _make_summary()
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    out_dir = tmp_path / "health"
    exit_code = main(["--summary-path", str(summary_path), "--output-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "agent_score_health_report.json").exists()
    assert (out_dir / "agent_score_health_report.md").exists()

    report = json.loads((out_dir / "agent_score_health_report.json").read_text(encoding="utf-8"))
    assert report["overall_status"] == "monitor"
    assert len(report["headline_findings"]) > 0
    assert len(report["recommended_actions"]) > 0


# ---------------------------------------------------------------------------
# Execution Quality
# ---------------------------------------------------------------------------


def test_overall_status_risk_with_fallback_only():
    summary = _make_summary()
    summary["agent_execution_quality_rollup"] = {
        "dates_checked": 1,
        "healthy_dates": [],
        "degraded_dates": [],
        "fallback_only_dates": ["2026-07-01"],
        "unknown_dates": [],
        "default_score_total": 18,
        "warnings": [{"date": "2026-07-01", "type": "fallback_only_agent_execution", "message": "test"}],
    }
    # Override pipeline_warnings to be empty so fallback_only is the trigger
    summary["pipeline_warnings"] = []
    assert determine_overall_status(summary) == "risk"


def test_health_report_includes_execution_quality():
    summary = _make_summary()
    summary["agent_execution_quality_rollup"] = {
        "dates_checked": 7,
        "healthy_dates": ["2026-06-29", "2026-07-02", "2026-07-03", "2026-07-06", "2026-07-08"],
        "degraded_dates": [],
        "fallback_only_dates": [],
        "unknown_dates": [],
        "default_score_total": 0,
        "warnings": [],
    }
    report = build_health_report(summary, "test/path.json")
    assert "execution_quality" in report
    assert report["execution_quality"]["healthy_dates"] == ["2026-06-29", "2026-07-02", "2026-07-03", "2026-07-06", "2026-07-08"]


def test_markdown_includes_execution_quality():
    summary = _make_summary()
    summary["agent_execution_quality_rollup"] = {
        "dates_checked": 7,
        "healthy_dates": ["2026-06-29"],
        "degraded_dates": [],
        "fallback_only_dates": [],
        "unknown_dates": [],
        "default_score_total": 0,
        "warnings": [],
    }
    report = build_health_report(summary, "test/path.json")
    md = generate_markdown(report)
    assert "Agent Execution Quality" in md
    assert "Healthy" in md
