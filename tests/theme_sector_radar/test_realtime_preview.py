import json
from datetime import datetime

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
