import json

import pytest

from theme_sector_radar.history.sector_trend_history import load_sector_trend_history
from theme_sector_radar.agents.ranking_report.sector_ranking_agent import (
    generate_sector_ranking,
)
from theme_sector_radar.models import SectorSnapshot, SectorType


def test_sector_trend_history_excludes_records_after_as_of_date(tmp_path):
    root = tmp_path / "sector_history" / "industry"
    root.mkdir(parents=True)
    payload = {
        "sector_name": "测试行业",
        "records": [
            {"date": "2026-07-01", "close": 100.0},
            {"date": "2026-07-02", "close": 101.0},
            {"date": "2026-07-03", "close": 202.0},
        ],
    }
    (root / "测试行业.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    history, warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-02",
    )

    assert warnings == []
    assert history["测试行业"]["recent_dates"] == ["2026-07-02"]
    assert history["测试行业"]["recent_returns"] == pytest.approx([1.0])


def test_future_history_records_do_not_change_as_of_three_layer_shadow(tmp_path):
    root = tmp_path / "sector_history" / "industry"
    root.mkdir(parents=True)
    sector_names = ("Industry A", "Industry B")

    def write_history(include_future: bool) -> None:
        for index, name in enumerate(sector_names):
            records = [
                {
                    "date": f"2026-01-{day:02d}",
                    "close": 100.0 + (day * (index + 1)),
                }
                for day in range(1, 22)
            ]
            if include_future:
                records.append(
                    {"date": "2026-01-22", "close": 1_000.0 - index * 900.0}
                )
            (root / f"{name}.json").write_text(
                json.dumps({"sector_name": name, "records": records}),
                encoding="utf-8",
            )

    sectors = [
        SectorSnapshot(
            sector_id=f"BK000{index + 1}",
            name=name,
            type=SectorType.INDUSTRY,
            price_change_pct=1.0,
            turnover=1_000_000_000,
            main_net_inflow=0.0,
            data_quality_score=80.0,
        )
        for index, name in enumerate(sector_names)
    ]

    write_history(include_future=False)
    before_history, before_warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-01-21",
    )
    before = generate_sector_ranking(
        sectors, [], top_n=2, industry_history=before_history
    )

    write_history(include_future=True)
    after_history, after_warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-01-21",
    )
    after = generate_sector_ranking(
        sectors, [], top_n=2, industry_history=after_history
    )

    assert before_warnings == after_warnings == []
    before_shadows = {
        row["name"]: row["score_breakdown"]["three_layer_shadow"]
        for row in before.data["industry_top"]
    }
    after_shadows = {
        row["name"]: row["score_breakdown"]["three_layer_shadow"]
        for row in after.data["industry_top"]
    }
    assert after_shadows == before_shadows


def test_sector_trend_history_rejects_duplicate_dates_per_document(tmp_path):
    root = tmp_path / "sector_history" / "industry"
    root.mkdir(parents=True)
    payload = {
        "sector_name": "测试行业",
        "records": [
            {"date": "2026-07-01", "close": 100.0},
            {"date": "2026-07-01", "close": 101.0},
        ],
    }
    (root / "测试行业.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    history, warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-02",
    )

    assert history == {}
    assert len(warnings) == 1
    assert "duplicate history date" in warnings[0]


def test_sector_trend_history_does_not_use_a_stale_window(tmp_path):
    root = tmp_path / "sector_history" / "industry"
    root.mkdir(parents=True)
    payload = {
        "sector_name": "测试行业",
        "records": [
            {"date": "2026-07-01", "close": 100.0},
            {"date": "2026-07-02", "close": 101.0},
        ],
    }
    (root / "测试行业.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    history, warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-03",
    )

    assert history == {}
    assert warnings == []


def test_sector_trend_history_uses_closes_as_the_canonical_return_source(tmp_path):
    root = tmp_path / "sector_history" / "industry"
    root.mkdir(parents=True)
    payload = {
        "sector_name": "测试行业",
        "records": [
            {"date": "2026-07-01", "close": 100.0, "change_pct": 99.0},
            {"date": "2026-07-02", "close": 101.0, "change_pct": 99.0},
        ],
    }
    (root / "测试行业.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    history, warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-02",
    )

    assert warnings == []
    assert history["测试行业"]["recent_returns"] == pytest.approx([1.0])


def test_sector_trend_history_rejects_non_iso_dates(tmp_path):
    root = tmp_path / "sector_history" / "industry"
    root.mkdir(parents=True)
    payload = {
        "sector_name": "测试行业",
        "records": [
            {"date": "07/18/2026", "close": 200.0},
            {"date": "2026-07-17", "close": 100.0},
        ],
    }
    (root / "测试行业.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    history, warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-17",
    )

    assert history == {}
    assert len(warnings) == 1
    assert "ISO date" in warnings[0]


def test_sector_trend_history_rejects_non_finite_derived_return(tmp_path):
    root = tmp_path / "sector_history" / "industry"
    root.mkdir(parents=True)
    (root / "extreme.json").write_text(
        json.dumps(
            {
                "sector_name": "Extreme Industry",
                "records": [
                    {"date": "2026-07-01", "close": 1e-300},
                    {"date": "2026-07-02", "close": 1e300},
                ],
            }
        ),
        encoding="utf-8",
    )

    history, warnings = load_sector_trend_history(
        tmp_path / "sector_history",
        sector_type=SectorType.INDUSTRY,
        as_of_date="2026-07-02",
    )

    assert history == {}
    assert len(warnings) == 1
    assert "trusted daily return range" in warnings[0]
