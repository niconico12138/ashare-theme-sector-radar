import json
from pathlib import Path

from theme_sector_radar.agents.data.data_reliability_agent import calculate_data_reliability
from theme_sector_radar.models import SectorSnapshot, SectorType
from theme_sector_radar.pipeline import _load_sector_history_fallback


def _write_history(root: Path, sector_type: str, name: str, closes: list[tuple[str, float]]):
    history_dir = root / "sector_history" / sector_type
    history_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for date, close in closes:
        records.append({
            "日期": date,
            "开盘价": close - 1,
            "最高价": close + 1,
            "最低价": close - 2,
            "收盘价": close,
            "成交量": 1000,
            "成交额": close * 10000,
        })
    payload = {
        "sector_name": name,
        "sector_type": sector_type,
        "source": "akshare/ths",
        "records": records,
    }
    (history_dir / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_load_sector_history_fallback_uses_latest_record_before_as_of_date(tmp_path):
    _write_history(
        tmp_path,
        "industry",
        "测试行业A",
        [
            ("2026-06-28", 100.0),
            ("2026-06-29", 110.0),
            ("2026-07-02", 200.0),
        ],
    )

    sectors, meta = _load_sector_history_fallback(
        cache_dir=str(tmp_path),
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-01",
        top_n=10,
    )

    assert len(sectors) == 1
    assert sectors[0].name == "测试行业A"
    assert sectors[0].updated_at == "2026-06-29"
    assert sectors[0].price_change_pct == 10.0
    assert sectors[0].turnover == 1100000.0
    assert sectors[0].data_sources == ["sector_history/ths_industry_index"]
    assert sectors[0].data_quality_score >= 80
    assert meta["source_as_of_date"] == "2026-06-29"


def test_load_sector_history_fallback_sorts_by_latest_change(tmp_path):
    _write_history(tmp_path, "industry", "强行业", [("2026-06-28", 100.0), ("2026-06-29", 120.0)])
    _write_history(tmp_path, "industry", "弱行业", [("2026-06-28", 100.0), ("2026-06-29", 101.0)])

    sectors, meta = _load_sector_history_fallback(
        cache_dir=str(tmp_path),
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-01",
        top_n=1,
    )

    assert [s.name for s in sectors] == ["强行业"]
    assert meta["available_count"] == 2


def test_reliability_does_not_over_penalize_sector_history_without_constituents():
    sector = SectorSnapshot(
        sector_id="sector_history_industry_test",
        name="测试行业",
        type=SectorType.INDUSTRY,
        price_change_pct=3.5,
        turnover=1000000.0,
        constituents=[],
        data_sources=["sector_history/ths_industry_index"],
        updated_at="2026-07-01",
        data_quality_score=85.0,
    )

    output = calculate_data_reliability([sector])

    assert output.data_quality_score >= 80
    assert "无成分股数据" not in output.data["sector_scores"][sector.sector_id]["issues"]



def test_reliability_treats_ths_industry_as_index_data_without_constituents():
    sector = SectorSnapshot(
        sector_id="ths_industry_test",
        name="测试行业",
        type=SectorType.INDUSTRY,
        price_change_pct=2.1,
        turnover=0.0,
        constituents=[],
        data_sources=["akshare/ths_industry"],
        updated_at="2026-07-01T15:30:00",
        data_quality_score=60.0,
    )

    output = calculate_data_reliability([sector])

    assert output.data_quality_score >= 80
    assert "无成分股数据" not in output.data["sector_scores"][sector.sector_id]["issues"]



def test_ths_industry_snapshot_quality_is_usable_index_data():
    from theme_sector_radar.data.akshare_provider import AkShareProvider

    provider = AkShareProvider()
    sector = provider._normalize_ths_industry_sector({
        "板块名称": "测试行业",
        "涨跌幅": 2.5,
        "总成交额": 1000000.0,
    })

    assert sector.data_sources == ["akshare/ths_industry"]
    assert sector.price_change_available is True
    assert sector.data_quality_score >= 80
