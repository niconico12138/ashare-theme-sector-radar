from scripts.probe_minute_bar_sources import EastmoneyMinuteBarsClient, probe_minute_bars


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    trust_env = False

    def get(self, url, params, timeout):
        if "trends2" in url:
            return FakeResponse(
                {
                    "data": {
                        "trends": [
                            "2026-07-13 09:30,0.00,10.10,10.10,10.10,100,1010.0,10.10",
                            "2026-07-13 09:31,10.10,10.20,10.20,10.10,120,1224.0,10.15",
                        ]
                    }
                }
            )
        return FakeResponse(
            {
                "data": {
                    "klines": [
                        "2026-07-13 09:35,10.00,10.20,10.30,10.00,1000,10100.0,3.0,2.0,0.2,1.0",
                        "2026-07-13 09:40,10.20,10.25,10.30,10.10,1100,11200.0,2.0,0.5,0.05,1.1",
                    ]
                }
            }
        )


def test_eastmoney_minute_client_fetches_5m_and_1m_rows():
    client = EastmoneyMinuteBarsClient()
    client.session = FakeSession()

    bars_5m = client.get_stock_bars("600001", "20260713093000", "20260713150000", frequency="5m")
    bars_1m = client.get_stock_bars("600001", "20260713093000", "20260713150000", frequency="1m")

    assert len(bars_5m) == 2
    assert bars_5m[0]["date"] == "20260713093500"
    assert bars_5m[0]["amount"] == 10100.0
    assert len(bars_1m) == 2
    assert bars_1m[0]["date"] == "20260713093000"
    assert bars_1m[1]["close"] == 10.2


def test_probe_minute_bars_writes_paper_only_report(tmp_path, monkeypatch):
    class FakeClient(EastmoneyMinuteBarsClient):
        def __init__(self, timeout=20):
            self.timeout = timeout

        def get_stock_bars(self, code, start, end, frequency="5m", fq=None):
            if frequency == "1m":
                return []
            return [{"date": "202607130935", "close": 10.2, "amount": 1000.0}]

    monkeypatch.setattr("scripts.probe_minute_bar_sources.EastmoneyMinuteBarsClient", FakeClient)

    result = probe_minute_bars(
        codes=["600001"],
        dates=["2026-07-13"],
        frequencies=["5m", "1m"],
        output_dir=tmp_path,
    )

    assert result["json_path"].exists()
    report = result["report"]
    assert report["paper_trading_only"] is True
    assert report["no_execution_signals"] is True
    assert report["summary"]["ok_count"] == 1
    assert report["summary"]["empty_count"] == 1
