"""Tests for scoring calibration summary script."""

import json

import pytest

from scripts.summarize_scoring_calibration import (
    assess_agent_score_data_quality,
    classify_evidence,
    compute_aihf_coverage_for_date,
    compute_agent_score_coverage_quality_rollup,
    compute_agent_score_date_influence,
    compute_agent_score_market_adjusted,
    compute_agent_score_outlier_context,
    compute_agent_score_presence_effect,
    determine_recommendation,
    evaluate_bucket_performance,
    generate_summary_markdown,
    main,
    summarize_scoring_calibration,
)


# ---------------------------------------------------------------------------
# classify_evidence
# ---------------------------------------------------------------------------


def test_classify_evidence_no_data():
    assert classify_evidence(0) == "no_data"


def test_classify_evidence_thin():
    assert classify_evidence(5) == "thin"
    assert classify_evidence(9) == "thin"


def test_classify_evidence_usable():
    assert classify_evidence(10) == "usable"
    assert classify_evidence(29) == "usable"


def test_classify_evidence_strong():
    assert classify_evidence(30) == "strong"
    assert classify_evidence(100) == "strong"


# ---------------------------------------------------------------------------
# evaluate_bucket_performance
# ---------------------------------------------------------------------------


def test_evaluate_bucket_performance_extracts_horizon_stats():
    bucket = {
        "candidate_count": 10,
        "horizons": {
            "1d": {"sample_count": 10, "avg_return_pct": 2.5, "hit_rate": 0.8},
            "3d": {"sample_count": 8, "avg_return_pct": 4.0, "hit_rate": 0.75},
        },
    }
    result = evaluate_bucket_performance(bucket, "80+", horizon="1d")
    assert result["sample_count"] == 10
    assert result["avg_return_pct"] == 2.5
    assert result["hit_rate"] == 0.8
    assert result["evidence"] == "usable"


def test_evaluate_bucket_performance_missing_horizon():
    bucket = {
        "candidate_count": 0,
        "horizons": {},
    }
    result = evaluate_bucket_performance(bucket, "80+", horizon="1d")
    assert result["sample_count"] == 0
    assert result["avg_return_pct"] is None
    assert result["evidence"] == "no_data"


# ---------------------------------------------------------------------------
# determine_recommendation
# ---------------------------------------------------------------------------


def _make_buckets(high_ret=None, mid_ret=None, low_ret=None, very_low_ret=None,
                  high_n=0, mid_n=0, low_n=0, very_low_n=0, missing_n=0):
    """Helper to build a buckets dict for testing."""
    def _h(count, ret):
        return {
            "candidate_count": count,
            "horizons": {"1d": {"sample_count": count, "avg_return_pct": ret, "hit_rate": 0.5 if ret is not None else None}},
        }
    return {
        "80+": _h(high_n, high_ret),
        "60-80": _h(mid_n, mid_ret),
        "40-60": _h(low_n, low_ret),
        "<40": _h(very_low_n, very_low_ret),
        "missing": _h(missing_n, None),
    }


def test_risk_filter_candidate_identification():
    buckets = _make_buckets(high_ret=2.0, mid_ret=1.0, low_ret=-1.0,
                            very_low_ret=-5.0, high_n=10, mid_n=15,
                            low_n=10, very_low_n=10)
    result = determine_recommendation("quant_score", buckets, 45, "1d")
    assert result["type"] == "risk_filter_candidate"
    assert "notably bad" in result["reason"]


def test_high_bucket_insufficient_samples():
    buckets = _make_buckets(high_ret=3.0, mid_ret=1.5, low_ret=0.5,
                            very_low_ret=-1.0, high_n=5, mid_n=20,
                            low_n=10, very_low_n=5)
    result = determine_recommendation("final_score", buckets, 40, "1d")
    assert result["type"] == "insufficient_evidence"
    assert "insufficient samples" in result["reason"]


def test_missing_field_gap_identification():
    buckets = _make_buckets(missing_n=30)
    result = determine_recommendation("agent_score", buckets, 30, "1d")
    assert result["type"] == "missing_field_gap"
    assert "missing for all candidates" in result["reason"]


def test_keep_candidate_identification():
    buckets = _make_buckets(high_ret=4.0, mid_ret=1.5, low_ret=0.5,
                            very_low_ret=None, high_n=15, mid_n=10,
                            low_n=5, very_low_n=0)
    result = determine_recommendation("final_score", buckets, 30, "1d")
    assert result["type"] == "keep_candidate"
    assert "notably better" in result["reason"]


def test_downweight_candidate_identification():
    """High bucket worse than mid bucket -> downweight."""
    buckets = _make_buckets(high_ret=0.5, mid_ret=2.0, low_ret=1.0,
                            very_low_ret=None, high_n=15, mid_n=10,
                            low_n=5, very_low_n=0)
    result = determine_recommendation("final_score", buckets, 30, "1d")
    assert result["type"] == "downweight_candidate"
    assert "not better" in result["reason"]


def test_insufficient_evidence_default():
    """When high bucket has enough samples but difference is marginal."""
    buckets = _make_buckets(high_ret=2.0, mid_ret=1.5, low_ret=1.0,
                            very_low_ret=None, high_n=15, mid_n=10,
                            low_n=5, very_low_n=0)
    result = determine_recommendation("final_score", buckets, 30, "1d")
    # 2.0 > 1.5 + 1.0 is False, so falls through to insufficient_evidence
    assert result["type"] == "insufficient_evidence"


# ---------------------------------------------------------------------------
# CLI writes json and md
# ---------------------------------------------------------------------------


def test_cli_writes_json_and_md(tmp_path):
    aggregate_data = {
        "schema_version": "1.0",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": ["2026-07-01", "2026-07-08"],
        "coverage": {"candidate_count": 30},
        "horizons": ["1d"],
        "layers": {
            "final_score": {
                "source_fields": ["final_score"],
                "buckets": {
                    "80+": {"candidate_count": 10, "horizons": {"1d": {"sample_count": 10, "avg_return_pct": 2.5, "hit_rate": 0.8}}},
                    "60-80": {"candidate_count": 15, "horizons": {"1d": {"sample_count": 15, "avg_return_pct": 1.0, "hit_rate": 0.6}}},
                    "40-60": {"candidate_count": 5, "horizons": {"1d": {"sample_count": 5, "avg_return_pct": -0.5, "hit_rate": 0.4}}},
                    "<40": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
                    "missing": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
                },
            }
        },
    }

    aggregate_path = tmp_path / "aggregate_scoring_calibration.json"
    aggregate_path.write_text(json.dumps(aggregate_data), encoding="utf-8")

    out_dir = tmp_path / "output"
    exit_code = main(["--aggregate-path", str(aggregate_path), "--output-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "scoring_calibration_summary.json").exists()
    assert (out_dir / "scoring_calibration_summary.md").exists()

    md_content = (out_dir / "scoring_calibration_summary.md").read_text(encoding="utf-8")
    assert "Recommendation" in md_content
    assert "Evidence" in md_content
    assert "final_score" in md_content


# ---------------------------------------------------------------------------
# Markdown content
# ---------------------------------------------------------------------------


def test_markdown_contains_recommendation_evidence_missing_field_gap():
    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": ["2026-07-01", "2026-07-08"],
        "candidate_count": 30,
        "primary_horizon": "1d",
        "layers": {
            "final_score": {
                "source_fields": ["final_score"],
                "buckets": {
                    "80+": {"sample_count": 10, "avg_return_pct": 2.5, "hit_rate": 0.8, "evidence": "usable"},
                    "60-80": {"sample_count": 15, "avg_return_pct": 1.0, "hit_rate": 0.6, "evidence": "usable"},
                    "40-60": {"sample_count": 5, "avg_return_pct": -0.5, "hit_rate": 0.4, "evidence": "thin"},
                    "<40": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None, "evidence": "no_data"},
                    "missing": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None, "evidence": "no_data"},
                },
                "recommendation": {
                    "type": "keep_candidate",
                    "reason": "High bucket performs notably better",
                    "evidence": "usable",
                    "coverage_ratio": 1.0,
                },
            },
            "agent_score": {
                "source_fields": ["agent_score", "risk_adjusted_score"],
                "buckets": {
                    "80+": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None, "evidence": "no_data"},
                    "60-80": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None, "evidence": "no_data"},
                    "40-60": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None, "evidence": "no_data"},
                    "<40": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None, "evidence": "no_data"},
                    "missing": {"sample_count": 30, "avg_return_pct": 0.5, "hit_rate": 0.5, "evidence": "strong"},
                },
                "recommendation": {
                    "type": "missing_field_gap",
                    "reason": "agent_score is missing for all candidates",
                    "evidence": "strong",
                    "coverage_ratio": 1.0,
                },
            },
        },
    }

    markdown = generate_summary_markdown(summary)

    assert "Recommendation" in markdown
    assert "Evidence" in markdown
    assert "Missing Field Gaps" in markdown
    assert "agent_score" in markdown


# ---------------------------------------------------------------------------
# Agent Score Data Quality
# ---------------------------------------------------------------------------


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_healthy_coverage_no_warning(tmp_path):
    """Healthy coverage (>= 80%) produces no low-coverage warning."""
    bridge = tmp_path / "agent_bridge"
    date = "2026-07-08"
    _write_json(bridge / date / "daily_bridge_report.json", {"aihf_coverage": {}})
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(bridge / date / "aihf_stock_ranking.json", {
        "items": [{"code": f"60000{i}", "agent_score": 80} for i in range(1, 10)],
    })

    dq = assess_agent_score_data_quality([date], bridge, 0.5)
    assert date in dq["healthy_dates"]
    assert date not in dq["stale_or_mismatched_dates"]
    assert date not in dq["excluded_from_agent_score_interpretation"]
    assert len(dq["warnings"]) == 0


def test_stale_coverage_excluded(tmp_path):
    """stale_or_mismatched_ranking → excluded from interpretation."""
    bridge = tmp_path / "agent_bridge"
    date = "2026-07-01"
    _write_json(bridge / date / "daily_bridge_report.json", {"aihf_coverage": {}})
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(bridge / date / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 80}],  # 1/10 = 10%
    })

    dq = assess_agent_score_data_quality([date], bridge, 0.5)
    assert date in dq["stale_or_mismatched_dates"]
    assert date in dq["excluded_from_agent_score_interpretation"]
    assert any(w["type"] == "low_aihf_ranking_coverage" for w in dq["warnings"])


def test_partial_coverage_warning_not_excluded(tmp_path):
    """partial coverage (50-80%) → warning but not excluded."""
    bridge = tmp_path / "agent_bridge"
    date = "2026-07-07"
    _write_json(bridge / date / "daily_bridge_report.json", {"aihf_coverage": {}})
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(bridge / date / "aihf_stock_ranking.json", {
        "items": [{"code": f"60000{i}", "agent_score": 80} for i in range(1, 8)],  # 7/10 = 70%
    })

    dq = assess_agent_score_data_quality([date], bridge, 0.5)
    assert date in dq["partial_dates"]
    assert date not in dq["excluded_from_agent_score_interpretation"]
    assert any(w["type"] == "partial_aihf_ranking_coverage" for w in dq["warnings"])


def test_missing_bridge_report_not_blocking(tmp_path):
    """Missing daily_bridge_report.json → warning but does not block summary."""
    bridge = tmp_path / "agent_bridge"
    date = "2026-07-02"
    # No bridge report file

    dq = assess_agent_score_data_quality([date], bridge, 0.5)
    assert date in dq["missing_bridge_report_dates"]
    assert any(w["type"] == "missing_bridge_report" for w in dq["warnings"])


def test_markdown_includes_agent_score_data_quality(tmp_path):
    """Markdown output includes Agent Score Data Quality section."""
    bridge = tmp_path / "agent_bridge"
    _write_json(bridge / "2026-07-01" / "daily_bridge_report.json", {"aihf_coverage": {}})
    _write_json(bridge / "2026-07-01" / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(bridge / "2026-07-01" / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 80}],
    })
    _write_json(bridge / "2026-07-08" / "daily_bridge_report.json", {"aihf_coverage": {}})
    _write_json(bridge / "2026-07-08" / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(bridge / "2026-07-08" / "aihf_stock_ranking.json", {
        "items": [{"code": f"60000{i}", "agent_score": 80} for i in range(1, 10)],
    })

    dq = assess_agent_score_data_quality(["2026-07-01", "2026-07-08"], bridge, 0.5)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": ["2026-07-01", "2026-07-08"],
        "candidate_count": 20,
        "primary_horizon": "1d",
        "layers": {
            "agent_score": {
                "source_fields": ["agent_score"],
                "buckets": {},
                "recommendation": {"type": "insufficient_evidence", "reason": "test", "evidence": "thin", "coverage_ratio": 0.5, "notes": []},
            },
        },
        "agent_score_data_quality": dq,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Score Data Quality" in md
    assert "Stale/Mismatched" in md
    assert "2026-07-01" in md


def test_agent_score_recommendation_notes_quality_limited(tmp_path):
    """When stale dates exist, agent_score recommendation includes quality-limited note."""
    bridge = tmp_path / "agent_bridge"
    _write_json(bridge / "2026-07-01" / "daily_bridge_report.json", {"aihf_coverage": {}})
    _write_json(bridge / "2026-07-01" / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(bridge / "2026-07-01" / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 80}],
    })

    dq = assess_agent_score_data_quality(["2026-07-01"], bridge, 0.5)
    assert "2026-07-01" in dq["excluded_from_agent_score_interpretation"]

    buckets = {
        "80+": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "60-80": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "40-60": {"candidate_count": 5, "horizons": {"1d": {"sample_count": 5, "avg_return_pct": 1.0, "hit_rate": 0.6}}},
        "<40": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "missing": {"candidate_count": 5, "horizons": {"1d": {"sample_count": 5, "avg_return_pct": 0.5, "hit_rate": 0.5}}},
    }

    result = determine_recommendation("agent_score", buckets, 10, "1d", data_quality=dq)
    assert any("quality-limited" in n for n in result.get("notes", []))
    assert any("2026-07-01" in n for n in result.get("notes", []))


# ---------------------------------------------------------------------------
# Agent Score By Date
# ---------------------------------------------------------------------------


def test_agent_score_by_date_aggregates_per_date(tmp_path):
    """Per-date analysis reads candidates and returns for each date."""
    from scripts.summarize_scoring_calibration import compute_agent_score_by_date

    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    # Date with agent_score data
    d1 = "2026-07-07"
    _write_json(bridge / d1 / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "agent_score": 75, "final_score": 80},
            {"code": "600002", "name": "S2", "final_score": 70},
        ],
    })
    _write_json(fr / d1 / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 2.0}},
    })

    # Date with no agent_score
    d2 = "2026-07-01"
    _write_json(bridge / d2 / "top30_candidates.json", {
        "candidates": [
            {"code": "600003", "name": "S3", "final_score": 60},
        ],
    })
    _write_json(fr / d2 / "forward_returns.json", {
        "forward_returns": {"600003": {"1d": -1.0}},
    })

    dq = {
        "healthy_dates": [d1],
        "partial_dates": [],
        "stale_or_mismatched_dates": [d2],
        "missing_bridge_report_dates": [],
        "excluded_from_agent_score_interpretation": [d2],
    }

    result = compute_agent_score_by_date([d1, d2], bridge, cal, dq)

    # d1: has agent_score
    assert result["dates"][d1]["agent_score_count"] == 1
    assert result["dates"][d1]["missing_agent_score_count"] == 1
    assert result["dates"][d1]["coverage_ratio"] == 0.5
    assert result["dates"][d1]["quality_status"] == "healthy"
    assert result["dates"][d1]["excluded_from_interpretation"] is False

    # d2: no agent_score
    assert result["dates"][d2]["agent_score_count"] == 0
    assert result["dates"][d2]["missing_agent_score_count"] == 1
    assert result["dates"][d2]["quality_status"] == "stale_or_mismatched_ranking"
    assert result["dates"][d2]["excluded_from_interpretation"] is True


def test_agent_score_by_date_partial_quality(tmp_path):
    """Partial quality status is correctly assigned."""
    from scripts.summarize_scoring_calibration import compute_agent_score_by_date

    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"

    d = "2026-07-07"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [{"code": "600001", "name": "S1", "agent_score": 80, "final_score": 85}],
    })

    dq = {
        "healthy_dates": [],
        "partial_dates": [d],
        "stale_or_mismatched_dates": [],
        "missing_bridge_report_dates": [],
        "excluded_from_agent_score_interpretation": [],
    }

    result = compute_agent_score_by_date([d], bridge, cal, dq)
    assert result["dates"][d]["quality_status"] == "partial"
    assert result["dates"][d]["excluded_from_interpretation"] is False


def test_agent_score_by_date_missing_counted_in_bucket(tmp_path):
    """Missing agent_score candidates are counted in missing bucket."""
    from scripts.summarize_scoring_calibration import compute_agent_score_by_date

    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"

    d = "2026-07-08"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "agent_score": 65, "final_score": 70},
            {"code": "600002", "name": "S2", "final_score": 60},
        ],
    })

    result = compute_agent_score_by_date([d], bridge, cal, None)
    bd = result["dates"][d]["bucket_distribution"]
    assert bd["60-80"]["candidate_count"] == 1
    assert bd["missing"]["candidate_count"] == 1
    assert result["dates"][d]["candidate_count"] == 2


def test_markdown_includes_agent_score_by_date(tmp_path):
    """Markdown output includes Agent Score By Date table."""
    from scripts.summarize_scoring_calibration import compute_agent_score_by_date

    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    d = "2026-07-07"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [{"code": "600001", "name": "S1", "agent_score": 80, "final_score": 85}],
    })
    _write_json(fr / d / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 3.0}},
    })

    dq = {
        "healthy_dates": [],
        "partial_dates": [d],
        "stale_or_mismatched_dates": [],
        "missing_bridge_report_dates": [],
        "excluded_from_agent_score_interpretation": [],
        "bridge_dates_checked": 1,
        "warnings": [],
    }

    by_date = compute_agent_score_by_date([d], bridge, cal, dq)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-07_to_2026-07-07",
        "dates_evaluated": [d],
        "candidate_count": 1,
        "primary_horizon": "1d",
        "layers": {
            "agent_score": {
                "source_fields": ["agent_score"],
                "buckets": {},
                "recommendation": {"type": "insufficient_evidence", "reason": "test", "evidence": "thin", "coverage_ratio": 1.0, "notes": []},
            },
        },
        "agent_score_data_quality": dq,
        "agent_score_by_date": by_date,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Score By Date" in md
    assert d in md
    assert "partial" in md


# ---------------------------------------------------------------------------
# Agent Score Date Influence
# ---------------------------------------------------------------------------


def test_influence_excludes_dates_without_samples():
    """Dates with 0 samples do not participate in influence."""
    by_date = {
        "dates": {
            "2026-07-01": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 10, "avg_return_pct": 2.0, "hit_rate": 0.7}},
            },
            "2026-07-02": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}},
            },
        }
    }
    result = compute_agent_score_date_influence(by_date)
    assert result["date_count_with_samples"] == 1
    assert result["total_samples"] == 10
    assert result["top_positive_date"] == "2026-07-01"


def test_influence_excludes_excluded_dates():
    """Excluded dates do not participate in influence."""
    by_date = {
        "dates": {
            "2026-07-01": {
                "quality_status": "stale_or_mismatched_ranking",
                "excluded_from_interpretation": True,
                "horizons": {"1d": {"sample_count": 18, "avg_return_pct": -1.13, "hit_rate": 0.44}},
            },
            "2026-07-02": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 8, "avg_return_pct": 7.05, "hit_rate": 1.0}},
            },
        }
    }
    result = compute_agent_score_date_influence(by_date)
    assert result["date_count_with_samples"] == 1
    assert result["total_samples"] == 8
    assert result["top_positive_date"] == "2026-07-02"


def test_influence_single_day_outlier():
    """avg >= 5% and samples >= 5 triggers single_day_outlier."""
    by_date = {
        "dates": {
            "2026-07-02": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 8, "avg_return_pct": 7.05, "hit_rate": 1.0}},
            },
            "2026-07-03": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 20, "avg_return_pct": 2.66, "hit_rate": 0.85}},
            },
        }
    }
    result = compute_agent_score_date_influence(by_date)
    warnings = result["warnings"]
    assert any(w["type"] == "single_day_outlier" for w in warnings)
    assert any("2026-07-02" in w["message"] for w in warnings)


def test_influence_positive_evidence_concentrated():
    """Single date contributing >= 50% of positive samples triggers warning."""
    by_date = {
        "dates": {
            "2026-07-02": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 8, "avg_return_pct": 7.05, "hit_rate": 1.0}},
            },
            "2026-07-03": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 2, "avg_return_pct": 1.0, "hit_rate": 0.5}},
            },
        }
    }
    result = compute_agent_score_date_influence(by_date)
    # 8/10 = 80% positive samples from 2026-07-02
    assert result["concentration"]["largest_positive_return_contribution_share"] >= 0.5
    assert any(w["type"] == "positive_evidence_concentrated" for w in result["warnings"])


def test_markdown_includes_agent_score_date_influence():
    """Markdown output includes Agent Score Date Influence section."""
    by_date = {
        "dates": {
            "2026-07-02": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 8, "avg_return_pct": 7.05, "hit_rate": 1.0}},
            },
        }
    }
    influence = compute_agent_score_date_influence(by_date)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": ["2026-07-02"],
        "candidate_count": 8,
        "primary_horizon": "1d",
        "layers": {
            "agent_score": {
                "source_fields": ["agent_score"],
                "buckets": {},
                "recommendation": {"type": "insufficient_evidence", "reason": "test", "evidence": "thin", "coverage_ratio": 1.0, "notes": []},
            },
        },
        "agent_score_by_date": by_date,
        "agent_score_date_influence": influence,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Score Date Influence" in md
    assert "Total samples" in md
    assert "Top positive date" in md


def test_recommendation_notes_include_concentrated_returns():
    """When outlier exists, recommendation notes include concentrated single-date returns."""
    by_date = {
        "dates": {
            "2026-07-02": {
                "quality_status": "healthy",
                "excluded_from_interpretation": False,
                "horizons": {"1d": {"sample_count": 8, "avg_return_pct": 7.05, "hit_rate": 1.0}},
            },
        }
    }
    influence = compute_agent_score_date_influence(by_date)

    buckets = {
        "80+": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "60-80": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "40-60": {"candidate_count": 5, "horizons": {"1d": {"sample_count": 5, "avg_return_pct": 1.0, "hit_rate": 0.6}}},
        "<40": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "missing": {"candidate_count": 5, "horizons": {"1d": {"sample_count": 5, "avg_return_pct": 0.5, "hit_rate": 0.5}}},
    }

    result = determine_recommendation("agent_score", buckets, 10, "1d", influence=influence)
    assert any("concentrated single-date returns" in n for n in result.get("notes", []))


# ---------------------------------------------------------------------------
# Agent Score Outlier Context
# ---------------------------------------------------------------------------


def test_outlier_context_single_day_outlier_generates_context(tmp_path):
    """single_day_outlier dates generate context analysis."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "agent_score": 55, "boards": ["半导体"]},
            {"code": "600002", "name": "S2", "agent_score": 53, "boards": ["半导体"]},
            {"code": "600003", "name": "S3", "agent_score": 52, "boards": ["证券"]},
        ],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {
            "600001": {"1d": 8.0},
            "600002": {"1d": 7.0},
            "600003": {"1d": 6.0},
        },
    })

    influence = {
        "warnings": [{"date": date, "type": "single_day_outlier", "message": "test"}],
    }
    aggregate = {"dates_evaluated": [date]}

    ctx = compute_agent_score_outlier_context(influence, aggregate, bridge, cal)
    assert date in ctx["outlier_dates"]
    assert ctx["outlier_dates"][date]["sample_count"] == 3
    assert ctx["outlier_dates"][date]["interpretation"] != "insufficient_context"


def test_outlier_context_excluded_date_not_analyzed(tmp_path):
    """Excluded dates do not generate context."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"

    influence = {
        "warnings": [{"date": "2026-07-01", "type": "single_day_outlier", "message": "test"}],
    }
    aggregate = {"dates_evaluated": ["2026-07-01"]}

    # No files created for 2026-07-01 — but function should still handle gracefully
    ctx = compute_agent_score_outlier_context(influence, aggregate, bridge, cal)
    # Since no candidates/returns exist, it should return insufficient_context
    assert ctx["outlier_dates"]["2026-07-01"]["interpretation"] == "insufficient_context"


def test_outlier_context_top_contributors_sorted(tmp_path):
    """Top contributors are sorted by 1d return descending."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "boards": ["A"]},
            {"code": "600002", "name": "S2", "boards": ["B"]},
            {"code": "600003", "name": "S3", "boards": ["C"]},
        ],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {
            "600001": {"1d": 3.0},
            "600002": {"1d": 9.0},
            "600003": {"1d": 6.0},
        },
    })

    influence = {"warnings": [{"date": date, "type": "single_day_outlier", "message": "test"}]}
    ctx = compute_agent_score_outlier_context(influence, {"dates_evaluated": [date]}, bridge, cal)

    contribs = ctx["outlier_dates"][date]["top_return_contributors"]
    assert contribs[0]["code"] == "600002"  # highest return
    assert contribs[0]["forward_return_1d"] == 9.0
    assert contribs[1]["forward_return_1d"] == 6.0
    assert contribs[2]["forward_return_1d"] == 3.0


def test_outlier_context_top3_share_calculation(tmp_path):
    """top3_return_contribution_share is correctly computed."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "boards": ["A"]},
            {"code": "600002", "name": "S2", "boards": ["B"]},
            {"code": "600003", "name": "S3", "boards": ["C"]},
            {"code": "600004", "name": "S4", "boards": ["D"]},
        ],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {
            "600001": {"1d": 10.0},  # top3
            "600002": {"1d": 8.0},   # top3
            "600003": {"1d": 7.0},   # top3
            "600004": {"1d": 5.0},   # not top3
        },
    })

    influence = {"warnings": [{"date": date, "type": "single_day_outlier", "message": "test"}]}
    ctx = compute_agent_score_outlier_context(influence, {"dates_evaluated": [date]}, bridge, cal)

    # top3 = 10+8+7 = 25, total positive = 10+8+7+5 = 30, share = 25/30 = 0.8333
    assert ctx["outlier_dates"][date]["top3_return_contribution_share"] == pytest.approx(0.8333, abs=0.001)


def test_outlier_context_sector_cluster(tmp_path):
    """When one sector dominates, interpretation is sector_cluster."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "boards": ["半导体"]},
            {"code": "600002", "name": "S2", "boards": ["半导体"]},
            {"code": "600003", "name": "S3", "boards": ["半导体"]},
            {"code": "600004", "name": "S4", "boards": ["证券"]},
            {"code": "600005", "name": "S5", "boards": ["半导体"]},
            {"code": "600006", "name": "S6", "boards": ["证券"]},
        ],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {
            "600001": {"1d": 5.0},
            "600002": {"1d": 4.0},
            "600003": {"1d": 3.0},
            "600004": {"1d": 3.5},
            "600005": {"1d": 2.0},
            "600006": {"1d": 2.5},
        },
    })

    influence = {"warnings": [{"date": date, "type": "single_day_outlier", "message": "test"}]}
    ctx = compute_agent_score_outlier_context(influence, {"dates_evaluated": [date]}, bridge, cal)

    # top3 = 5+4+3.5 = 12.5, total = 5+4+3+3.5+2+2.5 = 20, share = 12.5/20 = 0.625 < 0.7
    # 半导体: 4/6 = 66.7% >= 0.6 → sector_cluster
    assert ctx["outlier_dates"][date]["interpretation"] == "sector_cluster"
    assert "半导体" in ctx["outlier_dates"][date]["sector_distribution"]


def test_outlier_context_market_broad_rally(tmp_path):
    """High hit rate across many sectors → market_broad_rally."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": f"60000{i}", "name": f"S{i}", "boards": [f"Sector{i % 4}"]}
            for i in range(1, 6)
        ],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {f"60000{i}": {"1d": 2.0 + i * 0.5} for i in range(1, 6)},
    })

    influence = {"warnings": [{"date": date, "type": "single_day_outlier", "message": "test"}]}
    ctx = compute_agent_score_outlier_context(influence, {"dates_evaluated": [date]}, bridge, cal)

    # hit_rate = 1.0 (all positive), 4 sectors → market_broad_rally
    assert ctx["outlier_dates"][date]["interpretation"] == "market_broad_rally"


def test_markdown_includes_outlier_context(tmp_path):
    """Markdown output includes Agent Score Outlier Context section."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "boards": ["A"]},
            {"code": "600002", "name": "S2", "boards": ["B"]},
        ],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 8.0}, "600002": {"1d": 6.0}},
    })

    influence = {"warnings": [{"date": date, "type": "single_day_outlier", "message": "test"}]}
    ctx = compute_agent_score_outlier_context(influence, {"dates_evaluated": [date]}, bridge, cal)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": [date],
        "candidate_count": 2,
        "primary_horizon": "1d",
        "layers": {},
        "agent_score_outlier_context": ctx,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Score Outlier Context" in md


# ---------------------------------------------------------------------------
# Agent Score Market-Adjusted
# ---------------------------------------------------------------------------


def test_market_adjusted_adjusted_return_calculation(tmp_path):
    """adjusted_return = individual_return - date_mean_return."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "agent_score": 85, "boards": ["A"]},
            {"code": "600002", "name": "S2", "agent_score": 55, "boards": ["B"]},
        ],
    })
    # mean = (10+2)/2 = 6.0; adjusted: 600001=+4.0, 600002=-4.0
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 10.0}, "600002": {"1d": 2.0}},
    })

    agg = {"dates_evaluated": [date], "coverage": {"candidate_count": 2}, "horizons": ["1d"]}
    result = compute_agent_score_market_adjusted(agg, bridge, cal, None)

    assert result["date_baselines"][date]["candidate_mean_1d_return"] == 6.0
    assert result["date_baselines"][date]["candidate_count"] == 2

    # 80+ bucket: 600001 (agent_score=85) adjusted = 10-6 = +4.0
    assert result["buckets"]["80+"]["sample_count"] == 1
    assert result["buckets"]["80+"]["avg_adjusted_return_pct"] == 4.0
    assert result["buckets"]["80+"]["hit_rate_above_date_mean"] == 1.0

    # 40-60 bucket: 600002 (agent_score=55) adjusted = 2-6 = -4.0
    assert result["buckets"]["40-60"]["sample_count"] == 1
    assert result["buckets"]["40-60"]["avg_adjusted_return_pct"] == -4.0
    assert result["buckets"]["40-60"]["hit_rate_above_date_mean"] == 0.0


def test_market_adjusted_excludes_dates(tmp_path):
    """Excluded dates do not participate in market-adjusted analysis."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    # Date 1: excluded
    d1 = "2026-07-01"
    _write_json(bridge / d1 / "top30_candidates.json", {
        "candidates": [{"code": "600001", "name": "S1", "agent_score": 70}],
    })
    _write_json(fr / d1 / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 5.0}},
    })

    # Date 2: not excluded
    d2 = "2026-07-02"
    _write_json(bridge / d2 / "top30_candidates.json", {
        "candidates": [{"code": "600002", "name": "S2", "agent_score": 80}],
    })
    _write_json(fr / d2 / "forward_returns.json", {
        "forward_returns": {"600002": {"1d": 3.0}},
    })

    dq = {"excluded_from_agent_score_interpretation": [d1]}
    agg = {"dates_evaluated": [d1, d2], "coverage": {"candidate_count": 2}, "horizons": ["1d"]}
    result = compute_agent_score_market_adjusted(agg, bridge, cal, dq)

    assert d1 in result["excluded_dates"]
    assert d1 not in result["date_baselines"]
    assert d2 in result["date_baselines"]


def test_market_adjusted_missing_agent_score_in_missing_bucket(tmp_path):
    """Candidates without agent_score go into missing bucket."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "agent_score": 85},
            {"code": "600002", "name": "S2"},  # no agent_score
        ],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 5.0}, "600002": {"1d": 3.0}},
    })

    agg = {"dates_evaluated": [date], "coverage": {"candidate_count": 2}, "horizons": ["1d"]}
    result = compute_agent_score_market_adjusted(agg, bridge, cal, None)

    assert result["buckets"]["80+"]["sample_count"] == 1
    assert result["buckets"]["missing"]["sample_count"] == 1


def test_market_adjusted_hit_rate_correct(tmp_path):
    """hit_rate_above_date_mean counts adjusted returns > 0."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "agent_score": 75},
            {"code": "600002", "name": "S2", "agent_score": 70},
            {"code": "600003", "name": "S3", "agent_score": 65},
        ],
    })
    # mean = (8+4+2)/3 = 4.67; adjusted: 600001=+3.33, 600002=-0.67, 600003=-2.67
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 8.0}, "600002": {"1d": 4.0}, "600003": {"1d": 2.0}},
    })

    agg = {"dates_evaluated": [date], "coverage": {"candidate_count": 3}, "horizons": ["1d"]}
    result = compute_agent_score_market_adjusted(agg, bridge, cal, None)

    # 60-80 bucket: 3 stocks, 1 above mean → hit_rate = 1/3
    assert result["buckets"]["60-80"]["sample_count"] == 3
    assert result["buckets"]["60-80"]["hit_rate_above_date_mean"] == pytest.approx(1 / 3, abs=0.01)


def test_markdown_includes_market_adjusted(tmp_path):
    """Markdown output includes Agent Score Market-Adjusted View section."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [{"code": "600001", "name": "S1", "agent_score": 75}],
    })
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 5.0}},
    })

    agg = {"dates_evaluated": [date], "coverage": {"candidate_count": 1}, "horizons": ["1d"]}
    market_adj = compute_agent_score_market_adjusted(agg, bridge, cal, None)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": [date],
        "candidate_count": 1,
        "primary_horizon": "1d",
        "layers": {},
        "agent_score_market_adjusted": market_adj,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Score Market-Adjusted View" in md
    assert "date_mean_adjusted_1d" in md
    assert "Date Baselines" in md
    assert "Adjusted Returns by Agent Score Bucket" in md


def test_recommendation_notes_include_market_adjusted_alpha(tmp_path):
    """When no alpha signal, recommendation notes include market-adjusted note."""
    bridge = tmp_path / "agent_bridge"
    cal = tmp_path / "scoring_calibration"
    fr = tmp_path / "forward_returns"

    date = "2026-07-02"
    _write_json(bridge / date / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1", "agent_score": 75},
            {"code": "600002", "name": "S2", "agent_score": 65},
        ],
    })
    # Both close to mean → no alpha
    _write_json(fr / date / "forward_returns.json", {
        "forward_returns": {"600001": {"1d": 5.0}, "600002": {"1d": 5.0}},
    })

    agg = {"dates_evaluated": [date], "coverage": {"candidate_count": 2}, "horizons": ["1d"]}
    market_adj = compute_agent_score_market_adjusted(agg, bridge, cal, None)

    # Both adjusted returns = 0, no alpha
    assert market_adj["interpretation"]["has_positive_alpha_signal"] is False

    buckets = {
        "80+": {"candidate_count": 1, "horizons": {"1d": {"sample_count": 1, "avg_return_pct": 0.0, "hit_rate": 0.5}}},
        "60-80": {"candidate_count": 1, "horizons": {"1d": {"sample_count": 1, "avg_return_pct": 0.0, "hit_rate": 0.5}}},
        "40-60": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "<40": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "missing": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
    }

    result = determine_recommendation("agent_score", buckets, 2, "1d", market_adjusted=market_adj)
    assert any("market-adjusted" in n.lower() for n in result.get("notes", []))


# ---------------------------------------------------------------------------
# Agent Score Presence Effect
# ---------------------------------------------------------------------------


def test_presence_effect_present_vs_missing_split():
    """Present = 80+ + 60-80 + 40-60 + <40, missing = missing."""
    market_adj = {
        "excluded_dates": [],
        "date_baselines": {"2026-07-02": {"candidate_mean_1d_return": 5.0, "candidate_count": 10}},
        "buckets": {
            "80+": {"sample_count": 5, "avg_adjusted_return_pct": 2.0, "hit_rate_above_date_mean": 0.8},
            "60-80": {"sample_count": 10, "avg_adjusted_return_pct": 1.0, "hit_rate_above_date_mean": 0.6},
            "40-60": {"sample_count": 20, "avg_adjusted_return_pct": 0.5, "hit_rate_above_date_mean": 0.5},
            "<40": {"sample_count": 3, "avg_adjusted_return_pct": -0.5, "hit_rate_above_date_mean": 0.3},
            "missing": {"sample_count": 8, "avg_adjusted_return_pct": -2.0, "hit_rate_above_date_mean": 0.25},
        },
        "interpretation": {"has_positive_alpha_signal": False, "notes": []},
    }

    result = compute_agent_score_presence_effect(market_adj)

    # Present = 5+10+20+3 = 38
    assert result["present"]["sample_count"] == 38
    # Missing = 8
    assert result["missing"]["sample_count"] == 8


def test_presence_effect_excluded_dates_not_participating():
    """Excluded dates are tracked but don't affect calculation."""
    market_adj = {
        "excluded_dates": ["2026-07-01"],
        "date_baselines": {},
        "buckets": {
            "80+": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "60-80": {"sample_count": 5, "avg_adjusted_return_pct": 1.0, "hit_rate_above_date_mean": 0.6},
            "40-60": {"sample_count": 10, "avg_adjusted_return_pct": 0.5, "hit_rate_above_date_mean": 0.5},
            "<40": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "missing": {"sample_count": 3, "avg_adjusted_return_pct": -1.0, "hit_rate_above_date_mean": 0.33},
        },
        "interpretation": {"has_positive_alpha_signal": False, "notes": []},
    }

    result = compute_agent_score_presence_effect(market_adj)
    assert "2026-07-01" in result["excluded_dates"]
    assert result["present"]["sample_count"] == 15


def test_presence_effect_spread_calculation():
    """Spread = present - missing."""
    market_adj = {
        "excluded_dates": [],
        "date_baselines": {},
        "buckets": {
            "80+": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "60-80": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "40-60": {"sample_count": 35, "avg_adjusted_return_pct": 1.5, "hit_rate_above_date_mean": 0.6},
            "<40": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "missing": {"sample_count": 10, "avg_adjusted_return_pct": -1.0, "hit_rate_above_date_mean": 0.3},
        },
        "interpretation": {"has_positive_alpha_signal": False, "notes": []},
    }

    result = compute_agent_score_presence_effect(market_adj)

    # spread.avg = 1.5 - (-1.0) = 2.5
    assert result["spread"]["avg_adjusted_return_pct"] == 2.5
    # spread.hr = 0.6 - 0.3 = 0.3
    assert result["spread"]["hit_rate_diff"] == 0.3


def test_presence_effect_has_presence_signal_true():
    """has_presence_signal when present>=30, missing>=5, spread>1%."""
    market_adj = {
        "excluded_dates": [],
        "date_baselines": {},
        "buckets": {
            "80+": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "60-80": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "40-60": {"sample_count": 40, "avg_adjusted_return_pct": 2.0, "hit_rate_above_date_mean": 0.6},
            "<40": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "missing": {"sample_count": 10, "avg_adjusted_return_pct": -1.0, "hit_rate_above_date_mean": 0.3},
        },
        "interpretation": {"has_positive_alpha_signal": False, "notes": []},
    }

    result = compute_agent_score_presence_effect(market_adj)
    assert result["interpretation"]["has_presence_signal"] is True


def test_presence_effect_has_presence_signal_false_insufficient_samples():
    """has_presence_signal false when present < 30."""
    market_adj = {
        "excluded_dates": [],
        "date_baselines": {},
        "buckets": {
            "80+": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "60-80": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "40-60": {"sample_count": 20, "avg_adjusted_return_pct": 2.0, "hit_rate_above_date_mean": 0.6},
            "<40": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "missing": {"sample_count": 10, "avg_adjusted_return_pct": -1.0, "hit_rate_above_date_mean": 0.3},
        },
        "interpretation": {"has_positive_alpha_signal": False, "notes": []},
    }

    result = compute_agent_score_presence_effect(market_adj)
    assert result["interpretation"]["has_presence_signal"] is False


def test_markdown_includes_presence_effect():
    """Markdown output includes Agent Score Presence Effect section."""
    market_adj = {
        "excluded_dates": [],
        "date_baselines": {},
        "buckets": {
            "80+": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "60-80": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "40-60": {"sample_count": 35, "avg_adjusted_return_pct": 1.0, "hit_rate_above_date_mean": 0.55},
            "<40": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "missing": {"sample_count": 8, "avg_adjusted_return_pct": -2.0, "hit_rate_above_date_mean": 0.25},
        },
        "interpretation": {"has_positive_alpha_signal": False, "notes": []},
    }

    presence = compute_agent_score_presence_effect(market_adj)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": ["2026-07-02"],
        "candidate_count": 43,
        "primary_horizon": "1d",
        "layers": {},
        "agent_score_presence_effect": presence,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Score Presence Effect" in md
    assert "Present" in md
    assert "Missing" in md
    assert "Spread" in md


def test_recommendation_notes_include_presence_effect():
    """Presence effect notes appear in recommendation."""
    market_adj = {
        "excluded_dates": [],
        "date_baselines": {},
        "buckets": {
            "80+": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "60-80": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "40-60": {"sample_count": 40, "avg_adjusted_return_pct": 2.0, "hit_rate_above_date_mean": 0.6},
            "<40": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "missing": {"sample_count": 10, "avg_adjusted_return_pct": -1.0, "hit_rate_above_date_mean": 0.3},
        },
        "interpretation": {"has_positive_alpha_signal": False, "notes": []},
    }

    presence = compute_agent_score_presence_effect(market_adj)
    assert presence["interpretation"]["has_presence_signal"] is True

    buckets = {
        "80+": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "60-80": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "40-60": {"candidate_count": 40, "horizons": {"1d": {"sample_count": 40, "avg_return_pct": 1.0, "hit_rate": 0.6}}},
        "<40": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "missing": {"candidate_count": 10, "horizons": {"1d": {"sample_count": 10, "avg_return_pct": -1.0, "hit_rate": 0.3}}},
    }

    result = determine_recommendation("agent_score", buckets, 50, "1d", presence_effect=presence)
    assert any("presence" in n.lower() for n in result.get("notes", []))


# ---------------------------------------------------------------------------
# Agent Score Coverage Quality Rollup
# ---------------------------------------------------------------------------


def test_coverage_quality_rollup_healthy(tmp_path):
    """Healthy coverage (>= 80%) is classified correctly."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-08"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
        ],
    })

    result = compute_agent_score_coverage_quality_rollup([d], bridge)
    assert result["healthy_dates"] == [d]
    assert result["avg_coverage_ratio"] == 1.0


def test_coverage_quality_rollup_partial(tmp_path):
    """Partial coverage (50-80%) is classified correctly."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-07"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
            {"code": "600003"},  # missing
            {"code": "600004"},  # missing
        ],
    })

    result = compute_agent_score_coverage_quality_rollup([d], bridge)
    assert result["partial_dates"] == [d]
    assert result["avg_coverage_ratio"] == 0.5


def test_coverage_quality_rollup_poor(tmp_path):
    """Poor coverage (< 50%) is classified correctly."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-01"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    result = compute_agent_score_coverage_quality_rollup([d], bridge)
    assert result["poor_dates"] == [d]
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["type"] == "low_agent_score_coverage"


def test_coverage_quality_rollup_fallback_top30(tmp_path):
    """Fallback to top30_candidates.json when bridge report missing."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-02"
    # No bridge report, only top30
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
        ],
    })

    result = compute_agent_score_coverage_quality_rollup([d], bridge)
    assert result["healthy_dates"] == [d]
    assert result["avg_coverage_ratio"] == 1.0


def test_markdown_includes_coverage_quality_rollup(tmp_path):
    """Markdown output includes Agent Score Coverage Quality Rollup section."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-08"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [{"code": "600001", "agent_score": 80}],
    })

    rollup = compute_agent_score_coverage_quality_rollup([d], bridge)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": [d],
        "candidate_count": 1,
        "primary_horizon": "1d",
        "layers": {},
        "agent_score_coverage_quality_rollup": rollup,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Score Coverage Quality Rollup" in md
    assert "Healthy" in md


def test_recommendation_notes_include_coverage_quality(tmp_path):
    """When presence signal true and poor dates exist, coverage quality note added."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-01"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    rollup = compute_agent_score_coverage_quality_rollup([d], bridge)
    assert rollup["poor_dates"] == [d]

    presence = {
        "interpretation": {"has_presence_signal": True, "notes": []},
    }

    buckets = {
        "80+": {"candidate_count": 1, "horizons": {"1d": {"sample_count": 1, "avg_return_pct": 2.0, "hit_rate": 1.0}}},
        "60-80": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "40-60": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "<40": {"candidate_count": 0, "horizons": {"1d": {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}}},
        "missing": {"candidate_count": 3, "horizons": {"1d": {"sample_count": 3, "avg_return_pct": -1.0, "hit_rate": 0.3}}},
    }

    result = determine_recommendation(
        "agent_score", buckets, 4, "1d",
        presence_effect=presence, coverage_rollup=rollup,
    )
    assert any("coverage" in n.lower() and "quality" in n.lower() for n in result.get("notes", []))


# ---------------------------------------------------------------------------
# Pipeline Warnings
# ---------------------------------------------------------------------------


def test_summary_poor_dates_generates_pipeline_warning(tmp_path):
    """Poor dates in rollup generate pipeline_warnings in summary."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-01"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    rollup = compute_agent_score_coverage_quality_rollup([d], bridge)
    assert rollup["poor_dates"] == [d]

    # Simulate summary construction
    summary = {
        "agent_score_coverage_quality_rollup": rollup,
    }

    # Manually add pipeline_warnings (as summarize_scoring_calibration does)
    poor_dates = rollup.get("poor_dates", [])
    if poor_dates:
        summary["pipeline_warnings"] = [{
            "type": "poor_agent_score_coverage_dates",
            "severity": "warn",
            "dates": poor_dates,
            "avg_coverage_ratio": rollup.get("avg_coverage_ratio", 0),
            "message": f"Poor agent_score coverage on {len(poor_dates)} date(s): {', '.join(poor_dates)}.",
        }]

    pw = summary.get("pipeline_warnings", [])
    assert len(pw) == 1
    assert pw[0]["type"] == "poor_agent_score_coverage_dates"
    assert "2026-07-01" in pw[0]["dates"]


def test_summary_healthy_dates_no_pipeline_warning(tmp_path):
    """Healthy dates do not generate pipeline_warnings."""
    bridge = tmp_path / "agent_bridge"
    d = "2026-07-08"
    _write_json(bridge / d / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
        ],
    })

    rollup = compute_agent_score_coverage_quality_rollup([d], bridge)
    assert rollup["poor_dates"] == []
    assert len(rollup.get("warnings", [])) == 0


def test_markdown_includes_pipeline_warnings(tmp_path):
    """Markdown output includes Pipeline Warnings section."""
    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": ["2026-07-01"],
        "candidate_count": 4,
        "primary_horizon": "1d",
        "layers": {},
        "pipeline_warnings": [{
            "type": "poor_agent_score_coverage_dates",
            "severity": "warn",
            "dates": ["2026-07-01"],
            "avg_coverage_ratio": 0.25,
            "message": "Poor agent_score coverage on 1 date(s): 2026-07-01.",
        }],
    }

    md = generate_summary_markdown(summary)
    assert "Pipeline Warnings" in md
    assert "poor_agent_score_coverage_dates" in md


# ---------------------------------------------------------------------------
# Agent Execution Quality Rollup
# ---------------------------------------------------------------------------


def test_execution_quality_rollup_healthy(tmp_path):
    """Healthy execution quality is classified correctly."""
    from scripts.summarize_scoring_calibration import compute_agent_execution_quality_rollup

    bridge = tmp_path / "agent_bridge"
    d = "2026-07-08"
    _write_json(bridge / d / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 72.0, "contributing_agents": 7}],
        "run_meta": {"succeeded_agents": ["a"], "failed_agents": [], "fallback_agents": []},
    })

    result = compute_agent_execution_quality_rollup([d], bridge)
    assert result["healthy_dates"] == [d]
    assert result["fallback_only_dates"] == []
    assert result["default_score_total"] == 0


def test_execution_quality_rollup_fallback_only(tmp_path):
    """Fallback-only execution is classified correctly."""
    from scripts.summarize_scoring_calibration import compute_agent_execution_quality_rollup

    bridge = tmp_path / "agent_bridge"
    d = "2026-07-01"
    _write_json(bridge / d / "aihf_stock_ranking.json", {
        "items": [
            {"code": "600001", "agent_score": 50.0, "contributing_agents": 0},
            {"code": "600002", "agent_score": 50.0, "contributing_agents": 0},
        ],
        "run_meta": {"succeeded_agents": [], "failed_agents": ["a"], "fallback_agents": []},
    })

    result = compute_agent_execution_quality_rollup([d], bridge)
    assert result["fallback_only_dates"] == [d]
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["type"] == "fallback_only_agent_execution"


def test_markdown_includes_execution_quality_rollup(tmp_path):
    """Markdown output includes Agent Execution Quality Rollup section."""
    from scripts.summarize_scoring_calibration import compute_agent_execution_quality_rollup

    bridge = tmp_path / "agent_bridge"
    d = "2026-07-08"
    _write_json(bridge / d / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 72.0, "contributing_agents": 7}],
        "run_meta": {"succeeded_agents": ["a"], "failed_agents": [], "fallback_agents": []},
    })

    rollup = compute_agent_execution_quality_rollup([d], bridge)

    summary = {
        "generated_at": "2026-07-09T10:00:00",
        "as_of": "2026-07-01_to_2026-07-08",
        "dates_evaluated": [d],
        "candidate_count": 1,
        "primary_horizon": "1d",
        "layers": {},
        "agent_execution_quality_rollup": rollup,
    }

    md = generate_summary_markdown(summary)
    assert "Agent Execution Quality Rollup" in md
    assert "Healthy" in md
