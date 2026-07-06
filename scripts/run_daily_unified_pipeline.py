#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日一键运行脚本 — Unified Pipeline 盘后执行入口。

功能:
  1. 检查 StockDB (7899) 是否监听。
  2. 检查 market_data_service API (8000) 是否可访问。
  3. 运行 unified_pipeline.py quick 模式。
  4. 输出报告路径、健康门禁、数据来源。
  5. 可选 --fail-on-health-fail 使 health=fail 时 exit code = 2。

用法:
  python scripts/run_daily_unified_pipeline.py --as-of 2026-07-02 --mode quick
  python scripts/run_daily_unified_pipeline.py --fail-on-health-fail
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

STOCKDB_HOST = "127.0.0.1"
STOCKDB_PORT = 7899

DEFAULT_API_URL = "http://127.0.0.1:8000"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNIFIED_PIPELINE = PROJECT_ROOT / "unified_pipeline.py"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _check_tcp_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is listening."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _check_http_health(api_url: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """Return (reachable, health_json_or_error)."""
    try:
        import urllib.request
        url = f"{api_url.rstrip('/')}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return True, body
    except Exception as exc:
        return False, str(exc)


def _run_unified_pipeline(
    as_of: str,
    mode: str,
    output_dir: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Run unified_pipeline.py as a subprocess."""
    cmd = [
        sys.executable,
        str(UNIFIED_PIPELINE),
        "--as-of", as_of,
        "--mode", mode,
    ]
    if output_dir:
        cmd.extend(["--output", output_dir])

    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          cwd=str(PROJECT_ROOT))


def _find_latest_report(as_of: str) -> Optional[Path]:
    """Locate the unified_report.json written by the pipeline."""
    report_dir = PROJECT_ROOT / "reports" / "unified" / as_of
    report_path = report_dir / "unified_report.json"
    if report_path.exists():
        return report_path
    return None


def _load_report(report_path: Path) -> Dict[str, Any]:
    """Load a unified report JSON."""
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _print_status_header():
    print(f"{'='*70}")
    print(f"  Unified Pipeline — 每日盘后执行")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print()


def _print_preflight(label: str, ok: bool, detail: str = ""):
    icon = "✅" if ok else "❌"
    msg = f"  {icon} {label}"
    if detail:
        msg += f": {detail}"
    print(msg)


def _print_health(result: Dict[str, Any]):
    health = result.get("run_health", {})
    status = health.get("status", "unknown")
    reasons = health.get("reasons", [])

    status_icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(status, "")
    print(f"{status_icon} 健康门禁: {status.upper()}")
    for r in reasons:
        print(f"    - {r}")

    ds = result.get("data_source", {})
    csrc = ds.get("constituent_sources", {})
    qsrc = ds.get("quant_score_sources", {})
    if csrc:
        print(f"  成分股来源: {json.dumps(csrc, ensure_ascii=False)}")
    if qsrc:
        print(f"  量化评分来源: {json.dumps(qsrc, ensure_ascii=False)}")


# ---------------------------------------------------------------------------
# 运行索引（Phase 8）
# ---------------------------------------------------------------------------

DEFAULT_INDEX_PATH = PROJECT_ROOT / "reports" / "unified_runs_index.jsonl"


def _build_index_entry(
    as_of: str,
    mode: str,
    report_path: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a single index line from a pipeline result."""
    health = result.get("run_health", {})
    ds = result.get("data_source", {})

    # Top candidates summary (code + name + final_score only)
    trend_top = [
        {"code": s.get("code", ""), "name": s.get("name", ""),
         "final_score": s.get("final_score", 0)}
        for s in result.get("trend_top_stocks", [])[:10]
    ]
    burst_top = [
        {"code": s.get("code", ""), "name": s.get("name", ""),
         "final_score": s.get("final_score", 0)}
        for s in result.get("burst_top_stocks", [])[:10]
    ]

    return {
        "run_at": datetime.now().isoformat(),
        "as_of": as_of,
        "mode": mode,
        "report_path": str(report_path),
        "run_health_status": health.get("status", "unknown"),
        "run_health_reasons": health.get("reasons", []),
        "constituent_sources": ds.get("constituent_sources", {}),
        "quant_score_sources": ds.get("quant_score_sources", {}),
        "trend_top_candidates": trend_top,
        "burst_top_candidates": burst_top,
    }


def _append_index(index_path: Path, entry: Dict[str, Any]) -> None:
    """Append one JSON line to the index file.

    Write failure is caught and printed as a warning — it must not
    cause the main pipeline to fail.
    """
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False)
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as exc:
        print(f"⚠️  索引写入失败 (非致命): {exc}")


# ---------------------------------------------------------------------------
# 运行历史摘要（Phase 9）
# ---------------------------------------------------------------------------


def load_run_history(path: Path, limit: int = 0) -> list[Dict[str, Any]]:
    """Load all entries from a JSONL index file.

    Parameters
    ----------
    path : Path
        Path to the JSONL file.
    limit : int
        If > 0, return only the last *limit* entries.

    Returns
    -------
    list[dict]
        Parsed entries (empty list on any error).
    """
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    entries: list[Dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if limit > 0 and len(entries) > limit:
        return entries[-limit:]
    return entries


def summarize_run_history(records: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute a summary from a list of run-history records.

    Parameters
    ----------
    records : list[dict]
        Entries from :func:`load_run_history`, newest last.

    Returns
    -------
    dict
        {
            "total": int,
            "pass_count": int, "warn_count": int, "fail_count": int,
            "consecutive_warn_count": int,
            "consecutive_fail_count": int,
            "latest_status": str,
            "all_http_mapping": bool,
            "repeated_trend_stocks": [(code, name, count), ...],
            "repeated_burst_stocks": [(code, name, count), ...],
            "merged_constituent_sources": dict,
            "merged_quant_sources": dict,
        }
    """
    if not records:
        return {
            "total": 0,
            "pass_count": 0, "warn_count": 0, "fail_count": 0,
            "consecutive_warn_count": 0, "consecutive_fail_count": 0,
            "latest_status": "unknown",
            "all_http_mapping": False,
            "repeated_trend_stocks": [],
            "repeated_burst_stocks": [],
            "merged_constituent_sources": {},
            "merged_quant_sources": {},
        }

    total = len(records)
    pass_count = sum(1 for r in records if r.get("run_health_status") == "pass")
    warn_count = sum(1 for r in records if r.get("run_health_status") == "warn")
    fail_count = sum(1 for r in records if r.get("run_health_status") == "fail")

    # Consecutive counts (from the end backwards)
    consecutive_warn = 0
    consecutive_fail = 0
    for r in reversed(records):
        st = r.get("run_health_status", "")
        if st == "warn":
            consecutive_warn += 1
        else:
            break
    for r in reversed(records):
        st = r.get("run_health_status", "")
        if st == "fail":
            consecutive_fail += 1
        else:
            break

    latest_status = records[-1].get("run_health_status", "unknown") if records else "unknown"

    # Check if ALL records are http_mapping-dominated (http_em==0, http_stale==0,
    # http_local_industry==0, http_mapping>0) — only warn when NO real source is used
    all_http_mapping = True
    for r in records:
        csrc = r.get("constituent_sources", {})
        if csrc.get("http_em", 0) > 0 or csrc.get("http_stale", 0) > 0 or csrc.get("http_local_industry", 0) > 0:
            all_http_mapping = False
            break
        if csrc.get("http_mapping", 0) == 0 and csrc.get("local_emergency_mapping", 0) == 0:
            all_http_mapping = False
            break

    # Repeated stocks across recent runs
    from collections import Counter
    trend_counter: Counter = Counter()
    burst_counter: Counter = Counter()
    for r in records:
        for s in r.get("trend_top_candidates", []):
            code = s.get("code", "")
            name = s.get("name", "")
            if code:
                trend_counter[(code, name)] += 1
        for s in r.get("burst_top_candidates", []):
            code = s.get("code", "")
            name = s.get("name", "")
            if code:
                burst_counter[(code, name)] += 1

    repeated_trend = [(code, name, cnt) for (code, name), cnt in trend_counter.most_common(5) if cnt > 1]
    repeated_burst = [(code, name, cnt) for (code, name), cnt in burst_counter.most_common(5) if cnt > 1]

    # Merged source distributions
    merged_csrc: Dict[str, int] = {}
    merged_qsrc: Dict[str, int] = {}
    for r in records:
        for k, v in r.get("constituent_sources", {}).items():
            merged_csrc[k] = merged_csrc.get(k, 0) + v
        for k, v in r.get("quant_score_sources", {}).items():
            merged_qsrc[k] = merged_qsrc.get(k, 0) + v

    return {
        "total": total,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "consecutive_warn_count": consecutive_warn,
        "consecutive_fail_count": consecutive_fail,
        "latest_status": latest_status,
        "all_http_mapping": all_http_mapping,
        "repeated_trend_stocks": repeated_trend,
        "repeated_burst_stocks": repeated_burst,
        "merged_constituent_sources": merged_csrc,
        "merged_quant_sources": merged_qsrc,
    }


def _print_history_summary(records: list[Dict[str, Any]], summary: Dict[str, Any]) -> None:
    """Print the enhanced summary block after the history table."""
    print()
    print(f"{'─'*70}")
    print(f"  Summary")
    print(f"{'─'*70}")

    total = summary["total"]
    if total == 0:
        print("  (无可用数据)")
        return

    # Health distribution
    p, w, f = summary["pass_count"], summary["warn_count"], summary["fail_count"]
    print(f"  健康分布: PASS={p}  WARN={w}  FAIL={f}  (共 {total} 次)")

    # Consecutive status
    latest = summary["latest_status"]
    icon_latest = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(latest, "")
    print(f"  最新状态: {icon_latest} {latest.upper()}")

    if summary["consecutive_warn_count"] >= 3:
        print(f"  ⚠️ 连续 WARN {summary['consecutive_warn_count']} 次 — 请排查数据源降级原因")
    elif summary["consecutive_warn_count"] > 0:
        print(f"  连续 WARN: {summary['consecutive_warn_count']} 次")

    if summary["consecutive_fail_count"] > 0:
        print(f"  ❌ 连续 FAIL {summary['consecutive_fail_count']} 次 — 数据严重不足，请立即检查")

    # Data source stagnation
    if summary["all_http_mapping"] and total > 0:
        print(f"  ⚠️ 成分股连续依赖离线映射，建议检查 EM 源或扩展真实成分股源")

    # Merged sources
    csrc = summary["merged_constituent_sources"]
    qsrc = summary["merged_quant_sources"]
    if csrc:
        print(f"  成分股来源汇总: {json.dumps(csrc, ensure_ascii=False)}")
    if qsrc:
        print(f"  量化评分来源汇总: {json.dumps(qsrc, ensure_ascii=False)}")

    # Repeated stocks
    rt = summary["repeated_trend_stocks"]
    rb = summary["repeated_burst_stocks"]
    if rt:
        print(f"  趋势候选连续上榜 (≥2次):")
        for code, name, cnt in rt:
            print(f"    {code} {name} — {cnt} 次")
    if rb:
        print(f"  短线候选连续上榜 (≥2次):")
        for code, name, cnt in rb:
            print(f"    {code} {name} — {cnt} 次")


def _show_history(index_path: Path, count: int) -> None:
    """Print the last *count* runs + enhanced summary."""
    records = load_run_history(index_path, limit=count)
    if not records:
        print("(暂无历史记录)")
        return

    # Print table
    print(f"{'as_of':<12} {'health':<6} {'trend':>5} {'burst':>5}  source summary")
    print(f"{'─'*70}")
    for e in reversed(records):  # newest first
        as_of = e.get("as_of", "?")
        health = e.get("run_health_status", "?")[:6]
        trend_n = len(e.get("trend_top_candidates", []))
        burst_n = len(e.get("burst_top_candidates", []))
        csrc = e.get("constituent_sources", {})
        parts = []
        for k in ("http_em", "http_stale", "http_local_industry", "http_mapping", "local_emergency_mapping", "unavailable"):
            v = csrc.get(k, 0)
            if v:
                short = k.replace("http_local_industry", "local_ind") \
                          .replace("http_", "") \
                          .replace("local_emergency_", "local_emg_") \
                          .replace("mapping", "map")
                parts.append(f"{short}={v}")
        src_str = " ".join(parts) if parts else "—"

        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(health, "")
        print(f"{as_of:<12} {icon}{health:<5} {trend_n:>5} {burst_n:>5}  {src_str}")

    # Print summary
    summary = summarize_run_history(records)
    _print_history_summary(records, summary)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="每日一键运行 Unified Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/run_daily_unified_pipeline.py
  python scripts/run_daily_unified_pipeline.py --as-of 2026-07-02 --mode deep
  python scripts/run_daily_unified_pipeline.py --fail-on-health-fail
  python scripts/run_daily_unified_pipeline.py --show-history 10
        """,
    )
    parser.add_argument(
        "--as-of", type=str, default=datetime.now().strftime("%Y-%m-%d"),
        help="分析日期 (默认: 今天)",
    )
    parser.add_argument(
        "--mode", type=str, choices=["quick", "deep"], default="quick",
        help="运行模式 (默认: quick)",
    )
    parser.add_argument(
        "--api-url", type=str, default=DEFAULT_API_URL,
        help="market_data_service HTTP API 地址 (默认: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--fail-on-health-fail", action="store_true",
        help="当 run_health.status == 'fail' 时 exit code = 2",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="覆盖默认报告输出目录",
    )
    # Phase 8: 运行索引
    parser.add_argument(
        "--no-append-index", action="store_true",
        help="不追加运行记录到索引文件",
    )
    parser.add_argument(
        "--index-path", type=str, default=str(DEFAULT_INDEX_PATH),
        help=f"索引文件路径 (默认: {DEFAULT_INDEX_PATH})",
    )
    parser.add_argument(
        "--show-history", type=int, default=0, metavar="N",
        help="仅显示最近 N 次运行历史，不执行 pipeline",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # --show-history: print recent runs and exit
    # ------------------------------------------------------------------
    if args.show_history > 0:
        index_path = Path(args.index_path)
        print(f"{'='*70}")
        print(f"  Unified Pipeline 运行历史 (最近 {args.show_history} 次)")
        print(f"{'='*70}")
        print()
        _show_history(index_path, args.show_history)
        return 0

    _print_status_header()

    # ------------------------------------------------------------------
    # Pre-flight checks
    # ------------------------------------------------------------------

    print("── 前置检查 ──")

    # 1. StockDB
    stockdb_ok = _check_tcp_port(STOCKDB_HOST, STOCKDB_PORT)
    _print_preflight(
        f"StockDB ({STOCKDB_HOST}:{STOCKDB_PORT})",
        stockdb_ok,
        "可连接" if stockdb_ok else "无法连接 — 个股K线将使用缓存或降级",
    )

    # 2. market_data_service API
    api_ok, api_detail = _check_http_health(args.api_url)
    _print_preflight(
        f"market_data_service API ({args.api_url})",
        api_ok,
        api_detail[:120] if api_ok else "无法访问",
    )

    if not api_ok:
        print()
        print("❌ market_data_service API 未启动，请先启动：")
        print()
        print("    cd E:\\liaohua\\01_projects\\market_data_service")
        print("    python -m market_data_service.api_server --host 127.0.0.1 --port 8000")
        print()
        print("   然后重新运行本脚本。")
        return 1

    print()

    # ------------------------------------------------------------------
    # Run unified pipeline
    # ------------------------------------------------------------------

    print("── 运行 Unified Pipeline ──")
    print()

    proc = _run_unified_pipeline(
        as_of=args.as_of,
        mode=args.mode,
        output_dir=args.output_dir,
    )

    # Print subprocess output (already captured)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)

    if proc.returncode != 0:
        print(f"❌ unified_pipeline.py 退出码: {proc.returncode}")
        return proc.returncode

    # ------------------------------------------------------------------
    # Read and summarise report
    # ------------------------------------------------------------------

    report_path = _find_latest_report(args.as_of)
    if not report_path:
        print(f"⚠️  未找到报告文件 (reports/unified/{args.as_of}/unified_report.json)")
        return 0

    print(f"📁 报告路径: {report_path}")

    result = _load_report(report_path)

    print()
    print(f"{'─'*70}")
    print(f"  运行摘要")
    print(f"{'─'*70}")
    _print_health(result)

    # ------------------------------------------------------------------
    # Append to run index (Phase 8)
    # ------------------------------------------------------------------
    if not args.no_append_index:
        index_path = Path(args.index_path)
        entry = _build_index_entry(
            as_of=args.as_of,
            mode=args.mode,
            report_path=str(report_path),
            result=result,
        )
        _append_index(index_path, entry)
        print(f"\n📋 运行记录已追加到索引: {index_path}")

    # Exit code based on health gate
    health = result.get("run_health", {})
    if args.fail_on_health_fail and health.get("status") == "fail":
        print()
        print("❌ 健康门禁 FAIL，且 --fail-on-health-fail 已启用")
        return 2

    if health.get("status") == "warn":
        print()
        print("⚠️  健康门禁 WARN — 数据可能降级，请检查报告")

    print()
    print("✅ 每日运行完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
