"""Immutable point-in-time snapshots of board constituents."""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from ..reporting.strict_json import load_strict_json_with_sha256
from .stockdb_board_client import normalize_a_share_code


SCHEMA_VERSION = "board_membership_snapshot.v1"
PAPER_MODE = "paper_shadow_research_only"
SNAPSHOT_FILENAME = "concept_membership_snapshot.json"


def snapshot_path(root: Path | str, as_of_date: str) -> Path:
    normalized_date = _iso_date(as_of_date, field="as_of_date")
    return Path(root) / normalized_date / SNAPSHOT_FILENAME


def build_membership_snapshot(
    boards: Iterable[dict[str, Any]],
    *,
    as_of_date: str,
    captured_at: str | None = None,
    source_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_date = _iso_date(as_of_date, field="as_of_date")
    capture_time = captured_at or datetime.now().astimezone().isoformat(timespec="seconds")
    _iso_datetime(capture_time, field="captured_at")
    if isinstance(boards, (str, bytes)):
        raise ValueError("boards must be an array")

    rows = [_snapshot_board(board) for board in boards]
    rows.sort(key=lambda item: (item["board_code"], item["board_name"]))
    if not rows:
        raise ValueError("membership snapshot requires at least one board")
    _assert_unique_board_dimensions(rows)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": PAPER_MODE,
        "as_of_date": normalized_date,
        "captured_at": capture_time,
        "board_type": "concept",
        "board_count": len(rows),
        "boards": rows,
    }
    if source_audit is not None:
        if not isinstance(source_audit, dict):
            raise ValueError("source_audit must be an object")
        payload["source_audit"] = json.loads(
            json.dumps(source_audit, ensure_ascii=False, allow_nan=False)
        )
    else:
        payload["source_audit"] = {
            "raw_board_count": len(rows),
            "normalized_board_count": len(rows),
            "skipped_non_stock_board_count": 0,
            "skipped_non_stock_boards": [],
        }
    payload["boards_sha256"] = _sha256(rows)
    validate_membership_snapshot(payload, expected_as_of_date=normalized_date)
    return payload


def capture_membership_snapshot(
    board_client: Any,
    *,
    as_of_date: str,
    captured_at: str | None = None,
) -> dict[str, Any]:
    boards = board_client.list_boards("concept")
    return build_membership_snapshot(
        boards,
        as_of_date=as_of_date,
        captured_at=captured_at,
        source_audit=getattr(board_client, "last_list_audit", None),
    )


def write_membership_snapshot_once(
    root: Path | str,
    snapshot: dict[str, Any],
) -> Path:
    validate_membership_snapshot(
        snapshot,
        expected_as_of_date=str(snapshot.get("as_of_date") or ""),
    )
    target = snapshot_path(root, snapshot["as_of_date"])
    target.parent.mkdir(parents=True, exist_ok=True)
    content = _stable_json_bytes(snapshot)
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if target.read_bytes() == content:
            return target
        raise FileExistsError(
            f"refusing to overwrite immutable membership snapshot: {target}"
        )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def load_membership_snapshot(
    root: Path | str,
    as_of_date: str,
) -> tuple[dict[str, Any], str]:
    expected_date = _iso_date(as_of_date, field="as_of_date")
    target = snapshot_path(root, expected_date)
    if not target.is_file():
        raise FileNotFoundError(f"membership snapshot not found for {expected_date}: {target}")
    payload, file_sha256 = load_strict_json_with_sha256(target)
    validate_membership_snapshot(payload, expected_as_of_date=expected_date)
    return payload, file_sha256


def validate_membership_snapshot(
    payload: Any,
    *,
    expected_as_of_date: str,
) -> None:
    if not isinstance(payload, dict):
        raise ValueError("membership snapshot must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("membership snapshot schema_version mismatch")
    if payload.get("mode") != PAPER_MODE:
        raise ValueError("membership snapshot mode mismatch")
    expected_date = _iso_date(expected_as_of_date, field="expected_as_of_date")
    actual_date = _iso_date(payload.get("as_of_date"), field="as_of_date")
    if actual_date != expected_date:
        raise ValueError(
            f"membership snapshot as_of_date mismatch: expected {expected_date}, got {actual_date}"
        )
    _iso_datetime(payload.get("captured_at"), field="captured_at")
    if payload.get("board_type") != "concept":
        raise ValueError("membership snapshot board_type mismatch")
    boards = payload.get("boards")
    if not isinstance(boards, list) or not boards:
        raise ValueError("membership snapshot boards must be a non-empty array")
    if payload.get("board_count") != len(boards):
        raise ValueError("membership snapshot board_count mismatch")
    if payload.get("boards_sha256") != _sha256(boards):
        raise ValueError("membership snapshot boards_sha256 mismatch")
    if "source_audit" not in payload:
        raise ValueError("membership snapshot source_audit is required")
    _validate_source_audit(payload["source_audit"], board_count=len(boards))

    _assert_unique_board_dimensions(boards)
    previous_identity: tuple[str, str] | None = None
    for board in boards:
        if not isinstance(board, dict):
            raise ValueError("membership snapshot board must be an object")
        identity = _validate_snapshot_board(board)
        if previous_identity is not None and identity < previous_identity:
            raise ValueError("membership snapshot boards must be stably sorted")
        previous_identity = identity


def membership_snapshot_sha256(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json_bytes(snapshot)).hexdigest()


def _snapshot_board(board: Any) -> dict[str, Any]:
    if not isinstance(board, dict):
        raise ValueError("board must be an object")
    member_values = board.get("symbols", board.get("member_codes"))
    if not isinstance(member_values, list) or not member_values:
        raise ValueError("board members must be a non-empty array")
    members = sorted({normalize_a_share_code(value) for value in member_values})
    if len(members) != len(member_values):
        raise ValueError("snapshot input members must already be unique valid codes")
    raw_sha256 = str(board.get("raw_sha256") or "").lower()
    if not _is_sha256(raw_sha256):
        raise ValueError("board raw_sha256 must be a SHA-256 digest")
    row = {
        "source_key": _required_text(board.get("source_key"), "source_key"),
        "board_code": _required_text(
            board.get("code") or board.get("board_code"), "board_code"
        ).upper(),
        "board_name": _required_text(
            board.get("name") or board.get("board_name"), "board_name"
        ),
        "source": _required_text(board.get("source"), "source"),
        "category": _required_text(board.get("category"), "category"),
        "type": _required_text(board.get("type"), "type"),
        "group": _required_text(board.get("group"), "group"),
        "member_codes": members,
        "member_count": len(members),
        "symbols_sha256": _sha256(members),
        "raw_sha256": raw_sha256,
    }
    _validate_snapshot_board(row)
    return row


def _validate_snapshot_board(board: dict[str, Any]) -> tuple[str, str]:
    source_key = _required_text(board.get("source_key"), "source_key")
    code = _required_text(board.get("board_code"), "board_code")
    name = _required_text(board.get("board_name"), "board_name")
    for field in ("source", "category", "group"):
        _required_text(board.get(field), field)
    if board.get("type") != "concept":
        raise ValueError(f"snapshot board type must be concept: {source_key}")
    members = board.get("member_codes")
    if not isinstance(members, list) or not members:
        raise ValueError("snapshot member_codes must be a non-empty array")
    normalized = [normalize_a_share_code(value) for value in members]
    if normalized != sorted(set(normalized)):
        raise ValueError("snapshot member_codes must be unique and stably sorted")
    if board.get("member_count") != len(normalized):
        raise ValueError("snapshot member_count mismatch")
    if board.get("symbols_sha256") != _sha256(normalized):
        raise ValueError("snapshot symbols_sha256 mismatch")
    if not _is_sha256(board.get("raw_sha256")):
        raise ValueError("snapshot raw_sha256 is invalid")
    return code, name


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _assert_unique_board_dimensions(rows: list[dict[str, Any]]) -> None:
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("membership snapshot board must be an object")
    dimensions = {
        "board_code": [row.get("board_code") for row in rows],
        "board_name": [row.get("board_name") for row in rows],
        "source_key": [row.get("source_key") for row in rows],
    }
    for field, values in dimensions.items():
        if len(values) != len(set(values)):
            raise ValueError(f"membership snapshot contains duplicate board {field}")


def _validate_source_audit(audit: Any, *, board_count: int) -> None:
    if not isinstance(audit, dict):
        raise ValueError("membership snapshot source_audit must be an object")
    names = ("raw_board_count", "normalized_board_count", "skipped_non_stock_board_count")
    counts = {}
    for name in names:
        value = audit.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"source_audit {name} must be a non-negative integer")
        counts[name] = value
    skipped = audit.get("skipped_non_stock_boards")
    if not isinstance(skipped, list):
        raise ValueError("source_audit skipped_non_stock_boards must be an array")
    if counts["raw_board_count"] != counts["normalized_board_count"] + counts["skipped_non_stock_board_count"]:
        raise ValueError("source_audit board counts are inconsistent")
    if counts["normalized_board_count"] != board_count:
        raise ValueError("source_audit normalized board count mismatch")
    if len(skipped) != counts["skipped_non_stock_board_count"]:
        raise ValueError("source_audit skipped board count mismatch")
    skipped_dimensions = {
        field: [item.get(field) for item in skipped if isinstance(item, dict)]
        for field in ("source_key", "board_code", "board_name")
    }
    for field, values in skipped_dimensions.items():
        if len(values) != len(set(values)):
            raise ValueError(f"source_audit duplicate skipped board {field}")
    for item in skipped:
        if not isinstance(item, dict):
            raise ValueError("source_audit skipped board must be an object")
        for field in ("source_key", "board_code", "board_name", "reason"):
            _required_text(item.get(field), f"source_audit {field}")
        input_count = item.get("input_symbol_count")
        if isinstance(input_count, bool) or not isinstance(input_count, int) or input_count < 1:
            raise ValueError("source_audit input_symbol_count is invalid")
        raw_symbols = item.get("raw_symbols")
        if not isinstance(raw_symbols, list) or len(raw_symbols) != input_count:
            raise ValueError("source_audit raw_symbols are invalid")
        if item.get("raw_symbols_sha256") != _sha256(raw_symbols):
            raise ValueError("source_audit raw_symbols_sha256 mismatch")
        raw_record = item.get("raw_record")
        if not isinstance(raw_record, dict):
            raise ValueError("source_audit raw_record is invalid")
        if raw_record.get("symbols") != raw_symbols:
            raise ValueError("source_audit raw_record symbols mismatch")
        if any(_is_valid_a_share_symbol(value) for value in raw_symbols):
            raise ValueError("source_audit contains a valid A-share symbol")
        if item.get("reason") != "no_valid_a_share_constituents":
            raise ValueError("source_audit exclusion reason is invalid")
        if item.get("raw_record_sha256") != _sha256(raw_record):
            raise ValueError("source_audit raw_record_sha256 mismatch")


def _is_valid_a_share_symbol(value: Any) -> bool:
    try:
        normalize_a_share_code(value)
    except ValueError:
        return False
    return True


def _iso_date(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be an ISO date")
    return value


def _iso_datetime(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO datetime")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return value


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value.lower())


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _stable_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
