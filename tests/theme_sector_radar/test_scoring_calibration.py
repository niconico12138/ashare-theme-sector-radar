import json

import pytest

from scripts.evaluate_scoring_calibration import (
    assign_score_bucket,
    evaluate_score_layers,
    generate_markdown_report,
    load_candidates,
    main,
)


def test_assign_score_bucket_uses_stable_ranges():
    assert assign_score_bucket(None) == "missing"
    assert assign_score_bucket(81) == "80+"
    assert assign_score_bucket(60) == "60-80"
    assert assign_score_bucket(40) == "40-60"
    assert assign_score_bucket(39.9) == "<40"


def test_evaluate_score_layers_groups_forward_returns_by_bucket():
    candidates = [
        {"code": "600001", "final_score": 85, "quant_score": 82},
        {"code": "600002", "final_score": 72, "quant_score": 65},
        {"code": "600003", "final_score": 45, "quant_score": 41},
    ]
    forward_returns = {
        "600001": {"1d": 3.0, "3d": 5.0},
        "600002": {"1d": 1.0, "3d": -2.0},
        "600003": {"1d": -4.0, "3d": -6.0},
    }

    result = evaluate_score_layers(candidates, forward_returns, horizons=("1d", "3d"), as_of="2026-07-08")

    assert result["coverage"]["candidate_count"] == 3
    assert result["coverage"]["forward_return_count"] == 3
    final_buckets = result["layers"]["final_score"]["buckets"]
    assert final_buckets["80+"]["horizons"]["1d"]["avg_return_pct"] == pytest.approx(3.0)
    assert final_buckets["80+"]["horizons"]["1d"]["hit_rate"] == pytest.approx(1.0)
    assert final_buckets["40-60"]["horizons"]["1d"]["hit_rate"] == pytest.approx(0.0)


def test_evaluate_score_layers_reports_missing_forward_return_coverage():
    candidates = [
        {"code": "600001", "final_score": 85},
        {"code": "600002", "final_score": 72},
        {"code": "600003", "final_score": 45},
    ]
    forward_returns = {"600001": {"1d": 3.0}}

    result = evaluate_score_layers(candidates, forward_returns, horizons=("1d",), as_of="2026-07-08")

    assert result["coverage"]["forward_return_count"] == 1
    assert result["coverage"]["missing_forward_return_count"] == 2
    assert result["coverage"]["coverage_ratio"] == pytest.approx(0.3333)
    bucket = result["layers"]["final_score"]["buckets"]["60-80"]["horizons"]["1d"]
    assert bucket["sample_count"] == 0
    assert bucket["avg_return_pct"] is None


def test_evaluate_score_layers_does_not_count_all_null_returns_as_covered():
    candidates = [{"code": "600001", "final_score": 85}]
    forward_returns = {"600001": {"1d": None, "3d": None}}

    result = evaluate_score_layers(candidates, forward_returns, horizons=("1d", "3d"), as_of="2026-07-08")

    assert result["coverage"]["forward_return_count"] == 0
    assert result["coverage"]["missing_forward_return_count"] == 1
    assert result["coverage"]["coverage_ratio"] == 0


def test_generate_markdown_report_includes_layers_and_coverage():
    result = evaluate_score_layers(
        [{"code": "600001", "final_score": 85, "quant_score": 82}],
        {"600001": {"1d": 3.0}},
        horizons=("1d",),
        as_of="2026-07-08",
    )

    markdown = generate_markdown_report(result)

    assert "# Scoring Calibration Report" in markdown
    assert "final_score" in markdown
    assert "quant_score" in markdown
    assert "Forward Return Coverage" in markdown


def test_load_candidates_accepts_candidate_pool_schema(tmp_path):
    path = tmp_path / "top30_candidates.json"
    path.write_text(
        json.dumps({"candidates": [{"code": "600001", "final_score": 85}]}),
        encoding="utf-8",
    )

    assert load_candidates(path) == [{"code": "600001", "final_score": 85}]


def test_load_candidates_accepts_utf8_bom(tmp_path):
    path = tmp_path / "top30_candidates.json"
    path.write_text(
        '\ufeff{"candidates": [{"code": "600001", "final_score": 85}]}',
        encoding="utf-8",
    )

    assert load_candidates(path) == [{"code": "600001", "final_score": 85}]


def test_cli_writes_json_and_markdown_outputs(tmp_path):
    bridge_dir = tmp_path / "agent_bridge" / "2026-07-08"
    bridge_dir.mkdir(parents=True)
    (bridge_dir / "top30_candidates.json").write_text(
        json.dumps({"candidates": [{"code": "600001", "final_score": 85}]}),
        encoding="utf-8",
    )
    returns_path = tmp_path / "returns.json"
    returns_path.write_text(json.dumps({"600001": {"1d": 3.0}}), encoding="utf-8")
    out_dir = tmp_path / "scoring_calibration"

    exit_code = main(
        [
            "--as-of",
            "2026-07-08",
            "--candidate-path",
            str(bridge_dir / "top30_candidates.json"),
            "--returns-json",
            str(returns_path),
            "--output-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "2026-07-08" / "scoring_calibration.json").exists()
    assert (out_dir / "2026-07-08" / "scoring_calibration.md").exists()
