from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_artifact_inventory_classifies_legacy_and_current_payloads(tmp_path: Path):
    from theme_sector_radar.ml.artifact_inventory import (
        build_artifact_inventory,
        verify_artifact_inventory,
    )

    reports = tmp_path / "reports"
    models = tmp_path / "models"
    current = reports / "current.json"
    legacy = reports / "legacy.json"
    model = models / "registry.json"
    current.parent.mkdir(parents=True)
    models.mkdir(parents=True)
    current.write_text(
        json.dumps(
            {
                "schema_version": "ml-stock-data-readiness-v1",
                "mode": "paper_shadow_research_only",
                "status": "blocked",
                "live_trading_allowed": False,
                "promotion_allowed": False,
                "eligible_for_oos_claim": False,
            }
        ),
        encoding="utf-8",
    )
    legacy.write_text(
        json.dumps({"mode": "paper_shadow_research_only", "status": "ok"}),
        encoding="utf-8",
    )
    model_binary = models / "model.txt"
    model_binary.write_text("fixture model bytes", encoding="utf-8")
    import hashlib

    model.write_text(
        json.dumps(
            {
                "mode": "paper_shadow_research_only",
                "status": "ready",
                "model_artifact": {
                    "path": "model.txt",
                    "sha256": hashlib.sha256(model_binary.read_bytes()).hexdigest(),
                },
            }
        ),
        encoding="utf-8",
    )

    inventory_path = tmp_path / "inventory.json"
    inventory = build_artifact_inventory([reports, models], output_path=inventory_path)

    assert inventory["live_trading_allowed"] is False
    assert inventory["legacy_missing_live_flag_count"] == 2
    assert inventory["artifact_count"] == 4
    assert inventory["json_artifact_count"] == 3
    assert inventory["model_binary_count"] == 1
    entries = {entry["path"]: entry for entry in inventory["artifacts"]}
    assert entries["reports/current.json"]["artifact_status"] == "current_or_compatible"
    assert entries["reports/current.json"]["eligible_as_current_evidence"] is True
    assert entries["reports/legacy.json"]["artifact_status"] == "superseded_legacy"
    assert entries["reports/legacy.json"]["eligible_as_current_evidence"] is False
    assert entries["models/registry.json"]["artifact_status"] == "superseded_legacy"
    assert entries["models/model.txt"]["artifact_status"] == "bound_model_binary"

    inventory_sha = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
    verified = verify_artifact_inventory(
        inventory_path, expected_sha256=inventory_sha
    )
    assert verified["artifact_count"] == 4

    model_binary.write_text("tampered model bytes", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact SHA mismatch|registry model SHA mismatch"):
        verify_artifact_inventory(inventory_path, expected_sha256=inventory_sha)


@pytest.mark.parametrize("unsafe_value", [True, None, 0, "false"])
def test_artifact_inventory_rejects_non_false_live_flag(
    tmp_path: Path, unsafe_value: object
):
    from theme_sector_radar.ml.artifact_inventory import build_artifact_inventory

    payload = tmp_path / "unsafe.json"
    payload.write_text(
        json.dumps(
            {
                "mode": "paper_shadow_research_only",
                "status": "ok",
                "live_trading_allowed": unsafe_value,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="live_trading_allowed"):
        build_artifact_inventory([tmp_path], output_path=tmp_path / "inventory.json")


def test_artifact_inventory_rejects_non_false_promotion_flag(tmp_path: Path):
    from theme_sector_radar.ml.artifact_inventory import build_artifact_inventory

    payload = tmp_path / "unsafe.json"
    payload.write_text(
        json.dumps(
            {
                "mode": "paper_shadow_research_only",
                "status": "ok",
                "live_trading_allowed": False,
                "promotion_allowed": True,
                "eligible_for_oos_claim": False,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="promotion_allowed"):
        build_artifact_inventory([tmp_path], output_path=tmp_path / "inventory.json")


def test_artifact_inventory_requires_registry_and_model_pair(tmp_path: Path):
    import hashlib

    from theme_sector_radar.ml.artifact_inventory import (
        build_artifact_inventory,
        verify_artifact_inventory,
    )

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    model_path = model_dir / "model.txt"
    model_path.write_text("model", encoding="utf-8")
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    (model_dir / "registry.json").write_text(
        json.dumps(
            {
                "mode": "paper_shadow_research_only",
                "status": "ready",
                "live_trading_allowed": False,
                "promotion_allowed": False,
                "eligible_for_oos_claim": False,
                "model_artifact": {"path": "model.txt", "sha256": model_sha},
            }
        ),
        encoding="utf-8",
    )
    inventory_path = tmp_path / "inventory.json"
    inventory = build_artifact_inventory([model_dir], output_path=inventory_path)
    inventory_sha = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
    assert inventory["model_binary_count"] == 1

    model_path.unlink()
    with pytest.raises(ValueError, match="cover|model"):
        verify_artifact_inventory(inventory_path, expected_sha256=inventory_sha)


def test_artifact_inventory_rejects_registry_model_sha_mismatch(tmp_path: Path):
    from theme_sector_radar.ml.artifact_inventory import build_artifact_inventory

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "model.txt").write_text("model", encoding="utf-8")
    (model_dir / "registry.json").write_text(
        json.dumps(
            {
                "mode": "paper_shadow_research_only",
                "status": "ready",
                "model_artifact": {"path": "model.txt", "sha256": "0" * 64},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="model.*SHA|SHA.*model"):
        build_artifact_inventory([model_dir], output_path=tmp_path / "inventory.json")


def test_artifact_inventory_current_requires_complete_top_level_safety(tmp_path: Path):
    from theme_sector_radar.ml.artifact_inventory import build_artifact_inventory

    payload = tmp_path / "incomplete.json"
    payload.write_text(
        json.dumps(
            {
                "schema_version": "ml-stock-training-cycle-v1",
                "mode": "paper_shadow_research_only",
                "status": "blocked",
                "promotion_allowed": False,
                "live_trading_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    inventory = build_artifact_inventory(
        [payload], output_path=tmp_path / "inventory.json"
    )

    assert inventory["current_or_compatible_count"] == 0
    assert inventory["legacy_missing_live_flag_count"] == 1
    assert inventory["artifacts"][0]["eligible_as_current_evidence"] is False


def test_default_inventory_roots_include_all_ml_test_output_directories():
    from scripts.audit_ml_artifact_inventory import default_ml_artifact_roots

    names = {path.name for path in default_ml_artifact_roots(Path("project"))}
    assert "ml_shadow_relevance_demotion_fixture" in names
    assert "ml_shadow_relevance_demotion_fixture_model" in names
    assert "ml_training_cycle_iter1" in names
    assert "ml_readiness_relevance_demotion.json" in names


@pytest.mark.parametrize(
    "raw",
    [
        '{"mode":"paper_shadow_research_only","live_trading_allowed":false,"live_trading_allowed":false}',
        '{"mode":"paper_shadow_research_only","live_trading_allowed":false,"value":NaN}',
    ],
)
def test_artifact_inventory_requires_strict_json(tmp_path: Path, raw: str):
    from theme_sector_radar.ml.artifact_inventory import build_artifact_inventory

    (tmp_path / "invalid.json").write_text(raw, encoding="utf-8")

    with pytest.raises(ValueError, match="strict JSON|duplicate|non-finite"):
        build_artifact_inventory([tmp_path], output_path=tmp_path / "inventory.json")
