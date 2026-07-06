from theme_sector_radar.agents.sector_scoring import calculate_sector_scores
from theme_sector_radar.models import SectorScore, SectorType
from theme_sector_radar.reports.sector_score_report import generate_sector_score_report


def test_sector_score_json_includes_chinese_level_labels():
    sector = SectorScore(
        sector_id="test_sector",
        name="测试板块",
        type=SectorType.INDUSTRY,
        score=80.0,
        positive_score=80.0,
        risk_penalty=0.0,
        data_quality_score=80.0,
    )

    result = calculate_sector_scores(
        radar_sectors=[sector],
        history_data={
            "测试板块": {
                "recent_returns": [1.0, 1.2, 0.8, 1.1, 0.9],
                "total_return": 5.0,
                "positive_days": 5,
                "total_days": 5,
                "max_drawdown": -0.5,
                "volatility": 0.2,
                "history_days": 5,
            }
        },
        sector_type=SectorType.INDUSTRY,
    )

    score = result.data["scores"][0]
    assert score["selection_level_cn"] in {"重点观察", "观察", "中性", "降温", "偏弱"}
    assert score["trend_level_cn"] == score["selection_level_cn"]
    assert score["burst_level_cn"] in {"短线强势", "短线活跃", "短线中性", "短线降温", "短线偏弱"}
    assert score["selection_level"] in {"strong_watch", "watch", "neutral", "cooling", "avoid"}
    assert score["burst_level"].startswith("burst_")


def test_sector_score_markdown_uses_chinese_level_labels():
    report = generate_sector_score_report(
        {
            "report_type": "sector_scores",
            "as_of_date": "2026-06-30",
            "updated_at": "2026-06-30T16:00:00",
            "metadata": {"sector_type": "industry", "top_n": 1},
            "scores": [
                {
                    "sector_name": "测试板块",
                    "sector_selection_score": 82.0,
                    "selection_level": "strong_watch",
                    "trend_continuation_score": 82.0,
                    "trend_level": "strong_watch",
                    "short_term_burst_score": 40.0,
                    "burst_level": "burst_fading",
                    "score_interpretation": {"profile": "neutral"},
                    "trend_breakdown": {},
                    "burst_breakdown": {},
                }
            ],
        }
    )

    assert "重点观察" in report
    assert "短线降温" in report
    assert "| 测试板块 | 82.0 | 重点观察 | 40.0 | 短线降温 |" in report
