import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import export_top30_candidates as export_candidates

def test_export_sample_top30_writes_demo_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(export_candidates, "OUTPUT_DIR", tmp_path / "agent_bridge")

    top30_path = export_candidates.export_sample_top30(
        "2026-06-28",
        stock_limit=3,
        agent_stock_limit=2,
    )

    data = json.loads(top30_path.read_text(encoding="utf-8"))
    assert data["sample_mode"] is True
    assert data["rank_hidden"] is True
    assert data["candidate_count"] == 3
    assert data["production_change_allowed"] is False
    assert data["shadow_score_policy"]["v5_status"] == "review_ready_shadow_only"
    assert all("regime_router_shadow_score_v5" in c for c in data["candidates"])

    request = json.loads((top30_path.parent / "aihf_request.json").read_text(encoding="utf-8"))
    assert request["sample_mode"] is True
    assert request["llm_enabled"] is False
    assert len(request["stocks"]) == 2


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


def test_generate_aihf_request_limits_agent_stock_count(tmp_path, monkeypatch):
    top30_path = tmp_path / "top30_candidates.json"
    top30_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "code": f"600{i:03d}",
                        "name": f"trend{i}",
                        "source_pool": "trend",
                        "trend_score": i,
                        "burst_score": 0,
                        "final_score": 100 - i,
                    }
                    for i in range(1, 16)
                ]
                + [
                    {
                        "code": f"601{i:03d}",
                        "name": f"burst{i}",
                        "source_pool": "burst",
                        "trend_score": 40,
                        "burst_score": 80,
                        "final_score": 90 - i,
                    }
                    for i in range(1, 16)
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(export_candidates, "_build_board_context", lambda date: {"industry_top": [], "concept_top": []})

    request_path = export_candidates.generate_aihf_request(
        top30_path,
        "2026-07-07",
        agent_preset="selected",
        agent_stock_limit=10,
    )

    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert len(request["stocks"]) == 10
    assert request["agent_stock_limit"] == 10
    assert request["source_candidate_count"] == 30
    assert request["agent_skipped_count"] == 20
    assert len([s for s in request["stocks"] if s["source_pool"] == "trend"]) == 5
    assert len([s for s in request["stocks"] if s["source_pool"] == "burst"]) == 5
    assert [s["code"] for s in request["stocks"][:5]] == [f"600{i:03d}" for i in range(1, 6)]

    top30 = json.loads(top30_path.read_text(encoding="utf-8"))
    assert top30["agent_analysis_policy"]["agent_stock_limit"] == 10
    assert top30["agent_analysis_policy"]["agent_analyzed_count"] == 10
    assert top30["agent_analysis_policy"]["agent_skipped_count"] == 20
    analyzed = [c for c in top30["candidates"] if c["agent_analysis_status"] == "pending_agent_analysis"]
    skipped = [c for c in top30["candidates"] if c["agent_analysis_status"] == "skipped_by_agent_stock_limit"]
    assert len(analyzed) == 10
    assert len(skipped) == 20


# ======================================================================
# New scoring field tests
# ======================================================================


def test_enrich_candidates_adds_all_new_fields():
    """enrich_candidates_with_scoring should add all required new fields."""
    candidates = [
        {
            "code": "600001",
            "name": "测试股A",
            "boards": ["半导体"],
            "change_pct": 3.0,
            "amount": 50_000_000,
            "turnover_rate": 2.0,
            "sector_burst_score": 65.0,
            "sector_trend_score": 70.0,
            "final_score": 75.0,
        },
        {
            "code": "600002",
            "name": "测试股B",
            "boards": ["半导体"],
            "change_pct": 1.0,
            "amount": 30_000_000,
            "turnover_rate": 1.5,
            "sector_burst_score": 50.0,
            "sector_trend_score": 55.0,
            "final_score": 55.0,
        },
    ]
    enriched = export_candidates.enrich_candidates_with_scoring(candidates)

    required_fields = [
        "stock_short_score", "stock_short_breakdown", "stock_short_tags",
        "stock_trend_score", "stock_trend_breakdown", "stock_trend_tags",
        "sector_leader_score", "sector_role", "leader_tags",
        "risk_penalty_score", "risk_tags", "trade_eligibility", "invalid_reason",
        "decision_score", "decision_breakdown",
    ]
    for c in enriched:
        for field in required_fields:
            assert field in c, f"Missing field: {field}"


def test_enrich_empty_list():
    """enrich_candidates_with_scoring should handle empty list."""
    result = export_candidates.enrich_candidates_with_scoring([])
    assert result == []


def test_enrich_st_stock_gets_invalid():
    """ST stock should get trade_eligibility=invalid after enrichment."""
    candidates = [
        {
            "code": "600001",
            "name": "*ST退市",
            "boards": ["测试"],
            "change_pct": 5.0,
            "amount": 50_000_000,
        },
    ]
    enriched = export_candidates.enrich_candidates_with_scoring(candidates)
    assert enriched[0]["trade_eligibility"] == "invalid"


def test_enrich_sector_leader_score_differentiation():
    """Within same sector, leader should score higher than laggard."""
    candidates = [
        {
            "code": "600001", "name": "龙头", "boards": ["板块A"],
            "change_pct": 8.0, "amount": 100_000_000, "stock_short_score": 80,
            "stock_trend_score": 75, "final_score": 80,
        },
        {
            "code": "600002", "name": "跟风", "boards": ["板块A"],
            "change_pct": 1.0, "amount": 20_000_000, "stock_short_score": 40,
            "stock_trend_score": 40, "final_score": 30,
        },
    ]
    enriched = export_candidates.enrich_candidates_with_scoring(candidates)
    by_code = {c["code"]: c for c in enriched}
    assert by_code["600001"]["sector_leader_score"] > by_code["600002"]["sector_leader_score"]
    assert by_code["600001"]["sector_role"] == "leader"


def test_aihf_request_includes_new_fields(tmp_path, monkeypatch):
    """aihf_request.json stocks should include new scoring fields."""
    top30_path = tmp_path / "top30_candidates.json"
    top30_path.write_text(
        json.dumps({
            "candidates": [
                {
                    "code": "600001",
                    "name": "测试股",
                    "source_pool": "trend",
                    "trend_score": 70.0,
                    "burst_score": 60.0,
                    "final_score": 75.0,
                    "stock_short_score": 68.0,
                    "stock_trend_score": 72.0,
                    "sector_leader_score": 80.0,
                    "decision_score": 70.0,
                    "trade_eligibility": "focus",
                    "risk_tags": [],
                },
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(export_candidates, "_build_board_context", lambda date: {"industry_top": [], "concept_top": []})

    request_path = export_candidates.generate_aihf_request(
        top30_path, "2026-07-07", agent_stock_limit=10,
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    stock = request["stocks"][0]
    assert "stock_short_score" in stock
    assert "stock_trend_score" in stock
    assert "sector_leader_score" in stock
    assert "decision_score" in stock
    assert "trade_eligibility" in stock
    assert "risk_tags" in stock


def test_top30_still_has_30_candidates(tmp_path, monkeypatch):
    """top30_candidates.json should still contain up to 30 candidates."""
    unified_dir = tmp_path / "reports" / "unified" / "2026-07-07"
    unified_dir.mkdir(parents=True)
    trend = [
        {"code": f"600{i:03d}", "name": f"趋势{i}", "sector_name": "趋势板块",
         "sector_trend_score": 70.0, "sector_burst_score": 40.0, "final_score": 80.0 - i}
        for i in range(1, 18)
    ]
    burst = [
        {"code": f"601{i:03d}", "name": f"短线{i}", "sector_name": "短线板块",
         "sector_trend_score": 40.0, "sector_burst_score": 80.0, "final_score": 75.0 - i}
        for i in range(1, 18)
    ]
    (unified_dir / "unified_report.json").write_text(
        json.dumps({"trend_top_stocks": trend, "burst_top_stocks": burst}, ensure_ascii=False),
        encoding="utf-8",
    )

    orig_unified_dir = export_candidates.UNIFIED_DIR
    export_candidates.UNIFIED_DIR = tmp_path / "reports" / "unified"
    try:
        candidates, _ = export_candidates.load_unified_candidates("2026-07-07")
    finally:
        export_candidates.UNIFIED_DIR = orig_unified_dir

    assert len(candidates) == 30


def test_agent_stock_limit_10_in_request(tmp_path, monkeypatch):
    """aihf_request.json should contain exactly 10 stocks by default."""
    top30_path = tmp_path / "top30_candidates.json"
    candidates = [
        {
            "code": f"600{i:03d}",
            "name": f"stock{i}",
            "source_pool": "trend" if i <= 15 else "burst",
            "trend_score": 60,
            "burst_score": 50,
            "final_score": 70 - i,
        }
        for i in range(1, 31)
    ]
    top30_path.write_text(
        json.dumps({"candidates": candidates}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(export_candidates, "_build_board_context", lambda date: {"industry_top": [], "concept_top": []})

    request_path = export_candidates.generate_aihf_request(
        top30_path, "2026-07-07", agent_stock_limit=10,
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert len(request["stocks"]) == 10

