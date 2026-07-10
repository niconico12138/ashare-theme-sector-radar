import json

import pytest

from scripts.aggregate_scoring_calibration import (
    aggregate_scoring_calibration,
    build_aggregate_samples,
    generate_markdown_report,
    main,
)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_aggregate_samples_preserves_date_code_identity(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.json",
        {"candidates": [{"code": "600001", "final_score": 80}, {"code": "600002", "final_score": 50}]},
    )
    _write_json(
        returns_root / "2026-07-01" / "forward_returns.json",
        {"forward_returns": {"600001": {"1d": 2.0}, "600002": {"1d": -1.0}}},
    )
    _write_json(
        candidate_root / "2026-07-02" / "top30_candidates.json",
        {"candidates": [{"code": "600001", "final_score": 40}]},
    )
    _write_json(
        returns_root / "2026-07-02" / "forward_returns.json",
        {"forward_returns": {"600001": {"1d": -3.0}}},
    )

    samples, forward_returns, date_summary = build_aggregate_samples(
        ["2026-07-01", "2026-07-02"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=("1d",),
    )

    assert [sample["code"] for sample in samples] == [
        "2026-07-01:600001",
        "2026-07-01:600002",
        "2026-07-02:600001",
    ]
    assert samples[0]["original_code"] == "600001"
    assert forward_returns["2026-07-02:600001"]["1d"] == pytest.approx(-3.0)
    assert date_summary["2026-07-01"]["forward_return_count"] == 2


def test_aggregate_scoring_calibration_records_missing_dates(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.json",
        {"candidates": [{"code": "600001", "final_score": 80}]},
    )
    _write_json(
        returns_root / "2026-07-01" / "forward_returns.json",
        {"forward_returns": {"600001": {"1d": 2.0}}},
    )

    result = aggregate_scoring_calibration(
        ["2026-07-01", "2026-07-02"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=("1d",),
    )

    assert result["coverage"]["candidate_count"] == 1
    assert result["coverage"]["forward_return_count"] == 1
    assert result["date_summary"]["2026-07-02"]["status"] == "missing_candidate_file"
    assert result["layers"]["final_score"]["buckets"]["80+"]["horizons"]["1d"]["avg_return_pct"] == pytest.approx(2.0)


def test_generate_markdown_report_includes_aggregate_and_date_summary(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.json",
        {"candidates": [{"code": "600001", "final_score": 80}]},
    )
    _write_json(
        returns_root / "2026-07-01" / "forward_returns.json",
        {"forward_returns": {"600001": {"1d": 2.0}}},
    )
    result = aggregate_scoring_calibration(
        ["2026-07-01"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=("1d",),
    )

    markdown = generate_markdown_report(result)

    assert "# Aggregate Scoring Calibration Report" in markdown
    assert "Date Coverage" in markdown
    assert "final_score" in markdown


def test_cli_writes_aggregate_outputs(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.json",
        {"candidates": [{"code": "600001", "final_score": 80}]},
    )
    _write_json(
        returns_root / "2026-07-01" / "forward_returns.json",
        {"forward_returns": {"600001": {"1d": 2.0}}},
    )

    exit_code = main(
        [
            "--dates",
            "2026-07-01",
            "--candidate-root",
            str(candidate_root),
            "--returns-root",
            str(returns_root),
            "--output-dir",
            str(output_dir),
            "--horizons",
            "1d",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "aggregate" / "2026-07-01" / "aggregate_scoring_calibration.json").exists()
    assert (output_dir / "aggregate" / "2026-07-01" / "aggregate_scoring_calibration.md").exists()
