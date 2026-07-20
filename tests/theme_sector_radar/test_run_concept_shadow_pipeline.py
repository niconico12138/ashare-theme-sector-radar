from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

import pytest


class NeverReadBoards:
    def list_boards(self, _board_type):
        raise AssertionError("historical runs must not read current membership")


def _board(index=3):
    members = [f"0000{index}3", f"6000{index}0"]
    code = f"30084{index}.TI"
    name = f"C{index}"
    return {
        "source_key": f"板块:概念_{name}:{code}",
        "code": code,
        "name": name,
        "source": "ths",
        "category": "概念",
        "type": "concept",
        "group": "同花顺概念",
        "symbols": members,
        "raw_sha256": hashlib.sha256(name.encode()).hexdigest(),
    }


class FakeHistoryService:
    def get_history(self, *, board_code, board_name, start_date, end_date, as_of_date):
        from theme_sector_radar.data.akshare_concept_history import history_rows_sha256

        rows = []
        end = date.fromisoformat(as_of_date)
        start = end.fromordinal(end.toordinal() - 24)
        for index in range(25):
            iso = date.fromordinal(start.toordinal() + index).isoformat()
            close = 100.0 + index
            rows.append(
                {
                    "date": iso,
                    "open": close - 0.5,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "pct_change": 0.1 + index * 0.02,
                    "amount": 100000.0 + index,
                }
            )
        return {
            "schema_version": "akshare_concept_history.v1",
            "mode": "paper_shadow_research_only",
            "identity": {"board_code": board_code, "board_name": board_name},
            "query": {
                "start_date": start_date,
                "end_date": end_date,
                "as_of_date": as_of_date,
            },
            "coverage": {
                "through_as_of": True,
                "row_count": len(rows),
                "first_date": rows[0]["date"],
                "last_date": rows[-1]["date"],
            },
            "rows": rows,
            "rows_sha256": history_rows_sha256(rows),
        }


def test_historical_pipeline_fails_closed_without_exact_snapshot(tmp_path):
    from theme_sector_radar.concept_shadow_pipeline import run_concept_shadow_pipeline

    with pytest.raises(FileNotFoundError, match="historical membership snapshot"):
        run_concept_shadow_pipeline(
            as_of_date="2026-07-17",
            today=date(2026, 7, 19),
            membership_root=tmp_path / "memberships",
            report_root=tmp_path / "reports",
            board_client=NeverReadBoards(),
            history_client=FakeHistoryService(),
        )


def test_pipeline_captures_only_today_and_writes_independent_strict_report(tmp_path):
    from theme_sector_radar.concept_shadow_pipeline import run_concept_shadow_pipeline

    class CurrentBoards:
        def list_boards(self, board_type):
            assert board_type == "concept"
            return [_board(index) for index in range(3)]

    report = run_concept_shadow_pipeline(
        as_of_date="2026-07-19",
        today=date(2026, 7, 19),
        membership_root=tmp_path / "memberships",
        report_root=tmp_path / "reports",
        board_client=CurrentBoards(),
        history_client=FakeHistoryService(),
        history_lookback_days=40,
        captured_at="2026-07-19T09:00:00+08:00",
    )

    assert report["mode"] == "paper_shadow_research_only"
    assert report["status"] == "ok"
    assert report["formal_candidate_eligible"] is False
    assert report["bridge"]["unique_stock_count"] == 6
    first_stock = report["bridge"]["stocks"][0]
    assert first_stock["stock_code"] == "000003"
    assert first_stock["formal_candidate_eligible"] is False
    provenance = first_stock["concept_provenance"][0]
    assert provenance["membership_snapshot_sha256"] == report["provenance"][
        "membership_snapshot_sha256"
    ]
    assert {
        "board_code",
        "board_name",
        "source_key",
        "symbols_sha256",
        "raw_sha256",
        "as_of_date",
        "direction_score_shadow",
        "direction_state",
        "concept_shadow_rank",
        "history_rows_sha256",
    } <= set(provenance)
    report_path = (
        tmp_path
        / "reports"
        / "concept_direction_2026-07-19"
        / "concept_shadow_report.json"
    )
    parsed = json.loads(
        report_path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )
    assert parsed == report


def test_cli_failure_outputs_strict_json(monkeypatch, capsys):
    import scripts.run_concept_shadow_pipeline as cli

    def fail(**_kwargs):
        raise FileNotFoundError("missing historical membership snapshot")

    monkeypatch.setattr(cli, "run_concept_shadow_pipeline", fail)

    exit_code = cli.main(["--as-of", "2026-07-17"])

    payload = json.loads(
        capsys.readouterr().out,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )
    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["mode"] == "paper_shadow_research_only"
    assert payload["error_type"] == "FileNotFoundError"


def test_cli_argument_failure_outputs_strict_json(capsys):
    import scripts.run_concept_shadow_pipeline as cli

    exit_code = cli.main(["--as-of", "2026-07-17", "--top-n", "bad"])

    payload = json.loads(
        capsys.readouterr().out,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )
    assert exit_code == 2
    assert payload["status"] == "failed"
    assert payload["error_type"] == "ValueError"


def test_shadow_source_files_exclude_execution_integration_tokens():
    root = Path(__file__).resolve().parents[2]
    paths = [
        root / "theme_sector_radar/data/stockdb_board_client.py",
        root / "theme_sector_radar/data/board_membership_snapshot.py",
        root / "theme_sector_radar/data/akshare_concept_history.py",
        root / "theme_sector_radar/scoring/concept_direction_shadow.py",
        root / "theme_sector_radar/concept_shadow_pipeline.py",
        root / "scripts/run_concept_shadow_pipeline.py",
    ]
    forbidden = ["bro" + "ker", "place_" + "order", "submit_" + "order"]

    for path in paths:
        source = path.read_text(encoding="utf-8").lower()
        assert not any(token in source for token in forbidden), path
