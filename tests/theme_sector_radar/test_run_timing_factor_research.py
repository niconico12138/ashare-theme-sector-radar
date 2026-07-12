import json

from scripts.run_timing_factor_research import main, run_timing_factor_research


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_run_timing_factor_research_writes_json_and_markdown(tmp_path):
    candidates_json = tmp_path / "candidates.json"
    output_dir = tmp_path / "out"
    _write_json(
        candidates_json,
        {
            "candidates": [
                {"code": "600001", "opening_drive_score": 90, "forward_return_pct": 4.0},
                {"code": "600002", "opening_drive_score": 75, "forward_return_pct": 2.0},
                {"code": "600003", "opening_drive_score": 25, "forward_return_pct": -1.0},
                {"code": "600004", "opening_drive_score": 20, "forward_return_pct": -2.0},
            ]
        },
    )

    result = run_timing_factor_research(
        candidate_files=[candidates_json],
        output_dir=output_dir,
        as_of="2026-07-12",
        snapshot_label="unit",
        min_labeled_samples=4,
    )

    assert result["status"] == "ok"
    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    report = json.loads(result["json_path"].read_text(encoding="utf-8"))
    assert report["summary"]["category_count"] == 8
    assert report["paper_trading_only"] is True
    assert "opening_drive_score" in {item["factor_id"] for item in report["valuable_factors"]}
    markdown = result["markdown_path"].read_text(encoding="utf-8")
    assert "Timing Factor Research" in markdown
    assert "Paper-only" in markdown


def test_timing_factor_research_cli_returns_zero(tmp_path):
    candidates_json = tmp_path / "candidates.json"
    _write_json(candidates_json, [{"code": "600001", "opening_drive_score": 80}])

    assert main(
        [
            "--candidate-json",
            str(candidates_json),
            "--output-dir",
            str(tmp_path / "out"),
            "--as-of",
            "2026-07-12",
            "--snapshot-label",
            "unit",
        ]
    ) == 0


def test_run_timing_factor_research_merges_selection_validation_by_date(tmp_path):
    date_dir = tmp_path / "candidates" / "2026-07-12"
    date_dir.mkdir(parents=True)
    candidates_json = date_dir / "top30_candidates.intraday_backfilled.json"
    validation_dir = tmp_path / "selection_validation" / "2026-07-12"
    validation_dir.mkdir(parents=True)
    _write_json(
        candidates_json,
        {
            "candidates": [
                {"code": "600001", "opening_drive_score": 90},
                {"code": "600002", "opening_drive_score": 75},
                {"code": "600003", "opening_drive_score": 25},
                {"code": "600004", "opening_drive_score": 20},
            ]
        },
    )
    _write_json(
        validation_dir / "next_day_selection_validation.json",
        {
            "per_stock": [
                {"code": "600001", "next_return_pct": 4.0},
                {"code": "600002", "next_return_pct": 2.0},
                {"code": "600003", "next_return_pct": -1.0},
                {"code": "600004", "next_return_pct": -2.0},
            ]
        },
    )

    result = run_timing_factor_research(
        candidate_files=[candidates_json],
        output_dir=tmp_path / "out",
        as_of="2026-07-12",
        snapshot_label="validation",
        selection_validation_root=tmp_path / "selection_validation",
        min_labeled_samples=4,
    )

    assert result["report"]["summary"]["labeled_sample_count"] == 4
    assert "opening_drive_score" in {item["factor_id"] for item in result["report"]["valuable_factors"]}


def test_run_timing_factor_research_discovers_candidate_files_and_reports_coverage(tmp_path):
    candidate_root = tmp_path / "candidates"
    for date, score in [("2026-07-11", 88), ("2026-07-12", 22)]:
        date_dir = candidate_root / date
        date_dir.mkdir(parents=True)
        _write_json(
            date_dir / "top30_candidates.intraday_backfilled.json",
            {"candidates": [{"code": f"6{date[-2:]}001", "opening_drive_score": score}]},
        )
    validation_dir = tmp_path / "selection_validation" / "2026-07-12"
    validation_dir.mkdir(parents=True)
    _write_json(
        validation_dir / "next_day_selection_validation.json",
        {"per_stock": [{"code": "612001", "next_return_pct": -1.0}]},
    )

    result = run_timing_factor_research(
        candidate_files=[],
        candidate_root=candidate_root,
        start="2026-07-11",
        end="2026-07-12",
        output_dir=tmp_path / "out",
        as_of="2026-07-12",
        snapshot_label="discovered",
        selection_validation_root=tmp_path / "selection_validation",
        min_labeled_samples=2,
    )

    coverage = result["report"]["data_coverage"]
    assert coverage["candidate_file_count"] == 2
    assert coverage["sample_count"] == 2
    assert coverage["labeled_sample_count"] == 1
    assert coverage["intraday_observed_sample_count"] == 2
    assert "2026-07-11" in coverage["dates_without_selection_validation"]


def test_timing_factor_research_cli_accepts_thresholds(tmp_path):
    candidates_json = tmp_path / "candidates.json"
    _write_json(
        candidates_json,
        [
            {"code": "600001", "open_to_midday_resilience_score": 85, "forward_return_pct": 3.0},
            {"code": "600002", "open_to_midday_resilience_score": 25, "forward_return_pct": -1.0},
        ],
    )

    assert main(
        [
            "--candidate-json",
            str(candidates_json),
            "--output-dir",
            str(tmp_path / "out"),
            "--as-of",
            "2026-07-12",
            "--snapshot-label",
            "thresholds",
            "--min-labeled-samples",
            "2",
            "--thresholds",
            "50",
            "70",
        ]
    ) == 0
