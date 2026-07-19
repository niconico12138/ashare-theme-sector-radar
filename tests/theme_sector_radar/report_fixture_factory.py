from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return path


def minimal_sector_scores(date: str) -> dict[str, Any]:
    return {
        "as_of_date": date,
        "scores": [
            {
                "sector_name": "证券",
                "sector_type": "industry",
                "sector_selection_score": 78.0,
                "trend_continuation_score": 72.0,
                "short_term_burst_score": 64.0,
                "market_temperature_score": 58.0,
                "capital_flow_score": 61.0,
                "risk_score": 20.0,
                "history_days": 20,
                "actual_history_days": 18,
                "history_coverage_ratio": 0.9,
                "trend_breakdown": {"risk_penalty": 10.0},
            },
            {
                "sector_name": "银行",
                "sector_type": "industry",
                "sector_selection_score": 52.0,
                "trend_continuation_score": 55.0,
                "short_term_burst_score": 45.0,
                "market_temperature_score": 52.0,
                "capital_flow_score": 48.0,
                "risk_score": 30.0,
                "history_days": 16,
                "actual_history_days": 12,
                "history_coverage_ratio": 0.75,
                "trend_breakdown": {"risk_penalty": 25.0},
            },
        ],
    }


def build_sector_score_tree(root: Path, dates: Iterable[str]) -> dict[str, Path]:
    roots = {
        "sector_scores": root / "reports" / "sector_scores",
        "sector_research": root / "reports" / "full90" / "sector_research",
        "concept_rank": root / "reports" / "full_concept" / "unified_rank",
        "selection_validation": root / "reports" / "selection_validation",
        "unified": root / "reports" / "unified",
        "agent_bridge": root / "reports" / "agent_bridge",
        "theme_sector_radar": root / "reports" / "theme_sector_radar",
    }
    for date in dates:
        write_json(
            roots["sector_scores"] / date / "sector_scores.json",
            minimal_sector_scores(date),
        )
    return roots


def write_theme_snapshot(report_root: Path, date: str, profile: str) -> Path:
    return write_json(
        report_root / date / "theme_sector_radar.json",
        {
            "report_type": "theme_sector_radar",
            "as_of_date": date,
            "fixture_profile": profile,
            "industry_top": [{"sector_name": "证券", "score": 72.0}],
            "concept_top": [{"sector_name": "国企改革", "score": 65.0}],
        },
    )


def write_selection_validation(root: Path, date: str) -> Path:
    return write_json(
        root / date / "next_day_selection_validation.json",
        {
            "as_of": date,
            "coverage": {
                "total_candidates": 1,
                "data_available": 1,
                "data_missing": 0,
                "missing_codes": [],
            },
            "per_stock": [
                {
                    "code": "600000",
                    "name": "浦发银行",
                    "data_available": True,
                    "next_return_pct": 1.0,
                }
            ],
            "ranking_groups": {},
            "score_buckets": {},
            "categorical_groups": {},
        },
    )
