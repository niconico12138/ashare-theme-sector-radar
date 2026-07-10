"""Today realtime A-share snapshot client.

This client is intentionally labelled as ``intraday_snapshot``.  It can help
daily observation when StockDB has not published final daily bars yet, but it
must not be treated as final OHLC daily data for calibration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class TodayRealtimeClient:
    def __init__(self, ak_client: Any | None = None):
        self._ak_client = ak_client

    def _get_ak(self):
        if self._ak_client is not None:
            return self._ak_client
        import akshare as ak

        self._ak_client = ak
        return ak

    def get_a_share_spot(self) -> dict[str, Any]:
        ak = self._get_ak()
        fallback_reason = None
        try:
            df = ak.stock_zh_a_spot_em()
            source = "akshare/stock_zh_a_spot_em"
            fallback_used = False
        except Exception as exc:
            fallback_reason = str(exc)
            df = ak.stock_zh_a_spot()
            source = "akshare/stock_zh_a_spot"
            fallback_used = True

        rows = [self._normalize_row(row) for row in df.to_dict(orient="records")]
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "source": source,
            "data_semantics": "intraday_snapshot",
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "row_count": len(rows),
            "rows": rows,
        }

    def get_stock_snapshot(self, code: str) -> dict[str, Any] | None:
        wanted = str(code).strip()
        result = self.get_a_share_spot()
        for row in result["rows"]:
            if row.get("code") == wanted:
                return {
                    **row,
                    "source": result["source"],
                    "data_semantics": result["data_semantics"],
                    "generated_at": result["generated_at"],
                }
        return None

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "code": _clean_code(row.get("代码") or row.get("code") or row.get("symbol")),
            "name": _clean_text(row.get("名称") or row.get("name")),
            "latest_price": _coerce_float(row.get("最新价") or row.get("最新报价") or row.get("price")),
            "change_pct": _coerce_float(row.get("涨跌幅") or row.get("change_pct")),
            "volume": _coerce_float(row.get("成交量") or row.get("volume")),
            "amount": _coerce_float(row.get("成交额") or row.get("amount")),
        }


def _clean_code(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[-6:] if len(text) >= 6 else text


def _clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
