#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Forward Return 构建脚本

为 top30_candidates.json 中的候选股构建 forward returns，
使 evaluate_factor_composite_shadow_score.py 能真正计算 Rank IC。

本阶段只生成 forward return 数据和评估报告，不改变生产排序逻辑。

用法:
  python scripts/build_factor_forward_returns.py --start 2026-07-01 --end 2026-07-10 --prefer-backfilled
  python scripts/build_factor_forward_returns.py --start 2026-07-01 --end 2026-07-10 --force
  python scripts/build_factor_forward_returns.py --start 2026-07-01 --end 2026-07-10 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def normalize_code(code: str) -> str:
    """标准化股票代码格式。

    支持格式:
    - 600001
    - sh600001
    - 600001.SH
    - SZ000001
    - 000001.SZ
    """
    code = code.strip().upper()

    # 去除前缀
    if code.startswith("SH"):
        code = code[2:]
    elif code.startswith("SZ"):
        code = code[2:]

    # 去除后缀
    if "." in code:
        code = code.split(".")[0]

    return code


def make_bars_client(source: str = "auto", expected_min_date: str | None = None):
    """创建 bars 数据客户端。"""
    if source == "stockdb-sdk":
        from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient
        return StockDBSdkClient()
    if source == "auto":
        from theme_sector_radar.data.bars_data_router import AutoBarsClient
        return AutoBarsClient(expected_min_date=expected_min_date)
    if source == "http":
        from theme_sector_radar.data.market_data_http_client import MarketDataHttpClient
        return MarketDataHttpClient()
    raise ValueError(f"unsupported source: {source}")


# ============================================================
# Data Loading
# ============================================================

def _parse_date(value: str) -> datetime:
    """解析日期字符串。"""
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value[:10] if fmt == "%Y-%m-%d" else value[:8], fmt)
        except ValueError:
            continue
    raise ValueError(f"unsupported date: {value}")


def _date_key(value: Any) -> str:
    """转换为 YYYY-MM-DD 格式。"""
    if value is None:
        return ""
    # 处理整数类型（如 20260710）
    if isinstance(value, (int, float)):
        value = str(int(value))
    return _parse_date(value).strftime("%Y-%m-%d")


def _service_date(value: datetime) -> str:
    """转换为 YYYYMMDD 格式。"""
    return value.strftime("%Y%m%d")


def _coerce_float(value: Any) -> float | None:
    """安全转换为 float。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_candidates(date: str, candidate_root: Path, prefer_backfilled: bool = True) -> list[dict] | None:
    """加载候选股列表。

    优先使用 factor_backfilled 文件，回退到原文件。
    """
    if prefer_backfilled:
        backfilled_path = candidate_root / date / "top30_candidates.factor_backfilled.json"
        if backfilled_path.exists():
            try:
                data = json.loads(backfilled_path.read_text(encoding="utf-8"))
                return data.get("candidates", [])
            except Exception:
                pass

    original_path = candidate_root / date / "top30_candidates.json"
    if original_path.exists():
        try:
            data = json.loads(original_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            return None

    return None


def find_cached_bars(code: str, date: str, cache_root: Path) -> list[dict] | None:
    """查找已缓存的 bars 数据。"""
    # 尝试不同的缓存路径格式
    patterns = [
        cache_root / code / f"{date}.json",
        cache_root / f"{code}_{date}.json",
        cache_root / date / f"{code}.json",
    ]
    for path in patterns:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


# ============================================================
# Forward Return Computation
# ============================================================

def compute_forward_returns_from_bars(
    bars: list[dict],
    as_of: str,
    horizons: Iterable[int] = (1, 3, 5, 10),
) -> dict[str, float | None]:
    """从 bars 数据计算 forward returns。"""
    # 过滤出有效的 bar 数据
    valid_bars = []
    for bar in bars:
        if not isinstance(bar, dict):
            continue
        date_val = bar.get("date")
        close_val = bar.get("close")
        if date_val and close_val is not None:
            parsed_date = _date_key(date_val)
            parsed_close = _coerce_float(close_val)
            if parsed_date and parsed_close is not None:
                valid_bars.append({"date": parsed_date, "close": parsed_close})

    if not valid_bars:
        return {f"{horizon}d": None for horizon in horizons}

    ordered = sorted(valid_bars, key=lambda item: item["date"])
    as_of_key = _date_key(as_of)
    signal_idx = next((idx for idx, bar in enumerate(ordered) if bar["date"] == as_of_key), None)

    result = {f"{horizon}d": None for horizon in horizons}
    if signal_idx is None:
        return result

    base_close = ordered[signal_idx]["close"]
    if not base_close or base_close <= 0:
        return result

    for horizon in horizons:
        target_idx = signal_idx + int(horizon)
        if target_idx >= len(ordered):
            result[f"{horizon}d"] = None
            continue
        target_close = ordered[target_idx]["close"]
        if target_close is None:
            result[f"{horizon}d"] = None
        else:
            result[f"{horizon}d"] = round((target_close - base_close) / base_close * 100, 4)
    return result


def compute_forward_returns_from_candidate(
    candidate: dict,
    as_of: str,
    bars: list[dict] | None,
    horizons: Iterable[int] = (1, 3, 5, 10),
) -> dict:
    """为单个候选股计算 forward returns。"""
    code = candidate.get("code", "")
    name = candidate.get("name", "")
    close_t = None

    # 尝试从 bars 获取 as_of 日的收盘价
    if bars:
        for bar in bars:
            bar_date = _date_key(bar.get("date", ""))
            if bar_date == _date_key(as_of):
                close_t = _coerce_float(bar.get("close"))
                break

    # 计算 forward returns
    forward_returns = compute_forward_returns_from_bars(bars or [], as_of, horizons)

    # 确定 data quality
    has_any_return = any(v is not None for v in forward_returns.values())
    if bars is None:
        data_quality = "missing"
        missing_reason = "bars_not_available"
    elif len(bars) == 0:
        data_quality = "missing"
        missing_reason = "bars_empty"
    elif not has_any_return:
        data_quality = "partial"
        missing_reason = "no_valid_forward_return"
    else:
        data_quality = "ok"
        missing_reason = ""

    # 构建 close values
    close_values = {}
    if bars:
        ordered = sorted(
            [{"date": _date_key(b.get("date", "")), "close": _coerce_float(b.get("close"))}
             for b in bars if b.get("date") and _coerce_float(b.get("close")) is not None],
            key=lambda x: x["date"],
        )
        as_of_idx = next((i for i, b in enumerate(ordered) if b["date"] == _date_key(as_of)), None)
        if as_of_idx is not None:
            for horizon in horizons:
                target_idx = as_of_idx + int(horizon)
                if target_idx < len(ordered):
                    close_values[f"close_{horizon}d"] = ordered[target_idx]["close"]

    result = {
        "code": code,
        "name": name,
        "as_of": as_of,
        "close_t": close_t,
    }
    result.update(close_values)
    result.update(forward_returns)
    result["data_quality"] = data_quality
    result["missing_reason"] = missing_reason

    return result


def fetch_bars_for_candidate(
    candidate: dict,
    as_of: str,
    client=None,
    lookahead_days: int = 14,
) -> tuple[list[dict] | None, dict]:
    """为单个候选股获取 bars 数据。

    Returns:
        (bars, metadata) where metadata contains source info
    """
    code = candidate.get("code", "")
    normalized = normalize_code(code)

    metadata = {
        "bars_source": "none",
        "bars_count": 0,
        "bars_start": None,
        "bars_end": None,
        "normalized_code": normalized,
    }

    if client is None:
        metadata["bars_source"] = "no_client"
        return None, metadata

    try:
        # 计算日期范围
        signal_date = _parse_date(as_of)
        # 往前看7天确保有 as_of 日，往后看 lookahead_days 天确保有未来数据
        # 注意：lookahead_days 是自然日，需要额外加一些天数来覆盖交易日
        start = _service_date(signal_date - timedelta(days=7))
        end = _service_date(signal_date + timedelta(days=lookahead_days + 5))

        # 尝试使用标准化代码
        raw_bars = client.get_stock_bars(normalized, start, end, frequency="1d", fq="qfq")

        # 处理不同的返回格式
        bars = []
        if isinstance(raw_bars, list):
            for item in raw_bars:
                if isinstance(item, dict):
                    bars.append(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 7:
                    # 可能是 [date, code, open, high, low, close, volume, amount, ...]
                    bars.append({
                        "date": str(item[0]) if item[0] else None,
                        "code": str(item[1]) if len(item) > 1 else normalized,
                        "open": _coerce_float(item[2]) if len(item) > 2 else None,
                        "high": _coerce_float(item[3]) if len(item) > 3 else None,
                        "low": _coerce_float(item[4]) if len(item) > 4 else None,
                        "close": _coerce_float(item[5]) if len(item) > 5 else None,
                        "volume": _coerce_float(item[6]) if len(item) > 6 else None,
                        "amount": _coerce_float(item[7]) if len(item) > 7 else None,
                    })
        elif isinstance(raw_bars, dict):
            # 可能是 {"code": [bars]} 格式
            if normalized in raw_bars:
                raw_list = raw_bars[normalized]
                if isinstance(raw_list, list):
                    for item in raw_list:
                        if isinstance(item, dict):
                            bars.append(item)
                        elif isinstance(item, (list, tuple)) and len(item) >= 7:
                            bars.append({
                                "date": str(item[0]) if item[0] else None,
                                "code": normalized,
                                "open": _coerce_float(item[2]) if len(item) > 2 else None,
                                "high": _coerce_float(item[3]) if len(item) > 3 else None,
                                "low": _coerce_float(item[4]) if len(item) > 4 else None,
                                "close": _coerce_float(item[5]) if len(item) > 5 else None,
                                "volume": _coerce_float(item[6]) if len(item) > 6 else None,
                                "amount": _coerce_float(item[7]) if len(item) > 7 else None,
                            })

        if bars and len(bars) > 0:
            metadata["bars_count"] = len(bars)
            # 找到首尾日期
            dates = [_date_key(b.get("date", "")) for b in bars if b.get("date")]
            if dates:
                metadata["bars_start"] = min(dates)
                metadata["bars_end"] = max(dates)
            metadata["bars_source"] = getattr(client, "selection", {}).get("source", "unknown") if hasattr(client, "selection") else "client"
            return bars, metadata
        else:
            metadata["bars_source"] = "empty"
            return [], metadata

    except Exception as e:
        metadata["bars_source"] = f"error: {str(e)[:50]}"
        return None, metadata


# ============================================================
# Main Build Logic
# ============================================================

def build_factor_forward_returns(
    date: str,
    candidate_root: Path,
    output_root: Path,
    horizons: list[int] = [1, 3, 5, 10],
    prefer_backfilled: bool = True,
    dry_run: bool = False,
    force: bool = False,
    client=None,
) -> dict:
    """为单天构建 forward returns。"""
    result = {
        "date": date,
        "status": "unknown",
        "candidate_count": 0,
        "forward_return_count": 0,
        "has_forward_return_file": False,
        "errors": [],
    }

    # 检查是否已存在 forward return 文件
    output_path = output_root / f"{date}.json"
    if output_path.exists() and not force:
        result["status"] = "already_exists"
        result["has_forward_return_file"] = True
        return result

    # 加载候选股
    candidates = load_candidates(date, candidate_root, prefer_backfilled)
    if candidates is None:
        result["status"] = "missing_candidate_file"
        return result
    if not candidates:
        result["status"] = "no_candidates"
        return result

    result["candidate_count"] = len(candidates)

    # 尝试获取 bars 数据
    items = []
    matched_count = 0
    missing_reason_counts = {}

    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")

        # 尝试获取 bars
        bars, bars_meta = fetch_bars_for_candidate(c, date, client)

        # 计算 forward returns
        item = compute_forward_returns_from_candidate(c, date, bars, horizons)

        # 添加 bars 元数据
        item["bars_source"] = bars_meta["bars_source"]
        item["bars_count"] = bars_meta["bars_count"]
        item["bars_start"] = bars_meta["bars_start"]
        item["bars_end"] = bars_meta["bars_end"]

        items.append(item)

        if item["data_quality"] == "ok":
            matched_count += 1
        else:
            reason = item["missing_reason"]
            missing_reason_counts[reason] = missing_reason_counts.get(reason, 0) + 1

    # 构建输出
    output_data = {
        "schema_version": "1.0",
        "as_of": date,
        "source": "factor_forward_return_builder",
        "generated_at": datetime.now().isoformat(),
        "horizons": [f"{h}d" for h in horizons],
        "items": items,
        "summary": {
            "candidate_count": len(candidates),
            "matched_count": matched_count,
            "missing_count": len(candidates) - matched_count,
            "missing_reason_counts": missing_reason_counts,
        },
    }

    result["forward_return_count"] = matched_count

    # 写入文件
    if dry_run:
        result["status"] = "dry_run"
        return result

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result["status"] = "processed"
    except Exception as e:
        result["status"] = f"error: {str(e)}"
        result["errors"].append(str(e))

    return result


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build Factor Forward Returns"
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--candidate-root",
        default=str(PROJECT_ROOT / "reports" / "agent_bridge"),
        help="Root directory for candidate files",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "reports" / "forward_returns"),
        help="Output directory for forward returns",
    )
    parser.add_argument(
        "--horizons",
        default="1,3,5,10",
        help="Comma-separated horizons (days)",
    )
    parser.add_argument("--prefer-backfilled", action="store_true", help="Prefer backfilled candidate files")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing files")
    parser.add_argument("--source", choices=["auto", "http", "stockdb-sdk", "none"], default="auto", help="Bars data source")
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    output_root = Path(args.output_root)
    horizons = [int(h.strip()) for h in args.horizons.split(",") if h.strip()]

    print(f"  Building Factor Forward Returns...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizons: {horizons}")
    print(f"  Source: {args.source}")
    print(f"  Mode: {'dry-run' if args.dry_run else 'force' if args.force else 'default'}")

    # 创建 bars client
    client = None
    if args.source != "none":
        try:
            client = make_bars_client(args.source, expected_min_date=args.start)
            print(f"  ✅ Bars client initialized: {args.source}")
        except Exception as e:
            print(f"  ⚠️ Failed to initialize bars client: {e}")
            client = None

    # 生成日期列表
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 处理每天
    daily_results = []
    total_candidates = 0
    total_matched = 0

    for date in dates:
        result = build_factor_forward_returns(
            date=date,
            candidate_root=candidate_root,
            output_root=output_root,
            horizons=horizons,
            prefer_backfilled=args.prefer_backfilled,
            dry_run=args.dry_run,
            force=args.force,
            client=client,
        )
        daily_results.append(result)

        total_candidates += result["candidate_count"]
        total_matched += result["forward_return_count"]

        # 打印状态
        status_icon = {
            "processed": "✅",
            "dry_run": "🔍",
            "already_exists": "⏭️",
            "missing_candidate_file": "❌",
            "no_candidates": "⚠️",
        }.get(result["status"].split(":")[0], "❓")
        print(f"  {status_icon} {date}: {result['status']} ({result['candidate_count']} candidates, {result['forward_return_count']} matched)")

    # 打印摘要
    print(f"\n  ✅ Build complete")
    print(f"  📊 Processed: {len(dates)} days")
    print(f"  📦 Total candidates: {total_candidates}")
    print(f"  📈 Total matched: {total_matched}")

    # 建议运行评估
    if total_matched > 0:
        print(f"\n  💡 Suggested next step:")
        print(f"     python scripts/evaluate_factor_composite_shadow_score.py --start {args.start} --end {args.end}")


if __name__ == "__main__":
    main()
