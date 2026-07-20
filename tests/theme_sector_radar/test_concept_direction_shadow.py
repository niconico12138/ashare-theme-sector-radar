from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json

from theme_sector_radar.data.board_membership_snapshot import membership_snapshot_sha256


PROTECTED = {
    "quant_score",
    "final_score",
    "v2_score",
    "selection_score",
    "selection_score_adjusted",
}


def _snapshot(board_count=3):
    boards = []
    for index in range(board_count):
        code = f"30084{index}.TI"
        members = sorted([f"6000{index}1", f"0000{index}2"])
        boards.append(
            {
                "source_key": f"板块:概念_C{index}:{code}",
                "board_code": code,
                "board_name": f"C{index}",
                "source": "ths",
                "category": "概念",
                "type": "concept",
                "group": "同花顺概念",
                "member_codes": members,
                "member_count": len(members),
                "symbols_sha256": hashlib.sha256(
                    json.dumps(members, separators=(",", ":")).encode()
                ).hexdigest(),
                "raw_sha256": hashlib.sha256(code.encode()).hexdigest(),
                "quant_score": 11 + index,
                "final_score": 22 + index,
                "v2_score": 33 + index,
                "selection_score": 44 + index,
                "selection_score_adjusted": 55 + index,
            }
        )
    snapshot = {
        "schema_version": "board_membership_snapshot.v1",
        "mode": "paper_shadow_research_only",
        "as_of_date": "2026-07-17",
        "captured_at": "2026-07-17T15:00:00+08:00",
        "board_type": "concept",
        "board_count": len(boards),
        "boards": boards,
        "source_audit": {
            "raw_board_count": len(boards),
            "normalized_board_count": len(boards),
            "skipped_non_stock_board_count": 0,
            "skipped_non_stock_boards": [],
        },
    }
    snapshot["boards_sha256"] = hashlib.sha256(
        json.dumps(
            boards,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return snapshot


def _history(code, name, days=25, offset=0.0):
    from theme_sector_radar.data.akshare_concept_history import history_rows_sha256

    start = date(2026, 7, 17) - timedelta(days=days - 1)
    rows = []
    for index in range(days):
        day = start + timedelta(days=index)
        pct = round(-0.5 + index * 0.08 + offset, 4)
        close = 100.0 + index + offset
        rows.append(
            {
                "date": day.isoformat(),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "pct_change": pct,
                "amount": 100000.0 + index,
            }
        )
    return {
        "schema_version": "akshare_concept_history.v1",
        "mode": "paper_shadow_research_only",
        "identity": {"board_code": code, "board_name": name},
        "query": {
            "start_date": rows[0]["date"],
            "end_date": "2026-07-17",
            "as_of_date": "2026-07-17",
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


def _histories(snapshot, days=25):
    return {
        board["board_code"]: _history(
            board["board_code"], board["board_name"], days=days, offset=index * 0.2
        )
        for index, board in enumerate(snapshot["boards"])
    }


def test_concept_direction_shadow_is_unavailable_without_20_days():
    from theme_sector_radar.scoring.concept_direction_shadow import (
        score_concept_directions,
    )

    snapshot = _snapshot()
    report = score_concept_directions(
        snapshot,
        _histories(snapshot, days=19),
        snapshot_sha256=membership_snapshot_sha256(snapshot),
        as_of_date="2026-07-17",
    )

    assert all(row["direction_score_shadow"] is None for row in report["concepts"])
    assert all(row["direction_state"] == "unavailable" for row in report["concepts"])


def test_concept_direction_shadow_is_unavailable_without_rank_cross_section():
    from theme_sector_radar.scoring.concept_direction_shadow import (
        score_concept_directions,
    )

    snapshot = _snapshot(board_count=1)
    report = score_concept_directions(
        snapshot,
        _histories(snapshot),
        snapshot_sha256=membership_snapshot_sha256(snapshot),
        as_of_date="2026-07-17",
    )

    row = report["concepts"][0]
    assert row["direction_score_shadow"] is None
    assert row["layers"]["rank_momentum"]["status"] == "unavailable"


def test_complete_concept_inputs_score_and_remain_shadow_only():
    from theme_sector_radar.scoring.concept_direction_shadow import (
        score_concept_directions,
        select_concept_shadow_candidates,
    )

    snapshot = _snapshot()
    histories = _histories(snapshot)
    snapshot_before = deepcopy(snapshot)
    histories_before = deepcopy(histories)
    report = score_concept_directions(
        snapshot,
        histories,
        snapshot_sha256=membership_snapshot_sha256(snapshot),
        as_of_date="2026-07-17",
    )
    selected = select_concept_shadow_candidates(report, top_n=2)

    assert report["schema_version"] == "concept_direction_score_shadow.v1"
    assert report["mode"] == "paper_shadow_research_only"
    assert report["formal_candidate_eligible"] is False
    assert all(row["direction_score_shadow"] is not None for row in report["concepts"])
    assert all(row["formal_candidate_eligible"] is False for row in report["concepts"])
    assert selected["formal_candidate_eligible"] is False
    assert all(
        row["formal_candidate_eligible"] is False
        for row in selected["concept_shadow_candidates"]
    )
    assert snapshot == snapshot_before
    assert histories == histories_before
    for board_before, board_after in zip(snapshot_before["boards"], snapshot["boards"]):
        for field in PROTECTED:
            assert board_after[field] == board_before[field]
    assert not any(field in row for row in report["concepts"] for field in PROTECTED)
    json.loads(
        json.dumps(report, ensure_ascii=False, allow_nan=False),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def test_concept_direction_rejects_stale_history_end_date():
    import pytest

    from theme_sector_radar.data.board_membership_snapshot import (
        membership_snapshot_sha256,
    )
    from theme_sector_radar.scoring.concept_direction_shadow import (
        score_concept_directions,
    )

    snapshot = _snapshot()
    histories = _histories(snapshot)
    for history in histories.values():
        history["query"]["end_date"] = "2026-07-16"
        history["rows"] = history["rows"][:-1]
        history["coverage"]["row_count"] -= 1
        history["coverage"]["last_date"] = "2026-07-16"
        from theme_sector_radar.data.akshare_concept_history import history_rows_sha256

        history["rows_sha256"] = history_rows_sha256(history["rows"])

    with pytest.raises(ValueError, match="through_as_of|not PIT for"):
        score_concept_directions(
            snapshot,
            histories,
            snapshot_sha256=membership_snapshot_sha256(snapshot),
            as_of_date="2026-07-17",
        )


def test_concept_direction_rejects_snapshot_sha_mismatch():
    import pytest

    from theme_sector_radar.scoring.concept_direction_shadow import (
        score_concept_directions,
    )

    snapshot = _snapshot()

    with pytest.raises(ValueError, match="does not match membership snapshot"):
        score_concept_directions(
            snapshot,
            _histories(snapshot),
            snapshot_sha256="a" * 64,
            as_of_date="2026-07-17",
        )


def test_concept_direction_with_short_history_is_unavailable():
    from theme_sector_radar.scoring.concept_direction_shadow import (
        score_concept_directions,
    )

    snapshot = _snapshot()
    histories = _histories(snapshot, days=2)
    report = score_concept_directions(
        snapshot,
        histories,
        snapshot_sha256=membership_snapshot_sha256(snapshot),
        as_of_date="2026-07-17",
    )

    assert all(row["direction_score_shadow"] is None for row in report["concepts"])
