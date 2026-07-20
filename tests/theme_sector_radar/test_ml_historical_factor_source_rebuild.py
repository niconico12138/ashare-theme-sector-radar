from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from theme_sector_radar.ml.contract import canonical_sha256
from theme_sector_radar.ml.historical_factor_source_rebuild import (
    CLASSIFICATION,
    FORBIDDEN_FIELDS,
    SOURCE_DATASET_SCHEMA_VERSION,
    match_candidate_factor_sources,
    validate_source_rebuilt_dataset,
    write_historical_factor_source_rebuild,
)
from theme_sector_radar.ml.historical_iteration_extension import (
    FEATURE_INVENTORY_SCHEMA_VERSION,
    _rotate_labels,
    _validate_source_gate,
    extension_specs,
    validate_historical_iteration_artifact_directory,
)
from theme_sector_radar.ml.registry import load_model_bundle
from theme_sector_radar.ml.schema import DISCLAIMER, MODE
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    write_strict_json_atomic,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _safe_flags() -> dict[str, bool]:
    return {
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }


def _minimal_rebuilt_artifact() -> dict:
    core = {
        "schema_version": SOURCE_DATASET_SCHEMA_VERSION,
        "mode": MODE,
        "status": "blocked_insufficient_strict_pit_coverage",
        "dataset_classification": CLASSIFICATION,
        "counts": {"candidate_rows": 1},
        "records": [
            {
                "stock_code": "000001",
                "direction": {
                    "source": {
                        "report_path": "direction.json",
                        "report_sha256": "a" * 64,
                        "history_manifest_sha256": "b" * 64,
                    },
                    "usable_value": None,
                },
                "linkage_v2": {"usable_value": None},
                "excluded_reason": ["linkage_v2_no_exact_as_of_source"],
            }
        ],
        **_safe_flags(),
    }
    return {
        **core,
        "source_rebuilt_dataset_sha256": canonical_sha256(core),
        "disclaimer": DISCLAIMER,
    }


def test_exact_direction_name_remains_ineligible_when_semantics_and_pit_fail():
    candidate = {
        "as_of_date": "2026-05-06",
        "stock_code": "000001",
        "board_identities": [
            {"name": "sector-a", "type": "concept", "source": "candidate_archive"}
        ],
    }
    direction = {
        ("2026-05-06", "sector-a"): {
            "sector_name": "sector-a",
            "sector_id": "pit_industry_sector-a",
            "direction_score_shadow": 72.0,
            "time_series_score": 70.0,
            "cross_section_score": 74.0,
            "rank_momentum_score": 71.0,
            "feature_max_date": "2026-05-06",
        }
    }
    row = match_candidate_factor_sources(
        candidate,
        direction,
        direction_catalog={
            "source_strict_pit_eligible": False,
            "report": {"path": "direction.json", "sha256": "a" * 64},
            "history_manifest_sha256": "b" * 64,
        },
        linkage_by_date={},
    )
    assert row["direction"]["observed"] is True
    assert row["direction"]["usable_value"] is None
    assert row["usable_for_direction_ml"] is False
    assert row["direction"]["source"]["report_sha256"] == "a" * 64
    assert "direction_board_type_semantics_mismatch" in row["excluded_reason"]
    assert "direction_source_universe_not_point_in_time" in row["excluded_reason"]
    assert row["linkage_v2"]["usable_value"] is None


def test_rebuilt_dataset_rejects_protected_fields_and_formal_loader(tmp_path):
    artifact = _minimal_rebuilt_artifact()
    validate_source_rebuilt_dataset(artifact)
    tampered = copy.deepcopy(artifact)
    tampered["records"][0]["quant_score"] = 1.0
    with pytest.raises(ValueError, match="protected fields"):
        validate_source_rebuilt_dataset(tampered)

    write_strict_json_atomic(tmp_path / "registry.json", artifact)
    registry_sha = hashlib.sha256((tmp_path / "registry.json").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="registry schema mismatch"):
        load_model_bundle(tmp_path, expected_registry_sha256=registry_sha)


def test_round11_20_specs_are_exact_and_technical_only():
    specs = extension_specs()
    assert [spec["iteration"] for spec in specs] == list(range(11, 21))
    assert len({spec["id"] for spec in specs}) == 10
    assert {spec["axis"] for spec in specs} == {
        "purge", "window", "seed", "feature_ablation", "random_control", "complexity"
    }
    for spec in specs:
        feature_names = tuple(spec.get("feature_names") or ())
        feature_drop = tuple(spec.get("feature_drop") or ())
        assert not FORBIDDEN_FIELDS.intersection(feature_names)
        assert not FORBIDDEN_FIELDS.intersection(feature_drop)


def test_label_rotation_is_date_local_and_deterministic():
    rows = [
        {"as_of_date": "2026-01-01", "stock_code": "000002", "training_label": 2.0},
        {"as_of_date": "2026-01-01", "stock_code": "000001", "training_label": 1.0},
        {"as_of_date": "2026-01-02", "stock_code": "000003", "training_label": 3.0},
    ]
    rotated = _rotate_labels(rows)
    assert rotated == _rotate_labels(rows)
    by_identity = {(row["as_of_date"], row["stock_code"]): row for row in rotated}
    assert by_identity[("2026-01-01", "000001")]["training_label"] == 2.0
    assert by_identity[("2026-01-01", "000002")]["training_label"] == 1.0
    assert by_identity[("2026-01-02", "000003")]["training_label"] == 3.0


def test_extension_requires_zero_coverage_blocking_gate():
    core = {
        "schema_version": "ml-stock-historical-factor-source-rebuild-report-v2",
        "status": "blocked_insufficient_strict_pit_coverage",
        "incremental_direction_linkage_experiment_allowed": False,
        "counts": {
            "direction_strict_pit_eligible_rows": 0,
            "linkage_strict_pit_eligible_rows": 0,
        },
        **_safe_flags(),
    }
    gate = {**core, "rebuild_report_sha256": canonical_sha256(core)}
    _validate_source_gate(gate)
    gate["incremental_direction_linkage_experiment_allowed"] = True
    with pytest.raises(ValueError, match="blocking historical factor source gate"):
        _validate_source_gate(gate)


def test_source_rebuild_replacement_rejects_non_exact_directory(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "unexpected.txt").write_text("do not replace", encoding="utf-8")
    with pytest.raises(ValueError, match="replacement target is not exact"):
        write_historical_factor_source_rebuild(
            tmp_path / "missing-dataset.json",
            tmp_path / "missing-direction.json",
            [],
            output,
            replace_existing=True,
        )


def test_generated_source_rebuild_and_round11_20_artifacts_are_safe():
    root = PROJECT_ROOT / "reports" / "paper_shadow" / "ml_stock_ranker"
    rebuilt = load_strict_json(
        root / "historical_factor_source_rebuild_v2_20260720"
        / "source_rebuilt_dataset.json"
    )
    report = load_strict_json(
        root / "historical_factor_source_rebuild_v2_20260720" / "rebuild_report.json"
    )
    suite = load_strict_json(
        root / "historical_iterations_round11_20_v2_20260720" / "suite_report.json"
    )
    inventory = load_strict_json(
        root / "historical_iterations_round11_20_v2_20260720" / "feature_inventory.json"
    )
    validate_source_rebuilt_dataset(rebuilt)
    assert report["counts"]["candidate_rows"] == 1730
    assert report["counts"]["direction_exact_name_observed_rows"] == 675
    assert report["counts"]["direction_strict_pit_eligible_rows"] == 0
    assert report["counts"]["linkage_strict_pit_eligible_rows"] == 0
    assert report["incremental_direction_linkage_experiment_allowed"] is False
    assert suite["round_count"] == 10
    assert suite["total_iteration_count"] == 20
    assert [item["iteration"] for item in suite["rounds"]] == list(range(11, 21))
    assert all(item["status"] == "completed" for item in suite["rounds"])
    assert suite["source_rebuild_gate"]["incremental_direction_linkage_experiment_allowed"] is False
    assert all(suite[key] is False for key in _safe_flags())
    assert inventory["schema_version"] == FEATURE_INVENTORY_SCHEMA_VERSION
    assert inventory["candidate_source_count"] == 99
    assert inventory["candidate_row_count"] == 1730
    assert inventory["ranking_policy"] == "cross-sectional ranking grouped by as_of_date"
    assert "never overwrite formal ranking fields" in inventory["rule_parallel_policy"]
    selected = [row for row in inventory["features"] if row["selected_by_round11_20"]]
    assert selected
    assert all(row["approved_for_historical_ml"] for row in selected)
    assert not FORBIDDEN_FIELDS.intersection(
        row["feature_name"] for row in selected
    )
    suite_root = root / "historical_iterations_round11_20_v2_20260720"
    for round_row in suite["rounds"]:
        round_dir = suite_root / f"iteration_{round_row['iteration']:02d}_{round_row['id']}"
        verified = validate_historical_iteration_artifact_directory(round_dir)
        assert verified["iteration"] == round_row["iteration"]
        registry = load_strict_json(round_dir / "registry.json")
        assert registry["feature_input_policy"]["direction_feature_count"] == 0
        assert registry["feature_input_policy"]["linkage_v2_feature_count"] == 0
        assert registry["feature_input_policy"]["protected_feature_count"] == 0
        assert all(name.endswith("_missing") for name in registry["feature_input_policy"]["missing_indicator_names"])


def test_generated_round_registry_is_rejected_by_formal_loader():
    round_dir = (
        PROJECT_ROOT / "reports" / "paper_shadow" / "ml_stock_ranker"
        / "historical_iterations_round11_20_v2_20260720"
        / "iteration_11_long_purge_10"
    )
    registry_sha = hashlib.sha256((round_dir / "registry.json").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="registry schema mismatch"):
        load_model_bundle(round_dir, expected_registry_sha256=registry_sha)
