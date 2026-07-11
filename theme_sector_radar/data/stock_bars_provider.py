"""
Stock Bars Provider 模块

提供统一的 bars 获取逻辑，供 backfill 和 factor snapshot 复用。
支持 cache -> http -> stockdb-sdk 的 fallback 链路。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_date(value: Any) -> str | None:
    """标准化日期为 YYYY-MM-DD 格式。"""
    if value is None:
        return None

    # 处理 int 类型（如 20260710）
    if isinstance(value, (int, float)):
        value = str(int(value))

    value = str(value).strip()

    # 处理 YYYYMMDD 格式
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    # 处理 YYYY-MM-DD 格式
    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        return value

    return None


def _normalize_bar(bar: dict) -> dict | None:
    """标准化 bar 字段。"""
    if not isinstance(bar, dict):
        return None

    # 标准化字段名
    field_mapping = {
        "date": ["date", "trade_date", "交易日期"],
        "open": ["open", "开盘", "开盘价"],
        "high": ["high", "最高", "最高价"],
        "low": ["low", "最低", "最低价"],
        "close": ["close", "收盘", "收盘价"],
        "volume": ["volume", "成交量"],
        "amount": ["amount", "成交额"],
    }

    normalized = {}
    for std_name, aliases in field_mapping.items():
        for alias in aliases:
            if alias in bar:
                normalized[std_name] = bar[alias]
                break

    # 标准化日期
    if "date" in normalized:
        normalized["date"] = _normalize_date(normalized["date"])

    # 确保数值字段存在
    for field in ["open", "high", "low", "close", "volume", "amount"]:
        if field not in normalized:
            normalized[field] = None

    return normalized


def _sort_bars_old_to_new(bars: list[dict]) -> list[dict]:
    """排序 bars 为旧到新。"""
    def get_date(bar: dict) -> str:
        return bar.get("date", "")

    return sorted(bars, key=get_date)


# ============================================================
# Cache Operations
# ============================================================

def _get_cache_path(code: str, cache_dir: Path) -> Path:
    """获取 cache 文件路径。"""
    return cache_dir / f"{code}.json"


def _read_cache(cache_path: Path) -> dict | None:
    """读取 cache。"""
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(cache_path: Path, data: dict) -> None:
    """写入 cache。"""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cache_covers_date_range(cache_data: dict, as_of: str, lookback: int) -> bool:
    """检查 cache 是否覆盖所需日期范围。"""
    bars = cache_data.get("bars", [])
    if not bars:
        return False

    # 获取 cache 中的日期范围
    dates = []
    for bar in bars:
        date = bar.get("date")
        if date:
            normalized = _normalize_date(date)
            if normalized:
                dates.append(normalized)

    if not dates:
        return False

    min_date = min(dates)
    max_date = max(dates)

    # 检查是否覆盖 as_of 前 lookback 天
    as_of_date = _normalize_date(as_of)
    if not as_of_date:
        return False

    # 计算所需的最早日期
    try:
        as_of_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
        required_min_date = (as_of_dt - timedelta(days=lookback * 2)).strftime("%Y-%m-%d")  # 乘以2考虑非交易日
    except Exception:
        return False

    return min_date <= required_min_date and max_date >= as_of_date


# ============================================================
# HTTP Provider
# ============================================================

def _fetch_bars_http(code: str, start: str, end: str) -> list[dict] | None:
    """通过 HTTP 获取 bars。"""
    try:
        from theme_sector_radar.data.market_data_http_client import MarketDataHttpClient
        client = MarketDataHttpClient()
        bars = client.get_stock_bars(code, start, end, frequency="1d", fq="qfq")
        return bars
    except Exception:
        return None


def _fetch_bars_stockdb_sdk(code: str, start: str, end: str) -> list[dict] | None:
    """通过 StockDB SDK 获取 bars。"""
    try:
        from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient
        client = StockDBSdkClient()
        bars = client.get_stock_bars(code, start, end, frequency="1d", fq="qfq")
        return bars
    except Exception:
        return None


# ============================================================
# Main Provider Function
# ============================================================

def get_stock_bars_for_factor(
    code: str,
    as_of: str,
    lookback: int = 80,
    source: str = "auto",
    cache_dir: str | Path | None = None,
) -> dict:
    """获取股票 bars 数据。

    Args:
        code: 股票代码
        as_of: 日期 (YYYY-MM-DD)
        lookback: 回溯天数
        source: 数据源 (auto/http/stockdb-sdk)
        cache_dir: cache 目录

    Returns:
        dict with code, as_of, source, status, bars, missing_reason
    """
    result = {
        "code": code,
        "as_of": as_of,
        "source": "missing",
        "status": "missing",
        "bars": [],
        "missing_reason": "",
    }

    # 标准化 code
    normalized_code = _normalize_date(code) if isinstance(code, (int, float)) else _normalize_date(code)
    if normalized_code:
        code_for_query = normalized_code
    else:
        code_for_query = code

    # 标准化日期
    as_of_normalized = _normalize_date(as_of)
    if not as_of_normalized:
        result["missing_reason"] = "invalid_as_of_date"
        return result

    # 设置 cache 目录
    if cache_dir is None:
        cache_dir = Path("data_cache") / "stock_bars"
    elif isinstance(cache_dir, str):
        cache_dir = Path(cache_dir)
    cache_path = _get_cache_path(code_for_query, cache_dir)

    # 记录每个 source 的失败原因
    missing_reasons = []

    # 尝试从 cache 获取
    if source in ("auto", "cache"):
        cache_data = _read_cache(cache_path)
        if cache_data and _cache_covers_date_range(cache_data, as_of_normalized, lookback):
            bars = cache_data.get("bars", [])
            if bars:
                result["source"] = "cache"
                result["status"] = "ok"
                result["bars"] = _sort_bars_old_to_new(bars)
                return result
        else:
            missing_reasons.append("cache:not_found_or_insufficient")

    # 尝试从 HTTP 获取
    if source in ("auto", "http"):
        try:
            # 计算日期范围
            as_of_dt = datetime.strptime(as_of_normalized, "%Y-%m-%d")
            start_date = (as_of_dt - timedelta(days=lookback * 2)).strftime("%Y%m%d")
            end_date = as_of_dt.strftime("%Y%m%d")

            bars = _fetch_bars_http(code_for_query, start_date, end_date)
            if bars and len(bars) > 0:
                # 标准化 bars
                normalized_bars = [_normalize_bar(b) for b in bars if _normalize_bar(b) is not None]
                if normalized_bars:
                    # 写入 cache
                    cache_data = {
                        "code": code_for_query,
                        "updated_at": datetime.now().isoformat(),
                        "source": "http",
                        "bars": normalized_bars,
                    }
                    _write_cache(cache_path, cache_data)

                    result["source"] = "http"
                    result["status"] = "ok"
                    result["bars"] = _sort_bars_old_to_new(normalized_bars)
                    return result
                else:
                    missing_reasons.append("http:bars_normalization_failed")
            else:
                missing_reasons.append("http:no_bars_returned")
        except Exception as e:
            missing_reasons.append(f"http:{str(e)[:50]}")

    # 尝试从 StockDB SDK 获取
    if source in ("auto", "stockdb-sdk"):
        try:
            as_of_dt = datetime.strptime(as_of_normalized, "%Y-%m-%d")
            start_date = (as_of_dt - timedelta(days=lookback * 2)).strftime("%Y%m%d")
            end_date = as_of_dt.strftime("%Y%m%d")

            bars = _fetch_bars_stockdb_sdk(code_for_query, start_date, end_date)
            if bars and len(bars) > 0:
                normalized_bars = [_normalize_bar(b) for b in bars if _normalize_bar(b) is not None]
                if normalized_bars:
                    cache_data = {
                        "code": code_for_query,
                        "updated_at": datetime.now().isoformat(),
                        "source": "stockdb-sdk",
                        "bars": normalized_bars,
                    }
                    _write_cache(cache_path, cache_data)

                    result["source"] = "stockdb-sdk"
                    result["status"] = "ok"
                    result["bars"] = _sort_bars_old_to_new(normalized_bars)
                    return result
                else:
                    missing_reasons.append("stockdb-sdk:bars_normalization_failed")
            else:
                missing_reasons.append("stockdb-sdk:no_bars_returned")
        except ImportError as e:
            missing_reasons.append(f"stockdb-sdk:import_error:{str(e)[:50]}")
        except Exception as e:
            missing_reasons.append(f"stockdb-sdk:{str(e)[:50]}")

    # 汇总 missing_reason
    result["missing_reason"] = "; ".join(missing_reasons) if missing_reasons else "no_data_source_available"
    return result
