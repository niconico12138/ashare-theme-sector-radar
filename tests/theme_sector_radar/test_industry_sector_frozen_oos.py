from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json

import pytest


def _dates(start: date, end: date):
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current.isoformat()
        current += timedelta(days=1)


def _source_root(tmp_path, *, sectors=12):
    root = tmp_path / "sector_history"
    industry = root / "industry"
    industry.mkdir(parents=True)
    days = list(_dates(date(2026, 5, 18), date(2026, 7, 16)))
    for sector_index in range(sectors):
        payload = {
            "sector_name": f"industry-{sector_index:02d}",
            "sector_type": "industry",
            "source": "unit_test_source",
            "records": [
                {
                    "date": day,
                    "close": 100.0 + sector_index + index * 0.2,
                    "volume": 1000.0 + index,
                    "amount": 100000.0 + index * 10,
                }
                for index, day in enumerate(days)
            ],
        }
        (industry / f"industry_{sector_index:02d}.json").write_text(
            json.dumps(payload, sort_keys=True), encoding="utf-8"
        )
    return root


def _append_complete_date(root, day):
    for path in (root / "industry").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        last = payload["records"][-1]
        payload["records"].append({
            "date": day,
            "close": last["close"] + 0.2,
            "volume": last["volume"] + 1,
            "amount": last["amount"] + 10,
        })
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _collection(root, output, monkeypatch):
    from theme_sector_radar.ml import industry_sector_shadow as shadow
    from theme_sector_radar.ml.industry_sector_prospective_collection import (
        collect_prospective_collection_status,
    )

    monkeypatch.setattr(shadow, "MIN_SECTORS", 10)
    return collect_prospective_collection_status(root, output)


def test_frozen_oos_blocked_never_calls_training_and_is_repeatable(tmp_path, monkeypatch):
    from theme_sector_radar.ml import industry_sector_frozen_oos as frozen

    source = _source_root(tmp_path)
    collection = tmp_path / "collection"
    _collection(source, collection, monkeypatch)
    monkeypatch.setattr(
        frozen,
        "_run_ready_evaluation",
        lambda *args, **kwargs: pytest.fail("blocked runner attempted model training"),
    )
    output = tmp_path / "evaluation"
    first = frozen.run_frozen_oos_evaluation(
        collection / "prospective_collection_status.json",
        source,
        output,
        tmp_path / "models",
    )
    first_bytes = (output / "frozen_oos_evaluation_readiness.json").read_bytes()
    second = frozen.run_frozen_oos_evaluation(
        collection / "prospective_collection_status.json",
        source,
        output,
        tmp_path / "models",
    )
    second_bytes = (output / "frozen_oos_evaluation_readiness.json").read_bytes()
    assert first["status"] == "blocked_frozen_oos_not_ready"
    assert second["candidate_model_training_run"] is False
    assert first_bytes == second_bytes
    assert not (tmp_path / "models").exists()


def test_frozen_oos_rejects_snapshot_sha_and_candidate_parameter_drift(tmp_path, monkeypatch):
    from theme_sector_radar.ml.industry_sector_frozen_oos import frozen_oos_preflight

    source = _source_root(tmp_path)
    collection = tmp_path / "collection"
    _collection(source, collection, monkeypatch)
    status_path = collection / "prospective_collection_status.json"
    snapshot_path = collection / "snapshots" / "2026-07-13.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["sector_count"] -= 1
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    tampered = frozen_oos_preflight(status_path)
    assert tampered["status"] == "rejected_frozen_oos_preflight"
    assert any("artifact_sha_mismatch" in error for error in tampered["integrity_errors"])

    source2 = _source_root(tmp_path / "second")
    collection2 = tmp_path / "collection2"
    _collection(source2, collection2, monkeypatch)
    candidate_path = collection2 / "candidate_freeze.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["candidate_configs"][0]["n_estimators"] = 999
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    status2_path = collection2 / "prospective_collection_status.json"
    status2 = json.loads(status2_path.read_text(encoding="utf-8"))
    status2["candidate_freeze"]["sha256"] = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    status2_path.write_text(json.dumps(status2), encoding="utf-8")
    drifted = frozen_oos_preflight(status2_path)
    assert "candidate_parameter_drift" in drifted["integrity_errors"]


def test_frozen_oos_rejects_unreviewed_event_without_reading_adjustment(tmp_path, monkeypatch):
    from theme_sector_radar.ml.industry_sector_frozen_oos import frozen_oos_preflight

    source = _source_root(tmp_path)
    collection = tmp_path / "collection"
    _collection(source, collection, monkeypatch)
    event_manifest = tmp_path / "event_manifest.json"
    event_manifest.write_text(json.dumps({
        "schema_version": "ml-industry-sector-event-adjustment-manifest-v1",
        "review_status": "pending",
        "approved_for_frozen_oos_ab": False,
        "adjustment_artifact": {"path": str((tmp_path / "must_not_read.json").resolve()), "sha256": "fake"},
    }), encoding="utf-8")
    result = frozen_oos_preflight(
        collection / "prospective_collection_status.json",
        event_adjustment_manifest=event_manifest,
    )
    assert result["status"] == "rejected_frozen_oos_preflight"
    assert "event_manifest_not_reviewed_approved" in result["integrity_errors"]
    assert result["event_adjustment"]["event_source_read"] is False


def test_frozen_oos_rejects_event_without_pit_contract_before_artifact_read(tmp_path, monkeypatch):
    from theme_sector_radar.ml.industry_sector_frozen_oos import frozen_oos_preflight

    source = _source_root(tmp_path)
    collection = tmp_path / "collection"
    _collection(source, collection, monkeypatch)
    event_manifest = tmp_path / "event_manifest.json"
    event_manifest.write_text(json.dumps({
        "schema_version": "ml-industry-sector-event-adjustment-manifest-v1",
        "review_status": "approved",
        "approved_for_frozen_oos_ab": True,
        "arm_id": "industry_ml_event_adjustment",
        "adjustment_artifact": {
            "path": str((tmp_path / "must_not_read.json").resolve()),
            "sha256": "fake",
        },
    }), encoding="utf-8")
    result = frozen_oos_preflight(
        collection / "prospective_collection_status.json",
        event_adjustment_manifest=event_manifest,
    )
    assert result["status"] == "rejected_frozen_oos_preflight"
    assert "event_pit_strict_contract_missing" in result["integrity_errors"]
    assert "event_record_time_contract_missing" in result["integrity_errors"]
    assert "event_adjustment_artifact_missing" not in result["integrity_errors"]
    assert result["event_adjustment"]["event_source_read"] is False


def test_frozen_oos_exposes_three_arm_contract_and_formal_chain_isolation(tmp_path, monkeypatch):
    import inspect

    from theme_sector_radar.ml import industry_sector_frozen_oos as frozen

    source = _source_root(tmp_path)
    collection = tmp_path / "collection"
    _collection(source, collection, monkeypatch)
    result = frozen.frozen_oos_preflight(collection / "prospective_collection_status.json")
    arms = {item["arm_id"]: item for item in result["arm_contract"]["arms"]}
    assert set(arms) == {
        "industry_ml_baseline",
        "industry_ml_event_features",
        "industry_ml_event_adjustment",
    }
    assert arms["industry_ml_baseline"]["enabled"] is True
    assert arms["industry_ml_baseline"]["status"] == "reserved_blocked"
    assert arms["industry_ml_event_features"]["enabled"] is False
    assert arms["industry_ml_event_adjustment"]["enabled"] is False
    assert result["event_ab"]["event_input_default_enabled"] is False
    assert result["event_ab"]["event_source_read"] is False
    assert result["promotion_allowed"] is False
    assert result["live_trading_allowed"] is False

    module_source = inspect.getsource(frozen)
    for forbidden in (
        "formal_candidate_selection",
        "Linkage V2",
    ):
        assert forbidden not in module_source


def test_frozen_oos_rejects_protected_score_fields():
    from theme_sector_radar.ml.industry_sector_frozen_oos import validate_no_protected_score_fields

    with pytest.raises(ValueError, match="protected score field"):
        validate_no_protected_score_fields({"arm_reports": [{"selection_score": 1.0}]})


def test_frozen_oos_ready_gate_calls_ready_path_only_after_all_maturity(tmp_path, monkeypatch):
    from theme_sector_radar.ml import industry_sector_frozen_oos as frozen

    source = _source_root(tmp_path)
    collection = tmp_path / "collection"
    _collection(source, collection, monkeypatch)
    for day in ("2026-07-17", "2026-07-20", "2026-07-21", "2026-07-22", "2026-07-23"):
        _append_complete_date(source, day)
    status = _collection(source, collection, monkeypatch)
    assert status["collection_ready"] is True
    preflight = frozen.frozen_oos_preflight(collection / "prospective_collection_status.json")
    assert preflight["ready"] is True
    assert preflight["immutable_file_count_verified"] == 10

    called = []
    monkeypatch.setattr(
        frozen,
        "_run_ready_evaluation",
        lambda *args: called.append(args) or {"status": "ready_path_called"},
    )
    result = frozen.run_frozen_oos_evaluation(
        collection / "prospective_collection_status.json",
        source,
        tmp_path / "evaluation",
        tmp_path / "models",
    )
    assert result["status"] == "ready_path_called"
    assert len(called) == 1


def test_frozen_oos_metrics_and_paired_candidate_comparison():
    from theme_sector_radar.ml.industry_sector_frozen_oos import (
        evaluate_frozen_scores,
        paired_candidate_comparison,
    )

    records = []
    scores_a = {}
    scores_b = {}
    for date_index, day in enumerate(("2026-07-13", "2026-07-14")):
        for sector_index in range(3):
            name = f"sector-{sector_index}"
            records.append({
                "as_of_date": day,
                "sector_name": name,
                "training_label": 0.01 * (sector_index - 1),
                "future_return_5d": 0.02 * (sector_index - 1),
                "market_regime": "risk_on" if date_index == 0 else "risk_off",
            })
            scores_a[(day, name)] = float(sector_index)
            scores_b[(day, name)] = float(2 - sector_index)
    report_a = evaluate_frozen_scores(records, scores_a)
    report_b = evaluate_frozen_scores(records, scores_b)
    assert report_a["top3"]["date_count"] == 2
    assert report_a["top3"]["cost_scenarios"]["25.0"]["mean_net_excess_return"] <= report_a["top3"]["mean_gross_excess_return"]
    assert report_a["top3"]["gross_excess_path"]["max_drawdown"] >= 0.0
    assert report_a["top3"]["regime"]["risk_on"]["date_count"] == 1
    paired = paired_candidate_comparison({"A": report_a, "B": report_b}, baseline_id="A")
    assert paired["comparisons"]["B"]["top3"]["paired_date_count"] == 2
