"""Tests for agent score merge coverage diagnostic script."""

import json
from pathlib import Path

import pytest

from scripts.analyze_agent_score_merge_coverage import (
    analyze_date,
    generate_markdown,
    main,
)


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_top30(codes, rank_hidden=True, merged=None):
    """Build a top30_candidates.json payload."""
    candidates = []
    for code in codes:
        c = {"code": code, "name": f"Stock{code}", "final_score": 70}
        if merged and code in merged:
            c["agent_score"] = merged[code]
        candidates.append(c)
    return {
        "schema_version": "1.0",
        "rank_hidden": rank_hidden,
        "candidates": candidates,
        "agent_score_merged": bool(merged),
        "agent_score_merge_count": len(merged) if merged else None,
    }


def _make_ranking(items):
    """Build an aihf_stock_ranking.json payload."""
    return {"items": items}


# ---------------------------------------------------------------------------
# analyze_date
# ---------------------------------------------------------------------------


def test_analyze_full_merge(tmp_path):
    """All candidates have matching ranking items with agent_score."""
    d = "2026-07-07"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(
        ["600001", "600002"], merged={"600001": 80, "600002": 70}
    ))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
        {"code": "600002", "agent_score": 70},
    ]))

    result = analyze_date(d, tmp_path)
    assert result["merge_status"] == "full"
    assert result["merged_count"] == 2
    assert result["candidate_count"] == 2
    assert result["missing_from_ranking_count"] == 0
    assert result["rank_hidden"] is True
    assert result["raw_rank_leaked"] is False


def test_analyze_partial_merge_lists_missing_codes(tmp_path):
    """Partial merge: some candidates not in ranking."""
    d = "2026-07-01"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(
        ["600001", "600002", "600003"]
    ))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
        {"code": "600002", "agent_score": 70},
        # 600003 not in ranking
    ]))

    result = analyze_date(d, tmp_path)
    assert result["merge_status"] == "pending"
    assert result["missing_from_ranking_count"] == 1
    assert "600003" in result["missing_from_ranking_codes"]
    assert result["ranking_extra_count"] == 0


def test_analyze_ranking_extra_codes(tmp_path):
    """Ranking has extra codes not in candidates."""
    d = "2026-06-29"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(["600001"]))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
        {"code": "999999", "agent_score": 50},  # extra
    ]))

    result = analyze_date(d, tmp_path)
    assert result["ranking_extra_count"] == 1
    assert "999999" in result["ranking_extra_codes"]
    assert result["merge_status"] == "pending"


def test_analyze_missing_ranking(tmp_path):
    """Missing ranking file."""
    d = "2026-07-02"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(["600001"]))

    result = analyze_date(d, tmp_path)
    assert result["merge_status"] == "missing_ranking"
    assert result["ranking_item_count"] == 0


def test_analyze_missing_top30(tmp_path):
    """Missing top30 file."""
    d = "2026-07-03"
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
    ]))

    result = analyze_date(d, tmp_path)
    assert result["merge_status"] == "missing_top30"


def test_analyze_raw_rank_leaked(tmp_path):
    """Detect raw rank field in candidates."""
    d = "2026-07-06"
    top30 = _make_top30(["600001"])
    top30["candidates"][0]["rank"] = 1  # leaked rank
    _write_json(tmp_path / d / "top30_candidates.json", top30)
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
    ]))

    result = analyze_date(d, tmp_path)
    assert result["raw_rank_leaked"] is True


# ---------------------------------------------------------------------------
# CLI --apply
# ---------------------------------------------------------------------------


def test_apply_writes_agent_score_fields(tmp_path):
    """--apply performs merge and writes agent_score into candidates."""
    d = "2026-07-07"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(["600001", "600002"]))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80, "risk_adjusted_score": 78, "risk_level": "low"},
        {"code": "600002", "agent_score": 60, "risk_adjusted_score": 58, "risk_level": "high"},
    ]))

    out_dir = tmp_path / "coverage"
    exit_code = main(["--dates", d, "--apply",
                       "--bridge-dir", str(tmp_path),
                       "--output-dir", str(out_dir)])
    assert exit_code == 0

    # Verify files written
    assert (out_dir / "agent_score_merge_coverage.json").exists()
    assert (out_dir / "agent_score_merge_coverage.md").exists()

    # Verify agent_score was merged
    enriched = json.loads((tmp_path / d / "top30_candidates.json").read_text("utf-8"))
    for c in enriched["candidates"]:
        assert "agent_score" in c
    assert enriched["agent_score_merged"] is True
    assert enriched["agent_score_merge_count"] == 2


def test_apply_does_not_leak_rank(tmp_path):
    """--apply does not introduce raw rank into candidates."""
    d = "2026-07-07"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(["600001"]))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"rank": 1, "code": "600001", "agent_score": 80},
    ]))

    out_dir = tmp_path / "coverage"
    main(["--dates", d, "--apply",
           "--bridge-dir", str(tmp_path),
           "--output-dir", str(out_dir)])

    enriched = json.loads((tmp_path / d / "top30_candidates.json").read_text("utf-8"))
    assert enriched.get("rank_hidden") is True
    for c in enriched["candidates"]:
        assert "rank" not in c


def test_apply_preserves_rank_hidden(tmp_path):
    """--apply keeps rank_hidden: true intact."""
    d = "2026-07-07"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(["600001"], rank_hidden=True))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
    ]))

    out_dir = tmp_path / "coverage"
    main(["--dates", d, "--apply",
           "--bridge-dir", str(tmp_path),
           "--output-dir", str(out_dir)])

    enriched = json.loads((tmp_path / d / "top30_candidates.json").read_text("utf-8"))
    assert enriched.get("rank_hidden") is True


def test_dry_run_does_not_modify_files(tmp_path):
    """Without --apply, no files are modified."""
    d = "2026-07-07"
    top30_path = tmp_path / d / "top30_candidates.json"
    _write_json(top30_path, _make_top30(["600001"]))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
    ]))

    out_dir = tmp_path / "coverage"
    main(["--dates", d,
           "--bridge-dir", str(tmp_path),
           "--output-dir", str(out_dir)])

    # top30 should be unchanged
    raw = json.loads(top30_path.read_text("utf-8"))
    assert raw.get("agent_score_merged") is False
    assert "agent_score" not in raw["candidates"][0]


def test_markdown_output_exists(tmp_path):
    """Markdown report is generated."""
    d = "2026-07-07"
    _write_json(tmp_path / d / "top30_candidates.json", _make_top30(["600001"]))
    _write_json(tmp_path / d / "aihf_stock_ranking.json", _make_ranking([
        {"code": "600001", "agent_score": 80},
    ]))

    out_dir = tmp_path / "coverage"
    main(["--dates", d,
           "--bridge-dir", str(tmp_path),
           "--output-dir", str(out_dir)])

    md = (out_dir / "agent_score_merge_coverage.md").read_text("utf-8")
    assert "Agent Score Merge Coverage Report" in md
    assert "2026-07-07" in md
    assert "Summary Table" in md
