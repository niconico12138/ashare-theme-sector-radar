#!/usr/bin/env python3
"""Build the unified joint decision summary.

This command only reads existing artifacts. It does not call LLM agents and it
does not change official scoring or ranking.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.joint_decision.runner import run_joint_decision  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build joint decision summary")
    parser.add_argument("--as-of", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--top-n", type=int, default=10, help="Max rows per section")
    parser.add_argument("--output-dir", default="", help="Optional output directory")
    args = parser.parse_args()

    result = run_joint_decision(
        args.as_of,
        project_root=PROJECT_ROOT,
        top_n=args.top_n,
        output_root=args.output_dir or None,
    )
    print(f"Joint decision JSON: {result['json']}")
    print(f"Joint decision Markdown: {result['md']}")


if __name__ == "__main__":
    main()
