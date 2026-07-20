"""Run the independent concept direction research path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.concept_shadow_pipeline import run_concept_shadow_pipeline
from theme_sector_radar.data.akshare_concept_history import (
    AkShareConceptHistoryClient,
)


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument parsing failed: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description="Run concept direction paper/shadow research."
    )
    parser.add_argument("--as-of", required=True)
    parser.add_argument(
        "--membership-root",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "board_membership_snapshots",
    )
    parser.add_argument(
        "--history-cache-root",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "concept_history",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow",
    )
    parser.add_argument("--history-lookback-days", type=int, default=60)
    parser.add_argument("--top-n", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = build_parser().parse_args(raw_argv)
        history_client = AkShareConceptHistoryClient(
            cache_root=args.history_cache_root,
        )
        report = run_concept_shadow_pipeline(
            as_of_date=args.as_of,
            membership_root=args.membership_root,
            report_root=args.report_root,
            history_client=history_client,
            history_lookback_days=args.history_lookback_days,
            top_n=args.top_n,
        )
    except Exception as exc:
        failure = {
            "status": "failed",
            "mode": "paper_shadow_research_only",
            "as_of_date": (
                raw_argv[raw_argv.index("--as-of") + 1]
                if "--as-of" in raw_argv
                and raw_argv.index("--as-of") + 1 < len(raw_argv)
                else None
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "disclaimer": "Paper/shadow research only; no executable instructions.",
        }
        print(json.dumps(failure, ensure_ascii=False, allow_nan=False))
        return 2 if str(exc).startswith("argument parsing failed:") else 1
    summary = {
        "status": report["status"],
        "as_of_date": report["as_of_date"],
        "mode": report["mode"],
        "scored_concepts": report["concept_direction"]["input_counts"]["scored"],
        "selected_concepts": len(
            report["concept_selection"]["concept_shadow_candidates"]
        ),
        "bridged_stocks": report["bridge"]["unique_stock_count"],
    }
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
