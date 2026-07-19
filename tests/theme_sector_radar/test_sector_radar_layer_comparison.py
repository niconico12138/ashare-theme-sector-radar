import copy
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

import scripts.compare_sector_radar_layers as comparison_script
from theme_sector_radar.backtest.sector_radar_layer_comparison import (
    compare_sector_radar_layers,
    write_layer_comparison_report,
)
from theme_sector_radar.reporting.strict_json import load_strict_json
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)


def _sample(
    as_of_date: str,
    sector_index: int,
    *,
    formal_score: float,
    direction_score: float,
    returns: dict[str, float],
) -> dict:
    return {
        "as_of_date": as_of_date,
        "sector_id": f"S{sector_index}",
        "sector_name": f"行业{sector_index}",
        "feature_max_date": as_of_date,
        "forward_returns": returns,
        "forward_label_dates": {
            "1d": "2026-02-10",
            "3d": "2026-02-12",
            "5d": "2026-02-14",
            "10d": "2026-02-19",
        },
        "radar_base_score": formal_score,
        "trend_continuation_score": formal_score - 1.0,
        "short_term_burst_score": formal_score - 2.0,
        "score_breakdowns": {
            "radar_base_score": {
                "data_quality": 4.0,
                "price_change_available": True,
                "trend_history_status": "ok",
                "risk_breakdown": {"risk_level": "low"},
                "three_layer_shadow": {
                    "direction_score_shadow": direction_score,
                },
            }
        },
    }


def _sample_manifest_sha(samples: list[dict]) -> str:
    identity = [
        {
            "as_of_date": sample["as_of_date"],
            "sector_id": sample["sector_id"],
            "feature_max_date": sample["feature_max_date"],
            "radar_base_score": sample["radar_base_score"],
            "trend_continuation_score": sample["trend_continuation_score"],
            "short_term_burst_score": sample["short_term_burst_score"],
            "three_layer_shadow": sample["score_breakdowns"]["radar_base_score"][
                "three_layer_shadow"
            ],
        }
        for sample in samples
    ]
    return hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _dataset(date_count: int = 3) -> dict:
    samples = []
    for date_index in range(date_count):
        as_of_date = f"2026-02-{2 + date_index:02d}"
        for sector_index in range(8):
            samples.append(
                _sample(
                    as_of_date,
                    sector_index,
                    formal_score=100.0 - sector_index,
                    direction_score=float(sector_index * 10),
                    returns={
                        "1d": float(sector_index - 3),
                        "3d": float(sector_index - 2),
                        "5d": float(sector_index - 1),
                        "10d": float(sector_index),
                    },
                )
            )
    documents = [{"relative_path": "industry/test.json", "sha256": "a" * 64}]
    source_sha = hashlib.sha256(
        json.dumps(
            documents,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    sample_sha = _sample_manifest_sha(samples)
    return {
        "source_manifest": {
            "document_count": 1,
            "documents": documents,
            "manifest_sha256": source_sha,
        },
        "samples": samples,
        "provenance_audit": {
            "sample_manifest_sha256": sample_sha,
            "feature_date_violation_count": 0,
            "universe_vintage_lookahead_eliminated": False,
        },
    }


def test_comparison_preregisters_groups_and_keeps_selection_independent_of_labels():
    dataset = _dataset()
    dataset["samples"][0].update(
        {
            "final_score": 1.0,
            "v2_score": 2.0,
            "selection_score": 3.0,
            "selection_score_adjusted": 4.0,
        }
    )
    before = copy.deepcopy(dataset)
    report = compare_sector_radar_layers(
        dataset,
        top_ks=(3,),
        direction_thresholds=(55.0,),
        horizons=(1, 3, 5, 10),
    )
    changed_labels = copy.deepcopy(dataset)
    for sample in changed_labels["samples"]:
        sample["forward_returns"] = {
            key: -value for key, value in sample["forward_returns"].items()
        }
    changed = compare_sector_radar_layers(
        changed_labels,
        top_ks=(3,),
        direction_thresholds=(55.0,),
        horizons=(1, 3, 5, 10),
    )

    assert report["mode"] == "paper_shadow_research_only"
    assert report["strict_pit_eligible"] is False
    assert report["preregistration"]["groups"]["C"]["formal_admission"] == (
        "top_25_percent_within_common_eligible_universe"
    )
    assert report["selection_manifest_sha256"] == changed["selection_manifest_sha256"]
    assert hashlib.sha256(
        json.dumps(
            report["selection_manifest"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest() == report["selection_manifest_sha256"]
    assert {result["group"] for result in report["results"]} == {"A", "B", "C", "D"}
    assert report["provenance"]["cluster_map_completeness_status"] == (
        "partial_unmapped_sectors_treated_as_self_clusters"
    )
    assert report["formal_baseline_status"] == (
        "historical_pit_reconstruction_proxy_not_full_formal_score"
    )
    assert dataset == before


def test_missing_future_label_does_not_change_selection_manifest():
    dataset = _dataset()
    baseline = compare_sector_radar_layers(
        dataset,
        top_ks=(3,),
        direction_thresholds=(55.0,),
        horizons=(1, 3, 5, 10),
    )
    missing = copy.deepcopy(dataset)
    missing["samples"][0]["forward_returns"]["5d"] = None
    missing["samples"][0]["forward_label_dates"]["5d"] = None

    changed = compare_sector_radar_layers(
        missing,
        top_ks=(3,),
        direction_thresholds=(55.0,),
        horizons=(1, 3, 5, 10),
    )

    assert changed["selection_manifest_sha256"] == baseline["selection_manifest_sha256"]
    assert changed["coverage"]["incomplete_common_label_row_count"] == 1


def test_comparison_rejects_unverified_source_or_sample_manifest():
    dataset = _dataset()
    dataset["source_manifest"]["manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source manifest SHA"):
        compare_sector_radar_layers(dataset)

    dataset = _dataset()
    dataset["provenance_audit"]["sample_manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="sample manifest SHA"):
        compare_sector_radar_layers(dataset)


def test_comparison_uses_common_dates_and_reports_d_threshold_gaps_without_dropping_them():
    report = compare_sector_radar_layers(
        _dataset(),
        top_ks=(3,),
        direction_thresholds=(95.0,),
        horizons=(1, 3, 5, 10),
    )
    by_group = {result["group"]: result for result in report["results"]}

    assert report["coverage"]["common_date_count"] == 3
    assert by_group["A"]["selection"]["selected_candidate_count"] == 9
    assert by_group["C"]["selection"]["formal_admission_count"] == 6
    assert by_group["D"]["selection"]["zero_candidate_date_count"] == 3
    assert by_group["D"]["horizons"]["3d"]["label_date_coverage_ratio"] == 0.0
    assert by_group["D"]["horizons"]["3d"]["paired_vs_a"]["missing_pair_date_count"] == 3


def test_comparison_reports_universe_return_on_the_same_dates_as_each_candidate_path():
    dataset = _dataset()
    for sample in dataset["samples"]:
        date_offset = int(sample["as_of_date"][-2:]) - 2
        sample["forward_returns"] = {
            key: value + date_offset * 10.0
            for key, value in sample["forward_returns"].items()
        }
        if sample["sector_id"] == "S0" and sample["as_of_date"] == "2026-02-02":
            sample["score_breakdowns"]["radar_base_score"]["three_layer_shadow"][
                "direction_score_shadow"
            ] = 100.0
    dataset["provenance_audit"]["sample_manifest_sha256"] = _sample_manifest_sha(
        dataset["samples"]
    )
    report = compare_sector_radar_layers(
        dataset,
        top_ks=(3,),
        direction_thresholds=(95.0,),
        horizons=(1, 3, 5, 10),
    )
    result = next(item for item in report["results"] if item["group"] == "D")
    metrics = result["horizons"]["3d"]

    assert metrics["effective_date_count"] == 1
    assert round(
        metrics["mean_daily_candidate_return_pct"]
        - metrics["mean_daily_universe_return_pct"],
        8,
    ) == metrics["mean_daily_excess_return_pct"]


def test_comparison_requires_sixty_dates_and_all_predeclared_gates_for_promotion():
    report = compare_sector_radar_layers(
        _dataset(date_count=3),
        top_ks=(3,),
        direction_thresholds=(55.0,),
        horizons=(1, 3, 5, 10),
    )

    assert report["promotion_status"] == "insufficient_evidence"
    assert "fewer_than_60_effective_dates" in report["promotion_assessment"]["blocking_reasons"]
    assert report["promotion_assessment"]["recommended_architecture"] == (
        "maintain_current_formal_plus_shadow"
    )


def test_comparison_report_writes_strict_json_and_markdown(tmp_path: Path):
    report = compare_sector_radar_layers(
        _dataset(),
        top_ks=(3,),
        direction_thresholds=(55.0,),
        horizons=(1, 3, 5, 10),
    )

    json_path, markdown_path = write_layer_comparison_report(report, tmp_path)

    loaded = load_strict_json(json_path)
    assert loaded["selection_manifest_sha256"] == report["selection_manifest_sha256"]
    assert "Paper/shadow research only" in markdown_path.read_text(encoding="utf-8")
    assert json.loads(json_path.read_text(encoding="utf-8"))["broker_connection"] is False
    validate_no_executable_instructions(loaded, context="sector layer comparison")
    with pytest.raises(ValueError, match="broker_connection"):
        validate_no_executable_instructions(
            {"broker_connection": True}, context="positive broker audit"
        )


def test_cli_freezes_preregistration_before_building_and_writing_results(
    tmp_path: Path, monkeypatch
):
    history_root = tmp_path / "history"
    industry_root = history_root / "industry"
    industry_root.mkdir(parents=True)
    start = date(2026, 1, 1)
    for index, name in enumerate(("行业A", "行业B")):
        records = []
        for offset in range(45):
            close = 100.0 + offset * (1.0 if index == 0 else 0.5)
            records.append(
                {
                    "日期": (start + timedelta(days=offset)).isoformat(),
                    "收盘价": close,
                    "成交额": 100_000_000 + offset,
                }
            )
        (industry_root / f"{name}.json").write_text(
            json.dumps(
                {
                    "sector_name": name,
                    "sector_code": f"TEST{index}",
                    "source": "test",
                    "records": records,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    cluster_path = tmp_path / "clusters.json"
    cluster_path.write_text(json.dumps({"clusters": {}}), encoding="utf-8")
    output_root = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compare_sector_radar_layers.py",
            "--history-root",
            str(history_root),
            "--cluster-map",
            str(cluster_path),
            "--output-root",
            str(output_root),
        ],
    )

    assert comparison_script.main() == 0

    frozen = next(output_root.glob("sector_radar_layer_comparison_preregistration_*.json"))
    report_path = next(output_root.glob("sector_radar_layer_comparison_*/sector_radar_layer_comparison.json"))
    report = load_strict_json(report_path)
    assert frozen.stat().st_mtime_ns <= report_path.stat().st_mtime_ns
    assert report["provenance"]["preregistration_freeze_stage"] == (
        "before_dataset_build"
    )
    assert report["provenance"]["frozen_preregistration_path"] == str(
        frozen.resolve()
    )
