import json
from datetime import datetime

import pytest

from scripts.run_realtime_preview import (
    build_candidates,
    build_report,
    default_snapshot_label,
    generate_markdown,
    generate_realtime_aihf_request,
    main,
    normalize_as_of,
)


class FakeRealtimeClient:
    def __init__(self, spot=None, error=None):
        self.spot = spot
        self.error = error

    def get_a_share_spot(self):
        if self.error:
            raise self.error
        return self.spot


def _spot(rows):
    return {
        "schema_version": "1.0",
        "generated_at": "2026-07-09T14:20:00",
        "source": "akshare/test",
        "data_semantics": "intraday_snapshot",
        "fallback_used": False,
        "row_count": len(rows),
        "rows": rows,
    }


def _passing_timing_row(code="600001"):
    return {
        "code": code,
        "name": code,
        "latest_price": 10.0,
        "change_pct": 3.0,
        "volume": 100,
        "amount": 1000,
        "boards": ["gas"],
        "open_to_midday_resilience_score": 70,
        "midday_hold_score": 70,
        "vwap_above_ratio_score": 70,
        "late_high_near_close_score": 90,
        "high_to_close_drawdown_score": 12,
        "lower_low_sequence_risk": 20,
        "stock_vs_market_intraday_alpha_score": 75,
        "relative_resilience_score": 75,
        "optimized_watch_score": 80,
        "late_amount_surge_score": 40,
        "failed_breakout_risk": 20,
        "execution_tradeability_score": 60,
        "late_breakdown_risk": 0,
    }


def test_default_snapshot_label_uses_current_time():
    assert default_snapshot_label(datetime(2026, 7, 9, 14, 20, 31)) == "142031"


def test_normalize_as_of_accepts_compact_date():
    assert normalize_as_of("20260709") == "2026-07-09"


def test_build_candidates_filters_sorts_and_uses_intraday_rank_only():
    rows = [
        {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
        {"code": "600002", "name": "B", "latest_price": 11.0, "change_pct": 6.0, "volume": 90, "amount": 2000},
        {"code": "600003", "name": "C", "latest_price": 12.0, "change_pct": 6.0, "volume": 80, "amount": 3000},
        {"code": "600004", "name": "*ST Risk", "latest_price": 13.0, "change_pct": 9.0, "volume": 70, "amount": 4000},
        {"code": "600005", "name": "Missing", "latest_price": None, "change_pct": 8.0, "volume": 60, "amount": 5000},
        {"code": "300001", "name": "创业板", "latest_price": 14.0, "change_pct": 10.0, "volume": 60, "amount": 7000},
        {"code": "688001", "name": "科创板", "latest_price": 15.0, "change_pct": 10.0, "volume": 60, "amount": 8000},
        {"code": "920001", "name": "北交所", "latest_price": 16.0, "change_pct": 10.0, "volume": 60, "amount": 9000},
        {"code": "", "name": "NoCode", "latest_price": 9.0, "change_pct": 7.0, "volume": 50, "amount": 6000},
    ]

    candidates, warnings = build_candidates(_spot(rows), top_n=10)

    assert [item["code"] for item in candidates] == ["600003", "600002", "600001"]
    assert [item["rank_intraday"] for item in candidates] == [1, 2, 3]
    assert all("rank" not in item for item in candidates)
    assert all(item["data_semantics"] == "intraday_snapshot" for item in candidates)
    assert warnings


def test_build_candidates_rejects_nonfinite_market_numbers():
    spot = _spot(
        [
            {"code": "600001", "name": "nan-price", "latest_price": float("nan"), "change_pct": 1.0},
            {"code": "600002", "name": "inf-change", "latest_price": 10.0, "change_pct": float("inf")},
        ]
    )

    candidates, warnings = build_candidates(spot)

    assert candidates == []
    assert any("missing price or change_pct" in warning for warning in warnings)


def test_build_report_declares_main_board_selection_policy():
    report = build_report(
        as_of="2026-07-09",
        snapshot_label="1420",
        spot_result=_spot(
            [
                {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
                {"code": "300001", "name": "创业板", "latest_price": 20.0, "change_pct": 20.0, "volume": 200, "amount": 2000},
            ]
        ),
        top_n=30,
    )

    assert report["selection_policy"]["main_board_only"] is True
    assert report["candidate_count"] == 1
    assert report["candidates"][0]["code"] == "600001"


def test_build_report_marks_preview_as_not_for_formal_calibration():
    report = build_report(
        as_of="2026-07-09",
        snapshot_label="1420",
        spot_result=_spot(
            [
                {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
            ]
        ),
        top_n=30,
    )

    assert report["report_mode"] == "realtime_preview"
    assert report["data_semantics"] == "intraday_snapshot"
    assert report["not_for_calibration"] is True
    assert report["not_for_forward_returns"] is True
    assert report["not_for_weight_changes"] is True
    assert report["candidate_count"] == 1
    assert report["timing_paper_trading"]["paper_trading_only"] is True
    assert report["timing_paper_trading"]["summary"]["record_count"] == 0


def test_markdown_starts_with_realtime_warning():
    report = build_report(
        as_of="2026-07-09",
        snapshot_label="1420",
        spot_result=_spot(
            [
                {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
            ]
        ),
        top_n=30,
    )

    markdown = generate_markdown(report)

    assert markdown.startswith("# Realtime Preview Report")
    assert "This report uses intraday_snapshot data." in markdown
    assert "must not be used for scoring calibration" in markdown
    assert "| Intraday Rank | Code | Name |" in markdown


def test_aihf_request_is_preview_only_and_uses_candidates_key():
    report = build_report(
        as_of="2026-07-09",
        snapshot_label="1420",
        spot_result=_spot(
            [
                {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
            ]
        ),
        top_n=30,
    )

    request = generate_realtime_aihf_request(report)

    assert request["report_mode"] == "realtime_preview"
    assert request["snapshot_label"] == "1420"
    assert request["not_for_calibration"] is True
    assert request["not_for_forward_returns"] is True
    assert request["not_for_weight_changes"] is True
    assert request["candidates"][0]["code"] == "600001"
    assert "rank" not in request["candidates"][0]
    assert request["timing_paper_trading"]["paper_trading_only"] is True


def test_build_report_withholds_timing_versions_before_signal_session_close():
    spot = _spot(
        [
            {
                "code": "600001",
                "name": "A",
                "latest_price": 10.0,
                "change_pct": 4.0,
                "volume": 100,
                "amount": 1000,
                "boards": ["gas"],
                "open_to_midday_resilience_score": 70,
                "midday_hold_score": 70,
                "vwap_above_ratio_score": 70,
                "late_high_near_close_score": 90,
                "high_to_close_drawdown_score": 12,
                "lower_low_sequence_risk": 20,
                "stock_vs_market_intraday_alpha_score": 75,
                "relative_resilience_score": 75,
                "optimized_watch_score": 80,
                "late_amount_surge_score": 40,
                "failed_breakout_risk": 20,
                "execution_tradeability_score": 60,
                "late_breakdown_risk": 0,
            },
            {
                "code": "600002",
                "name": "B",
                "latest_price": 10.0,
                "change_pct": 3.0,
                "volume": 100,
                "amount": 1000,
                "boards": ["gas"],
                "open_to_midday_resilience_score": 70,
                "midday_hold_score": 70,
                "vwap_above_ratio_score": 70,
                "late_high_near_close_score": 90,
                "high_to_close_drawdown_score": 12,
                "lower_low_sequence_risk": 20,
                "stock_vs_market_intraday_alpha_score": 75,
                "relative_resilience_score": 75,
                "optimized_watch_score": 80,
                "late_amount_surge_score": 40,
                "failed_breakout_risk": 20,
                "execution_tradeability_score": 60,
                "late_breakdown_risk": 0,
            },
        ]
    )
    bars = {
        "600001": [
            {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0},
            {"time": "15:00", "price": 10.5, "high": 10.8, "low": 9.6, "close": 10.5},
        ],
        "600002": [
            {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0},
            {"time": "15:00", "price": 9.9, "high": 10.8, "low": 9.6, "close": 9.9},
        ],
    }

    report = build_report(
        as_of="2026-07-09",
        snapshot_label="1420",
        spot_result=spot,
        top_n=30,
        minute_bars_by_code=bars,
    )

    timing = report["timing_paper_trading"]
    assert timing["summary"]["record_count"] == 0
    assert timing["summary"]["version_counts"] == {}
    assert timing["realtime_observation_only"] is True
    assert timing["signal_visibility"] == "withheld_until_after_signal_session_close"
    assert timing["records"] == []

    request = generate_realtime_aihf_request(report)
    assert request["timing_paper_trading"]["records"] == []


def test_build_report_allows_paper_timing_versions_after_signal_session_close():
    spot = _spot([_passing_timing_row(code) for code in ("600001", "600002")])
    spot["generated_at"] = "2026-07-09T15:00:01"

    report = build_report(
        as_of="2026-07-09",
        snapshot_label="150001",
        spot_result=spot,
        top_n=30,
    )

    timing = report["timing_paper_trading"]
    assert timing["summary"]["record_count"] == 4
    assert timing["summary"]["version_counts"]["v31_expanded_balanced_tail_guard"] == 2
    assert timing["signal_visibility"] == "available_after_signal_session_close"


@pytest.mark.parametrize(
    "source_generated_at",
    [
        None,
        "not-a-time",
        "2026-07-09T14:20:00",
        "2026-07-08T15:00:01",
    ],
)
def test_build_report_fails_closed_when_source_time_does_not_confirm_close(source_generated_at):
    spot = _spot([_passing_timing_row()])
    if source_generated_at is None:
        spot.pop("generated_at")
    else:
        spot["generated_at"] = source_generated_at

    report = build_report(
        as_of="2026-07-09",
        snapshot_label="150001",
        spot_result=spot,
        top_n=30,
    )

    timing = report["timing_paper_trading"]
    assert timing["signal_session_closed"] is False
    assert timing["summary"]["record_count"] == 0
    assert timing["signal_visibility"] == "withheld_until_after_signal_session_close"


def test_cli_writes_snapshot_label_directory_and_preview_files(tmp_path):
    client = FakeRealtimeClient(
        _spot(
            [
                {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
                {"code": "600002", "name": "B", "latest_price": 11.0, "change_pct": 5.0, "volume": 200, "amount": 2000},
            ]
        )
    )

    exit_code = main(
        [
            "--as-of",
            "2026-07-09",
            "--snapshot-label",
            "1420",
            "--top-n",
            "1",
            "--output-dir",
            str(tmp_path / "realtime_preview"),
        ],
        realtime_client=client,
    )

    out_dir = tmp_path / "realtime_preview" / "2026-07-09" / "1420"
    report = json.loads((out_dir / "realtime_preview.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert (out_dir / "realtime_preview.md").exists()
    assert report["snapshot_label"] == "1420"
    assert report["candidate_count"] == 1
    assert report["candidates"][0]["code"] == "600002"


def test_cli_rerun_preserves_previous_snapshot_by_content_hash(tmp_path):
    output_root = tmp_path / "realtime_preview"
    arguments = [
        "--as-of",
        "2026-07-09",
        "--snapshot-label",
        "1420",
        "--top-n",
        "1",
        "--output-dir",
        str(output_root),
    ]
    first = FakeRealtimeClient(
        _spot([{"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0}])
    )
    second = FakeRealtimeClient(
        _spot([{"code": "600002", "name": "B", "latest_price": 11.0, "change_pct": 5.0}])
    )

    assert main(arguments, realtime_client=first) == 0
    assert main(arguments, realtime_client=second) == 0

    out_dir = output_root / "2026-07-09" / "1420"
    archived = list(out_dir.glob("realtime_preview.*.json"))
    assert len(archived) == 1
    assert json.loads(archived[0].read_text(encoding="utf-8"))["candidates"][0]["code"] == "600001"
    assert json.loads((out_dir / "realtime_preview.json").read_text(encoding="utf-8"))["candidates"][0]["code"] == "600002"


def test_cli_auto_snapshot_label_uses_current_time(tmp_path):
    client = FakeRealtimeClient(
        _spot(
            [
                {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
            ]
        )
    )

    exit_code = main(
        [
            "--as-of",
            "2026-07-09",
            "--output-dir",
            str(tmp_path / "realtime_preview"),
        ],
        realtime_client=client,
        now=datetime(2026, 7, 9, 14, 20, 31),
    )

    assert exit_code == 0
    assert (tmp_path / "realtime_preview" / "2026-07-09" / "142031" / "realtime_preview.json").exists()


def test_cli_run_aihf_writes_request_without_formal_dirs(tmp_path):
    client = FakeRealtimeClient(
        _spot(
            [
                {"code": "600001", "name": "A", "latest_price": 10.0, "change_pct": 4.0, "volume": 100, "amount": 1000},
            ]
        )
    )

    exit_code = main(
        [
            "--as-of",
            "2026-07-09",
            "--snapshot-label",
            "1420",
            "--run-aihf",
            "--output-dir",
            str(tmp_path / "realtime_preview"),
        ],
        realtime_client=client,
    )

    out_dir = tmp_path / "realtime_preview" / "2026-07-09" / "1420"
    request = json.loads((out_dir / "realtime_aihf_request.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert request["report_mode"] == "realtime_preview"
    assert not (tmp_path / "reports" / "agent_bridge").exists()
    assert not (tmp_path / "reports" / "forward_returns").exists()
    assert not (tmp_path / "reports" / "scoring_calibration").exists()


def test_cli_returns_1_when_realtime_source_fails(tmp_path):
    client = FakeRealtimeClient(error=RuntimeError("source down"))

    exit_code = main(
        [
            "--as-of",
            "2026-07-09",
            "--snapshot-label",
            "1420",
            "--output-dir",
            str(tmp_path / "realtime_preview"),
        ],
        realtime_client=client,
    )

    assert exit_code == 1
    assert not (tmp_path / "realtime_preview" / "2026-07-09" / "1420" / "realtime_preview.json").exists()
