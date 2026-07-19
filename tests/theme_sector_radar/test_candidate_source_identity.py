import gc
import importlib
import hashlib
import json
import weakref
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.rebuild_intraday_candidates_from_complete_1m import rebuild_trusted_candidate_root


def _bars(day="2026-03-03"):
    base = datetime.strptime(day, "%Y-%m-%d")
    times = []
    current = base.replace(hour=9, minute=30)
    while current <= base.replace(hour=11, minute=30):
        times.append(current)
        current += timedelta(minutes=1)
    current = base.replace(hour=13, minute=1)
    while current <= base.replace(hour=15, minute=0):
        times.append(current)
        current += timedelta(minutes=1)
    return [
        {
            "time": value.strftime("%Y%m%d%H%M%S"),
            "open": 10.0,
            "high": 10.1,
            "low": 9.9,
            "close": 10.0,
            "amount": 100.0,
            "volume": 10.0,
        }
        for value in times
    ]


def _derived_root(tmp_path, target_interval):
    source_root = tmp_path / "source"
    source_path = source_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        json.dumps(
            {
                "as_of": "2026-03-03",
                "candidates": [
                    {
                        "code": "000001",
                        "name": "sample",
                        "source_pool": "original",
                        "intraday_bars": _bars(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / f"derived-{target_interval}"
    rebuild_trusted_candidate_root(
        source_root=source_root,
        output_root=output_root,
        start="2026-03-03",
        end="2026-03-03",
        target_interval=target_interval,
    )
    return output_root


def _records_identity(root, timeframe="1m", source_root=None):
    return {
        "status": "validated",
        "candidate_root": str(root),
        "source_root": str(source_root or root.parent / "source"),
        "bar_interval": timeframe,
        "bar_source": {
            "1m": "complete_1m_session",
            "5m": "aggregated_from_complete_1m_session",
        }[timeframe],
        "manifest_sha256": "a" * 64,
    }


@pytest.mark.parametrize(
    ("timeframe", "bar_source"),
    [("1m", "complete_1m_session"), ("5m", "aggregated_from_complete_1m_session")],
)
def test_candidate_root_identity_accepts_only_source_addressed_derived_documents(tmp_path, timeframe, bar_source):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, timeframe)

    identity = module.validate_candidate_root_identity(
        root,
        source_root=tmp_path / "source",
        timeframe=timeframe,
        start="2026-03-03",
        end="2026-03-03",
    )

    assert identity["status"] == "validated"
    assert identity["bar_source"] == bar_source
    assert identity["document_count"] == 1
    assert identity["complete_candidate_count"] == 1
    assert identity["document_dates"] == ["2026-03-03"]
    assert identity["complete_candidate_dates"] == ["2026-03-03"]
    assert len(identity["manifest_sha256"]) == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_1m_bar_count", -1),
        ("bar_count", 1),
        ("invalid_reason", "fabricated_reason"),
    ],
)
def test_candidate_root_identity_reconciles_invalid_metadata_with_bound_source(
    tmp_path,
    field,
    value,
):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    source_root = tmp_path / "source"
    source_path = source_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        json.dumps(
            {
                "as_of": "2026-03-03",
                "candidates": [
                    {
                        "code": "000001",
                        "name": "sample",
                        "source_pool": "original",
                        "intraday_bars": _bars()[:-1],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "derived-1m"
    rebuild_trusted_candidate_root(
        source_root=source_root,
        output_root=output_root,
        start="2026-03-03",
        end="2026-03-03",
        target_interval="1m",
    )
    derived_path = output_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    document = json.loads(derived_path.read_text(encoding="utf-8"))
    document["candidates"][0]["intraday_bar_identity"][field] = value
    derived_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid candidate identity"):
        module.validate_candidate_root_identity(
            output_root,
            source_root=source_root,
            timeframe="1m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_candidate_root_identity_rejects_payload_date_mismatching_directory(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    source_path = tmp_path / "source" / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    derived_path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    derived = json.loads(derived_path.read_text(encoding="utf-8"))
    source["as_of"] = "2026-03-02"
    derived["as_of"] = "2026-03-02"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    derived["intraday_bar_identity"]["source_sha256"] = hashlib.sha256(
        source_path.read_bytes()
    ).hexdigest()
    derived_path.write_text(json.dumps(derived), encoding="utf-8")

    with pytest.raises(ValueError, match="payload date"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe="1m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_candidate_root_identity_rejects_non_date_directory_with_target_file(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    invalid_dir = root / "zzz"
    invalid_dir.mkdir()
    (invalid_dir / "top30_candidates.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="candidate directory date"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe="1m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_candidate_root_identity_hashes_the_derived_bytes_it_parsed(tmp_path, monkeypatch):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    expected = module.validate_candidate_root_identity(
        root,
        source_root=tmp_path / "source",
        timeframe="1m",
        start="2026-03-03",
        end="2026-03-03",
    )
    first_bytes = path.read_bytes()
    replacement = json.loads(first_bytes.decode("utf-8"))
    replacement["unused_research_note"] = "replacement"
    original_load = module.load_confined_strict_json_snapshot

    def load_then_replace(source, *, root):
        payload, digest, resolved_path = original_load(source, root=root)
        if Path(source) == path:
            path.write_text(json.dumps(replacement), encoding="utf-8")
        return payload, digest, resolved_path

    path.write_bytes(first_bytes)
    monkeypatch.setattr(
        module,
        "load_confined_strict_json_snapshot",
        load_then_replace,
    )

    actual = module.validate_candidate_root_identity(
        root,
        source_root=tmp_path / "source",
        timeframe="1m",
        start="2026-03-03",
        end="2026-03-03",
    )

    assert actual == expected


def test_candidate_identity_exposes_the_exact_documents_it_hashed(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    snapshots = {}

    module.validate_candidate_root_identity(
        root,
        source_root=tmp_path / "source",
        timeframe="1m",
        start="2026-03-03",
        end="2026-03-03",
        document_snapshots=snapshots,
    )
    replacement = json.loads(path.read_text(encoding="utf-8"))
    replacement["unused_research_note"] = "replacement"
    path.write_text(json.dumps(replacement), encoding="utf-8")

    assert "unused_research_note" not in snapshots[path]


def test_candidate_identity_releases_documents_when_snapshots_are_not_requested(
    tmp_path,
    monkeypatch,
):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    source_root = tmp_path / "source"
    for day in ("2026-03-03", "2026-03-04", "2026-03-05"):
        source_path = source_root / day / "top30_candidates.intraday_backfilled.json"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            json.dumps(
                {
                    "as_of": day,
                    "candidates": [
                        {
                            "code": "000001",
                            "name": "sample",
                            "source_pool": "original",
                            "intraday_bars": _bars(day),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    derived_root = tmp_path / "derived-1m"
    rebuild_trusted_candidate_root(
        source_root=source_root,
        output_root=derived_root,
        start="2026-03-03",
        end="2026-03-05",
        target_interval="1m",
    )

    class TrackedDocument(dict):
        pass

    original_load = module.load_confined_strict_json_snapshot
    document_refs = []
    released_before_third_document = []
    derived_root_resolved = derived_root.resolve()

    def tracked_load(path, *, root):
        data, digest, resolved_path = original_load(path, root=root)
        source = Path(path).resolve()
        if source.is_relative_to(derived_root_resolved):
            if len(document_refs) == 2:
                gc.collect()
                released_before_third_document.append(document_refs[0]() is None)
            data = TrackedDocument(data)
            document_refs.append(weakref.ref(data))
        return data, digest, resolved_path

    monkeypatch.setattr(module, "load_confined_strict_json_snapshot", tracked_load)

    identity = module.validate_candidate_root_identity(
        derived_root,
        source_root=source_root,
        timeframe="1m",
        start="2026-03-03",
        end="2026-03-05",
    )

    assert identity["document_count"] == 3
    assert released_before_third_document == [True]


def test_candidate_identity_exposes_shared_source_snapshot_without_changing_identity(
    tmp_path,
):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    source_snapshots = {}
    identities = {}
    roots = {"1m": _derived_root(tmp_path, "1m")}
    roots["5m"] = tmp_path / "derived-5m"
    rebuild_trusted_candidate_root(
        source_root=tmp_path / "source",
        output_root=roots["5m"],
        start="2026-03-03",
        end="2026-03-03",
        target_interval="5m",
    )
    for timeframe, root in roots.items():
        source_snapshot = {}
        identities[timeframe] = module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe=timeframe,
            start="2026-03-03",
            end="2026-03-03",
            source_snapshot_identity=source_snapshot,
        )
        source_snapshots[timeframe] = source_snapshot

    assert source_snapshots["1m"] == source_snapshots["5m"]
    assert source_snapshots["1m"]["document_dates"] == ["2026-03-03"]
    assert len(source_snapshots["1m"]["manifest_sha256"]) == 64
    assert "source_snapshot_identity" not in identities["1m"]


def test_candidate_identity_rejects_unbound_source_bar_security_hash(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["candidates"][0]["intraday_bar_identity"].pop(
        "source_security_bars_sha256", None
    )
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="source bar security identity"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe="1m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_candidate_root_identity_rejects_source_root_equal_to_derived_root(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")

    with pytest.raises(ValueError, match="source root.*derived root"):
        module.validate_candidate_root_identity(
            root,
            source_root=root,
            timeframe="1m",
        )


def test_candidate_root_identity_requires_caller_bound_source_root(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")

    with pytest.raises(ValueError, match="source path.*source root"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "different-source",
            timeframe="1m",
        )


def test_candidate_root_identity_counts_empty_candidate_document_as_source_date(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    source_root = tmp_path / "source"
    complete_path = source_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    empty_path = source_root / "2026-03-04" / "top30_candidates.intraday_backfilled.json"
    complete_path.parent.mkdir(parents=True)
    empty_path.parent.mkdir(parents=True)
    complete_path.write_text(
        json.dumps(
            {
                "as_of": "2026-03-03",
                "candidates": [
                    {"code": "000001", "name": "sample", "intraday_bars": _bars()}
                ],
            }
        ),
        encoding="utf-8",
    )
    empty_path.write_text(json.dumps({"as_of": "2026-03-04", "candidates": []}), encoding="utf-8")
    output_root = tmp_path / "derived"
    rebuild_trusted_candidate_root(
        source_root=source_root,
        output_root=output_root,
        start="2026-03-03",
        end="2026-03-04",
        target_interval="1m",
    )

    identity = module.validate_candidate_root_identity(
        output_root,
        source_root=source_root,
        timeframe="1m",
    )

    assert identity["document_dates"] == ["2026-03-03", "2026-03-04"]
    assert identity["complete_candidate_dates"] == ["2026-03-03"]


def test_candidate_root_identity_rejects_legacy_native_5m_document(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = tmp_path / "legacy"
    path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"as_of": "2026-03-03", "candidates": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="identity"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe="5m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_candidate_root_identity_rejects_5m_bars_not_rederived_from_bound_1m_source(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "5m")
    path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["candidates"][0]["intraday_bars"][0]["amount"] += 1.0
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="derived bars"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe="5m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_candidate_root_identity_rejects_factor_not_recomputed_from_bound_bars(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["candidates"][0]["open_to_midday_resilience_score"] = 0.0
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="derived factor"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe="1m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_candidate_root_identity_rejects_non_derived_field_changed_from_source(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["candidates"][0]["source_pool"] = "tampered"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="inherited fields"):
        module.validate_candidate_root_identity(
            root,
            source_root=tmp_path / "source",
            timeframe="1m",
            start="2026-03-03",
            end="2026-03-03",
        )


def test_records_candidate_source_identity_accepts_matching_validated_root(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = tmp_path / "trusted"

    identity = module.validate_records_candidate_source_identity(
        _records_identity(root, "5m"),
        candidate_root=root,
        source_root=tmp_path / "source",
        timeframe="5m",
        context="profit records",
    )

    assert identity["status"] == "validated"
    assert identity["candidate_root"] == str(root)
    assert identity["bar_source"] == "aggregated_from_complete_1m_session"


def test_records_candidate_source_identity_revalidates_current_root_manifest(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    recorded = module.validate_candidate_root_identity(
        root,
        source_root=tmp_path / "source",
        timeframe="1m",
        start="2026-03-03",
        end="2026-03-03",
    )

    current = module.revalidate_records_candidate_source_identity(
        recorded,
        candidate_root=root,
        source_root=tmp_path / "source",
        timeframe="1m",
        start="2026-03-03",
        end="2026-03-03",
        context="entry records",
    )

    assert current["manifest_sha256"] == recorded["manifest_sha256"]


def test_records_candidate_source_identity_rejects_stale_manifest_after_root_change(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = _derived_root(tmp_path, "1m")
    recorded = module.validate_candidate_root_identity(
        root,
        source_root=tmp_path / "source",
        timeframe="1m",
        start="2026-03-03",
        end="2026-03-03",
    )
    recorded["manifest_sha256"] = "b" * 64

    with pytest.raises(ValueError, match="manifest"):
        module.revalidate_records_candidate_source_identity(
            recorded,
            candidate_root=root,
            source_root=tmp_path / "source",
            timeframe="1m",
            start="2026-03-03",
            end="2026-03-03",
            context="profit records",
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("status", "unchecked", "status"),
        ("bar_interval", "5m", "timeframe"),
        ("bar_source", "native_1m_unverified", "bar source"),
        ("manifest_sha256", "short", "manifest SHA"),
        ("candidate_root", "wrong-root", "candidate root"),
    ],
)
def test_records_candidate_source_identity_fails_closed_on_mismatch(tmp_path, field, value, match):
    module = importlib.import_module("theme_sector_radar.timing.candidate_source_identity")
    root = tmp_path / "trusted"
    identity = _records_identity(root)
    identity[field] = value

    with pytest.raises(ValueError, match=match):
        module.validate_records_candidate_source_identity(
            identity,
            candidate_root=root,
            source_root=tmp_path / "source",
            timeframe="1m",
            context="entry records",
        )
