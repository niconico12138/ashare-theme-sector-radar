from __future__ import annotations

from datetime import date, timedelta
import json

import pytest


def _trading_dates(start: date, end: date) -> list[str]:
    result = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def _source_root(tmp_path, *, sectors: int = 12):
    root = tmp_path / "sector_history"
    industry = root / "industry"
    industry.mkdir(parents=True)
    dates = _trading_dates(date(2026, 5, 18), date(2026, 7, 16))
    for sector_index in range(sectors):
        records = [
            {
                "date": day,
                "close": 100.0 + sector_index + index * 0.2,
                "volume": 1000.0 + sector_index + index,
                "amount": 100000.0 + sector_index * 100 + index * 10,
            }
            for index, day in enumerate(dates)
        ]
        payload = {
            "sector_name": f"industry-{sector_index:02d}",
            "sector_type": "industry",
            "source": "unit_test_source",
            "start_date": dates[0],
            "end_date": dates[-1],
            "records": records,
        }
        (industry / f"industry_{sector_index:02d}.json").write_text(
            json.dumps(payload, sort_keys=True), encoding="utf-8"
        )
    return root


def _append_bar(path, day: str):
    payload = json.loads(path.read_text(encoding="utf-8"))
    last = payload["records"][-1]
    payload["records"].append({
        "date": day,
        "close": last["close"] + 0.2,
        "volume": last["volume"] + 1,
        "amount": last["amount"] + 10,
    })
    payload["end_date"] = day
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _collect(root, output, monkeypatch):
    from theme_sector_radar.ml import industry_sector_shadow as shadow
    from theme_sector_radar.ml.industry_sector_prospective_collection import (
        collect_prospective_collection_status,
    )

    monkeypatch.setattr(shadow, "MIN_SECTORS", 10)
    return collect_prospective_collection_status(root, output)


def test_prospective_snapshots_are_immutable_and_use_trading_day_maturity(tmp_path, monkeypatch):
    root = _source_root(tmp_path)
    output = tmp_path / "prospective"
    report = _collect(root, output, monkeypatch)

    assert report["status"] == "blocked_pending_label_maturity"
    assert report["all_test_labels_mature"] is False
    assert len(report["snapshots"]) == 4
    assert (output / "candidate_freeze.json").is_file()
    assert "candidate_freeze" in report
    assert report["maturity"][0]["observed_future_trading_dates"] == [
        "2026-07-14", "2026-07-15", "2026-07-16"
    ]
    assert report["maturity"][0]["missing_future_trading_day_count"] == 2
    assert all((output / "snapshots" / f"{day}.json").is_file() for day in report["frozen_signal_dates"])
    assert all((output / "manifests" / f"{day}.manifest.json").is_file() for day in report["frozen_signal_dates"])

    for day in ("2026-07-17", "2026-07-20", "2026-07-21", "2026-07-22", "2026-07-23"):
        for path in (root / "industry").glob("*.json"):
            _append_bar(path, day)
    ready = _collect(root, output, monkeypatch)
    assert ready["status"] == "ready_for_frozen_candidate_evaluation"
    assert ready["all_test_labels_mature"] is True
    assert ready["maturity"][-1]["label_maturity_date"] == "2026-07-23"
    assert ready["candidate_model_training_run"] is False


def test_prospective_rejects_missing_industry_and_missing_bar(tmp_path, monkeypatch):
    root = _source_root(tmp_path)
    output = tmp_path / "prospective"
    _collect(root, output, monkeypatch)
    next((root / "industry").glob("*.json")).unlink()
    missing_industry = _collect(root, output, monkeypatch)
    assert missing_industry["status"] == "rejected_source_integrity"
    assert any("industry_set_drift" in error or "missing_industries" in error for error in missing_industry["errors"])

    root2 = _source_root(tmp_path / "second")
    output2 = tmp_path / "prospective2"
    _collect(root2, output2, monkeypatch)
    paths = list((root2 / "industry").glob("*.json"))
    for path in paths[:-1]:
        _append_bar(path, "2026-07-17")
    missing_bar = _collect(root2, output2, monkeypatch)
    assert missing_bar["status"] == "rejected_source_integrity"
    assert "missing_bars_in_prospective_calendar" in missing_bar["errors"]


def test_prospective_rejects_source_revision_and_snapshot_sha_tampering(tmp_path, monkeypatch):
    root = _source_root(tmp_path)
    output = tmp_path / "prospective"
    _collect(root, output, monkeypatch)
    path = next((root / "industry").glob("*.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    row = next(item for item in payload["records"] if item["date"] == "2026-07-13")
    row["close"] += 1.0
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    revised = _collect(root, output, monkeypatch)
    assert revised["status"] == "rejected_source_integrity"
    assert any(error.startswith("source_revision:2026-07-13") for error in revised["errors"])

    snapshot_path = output / "snapshots" / "2026-07-13.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["sector_count"] -= 1
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ValueError, match="immutable prospective artifact differs"):
        _collect(root, output, monkeypatch)


def test_prospective_rejects_date_drift_and_missing_signal_bar(tmp_path, monkeypatch):
    from theme_sector_radar.ml import industry_sector_shadow as shadow
    from theme_sector_radar.ml.industry_sector_prospective_collection import (
        collect_prospective_collection_status,
    )

    monkeypatch.setattr(shadow, "MIN_SECTORS", 10)
    root = _source_root(tmp_path)
    with pytest.raises(ValueError, match="date drift"):
        collect_prospective_collection_status(
            root,
            tmp_path / "drift",
            signal_dates=("2026-07-14", "2026-07-15", "2026-07-16", "2026-07-17"),
        )

    path = next((root / "industry").glob("*.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"] = [row for row in payload["records"] if row["date"] != "2026-07-14"]
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError, match="missing or duplicate signal bar"):
        collect_prospective_collection_status(root, tmp_path / "missing_signal")
