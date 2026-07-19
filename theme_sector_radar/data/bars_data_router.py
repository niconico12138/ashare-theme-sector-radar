"""Bars data source router for calibration and backfill jobs."""

from __future__ import annotations

import logging
import math
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .market_data_http_client import MarketDataHttpClient
from .stock_bars_provider import get_stock_bars_for_factor
from .stockdb_sdk_client import StockDBSdkClient

HTTP_CLIENT_LOGGER = "theme_sector_radar.data.market_data_http_client"


def extract_latest_daily_date(health: dict[str, Any] | None) -> str | None:
    """Extract a comparable YYYYMMDD latest-date value from a health payload."""
    if not isinstance(health, dict):
        return None
    candidates = [
        health.get("latest_daily_date"),
        health.get("latest_trade_date"),
        health.get("latest_trading_date"),
        health.get("latest_date"),
    ]
    stockdb = health.get("stockdb")
    if isinstance(stockdb, dict):
        candidates.extend(
            [
                stockdb.get("latest_daily_date"),
                stockdb.get("latest_trade_date"),
                stockdb.get("latest_trading_date"),
                stockdb.get("latest_date"),
            ]
        )
    for value in candidates:
        normalized = normalize_date(value)
        if normalized:
            return normalized
    return None


def normalize_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip().replace("-", "")
    return text[:8] if len(text) >= 8 and text[:8].isdigit() else None


@contextmanager
def _suppress_expected_http_probe_warnings():
    logger = logging.getLogger(HTTP_CLIENT_LOGGER)
    previous_level = logger.level
    logger.setLevel(max(previous_level, logging.ERROR))
    try:
        yield
    finally:
        logger.setLevel(previous_level)


class AutoBarsClient:
    """Route stock bar reads across HTTP, StockDB SDK, and local cache."""

    def __init__(
        self,
        http_client: Any | None = None,
        sdk_client: Any | None = None,
        expected_min_date: str | None = None,
        cache_dir: str | Path | None = None,
    ):
        self.http_client = (
            http_client if http_client is not None else MarketDataHttpClient()
        )
        self._sdk_init_error = None
        if sdk_client is not None:
            self.sdk_client = sdk_client
        else:
            try:
                self.sdk_client = StockDBSdkClient()
            except (ImportError, OSError, ConnectionError, RuntimeError, ValueError) as exc:
                self.sdk_client = None
                self._sdk_init_error = str(exc)
        self.expected_min_date = normalize_date(expected_min_date)
        self.cache_dir = Path(cache_dir or "data_cache/stock_bars")
        self.selection = self._select_source()

    def _select_source(self) -> dict[str, Any]:
        http_latest = None
        http_error = None
        try:
            with _suppress_expected_http_probe_warnings():
                http_latest = extract_latest_daily_date(self.http_client.health_check())
        except Exception as exc:
            http_error = str(exc)

        sdk_latest = None
        sdk_error = self._sdk_init_error
        if self.sdk_client is not None:
            try:
                sdk_latest = normalize_date(self.sdk_client.get_latest_daily_date())
            except Exception as exc:
                sdk_error = str(exc)

        http_available = http_error is None
        sdk_available = sdk_error is None and self.sdk_client is not None
        http_fresh = http_available and (
            self.expected_min_date is None
            or bool(http_latest and http_latest >= self.expected_min_date)
        )
        sdk_fresh = sdk_available and (
            self.expected_min_date is None
            or bool(sdk_latest and sdk_latest >= self.expected_min_date)
        )

        source = "unavailable"
        reason = "no_usable_bars_source"
        if http_fresh and sdk_fresh:
            if sdk_latest and http_latest and sdk_latest > http_latest:
                source = "stockdb-sdk"
                reason = "sdk_newer_than_http"
            else:
                source = "http"
                reason = "http_fresh"
        elif http_fresh:
            source = "http"
            reason = (
                "sdk_unavailable_http_fallback"
                if sdk_error
                else "http_fresh"
            )
        elif sdk_fresh:
            source = "stockdb-sdk"
            reason = (
                "http_unavailable"
                if http_error
                else "http_older_than_expected"
            )
        elif self.expected_min_date and (http_available or sdk_available):
            reason = "no_source_meets_expected_min_date"

        return {
            "source": source,
            "reason": reason,
            "http_latest_daily_date": http_latest,
            "sdk_latest_daily_date": sdk_latest,
            "expected_min_date": self.expected_min_date,
            "http_error": http_error,
            "sdk_error": sdk_error,
        }

    @staticmethod
    def _cache_lookback(start: str, end: str) -> int:
        """Convert a requested calendar range to the cache provider lookback."""
        start_date = normalize_date(start)
        end_date = normalize_date(end)
        if not start_date or not end_date:
            return 1
        try:
            span = (
                datetime.strptime(end_date, "%Y%m%d")
                - datetime.strptime(start_date, "%Y%m%d")
            ).days
        except ValueError:
            return 1
        return max(1, math.ceil(max(0, span) / 2))

    def _get_local_cache_bars(
        self,
        code: str,
        start: str,
        end: str,
        frequency: str,
        fq: str | None,
    ) -> list[dict[str, Any]]:
        """Read only a date-complete daily cache; never use stale bars."""
        if frequency not in {"1d", "day", "daily"} or fq not in {"qfq", None}:
            return []
        start_date = normalize_date(start)
        end_date = normalize_date(end)
        if not start_date or not end_date:
            return []

        result = get_stock_bars_for_factor(
            code,
            end_date,
            lookback=self._cache_lookback(start, end),
            source="cache",
            cache_dir=self.cache_dir,
        )
        if result.get("status") != "ok":
            return []

        bars = []
        for raw_bar in result.get("bars", []):
            if not isinstance(raw_bar, dict):
                continue
            bar = dict(raw_bar)
            bar_date = normalize_date(bar.get("date"))
            if bar_date and start_date <= bar_date <= end_date:
                bar["date"] = f"{bar_date[:4]}-{bar_date[4:6]}-{bar_date[6:8]}"
                bars.append(bar)
        return bars

    def _mark_local_cache_used(self, bars: list[dict[str, Any]]) -> None:
        dates = [normalize_date(bar.get("date")) for bar in bars]
        dates = [date for date in dates if date]
        self.selection = {
            **self.selection,
            "source": "local-cache",
            "reason": "local_cache_fallback",
            "cache_dir": str(self.cache_dir),
            "cache_latest_daily_date": max(dates) if dates else None,
        }

    def get_stock_bars(
        self,
        code: str,
        start: str,
        end: str,
        frequency: str = "1d",
        fq: str | None = "qfq",
    ) -> list[dict[str, Any]]:
        source = self.selection["source"]
        if source != "unavailable":
            client = self.sdk_client if source == "stockdb-sdk" else self.http_client
            try:
                bars = client.get_stock_bars(
                    code, start, end, frequency=frequency, fq=fq
                )
                if bars:
                    return bars
            except Exception:
                pass

        # Keep the research chain usable when external services are down, but
        # only with a cache that contains the requested as-of date.
        cached = self._get_local_cache_bars(code, start, end, frequency, fq)
        if cached:
            self._mark_local_cache_used(cached)
            return cached
        return []
