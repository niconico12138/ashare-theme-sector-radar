from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest


class FakeBoardBackend:
    def __init__(self, keys, records):
        self._keys = list(keys)
        self._records = deepcopy(records)
        self.patterns = []

    def keys(self, pattern):
        self.patterns.append(pattern)
        return list(self._keys)

    def get(self, key):
        return deepcopy(self._records[key])


def _concept_record(**overrides):
    row = {
        "code": "300843.TI",
        "name": "5G",
        "source": "ths",
        "category": "概念",
        "type": "concept",
        "group": "同花顺概念",
        "symbols": ["600050", "000063", "600050", "bad", "510300"],
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("board_type", "expected_prefix"),
    [
        ("concept", "板块:概念*"),
        ("sw_1", "板块:申万一级*"),
        ("sw_2", "板块:申万二级*"),
        ("sw_3", "板块:申万三级*"),
    ],
)
def test_board_client_uses_native_prefix_and_normalizes_without_fixed_count(
    board_type, expected_prefix
):
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    key = "板块:概念_5G:300843.TI"
    backend = FakeBoardBackend([key], {key: _concept_record(type=board_type)})
    client = StockDBBoardClient(backend=backend)

    boards = client.list_boards(board_type)

    assert backend.patterns == [expected_prefix]
    assert len(boards) == 1
    assert boards[0]["source_key"] == key
    assert boards[0]["symbols"] == ["000063", "600050"]
    assert boards[0]["normalization_audit"] == {
        "input_symbol_count": 5,
        "invalid_symbol_count": 2,
        "duplicate_symbol_count": 1,
    }
    source = Path(client.__class__.__module__.replace(".", "/") + ".py")
    project_root = Path(__file__).resolve().parents[2]
    assert "978" not in (project_root / source).read_text(encoding="utf-8")


def test_board_client_get_board_and_constituents_are_stable():
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    key = "板块:概念_5G:300843.TI"
    backend = FakeBoardBackend([key], {key: _concept_record()})
    client = StockDBBoardClient(backend=backend)

    board = client.get_board("300843.TI", board_type="concept")

    assert board["code"] == "300843.TI"
    assert board["name"] == "5G"
    assert board["source"] == "ths"
    assert board["category"] == "概念"
    assert board["type"] == "concept"
    assert board["group"] == "同花顺概念"
    assert client.get_constituents("5G", board_type="concept") == [
        "000063",
        "600050",
    ]
    assert len(board["raw_sha256"]) == 64


@pytest.mark.parametrize(
    "bad_record",
    [
        None,
        [],
        {},
        _concept_record(code=""),
        _concept_record(name=""),
        _concept_record(symbols=[]),
    ],
)
def test_board_client_rejects_malformed_records(bad_record):
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    key = "板块:概念_bad"
    client = StockDBBoardClient(backend=FakeBoardBackend([key], {key: bad_record}))

    with pytest.raises(ValueError):
        client.list_boards("concept")


def test_board_client_rejects_duplicate_board_identity():
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    keys = ["板块:概念_5G:a", "板块:概念_5G:b"]
    records = {key: _concept_record() for key in keys}
    client = StockDBBoardClient(backend=FakeBoardBackend(keys, records))

    with pytest.raises(ValueError, match="duplicate board"):
        client.list_boards("concept")


def test_board_client_rejects_unsupported_type_and_bad_key_list():
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    with pytest.raises(ValueError, match="unsupported board_type"):
        StockDBBoardClient(backend=FakeBoardBackend([], {})).list_boards("other")

    class BadBackend:
        def keys(self, _pattern):
            return "not-a-list"

    with pytest.raises(ValueError, match="keys result"):
        StockDBBoardClient(backend=BadBackend()).list_boards("concept")


def test_board_client_accepts_stockdb_query_result_iterable():
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    key = "板块:概念_5G:300843.TI"

    class QueryResult:
        def __iter__(self):
            return iter([key])

    class QueryResultBackend(FakeBoardBackend):
        def keys(self, pattern):
            self.patterns.append(pattern)
            return QueryResult()

    client = StockDBBoardClient(
        backend=QueryResultBackend([key], {key: _concept_record()})
    )

    assert client.get_constituents("5G", board_type="concept") == [
        "000063",
        "600050",
    ]


def test_board_client_unwraps_stockdb_mapping_like_query_result():
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    key = "板块:概念_5G:300843.TI"
    record = _concept_record()

    class QueryResult:
        def keys(self):
            return record.keys()

        def __getitem__(self, name):
            return record[name]

    class MappingBackend(FakeBoardBackend):
        def get(self, _key):
            return QueryResult()

    board = StockDBBoardClient(
        backend=MappingBackend([key], {key: record})
    ).get_board("5G", board_type="concept")

    assert board["code"] == "300843.TI"


def test_board_client_skips_non_stock_etf_only_board_with_audit():
    from theme_sector_radar.data.stockdb_board_client import StockDBBoardClient

    key = "板块:概念_T+0基金:301643.TI"
    client = StockDBBoardClient(
        backend=FakeBoardBackend(
            [key],
            {key: _concept_record(code="301643.TI", name="T+0基金", symbols=["159920", "510900"])},
        )
    )

    assert client.list_boards("concept") == []
    assert client.last_list_audit["skipped_non_stock_board_count"] == 1
