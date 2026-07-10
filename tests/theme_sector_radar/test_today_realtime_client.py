import pandas as pd

from theme_sector_radar.data.today_realtime_client import TodayRealtimeClient


class FakeAk:
    def __init__(self, em_error=False):
        self.em_error = em_error

    def stock_zh_a_spot_em(self):
        if self.em_error:
            raise ConnectionError("eastmoney down")
        return pd.DataFrame(
            [
                {"代码": "600001", "名称": "测试A", "最新价": 10.5, "涨跌幅": 1.2, "成交量": 1000, "成交额": 2000},
            ]
        )

    def stock_zh_a_spot(self):
        return pd.DataFrame(
            [
                {"代码": "600002", "名称": "测试B", "最新价": 20.5, "涨跌幅": -0.5, "成交量": 3000, "成交额": 4000},
            ]
        )


def test_realtime_client_uses_em_when_available():
    client = TodayRealtimeClient(ak_client=FakeAk())

    result = client.get_a_share_spot()

    assert result["source"] == "akshare/stock_zh_a_spot_em"
    assert result["data_semantics"] == "intraday_snapshot"
    assert result["rows"][0]["code"] == "600001"
    assert result["rows"][0]["latest_price"] == 10.5


def test_realtime_client_supports_standard_chinese_em_columns():
    class StandardChineseAk:
        def stock_zh_a_spot_em(self):
            return pd.DataFrame(
                [
                    {"代码": "600003", "名称": "测试C", "最新价": 30.5, "涨跌幅": 2.5, "成交量": 5000, "成交额": 6000},
                ]
            )

    client = TodayRealtimeClient(ak_client=StandardChineseAk())

    result = client.get_a_share_spot()

    assert result["rows"][0]["code"] == "600003"
    assert result["rows"][0]["name"] == "测试C"
    assert result["rows"][0]["latest_price"] == 30.5
    assert result["rows"][0]["change_pct"] == 2.5
    assert result["rows"][0]["volume"] == 5000
    assert result["rows"][0]["amount"] == 6000


def test_realtime_client_falls_back_to_legacy_spot_when_em_fails():
    client = TodayRealtimeClient(ak_client=FakeAk(em_error=True))

    result = client.get_a_share_spot()

    assert result["source"] == "akshare/stock_zh_a_spot"
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "eastmoney down"
    assert result["rows"][0]["code"] == "600002"


def test_get_stock_snapshot_filters_by_code():
    client = TodayRealtimeClient(ak_client=FakeAk(em_error=True))

    snapshot = client.get_stock_snapshot("600002")

    assert snapshot["code"] == "600002"
    assert snapshot["name"] == "测试B"
    assert snapshot["data_semantics"] == "intraday_snapshot"


def test_get_stock_snapshot_returns_none_for_missing_code():
    client = TodayRealtimeClient(ak_client=FakeAk(em_error=True))

    assert client.get_stock_snapshot("600999") is None
