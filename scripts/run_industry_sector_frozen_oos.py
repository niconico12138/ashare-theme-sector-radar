"""Run fail-closed frozen industry OOS preflight and evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.industry_sector_frozen_oos import run_frozen_oos_evaluation
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    collection_root = PROJECT_ROOT / "reports" / "paper_shadow" / "industry_sector_ml_shadow" / "prospective_collection"
    parser.add_argument("--status", type=Path, default=collection_root / "prospective_collection_status.json")
    parser.add_argument("--source-root", type=Path, default=PROJECT_ROOT / "data_cache" / "sector_history")
    parser.add_argument("--output-root", type=Path, default=collection_root / "frozen_oos")
    parser.add_argument(
        "--model-root",
        type=Path,
        default=PROJECT_ROOT / "models" / "paper_shadow" / "industry_sector_ml_shadow" / "frozen_oos",
    )
    parser.add_argument("--event-adjustment-manifest", type=Path)
    args = parser.parse_args()
    report = run_frozen_oos_evaluation(
        args.status,
        args.source_root,
        args.output_root,
        args.model_root,
        event_adjustment_manifest=args.event_adjustment_manifest,
    )
    readiness = args.output_root / "frozen_oos_evaluation_readiness.json"
    _loaded, sha256 = load_strict_json_with_sha256(readiness)
    print(
        f"status={report['status']} ready={report.get('ready', False)} "
        f"training={report.get('candidate_model_training_run', False)} sha256={sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
