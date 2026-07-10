import json

from scripts.run_scoring_calibration_batch import (
    discover_candidate_dates,
    main,
    run_scoring_calibration_batch,
)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class FakeClient:
    def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
        return [
            {"date": "2026-07-01", "close": 10.0},
            {"date": "2026-07-02", "close": 11.0},
            {"date": "2026-07-03", "close": 12.0},
        ]


class FakeSdkSelectedClient(FakeClient):
    selection = {"source": "stockdb-sdk", "reason": "sdk_newer_than_http"}


def test_discover_candidate_dates_only_returns_dates_with_candidate_file(tmp_path):
    root = tmp_path / "agent_bridge"
    _write_json(root / "2026-07-01" / "top30_candidates.json", {"candidates": []})
    (root / "agent_effectiveness").mkdir(parents=True)
    (root / "2026-07-02").mkdir(parents=True)

    assert discover_candidate_dates(root) == ["2026-07-01"]


def test_batch_generates_missing_forward_returns_and_aggregate(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(candidate_root / "2026-07-01" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 80}]})
    _write_json(candidate_root / "2026-07-02" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 50}]})

    result = run_scoring_calibration_batch(
        ["2026-07-01", "2026-07-02"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        output_dir=output_dir,
        horizons=(1,),
        client=FakeClient(),
    )

    assert result["summary"]["generated_forward_returns"] == 2
    assert (returns_root / "2026-07-01" / "forward_returns.json").exists()
    assert (output_dir / "aggregate" / "2026-07-01_to_2026-07-02" / "aggregate_scoring_calibration.json").exists()
    assert result["aggregate"]["coverage"]["candidate_count"] == 2


def test_batch_skips_existing_forward_returns_unless_force(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(candidate_root / "2026-07-01" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 80}]})
    _write_json(returns_root / "2026-07-01" / "forward_returns.json", {"forward_returns": {"600001": {"1d": 1.0}}})

    skipped = run_scoring_calibration_batch(
        ["2026-07-01"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        output_dir=output_dir,
        horizons=(1,),
        client=FakeClient(),
    )
    forced = run_scoring_calibration_batch(
        ["2026-07-01"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        output_dir=output_dir,
        horizons=(1,),
        client=FakeClient(),
        force=True,
    )

    assert skipped["summary"]["skipped_existing_forward_returns"] == 1
    assert forced["summary"]["generated_forward_returns"] == 1


def test_batch_summarizes_bars_data_sources_for_existing_and_generated_returns(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(candidate_root / "2026-07-01" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 80}]})
    _write_json(candidate_root / "2026-07-02" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 50}]})
    _write_json(
        returns_root / "2026-07-01" / "forward_returns.json",
        {
            "bars_data_source": {"source": "http", "reason": "http_fresh"},
            "forward_returns": {"600001": {"1d": 1.0}},
        },
    )

    result = run_scoring_calibration_batch(
        ["2026-07-01", "2026-07-02"],
        candidate_root=candidate_root,
        returns_root=returns_root,
        output_dir=output_dir,
        horizons=(1,),
        client=FakeSdkSelectedClient(),
    )

    assert result["bars_data_source_summary"]["by_source"] == {"http": 1, "stockdb-sdk": 1}
    assert result["bars_data_source_summary"]["by_reason"] == {
        "http_fresh": 1,
        "sdk_newer_than_http": 1,
    }
    assert result["date_results"]["2026-07-01"]["bars_data_source"] == {
        "source": "http",
        "reason": "http_fresh",
    }
    assert result["date_results"]["2026-07-02"]["bars_data_source"] == {
        "source": "stockdb-sdk",
        "reason": "sdk_newer_than_http",
    }


def test_cli_batch_writes_summary(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(candidate_root / "2026-07-01" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 80}]})

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
            "1",
            "--source",
            "http",
        ],
        client=FakeClient(),
    )

    assert exit_code == 0
    assert (output_dir / "batch" / "2026-07-01" / "batch_scoring_calibration_summary.json").exists()


def test_cli_batch_accepts_stockdb_sdk_source_with_injected_client(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(candidate_root / "2026-07-01" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 80}]})

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
            "1",
            "--source",
            "stockdb-sdk",
        ],
        client=FakeClient(),
    )

    assert exit_code == 0


def test_cli_batch_accepts_auto_source_with_injected_client(tmp_path):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(candidate_root / "2026-07-01" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 80}]})

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
            "1",
            "--source",
            "auto",
        ],
        client=FakeClient(),
    )

    assert exit_code == 0


def test_cli_batch_prints_bars_data_source_summary(tmp_path, capsys):
    candidate_root = tmp_path / "agent_bridge"
    returns_root = tmp_path / "forward_returns"
    output_dir = tmp_path / "scoring_calibration"
    _write_json(candidate_root / "2026-07-01" / "top30_candidates.json", {"candidates": [{"code": "600001", "final_score": 80}]})

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
            "1",
            "--source",
            "auto",
        ],
        client=FakeSdkSelectedClient(),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Bars source summary: stockdb-sdk=1" in captured.out
    assert "Bars source reasons: sdk_newer_than_http=1" in captured.out
