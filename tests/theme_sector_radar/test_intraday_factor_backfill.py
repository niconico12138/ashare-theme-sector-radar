import json
import hashlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from backfill_intraday_factors import (
    DEFAULT_CANDIDATE_ROOT,
    DEFAULT_OUTPUT_ROOT,
    _read_json,
    _write_json,
    backfill_date,
    backfill_intraday_candidates,
    normalize_intraday_bars,
)


class FakeIntradayClient:
    def __init__(self):
        self.calls = []

    def get_stock_bars(self, code, start, end, frequency="5m", fq=None):
        self.calls.append((code, start, end, frequency, fq))
        if code != "600001":
            return []
        return [
            {"date": 20260702150000, "close": 104.0, "amount": 20_000_000.0},
            {"date": 20260702093000, "close": 100.0, "amount": 8_000_000.0},
            {"date": 20260702103000, "close": 101.0, "amount": 10_000_000.0},
            {"date": 20260702133000, "close": 102.0, "amount": 12_000_000.0},
            {"date": 20260702143000, "close": 103.0, "amount": 16_000_000.0},
        ]


def test_normalize_intraday_bars_sorts_old_to_new_and_maps_price():
    bars = normalize_intraday_bars(
        [
            {"date": 20260702150000, "close": 104.0, "amount": 20_000_000.0},
            {"date": 20260702093000, "close": 100.0, "amount": 8_000_000.0},
        ]
    )

    assert [bar["date"] for bar in bars] == ["20260702093000", "20260702150000"]
    assert bars[0]["price"] == 100.0
    assert bars[1]["amount"] == 20_000_000.0


def test_backfill_intraday_candidates_adds_shadow_fields_for_short_burst_only():
    data = {
        "candidates": [
            {
                "code": "600001",
                "name": "ShortBurst",
                "source_pool": "burst_top",
                "opportunity_type": "short_burst",
                "final_score": 66.0,
                "v2_score": 58.0,
            },
            {
                "code": "600002",
                "name": "Trend",
                "source_pool": "trend_top",
                "opportunity_type": "trend_follow",
                "final_score": 72.0,
                "v2_score": 61.0,
            },
        ]
    }
    client = FakeIntradayClient()

    result = backfill_intraday_candidates(data, "2026-07-02", client=client, frequency="5m")
    candidates = result["data"]["candidates"]
    short = candidates[0]
    trend = candidates[1]

    assert len(client.calls) == 1
    assert client.calls[0][0] == "600001"
    assert short["intraday_factor_snapshot"]["intraday_available"] is True
    assert short["short_burst_intraday_emotion_overlay_shadow"]["policy"] == "shadow_observation_only"
    assert short["short_burst_intraday_emotion_score_shadow"] is not None
    assert "intraday_bars" not in short
    assert trend["intraday_factor_snapshot"]["intraday_available"] is False
    assert result["summary"]["matched_count"] == 1
    assert result["summary"]["missing_count"] == 0


def test_backfill_intraday_candidates_can_store_raw_bars_when_requested():
    data = {
        "candidates": [
            {
                "code": "600001",
                "name": "ShortBurst",
                "source_pool": "burst_top",
                "opportunity_type": "short_burst",
                "final_score": 66.0,
                "v2_score": 58.0,
            }
        ]
    }

    result = backfill_intraday_candidates(
        data,
        "2026-07-02",
        client=FakeIntradayClient(),
        frequency="5m",
        store_bars=True,
    )

    assert len(result["data"]["candidates"][0]["intraday_bars"]) == 5
    json.dumps(result, ensure_ascii=False)


def test_backfill_intraday_candidates_persists_expanded_price_momentum_fields():
    data = {
        "candidates": [
            {
                "code": "600001",
                "name": "ShortBurst",
                "source_pool": "burst_top",
                "opportunity_type": "short_burst",
                "final_score": 66.0,
                "v2_score": 58.0,
                "prev_close": 99.0,
            }
        ]
    }

    result = backfill_intraday_candidates(
        data,
        "2026-07-02",
        client=FakeIntradayClient(),
        frequency="5m",
        store_bars=True,
    )
    candidate = result["data"]["candidates"][0]

    assert candidate["return_5m_strength_score"] is not None
    assert candidate["positive_bar_ratio_score"] is not None
    assert candidate["intraday_breakout_strength_score"] is not None


def test_backfill_intraday_candidates_persists_expanded_volume_money_flow_fields():
    data = {
        "candidates": [
            {
                "code": "600001",
                "name": "ShortBurst",
                "source_pool": "burst_top",
                "opportunity_type": "short_burst",
                "final_score": 66.0,
                "v2_score": 58.0,
                "prev_close": 99.0,
            }
        ]
    }

    result = backfill_intraday_candidates(
        data,
        "2026-07-02",
        client=FakeIntradayClient(),
        frequency="5m",
        store_bars=True,
    )
    candidate = result["data"]["candidates"][0]

    assert candidate["early_amount_surge_score"] is not None
    assert candidate["midday_amount_sustain_score"] is not None
    assert candidate["volume_price_alignment_score"] is not None
    assert candidate["late_money_flow_concentration_score"] is not None


def test_backfill_defaults_and_function_reject_in_place_candidate_mutation(tmp_path):
    assert DEFAULT_CANDIDATE_ROOT.resolve() != DEFAULT_OUTPUT_ROOT.resolve()
    candidate_path = tmp_path / "2026-07-02" / "top30_candidates.json"
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text('{"candidates":[]}', encoding="utf-8")

    with pytest.raises(ValueError, match="candidate and output roots must differ"):
        backfill_date(
            "2026-07-02",
            candidate_root=tmp_path,
            output_root=tmp_path,
            client=FakeIntradayClient(),
        )


def test_backfill_json_io_is_strict_atomic_and_content_addressed(tmp_path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON number"):
        _read_json(invalid_path)

    output_path = tmp_path / "output.json"
    _write_json(output_path, {"version": 1})
    previous = output_path.read_bytes()
    archived_path = _write_json(output_path, {"version": 2})

    assert archived_path == output_path.with_name(
        f"output.{hashlib.sha256(previous).hexdigest()[:12]}.json"
    )
    assert archived_path.read_bytes() == previous
    assert _read_json(output_path) == {"version": 2}

    with pytest.raises(ValueError, match="Out of range float values"):
        _write_json(output_path, {"value": float("nan")})
    assert _read_json(output_path) == {"version": 2}
