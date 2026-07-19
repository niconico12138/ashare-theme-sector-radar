#!/usr/bin/env python
"""Run the pre-registered sector-radar layer comparison in paper/shadow mode."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.backtest.sector_radar_layer_comparison import (  # noqa: E402
    compare_sector_radar_layers,
    layer_comparison_preregistration,
    write_layer_comparison_report,
)
from theme_sector_radar.backtest.sector_score_pit_validation import (  # noqa: E402
    build_pit_dataset,
)
from theme_sector_radar.reporting.strict_json import (  # noqa: E402
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _csv_ints(value: str) -> tuple[int, ...]:
    try:
        result = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not result or any(item <= 0 for item in result):
        raise argparse.ArgumentTypeError("values must be positive")
    return result


def _csv_floats(value: str) -> tuple[float, ...]:
    try:
        result = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated numbers") from exc
    if not result:
        raise argparse.ArgumentTypeError("at least one value is required")
    return result


def _freeze_preregistration(
    output_root: Path, preregistration: dict
) -> tuple[Path, str]:
    identity = str(preregistration["preregistration_sha256"])
    path = output_root / f"sector_radar_layer_comparison_preregistration_{identity}.json"
    if path.is_file():
        existing, sha256 = load_strict_json_with_sha256(path)
        if existing != preregistration:
            raise ValueError("frozen preregistration identity collision")
        return path, sha256
    write_strict_json_atomic(path, preregistration)
    existing, sha256 = load_strict_json_with_sha256(path)
    if existing != preregistration:
        raise ValueError("frozen preregistration write verification failed")
    return path, sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history-root",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "sector_history",
    )
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--top-ks", type=_csv_ints, default=(3, 5, 8))
    parser.add_argument(
        "--direction-thresholds", type=_csv_floats, default=(55.0, 60.0, 65.0)
    )
    parser.add_argument("--horizons", type=_csv_ints, default=(1, 3, 5, 10))
    parser.add_argument(
        "--cluster-map",
        type=Path,
        default=PROJECT_ROOT / "config" / "path_a_sector_clusters.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow",
    )
    args = parser.parse_args()

    preregistration = layer_comparison_preregistration(
        top_ks=args.top_ks,
        direction_thresholds=args.direction_thresholds,
        horizons=args.horizons,
    )
    frozen_preregistration_path, frozen_preregistration_sha256 = (
        _freeze_preregistration(args.output_root, preregistration)
    )
    dataset = build_pit_dataset(
        args.history_root,
        start_date=args.start_date,
        end_date=args.end_date,
        horizons=args.horizons,
        holdout_days=0,
    )
    cluster_payload, cluster_sha256 = load_strict_json_with_sha256(args.cluster_map)
    clusters = cluster_payload.get("clusters")
    if not isinstance(clusters, dict):
        raise ValueError("cluster map must contain a clusters object")
    report = compare_sector_radar_layers(
        dataset,
        top_ks=args.top_ks,
        direction_thresholds=args.direction_thresholds,
        horizons=args.horizons,
        cluster_map=clusters,
        cluster_map_sha256=cluster_sha256,
    )
    report["provenance"]["history_root"] = str(args.history_root.resolve())
    report["provenance"]["cluster_map_path"] = str(args.cluster_map.resolve())
    report["provenance"]["requested_start_date"] = args.start_date
    report["provenance"]["requested_end_date"] = args.end_date
    report["provenance"]["preregistration_freeze_stage"] = (
        "before_dataset_build"
    )
    report["provenance"]["frozen_preregistration_path"] = str(
        frozen_preregistration_path.resolve()
    )
    report["provenance"]["frozen_preregistration_file_sha256"] = (
        frozen_preregistration_sha256
    )
    start = report["coverage"]["common_start_date"]
    end = report["coverage"]["common_end_date"]
    output_dir = args.output_root / f"sector_radar_layer_comparison_{start}_to_{end}"
    preregistration_path = output_dir / "preregistered_experiment.json"
    write_strict_json_atomic(preregistration_path, preregistration)
    json_path, markdown_path = write_layer_comparison_report(report, output_dir)
    print(frozen_preregistration_path)
    print(preregistration_path)
    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
