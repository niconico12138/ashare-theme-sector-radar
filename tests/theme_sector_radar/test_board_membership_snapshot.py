from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest


def _board(code="300843.TI", name="5G", symbols=None):
    members = list(symbols or ["000063", "600050"])
    return {
        "source_key": f"板块:概念_{name}:{code}",
        "code": code,
        "name": name,
        "source": "ths",
        "category": "概念",
        "type": "concept",
        "group": "同花顺概念",
        "symbols": members,
        "raw_sha256": hashlib.sha256(f"{code}:{name}".encode()).hexdigest(),
    }


def test_membership_snapshot_write_once_idempotent_and_strict_load(tmp_path):
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
        load_membership_snapshot,
        write_membership_snapshot_once,
    )

    snapshot = build_membership_snapshot(
        [_board()],
        as_of_date="2026-07-19",
        captured_at="2026-07-19T09:00:00+08:00",
    )
    path = write_membership_snapshot_once(tmp_path, snapshot)
    first_bytes = path.read_bytes()

    assert write_membership_snapshot_once(tmp_path, deepcopy(snapshot)) == path
    assert path.read_bytes() == first_bytes
    loaded, file_sha = load_membership_snapshot(tmp_path, "2026-07-19")
    assert loaded == snapshot
    assert file_sha == hashlib.sha256(first_bytes).hexdigest()
    assert loaded["schema_version"] == "board_membership_snapshot.v1"
    assert loaded["mode"] == "paper_shadow_research_only"
    assert loaded["boards"][0]["member_count"] == 2
    json.loads(first_bytes, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def test_membership_snapshot_preserves_capture_source_audit():
    from theme_sector_radar.data.board_membership_snapshot import build_membership_snapshot

    snapshot = build_membership_snapshot(
        [_board()],
        as_of_date="2026-07-19",
        captured_at="2026-07-19T09:00:00+08:00",
        source_audit={
            "raw_board_count": 2,
            "normalized_board_count": 1,
            "skipped_non_stock_board_count": 1,
            "skipped_non_stock_boards": [
                {
                    "source_key": "板块:概念_T+0基金:301643.TI",
                    "board_code": "301643.TI",
                    "board_name": "T+0基金",
                    "reason": "no_valid_a_share_constituents",
                    "input_symbol_count": 2,
                    "raw_record": {"code": "301643.TI", "symbols": ["159920", "510900"]},
                    "raw_record_sha256": hashlib.sha256(
                        json.dumps(
                            {"code": "301643.TI", "symbols": ["159920", "510900"]},
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest(),
                    "raw_symbols": ["159920", "510900"],
                    "raw_symbols_sha256": hashlib.sha256(
                        json.dumps(
                            ["159920", "510900"],
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest(),
                }
            ],
        },
    )

    assert snapshot["source_audit"]["raw_board_count"] == 2
    assert snapshot["source_audit"]["skipped_non_stock_board_count"] == 1


def test_membership_snapshot_rejects_different_same_day_content(tmp_path):
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
        write_membership_snapshot_once,
    )

    first = build_membership_snapshot(
        [_board()],
        as_of_date="2026-07-19",
        captured_at="2026-07-19T09:00:00+08:00",
    )
    changed = build_membership_snapshot(
        [_board(symbols=["000063"])],
        as_of_date="2026-07-19",
        captured_at="2026-07-19T09:00:00+08:00",
    )
    write_membership_snapshot_once(tmp_path, first)

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_membership_snapshot_once(tmp_path, changed)


def test_membership_snapshot_never_falls_back_to_another_date(tmp_path):
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
        load_membership_snapshot,
        write_membership_snapshot_once,
    )

    snapshot = build_membership_snapshot(
        [_board()],
        as_of_date="2026-07-18",
        captured_at="2026-07-18T15:00:00+08:00",
    )
    write_membership_snapshot_once(tmp_path, snapshot)

    with pytest.raises(FileNotFoundError):
        load_membership_snapshot(tmp_path, "2026-07-17")


def test_membership_snapshot_rejects_date_mismatch(tmp_path):
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
        snapshot_path,
        load_membership_snapshot,
    )

    snapshot = build_membership_snapshot(
        [_board()],
        as_of_date="2026-07-18",
        captured_at="2026-07-18T15:00:00+08:00",
    )
    path = snapshot_path(tmp_path, "2026-07-17")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="as_of_date mismatch"):
        load_membership_snapshot(tmp_path, "2026-07-17")


@pytest.mark.parametrize("tamper", ["count", "symbols_sha", "raw_sha", "member_code"])
def test_membership_snapshot_rejects_tampering(tmp_path, tamper):
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
        load_membership_snapshot,
        snapshot_path,
    )

    snapshot = build_membership_snapshot(
        [_board()],
        as_of_date="2026-07-19",
        captured_at="2026-07-19T09:00:00+08:00",
    )
    board = snapshot["boards"][0]
    if tamper == "count":
        board["member_count"] += 1
    elif tamper == "symbols_sha":
        board["symbols_sha256"] = "0" * 64
    elif tamper == "raw_sha":
        board["raw_sha256"] = "bad"
    else:
        board["member_codes"] = ["not-a-stock"]
    path = snapshot_path(tmp_path, "2026-07-19")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError):
        load_membership_snapshot(tmp_path, "2026-07-19")


@pytest.mark.parametrize("duplicate_field", ["code", "name", "source_key"])
def test_membership_snapshot_rejects_duplicate_board_identity_dimension(
    duplicate_field,
):
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
    )

    first = _board(code="300843.TI", name="5G")
    second = _board(code="300844.TI", name="6G")
    second[duplicate_field] = first[duplicate_field]

    with pytest.raises(ValueError, match="duplicate board"):
        build_membership_snapshot(
            [first, second],
            as_of_date="2026-07-19",
            captured_at="2026-07-19T09:00:00+08:00",
        )


def test_membership_snapshot_rejects_inconsistent_source_audit():
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
    )

    with pytest.raises(ValueError, match="source_audit"):
        build_membership_snapshot(
            [_board()],
            as_of_date="2026-07-19",
            captured_at="2026-07-19T09:00:00+08:00",
            source_audit={
                "raw_board_count": 978,
                "normalized_board_count": 1,
                "skipped_non_stock_board_count": 1,
                "skipped_non_stock_boards": [],
            },
        )


def test_membership_snapshot_requires_source_audit():
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
        validate_membership_snapshot,
    )

    from copy import deepcopy
    payload = deepcopy(build_membership_snapshot([_board()], as_of_date="2026-07-19", captured_at="2026-07-19T09:00:00+08:00"))
    payload.pop("source_audit")

    with pytest.raises(ValueError, match="source_audit"):
        validate_membership_snapshot(payload, expected_as_of_date="2026-07-19")


def test_membership_snapshot_rejects_mismatched_excluded_symbols_sha():
    from theme_sector_radar.data.board_membership_snapshot import (
        build_membership_snapshot,
        validate_membership_snapshot,
    )

    snapshot = build_membership_snapshot(
        [_board()],
        as_of_date="2026-07-19",
        captured_at="2026-07-19T09:00:00+08:00",
    )
    audit = snapshot["source_audit"]
    audit["raw_board_count"] = 2
    audit["normalized_board_count"] = 1
    audit["skipped_non_stock_board_count"] = 1
    audit["skipped_non_stock_boards"] = [
        {
            "source_key": "板块:概念_T+0基金:301643.TI",
            "board_code": "301643.TI",
            "board_name": "T+0基金",
            "reason": "no_valid_a_share_constituents",
            "input_symbol_count": 2,
            "raw_record": {"code": "301643.TI", "symbols": ["159920", "510900"]},
            "raw_record_sha256": "0" * 64,
            "raw_symbols": ["159920", "510900"],
            "raw_symbols_sha256": "0" * 64,
        }
    ]

    with pytest.raises(ValueError, match="source_audit (raw_symbols_sha256|raw_record_sha256)"):
        validate_membership_snapshot(snapshot, expected_as_of_date="2026-07-19")
