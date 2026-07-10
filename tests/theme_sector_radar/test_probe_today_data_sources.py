from scripts.probe_today_data_sources import build_probe_result
from scripts.probe_today_data_sources import build_stock_snapshot_result


class FakeStockDB:
    def __init__(self, latest):
        self.latest = latest

    def get_latest_daily_date(self):
        return self.latest


class FakeRealtime:
    def __init__(self, row_count=2):
        self.row_count = row_count

    def get_a_share_spot(self):
        return {
            "source": "akshare/stock_zh_a_spot",
            "data_semantics": "intraday_snapshot",
            "row_count": self.row_count,
            "fallback_used": True,
            "rows": [],
        }


def test_probe_prefers_stockdb_final_daily_when_fresh():
    result = build_probe_result("20260709", stockdb_client=FakeStockDB("20260709"), realtime_client=FakeRealtime())

    assert result["status"] == "final_daily_available"
    assert result["recommended_source"] == "stockdb"


def test_probe_uses_realtime_snapshot_when_stockdb_is_stale():
    result = build_probe_result("20260709", stockdb_client=FakeStockDB("20260708"), realtime_client=FakeRealtime(row_count=5000))

    assert result["status"] == "intraday_snapshot_available"
    assert result["recommended_source"] == "akshare/stock_zh_a_spot"
    assert result["data_semantics"] == "intraday_snapshot"


def test_probe_reports_unavailable_when_both_sources_fail():
    class BrokenRealtime:
        def get_a_share_spot(self):
            raise ConnectionError("network down")

    result = build_probe_result("20260709", stockdb_client=FakeStockDB("20260708"), realtime_client=BrokenRealtime())

    assert result["status"] == "today_data_unavailable"
    assert result["realtime_error"] == "network down"


def test_build_stock_snapshot_result_returns_intraday_snapshot():
    class FakeRealtimeWithStock:
        def get_stock_snapshot(self, code):
            return {"code": code, "latest_price": 10.5, "data_semantics": "intraday_snapshot"}

    result = build_stock_snapshot_result("600001", realtime_client=FakeRealtimeWithStock())

    assert result["status"] == "stock_intraday_snapshot_available"
    assert result["snapshot"]["code"] == "600001"
