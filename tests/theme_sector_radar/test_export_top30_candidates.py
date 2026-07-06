import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import export_top30_candidates as export_candidates


def test_load_unified_candidates_preserves_sector_scores(tmp_path):
    unified_dir = tmp_path / "reports" / "unified" / "2026-07-02"
    unified_dir.mkdir(parents=True)
    (unified_dir / "unified_report.json").write_text(
        json.dumps(
            {
                "trend_top_stocks": [
                    {
                        "code": "002635",
                        "name": "安洁科技",
                        "sector_name": "电子化学品",
                        "sector_type": "industry",
                        "sector_trend_score": 70.9,
                        "sector_burst_score": 82.0,
                    }
                ],
                "burst_top_stocks": [
                    {
                        "code": "002294",
                        "name": "信立泰",
                        "sector_name": "生物制品",
                        "sector_type": "concept",
                        "sector_trend_score": 54.0,
                        "sector_burst_score": 121.2,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    orig_unified_dir = export_candidates.UNIFIED_DIR
    export_candidates.UNIFIED_DIR = tmp_path / "reports" / "unified"
    try:
        candidates, funnel = export_candidates.load_unified_candidates("2026-07-02")
    finally:
        export_candidates.UNIFIED_DIR = orig_unified_dir

    assert candidates[0]["trend_score"] == 70.9
    assert candidates[0]["burst_score"] == 82.0
    assert candidates[1]["trend_score"] == 54.0
    assert candidates[1]["burst_score"] == 121.2


def test_build_candidate_entry_uses_sector_score_aliases():
    entry = export_candidates.build_candidate_entry(
        {
            "code": "002294",
            "name": "信立泰",
            "sector_name": "生物制品",
            "sector_type": "concept",
            "sector_trend_score": 54.0,
            "sector_burst_score": 121.2,
        },
        {
            "industries": [],
            "concepts": [
                {
                    "name": "生物制品",
                    "agent_label": "trend_confirmed_but_strength_limited",
                }
            ],
        },
        1,
    )

    assert entry["trend_score"] == 54.0
    assert entry["burst_score"] == 121.2
    assert entry["source_pool"] == "both"


def test_load_unified_candidates_keeps_only_main_board_codes(tmp_path):
    unified_dir = tmp_path / "reports" / "unified" / "2026-07-02"
    unified_dir.mkdir(parents=True)
    stocks = [
        {"code": "600360", "name": "华微电子", "sector_name": "电子化学品", "sector_trend_score": 70.9, "sector_burst_score": 82.0},
        {"code": "002294", "name": "信立泰", "sector_name": "生物制品", "sector_trend_score": 54.0, "sector_burst_score": 121.2},
        {"code": "300558", "name": "贝达药业", "sector_name": "生物制品", "sector_trend_score": 54.0, "sector_burst_score": 121.2},
        {"code": "301379", "name": "天山电子", "sector_name": "电子化学品", "sector_trend_score": 70.9, "sector_burst_score": 82.0},
        {"code": "688068", "name": "热景生物", "sector_name": "生物制品", "sector_trend_score": 54.0, "sector_burst_score": 121.2},
        {"code": "833000", "name": "北交样例", "sector_name": "示例", "sector_trend_score": 50.0, "sector_burst_score": 50.0},
    ]
    (unified_dir / "unified_report.json").write_text(
        json.dumps({"trend_top_stocks": stocks, "burst_top_stocks": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    orig_unified_dir = export_candidates.UNIFIED_DIR
    export_candidates.UNIFIED_DIR = tmp_path / "reports" / "unified"
    try:
        candidates, funnel = export_candidates.load_unified_candidates("2026-07-02")
    finally:
        export_candidates.UNIFIED_DIR = orig_unified_dir

    assert [c["code"] for c in candidates] == ["600360", "002294"]


def test_load_unified_candidates_limits_each_pool_before_merge(tmp_path):
    unified_dir = tmp_path / "reports" / "unified" / "2026-07-02"
    unified_dir.mkdir(parents=True)

    trend = [
        {
            "code": f"600{i:03d}",
            "name": f"趋势{i}",
            "sector_name": "趋势板块",
            "sector_trend_score": 70.0,
            "sector_burst_score": 40.0,
        }
        for i in range(1, 18)
    ]
    burst = [
        {
            "code": f"601{i:03d}",
            "name": f"短线{i}",
            "sector_name": "短线板块",
            "sector_trend_score": 40.0,
            "sector_burst_score": 80.0,
        }
        for i in range(1, 18)
    ]
    (unified_dir / "unified_report.json").write_text(
        json.dumps({"trend_top_stocks": trend, "burst_top_stocks": burst}, ensure_ascii=False),
        encoding="utf-8",
    )

    orig_unified_dir = export_candidates.UNIFIED_DIR
    export_candidates.UNIFIED_DIR = tmp_path / "reports" / "unified"
    try:
        candidates, funnel = export_candidates.load_unified_candidates("2026-07-02")
    finally:
        export_candidates.UNIFIED_DIR = orig_unified_dir

    codes = [c["code"] for c in candidates]
    assert len(candidates) == 30
    assert "600015" in codes
    assert "601015" in codes
    assert "600016" not in codes
    assert "601016" not in codes



def test_build_candidate_entry_preserves_stock_score_fields():
    import export_top30_candidates as exp

    entry = exp.build_candidate_entry(
        {
            "code": "000536",
            "name": "华映科技",
            "sector_name": "光刻胶",
            "sector_type": "concept",
            "trend_score": 62.45,
            "burst_score": 30.3,
            "relevance_score": 0.833,
            "quant_score": 61.2,
            "final_score": 70.1,
        },
        {"industries": [], "concepts": [{"name": "光刻胶", "agent_label": "trend_confirmed"}]},
        1,
    )

    assert entry["trend_score"] == 62.45
    assert entry["burst_score"] == 30.3
    assert entry["relevance_score"] == 0.833
    assert entry["quant_score"] == 61.2
    assert entry["final_score"] == 70.1
