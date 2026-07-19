import hashlib
import importlib
import json
import inspect

import pytest

from scripts.run_timing_paper_trading_records import run_timing_paper_trading_records
from theme_sector_radar.data.local_minute_archive import aggregate_complete_1m_session_to_5m


def _in_memory_entry_bars_source_identity():
    return {
        "status": "validated",
        "source_kind": "in_memory_test_fixture",
        "sha256": "a" * 64,
    }


def _entry_bars_source_identity(
    tmp_path,
    *,
    codes=("600001", "600002"),
    entry_date="2026-07-02",
):
    path = tmp_path / "entry-bars" / "entry-bars.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "timing_entry_bars_source_manifest.v1",
        "as_of": "2026-07-13",
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "sessions": [
            {
                "code": code,
                "entry_date": entry_date,
                "bars": [
                    dict(row, name=f"stock-{code}")
                    for row in _complete_1m_session(code)
                ],
            }
            for code in codes
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {
        "status": "validated",
        "source_kind": "strict_json_manifest",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "schema_version": payload["schema_version"],
        "as_of": payload["as_of"],
        "session_count": len(payload["sessions"]),
    }


class _MinuteClient:
    def __init__(self):
        self.calls = []

    def get_stock_bars(self, code, start, end, frequency, fq):
        self.calls.append((code, start, end, frequency, fq))
        return list(reversed(_complete_1m_session(code)))


class _GapMinuteClient(_MinuteClient):
    def get_stock_bars(self, code, start, end, frequency, fq):
        rows = super().get_stock_bars(code, start, end, frequency, fq)
        return [row for row in rows if str(row["date"]) != "20260702093200"]


class _WrongDateMinuteClient(_MinuteClient):
    def get_stock_bars(self, code, start, end, frequency, fq):
        self.calls.append((code, start, end, frequency, fq))
        return [dict(row, date=int(str(row["date"]).replace("20260702", "20260703"))) for row in _complete_1m_session(code)]


class _WrongCodeMinuteClient(_MinuteClient):
    def get_stock_bars(self, code, start, end, frequency, fq):
        return [dict(row, code="000001") for row in _complete_1m_session(code)]


class _ExecutableBarMinuteClient(_MinuteClient):
    def get_stock_bars(self, code, start, end, frequency, fq):
        rows = super().get_stock_bars(code, start, end, frequency, fq)
        rows[0]["orders"] = [{"side": "buy", "quantity": 1}]
        return rows


def _complete_1m_session(code):
    times = ["0930"]
    times.extend(f"{hour:02d}{minute:02d}" for hour in (9, 10, 11) for minute in range(60) if (hour, minute) >= (9, 31) and (hour, minute) <= (11, 30))
    times.extend(f"{hour:02d}{minute:02d}" for hour in (13, 14, 15) for minute in range(60) if (hour, minute) >= (13, 1) and (hour, minute) <= (15, 0))
    rows = []
    for index, value in enumerate(times):
        close = 10.5 if index == len(times) - 1 else 10.0
        rows.append(
            {
                "date": int(f"20260702{value}00"),
                "code": code,
                "open": 10.0,
                "high": 10.8 if index == 100 else max(10.0, close),
                "low": 9.6 if index == 120 else min(10.0, close),
                "close": close,
                "volume": 100,
                "amount": 1000,
            }
        )
    return rows


def _write_json(path, data):
    path.parent.mkdir(parents=True)
    payload = dict(data) if isinstance(data, dict) else data
    if isinstance(payload, dict) and path.name in {
        "next_day_selection_validation.json",
        "top30_candidates.intraday_backfilled.json",
    }:
        payload.setdefault("as_of", path.parent.name)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _selection_root(tmp_path, date="2026-07-01"):
    root = tmp_path / "selection"
    _write_json(root / date / "next_day_selection_validation.json", {"per_stock": []})
    return root


def _candidate(code, **overrides):
    row = {
        "code": code,
        "name": f"stock-{code}",
        "boards": ["gas"],
        "open_to_midday_resilience_score": 70,
        "midday_hold_score": 70,
        "vwap_above_ratio_score": 70,
        "late_high_near_close_score": 90,
        "high_to_close_drawdown_score": 12,
        "lower_low_sequence_risk": 20,
        "stock_vs_market_intraday_alpha_score": 75,
        "relative_resilience_score": 75,
        "optimized_watch_score": 80,
        "late_amount_surge_score": 40,
        "failed_breakout_risk": 20,
        "execution_tradeability_score": 60,
        "late_breakdown_risk": 0,
        "intraday_bars": [
            {"time": "09:30", "price": 10.0, "high": 10.1, "low": 9.9, "close": 10.0},
            {"time": "15:00", "price": 10.5, "high": 10.8, "low": 9.6, "close": 10.5},
        ],
    }
    row.update(overrides)
    return row


def _source_identity(timeframe):
    return {
        "status": "validated",
        "bar_interval": timeframe,
        "bar_source": {
            "1m": "complete_1m_session",
            "5m": "aggregated_from_complete_1m_session",
        }[timeframe],
        "manifest_sha256": "a" * 64,
    }


@pytest.fixture
def trusted_candidate_root(monkeypatch):
    def validate(
        root,
        *,
        source_root,
        timeframe,
        start=None,
        end=None,
        document_snapshots=None,
    ):
        if document_snapshots is not None:
            document_snapshots.clear()
            for path in sorted(root.rglob("top30_candidates*.json")):
                document_snapshots[path] = json.loads(path.read_text(encoding="utf-8"))
        return {
            **_source_identity(timeframe),
            "candidate_root": str(root),
            "source_root": str(source_root),
            "document_count": 1,
            "complete_candidate_count": 1,
            "invalid_candidate_count": 0,
        }

    monkeypatch.setattr(
        "scripts.run_timing_paper_trading_records.validate_candidate_root_identity",
        validate,
    )


def test_run_paper_records_has_no_programmatic_candidate_identity_bypass():
    assert "candidate_source_identity" not in inspect.signature(run_timing_paper_trading_records).parameters


def test_entry_bar_source_identity_is_caller_bound():
    module = importlib.import_module("scripts.run_timing_paper_trading_records")

    with pytest.raises(ValueError, match="caller-bound entry-bar source"):
        module._validate_entry_bars_source_identity(None)

    with pytest.raises(ValueError, match="durable strict JSON manifest"):
        module._validate_entry_bars_source_identity(
            _in_memory_entry_bars_source_identity()
        )

    identity = module._validate_entry_bars_source_identity(
        {
            "status": "validated",
            "source_kind": "strict_json_manifest",
            "path": "entry-bars.json",
            "sha256": "a" * 64,
        }
    )
    assert identity["sha256"] == "a" * 64


def test_entry_bars_manifest_requires_strict_paper_guards(tmp_path):
    module = importlib.import_module("scripts.run_timing_paper_trading_records")
    path = tmp_path / "entry-bars.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "timing_entry_bars_source_manifest.v1",
                "sessions": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="paper_trading_only"):
        module._load_entry_bars_manifest(
            path,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )


def test_run_timing_paper_trading_records_writes_json_and_markdown(tmp_path, trusted_candidate_root):
    candidate_root = tmp_path / "candidates"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.intraday_backfilled.json",
        {"candidates": [_candidate("600001"), _candidate("600002")]},
    )

    client = _MinuteClient()
    entry_bars_source_identity = _entry_bars_source_identity(tmp_path)
    result = run_timing_paper_trading_records(
        candidate_root=candidate_root,
        candidate_source_root=tmp_path / "source",
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        start="2026-07-01",
        end="2026-07-01",
        selection_validation_root=_selection_root(tmp_path),
        bar_interval="1m",
        trading_calendar_dates=["2026-07-01", "2026-07-02"],
        client=client,
        entry_bars_source_identity=entry_bars_source_identity,
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    report = result["report"]
    assert report["paper_trading_only"] is True
    assert report["summary"]["record_count"] == 4
    assert report["record_cohort_identity"]["status"] == "validated"
    assert report["entry_bars_source_identity"] == entry_bars_source_identity
    assert report["record_cohort_identity"]["expected_record_count"] == 4
    assert len(report["record_cohort_identity"]["record_key_manifest_sha256"]) == 64
    assert report["parameters"]["selection_source_identity"]["document_dates"] == ["2026-07-01"]
    assert report["summary"]["causal_entry_valid_count"] == 4
    assert report["summary"]["risk_tag_counts"]["same_day_board_concentration"] == 4
    assert report["records"][0]["path_stats"]["max_favorable_excursion_pct"] == 8.0
    assert report["records"][0]["signal_date"] == "2026-07-01"
    assert report["records"][0]["entry_date"] == "2026-07-02"
    assert all(bar["code"] == report["records"][0]["code"] for bar in report["records"][0]["entry_bars"])
    assert all(bar["name"] == report["records"][0]["name"] for bar in report["records"][0]["entry_bars"])
    assert all(call[3] == "1m" for call in client.calls)
    assert "Timing Paper Trading Records" in result["markdown_path"].read_text(encoding="utf-8")


def test_run_paper_records_rejects_executable_fields_before_writing(
    tmp_path,
    trusted_candidate_root,
):
    candidate_root = tmp_path / "candidates"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.intraday_backfilled.json",
        {"candidates": [_candidate("600001")]},
    )
    output_dir = tmp_path / "out"

    with pytest.raises(ValueError, match="executable instruction fields"):
        run_timing_paper_trading_records(
            candidate_root=candidate_root,
            candidate_source_root=tmp_path / "source",
            output_dir=output_dir,
            as_of="2026-07-13",
            snapshot_label="unit",
            start="2026-07-01",
            end="2026-07-01",
            selection_validation_root=_selection_root(tmp_path),
            bar_interval="1m",
            trading_calendar_dates=["2026-07-01", "2026-07-02"],
            client=_ExecutableBarMinuteClient(),
            entry_bars_source_identity=_entry_bars_source_identity(
                tmp_path,
                codes=("600001",),
            ),
        )

    assert not output_dir.exists()


def test_run_paper_records_builds_5m_from_complete_1m_bars(tmp_path, trusted_candidate_root):
    candidate_root = tmp_path / "candidates"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.intraday_backfilled.json",
        {"candidates": [_candidate("600001")]},
    )

    client = _MinuteClient()
    result = run_timing_paper_trading_records(
        candidate_root=candidate_root,
        candidate_source_root=tmp_path / "source",
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        start="2026-07-01",
        end="2026-07-01",
        selection_validation_root=_selection_root(tmp_path),
        bar_interval="5m",
        trading_calendar_dates=["2026-07-01", "2026-07-02"],
        client=client,
        entry_bars_source_identity=_entry_bars_source_identity(
            tmp_path,
            codes=("600001",),
        ),
    )

    record = result["report"]["records"][0]
    assert record["causal_entry_valid"] is True
    assert record["path_stats"]["entry_reference_price"] == 10.0
    assert record["exit_data_quality"]["bar_count"] == 48
    assert len(record["source_1m_bars"]) == 241
    assert len(record["source_1m_bars_sha256"]) == 64
    assert aggregate_complete_1m_session_to_5m(record["source_1m_bars"]) == record["entry_bars"]
    assert result["report"]["bar_source"] == "aggregated_from_complete_1m_session"
    assert record["execution_assumptions"]["bar_source"] == "aggregated_from_complete_1m_session"
    assert all(call[3] == "1m" for call in client.calls)


def test_run_paper_records_rejects_untrusted_candidate_factor_source(tmp_path):
    candidate_root = tmp_path / "candidates"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.intraday_backfilled.json",
        {"candidates": [_candidate("600001")]},
    )

    with pytest.raises(ValueError, match="candidate.*identity"):
        run_timing_paper_trading_records(
            candidate_root=candidate_root,
            candidate_source_root=tmp_path / "source",
            output_dir=tmp_path / "out",
            as_of="2026-07-13",
            snapshot_label="unit",
            start="2026-07-01",
            end="2026-07-01",
            selection_validation_root=_selection_root(tmp_path),
            bar_interval="5m",
            trading_calendar_dates=["2026-07-01", "2026-07-02"],
            client=_MinuteClient(),
            entry_bars_source_identity=_entry_bars_source_identity(
                tmp_path,
                codes=("600001",),
            ),
        )


def test_run_paper_records_rejects_entry_bars_for_another_security(tmp_path, trusted_candidate_root):
    candidate_root = tmp_path / "candidates"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.intraday_backfilled.json",
        {"candidates": [_candidate("600001")]},
    )

    with pytest.raises(ValueError, match="security code"):
        run_timing_paper_trading_records(
            candidate_root=candidate_root,
            candidate_source_root=tmp_path / "source",
            output_dir=tmp_path / "out",
            as_of="2026-07-13",
            snapshot_label="unit",
            start="2026-07-01",
            end="2026-07-01",
            selection_validation_root=_selection_root(tmp_path),
            bar_interval="1m",
            trading_calendar_dates=["2026-07-01", "2026-07-02"],
            client=_WrongCodeMinuteClient(),
            entry_bars_source_identity=_entry_bars_source_identity(
                tmp_path,
                codes=("600001",),
            ),
        )


@pytest.mark.parametrize("client", [_GapMinuteClient(), _WrongDateMinuteClient()])
def test_run_paper_records_keeps_incomplete_or_wrong_session_unlabeled(tmp_path, client, trusted_candidate_root):
    candidate_root = tmp_path / "candidates"
    _write_json(
        candidate_root / "2026-07-01" / "top30_candidates.intraday_backfilled.json",
        {"candidates": [_candidate("600001")]},
    )

    result = run_timing_paper_trading_records(
        candidate_root=candidate_root,
        candidate_source_root=tmp_path / "source",
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        start="2026-07-01",
        end="2026-07-01",
        selection_validation_root=_selection_root(tmp_path),
        bar_interval="1m",
        trading_calendar_dates=["2026-07-01", "2026-07-02", "2026-07-03"],
        client=client,
        entry_bars_source_identity=_entry_bars_source_identity(
            tmp_path,
            codes=("600001",),
        ),
    )

    record = result["report"]["records"][0]
    assert record["entry_date"] == "2026-07-02"
    assert record["causal_entry_valid"] is False
    assert record["forward_return_pct"] is None


def test_run_paper_records_excludes_sample_mode_weekend_signals(tmp_path, trusted_candidate_root):
    candidate_root = tmp_path / "candidates"
    _write_json(
        candidate_root / "2026-06-28" / "top30_candidates.intraday_backfilled.json",
        {"as_of": "2026-06-28", "sample_mode": True, "candidates": [_candidate("600001")]},
    )
    client = _MinuteClient()

    result = run_timing_paper_trading_records(
        candidate_root=candidate_root,
        candidate_source_root=tmp_path / "source",
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        selection_validation_root=_selection_root(tmp_path, "2026-06-28"),
        bar_interval="1m",
        trading_calendar_dates=["2026-06-26", "2026-06-29"],
        client=client,
        entry_bars_source_identity=_entry_bars_source_identity(
            tmp_path,
            codes=(),
        ),
    )

    assert result["report"]["summary"]["sample_count"] == 0
    assert result["report"]["summary"]["record_count"] == 0
    assert client.calls == []
