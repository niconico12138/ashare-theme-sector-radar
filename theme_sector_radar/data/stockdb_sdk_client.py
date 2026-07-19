"""Local StockDB SDK adapter.

This module wraps the desktop StockDB Python SDK behind the same small
``get_stock_bars`` shape used by ``MarketDataHttpClient``.  It is intended for
local freshness checks and calibration backfills when the HTTP service is
stale or unavailable.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

DEFAULT_PROBE_CODES = ("600519", "600633", "000001")
DEFAULT_BAR_FIELDS = (
    "date",
    "code",
    "name",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "pct_chg",
    "is_st",
)


class StockDBSdkClient:
    """Small adapter around the desktop StockDB ``StockDBClient``."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7899,
        sdk_path: Path | str | None = None,
        sdk_client: Any = None,
    ):
        if sdk_client is not None:
            self._client = sdk_client
            return

        resolved_sdk_path = _resolve_stockdb_sdk_path(sdk_path)
        if str(resolved_sdk_path) not in sys.path:
            sys.path.insert(0, str(resolved_sdk_path))

        sdk_file = resolved_sdk_path / "stock_sdk.py"
        spec = importlib.util.spec_from_file_location("desktop_stockdb_stock_sdk", sdk_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load StockDB SDK from {sdk_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stockdb_client_cls = module.StockDBClient

        self._client = stockdb_client_cls(host=host, port=port)

    def get_stock_bars(
        self,
        code: str,
        start: str,
        end: str,
        frequency: str = "1d",
        fq: Optional[str] = "qfq",
        fields: Iterable[str] | str = DEFAULT_BAR_FIELDS,
        limit: int | None = None,
        desc: bool = False,
    ) -> list[dict[str, Any]]:
        """Return normalized bar dictionaries for one stock."""
        field_list = _field_list(fields)
        kwargs = {
            "start": start,
            "end": end,
            "frequency": frequency,
            "fields": ",".join(field_list),
            "fq": fq,
        }
        if limit is not None:
            kwargs["limit"] = limit
        if desc:
            kwargs["desc"] = desc
        rows = self._client.get_data(code, **kwargs)
        if isinstance(rows, dict):
            rows = rows.get(code, [])
        return [self._normalize_row(row, field_list) for row in rows or [] if row is not None]

    def get_latest_daily_date(
        self,
        codes: Iterable[str] = DEFAULT_PROBE_CODES,
        start: str = "20260101",
        end: str = "20261231",
    ) -> str | None:
        """Probe several liquid stocks and return the latest available date."""
        latest: str | None = None
        for code in codes:
            try:
                bars = self.get_stock_bars(
                    str(code),
                    start=start,
                    end=end,
                    frequency="1d",
                    fields=("date",),
                    limit=1,
                    desc=True,
                )
            except Exception:
                continue
            for bar in bars:
                date = _normalize_date(bar.get("date"))
                if date and (latest is None or date > latest):
                    latest = date
        return latest

    def probe_freshness(
        self,
        expected_date: str | None = None,
        codes: Iterable[str] = DEFAULT_PROBE_CODES,
    ) -> dict[str, Any]:
        """Return a compact StockDB freshness diagnostic."""
        try:
            latest = self.get_latest_daily_date(codes=codes)
            ok = bool(latest) and (expected_date is None or latest >= expected_date.replace("-", ""))
            return {
                "ok": ok,
                "latest_daily_date": latest,
                "expected_date": expected_date,
                "probe_codes": list(codes),
                "source": "stockdb-sdk",
                "error": None,
            }
        except Exception as exc:
            return {
                "ok": False,
                "latest_daily_date": None,
                "expected_date": expected_date,
                "probe_codes": list(codes),
                "source": "stockdb-sdk",
                "error": str(exc),
            }

    @staticmethod
    def _normalize_row(row: Any, fields: Iterable[str] = DEFAULT_BAR_FIELDS) -> dict[str, Any]:
        field_list = _field_list(fields)
        if isinstance(row, dict):
            normalized = dict(row)
        elif isinstance(row, (list, tuple)):
            normalized = {
                field: row[idx] if idx < len(row) else None
                for idx, field in enumerate(field_list)
            }
        elif len(field_list) == 1:
            normalized = {field_list[0]: row}
        else:
            normalized = {}

        if "date" in normalized:
            normalized["date"] = _normalize_date(normalized.get("date"))
        if "code" in normalized and normalized["code"] is not None:
            normalized["code"] = str(normalized["code"]).strip()
        return normalized


def _field_list(fields: Iterable[str] | str) -> list[str]:
    if isinstance(fields, str):
        return [field.strip() for field in fields.split(",") if field.strip()]
    return [str(field).strip() for field in fields if str(field).strip()]


def _resolve_stockdb_sdk_path(sdk_path: Path | str | None) -> Path:
    candidates: list[Path] = []
    if sdk_path is not None and str(sdk_path).strip():
        candidates.append(Path(sdk_path).expanduser())

    env_path = os.environ.get("STOCKDB_SDK_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())

    candidates.append(Path.home() / "Desktop" / "stockdb" / "pybao")

    checked: list[str] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if str(resolved) in checked:
            continue
        checked.append(str(resolved))
        if (resolved / "stock_sdk.py").is_file() and (
            resolved / "stockdb.pyd"
        ).is_file():
            return resolved

    locations = ", ".join(checked) or "<none>"
    raise ImportError(
        "StockDB desktop SDK requires both stock_sdk.py and stockdb.pyd; "
        f"checked: {locations}"
    )


def _normalize_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value).strip().replace("-", "")[:8]
