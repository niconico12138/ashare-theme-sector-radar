import json
import subprocess
import sys

import pytest

from scripts.build_forward_returns import (
    StockDBSdkBarsClient,
    build_forward_returns,
    compute_forward_returns_from_bars,
    load_candidate_codes,
    main,
)


def test_compute_forward_returns_from_bars_uses_future_trading_days():
    bars = [
        {"date": "2026-07-07", "close": 9.5},
        {"date": "2026-07-08", "close": 10.0},
        {"date": "2026-07-09", "close": 11.0},
        {"date": "2026-07-10", "close": 12.0},
        {"date": "2026-07-13", "close": 9.0},
    ]

    result = compute_forward_returns_from_bars(bars, "2026-07-08", horizons=(1, 2, 3))

    assert result["1d"] == pytest.approx(10.0)
    assert result["2d"] == pytest.approx(20.0)
    assert result["3d"] == pytest.approx(-10.0)


def test_compute_forward_returns_from_bars_reports_missing_signal_or_future_days():
    bars = [
        {"date": "2026-07-09", "close": 11.0},
        {"date": "2026-07-10", "close": 12.0},
    ]

    result = compute_forward_returns_from_bars(bars, "2026-07-08", horizons=(1, 3))

    assert result["1d"] is None
    assert result["3d"] is None


def test_load_candidate_codes_deduplicates_candidate_pool(tmp_path):
    path = tmp_path / "top30_candidates.json"
    path.write_text(
        json.dumps(
            {
                "candidates": [
                    {"code": "600001"},
                    {"code": "600001"},
                    {"code": "000002"},
                    {"code": ""},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert load_candidate_codes(path) == ["600001", "000002"]


def test_load_candidate_codes_accepts_utf8_bom(tmp_path):
    path = tmp_path / "top30_candidates.json"
    path.write_text('\ufeff{"candidates": [{"code": "600001"}]}', encoding="utf-8")

    assert load_candidate_codes(path) == ["600001"]


def test_build_forward_returns_records_coverage_and_errors():
    class FakeClient:
        def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
            if code == "600001":
                return [
                    {"date": "2026-07-08", "close": 10.0},
                    {"date": "2026-07-09", "close": 11.0},
                    {"date": "2026-07-10", "close": 12.0},
                ]
            raise ConnectionError("down")

    result = build_forward_returns(
        ["600001", "600002"],
        "2026-07-08",
        client=FakeClient(),
        horizons=(1, 2),
        lookahead_days=7,
    )

    assert result["forward_returns"]["600001"]["1d"] == pytest.approx(10.0)
    assert result["forward_returns"]["600001"]["2d"] == pytest.approx(20.0)
    assert result["forward_returns"]["600002"]["1d"] is None
    assert result["coverage"]["stock_count"] == 2
    assert result["coverage"]["stocks_with_any_forward_return"] == 1
    assert result["errors"]["600002"] == "down"
    assert result["bars_data_source"] == {"source": "custom_client"}


def test_build_forward_returns_records_auto_source_selection():
    class FakeClient:
        selection = {"source": "stockdb-sdk", "reason": "sdk_newer_than_http"}

        def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
            return [
                {"date": "2026-07-08", "close": 10.0},
                {"date": "2026-07-09", "close": 11.0},
            ]

    result = build_forward_returns(
        ["600001"],
        "2026-07-08",
        client=FakeClient(),
        horizons=(1,),
        lookahead_days=7,
    )

    assert result["bars_data_source"] == {"source": "stockdb-sdk", "reason": "sdk_newer_than_http"}


def test_stockdb_sdk_bars_client_normalizes_dict_records():
    class FakeSdk:
        def __init__(self):
            self.calls = []

        def get_data(self, code, start, end, frequency="1d", fields=None, fq="qfq"):
            self.calls.append((code, start, end, frequency, fields, fq))
            return [
                {"date": 20260708, "code": code, "close": 10.5, "open": 10.1},
                {"date": 20260709, "code": code, "close": 11.0, "open": 10.6},
            ]

    client = StockDBSdkBarsClient(sdk_client=FakeSdk())

    bars = client.get_stock_bars("600001", "20260708", "20260709")

    assert bars == [
        {"date": "20260708", "code": "600001", "close": 10.5, "open": 10.1},
        {"date": "20260709", "code": "600001", "close": 11.0, "open": 10.6},
    ]


def test_stockdb_sdk_bars_client_normalizes_projected_rows():
    class FakeSdk:
        def get_data(self, code, start, end, frequency="1d", fields=None, fq="qfq"):
            return [[20260708, "600001", 10.5, 10.1]]

    client = StockDBSdkBarsClient(sdk_client=FakeSdk())

    bars = client.get_stock_bars("600001", "20260708", "20260709")

    assert bars == [{"date": "20260708", "code": "600001", "close": 10.5, "open": 10.1}]


def test_cli_writes_forward_returns_json(tmp_path):
    candidate_path = tmp_path / "top30_candidates.json"
    candidate_path.write_text(json.dumps({"candidates": [{"code": "600001"}]}), encoding="utf-8")
    out_dir = tmp_path / "forward_returns"

    class FakeClient:
        def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
            return [
                {"date": "2026-07-08", "close": 10.0},
                {"date": "2026-07-09", "close": 11.0},
            ]

    exit_code = main(
        [
            "--as-of",
            "2026-07-08",
            "--candidate-path",
            str(candidate_path),
            "--output-dir",
            str(out_dir),
            "--horizons",
            "1",
            "--source",
            "http",
        ],
        client=FakeClient(),
    )

    assert exit_code == 0
    output = json.loads((out_dir / "2026-07-08" / "forward_returns.json").read_text(encoding="utf-8"))
    assert output["forward_returns"]["600001"]["1d"] == pytest.approx(10.0)


def test_cli_accepts_auto_source_with_injected_client(tmp_path):
    candidate_path = tmp_path / "top30_candidates.json"
    candidate_path.write_text(json.dumps({"candidates": [{"code": "600001"}]}), encoding="utf-8")
    out_dir = tmp_path / "forward_returns"

    class FakeClient:
        def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
            return [
                {"date": "2026-07-08", "close": 10.0},
                {"date": "2026-07-09", "close": 11.0},
            ]

    exit_code = main(
        [
            "--as-of",
            "2026-07-08",
            "--candidate-path",
            str(candidate_path),
            "--output-dir",
            str(out_dir),
            "--horizons",
            "1",
            "--source",
            "auto",
        ],
        client=FakeClient(),
    )

    assert exit_code == 0


def test_cli_prints_bars_data_source_when_available(tmp_path, capsys):
    candidate_path = tmp_path / "top30_candidates.json"
    candidate_path.write_text(json.dumps({"candidates": [{"code": "600001"}]}), encoding="utf-8")
    out_dir = tmp_path / "forward_returns"

    class FakeClient:
        selection = {"source": "stockdb-sdk", "reason": "sdk_newer_than_http"}

        def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
            return [
                {"date": "2026-07-08", "close": 10.0},
                {"date": "2026-07-09", "close": 11.0},
            ]

    exit_code = main(
        [
            "--as-of",
            "2026-07-08",
            "--candidate-path",
            str(candidate_path),
            "--output-dir",
            str(out_dir),
            "--horizons",
            "1",
            "--source",
            "auto",
        ],
        client=FakeClient(),
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Bars source: stockdb-sdk (sdk_newer_than_http)" in captured.out


def test_script_help_runs_when_called_by_file_path():
    proc = subprocess.run(
        [sys.executable, "scripts/build_forward_returns.py", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert proc.returncode == 0
    assert "Build forward_returns.json" in proc.stdout


def test_script_can_import_project_package_when_called_by_file_path():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy; ns=runpy.run_path('scripts/build_forward_returns.py'); ns['make_bars_client']('http'); print('ok')",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert proc.returncode == 0, proc.stderr
    assert "ok" in proc.stdout
