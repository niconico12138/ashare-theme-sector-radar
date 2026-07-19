import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import scripts.rebuild_intraday_candidates_from_complete_1m as candidate_rebuild
import pytest
from scripts.rebuild_intraday_candidates_from_complete_1m import (
    rebuild_5m_candidate_document,
    rebuild_5m_candidate_root,
)


def _complete_bars(day="2026-03-03"):
    trading_day = datetime.strptime(day, "%Y-%m-%d")
    times = []
    current = trading_day.replace(hour=9, minute=30)
    while current <= trading_day.replace(hour=11, minute=30):
        times.append(current)
        current += timedelta(minutes=1)
    current = trading_day.replace(hour=13, minute=1)
    while current <= trading_day.replace(hour=15, minute=0):
        times.append(current)
        current += timedelta(minutes=1)
    bars = []
    previous = 10.0
    for index, timestamp in enumerate(times):
        close = round(10.0 + index * 0.01, 2)
        bars.append(
            {
                "time": timestamp.strftime("%Y%m%d%H%M%S"),
                "date": timestamp.strftime("%Y%m%d%H%M%S"),
                "open": previous,
                "high": close + 0.02,
                "low": min(previous, close) - 0.02,
                "close": close,
                "price": close,
                "volume": float(index + 1),
                "amount": float((index + 1) * 100),
            }
        )
        previous = close
    return bars


def _document(bars):
    return {
        "schema_version": "1.0",
        "as_of": "2026-03-03",
        "candidates": [
            {
                "code": "000001",
                "name": "sample",
                "prev_close": 9.9,
                "intraday_bars": bars,
                "midday_hold_score": 999.0,
            }
        ],
    }


def test_rebuild_document_aggregates_complete_1m_and_recomputes_factors():
    source_bars = _complete_bars()

    result = rebuild_5m_candidate_document(
        _document(source_bars),
        date="2026-03-03",
        source_path="source.json",
        source_sha256="a" * 64,
    )

    rebuilt = result["data"]
    candidate = rebuilt["candidates"][0]
    bars = candidate["intraday_bars"]
    assert result["summary"]["complete_candidate_count"] == 1
    assert result["summary"]["invalid_candidate_count"] == 0
    assert rebuilt["intraday_bar_identity"]["bar_source"] == "aggregated_from_complete_1m_session"
    assert rebuilt["intraday_bar_identity"]["source_sha256"] == "a" * 64
    assert candidate["intraday_bar_identity"]["complete_session"] is True
    assert len(candidate["intraday_bar_identity"]["source_security_bars_sha256"]) == 64
    assert len(bars) == 48
    assert bars[0]["open"] == source_bars[0]["open"]
    assert bars[0]["close"] == source_bars[5]["close"]
    assert bars[0]["volume"] == sum(item["volume"] for item in source_bars[:6])
    assert all(bar["code"] == "000001" and bar["name"] == "sample" for bar in bars)
    assert candidate["midday_hold_score"] != 999.0
    assert candidate["midday_hold_score"] is not None


def test_rebuild_document_rejects_bars_from_another_security():
    source_bars = _complete_bars()
    for bar in source_bars:
        bar["code"] = "600000"
        bar["name"] = "other"

    with pytest.raises(ValueError, match="bar security identity"):
        rebuild_5m_candidate_document(
            _document(source_bars),
            date="2026-03-03",
            source_path="source.json",
            source_sha256="a" * 64,
        )


def test_rebuild_document_can_emit_trusted_complete_1m_candidates():
    source_bars = _complete_bars()

    result = candidate_rebuild.rebuild_trusted_candidate_document(
        _document(source_bars),
        date="2026-03-03",
        source_path="source.json",
        source_sha256="c" * 64,
        target_interval="1m",
    )

    rebuilt = result["data"]
    candidate = rebuilt["candidates"][0]
    assert rebuilt["intraday_bar_identity"]["bar_interval"] == "1m"
    assert rebuilt["intraday_bar_identity"]["bar_source"] == "complete_1m_session"
    assert candidate["intraday_bar_identity"]["complete_session"] is True
    assert len(candidate["intraday_bars"]) == 241
    assert candidate["intraday_bars"][0]["open"] == source_bars[0]["open"]
    assert all(
        bar["code"] == "000001" and bar["name"] == "sample"
        for bar in candidate["intraday_bars"]
    )
    assert candidate["midday_hold_score"] != 999.0


def test_rebuild_document_fails_closed_when_1m_session_has_gap():
    source_bars = _complete_bars()
    source_bars.pop(50)

    result = rebuild_5m_candidate_document(
        _document(source_bars),
        date="2026-03-03",
        source_path="source.json",
        source_sha256="b" * 64,
    )

    candidate = result["data"]["candidates"][0]
    assert result["summary"]["complete_candidate_count"] == 0
    assert result["summary"]["invalid_candidate_count"] == 1
    assert "intraday_bars" not in candidate
    assert candidate["midday_hold_score"] is None
    identity = candidate["intraday_bar_identity"]
    assert len(identity.pop("source_security_bars_sha256")) == 64
    assert identity == {
        "bar_interval": "5m",
        "bar_source": "aggregated_from_complete_1m_session",
        "complete_session": False,
        "source_1m_bar_count": 240,
        "bar_count": 0,
        "invalid_reason": "incomplete_1m_session",
    }


def test_rebuild_root_writes_source_addressed_derived_candidates(tmp_path):
    source_root = tmp_path / "source"
    source_path = source_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(json.dumps(_document(_complete_bars())), encoding="utf-8")
    output_root = tmp_path / "derived"

    report = rebuild_5m_candidate_root(
        source_root=source_root,
        output_root=output_root,
        start="2026-03-03",
        end="2026-03-03",
    )

    output_path = output_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    rebuilt = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["summary"]["processed_date_count"] == 1
    assert report["summary"]["complete_candidate_count"] == 1
    assert report["daily_results"][0]["output_sha256"] == hashlib.sha256(output_path.read_bytes()).hexdigest()
    assert rebuilt["intraday_bar_identity"]["source_path"] == str(source_path)
    assert rebuilt["intraday_bar_identity"]["source_sha256"] == hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert rebuilt["intraday_bar_identity"]["derived_output"] is True


def test_rebuild_root_hashes_the_source_bytes_it_parsed(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    source_path = source_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source_path.parent.mkdir(parents=True)
    first_document = _document(_complete_bars())
    first_bytes = json.dumps(first_document).encode("utf-8")
    source_path.write_bytes(first_bytes)
    replacement = _document(_complete_bars())
    replacement["candidates"][0]["prev_close"] = 1.0
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        if self == source_path:
            self.write_text(json.dumps(replacement), encoding="utf-8")
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    report = rebuild_5m_candidate_root(
        source_root=source_root,
        output_root=tmp_path / "derived",
        start="2026-03-03",
        end="2026-03-03",
    )

    output_path = Path(report["daily_results"][0]["output_path"])
    rebuilt = json.loads(output_path.read_text(encoding="utf-8"))
    assert rebuilt["candidates"][0]["prev_close"] == 9.9
    assert rebuilt["intraday_bar_identity"]["source_sha256"] == hashlib.sha256(
        first_bytes
    ).hexdigest()


def test_rebuild_root_rejects_source_and_output_same_root(tmp_path):
    root = tmp_path / "same-root"
    source_path = root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(json.dumps(_document(_complete_bars())), encoding="utf-8")

    with pytest.raises(ValueError, match="source and output roots must differ"):
        candidate_rebuild.rebuild_trusted_candidate_root(
            source_root=root,
            output_root=root,
            start="2026-03-03",
            end="2026-03-03",
            target_interval="1m",
        )


def test_rebuild_root_rejects_output_nested_inside_source(tmp_path):
    source_root = tmp_path / "source"
    source_path = source_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(json.dumps(_document(_complete_bars())), encoding="utf-8")
    output_root = source_root / "derived"

    with pytest.raises(ValueError, match="must not contain"):
        candidate_rebuild.rebuild_trusted_candidate_root(
            source_root=source_root,
            output_root=output_root,
            start="2026-03-03",
            end="2026-03-03",
            target_interval="1m",
        )

    assert not output_root.exists()


def test_rebuild_root_rejects_source_nested_inside_output(tmp_path):
    output_root = tmp_path / "derived"
    source_root = output_root / "source"
    source_path = source_root / "2026-03-03" / "top30_candidates.intraday_backfilled.json"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(json.dumps(_document(_complete_bars())), encoding="utf-8")

    with pytest.raises(ValueError, match="must not contain"):
        candidate_rebuild.rebuild_trusted_candidate_root(
            source_root=source_root,
            output_root=output_root,
            start="2026-03-03",
            end="2026-03-03",
            target_interval="1m",
        )
