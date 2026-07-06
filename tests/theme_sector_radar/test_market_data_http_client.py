#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for market_data_http_client.py.

All tests use monkeypatch — no real network required.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.market_data_http_client import (
    MarketDataHttpClient,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRIES,
    _env_base_url,
)


# ============================================================
# Helpers
# ============================================================


def _mock_response(status_code=200, json_data=None):
    """Build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def _patch_session_request(client, return_value):
    """Patch the internal session.request method."""
    return patch.object(client._session, "request", return_value=return_value)


# ============================================================
# Tests: config / defaults
# ============================================================


class TestConfig:
    def test_default_base_url(self):
        client = MarketDataHttpClient()
        assert client.base_url == DEFAULT_BASE_URL

    def test_custom_base_url(self):
        client = MarketDataHttpClient(base_url="http://192.168.1.100:9000")
        assert client.base_url == "http://192.168.1.100:9000"

    def test_env_var_override(self):
        old = os.environ.get("MARKET_DATA_SERVICE_URL")
        os.environ["MARKET_DATA_SERVICE_URL"] = "http://myhost:9999"
        try:
            client = MarketDataHttpClient()
            assert client.base_url == "http://myhost:9999"
        finally:
            if old is not None:
                os.environ["MARKET_DATA_SERVICE_URL"] = old
            else:
                os.environ.pop("MARKET_DATA_SERVICE_URL", None)

    def test_default_timeout(self):
        client = MarketDataHttpClient()
        assert client.timeout == DEFAULT_TIMEOUT

    def test_custom_timeout_and_retries(self):
        client = MarketDataHttpClient(timeout=5, retries=0)
        assert client.timeout == 5

    def test_trailing_slash_stripped(self):
        client = MarketDataHttpClient(base_url="http://127.0.0.1:8000/")
        assert client.base_url == "http://127.0.0.1:8000"

    def test_env_base_url_function(self):
        old = os.environ.get("MARKET_DATA_SERVICE_URL")
        if "MARKET_DATA_SERVICE_URL" in os.environ:
            del os.environ["MARKET_DATA_SERVICE_URL"]
        try:
            assert _env_base_url() == DEFAULT_BASE_URL
        finally:
            if old is not None:
                os.environ["MARKET_DATA_SERVICE_URL"] = old


# ============================================================
# Tests: health_check
# ============================================================


class TestHealthCheck:
    def test_success(self):
        client = MarketDataHttpClient()
        expected = {"stockdb": "ok", "akshare_ths": "ok"}
        with _patch_session_request(client, _mock_response(200, expected)):
            result = client.health_check()
            assert result == expected

    def test_503(self):
        client = MarketDataHttpClient()
        with _patch_session_request(
            client,
            _mock_response(503, {"error": {"type": "ConnectionError", "message": "downstream unavailable"}}),
        ):
            with pytest.raises(ConnectionError, match="downstream unavailable"):
                client.health_check()


# ============================================================
# Tests: get_stock_bars
# ============================================================


class TestGetStockBars:
    SAMPLE_BARS = [
        {
            "code": "600633",
            "date": "2026-07-01",
            "open": 21.50,
            "high": 22.10,
            "low": 21.30,
            "close": 21.80,
            "volume": 5000000.0,
            "amount": 108500000.0,
        },
        {
            "code": "600633",
            "date": "2026-07-02",
            "open": 21.80,
            "high": 22.50,
            "low": 21.60,
            "close": 22.30,
            "volume": 6200000.0,
            "amount": 136500000.0,
        },
    ]

    def test_success_default_params(self):
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, self.SAMPLE_BARS)):
            result = client.get_stock_bars("600633", "20260701", "20260702")
            assert len(result) == 2
            assert result[0]["code"] == "600633"
            assert result[0]["close"] == 21.80

    def test_success_with_frequency(self):
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, [])) as mock_req:
            client.get_stock_bars("600633", "20260701", "20260702", frequency="1w")
            call_args = mock_req.call_args
            params = call_args.kwargs.get("params", {})
            assert params.get("frequency") == "1w"

    def test_fq_none(self):
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, [])) as mock_req:
            client.get_stock_bars("600633", "20260701", "20260702", fq=None)
            call_args = mock_req.call_args
            params = call_args.kwargs.get("params", {})
            assert "fq" not in params

    def test_400_value_error(self):
        client = MarketDataHttpClient()
        with _patch_session_request(
            client,
            _mock_response(400, {"error": {"type": "ValueError", "message": "invalid frequency: xyz"}}),
        ):
            with pytest.raises(ValueError, match="invalid frequency"):
                client.get_stock_bars("600633", "20260701", "20260702", frequency="xyz")


# ============================================================
# Tests: get_board_constituents
# ============================================================


class TestGetBoardConstituents:
    SAMPLE_CONSTITUENTS = [
        {"code": "688981", "name": "中芯国际", "market_cap": 500000000000.0},
        {"code": "002371", "name": "北方华创", "market_cap": 300000000000.0},
        {"code": "603501", "name": "韦尔股份", "market_cap": 250000000000.0},
    ]

    def test_success_industry(self):
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, self.SAMPLE_CONSTITUENTS)):
            result = client.get_board_constituents("半导体", board_type="industry")
            assert len(result) == 3
            assert result[0]["code"] == "688981"
            assert result[1]["name"] == "北方华创"

    def test_success_concept(self):
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, self.SAMPLE_CONSTITUENTS)):
            result = client.get_board_constituents("人工智能", board_type="concept")
            assert len(result) == 3

    def test_503_connection_error(self):
        """constituents 503 should map to ConnectionError."""
        client = MarketDataHttpClient()
        with _patch_session_request(
            client,
            _mock_response(503, {"error": {"type": "BoardConstituentsUnavailableError", "message": "EM unavailable"}}),
        ):
            with pytest.raises(ConnectionError, match="EM unavailable"):
                client.get_board_constituents("半导体")

    def test_board_type_in_path(self):
        """Verify board_type and name are embedded in the URL path (Phase 21: encoded)."""
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, [])) as mock_req:
            client.get_board_constituents("白酒", board_type="industry")
            url = mock_req.call_args.kwargs.get("url", "")
            assert "/boards/industry/" in url
            # Chinese chars are percent-encoded
            assert "%E9%85%92" in url  # 酒 = %E9%85%92
            assert "/constituents" in url


# ============================================================
# Tests: get_board_index
# ============================================================


class TestGetBoardIndex:
    def test_success(self):
        client = MarketDataHttpClient()
        bars = [{"date": "2026-07-01", "open": 1000.0, "close": 1020.0}]
        with _patch_session_request(client, _mock_response(200, bars)):
            result = client.get_board_index("半导体", "industry", "20260701", "20260702")
            assert len(result) == 1
            assert result[0]["close"] == 1020.0

    def test_passes_params(self):
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, [])) as mock_req:
            client.get_board_index("半导体", "industry", "20260701", "20260702")
            params = mock_req.call_args.kwargs.get("params", {})
            assert params["start"] == "20260701"
            assert params["end"] == "20260702"


# ============================================================
# Tests: get_industry_summary
# ============================================================


class TestGetIndustrySummary:
    def test_success(self):
        client = MarketDataHttpClient()
        summary = [
            {"name": "半导体", "pct_chg": 3.5, "amount": 1.2e11, "net_inflow": 5.0e9},
            {"name": "证券", "pct_chg": -1.2, "amount": 8.0e10, "net_inflow": -2.0e9},
        ]
        with _patch_session_request(client, _mock_response(200, summary)):
            result = client.get_industry_summary()
            assert len(result) == 2
            assert result[0]["name"] == "半导体"

    def test_empty(self):
        client = MarketDataHttpClient()
        with _patch_session_request(client, _mock_response(200, [])):
            result = client.get_industry_summary()
            assert result == []


# ============================================================
# Tests: error / retry behaviour
# ============================================================


class TestErrorAndRetry:
    def test_timeout_raises_timeout_error(self):
        client = MarketDataHttpClient(timeout=1, retries=0)
        with patch.object(
            client._session,
            "request",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with pytest.raises(TimeoutError):
                client.health_check()

    def test_connection_refused_raises_connection_error(self):
        client = MarketDataHttpClient(retries=0)
        with patch.object(
            client._session,
            "request",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(ConnectionError, match="connection refused"):
                client.health_check()

    def test_500_raises_runtime_error(self):
        client = MarketDataHttpClient(retries=0)
        with _patch_session_request(
            client,
            _mock_response(500, {"error": {"type": "RuntimeError", "message": "internal error"}}),
        ):
            with pytest.raises(RuntimeError, match="internal error"):
                client.health_check()

    def test_no_error_body_falls_back_to_status_text(self):
        client = MarketDataHttpClient(retries=0)
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 503
        resp.json.side_effect = ValueError("not json")
        with patch.object(client._session, "request", return_value=resp):
            with pytest.raises(ConnectionError, match="returned 503"):
                client.health_check()

    def test_close(self):
        client = MarketDataHttpClient()
        client._session.close = MagicMock()
        client.close()
        client._session.close.assert_called_once()
