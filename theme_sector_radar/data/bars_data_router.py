"""Bars data source router for calibration and backfill jobs."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

from .market_data_http_client import MarketDataHttpClient
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
    """Route stock bar reads to HTTP or local StockDB SDK based on freshness."""

    def __init__(
        self,
        http_client: Any | None = None,
        sdk_client: Any | None = None,
        expected_min_date: str | None = None,
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

    def get_stock_bars(
        self,
        code: str,
        start: str,
        end: str,
        frequency: str = "1d",
        fq: str | None = "qfq",
    ) -> list[dict[str, Any]]:
        if self.selection["source"] == "unavailable":
            return []
        client = self.sdk_client if self.selection["source"] == "stockdb-sdk" else self.http_client
        return client.get_stock_bars(code, start, end, frequency=frequency, fq=fq)
