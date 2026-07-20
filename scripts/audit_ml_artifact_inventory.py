"""Audit and bind the identities of ML shadow artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.artifact_inventory import (
    build_artifact_inventory,
    verify_artifact_inventory,
)


def default_ml_artifact_roots(project_root: Path = PROJECT_ROOT) -> list[Path]:
    test_output = project_root / "test_output"
    fixture_roots = sorted(
        path
        for path in test_output.glob("ml_*")
        if path.is_dir()
    )
    known_fixture_roots = [
        test_output / "ml_shadow_relevance_demotion_fixture",
        test_output / "ml_shadow_relevance_demotion_fixture_model",
        test_output / "ml_training_cycle_iter1",
        test_output / "ml_training_cycle_relevance_demotion",
        test_output / "ml_readiness_relevance_demotion.json",
    ]
    top_level_ml_files = sorted(
        path for path in test_output.glob("ml_*.json") if path.is_file()
    )
    return [
        project_root / "reports" / "paper_shadow" / "ml_stock_ranker",
        project_root / "models" / "paper_shadow",
        *sorted(
            {
                path.resolve()
                for path in [
                    *known_fixture_roots,
                    *fixture_roots,
                    *top_level_ml_files,
                ]
            },
            key=lambda path: str(path).casefold(),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        dest="roots",
        help="ML artifact root; may be repeated",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "test_output" / "ml_artifact_inventory_iter1.json",
    )
    parser.add_argument("--verify-existing", action="store_true")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    if args.verify_existing:
        inventory = verify_artifact_inventory(
            args.output,
            expected_sha256=str(args.expected_sha256 or ""),
        )
        print(
            "status=verified "
            f"artifacts={inventory['artifact_count']} "
            f"legacy_superseded={inventory['legacy_missing_live_flag_count']} "
            f"current={inventory['current_or_compatible_count']} "
            f"model_binaries={inventory['model_binary_count']} "
            "live_trading_allowed=false"
        )
        return 0
    roots = args.roots or [
        path for path in default_ml_artifact_roots() if path.exists()
    ]
    inventory = build_artifact_inventory(roots, output_path=args.output)
    print(
        "status=ok "
        f"artifacts={inventory['artifact_count']} "
        f"legacy_superseded={inventory['legacy_missing_live_flag_count']} "
        f"current={inventory['current_or_compatible_count']} "
        f"model_binaries={inventory['model_binary_count']} "
        "live_trading_allowed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
