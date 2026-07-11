#!/usr/bin/env python3
"""
run_daily.py — one-command daily orchestration with preflight diagnostics.

Usage:
  python run_daily.py --as-of 2026-07-08
  python run_daily.py --as-of 2026-07-08 --skip-agent
  python run_daily.py --as-of 2026-07-08 --quick
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent

# ---- Load local .env files if available ----
try:
    from dotenv import load_dotenv
    _project_env = PROJECT_ROOT / ".env"
    if _project_env.exists():
        load_dotenv(_project_env, override=False)
    _aihedge_env = PROJECT_ROOT.parent / "ai-hedge-fund" / ".env"
    if _aihedge_env.exists():
        load_dotenv(_aihedge_env, override=False)
except ImportError:
    pass

DEFAULT_API_URL = "http://127.0.0.1:8000"
STOCKDB_HOST = "127.0.0.1"
STOCKDB_PORT = 7899


@dataclass(frozen=True)
class Step:
    name: str
    cmd: list[str]
    timeout_seconds: int = 300
    required_mode: str = "data_degraded"


@dataclass
class StepResult:
    name: str
    ok: bool
    returncode: int | None
    duration_seconds: float
    timeout_seconds: int
    timed_out: bool = False
    skipped: bool = False
    skip_reason: str = ""
    stdout_tail: list[str] | None = None
    stderr_tail: list[str] | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stdout_tail"] = self.stdout_tail or []
        data["stderr_tail"] = self.stderr_tail or []
        return data


def _tail_lines(text: str | None, limit: int = 8) -> list[str]:
    if not text:
        return []
    return [line for line in text.splitlines() if line.strip()][-limit:]


def _safe_print_tail(prefix: str, lines: list[str]) -> None:
    for line in lines:
        print(f"  {prefix}{line}")


def _check_tcp_port(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def _check_http_health(api_url: str, timeout: int = 5) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(f"{api_url.rstrip('/')}/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status == 200, body
    except Exception as exc:
        return False, str(exc)


def _check_llm_configured() -> bool:
    keys = [
        "OPENAI_API_KEY",
        "MIMO_API_KEY",
        "XIAOMI_MIMO_API_KEY",
        "LLM_API_KEY",
    ]
    return any(bool(os.environ.get(key)) for key in keys)


def _normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return ""



def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def should_auto_update_data_source(
    preflight: dict[str, Any],
    as_of: str | None,
    enabled: bool,
    today: str | None = None,
) -> tuple[bool, str]:
    if not enabled:
        return False, "disabled"
    target = _normalize_date(as_of)
    current_day = _normalize_date(today or datetime.now().strftime("%Y-%m-%d"))
    if not target:
        return False, "missing_as_of"
    if target != current_day:
        return False, "not_today"
    freshness = preflight.get("data_freshness", {})
    if freshness.get("status") != "stale":
        return False, "not_stale"
    if not preflight.get("stockdb_available"):
        return False, "stockdb_unavailable"
    return True, "today_data_stale"


def run_stockdb_update(expected_date: str, wait_seconds: int, poll_seconds: int) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "scripts/update_stockdb_and_verify.py",
        "--expected-date",
        expected_date,
        "--wait-seconds",
        str(wait_seconds),
        "--poll-seconds",
        str(poll_seconds),
        "--json",
    ]
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(wait_seconds + 120, 180),
        env=_subprocess_env(),
    )
    try:
        payload: dict[str, Any] = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    payload.setdefault("status", "failed" if result.returncode else "unknown")
    payload["returncode"] = result.returncode
    payload["stdout_tail"] = _tail_lines(result.stdout)
    payload["stderr_tail"] = _tail_lines(result.stderr)
    return payload


def maybe_auto_update_data_source(
    preflight: dict[str, Any],
    api_url: str,
    as_of: str,
    enabled: bool,
    wait_seconds: int,
    poll_seconds: int,
) -> dict[str, Any]:
    should_update, reason = should_auto_update_data_source(preflight, as_of, enabled)
    attempt: dict[str, Any] = {
        "enabled": enabled,
        "attempted": False,
        "reason": reason,
    }
    if not should_update:
        updated = dict(preflight)
        updated["data_update_attempt"] = attempt
        return updated

    expected_date = _normalize_date(as_of).replace("-", "")
    print(f"\n[INFO] Today's data is stale; updating StockDB to {expected_date} before running steps...")
    attempt["attempted"] = True
    attempt["expected_date"] = expected_date
    attempt["result"] = run_stockdb_update(expected_date, wait_seconds, poll_seconds)
    refreshed = run_preflight(api_url, as_of=as_of)
    refreshed["data_update_attempt"] = attempt
    if refreshed.get("data_freshness", {}).get("status") == "stale":
        flags = list(refreshed.get("degradation_flags", []))
        if "data_update_failed" not in flags:
            flags.append("data_update_failed")
        refreshed["degradation_flags"] = flags
    return refreshed


def _find_latest_data_date(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("latest_daily_date", "latest_trade_date", "latest_trading_date", "latest_date"):
            if key in value:
                normalized = _normalize_date(value[key])
                if normalized:
                    return normalized
        for child in value.values():
            found = _find_latest_data_date(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_latest_data_date(child)
            if found:
                return found
    return ""


def assess_data_freshness(as_of: str | None, api_detail: str, api_ok: bool) -> dict[str, str]:
    latest = ""
    if api_detail:
        try:
            latest = _find_latest_data_date(json.loads(api_detail))
        except json.JSONDecodeError:
            latest = ""
    target = _normalize_date(as_of)
    if not api_ok:
        status = "unknown"
    elif not target or not latest:
        status = "unknown"
    elif latest < target:
        status = "stale"
    else:
        status = "fresh"
    return {
        "as_of": target,
        "latest_data_date": latest,
        "status": status,
    }


def run_preflight(api_url: str = DEFAULT_API_URL, as_of: str | None = None) -> dict[str, Any]:
    stockdb_ok = _check_tcp_port(STOCKDB_HOST, STOCKDB_PORT)
    api_ok, api_detail = _check_http_health(api_url)
    llm_configured = _check_llm_configured()
    data_freshness = assess_data_freshness(as_of, api_detail, api_ok)

    degradation_flags: list[str] = []
    if not stockdb_ok:
        degradation_flags.append("stockdb_unavailable")
    if not api_ok:
        degradation_flags.append("api_unavailable")
    if not llm_configured:
        degradation_flags.append("llm_unconfigured")
    if data_freshness["status"] == "stale":
        degradation_flags.append("data_stale")

    if stockdb_ok and api_ok and llm_configured:
        run_mode = "full_real"
    elif stockdb_ok or api_ok:
        run_mode = "data_degraded"
    elif llm_configured:
        run_mode = "agent_only"
    else:
        run_mode = "report_only"

    return {
        "run_mode": run_mode,
        "stockdb_available": stockdb_ok,
        "api_available": api_ok,
        "llm_configured": llm_configured,
        "api_url": api_url,
        "data_freshness": data_freshness,
        "degradation_flags": degradation_flags,
        "details": {
            "stockdb": "ok" if stockdb_ok else f"{STOCKDB_HOST}:{STOCKDB_PORT} not reachable",
            "api": api_detail[:500],
            "llm": "configured" if llm_configured else "no known LLM API key env var",
        },
    }


def _mode_allows(step: Step, preflight: dict[str, Any]) -> tuple[bool, str]:
    required = step.required_mode
    run_mode = preflight.get("run_mode", "report_only")
    api_ok = bool(preflight.get("api_available"))
    stockdb_ok = bool(preflight.get("stockdb_available"))
    llm_ok = bool(preflight.get("llm_configured"))

    if required == "full_real" and not (api_ok and stockdb_ok):
        return False, "requires stockdb and market_data_service API"
    if required == "agent_only" and not llm_ok:
        return False, "requires LLM configuration"
    if required == "data_degraded" and run_mode == "report_only":
        return False, "requires at least one data source or explicit report-only mode"
    return True, ""


def build_steps(date: str, py: str, quick: bool = False, skip_agent: bool = False) -> list[Step]:
    steps = [
        Step(
            "Daily Radar",
            [
                py, "-m", "theme_sector_radar.cli",
                "--daily", "--as-of", date, "--provider", "akshare", "--refresh",
                "--lookback-days", "5", "--report-root", "reports/theme_sector_radar",
            ],
            timeout_seconds=420,
            required_mode="data_degraded",
        ),
        Step(
            "Sector Score (industry+concept)",
            [
                py, "-m", "theme_sector_radar.cli",
                "--score-sectors", "--as-of", date, "--sector-type", "both",
                "--top-n", "100", "--report-root", "reports/theme_sector_radar",
            ],
            timeout_seconds=300,
            required_mode="data_degraded",
        ),
        Step(
            "Multi-Window Consensus",
            [
                py, "-m", "theme_sector_radar.cli",
                "--multi-window-consensus", "--as-of", date, "--sector-type", "both",
                "--report-root", "reports/theme_sector_radar",
            ],
            timeout_seconds=300,
            required_mode="data_degraded",
        ),
        Step(
            "Research Agents",
            [
                py, "-m", "theme_sector_radar.cli",
                "--research-agents", "--as-of", date, "--sector-type", "both",
                "--report-root", "reports/theme_sector_radar",
            ],
            timeout_seconds=300,
            required_mode="data_degraded",
        ),
        Step(
            "Unified Pipeline",
            [py, "unified_pipeline.py", "--as-of", date, "--mode", "quick"],
            timeout_seconds=900,
            required_mode="data_degraded",
        ),
    ]

    if not quick and not skip_agent:
        steps.extend([
            Step(
                "AI Stock Report",
                [
                    py, "scripts/run_daily_ai_stock_report.py",
                    "--as-of", date, "--agent-preset", "core", "--agent-mode", "real",
                ],
                timeout_seconds=1200,
                required_mode="full_real",
            ),
            Step(
                "Bridge Report",
                [
                    py, "scripts/run_daily_bridge_report.py",
                    "--as-of", date, "--agent-preset", "selected", "--agent-mode", "real",
                ],
                timeout_seconds=1800,
                required_mode="agent_only",
            ),
        ])
    return steps


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"]:
        env[key] = ""
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run_step(step: Step, step_num: int, total: int) -> StepResult:
    print(f"\n{'=' * 60}")
    print(f"  [{step_num}/{total}] {step.name}")
    print(f"{'=' * 60}")

    start = time.time()
    try:
        result = subprocess.run(
            step.cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=step.timeout_seconds,
            env=_subprocess_env(),
        )
        elapsed = time.time() - start
        stdout_tail = _tail_lines(result.stdout)
        stderr_tail = _tail_lines(result.stderr, limit=5)
        _safe_print_tail("", stdout_tail[-5:])

        ok = result.returncode == 0
        if ok:
            print(f"  [OK] 完成 ({elapsed:.0f}s)")
        else:
            print(f"  [FAIL] 失败 (exit code {result.returncode}, {elapsed:.0f}s)")
            _safe_print_tail("stderr: ", stderr_tail[-5:])

        return StepResult(
            name=step.name,
            ok=ok,
            returncode=result.returncode,
            duration_seconds=elapsed,
            timeout_seconds=step.timeout_seconds,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - start
        stdout_tail = _tail_lines(exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout)
        stderr_tail = _tail_lines(exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr)
        print(f"  [TIMEOUT] 超时 ({step.timeout_seconds}s)")
        _safe_print_tail("", stdout_tail[-5:])
        _safe_print_tail("stderr: ", stderr_tail[-5:])
        return StepResult(
            name=step.name,
            ok=False,
            returncode=None,
            duration_seconds=elapsed,
            timeout_seconds=step.timeout_seconds,
            timed_out=True,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            error="timeout",
        )
    except Exception as exc:
        elapsed = time.time() - start
        print(f"  [ERROR] 异常: {exc}")
        return StepResult(
            name=step.name,
            ok=False,
            returncode=None,
            duration_seconds=elapsed,
            timeout_seconds=step.timeout_seconds,
            error=str(exc),
        )


def _skip_step(step: Step, reason: str) -> StepResult:
    print(f"\n{'=' * 60}")
    print(f"  [SKIP] {step.name}")
    print(f"{'=' * 60}")
    print(f"  [SKIP] {reason}")
    return StepResult(
        name=step.name,
        ok=False,
        returncode=None,
        duration_seconds=0.0,
        timeout_seconds=step.timeout_seconds,
        skipped=True,
        skip_reason=reason,
    )


def expected_artifacts(as_of: str, quick: bool = False, skip_agent: bool = False) -> list[Path]:
    paths = [
        Path("reports") / "theme_sector_radar" / as_of / "run_log.json",
        Path("reports") / "theme_sector_radar" / as_of / "theme_sector_radar.json",
        Path("reports") / "theme_sector_radar" / as_of / "theme_sector_radar.md",
        Path("reports") / "sector_scores" / as_of / "sector_scores.json",
        Path("reports") / "sector_scores" / as_of / "sector_scores.md",
        Path("reports") / "sector_consensus" / as_of / "multi_window_consensus.json",
        Path("reports") / "sector_consensus" / as_of / "multi_window_consensus.md",
        Path("reports") / "sector_research" / as_of / "sector_research.json",
        Path("reports") / "sector_research" / as_of / "sector_research.md",
        Path("reports") / "unified" / as_of / "unified_report.json",
        Path("reports") / "unified" / as_of / "unified_report.md",
    ]
    if not quick and not skip_agent:
        paths.extend([
            Path("reports") / "daily_ai_stock_report" / as_of / "daily_ai_stock_report.json",
            Path("reports") / "daily_ai_stock_report" / as_of / "daily_ai_stock_report.md",
            Path("reports") / "agent_bridge" / as_of / "top30_candidates.json",
            Path("reports") / "agent_bridge" / as_of / "aihf_request.json",
            Path("reports") / "agent_bridge" / as_of / "aihf_stock_ranking.json",
            Path("reports") / "agent_bridge" / as_of / "daily_bridge_report.json",
            Path("reports") / "agent_bridge" / as_of / "daily_bridge_report.md",
        ])
    return paths


def expected_report_date_files(as_of: str) -> list[Path]:
    return [
        Path("reports") / "theme_sector_radar" / as_of / "theme_sector_radar.json",
        Path("reports") / "sector_scores" / as_of / "sector_scores.json",
        Path("reports") / "sector_consensus" / as_of / "multi_window_consensus.json",
        Path("reports") / "sector_research" / as_of / "sector_research.json",
        Path("reports") / "unified" / as_of / "unified_report.json",
    ]


def _extract_payload_date(payload: dict[str, Any]) -> str:
    for key in ("as_of", "as_of_date", "report_date", "trading_date", "date"):
        normalized = _normalize_date(payload.get(key))
        if normalized:
            return normalized
    return ""


def check_report_date_consistency(
    as_of: str,
    project_root: Path | str = PROJECT_ROOT,
) -> list[dict[str, Any]]:
    root = Path(project_root)
    target = _normalize_date(as_of)
    checks: list[dict[str, Any]] = []
    for rel_path in expected_report_date_files(as_of):
        path = root / rel_path
        if not path.exists():
            checks.append({
                "path": rel_path.as_posix(),
                "status": "missing",
                "payload_date": "",
                "expected_date": target,
            })
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload_date = _extract_payload_date(payload) if isinstance(payload, dict) else ""
        except Exception as exc:
            checks.append({
                "path": rel_path.as_posix(),
                "status": "unreadable",
                "payload_date": "",
                "expected_date": target,
                "error": str(exc),
            })
            continue
        if not payload_date:
            status = "unknown"
        elif payload_date == target:
            status = "matched"
        else:
            status = "mismatch"
        checks.append({
            "path": rel_path.as_posix(),
            "status": status,
            "payload_date": payload_date,
            "expected_date": target,
        })
    return checks


def check_artifact_consistency(
    as_of: str,
    started_at: str,
    quick: bool = False,
    skip_agent: bool = False,
    project_root: Path | str = PROJECT_ROOT,
) -> list[dict[str, Any]]:
    root = Path(project_root)
    started_ts = datetime.fromisoformat(started_at).timestamp()
    checks: list[dict[str, Any]] = []
    for rel_path in expected_artifacts(as_of, quick=quick, skip_agent=skip_agent):
        path = root / rel_path
        exists = path.exists()
        if exists:
            mtime_ts = path.stat().st_mtime
            fresh = mtime_ts >= started_ts
            mtime = datetime.fromtimestamp(mtime_ts).isoformat(timespec="seconds")
            status = "fresh" if fresh else "stale"
        else:
            fresh = False
            mtime = ""
            status = "missing"
        checks.append({
            "path": rel_path.as_posix(),
            "exists": exists,
            "fresh": fresh,
            "mtime": mtime,
            "status": status,
        })
    return checks


def summarize_artifact_checks(artifact_checks: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"fresh": 0, "stale": 0, "missing": 0, "total": len(artifact_checks)}
    for item in artifact_checks:
        status = item.get("status")
        if status in ("fresh", "stale", "missing"):
            summary[status] += 1
    return summary


def _dry_run_result(step: Step, allowed: bool, reason: str) -> StepResult:
    return StepResult(
        name=step.name,
        ok=allowed,
        returncode=0 if allowed else None,
        duration_seconds=0.0,
        timeout_seconds=step.timeout_seconds,
        skipped=not allowed,
        skip_reason=reason,
    )


def write_daily_run_report(
    as_of: str,
    started_at: str,
    finished_at: str,
    elapsed_seconds: float,
    preflight: dict[str, Any],
    step_results: list[StepResult],
    artifact_checks: list[dict[str, Any]] | None = None,
    report_date_checks: list[dict[str, Any]] | None = None,
    output_root: Path | str | None = None,
) -> dict[str, Path]:
    root = Path(output_root) if output_root is not None else PROJECT_ROOT / "reports"
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / f"daily_run_report_{as_of}.json"
    md_path = root / f"daily_run_report_{as_of}.md"

    passed = sum(1 for r in step_results if r.ok)
    skipped = sum(1 for r in step_results if r.skipped)
    failed = len(step_results) - passed - skipped
    artifact_checks = artifact_checks or []
    report_date_checks = report_date_checks or []
    artifact_summary = summarize_artifact_checks(artifact_checks)
    payload = {
        "schema_version": "1.0",
        "report_type": "daily_run_report",
        "as_of": as_of,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "preflight": preflight,
        "summary": {"passed": passed, "failed": failed, "skipped": skipped, "total": len(step_results)},
        "steps": [r.to_dict() for r in step_results],
        "artifact_summary": artifact_summary,
        "artifact_consistency": artifact_checks,
        "report_date_consistency": report_date_checks,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Daily Run Report {as_of}",
        "",
        f"- Started: {started_at}",
        f"- Finished: {finished_at}",
        f"- Elapsed seconds: {elapsed_seconds:.0f}",
        f"- Run mode: {preflight.get('run_mode', 'unknown')}",
        f"- Degradation flags: {', '.join(preflight.get('degradation_flags', [])) or '-'}",
        "",
        "## Preflight",
        "",
        f"- StockDB: {'OK' if preflight.get('stockdb_available') else 'MISSING'}",
        f"- market_data_service API: {'OK' if preflight.get('api_available') else 'MISSING'}",
        f"- LLM configured: {'YES' if preflight.get('llm_configured') else 'NO'}",
        "",
        "## Steps",
        "",
        "| Step | Status | Seconds | Timeout | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for r in step_results:
        if r.skipped:
            status = "SKIP"
            note = r.skip_reason
        elif r.ok:
            status = "OK"
            note = ""
        elif r.timed_out:
            status = "TIMEOUT"
            note = r.error or "timeout"
        else:
            status = "FAIL"
            note = r.error or "; ".join((r.stderr_tail or [])[-2:])
        safe_note = str(note).replace("|", "/")[:180]
        lines.append(f"| {r.name} | {status} | {r.duration_seconds:.0f} | {r.timeout_seconds} | {safe_note} |")

    if artifact_checks:
        lines.extend([
            "",
            "## Artifact Consistency",
            "",
            f"- Fresh: {artifact_summary['fresh']}",
            f"- Stale: {artifact_summary['stale']}",
            f"- Missing: {artifact_summary['missing']}",
            "",
            "| Artifact | Status | MTime |",
            "|---|---:|---|",
        ])
        for item in artifact_checks:
            lines.append(f"| {item['path']} | {item['status']} | {item.get('mtime', '') or '-'} |")

    if report_date_checks:
        lines.extend([
            "",
            "## Report Date Consistency",
            "",
            "| Report | Status | Payload Date | Expected Date |",
            "|---|---:|---|---|",
        ])
        for item in report_date_checks:
            lines.append(
                f"| {item['path']} | {item['status']} | "
                f"{item.get('payload_date', '') or '-'} | {item.get('expected_date', '') or '-'} |"
            )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_path, "md": md_path}


def write_artifact_manifest(
    as_of: str,
    started_at: str,
    finished_at: str,
    preflight: dict[str, Any],
    steps: list[Step],
    step_results: list[StepResult],
    artifact_checks: list[dict[str, Any]],
    report_date_checks: list[dict[str, Any]] | None = None,
    output_root: Path | str | None = None,
) -> Path:
    root = Path(output_root) if output_root is not None else PROJECT_ROOT / "reports" / "artifact_manifest" / as_of
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "run_manifest.json"
    payload = {
        "schema_version": "1.0",
        "report_type": "artifact_manifest",
        "as_of": as_of,
        "started_at": started_at,
        "finished_at": finished_at,
        "preflight": preflight,
        "steps": [asdict(step) for step in steps],
        "step_results": [result.to_dict() for result in step_results],
        "artifact_summary": summarize_artifact_checks(artifact_checks),
        "artifacts": artifact_checks,
        "report_date_consistency": report_date_checks or [],
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def _print_preflight(preflight: dict[str, Any]) -> None:
    print("\nPreflight")
    print("---------")
    print(f"  Run mode: {preflight['run_mode']}")
    print(f"  StockDB {STOCKDB_HOST}:{STOCKDB_PORT}: {'OK' if preflight['stockdb_available'] else 'MISSING'}")
    print(f"  market_data_service API: {'OK' if preflight['api_available'] else 'MISSING'}")
    print(f"  LLM configured: {'YES' if preflight['llm_configured'] else 'NO'}")
    freshness = preflight.get("data_freshness", {})
    if freshness:
        latest = freshness.get("latest_data_date") or "unknown"
        print(f"  Data freshness: {freshness.get('status', 'unknown')} (latest={latest})")
    flags = preflight.get("degradation_flags", [])
    if flags:
        print(f"  Degradation flags: {', '.join(flags)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="一键运行完整管线")
    parser.add_argument("--as-of", required=True, help="分析日期 (YYYY-MM-DD)")
    parser.add_argument("--skip-agent", action="store_true", help="跳过 Agent 分析（Step 6-7）")
    parser.add_argument("--quick", action="store_true", help="快速模式（仅 Step 1-5）")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="market_data_service API URL")
    parser.add_argument(
        "--auto-update-data-source",
        action=argparse.BooleanOptionalAction,
        default=_env_flag("THEME_RADAR_AUTO_UPDATE_TODAY_DATA", False),
        help="Auto-update StockDB when --as-of is today and preflight reports stale data.",
    )
    parser.add_argument(
        "--data-update-wait-seconds",
        type=int,
        default=_env_int("THEME_RADAR_DATA_UPDATE_WAIT_SECONDS", 1200),
        help="Maximum seconds to wait for automatic StockDB update.",
    )
    parser.add_argument(
        "--data-update-poll-seconds",
        type=int,
        default=_env_int("THEME_RADAR_DATA_UPDATE_POLL_SECONDS", 30),
        help="Seconds between automatic StockDB freshness checks.",
    )
    parser.add_argument("--preflight-only", action="store_true", help="只检查前置依赖，不构建或执行步骤")
    parser.add_argument("--dry-run", action="store_true", help="只列出将执行的步骤并写入诊断报告，不执行 subprocess")
    parser.add_argument(
        "--fail-on-stale-artifact",
        action="store_true",
        help="产物存在 stale/missing 时以退出码 3 失败",
    )
    args = parser.parse_args()

    date = args.as_of
    started_at = datetime.now().isoformat(timespec="seconds")
    preflight = run_preflight(args.api_url, as_of=date)

    if not args.preflight_only and not args.dry_run:
        preflight = maybe_auto_update_data_source(
            preflight,
            args.api_url,
            as_of=date,
            enabled=args.auto_update_data_source,
            wait_seconds=args.data_update_wait_seconds,
            poll_seconds=args.data_update_poll_seconds,
        )

    if args.preflight_only:
        _print_preflight(preflight)
        raise SystemExit(0 if preflight.get("run_mode") != "report_only" else 2)

    steps = build_steps(date, sys.executable, quick=args.quick, skip_agent=args.skip_agent)
    total = len(steps)

    print(f"\n{'#' * 60}")
    print(f"  Theme Sector Radar — 一键运行 {total} 步")
    print(f"  日期: {date}")
    print(f"{'#' * 60}")
    _print_preflight(preflight)

    start_time = time.time()
    results: list[StepResult] = []
    for i, step in enumerate(steps, 1):
        allowed, reason = _mode_allows(step, preflight)
        if args.dry_run:
            print(f"  [DRY-RUN] {step.name}: {'RUN' if allowed else 'SKIP'} {reason}")
            result = _dry_run_result(step, allowed, reason)
        elif not allowed:
            result = _skip_step(step, reason)
        else:
            result = run_step(step, i, total)
        results.append(result)
        if not result.ok and not result.skipped and i < total:
            print(f"\n[WARN] Step {i} 失败，后续步骤可能受影响")

    elapsed = time.time() - start_time
    finished_at = datetime.now().isoformat(timespec="seconds")
    artifact_checks = check_artifact_consistency(
        date,
        started_at,
        quick=args.quick,
        skip_agent=args.skip_agent,
        project_root=PROJECT_ROOT,
    )
    report_date_checks = check_report_date_consistency(date, project_root=PROJECT_ROOT)
    artifact_summary = summarize_artifact_checks(artifact_checks)
    report_paths = write_daily_run_report(
        date,
        started_at,
        finished_at,
        elapsed,
        preflight,
        results,
        artifact_checks=artifact_checks,
        report_date_checks=report_date_checks,
    )
    manifest_path = write_artifact_manifest(
        date,
        started_at,
        finished_at,
        preflight,
        steps,
        results,
        artifact_checks,
        report_date_checks=report_date_checks,
    )

    passed = sum(1 for r in results if r.ok)
    skipped = sum(1 for r in results if r.skipped)
    failed = total - passed - skipped

    print(f"\n{'#' * 60}")
    print(f"  运行完成 — {passed}/{total} 步成功, {skipped} 步跳过 ({elapsed:.0f}s)")
    print(f"{'#' * 60}")
    for r in results:
        if r.ok:
            status = "[OK]"
        elif r.skipped:
            status = "[SKIP]"
        else:
            status = "[FAIL]"
        print(f"  {status} {r.name}")

    stale_or_missing = artifact_summary["stale"] + artifact_summary["missing"]
    if stale_or_missing:
        print(
            "\n[WARN] artifact consistency: "
            f"fresh={artifact_summary['fresh']}, "
            f"stale={artifact_summary['stale']}, "
            f"missing={artifact_summary['missing']}"
        )
    mismatched_dates = [item for item in report_date_checks if item.get("status") == "mismatch"]
    if mismatched_dates:
        print(f"\n[WARN] report date consistency: mismatches={len(mismatched_dates)}")

    print(f"\n运行诊断报告: {report_paths['md']}")
    print(f"产物 manifest: {manifest_path}")
    if failed:
        print(f"\n[WARN] {failed} 步失败，请检查 daily_run_report")
        raise SystemExit(1)
    if skipped:
        print(f"\n[WARN] {skipped} 步因前置依赖不足跳过，报告已记录降级原因")
        raise SystemExit(2)
    if args.fail_on_stale_artifact and stale_or_missing:
        print("\n[WARN] stale/missing artifacts detected; failing because --fail-on-stale-artifact is set")
        raise SystemExit(3)
    print("\n[OK] 全部完成！报告目录: reports/")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
