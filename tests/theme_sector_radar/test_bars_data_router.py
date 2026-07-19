import logging

import theme_sector_radar.data.bars_data_router as bars_router
from theme_sector_radar.data.bars_data_router import AutoBarsClient, extract_latest_daily_date


class FakeHttp:
    def __init__(self, latest="20260708", bars=None, error=None):
        self.latest = latest
        self.bars = bars or [{"date": "20260708", "close": 10.0, "source": "http"}]
        self.error = error

    def health_check(self):
        if self.error:
            raise ConnectionError(self.error)
        return {"stockdb": {"latest_daily_date": self.latest}}

    def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
        return self.bars


class FakeSdk:
    def __init__(self, latest="20260708", bars=None, error=None):
        self.latest = latest
        self.bars = bars or [{"date": "20260708", "close": 11.0, "source": "sdk"}]
        self.error = error

    def get_latest_daily_date(self):
        if self.error:
            raise ConnectionError(self.error)
        return self.latest

    def get_stock_bars(self, code, start, end, frequency="1d", fq="qfq"):
        return self.bars


def test_extract_latest_daily_date_supports_nested_stockdb_payload():
    assert extract_latest_daily_date({"stockdb": {"latest_daily_date": "2026-07-08"}}) == "20260708"


def test_auto_bars_client_uses_http_when_http_is_fresh():
    client = AutoBarsClient(
        http_client=FakeHttp(latest="20260708"),
        sdk_client=FakeSdk(latest="20260708"),
        expected_min_date="2026-07-08",
    )

    assert client.selection["source"] == "http"
    assert client.get_stock_bars("600001", "20260708", "20260709")[0]["source"] == "http"


def test_auto_bars_client_uses_sdk_when_http_is_older_than_expected():
    client = AutoBarsClient(
        http_client=FakeHttp(latest="20260702"),
        sdk_client=FakeSdk(latest="20260708"),
        expected_min_date="2026-07-08",
    )

    assert client.selection["source"] == "stockdb-sdk"
    assert client.selection["reason"] == "http_older_than_expected"
    assert client.get_stock_bars("600001", "20260708", "20260709")[0]["source"] == "sdk"


def test_auto_bars_client_uses_sdk_when_sdk_is_newer_than_http():
    client = AutoBarsClient(
        http_client=FakeHttp(latest="20260707"),
        sdk_client=FakeSdk(latest="20260708"),
    )

    assert client.selection["source"] == "stockdb-sdk"
    assert client.selection["reason"] == "sdk_newer_than_http"


def test_auto_bars_client_falls_back_to_http_when_sdk_is_unavailable():
    client = AutoBarsClient(
        http_client=FakeHttp(latest="20260708"),
        sdk_client=FakeSdk(error="sdk down"),
        expected_min_date="2026-07-08",
    )

    assert client.selection["source"] == "http"
    assert client.selection["reason"] == "sdk_unavailable_http_fallback"


def test_auto_bars_client_fails_closed_when_both_sources_are_stale():
    client = AutoBarsClient(
        http_client=FakeHttp(latest="20260701"),
        sdk_client=FakeSdk(latest="20260702"),
        expected_min_date="2026-07-16",
    )

    assert client.selection["source"] == "unavailable"
    assert client.selection["reason"] == "no_source_meets_expected_min_date"
    assert client.get_stock_bars("600001", "20260701", "20260716") == []


def test_auto_bars_client_fails_closed_when_http_and_sdk_are_unavailable():
    client = AutoBarsClient(
        http_client=FakeHttp(error="http down"),
        sdk_client=FakeSdk(error="sdk down"),
        expected_min_date="2026-07-08",
    )

    assert client.selection["source"] == "unavailable"
    assert client.selection["reason"] == "no_usable_bars_source"
    assert client.get_stock_bars("600001", "20260701", "20260708") == []


def test_auto_bars_client_suppresses_expected_http_health_warning(caplog):
    class NoisyHttp(FakeHttp):
        def health_check(self):
            logging.getLogger("theme_sector_radar.data.market_data_http_client").warning("connection refused")
            raise ConnectionError("connection refused")

    with caplog.at_level(logging.WARNING):
        client = AutoBarsClient(http_client=NoisyHttp(), sdk_client=FakeSdk(latest="20260708"))

    assert client.selection["source"] == "stockdb-sdk"
    assert "connection refused" not in caplog.text


def test_auto_bars_client_uses_fresh_http_when_sdk_initialization_fails(
    monkeypatch,
):
    def missing_sdk():
        raise ImportError("desktop SDK missing")

    monkeypatch.setattr(bars_router, "StockDBSdkClient", missing_sdk)

    client = AutoBarsClient(
        http_client=FakeHttp(latest="20260716"),
        expected_min_date="2026-07-16",
    )

    assert client.selection["source"] == "http"
    assert client.selection["reason"] == "sdk_unavailable_http_fallback"
    assert client.selection["sdk_error"] == "desktop SDK missing"
    assert client.get_stock_bars("600001", "20260701", "20260716")[0]["source"] == "http"
