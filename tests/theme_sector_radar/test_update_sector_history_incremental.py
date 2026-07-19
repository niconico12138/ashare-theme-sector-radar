import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from update_sector_history_incremental import (  # noqa: E402
    merge_history_documents,
    validate_history_document,
)


def _document(name, records, *, start="2026-07-07", end="2026-07-08"):
    return {
        "sector_name": name,
        "sector_code": "",
        "sector_type": "industry",
        "source": "akshare/ths",
        "start_date": start,
        "end_date": end,
        "fetched_at": "2026-07-09T00:00:00",
        "price_change_available": False,
        "records": records,
    }


def _record(date, close):
    return {
        "日期": date,
        "开盘价": close,
        "最高价": close + 1,
        "最低价": close - 1,
        "收盘价": close,
        "成交量": 100,
        "成交额": 1000.0,
    }


def test_merge_appends_increment_without_changing_existing_rows():
    existing = _document("测试行业", [_record("2026-07-07", 10), _record("2026-07-08", 11)])
    increment = _document(
        "测试行业",
        [_record("2026-07-09", 12), _record("2026-07-10", 13)],
        start="2026-07-09",
        end="2026-07-10",
    )

    merged = merge_history_documents(existing, increment)

    assert merged["records"][:2] == existing["records"]
    assert [row["日期"] for row in merged["records"]] == [
        "2026-07-07",
        "2026-07-08",
        "2026-07-09",
        "2026-07-10",
    ]
    assert merged["start_date"] == "2026-07-07"
    assert merged["end_date"] == "2026-07-10"


def test_merge_rejects_conflicting_overlap():
    existing = _document(
        "测试行业",
        [_record("2026-07-08", 11)],
        start="2026-07-08",
        end="2026-07-08",
    )
    increment = _document(
        "测试行业",
        [_record("2026-07-08", 99)],
        start="2026-07-08",
        end="2026-07-08",
    )

    with pytest.raises(ValueError, match="conflicting record"):
        merge_history_documents(existing, increment)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda row: row.update({"收盘价": float("nan")}), "finite"),
        (lambda row: row.update({"最高价": 8}), "OHLC"),
        (lambda row: row.update({"日期": "2026-7-8"}), "ISO"),
    ],
)
def test_validate_history_document_rejects_untrusted_rows(mutation, match):
    row = _record("2026-07-08", 11)
    mutation(row)
    document = _document("测试行业", [row])

    with pytest.raises(ValueError, match=match):
        validate_history_document(document, expected_name="测试行业")


def test_validate_history_document_rejects_duplicate_dates():
    row = _record("2026-07-08", 11)
    document = _document("测试行业", [row, dict(row)])

    with pytest.raises(ValueError, match="duplicate"):
        validate_history_document(document, expected_name="测试行业")


def test_validate_history_document_accepts_non_trading_request_start():
    document = _document(
        "测试行业",
        [_record("2026-07-06", 10), _record("2026-07-07", 11)],
        start="2026-07-04",
        end="2026-07-07",
    )

    assert validate_history_document(document, expected_name="测试行业") == [
        "2026-07-06",
        "2026-07-07",
    ]
