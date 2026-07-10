"""
HTTP client adapter for market_data_service.

Thin wrapper around ``requests`` — every method calls a market_data_service
HTTP API endpoint and returns parsed JSON.  Failures are mapped to well-known
exception types so callers can catch and fall back gracefully.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 60  # seconds (batch requests need more time)
DEFAULT_RETRIES = 2


def _env_base_url() -> str:
    return os.environ.get("MARKET_DATA_SERVICE_URL", DEFAULT_BASE_URL)


def _encode_path(path: str) -> str:
    """Percent-encode non-ASCII characters in a URL path.

    ``requests`` does not encode path segments, so Chinese characters in
    board names must be encoded manually.
    """
    return quote(path, safe="/?=&")


# ---------------------------------------------------------------------------
# Public client
# ---------------------------------------------------------------------------


class MarketDataHttpClient:
    """HTTP client for ``market_data_service``.

    Parameters
    ----------
    base_url : str | None
        Root URL of the market_data_service API.  Defaults to
        ``MARKET_DATA_SERVICE_URL`` env var or ``http://127.0.0.1:8000``.
    timeout : int
        Request timeout in seconds (default 10).
    retries : int
        Number of retries on transient failures (default 2).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ):
        self.base_url = (base_url or _env_base_url()).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

        # Retry on 5xx / connection errors with backoff
        if retries > 0:
            adapter = HTTPAdapter(
                max_retries=Retry(
                    total=retries,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504],
                    allowed_methods=["GET"],
                )
            )
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Issue an HTTP request and return the parsed JSON body.

        Raises
        ------
        ConnectionError
            On 503, connection-refused, or timeout.
        ValueError
            On 4xx client errors.
        RuntimeError
            On unexpected 5xx (non-503).
        """
        url = self.base_url + _encode_path(path)
        start = time.monotonic()

        try:
            resp = self._session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout,
            )
            elapsed = time.monotonic() - start
            logger.debug("HTTP %s %s → %d (%.2fs)", method, url, resp.status_code, elapsed)

            if resp.status_code == 200:
                return resp.json()

            # Structured error from market_data_service?
            error_msg = f"{method} {path} returned {resp.status_code}"
            try:
                body = resp.json()
                err = body.get("error", {})
                if isinstance(err, dict):
                    error_msg = err.get("message", error_msg)
            except Exception:
                pass

            if resp.status_code == 503:
                raise ConnectionError(error_msg)
            elif 400 <= resp.status_code < 500:
                raise ValueError(error_msg)
            else:
                raise RuntimeError(error_msg)

        except (ConnectionError, ValueError, RuntimeError):
            raise  # re-raise our own mapped exceptions
        except requests.exceptions.Timeout:
            elapsed = time.monotonic() - start
            logger.warning("HTTP %s %s timed out after %.2fs", method, url, elapsed)
            raise TimeoutError(f"{method} {path} timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as exc:
            logger.warning("HTTP %s %s connection failed: %s", method, url, exc)
            raise ConnectionError(f"{method} {path}: connection refused") from exc
        except requests.exceptions.RequestException as exc:
            logger.warning("HTTP %s %s request error: %s", method, url, exc)
            raise RuntimeError(f"{method} {path}: {exc}") from exc

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """Call ``GET /health``.

        Returns the health status dict, e.g.
        ``{"stockdb": "ok", "akshare_ths": "ok", ...}``.
        """
        return self._request("GET", "/health")

    def get_stock_bars(
        self,
        code: str,
        start: str,
        end: str,
        frequency: str = "1d",
        fq: Optional[str] = "qfq",
    ) -> List[Dict[str, Any]]:
        """Call ``GET /stocks/{code}/bars``.

        Parameters
        ----------
        code : str
            Stock code, e.g. ``"600633"``.
        start : str
            Start date ``YYYYMMDD`` (or ``YYYYMMDDHHMMSS`` for minute bars).
        end : str
            End date.
        frequency : str
            ``"1d"``, ``"1w"``, ``"1M"``, ``"1m"``, ``"5m"``, etc.
        fq : str | None
            Rehab adjustment: ``"qfq"`` (front), ``"hfq"`` (back), ``None``.

        Returns
        -------
        list[dict]
            List of bar dicts.  Each bar contains at minimum ``code``,
            ``date``, ``open``, ``high``, ``low``, ``close``, ``volume``,
            ``amount``.
        """
        params: Dict[str, Any] = {
            "start": start,
            "end": end,
            "frequency": frequency,
        }
        if fq is not None:
            params["fq"] = fq
        return self._request("GET", f"/stocks/{code}/bars", params=params)

    def get_board_constituents(
        self,
        name: str,
        board_type: str = "industry",
        as_of: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Call ``GET /boards/{board_type}/{name}/constituents``.

        Returns a list of ``StockInfo``-like dicts with ``code``, ``name``,
        and possibly ``market_cap``, ``weight``, etc.
        """
        params = {}
        if as_of is not None:
            params["as_of"] = as_of
        return self._request(
            "GET",
            f"/boards/{board_type}/{name}/constituents",
            params=params if params else None,
        )

    def get_board_index(
        self,
        name: str,
        board_type: str,
        start: str,
        end: str,
    ) -> List[Dict[str, Any]]:
        """Call ``GET /boards/{board_type}/{name}/index``.

        Returns a list of ``BoardIndexBar``-like dicts.
        """
        return self._request(
            "GET",
            f"/boards/{board_type}/{name}/index",
            params={"start": start, "end": end},
        )

    def get_industry_summary(self) -> List[Dict[str, Any]]:
        """Call ``GET /boards/industry-summary``.

        Returns a list of ``BoardSummary``-like dicts with fields such as
        ``name``, ``pct_chg``, ``amount``, ``net_inflow``, etc.
        """
        return self._request("GET", "/boards/industry-summary")

    # ------------------------------------------------------------------
    # Phase 15: security master + fund flow
    # ------------------------------------------------------------------

    def get_stock_info(self, code: str) -> Optional[Dict[str, Any]]:
        """Call ``GET /stocks/{code}/info``.

        Returns stock basic info (code, name, exchange, market, is_st)
        or ``None`` on 404.
        """
        try:
            return self._request("GET", f"/stocks/{code}/info")
        except ValueError:  # 404 → stock not found
            return None

    def get_stock_info_batch(self, codes: List[str]) -> Optional[Dict[str, Any]]:
        """Call ``POST /stocks/info/batch``.

        Returns ``{"items": {code: {...}, ...}, "missing": [...], "source": "security_master"}``
        or ``None`` on failure.
        """
        if not codes:
            return {"items": {}, "missing": [], "source": "security_master"}
        unique = list({c.strip() for c in codes if c.strip()})
        if not unique:
            return {"items": {}, "missing": [], "source": "security_master"}
        # Split into chunks of 500 (API max_length)
        all_items = {}
        all_missing = []
        for i in range(0, len(unique), 500):
            chunk = unique[i : i + 500]
            try:
                import json as _json
                url = f"{self.base_url}/stocks/info/batch"
                resp = self._session.post(url, json={"codes": chunk}, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get("items"):
                        all_items.update(data["items"])
                    if data and data.get("missing"):
                        all_missing.extend(data["missing"])
                else:
                    logger.warning("Batch stock info returned %d for %d codes", resp.status_code, len(chunk))
            except Exception as exc:
                logger.warning("Batch stock info failed: %s", exc)
        return {"items": all_items, "missing": all_missing, "source": "security_master"}

    def get_stock_fund_flow(self, code: str) -> Optional[Dict[str, Any]]:
        """Call ``GET /stocks/{code}/fund-flow``.

        Returns fund flow data (main_net_inflow, pct_chg, etc.)
        or a dict with ``available=False`` when no data.
        """
        try:
            return self._request("GET", f"/stocks/{code}/fund-flow")
        except (ConnectionError, TimeoutError, ValueError, RuntimeError):
            return None

    def get_stock_fund_flow_batch(self, codes: List[str]) -> Optional[Dict[str, Any]]:
        """Call ``POST /stocks/fund-flow/batch``.

        Returns ``{"items": {code: {...}, ...}, "missing": [...], "source": "fund_flow_ths"}``
        or ``None`` on failure.
        """
        if not codes:
            return {"items": {}, "missing": [], "source": "fund_flow_neutral"}
        unique = list({c.strip() for c in codes if c.strip()})
        if not unique:
            return {"items": {}, "missing": [], "source": "fund_flow_neutral"}
        # Split into chunks of 500 (API max_length)
        all_items = {}
        all_missing = []
        for i in range(0, len(unique), 500):
            chunk = unique[i : i + 500]
            try:
                import json as _json
                url = f"{self.base_url}/stocks/fund-flow/batch"
                resp = self._session.post(
                    url,
                    json={"codes": chunk},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get("items"):
                        all_items.update(data["items"])
                    if data and data.get("missing"):
                        all_missing.extend(data["missing"])
                else:
                    logger.warning("Batch fund flow returned %d for %d codes", resp.status_code, len(chunk))
            except Exception as exc:
                logger.warning("Batch fund flow failed: %s", exc)
        return {"items": all_items, "missing": all_missing, "source": "fund_flow_ths"}

    def close(self):
        """Close the underlying session."""
        self._session.close()
