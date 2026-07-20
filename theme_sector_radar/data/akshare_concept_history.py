"""Point-in-time concept history adapter with strict cache fallback."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from ..reporting.strict_json import load_strict_json
from .return_validation import trusted_daily_return


SCHEMA_VERSION = "akshare_concept_history.v1"
PAPER_MODE = "paper_shadow_research_only"


class AkShareConceptHistoryClient:
    """Fetch normalized daily concept bars and bind fallback to one query."""

    def __init__(self, *, client: Any = None, cache_root: Path | str):
        if client is None:
            import akshare as client  # type: ignore[no-redef]
        self._client = client
        self._cache_root = Path(cache_root)

    def get_history(
        self,
        *,
        board_code: str,
        board_name: str,
        start_date: str,
        end_date: str,
        as_of_date: str,
    ) -> dict[str, Any]:
        identity = {
            "board_code": _required_text(board_code, "board_code").upper(),
            "board_name": _required_text(board_name, "board_name"),
        }
        query = _query(start_date=start_date, end_date=end_date, as_of_date=as_of_date)
        cache_path = self._cache_path(identity=identity, query=query)
        try:
            raw_rows = self._client.stock_board_concept_hist_em(
                symbol=identity["board_name"],
                start_date=query["start_date"].replace("-", ""),
                end_date=query["end_date"].replace("-", ""),
                period="daily",
                adjust="",
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as upstream_error:
            try:
                payload = load_strict_json(cache_path)
                validate_history_payload(
                    payload,
                    expected_identity=identity,
                    expected_query=query,
                )
            except Exception as cache_error:
                raise RuntimeError(
                    "concept history fetch failed and no exact covering cache is available"
                ) from upstream_error
            return payload
        rows = _normalize_rows(raw_rows, query=query)
        payload = _build_payload(identity=identity, query=query, rows=rows)
        _write_cache(cache_path, payload)
        return payload

    def _cache_path(
        self,
        *,
        identity: dict[str, str],
        query: dict[str, str],
    ) -> Path:
        cache_identity = {"identity": identity, "query": query}
        digest = hashlib.sha256(_canonical_json_bytes(cache_identity)).hexdigest()[:20]
        safe_code = "".join(
            character if character.isalnum() else "_"
            for character in identity["board_code"]
        )
        return self._cache_root / safe_code / f"{digest}.json"


def history_rows_sha256(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical_json_bytes(rows)).hexdigest()


def validate_history_payload(
    payload: Any,
    *,
    expected_identity: dict[str, str] | None = None,
    expected_query: dict[str, str] | None = None,
) -> None:
    if not isinstance(payload, dict):
        raise ValueError("concept history payload must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("concept history schema_version mismatch")
    if payload.get("mode") != PAPER_MODE:
        raise ValueError("concept history mode mismatch")
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        raise ValueError("concept history identity must be an object")
    normalized_identity = {
        "board_code": _required_text(identity.get("board_code"), "board_code").upper(),
        "board_name": _required_text(identity.get("board_name"), "board_name"),
    }
    query_value = payload.get("query")
    if not isinstance(query_value, dict):
        raise ValueError("concept history query must be an object")
    if set(query_value) != {"start_date", "end_date", "as_of_date"}:
        raise ValueError("concept history query fields mismatch")
    normalized_query = _query(
        start_date=query_value.get("start_date"),
        end_date=query_value.get("end_date"),
        as_of_date=query_value.get("as_of_date"),
    )
    if expected_identity is not None and normalized_identity != expected_identity:
        raise ValueError("concept history identity mismatch")
    if expected_query is not None and normalized_query != expected_query:
        raise ValueError("concept history query does not exactly cover request")

    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("concept history rows must be a non-empty array")
    normalized_rows = _normalize_rows(rows, query=normalized_query)
    if normalized_rows != rows:
        raise ValueError("concept history rows are not canonically normalized")
    if payload.get("rows_sha256") != history_rows_sha256(rows):
        raise ValueError("concept history rows_sha256 mismatch")
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError("concept history coverage must be an object")
    if rows[-1]["date"] != normalized_query["end_date"]:
        raise ValueError("concept history rows do not cover end_date")
    if coverage.get("first_date") != rows[0]["date"]:
        raise ValueError("concept history first_date mismatch")
    if coverage.get("last_date") != rows[-1]["date"]:
        raise ValueError("concept history last_date mismatch")
    expected_through_as_of = rows[-1]["date"] >= normalized_query["as_of_date"]
    if coverage.get("through_as_of") is not expected_through_as_of:
        raise ValueError("concept history through_as_of mismatch")
    if not expected_through_as_of:
        raise ValueError("concept history cache does not cover as_of")
    if coverage.get("row_count") != len(rows):
        raise ValueError("concept history row_count mismatch")


def _build_payload(
    *,
    identity: dict[str, str],
    query: dict[str, str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": PAPER_MODE,
        "identity": identity,
        "query": query,
        "coverage": {
            "through_as_of": rows[-1]["date"] >= query["as_of_date"],
            "row_count": len(rows),
            "first_date": rows[0]["date"],
            "last_date": rows[-1]["date"],
        },
        "rows": rows,
        "rows_sha256": history_rows_sha256(rows),
        "provenance": {"source": "akshare.stock_board_concept_hist_em"},
    }
    validate_history_payload(
        payload,
        expected_identity=identity,
        expected_query=query,
    )
    return payload


def _normalize_rows(value: Any, *, query: dict[str, str]) -> list[dict[str, Any]]:
    if hasattr(value, "to_dict"):
        try:
            value = value.to_dict("records")
        except TypeError as exc:
            raise ValueError("concept history table cannot be converted to records") from exc
    if not isinstance(value, list) or not value:
        raise ValueError("concept history response must be a non-empty row array")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"concept history row {index} must be an object")
        row_date = _iso_date(
            _first(raw, "date", "日期"),
            field=f"rows[{index}].date",
        )
        if not (
            query["start_date"] <= row_date <= query["end_date"]
            and row_date <= query["as_of_date"]
        ):
            raise ValueError(f"concept history row {index} is outside PIT query")
        row = {
            "date": row_date,
            "open": _finite_float(_first(raw, "open", "开盘"), f"rows[{index}].open"),
            "high": _finite_float(_first(raw, "high", "最高"), f"rows[{index}].high"),
            "low": _finite_float(_first(raw, "low", "最低"), f"rows[{index}].low"),
            "close": _finite_float(_first(raw, "close", "收盘"), f"rows[{index}].close"),
            "pct_change": trusted_daily_return(
                _first(raw, "pct_change", "涨跌幅"),
                field=f"rows[{index}].pct_change",
            ),
            "amount": _finite_float(
                _first(raw, "amount", "成交额"), f"rows[{index}].amount"
            ),
        }
        if row["open"] <= 0 or row["close"] <= 0 or row["low"] <= 0:
            raise ValueError(f"concept history row {index} prices must be positive")
        if row["high"] < max(row["open"], row["close"], row["low"]):
            raise ValueError(f"concept history row {index} high is inconsistent")
        if row["low"] > min(row["open"], row["close"], row["high"]):
            raise ValueError(f"concept history row {index} low is inconsistent")
        if row["amount"] < 0:
            raise ValueError(f"concept history row {index} amount must be non-negative")
        rows.append(row)
    rows.sort(key=lambda item: item["date"])
    dates = [row["date"] for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("concept history contains duplicate dates")
    if dates[-1] != query["end_date"]:
        raise ValueError("concept history rows do not cover end_date")
    return rows


def _query(*, start_date: Any, end_date: Any, as_of_date: Any) -> dict[str, str]:
    start = _iso_date(start_date, field="start_date")
    end = _iso_date(end_date, field="end_date")
    as_of = _iso_date(as_of_date, field="as_of_date")
    if start > end:
        raise ValueError("concept history start_date must not exceed end_date")
    if end > as_of:
        raise ValueError("concept history end_date must not exceed as_of_date")
    return {"start_date": start, "end_date": end, "as_of_date": as_of}


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _finite_float(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


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


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    content = (json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if path.read_bytes() == content:
            return
        raise FileExistsError(f"immutable concept history cache already exists: {path}")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
