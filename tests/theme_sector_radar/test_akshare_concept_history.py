from __future__ import annotations

from copy import deepcopy
import json

import pytest


class FakeAkShare:
    def __init__(self, rows=None, error=None):
        self.rows = deepcopy(rows or [])
        self.error = error
        self.calls = []

    def stock_board_concept_hist_em(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return deepcopy(self.rows)


def _rows():
    return [
        {
            "日期": "2026-07-17",
            "开盘": "100",
            "最高": 102,
            "最低": 99,
            "收盘": 101,
            "涨跌幅": "1.25",
            "成交额": 123456,
        },
        {
            "日期": "2026-07-16",
            "开盘": 98,
            "最高": 101,
            "最低": 97,
            "收盘": 99,
            "涨跌幅": -0.5,
            "成交额": 100000,
        },
    ]


def test_akshare_history_normalizes_and_caches_strict_json(tmp_path):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
    )

    upstream = FakeAkShare(_rows())
    client = AkShareConceptHistoryClient(client=upstream, cache_root=tmp_path)
    payload = client.get_history(
        board_code="300843.TI",
        board_name="5G",
        start_date="2026-06-01",
        end_date="2026-07-17",
        as_of_date="2026-07-17",
    )

    assert payload["identity"] == {"board_code": "300843.TI", "board_name": "5G"}
    assert payload["rows"][0] == {
        "date": "2026-07-16",
        "open": 98.0,
        "high": 101.0,
        "low": 97.0,
        "close": 99.0,
        "pct_change": -0.5,
        "amount": 100000.0,
    }
    assert payload["query"]["as_of_date"] == "2026-07-17"
    assert len(payload["rows_sha256"]) == 64
    cache_files = list(tmp_path.rglob("*.json"))
    assert len(cache_files) == 1
    json.loads(
        cache_files[0].read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def test_akshare_history_network_failure_uses_only_exact_covering_cache(tmp_path):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
    )

    good = AkShareConceptHistoryClient(client=FakeAkShare(_rows()), cache_root=tmp_path)
    expected = good.get_history(
        board_code="300843.TI",
        board_name="5G",
        start_date="2026-06-01",
        end_date="2026-07-17",
        as_of_date="2026-07-17",
    )
    failed = AkShareConceptHistoryClient(
        client=FakeAkShare(error=RuntimeError("offline")), cache_root=tmp_path
    )

    actual = failed.get_history(
        board_code="300843.TI",
        board_name="5G",
        start_date="2026-06-01",
        end_date="2026-07-17",
        as_of_date="2026-07-17",
    )

    assert actual == expected


def test_akshare_history_rejects_old_cache_on_network_failure(tmp_path):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
    )

    old = AkShareConceptHistoryClient(client=FakeAkShare(_rows()), cache_root=tmp_path)
    old.get_history(
        board_code="300843.TI",
        board_name="5G",
        start_date="2026-06-01",
        end_date="2026-07-17",
        as_of_date="2026-07-17",
    )
    failed = AkShareConceptHistoryClient(
        client=FakeAkShare(error=RuntimeError("offline")), cache_root=tmp_path
    )

    with pytest.raises(RuntimeError, match="no exact covering cache"):
        failed.get_history(
            board_code="300843.TI",
            board_name="5G",
            start_date="2026-06-01",
            end_date="2026-07-18",
            as_of_date="2026-07-18",
        )


def test_akshare_history_rejects_tampered_or_nonfinite_cache(tmp_path):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
    )

    good = AkShareConceptHistoryClient(client=FakeAkShare(_rows()), cache_root=tmp_path)
    good.get_history(
        board_code="300843.TI",
        board_name="5G",
        start_date="2026-06-01",
        end_date="2026-07-17",
        as_of_date="2026-07-17",
    )
    cache_path = next(tmp_path.rglob("*.json"))
    text = cache_path.read_text(encoding="utf-8").replace("-0.5", "NaN")
    cache_path.write_text(text, encoding="utf-8")
    failed = AkShareConceptHistoryClient(
        client=FakeAkShare(error=RuntimeError("offline")), cache_root=tmp_path
    )

    with pytest.raises(RuntimeError, match="no exact covering cache"):
        failed.get_history(
            board_code="300843.TI",
            board_name="5G",
            start_date="2026-06-01",
            end_date="2026-07-17",
            as_of_date="2026-07-17",
        )


def test_history_payload_rejects_unknown_query_fields(tmp_path):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
        validate_history_payload,
    )

    client = AkShareConceptHistoryClient(client=FakeAkShare(_rows()), cache_root=tmp_path)
    payload = client.get_history(
        board_code="300843.TI",
        board_name="5G",
        start_date="2026-06-01",
        end_date="2026-07-17",
        as_of_date="2026-07-17",
    )
    payload["query"]["order"] = {"side": "buy"}

    with pytest.raises(ValueError, match="query fields"):
        validate_history_payload(payload)


def test_akshare_history_rejects_partial_pit_coverage(tmp_path):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
    )

    rows = _rows()
    rows = [row for row in rows if row["日期"] != "2026-07-17"]
    client = AkShareConceptHistoryClient(
        client=FakeAkShare(rows), cache_root=tmp_path
    )

    with pytest.raises(ValueError, match="do not cover end_date"):
        client.get_history(
            board_code="300843.TI",
            board_name="5G",
            start_date="2026-06-01",
            end_date="2026-07-17",
            as_of_date="2026-07-17",
        )


def test_akshare_history_cache_is_write_once_for_same_query(tmp_path):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
    )

    first = AkShareConceptHistoryClient(client=FakeAkShare(_rows()), cache_root=tmp_path)
    first.get_history(
        board_code="300843.TI",
        board_name="5G",
        start_date="2026-06-01",
        end_date="2026-07-17",
        as_of_date="2026-07-17",
    )
    changed_rows = _rows()
    changed_rows[0]["成交额"] += 1
    changed = AkShareConceptHistoryClient(
        client=FakeAkShare(changed_rows), cache_root=tmp_path
    )

    with pytest.raises(FileExistsError, match="immutable concept history cache"):
        changed.get_history(
            board_code="300843.TI",
            board_name="5G",
            start_date="2026-06-01",
            end_date="2026-07-17",
            as_of_date="2026-07-17",
        )


@pytest.mark.parametrize(
    "bad_row",
    [
        {**_rows()[0], "日期": "2026-07-18"},
        {**_rows()[0], "涨跌幅": float("nan")},
        {**_rows()[0], "最高": 90},
    ],
)
def test_akshare_history_rejects_bad_pit_rows(tmp_path, bad_row):
    from theme_sector_radar.data.akshare_concept_history import (
        AkShareConceptHistoryClient,
    )

    client = AkShareConceptHistoryClient(
        client=FakeAkShare([bad_row]), cache_root=tmp_path
    )

    with pytest.raises(ValueError):
        client.get_history(
            board_code="300843.TI",
            board_name="5G",
            start_date="2026-06-01",
            end_date="2026-07-17",
            as_of_date="2026-07-17",
        )
