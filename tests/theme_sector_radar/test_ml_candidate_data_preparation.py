from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from theme_sector_radar.ml.candidate_data_preparation import (
    FEATURE_SCHEMA_CONTRACT_VERSION,
    PREPARATION_SCHEMA_VERSION,
    SOURCE_INVENTORY_SCHEMA_VERSION,
    validate_candidate_data_preparation_artifacts,
)
from theme_sector_radar.reporting.strict_json import load_strict_json
from theme_sector_radar.reporting.strict_json import write_strict_json_atomic


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREPARATION_ROOT = (
    PROJECT_ROOT
    / "reports"
    / "paper_shadow"
    / "ml_stock_ranker"
    / "candidate_data_preparation_v2_20260720"
)


def test_candidate_data_preparation_artifacts_are_source_bound_and_blocked():
    summary = validate_candidate_data_preparation_artifacts(PREPARATION_ROOT)
    assert summary == {
        "v9_candidate_dates": 99,
        "v9_candidate_rows": 1730,
        "physical_candidate_source_dates": 160,
        "extra_candidate_source_dates": 61,
        "strict_direction_rows": 0,
        "strict_linkage_rows": 0,
    }
    inventory = load_strict_json(PREPARATION_ROOT / "source_inventory.json")
    schema = load_strict_json(PREPARATION_ROOT / "schema_contract.json")
    coverage = load_strict_json(PREPARATION_ROOT / "coverage_report.json")
    assert inventory["schema_version"] == SOURCE_INVENTORY_SCHEMA_VERSION
    assert schema["schema_version"] == FEATURE_SCHEMA_CONTRACT_VERSION
    assert coverage["schema_version"] == PREPARATION_SCHEMA_VERSION
    assert inventory["candidate_archive"]["v9_manifest_file_count"] == 99
    assert inventory["candidate_archive"]["extra_valid_row_count"] == 1072
    assert inventory["candidate_archive"]["v9_complete_intraday_bar_rows"] == 1353
    assert inventory["direction_source"]["exact_name_observed_rows"] == 675
    assert inventory["direction_source"]["strict_pit_eligible"] is False
    assert inventory["linkage_v2"]["candidate_date_overlap_count"] == 0
    assert schema["future_comparison_design"]["promotion_policy"]
    assert coverage["future_comparison_ready"] is False


def test_candidate_preparation_rejects_tampered_logical_sha(tmp_path):
    source = load_strict_json(PREPARATION_ROOT / "source_inventory.json")
    source["candidate_archive"]["physical_file_count"] += 1
    from theme_sector_radar.ml.contract import canonical_sha256

    core = {
        key: value
        for key, value in source.items()
        if key not in {"source_inventory_sha256", "disclaimer"}
    }
    assert source["source_inventory_sha256"] != canonical_sha256(core)
    for name in ("schema_contract.json", "coverage_report.json"):
        shutil.copy2(PREPARATION_ROOT / name, tmp_path / name)
    write_strict_json_atomic(tmp_path / "source_inventory.json", source)
    with pytest.raises(ValueError):
        validate_candidate_data_preparation_artifacts(tmp_path)
