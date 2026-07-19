"""Evaluate same-day rule and ML stock rankings in paper/shadow mode."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow
from theme_sector_radar.ml.dataset import validate_training_dataset
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--expected-dataset-file-sha256", required=True)
    parser.add_argument("--rule-rows", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top-k", nargs="+", type=int, default=[10, 20, 30])
    parser.add_argument("--hybrid-quant-weight", type=float, default=0.65)
    parser.add_argument("--hybrid-linkage-weight", type=float, default=0.35)
    parser.add_argument("--hybrid-partial-linkage-weight", type=float, default=0.20)
    args = parser.parse_args()

    predictions, prediction_sha = load_strict_json_with_sha256(args.predictions)
    dataset, dataset_sha = load_strict_json_with_sha256(args.dataset)
    if dataset_sha != str(args.expected_dataset_file_sha256).lower():
        raise ValueError("dataset file SHA mismatch")
    validate_training_dataset(dataset)
    rules, rule_sha = load_strict_json_with_sha256(args.rule_rows)
    report = evaluate_rule_vs_ml_shadow(
        predictions,
        dataset,
        list(rules.get("records") or []),
        top_ks=tuple(args.top_k),
        baseline_strict_pit_eligible=rules.get("strict_pit_eligible"),
        hybrid_quant_weight=args.hybrid_quant_weight,
        hybrid_linkage_weight=args.hybrid_linkage_weight,
        hybrid_partial_linkage_weight=args.hybrid_partial_linkage_weight,
    )
    report["source_manifest"] = {
        "predictions": {"path": str(args.predictions), "sha256": prediction_sha},
        "dataset": {"path": str(args.dataset), "sha256": dataset_sha},
        "rule_rows": {"path": str(args.rule_rows), "sha256": rule_sha},
    }
    validate_no_executable_instructions(report, context="ML rule comparison")
    write_strict_json_atomic(args.output, report)
    print(
        f"status={report['status']} paired_dates={report['paired_date_count']} "
        f"promotion={report['promotion_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
