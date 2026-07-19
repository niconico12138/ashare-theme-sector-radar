from pathlib import Path

import pytest

from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient


def test_get_stock_bars_normalizes_projected_list_rows():
    class FakeSdk:
        def get_data(self, code, start, end, frequency="1d", fields=None, fq="qfq"):
            return [[20260708, "600001", "测试股票", 10.1, 10.8, 9.9, 10.5]]

    client = StockDBSdkClient(sdk_client=FakeSdk())

    bars = client.get_stock_bars(
        "600001",
        "20260708",
        "20260709",
        fields=("date", "code", "name", "open", "high", "low", "close"),
    )

    assert bars == [
        {
            "date": "20260708",
            "code": "600001",
            "name": "测试股票",
            "open": 10.1,
            "high": 10.8,
            "low": 9.9,
            "close": 10.5,
        }
    ]


def test_get_stock_bars_handles_batch_dict_response_for_requested_code():
    class FakeSdk:
        def get_data(self, code, start, end, frequency="1d", fields=None, fq="qfq"):
            return {
                "600001": [[20260708, "600001", 10.5]],
                "600002": [[20260708, "600002", 20.5]],
            }

    client = StockDBSdkClient(sdk_client=FakeSdk())

    bars = client.get_stock_bars("600001", "20260708", "20260709", fields=("date", "code", "close"))

    assert bars == [{"date": "20260708", "code": "600001", "close": 10.5}]


def test_get_latest_daily_date_uses_multiple_probe_codes_and_max_date():
    class FakeSdk:
        def get_data(self, code, **kwargs):
            dates = {
                "600519": [[20260707]],
                "600633": [[20260708]],
                "000001": [],
            }
            return dates[code]

    client = StockDBSdkClient(sdk_client=FakeSdk())

    assert client.get_latest_daily_date(codes=("600519", "600633", "000001")) == "20260708"


def test_get_latest_daily_date_ignores_failed_probe_codes():
    class FakeSdk:
        def get_data(self, code, **kwargs):
            if code == "600519":
                raise ConnectionError("temporary failure")
            return [[20260708]]

    client = StockDBSdkClient(sdk_client=FakeSdk())

    assert client.get_latest_daily_date(codes=("600519", "600633")) == "20260708"


def test_probe_freshness_reports_stale_status():
    class FakeSdk:
        def get_data(self, code, **kwargs):
            return [[20260707]]

    client = StockDBSdkClient(sdk_client=FakeSdk())

    result = client.probe_freshness(expected_date="20260708", codes=("600519",))

    assert result["ok"] is False
    assert result["latest_daily_date"] == "20260707"
    assert result["expected_date"] == "20260708"
    assert result["source"] == "stockdb-sdk"


def test_client_auto_discovers_complete_desktop_pybao_sdk(tmp_path, monkeypatch):
    sdk_dir = tmp_path / "Desktop" / "stockdb" / "pybao"
    sdk_dir.mkdir(parents=True)
    (sdk_dir / "stock_sdk.py").write_text(
        "class StockDBClient:\n"
        "    def __init__(self, host, port):\n"
        "        self.endpoint = (host, port)\n",
        encoding="utf-8",
    )
    (sdk_dir / "stockdb.pyd").write_bytes(b"test-placeholder")
    monkeypatch.delenv("STOCKDB_SDK_PATH", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    client = StockDBSdkClient()

    assert client._client.endpoint == ("127.0.0.1", 7899)


def test_client_rejects_incomplete_sdk_without_importing_same_named_package(
    tmp_path, monkeypatch
):
    sdk_dir = tmp_path / "incomplete"
    sdk_dir.mkdir()
    (sdk_dir / "stock_sdk.py").write_text(
        "raise AssertionError('must not import incomplete SDK')\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STOCKDB_SDK_PATH", str(sdk_dir))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "missing"))

    with pytest.raises(ImportError, match="stock_sdk.py and stockdb.pyd"):
        StockDBSdkClient()
