from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "run_daily_bridge_report.py"


def _load_bridge_module():
    spec = importlib.util.spec_from_file_location("run_daily_bridge_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Resume path basics
# ---------------------------------------------------------------------------


def test_run_phase24_scripts_resume_reuses_existing_outputs(monkeypatch, tmp_path):
    module = _load_bridge_module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "AIHEDGE_ROOT", tmp_path / "ai-hedge-fund")
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    out_dir = module.OUTPUT_DIR / "2026-07-08"
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {"candidates": []})
    ranking = {"items": [{"code": "000001"}], "run_meta": {"agent_count": 1}}
    _write_json(out_dir / "aihf_stock_ranking.json", ranking)

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run should not be called during resume")

    monkeypatch.setattr(module.subprocess, "run", fail_run)
    # Stubs for merge + calibration in resume path
    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", lambda *a, **k: True)
    monkeypatch.setattr(module, "find_forward_returns_file", lambda date: None)
    monkeypatch.setattr(module, "run_scoring_calibration", lambda date: None)

    result = module.run_phase24_scripts("2026-07-08", "selected", "real", resume=True)

    assert result["status"] == "ok"
    assert result["resume_used"] is True
    assert "top30_candidates.json" in result["cache_hits"]
    assert "aihf_stock_ranking.json" in result["cache_hits"]
    assert result["ranking"]["items"][0]["code"] == "000001"


def test_bridge_report_records_resume_metadata(monkeypatch, tmp_path):
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")
    out_dir = module.OUTPUT_DIR / "2026-07-08"
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {"candidates": []})

    report = module.build_bridge_report(
        "2026-07-08",
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {
            "status": "ok",
            "resume_used": True,
            "cache_hits": ["top30_candidates.json", "aihf_stock_ranking.json"],
            "ranking": {},
        },
    )

    assert report["execution"]["resume_used"] is True
    assert report["execution"]["cache_hits"] == ["top30_candidates.json", "aihf_stock_ranking.json"]


# ---------------------------------------------------------------------------
# Normal path: calibration AFTER merge
# ---------------------------------------------------------------------------


def test_run_phase24_scripts_calibration_runs_after_merge(monkeypatch, tmp_path):
    """Step 2.6 (calibration) must run after Step 2.5 (merge)."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "AIHEDGE_ROOT", tmp_path / "ai-hedge-fund")
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    bridge_script = module.AIHEDGE_ROOT / "scripts" / "run_stock_agent_bridge.py"
    bridge_script.parent.mkdir(parents=True)
    bridge_script.write_text("# bridge", encoding="utf-8")

    out_dir = module.OUTPUT_DIR / "2026-07-08"
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "aihf_request.json", {})

    call_order = []

    def fake_run(cmd, **kwargs):
        if "export_top30_candidates.py" in str(cmd):
            _write_json(out_dir / "top30_candidates.json",
                        {"candidates": [{"code": "600001", "final_score": 85}]})
            return module.subprocess.CompletedProcess(cmd, 0, stdout="top30 ok", stderr="")
        if "run_stock_agent_bridge" in str(cmd):
            _write_json(out_dir / "aihf_stock_ranking.json",
                        {"items": [{"code": "600001", "agent_score": 75}]})
            return module.subprocess.CompletedProcess(cmd, 0, stdout="aihf ok", stderr="")
        return module.subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def fake_merge(top30_path, ranking_path):
        call_order.append("merge")
        return True

    def fake_calibration(date):
        call_order.append("calibration")
        return tmp_path / "reports" / "scoring_calibration" / date / "scoring_calibration.json"

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "run_candidate_pool_quality_analysis", lambda date: None)
    monkeypatch.setattr(module, "run_forward_returns_builder", lambda date: None)
    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", fake_merge)
    monkeypatch.setattr(module, "run_scoring_calibration", fake_calibration)

    module.run_phase24_scripts("2026-07-08", "selected", "real")

    assert "merge" in call_order, "merge was never called"
    assert "calibration" in call_order, "calibration was never called"
    assert call_order.index("merge") < call_order.index("calibration"), (
        f"merge must run before calibration, got order: {call_order}"
    )


def test_run_phase24_scripts_passes_agent_stock_limit_to_export(monkeypatch, tmp_path):
    """Daily bridge keeps top30 but limits AIHF request size through export script."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "AIHEDGE_ROOT", tmp_path / "ai-hedge-fund")
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    bridge_script = module.AIHEDGE_ROOT / "scripts" / "run_stock_agent_bridge.py"
    bridge_script.parent.mkdir(parents=True)
    bridge_script.write_text("# bridge", encoding="utf-8")

    out_dir = module.OUTPUT_DIR / "2026-07-08"
    out_dir.mkdir(parents=True)
    export_cmds = []

    def fake_run(cmd, **kwargs):
        if "export_top30_candidates.py" in str(cmd):
            export_cmds.append(cmd)
            _write_json(out_dir / "top30_candidates.json", {
                "candidates": [{"code": f"600{i:03d}", "final_score": 100 - i} for i in range(1, 31)]
            })
            _write_json(out_dir / "aihf_request.json", {
                "stocks": [{"code": f"600{i:03d}"} for i in range(1, 11)]
            })
            return module.subprocess.CompletedProcess(cmd, 0, stdout="top30 ok", stderr="")
        if "run_stock_agent_bridge" in str(cmd):
            _write_json(out_dir / "aihf_stock_ranking.json", {
                "items": [{"code": f"600{i:03d}", "agent_score": 70} for i in range(1, 11)]
            })
            return module.subprocess.CompletedProcess(cmd, 0, stdout="aihf ok", stderr="")
        return module.subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "run_candidate_pool_quality_analysis", lambda date: None)
    monkeypatch.setattr(module, "run_forward_returns_builder", lambda date: None)
    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", lambda *a, **k: True)
    monkeypatch.setattr(module, "run_scoring_calibration", lambda date: None)

    result = module.run_phase24_scripts("2026-07-08", "selected", "real", agent_stock_limit=10)

    assert result["status"] == "ok"
    assert export_cmds
    cmd = [str(part) for part in export_cmds[0]]
    assert "--stock-limit" in cmd
    assert "30" in cmd
    assert "--agent-stock-limit" in cmd
    assert "10" in cmd


def test_run_phase24_scripts_generates_scoring_calibration_when_returns_exist(monkeypatch, tmp_path):
    module = _load_bridge_module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "AIHEDGE_ROOT", tmp_path / "ai-hedge-fund")
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")
    monkeypatch.setattr(module, "FORWARD_RETURNS_DIR", tmp_path / "reports" / "forward_returns")
    bridge_script = module.AIHEDGE_ROOT / "scripts" / "run_stock_agent_bridge.py"
    bridge_script.parent.mkdir(parents=True)
    bridge_script.write_text("# bridge", encoding="utf-8")
    out_dir = module.OUTPUT_DIR / "2026-07-08"
    out_dir.mkdir(parents=True)
    returns_dir = module.FORWARD_RETURNS_DIR / "2026-07-08"
    returns_dir.mkdir(parents=True)
    _write_json(returns_dir / "forward_returns.json", {"600001": {"1d": 3.0}})
    _write_json(out_dir / "aihf_request.json", {})

    calls = {"calibration": 0}

    def fake_run(cmd, **kwargs):
        if "export_top30_candidates.py" in str(cmd):
            _write_json(out_dir / "top30_candidates.json",
                        {"candidates": [{"code": "600001", "final_score": 85}]})
            return module.subprocess.CompletedProcess(cmd, 0, stdout="top30 ok", stderr="")
        if "run_stock_agent_bridge" in str(cmd):
            _write_json(out_dir / "aihf_stock_ranking.json", {"items": []})
            return module.subprocess.CompletedProcess(cmd, 0, stdout="aihf ok", stderr="")
        return module.subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def fake_calibration(date):
        calls["calibration"] += 1
        return tmp_path / "reports" / "scoring_calibration" / date / "scoring_calibration.json"

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "run_candidate_pool_quality_analysis", lambda date: None)
    monkeypatch.setattr(module, "run_forward_returns_builder", lambda date: returns_dir / "forward_returns.json")
    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", lambda *a, **k: True)
    monkeypatch.setattr(module, "run_scoring_calibration", fake_calibration)

    result = module.run_phase24_scripts("2026-07-08", "selected", "real")

    assert result["status"] == "ok"
    assert calls["calibration"] == 1
    assert result["scoring_calibration_path"].endswith("scoring_calibration.json")


def test_run_phase24_scripts_builds_forward_returns_before_calibration(monkeypatch, tmp_path):
    module = _load_bridge_module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "AIHEDGE_ROOT", tmp_path / "ai-hedge-fund")
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")
    monkeypatch.setattr(module, "FORWARD_RETURNS_DIR", tmp_path / "reports" / "forward_returns")
    bridge_script = module.AIHEDGE_ROOT / "scripts" / "run_stock_agent_bridge.py"
    bridge_script.parent.mkdir(parents=True)
    bridge_script.write_text("# bridge", encoding="utf-8")
    out_dir = module.OUTPUT_DIR / "2026-07-08"
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "aihf_request.json", {})

    calls = []

    def fake_run(cmd, **kwargs):
        if "export_top30_candidates.py" in str(cmd):
            _write_json(out_dir / "top30_candidates.json",
                        {"candidates": [{"code": "600001", "final_score": 85}]})
            return module.subprocess.CompletedProcess(cmd, 0, stdout="top30 ok", stderr="")
        if "run_stock_agent_bridge" in str(cmd):
            _write_json(out_dir / "aihf_stock_ranking.json", {"items": []})
            return module.subprocess.CompletedProcess(cmd, 0, stdout="aihf ok", stderr="")
        return module.subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def fake_forward_returns(date):
        calls.append("forward_returns")
        path = module.FORWARD_RETURNS_DIR / date / "forward_returns.json"
        path.parent.mkdir(parents=True)
        _write_json(path, {"forward_returns": {"600001": {"1d": 3.0}}})
        return path

    def fake_calibration(date):
        calls.append("calibration")
        return tmp_path / "reports" / "scoring_calibration" / date / "scoring_calibration.json"

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "run_candidate_pool_quality_analysis", lambda date: None)
    monkeypatch.setattr(module, "run_forward_returns_builder", fake_forward_returns)
    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", lambda *a, **k: True)
    monkeypatch.setattr(module, "run_scoring_calibration", fake_calibration)

    result = module.run_phase24_scripts("2026-07-08", "selected", "real")

    # forward_returns must come before calibration
    assert "forward_returns" in calls
    assert "calibration" in calls
    assert calls.index("forward_returns") < calls.index("calibration")
    assert result["forward_returns_path"].endswith("forward_returns.json")


# ---------------------------------------------------------------------------
# Resume path: merge + calibration refresh
# ---------------------------------------------------------------------------


def test_resume_attempts_merge_and_refreshes_calibration(monkeypatch, tmp_path):
    """Resume with existing artifacts should merge and refresh calibration."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    top30_path = out_dir / "top30_candidates.json"
    ranking_path = out_dir / "aihf_stock_ranking.json"
    _write_json(top30_path, {"candidates": [{"code": "600001"}]})
    _write_json(ranking_path, {"items": [{"code": "600001", "agent_score": 75}]})

    merge_called_with = []
    cal_called = {"n": 0}

    def fake_merge(top30_path, ranking_path):
        merge_called_with.append((str(top30_path), str(ranking_path)))
        return True

    def fake_find_returns(d):
        return tmp_path / "forward_returns.json"

    def fake_cal(d):
        cal_called["n"] += 1
        return tmp_path / "cal.json"

    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", fake_merge)
    monkeypatch.setattr(module, "find_forward_returns_file", fake_find_returns)
    monkeypatch.setattr(module, "run_scoring_calibration", fake_cal)

    result = module.run_phase24_scripts(date, "selected", resume=True)

    assert result["resume_used"] is True
    assert len(merge_called_with) == 1
    assert str(top30_path) in merge_called_with[0][0]
    assert str(ranking_path) in merge_called_with[0][1]
    assert cal_called["n"] == 1


def test_resume_skips_calibration_when_no_forward_returns(monkeypatch, tmp_path):
    """Resume without forward_returns.json should skip calibration."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {"candidates": []})
    _write_json(out_dir / "aihf_stock_ranking.json", {"items": []})

    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", lambda *a, **k: True)
    monkeypatch.setattr(module, "find_forward_returns_file", lambda d: None)
    cal_called = {"n": 0}
    monkeypatch.setattr(module, "run_scoring_calibration", lambda d: (cal_called.__setitem__("n", cal_called["n"] + 1), None)[-1])

    result = module.run_phase24_scripts(date, "selected", resume=True)

    assert result["resume_used"] is True
    assert cal_called["n"] == 0


def test_resume_preserves_rank_hidden(monkeypatch, tmp_path):
    """Resume path must not expose raw rank and must keep rank_hidden."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    top30_data = {"rank_hidden": True, "candidates": [{"code": "600001"}]}
    _write_json(out_dir / "top30_candidates.json", top30_data)
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"rank": 1, "code": "600001", "agent_score": 75}],
    })

    def fake_merge(top30_path, ranking_path):
        # Simulate what merge_agent_scores_into_candidates does
        data = json.loads(top30_path.read_text(encoding="utf-8"))
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        for item in ranking.get("items", []):
            for c in data.get("candidates", []):
                if c.get("code") == item.get("code"):
                    c["agent_score"] = item.get("agent_score")
        data["agent_score_merged"] = True
        top30_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", fake_merge)
    monkeypatch.setattr(module, "find_forward_returns_file", lambda d: None)
    monkeypatch.setattr(module, "run_scoring_calibration", lambda d: None)

    module.run_phase24_scripts(date, "selected", resume=True)

    enriched = json.loads((out_dir / "top30_candidates.json").read_text(encoding="utf-8"))
    assert enriched.get("rank_hidden") is True
    for c in enriched.get("candidates", []):
        assert "rank" not in c


# ---------------------------------------------------------------------------
# AIHF input coverage
# ---------------------------------------------------------------------------


def test_compute_aihf_input_coverage_full_overlap(monkeypatch, tmp_path):
    """Full overlap: all candidates are in ranking."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1"},
            {"code": "600002", "name": "S2"},
        ],
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
        ],
    })

    cov = module.compute_aihf_input_coverage(date)
    assert cov["top30_candidate_count"] == 2
    assert cov["aihf_input_candidate_count"] == 2
    assert cov["aihf_input_coverage_ratio"] == 1.0
    assert cov["excluded_candidate_codes"] == []
    assert cov["truncation_applied"] is False


def test_compute_aihf_input_coverage_respects_agent_stock_limit(monkeypatch, tmp_path):
    """Intentional agent limit uses analyzed candidates as the coverage denominator."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "agent_analysis_policy": {
            "source_candidate_count": 30,
            "agent_stock_limit": 10,
            "agent_analyzed_count": 10,
            "agent_skipped_count": 20,
        },
        "candidates": [
            {
                "code": f"600{i:03d}",
                "name": f"S{i}",
                "agent_analysis_status": "pending_agent_analysis" if i <= 10 else "skipped_by_agent_stock_limit",
            }
            for i in range(1, 31)
        ],
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"code": f"600{i:03d}", "agent_score": 80} for i in range(1, 11)],
    })

    cov = module.compute_aihf_input_coverage(date)
    assert cov["top30_candidate_count"] == 30
    assert cov["aihf_input_candidate_count"] == 10
    assert cov["agent_input_limited"] is True
    assert cov["agent_skipped_count"] == 20
    assert cov["aihf_input_coverage_ratio"] == 1.0
    assert cov["coverage_status"] == "healthy"


def test_compute_aihf_input_coverage_partial_overlap(monkeypatch, tmp_path):
    """Partial overlap: some candidates not in ranking."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-01"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "name": "S1"},
            {"code": "600002", "name": "S2"},
            {"code": "600003", "name": "S3"},
        ],
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [
            {"code": "600001", "agent_score": 80},
            # 600002, 600003 not in ranking
        ],
    })

    cov = module.compute_aihf_input_coverage(date)
    assert cov["top30_candidate_count"] == 3
    assert cov["aihf_input_coverage_ratio"] == pytest.approx(0.3333, abs=0.001)
    assert "600002" in cov["excluded_candidate_codes"]
    assert "600003" in cov["excluded_candidate_codes"]
    assert cov["truncation_applied"] is True


def test_compute_aihf_input_coverage_missing_ranking(monkeypatch, tmp_path):
    """Missing ranking file returns zero coverage."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-02"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [{"code": "600001", "name": "S1"}],
    })
    # No ranking file

    cov = module.compute_aihf_input_coverage(date)
    assert cov["top30_candidate_count"] == 1
    assert cov["aihf_input_coverage_ratio"] == 0.0
    assert cov["truncation_applied"] is False


def test_resume_path_includes_coverage(monkeypatch, tmp_path):
    """Resume path returns aihf_coverage in result."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "rank_hidden": True,
        "candidates": [{"code": "600001", "name": "S1"}],
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 80}],
    })

    monkeypatch.setattr(module, "merge_agent_scores_into_candidates", lambda *a, **k: True)
    monkeypatch.setattr(module, "find_forward_returns_file", lambda d: None)
    monkeypatch.setattr(module, "run_scoring_calibration", lambda d: None)

    result = module.run_phase24_scripts(date, "selected", resume=True)

    assert "aihf_coverage" in result
    cov = result["aihf_coverage"]
    assert cov["top30_candidate_count"] == 1
    assert cov["aihf_input_coverage_ratio"] == 1.0
    assert cov["truncation_applied"] is False


def test_bridge_report_includes_coverage(monkeypatch, tmp_path):
    """build_bridge_report includes aihf_coverage section."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {"candidates": []})

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {
            "status": "ok",
            "resume_used": True,
            "cache_hits": [],
            "ranking": {},
            "aihf_coverage": {
                "top30_candidate_count": 17,
                "aihf_input_coverage_ratio": 0.88,
                "truncation_applied": True,
                "excluded_candidate_codes": ["600001"],
            },
        },
    )

    assert "aihf_coverage" in report
    assert report["aihf_coverage"]["aihf_input_coverage_ratio"] == 0.88
    assert report["aihf_coverage"]["truncation_applied"] is True


# ---------------------------------------------------------------------------
# Coverage risk assessment
# ---------------------------------------------------------------------------


def test_coverage_risk_stale_below_50(monkeypatch, tmp_path):
    """Coverage < 50% → stale_or_mismatched_ranking, rerun recommended."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-01"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 80}],  # only 1/10
    })

    cov = module.compute_aihf_input_coverage(date)
    assert cov["coverage_status"] == "stale_or_mismatched_ranking"
    assert cov["rerun_aihf_bridge_recommended"] is True
    assert cov["aihf_input_coverage_ratio"] == 0.1
    assert "below 50%" in cov["coverage_risk_reason"]


def test_coverage_risk_partial_50_to_80(monkeypatch, tmp_path):
    """50% <= coverage < 80% → partial, no rerun."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-07"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"code": f"60000{i}", "agent_score": 80} for i in range(1, 8)],  # 7/10
    })

    cov = module.compute_aihf_input_coverage(date)
    assert cov["coverage_status"] == "partial"
    assert cov["rerun_aihf_bridge_recommended"] is False
    assert cov["aihf_input_coverage_ratio"] == 0.7
    assert len(cov["excluded_candidate_codes"]) == 3


def test_coverage_risk_healthy_above_80(monkeypatch, tmp_path):
    """Coverage >= 80% → healthy, no rerun."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [{"code": f"60000{i}", "name": f"S{i}"} for i in range(1, 11)],
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"code": f"60000{i}", "agent_score": 80} for i in range(1, 10)],  # 9/10
    })

    cov = module.compute_aihf_input_coverage(date)
    assert cov["coverage_status"] == "healthy"
    assert cov["rerun_aihf_bridge_recommended"] is False
    assert cov["aihf_input_coverage_ratio"] == 0.9


def test_coverage_risk_missing_ranking(monkeypatch, tmp_path):
    """Missing ranking → missing_data status."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-02"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [{"code": "600001", "name": "S1"}],
    })
    # No ranking file

    cov = module.compute_aihf_input_coverage(date)
    assert cov["coverage_status"] == "missing_data"
    assert cov["rerun_aihf_bridge_recommended"] is False
    assert "not found" in cov["coverage_risk_reason"]


def test_coverage_risk_missing_top30(monkeypatch, tmp_path):
    """Missing top30 → missing_data status."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-03"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    # No top30 file

    cov = module.compute_aihf_input_coverage(date)
    assert cov["coverage_status"] == "missing_data"
    assert cov["rerun_aihf_bridge_recommended"] is False


def test_markdown_includes_coverage_risk_section(monkeypatch, tmp_path):
    """Markdown output includes AIHF Coverage Risk section."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-01"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)

    _write_json(out_dir / "top30_candidates.json", {"candidates": []})

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {
            "status": "ok",
            "resume_used": True,
            "cache_hits": [],
            "ranking": {},
            "aihf_coverage": {
                "top30_candidate_count": 18,
                "aihf_input_coverage_ratio": 0.11,
                "truncation_applied": True,
                "excluded_candidate_codes": ["600001"],
                "coverage_status": "stale_or_mismatched_ranking",
                "rerun_aihf_bridge_recommended": True,
                "coverage_risk_reason": "ranking coverage below 50%",
            },
        },
    )

    md = module.generate_bridge_markdown(report, date)
    assert "AIHF Coverage Risk" in md
    assert "stale_or_mismatched_ranking" in md
    assert "Rerun recommended" in md


# ---------------------------------------------------------------------------
# Agent Score Coverage Quality
# ---------------------------------------------------------------------------


def test_compute_agent_score_coverage_quality_healthy(monkeypatch, tmp_path):
    """Healthy coverage (>= 80%) is classified correctly."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
        ],
    })

    result = module.compute_agent_score_coverage_quality(date)
    assert result["quality_status"] == "healthy"
    assert result["coverage_ratio"] == 1.0
    assert result["agent_score_present_count"] == 2
    assert result["agent_score_missing_count"] == 0


def test_compute_agent_score_coverage_quality_partial(monkeypatch, tmp_path):
    """Partial coverage (50-80%) is classified correctly."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-07"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    result = module.compute_agent_score_coverage_quality(date)
    assert result["quality_status"] == "partial"
    assert result["coverage_ratio"] == 0.5
    assert result["agent_score_missing_count"] == 2
    assert "600003" in result["missing_codes"]


def test_compute_agent_score_coverage_quality_poor(monkeypatch, tmp_path):
    """Poor coverage (< 50%) is classified correctly."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-01"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    result = module.compute_agent_score_coverage_quality(date)
    assert result["quality_status"] == "poor"
    assert result["coverage_ratio"] == 0.25
    assert len(result["missing_codes"]) == 3
    assert any("quality risk" in n.lower() for n in result["notes"])


def test_bridge_report_includes_coverage_quality(monkeypatch, tmp_path):
    """build_bridge_report includes agent_score_coverage_quality."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
        ],
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    assert "agent_score_coverage_quality" in report
    cq = report["agent_score_coverage_quality"]
    assert cq["quality_status"] == "partial"
    assert cq["coverage_ratio"] == 0.5


def test_bridge_markdown_includes_coverage_quality(monkeypatch, tmp_path):
    """Markdown output includes Agent Score Coverage Quality section."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
        ],
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    md = module.generate_bridge_markdown(report, date)
    assert "Agent Score Coverage Quality" in md
    assert "partial" in md


# ---------------------------------------------------------------------------
# Pipeline Warnings
# ---------------------------------------------------------------------------


def test_poor_coverage_generates_pipeline_warning(monkeypatch, tmp_path):
    """Poor coverage generates a pipeline warning in bridge report."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-01"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    pw = report.get("pipeline_warnings", [])
    assert len(pw) == 1
    assert pw[0]["type"] == "poor_agent_score_coverage"
    assert pw[0]["severity"] == "warn"
    assert pw[0]["coverage_ratio"] == 0.25
    assert pw[0]["missing_count"] == 3


def test_healthy_coverage_no_pipeline_warning(monkeypatch, tmp_path):
    """Healthy coverage does not generate a pipeline warning."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
        ],
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    pw = report.get("pipeline_warnings", [])
    assert len(pw) == 0


def test_limited_agent_coverage_no_pipeline_warning(monkeypatch, tmp_path):
    """Intentional agent-stock limit should not produce a poor coverage warning."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "agent_analysis_policy": {
            "source_candidate_count": 30,
            "agent_stock_limit": 10,
            "agent_analyzed_count": 10,
            "agent_skipped_count": 20,
        },
        "candidates": [
            {
                "code": f"600{i:03d}",
                "agent_score": 80 if i <= 10 else None,
                "agent_analysis_status": "analyzed" if i <= 10 else "skipped_by_agent_stock_limit",
            }
            for i in range(1, 31)
        ],
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [{"code": f"600{i:03d}", "agent_score": 80} for i in range(1, 11)], "run_meta": {}},
        {"status": "ok", "resume_used": False, "cache_hits": [], "ranking": {}},
    )

    cq = report["agent_score_coverage_quality"]
    assert cq["candidate_count"] == 30
    assert cq["agent_analyzed_expected_count"] == 10
    assert cq["agent_skipped_count"] == 20
    assert cq["coverage_ratio"] == 1.0
    assert cq["quality_status"] == "healthy"
    assert report["pipeline_warnings"] == []


def test_partial_coverage_no_poor_warning(monkeypatch, tmp_path):
    """Partial coverage does not generate a poor_agent_score_coverage warning."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-07"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002", "agent_score": 70},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    pw = report.get("pipeline_warnings", [])
    poor_warnings = [w for w in pw if w.get("type") == "poor_agent_score_coverage"]
    assert len(poor_warnings) == 0


def test_pipeline_warning_in_markdown(monkeypatch, tmp_path):
    """Pipeline warning appears in markdown output."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-01"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": [
            {"code": "600001", "agent_score": 80},
            {"code": "600002"},
            {"code": "600003"},
            {"code": "600004"},
        ],
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    md = module.generate_bridge_markdown(report, date)
    assert "Pipeline Warnings" in md
    assert "poor_agent_score_coverage" in md


# ---------------------------------------------------------------------------
# Agent Execution Quality
# ---------------------------------------------------------------------------


def test_compute_agent_execution_quality_healthy(monkeypatch, tmp_path):
    """Healthy execution: all agents succeeded, no default scores."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [
            {"code": "600001", "agent_score": 72.0, "contributing_agents": 7},
            {"code": "600002", "agent_score": 65.0, "contributing_agents": 7},
        ],
        "run_meta": {
            "succeeded_agents": ["a", "b", "c"],
            "failed_agents": [],
            "fallback_agents": [],
        },
    })

    result = module.compute_agent_execution_quality(date)
    assert result["quality_status"] == "healthy"
    assert result["analyzed_stock_count"] == 2
    assert result["default_score_count"] == 0
    assert result["failed_agent_count"] == 0


def test_compute_agent_execution_quality_fallback_only(monkeypatch, tmp_path):
    """Fallback-only: all agent_score=50.0 with 0 contributing agents."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-01"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [
            {"code": "600001", "agent_score": 50.0, "contributing_agents": 0},
            {"code": "600002", "agent_score": 50.0, "contributing_agents": 0},
        ],
        "run_meta": {
            "succeeded_agents": [],
            "failed_agents": ["a", "b"],
            "fallback_agents": [],
        },
    })

    result = module.compute_agent_execution_quality(date)
    assert result["quality_status"] == "fallback_only"
    assert result["default_score_count"] == 2
    assert result["default_score_ratio"] == 1.0


def test_compute_agent_execution_quality_degraded(monkeypatch, tmp_path):
    """Degraded: some default scores."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-02"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [
            {"code": "600001", "agent_score": 72.0, "contributing_agents": 7},
            {"code": "600002", "agent_score": 50.0, "contributing_agents": 0},
        ],
        "run_meta": {
            "succeeded_agents": ["a"],
            "failed_agents": ["b"],
            "fallback_agents": [],
        },
    })

    result = module.compute_agent_execution_quality(date)
    assert result["quality_status"] == "degraded"
    assert result["default_score_count"] == 1
    assert result["failed_agent_count"] == 1


def test_bridge_report_includes_execution_quality(monkeypatch, tmp_path):
    """build_bridge_report includes agent_execution_quality."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {"candidates": []})
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 72.0, "contributing_agents": 7}],
        "run_meta": {"succeeded_agents": ["a"], "failed_agents": [], "fallback_agents": []},
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    assert "agent_execution_quality" in report
    assert report["agent_execution_quality"]["quality_status"] == "healthy"


def test_bridge_markdown_includes_execution_quality(monkeypatch, tmp_path):
    """Markdown output includes Agent Execution Quality section."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {"candidates": []})
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": [{"code": "600001", "agent_score": 72.0, "contributing_agents": 7}],
        "run_meta": {"succeeded_agents": ["a"], "failed_agents": [], "fallback_agents": []},
    })

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    md = module.generate_bridge_markdown(report, date)
    assert "Agent Execution Quality" in md
    assert "healthy" in md


# ---------------------------------------------------------------------------
# Agent Score Health Check
# ---------------------------------------------------------------------------


def test_run_agent_score_health_check_produces_result():
    """Health check produces a result dict with expected fields."""
    module = _load_bridge_module()
    result = module._run_agent_score_health_check("2026-07-08")
    assert "status" in result
    assert "overall_status" in result
    assert "health_report_path" in result
    assert "pipeline_warnings_count" in result
    assert "coverage_status" in result
    assert "execution_quality_status" in result


def test_bridge_report_includes_health_check(monkeypatch, tmp_path):
    """build_bridge_report includes agent_score_health_check when provided."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {"candidates": []})

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    # Manually add health check result
    report["agent_score_health_check"] = {
        "status": "ok",
        "overall_status": "monitor",
        "health_report_path": "/test/path.json",
        "pipeline_warnings_count": 0,
        "coverage_status": "healthy",
        "execution_quality_status": "healthy",
    }

    md = module.generate_bridge_markdown(report, date)
    assert "Agent Score Health Check" in md
    assert "monitor" in md
    assert "Coverage Status" in md


def test_health_check_risk_produces_warning(monkeypatch, tmp_path):
    """RISK status produces a warning but does not interrupt."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")

    date = "2026-07-08"
    out_dir = module.OUTPUT_DIR / date
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "top30_candidates.json", {"candidates": []})

    report = module.build_bridge_report(
        date,
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": [], "ranking": {}},
    )

    report["agent_score_health_check"] = {
        "status": "ok",
        "overall_status": "risk",
        "health_report_path": "/test/path.json",
        "pipeline_warnings_count": 1,
        "coverage_status": "poor",
        "execution_quality_status": "fallback_only",
    }

    md = module.generate_bridge_markdown(report, date)
    assert "Agent Score Health Check" in md
    assert "risk" in md.lower()
    assert "🔴" in md


# ======================================================================
# New scoring field tests
# ======================================================================


def test_bridge_report_top30_includes_new_scoring_fields(monkeypatch, tmp_path):
    """daily_bridge_report.json top30_candidates should include new scoring fields."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")
    out_dir = module.OUTPUT_DIR / "2026-07-09"
    out_dir.mkdir(parents=True)

    candidates_with_scoring = [
        {
            "code": "600001",
            "name": "测试股A",
            "boards": ["半导体"],
            "trend_score": 70.0,
            "burst_score": 65.0,
            "stock_short_score": 68.0,
            "stock_trend_score": 72.0,
            "sector_leader_score": 80.0,
            "decision_score": 70.0,
            "trade_eligibility": "focus",
            "risk_tags": [],
            "agent_analysis_status": "pending_agent_analysis",
        },
        {
            "code": "600002",
            "name": "测试股B",
            "boards": ["新能源"],
            "trend_score": 55.0,
            "burst_score": 50.0,
            "stock_short_score": 52.0,
            "stock_trend_score": 58.0,
            "sector_leader_score": 40.0,
            "decision_score": 50.0,
            "trade_eligibility": "watch",
            "risk_tags": ["moderate_liquidity_risk"],
            "agent_analysis_status": "skipped_by_agent_stock_limit",
        },
    ]
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": candidates_with_scoring,
        "agent_analysis_policy": {
            "agent_stock_limit": 1,
            "agent_analyzed_count": 1,
            "agent_skipped_count": 1,
        },
    })
    _write_json(out_dir / "aihf_stock_ranking.json", {"items": [], "run_meta": {}})

    report = module.build_bridge_report(
        "2026-07-09",
        {"industries": [], "concepts": []},
        {"items": [], "run_meta": {}},
        {"status": "ok", "resume_used": True, "cache_hits": []},
    )

    top30 = report.get("top30_candidates", [])
    assert len(top30) == 2

    # Check new fields present on first candidate
    c = top30[0]
    assert c["stock_short_score"] == 68.0
    assert c["stock_trend_score"] == 72.0
    assert c["sector_leader_score"] == 80.0
    assert c["decision_score"] == 70.0
    assert c["trade_eligibility"] == "focus"


def test_bridge_markdown_includes_scoring_columns(monkeypatch, tmp_path):
    """Markdown report should include new scoring column data."""
    module = _load_bridge_module()
    date = "2026-07-09"
    # Build report directly (bypass build_bridge_report to avoid OUTPUT_DIR issues)
    report = {
        "top30_candidates": [
            {
                "code": "600001", "name": "TestStock",
                "boards": ["Semiconductor"],
                "trend_score": 70, "burst_score": 65,
                "stock_short_score": 68, "stock_trend_score": 72,
                "sector_leader_score": 80, "decision_score": 70,
                "trade_eligibility": "focus", "risk_tags": [],
            },
        ],
        "industry_top": [], "concept_top": [], "agent_ranking": [],
        "data_sources": {}, "health": {}, "aihf_coverage": {},
        "agent_score_coverage_quality": {}, "agent_execution_quality": {},
        "warnings": [],
    }
    md = module.generate_bridge_markdown(report, date)

    # Check for scoring data in the table
    assert "600001" in md
    assert "68.0" in md  # stock_short_score
    assert "72.0" in md  # stock_trend_score
    assert "80.0" in md  # sector_leader_score
    assert "70.0" in md  # decision_score


def test_bridge_markdown_groups_by_eligibility(monkeypatch, tmp_path):
    """Markdown should group candidates by trade_eligibility."""
    module = _load_bridge_module()
    date = "2026-07-09"
    report = {
        "top30_candidates": [
            {
                "code": "600001", "name": "FocusStock",
                "boards": ["Semiconductor"],
                "trend_score": 70, "burst_score": 65,
                "stock_short_score": 68, "stock_trend_score": 72,
                "sector_leader_score": 80, "decision_score": 70,
                "trade_eligibility": "focus", "risk_tags": [],
            },
            {
                "code": "600002", "name": "WatchStock",
                "boards": ["Energy"],
                "trend_score": 55, "burst_score": 50,
                "stock_short_score": 52, "stock_trend_score": 58,
                "sector_leader_score": 40, "decision_score": 50,
                "trade_eligibility": "watch", "risk_tags": [],
            },
            {
                "code": "600003", "name": "AvoidStock",
                "boards": ["Pharma"],
                "trend_score": 40, "burst_score": 35,
                "stock_short_score": 30, "stock_trend_score": 35,
                "sector_leader_score": 20, "decision_score": 30,
                "trade_eligibility": "avoid", "risk_tags": ["overheated"],
            },
        ],
        "industry_top": [], "concept_top": [], "agent_ranking": [],
        "data_sources": {}, "health": {}, "aihf_coverage": {},
        "agent_score_coverage_quality": {}, "agent_execution_quality": {},
        "warnings": [],
    }
    md = module.generate_bridge_markdown(report, date)

    # All 3 stocks should appear with their scores
    assert "600001" in md
    assert "600002" in md
    assert "600003" in md
    # Scoring data should be present
    assert "68.0" in md  # stock_short_score of focus stock
    assert "30.0" in md  # stock_short_score of avoid stock
    # Risk tag should appear
    assert "overheated" in md


def test_skipped_agents_no_poor_coverage_warning(monkeypatch, tmp_path):
    """Agents skipped by stock_limit should not trigger poor coverage warning."""
    module = _load_bridge_module()
    monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "reports" / "agent_bridge")
    out_dir = module.OUTPUT_DIR / "2026-07-09"
    out_dir.mkdir(parents=True)

    # 30 candidates, only 10 analyzed, 20 skipped
    # compute_aihf_input_coverage only counts "pending_agent_analysis"|"analyzed"
    candidates = []
    for i in range(1, 31):
        if i <= 10:
            status = "pending_agent_analysis"
        else:
            status = "skipped_by_agent_stock_limit"
        entry = {
            "code": f"600{i:03d}",
            "name": f"stock{i}",
            "trend_score": 60,
            "burst_score": 50,
            "agent_analysis_status": status,
        }
        # Only analyzed candidates have agent_score (simulating merge result)
        if i <= 10:
            entry["agent_score"] = 60
        candidates.append(entry)
    _write_json(out_dir / "top30_candidates.json", {
        "candidates": candidates,
        "agent_analysis_policy": {
            "agent_stock_limit": 10,
            "agent_analyzed_count": 10,
            "agent_skipped_count": 20,
        },
    })
    # Only 10 stocks in ranking (matching the 10 analyzed)
    ranking_items = [{"code": f"600{i:03d}", "agent_score": 60} for i in range(1, 11)]
    _write_json(out_dir / "aihf_stock_ranking.json", {
        "items": ranking_items,
        "run_meta": {"agent_count": 1},
    })

    # Coverage should be healthy (10/10 analyzed candidates have rankings)
    coverage = module.compute_aihf_input_coverage("2026-07-09")
    assert coverage["coverage_status"] == "healthy"
    assert coverage["agent_skipped_count"] == 20

    # Agent score coverage: skipped candidates are not in expected_codes,
    # so only 10 are expected, all 10 have scores → healthy
    score_cov = module.compute_agent_score_coverage_quality("2026-07-09")
    assert score_cov["quality_status"] == "healthy"

