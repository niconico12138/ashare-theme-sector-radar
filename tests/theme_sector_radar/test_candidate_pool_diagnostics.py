from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "analyze_candidate_pool_quality.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_candidate_pool_quality", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_pool_shortfall_explains_main_board_filter(monkeypatch, tmp_path):
    module = _load_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")
    out_dir = module.OUTPUT_DIR / "2026-07-08"
    out_dir.mkdir(parents=True)
    payload = {
        "candidate_count": 20,
        "selection_policy": {"stock_limit": 30, "main_board_only": True, "exclude_st": True},
        "selection_funnel": {
            "trend_pool": {
                "raw": 20,
                "eligible": 10,
                "selected_final": 10,
                "filtered_non_main_board": 8,
                "filtered_st": 1,
                "filtered_invalid_code": 1,
                "filtered_empty_name": 0,
            },
            "burst_pool": {
                "raw": 20,
                "eligible": 10,
                "selected_final": 10,
                "filtered_non_main_board": 9,
                "filtered_st": 0,
                "filtered_invalid_code": 1,
                "filtered_empty_name": 0,
            },
            "merge": {"before_dedup": 20, "duplicates_removed": 0, "after_dedup": 20, "final_count": 20},
            "top_loss_reasons": [{"reason": "non_main_board", "count": 17}],
        },
        "candidates": [
            {"code": f"600{i:03d}", "name": f"stock{i}", "source_pool": "trend", "boards": ["BoardA"]}
            for i in range(10)
        ] + [
            {"code": f"601{i:03d}", "name": f"stockb{i}", "source_pool": "burst", "boards": ["BoardB"]}
            for i in range(10)
        ],
    }
    (out_dir / "top30_candidates.json").write_text(json.dumps(payload), encoding="utf-8")

    result = module.analyze_candidate_pool_quality("2026-07-08")

    assert result["shortfall_analysis"]["target_count"] == 30
    assert result["shortfall_analysis"]["shortfall"] == 10
    assert result["filter_loss_totals"]["non_main_board"] == 17
    assert result["shortfall_analysis"]["dominant_loss_reason"] == "non_main_board"
    assert "main-board" in result["shortfall_analysis"]["recommendation"]
    assert "candidate_count_below_target" in result["quality_risk_tags"]

