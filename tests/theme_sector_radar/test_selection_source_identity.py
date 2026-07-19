import importlib
import json
from pathlib import Path

import pytest

from theme_sector_radar.timing.selection_source_identity import (
    revalidate_records_selection_source_identity,
    validate_selection_source_identity,
)
from scripts.audit_timing_strategy_overfit import _load_samples


def _write_selection(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "as_of": path.parent.name,
                "per_stock": [{"code": "600001", "next_return_pct": value}],
            }
        ),
        encoding="utf-8",
    )


def test_selection_source_identity_builds_content_manifest(tmp_path):
    root = tmp_path / "selection"
    _write_selection(root / "2026-07-01" / "next_day_selection_validation.json", 1.0)
    _write_selection(root / "2026-07-03" / "next_day_selection_validation.json", -1.0)

    identity = validate_selection_source_identity(
        root,
        start="2026-07-01",
        end="2026-07-03",
    )

    assert identity["status"] == "validated"
    assert identity["selection_validation_root"] == str(root)
    assert identity["document_count"] == 2
    assert identity["document_dates"] == ["2026-07-01", "2026-07-03"]
    assert identity["start"] == "2026-07-01"
    assert identity["end"] == "2026-07-03"
    assert len(identity["manifest_sha256"]) == 64


def test_selection_source_identity_rejects_payload_date_mismatching_directory(tmp_path):
    root = tmp_path / "selection"
    path = root / "2026-07-01" / "next_day_selection_validation.json"
    _write_selection(path, 1.0)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["as_of"] = "2026-07-02"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="payload date"):
        validate_selection_source_identity(
            root,
            start="2026-07-01",
            end="2026-07-03",
        )


def test_selection_source_identity_rejects_changed_document(tmp_path):
    root = tmp_path / "selection"
    path = root / "2026-07-01" / "next_day_selection_validation.json"
    _write_selection(path, 1.0)
    recorded = validate_selection_source_identity(
        root,
        start="2026-07-01",
        end="2026-07-01",
    )

    _write_selection(path, 9.0)

    with pytest.raises(ValueError, match="selection source manifest SHA mismatch"):
        revalidate_records_selection_source_identity(
            recorded,
            selection_validation_root=root,
            start="2026-07-01",
            end="2026-07-01",
            context="paper records",
        )


def test_selection_source_identity_hashes_the_bytes_it_parsed(tmp_path, monkeypatch):
    root = tmp_path / "selection"
    path = root / "2026-07-01" / "next_day_selection_validation.json"
    _write_selection(path, 1.0)
    expected = validate_selection_source_identity(
        root,
        start="2026-07-01",
        end="2026-07-01",
    )
    first_bytes = path.read_bytes()
    module = importlib.import_module("theme_sector_radar.timing.selection_source_identity")
    original_load = module.load_confined_strict_json_snapshot

    def load_then_replace(source, *, root):
        payload, digest, resolved_path = original_load(source, root=root)
        if Path(source) == path:
            _write_selection(path, 9.0)
        return payload, digest, resolved_path

    path.write_bytes(first_bytes)
    monkeypatch.setattr(
        module,
        "load_confined_strict_json_snapshot",
        load_then_replace,
    )

    actual = validate_selection_source_identity(
        root,
        start="2026-07-01",
        end="2026-07-01",
    )

    assert actual == expected


def test_selection_identity_exposes_the_exact_documents_it_hashed(tmp_path):
    root = tmp_path / "selection"
    path = root / "2026-07-01" / "next_day_selection_validation.json"
    _write_selection(path, 1.0)
    snapshots = {}

    validate_selection_source_identity(
        root,
        start="2026-07-01",
        end="2026-07-01",
        document_snapshots=snapshots,
    )
    _write_selection(path, 9.0)

    assert snapshots["2026-07-01"]["per_stock"][0]["next_return_pct"] == 1.0


def test_sample_loader_consumes_bound_candidate_and_selection_snapshots(tmp_path, monkeypatch):
    candidate_root = tmp_path / "candidates"
    candidate_path = candidate_root / "2026-07-01" / "top30_candidates.json"
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text("{}", encoding="utf-8")
    candidate_snapshots = {
        candidate_path: {
            "candidates": [{"code": "600001", "name": "bound", "forward_return_pct": None}]
        }
    }
    selection_snapshots = {
        "2026-07-01": {
            "per_stock": [{"code": "600001", "next_return_pct": 1.25}]
        }
    }
    monkeypatch.setattr(
        "scripts.audit_timing_strategy_overfit._load_json",
        lambda *_args, **_kwargs: pytest.fail("bound sample loader must not reopen JSON files"),
    )

    samples = _load_samples(
        candidate_root,
        "2026-07-01",
        "2026-07-01",
        tmp_path / "selection",
        candidate_snapshots,
        selection_snapshots,
    )

    assert samples[0]["forward_return_pct"] == 1.25


def test_selection_source_identity_fails_closed_without_documents(tmp_path):
    with pytest.raises(ValueError, match="selection source identity cannot be validated"):
        validate_selection_source_identity(
            tmp_path / "selection",
            start="2026-07-01",
            end="2026-07-03",
        )


def test_selection_source_identity_ignores_non_dated_auxiliary_directories(tmp_path):
    root = tmp_path / "selection"
    _write_selection(root / "2026-07-01" / "next_day_selection_validation.json", 1.0)
    (root / "aggregate" / "2026-07-01_to_2026-07-03").mkdir(parents=True)

    identity = validate_selection_source_identity(
        root,
        start="2026-07-01",
        end="2026-07-03",
    )

    assert identity["document_dates"] == ["2026-07-01"]
