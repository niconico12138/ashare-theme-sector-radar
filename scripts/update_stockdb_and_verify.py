#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update the local desktop StockDB package and verify freshness."""

from __future__ import annotations

import argparse
import os
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient

STOCKDB_HOST = os.environ.get("STOCKDB_HOST", "127.0.0.1")
STOCKDB_PORT = int(os.environ.get("STOCKDB_PORT", "7899"))
STOCKDB_ROOT = Path(os.environ.get("STOCKDB_ROOT", ""))
STOCKDB_EXE = STOCKDB_ROOT / "stockdb.exe"


def resolve_stockdb_update_exe(root: Path) -> Path:
    candidates = ["数据更新.exe"]
    for name in candidates:
        candidate = root / name
        if candidate.exists():
            return candidate
    return root / candidates[0]


STOCKDB_UPDATE_EXE = resolve_stockdb_update_exe(STOCKDB_ROOT)

def normalize_date(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().replace("-", "")
    return text[:8] if len(text) >= 8 and text[:8].isdigit() else None


def last_trading_day(now: datetime | None = None) -> str:
    current = now or datetime.now()
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current.strftime("%Y%m%d")


class StockDBOps:
    """Side-effect operations for StockDB process control."""

    def __init__(
        self,
        stockdb_exe: Path = STOCKDB_EXE,
        update_exe: Path = STOCKDB_UPDATE_EXE,
        host: str = STOCKDB_HOST,
        port: int = STOCKDB_PORT,
    ):
        self.stockdb_exe = Path(stockdb_exe)
        self.update_exe = Path(update_exe)
        self.host = host
        self.port = port

    def is_running(self) -> bool:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=3)
            sock.close()
            return True
        except Exception:
            return False

    def get_latest_date(self) -> str | None:
        try:
            return StockDBSdkClient(host=self.host, port=self.port).get_latest_daily_date()
        except Exception:
            return None

    def stop_database(self) -> bool:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Process stockdb -ErrorAction SilentlyContinue | Stop-Process -Force"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return True

    def start_updater(self) -> bool:
        if not self.update_exe.exists():
            raise FileNotFoundError(str(self.update_exe))
        subprocess.Popen(
            [str(self.update_exe)],
            cwd=str(self.update_exe.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    def start_database(self) -> bool:
        if not self.stockdb_exe.exists():
            raise FileNotFoundError(str(self.stockdb_exe))
        if self.is_running():
            return True
        subprocess.Popen(
            [str(self.stockdb_exe)],
            cwd=str(self.stockdb_exe.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    def sleep(self, seconds: int) -> None:
        time.sleep(seconds)


class StockDBUpdateRunner:
    def __init__(
        self,
        ops: StockDBOps,
        expected_date: str | None = None,
        wait_seconds: int = 1200,
        poll_seconds: int = 30,
    ):
        self.ops = ops
        self.expected_date = normalize_date(expected_date) or last_trading_day()
        self.wait_seconds = int(wait_seconds)
        self.poll_seconds = max(int(poll_seconds), 1)

    def run(self) -> dict:
        latest = normalize_date(self.ops.get_latest_date())
        if latest and latest >= self.expected_date:
            return self._result("already_fresh", latest)

        self.ops.stop_database()
        self.ops.start_updater()

        elapsed = 0
        latest_after_update = latest
        while elapsed < self.wait_seconds:
            self.ops.sleep(self.poll_seconds)
            elapsed += self.poll_seconds
            self.ops.start_database()
            latest_after_update = normalize_date(self.ops.get_latest_date()) or latest_after_update
            if latest_after_update and latest_after_update >= self.expected_date:
                return self._result("updated", latest_after_update, elapsed)

        self.ops.start_database()
        latest_after_update = normalize_date(self.ops.get_latest_date()) or latest_after_update
        return self._result("timeout", latest_after_update, elapsed)

    def _result(self, status: str, latest: str | None, elapsed_seconds: int = 0) -> dict:
        return {
            "status": status,
            "latest_daily_date": latest,
            "expected_date": self.expected_date,
            "elapsed_seconds": elapsed_seconds,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update local StockDB and verify latest daily data")
    parser.add_argument("--expected-date", default=None, help="Expected latest date, YYYYMMDD or YYYY-MM-DD")
    parser.add_argument("--wait-seconds", type=int, default=1200, help="Maximum seconds to wait for update")
    parser.add_argument("--poll-seconds", type=int, default=30, help="Seconds between freshness checks")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runner = StockDBUpdateRunner(
        ops=StockDBOps(),
        expected_date=args.expected_date,
        wait_seconds=args.wait_seconds,
        poll_seconds=args.poll_seconds,
    )
    result = runner.run()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Status: {result['status']}")
        print(f"Latest daily date: {result['latest_daily_date']}")
        print(f"Expected date: {result['expected_date']}")
        print(f"Elapsed seconds: {result['elapsed_seconds']}")
    return 0 if result["status"] in ("already_fresh", "updated") else 1


if __name__ == "__main__":
    sys.exit(main())

