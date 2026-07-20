"""Strict adapter for StockDB's native board key space."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


BOARD_PREFIXES = {
    "concept": "板块:概念*",
    "sw_1": "板块:申万一级*",
    "sw_2": "板块:申万二级*",
    "sw_3": "板块:申万三级*",
}

_BOARD_CODE_RE = re.compile(r"^[0-9A-Z][0-9A-Z._-]{1,31}$")
_STOCK_CODE_RE = re.compile(r"^(?P<code>[0-9]{6})(?:\.(?:SH|SZ|BJ))?$", re.I)
_A_SHARE_LEADING_DIGITS = frozenset("034689")


class StockDBBoardClient:
    """Read and normalize board identities and current constituents."""

    def __init__(self, backend: Any = None):
        if backend is None:
            from stockdb import rd  # type: ignore[import-not-found]

            backend = rd
        self._backend = backend
        self.last_list_audit: dict[str, Any] = {}

    def list_boards(self, board_type: str) -> list[dict[str, Any]]:
        prefix = BOARD_PREFIXES.get(str(board_type))
        if prefix is None:
            raise ValueError(f"unsupported board_type: {board_type}")
        raw_keys = self._backend.keys(prefix)
        if isinstance(raw_keys, (str, bytes, dict)) or raw_keys is None:
            raise ValueError("StockDB board keys result must be an array")
        try:
            raw_key_values = list(raw_keys)
        except TypeError as exc:
            raise ValueError("StockDB board keys result must be an array") from exc

        source_keys: list[str] = []
        for raw_key in raw_key_values:
            key = str(raw_key).strip()
            if not key:
                raise ValueError("StockDB board key must be non-empty")
            source_keys.append(key)
        if len(source_keys) != len(set(source_keys)):
            raise ValueError("duplicate board source key")

        boards: list[dict[str, Any]] = []
        skipped_non_stock_boards: list[dict[str, Any]] = []
        for source_key in sorted(source_keys):
            raw_value = self._backend.get(source_key)
            raw_record = _unwrap_board_record(raw_value, source_key=source_key)
            symbols = raw_record.get("symbols")
            if (
                isinstance(symbols, (list, tuple))
                and symbols
                and not any(_normalize_stock_code(value) for value in symbols)
            ):
                skipped_non_stock_boards.append(
                    {
                        "source_key": source_key,
                        "board_code": raw_record.get("code") or raw_record.get("board_code"),
                        "board_name": raw_record.get("name") or raw_record.get("board_name"),
                        "reason": "no_valid_a_share_constituents",
                        "input_symbol_count": len(symbols),
                        "raw_record": raw_record,
                        "raw_record_sha256": hashlib.sha256(
                            _canonical_json_bytes(raw_record)
                        ).hexdigest(),
                        "raw_symbols": list(symbols),
                        "raw_symbols_sha256": hashlib.sha256(
                            _canonical_json_bytes(list(symbols))
                        ).hexdigest(),
                    }
                )
                continue
            boards.append(
                self._normalize_board(
                    raw_record,
                    source_key=source_key,
                    expected_type=str(board_type),
                )
            )
        self.last_list_audit = {
            "board_type": str(board_type),
            "raw_board_count": len(source_keys),
            "normalized_board_count": len(boards),
            "skipped_non_stock_board_count": len(skipped_non_stock_boards),
            "skipped_non_stock_boards": skipped_non_stock_boards,
        }
        identities: set[tuple[str, str]] = set()
        names: set[tuple[str, str]] = set()
        for board in boards:
            code_identity = (board["type"], board["code"])
            name_identity = (board["type"], board["name"])
            if code_identity in identities or name_identity in names:
                raise ValueError(
                    f"duplicate board identity: {board['code']} / {board['name']}"
                )
            identities.add(code_identity)
            names.add(name_identity)
        return sorted(boards, key=lambda item: (item["code"], item["name"]))

    def get_board(self, identity: str, *, board_type: str) -> dict[str, Any]:
        target = str(identity).strip()
        matches = [
            board
            for board in self.list_boards(board_type)
            if target in {board["code"], board["name"], board["source_key"]}
        ]
        if len(matches) != 1:
            raise ValueError(
                f"board identity must resolve exactly once: {identity!r}; matches={len(matches)}"
            )
        return matches[0]

    def get_constituents(self, identity: str, *, board_type: str) -> list[str]:
        return list(self.get_board(identity, board_type=board_type)["symbols"])

    @staticmethod
    def _normalize_board(
        raw_value: Any,
        *,
        source_key: str,
        expected_type: str,
    ) -> dict[str, Any]:
        raw = _unwrap_board_record(raw_value, source_key=source_key)
        raw_bytes = _canonical_json_bytes(raw)
        code = _required_text(raw.get("code") or raw.get("board_code"), "board code")
        name = _required_text(raw.get("name") or raw.get("board_name"), "board name")
        source = _required_text(raw.get("source"), "board source")
        category = _required_text(raw.get("category"), "board category")
        raw_type = _required_text(raw.get("type") or expected_type, "board type")
        group = _required_text(raw.get("group") or category, "board group")
        if raw_type != expected_type:
            raise ValueError(
                f"board type mismatch for {source_key}: expected {expected_type}, got {raw_type}"
            )
        if not _BOARD_CODE_RE.fullmatch(code.upper()):
            raise ValueError(f"invalid board code: {code}")

        symbols_value = raw.get("symbols")
        if isinstance(symbols_value, (str, bytes)) or not isinstance(
            symbols_value, (list, tuple)
        ):
            raise ValueError(f"board symbols must be an array: {source_key}")
        valid_symbols: list[str] = []
        invalid_count = 0
        for value in symbols_value:
            symbol = _normalize_stock_code(value)
            if symbol is None:
                invalid_count += 1
            else:
                valid_symbols.append(symbol)
        unique_symbols = sorted(set(valid_symbols))
        duplicate_count = len(valid_symbols) - len(unique_symbols)
        if not unique_symbols:
            raise ValueError(f"board has no valid A-share constituents: {source_key}")

        return {
            "source_key": source_key,
            "code": code.upper(),
            "name": name,
            "source": source,
            "category": category,
            "type": raw_type,
            "group": group,
            "symbols": unique_symbols,
            "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "normalization_audit": {
                "input_symbol_count": len(symbols_value),
                "invalid_symbol_count": invalid_count,
                "duplicate_symbol_count": duplicate_count,
            },
        }


def normalize_a_share_code(value: Any) -> str:
    result = _normalize_stock_code(value)
    if result is None:
        raise ValueError(f"invalid A-share stock code: {value!r}")
    return result


def _normalize_stock_code(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    match = _STOCK_CODE_RE.fullmatch(str(value).strip())
    if match is None:
        return None
    code = match.group("code")
    if code[0] not in _A_SHARE_LEADING_DIGITS:
        return None
    return code


def _unwrap_board_record(value: Any, *, source_key: str) -> dict[str, Any]:
    if not isinstance(value, (dict, list, tuple)) and hasattr(value, "keys"):
        try:
            value = dict(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"malformed board record: {source_key}") from exc
    if isinstance(value, dict) and source_key in value and len(value) == 1:
        value = value[source_key]
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError(f"board record must resolve exactly once: {source_key}")
        value = value[0]
        if not isinstance(value, dict) and hasattr(value, "keys"):
            try:
                value = dict(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"malformed board record: {source_key}") from exc
    if not isinstance(value, dict) or not value:
        raise ValueError(f"malformed board record: {source_key}")
    return dict(value)


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("board record must be strict JSON data") from exc
    return serialized.encode("utf-8")
