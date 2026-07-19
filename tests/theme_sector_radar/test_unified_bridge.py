#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sector_stock_bridge 和 unified_pipeline 最小测试。

覆盖:
  - 关联度计算（三维度加权）
  - 资金流对齐降级
  - 最新报告读取
  - 输出结构字段
"""

import json
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _is_proxy_env_key(key: str) -> bool:
    normalized = key.upper()
    return normalized.endswith("_PROXY") or normalized.endswith("_PROXY_")


def _snapshot_proxy_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if _is_proxy_env_key(key)}


def _restore_proxy_env(snapshot: dict[str, str]) -> None:
    for key in list(os.environ):
        if _is_proxy_env_key(key):
            os.environ.pop(key, None)
    os.environ.update(snapshot)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_COLLECTION_SYS_PATH = list(sys.path)
_COLLECTION_PROXY_ENV = _snapshot_proxy_env()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from sector_stock_bridge import (
        _compute_flow_alignment,
        _compute_rank_scores,
        _normalize_weights,
        compute_relevance_scores,
        extract_top_sectors,
        extract_top_sectors_from_stable,
        find_cross_sectors,
        find_latest_report,
        load_sector_scores,
    )
    from unified_pipeline import (
        _compute_fallback_quant_score,
        compute_final_scores,
        compute_quant_scores,
    )
    from tests.theme_sector_radar.report_fixture_factory import (
        build_sector_score_tree,
        write_json,
    )
finally:
    sys.path[:] = _COLLECTION_SYS_PATH
    _restore_proxy_env(_COLLECTION_PROXY_ENV)


def _link_directory_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError as exc:
        if os.name != "nt":
            pytest.skip(f"directory symlink unavailable: {exc}")

    import subprocess

    junction = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if junction.returncode != 0:
        pytest.skip(f"directory link unavailable: {junction.stderr}")


def test_module_import_preserves_process_globals():
    """Collecting this test module must not leak path or proxy mutations."""
    import subprocess

    probe = """
import os
import sys

proxy_keys = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "CUSTOM_PROXY", "CUSTOM_PROXY_",
)
for key in proxy_keys:
    os.environ[key] = f"fixture-{key}"
before_path = list(sys.path)
before_proxy = {key: os.environ.get(key) for key in proxy_keys}
import tests.theme_sector_radar.test_unified_bridge  # noqa: F401
assert sys.path == before_path, (before_path, sys.path)
assert {key: os.environ.get(key) for key in proxy_keys} == before_proxy
"""
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(PROJECT_ROOT),
    )

    assert proc.returncode == 0, proc.stderr


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(autouse=True)
def isolate_inherited_report_root(monkeypatch):
    """Reset import-time report-root state before every in-process test."""
    import sector_stock_bridge as bridge

    original_sys_path = list(sys.path)
    original_proxy_env = _snapshot_proxy_env()
    report_root = bridge.PROJECT_ROOT / "reports"
    monkeypatch.delenv("THEME_SECTOR_RADAR_REPORT_ROOT", raising=False)
    monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", None)
    monkeypatch.setattr(bridge, "REPORT_ROOT", report_root)
    monkeypatch.setattr(bridge, "SCORES_DIR", report_root / "sector_scores")
    monkeypatch.setattr(
        bridge, "STABLE_RESEARCH_DIR", report_root / "full90" / "sector_research"
    )
    monkeypatch.setattr(
        bridge,
        "STABLE_CONCEPT_DIR",
        report_root / "full_concept" / "unified_rank",
    )
    monkeypatch.setattr(
        bridge, "CACHE_DIR", bridge.PROJECT_ROOT / "data_cache" / "sector_stocks"
    )
    yield
    sys.path[:] = original_sys_path
    _restore_proxy_env(original_proxy_env)


@pytest.fixture
def isolated_bridge_reports(tmp_path, monkeypatch):
    """Build the smallest report tree and bind every bridge path to it."""
    import sector_stock_bridge as bridge

    monkeypatch.delenv("THEME_SECTOR_RADAR_REPORT_ROOT", raising=False)
    monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", None)
    roots = build_sector_score_tree(tmp_path, ["2026-06-30", "2026-07-01"])
    monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
    monkeypatch.setattr(bridge, "STABLE_RESEARCH_DIR", roots["sector_research"])
    monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])
    monkeypatch.setattr(bridge, "CACHE_DIR", tmp_path / "data_cache" / "sector_stocks")
    return roots


@pytest.fixture
def offline_bridge_io(monkeypatch):
    """Keep bridge integration tests off every direct market-data endpoint."""
    import sector_stock_bridge as bridge

    monkeypatch.setattr(bridge, "fetch_tencent_quotes", lambda _codes: {})
    monkeypatch.setattr(
        bridge,
        "fetch_sector_fund_flow",
        lambda _name: {
            "status": "degraded",
            "net_flow": None,
            "direction": "neutral",
            "error": "offline fixture",
        },
    )
    monkeypatch.setattr(bridge, "fetch_individual_fund_flow", lambda _codes: {})

@pytest.fixture
def sample_scores_data():
    """模拟板块评分数据"""
    return {
        "scores": [
            {
                "sector_name": "证券",
                "sector_type": "industry",
                "trend_continuation_score": 40.35,
                "short_term_burst_score": 34.4,
                "trend_level": "cooling",
                "trend_level_cn": "降温",
                "burst_level": "burst_avoid",
                "burst_level_cn": "短线偏弱",
            },
            {
                "sector_name": "保险",
                "sector_type": "industry",
                "trend_continuation_score": 29.3,
                "short_term_burst_score": 48.8,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_fading",
                "burst_level_cn": "短线降温",
            },
            {
                "sector_name": "化学制药",
                "sector_type": "industry",
                "trend_continuation_score": 20.3,
                "short_term_burst_score": 51.8,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_neutral",
                "burst_level_cn": "短线中性",
            },
            {
                "sector_name": "医疗服务",
                "sector_type": "industry",
                "trend_continuation_score": 18.85,
                "short_term_burst_score": 51.9,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_neutral",
                "burst_level_cn": "短线中性",
            },
            {
                "sector_name": "养殖业",
                "sector_type": "industry",
                "trend_continuation_score": 18.1,
                "short_term_burst_score": 48.8,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_fading",
                "burst_level_cn": "短线降温",
            },
            {
                "sector_name": "教育",
                "sector_type": "industry",
                "trend_continuation_score": 18.1,
                "short_term_burst_score": 44.8,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_fading",
                "burst_level_cn": "短线降温",
            },
            {
                "sector_name": "农产品加工",
                "sector_type": "industry",
                "trend_continuation_score": 17.6,
                "short_term_burst_score": 47.9,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_fading",
                "burst_level_cn": "短线降温",
            },
            {
                "sector_name": "多元金融",
                "sector_type": "industry",
                "trend_continuation_score": 17.6,
                "short_term_burst_score": 36.9,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_fading",
                "burst_level_cn": "短线降温",
            },
            {
                "sector_name": "物流",
                "sector_type": "industry",
                "trend_continuation_score": 17.6,
                "short_term_burst_score": 43.9,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_fading",
                "burst_level_cn": "短线降温",
            },
            {
                "sector_name": "生物制品",
                "sector_type": "industry",
                "trend_continuation_score": 14.85,
                "short_term_burst_score": 51.9,
                "trend_level": "avoid",
                "trend_level_cn": "偏弱",
                "burst_level": "burst_neutral",
                "burst_level_cn": "短线中性",
            },
        ]
    }


@pytest.fixture
def sample_stocks():
    """模拟板块成分股数据"""
    return [
        {"code": "600030", "name": "中信证券", "weight": 0.15, "change_pct": 2.3, "individual_flow_direction": "inflow"},
        {"code": "601211", "name": "国泰君安", "weight": 0.10, "change_pct": 1.5, "individual_flow_direction": "inflow"},
        {"code": "600999", "name": "招商证券", "weight": 0.08, "change_pct": -0.5, "individual_flow_direction": "outflow"},
        {"code": "601688", "name": "华泰证券", "weight": 0.07, "change_pct": 0.8, "individual_flow_direction": "neutral"},
        {"code": "600036", "name": "兴业证券", "weight": 0.05, "change_pct": -1.2, "individual_flow_direction": "outflow"},
    ]


def _valid_industry_research_payload(as_of):
    return {
        "as_of_date": as_of,
        "sector_type": "industry",
        "report_type": "sector_research",
        "research_results": [
            {
                "sector_name": "Valid Industry",
                "sector_type": "industry",
                "consensus_label": "observe",
                "ranking_score": 80.0,
                "opportunity_score": 70.0,
                "evidence_score": 60.0,
                "confidence_score": 50.0,
            }
        ],
    }


# ============================================================
# 测试：报告读取
# ============================================================

class TestReportReading:

    def test_find_latest_report_with_date(self, isolated_bridge_reports):
        """指定日期读取报告"""
        date, path = find_latest_report("2026-07-01")
        assert date == "2026-07-01"
        assert path is not None
        assert path.exists()
        assert path.is_relative_to(isolated_bridge_reports["sector_scores"])

    def test_find_latest_report_fallback(self, isolated_bridge_reports):
        """不存在的日期应 fallback 到最新"""
        date, path = find_latest_report("2099-01-01")
        assert date == "2026-07-01"
        assert path is not None
        assert path.is_relative_to(isolated_bridge_reports["sector_scores"])

    def test_stable_sector_extraction_preserves_explicit_zero_trend_score(self):
        stable = {
            "industries": [
                {
                    "sector_name": "Zero Trend",
                    "sector_type": "industry",
                    "ranking_score": 88.0,
                    "opportunity_score": 70.0,
                    "trend_score": 0.0,
                    "burst_score": 60.0,
                }
            ],
            "concepts": [],
        }

        trend, burst = extract_top_sectors_from_stable(stable, 1, 1)

        assert trend[0]["trend_score"] == 0.0
        assert burst[0]["trend_score"] == 0.0

    def test_find_latest_report_no_date(self, isolated_bridge_reports):
        """不指定日期应找到最新"""
        date, path = find_latest_report(None)
        assert date == "2026-07-01"
        assert path is not None
        assert path.is_relative_to(isolated_bridge_reports["sector_scores"])

    def test_default_report_root_rejects_as_of_path_traversal(
        self, tmp_path, monkeypatch
    ):
        import sector_stock_bridge as bridge

        scores_dir = tmp_path / "sector_scores"
        write_json(
            tmp_path / "escape" / "sector_scores.json",
            {"as_of_date": "../escape", "scores": []},
        )
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", None)
        monkeypatch.setattr(bridge, "SCORES_DIR", scores_dir)

        assert bridge.find_latest_report("../escape") == (None, None)

    def test_default_cache_rejects_key_traversal_on_read_and_write(
        self, tmp_path, monkeypatch
    ):
        import sector_stock_bridge as bridge

        cache_dir = tmp_path / "cache"
        payload = {
            "status": "ok",
            "as_of_date": "2026-07-02",
            "sector_name": "证券",
            "sector_type": "industry",
            "stocks": [{"code": "600030", "name": "中信证券", "weight": 1.0}],
            "error": None,
            "fallback_used": False,
            "source": "http_em",
        }
        write_json(tmp_path / "outside.json", payload)
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", None)
        monkeypatch.setattr(bridge, "CACHE_DIR", cache_dir)

        assert bridge._load_cache("../outside") is None
        bridge._save_cache("../written", payload)
        assert not (tmp_path / "written.json").exists()

    def test_fetch_constituents_rejects_invalid_as_of_before_cache_or_network(
        self, monkeypatch
    ):
        import sector_stock_bridge as bridge

        monkeypatch.setattr(
            bridge,
            "_load_cache",
            lambda *_args, **_kwargs: pytest.fail("cache work must not run"),
        )
        monkeypatch.setattr(
            bridge,
            "_get_http_client",
            lambda: pytest.fail("network work must not run"),
        )

        with pytest.raises(ValueError, match="analysis date"):
            bridge.fetch_sector_constituents("证券", as_of="../escape")

    def test_explicit_override_missing_exact_date_never_falls_back(
        self, tmp_path, monkeypatch
    ):
        """An explicit report root may only serve the requested exact date."""
        import sector_stock_bridge as bridge

        roots = build_sector_score_tree(tmp_path, ["2026-07-01"])
        report_root = roots["sector_scores"].parent
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])

        date, path = bridge.find_latest_report("2026-07-02")

        assert date is None
        assert path is None

    def test_explicit_override_rejects_linked_date_escape(
        self, tmp_path, monkeypatch
    ):
        """The child bridge rejects a linked exact date outside its score root."""
        import sector_stock_bridge as bridge

        report_root = tmp_path / "reports"
        score_root = report_root / "sector_scores"
        score_root.mkdir(parents=True)
        outside_date = tmp_path / "outside-date"
        write_json(
            outside_date / "sector_scores.json",
            {"as_of_date": "2026-07-02"},
        )
        _link_directory_or_skip(score_root / "2026-07-02", outside_date)
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))

        date, path = bridge.find_latest_report("2026-07-02")

        assert date is None
        assert path is None

    def test_explicit_override_rejects_score_root_linked_to_sibling(
        self, tmp_path, monkeypatch
    ):
        """The lexical sector_scores root may not redirect to a sibling tree."""
        import sector_stock_bridge as bridge

        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        source = build_sector_score_tree(tmp_path / "source", [as_of])
        report_root = tmp_path / "reports"
        sibling_scores = report_root / "unrelated-scores"
        shutil.copytree(source["sector_scores"], sibling_scores)
        _link_directory_or_skip(report_root / "sector_scores", sibling_scores)

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "SCORES_DIR", report_root / "sector_scores")

        assert bridge.find_latest_report(as_of) == (None, None)
        ok, validated, _error = bridge.validate_explicit_score_report(as_of)
        assert ok is False
        assert validated is None
        daily_ok, _detail = daily._validate_report_root(str(report_root), as_of)
        assert daily_ok is False

    def test_explicit_override_rejects_payload_date_before_network(
        self, tmp_path, monkeypatch
    ):
        """The child must recheck the score payload date before any API work."""
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        report_root = roots["sector_scores"].parent
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        score_payload = load_sector_scores(score_path)
        score_payload["as_of_date"] = "2026-07-01"
        write_json(score_path, score_payload)

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])
        for name in (
            "fetch_sector_constituents",
            "fetch_tencent_quotes",
            "fetch_sector_fund_flow",
            "fetch_individual_fund_flow",
        ):
            monkeypatch.setattr(
                bridge,
                name,
                lambda *_args, **_kwargs: pytest.fail("network work must not run"),
            )

        result = bridge.run_bridge(as_of_date=as_of)

        assert result["status"] == "failed"
        assert result["as_of_date"] is None

    def test_explicit_override_requires_as_of_instead_of_latest_fallback(
        self, tmp_path, monkeypatch
    ):
        import sector_stock_bridge as bridge

        roots = build_sector_score_tree(tmp_path, ["2026-07-02"])
        monkeypatch.setattr(
            bridge, "_REPORT_ROOT_OVERRIDE", str(roots["sector_scores"].parent)
        )
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])

        assert bridge.find_latest_report(None) == (None, None)

    def test_explicit_override_rejects_incomplete_score_payload_before_network(
        self, tmp_path, monkeypatch
    ):
        import sector_stock_bridge as bridge
        import unified_pipeline as pipeline

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        write_json(score_path, {"as_of_date": as_of})
        monkeypatch.setattr(
            bridge, "_REPORT_ROOT_OVERRIDE", str(roots["sector_scores"].parent)
        )
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            pipeline,
            "_get_http_client",
            lambda: pytest.fail("health network must not run for an invalid score payload"),
        )

        result = pipeline.run_pipeline(as_of_date=as_of)

        assert result["status"] == "failed"
        assert "scores" in result["warnings"][0]

    def test_pipeline_rejects_explicit_payload_before_health_network(
        self, tmp_path, monkeypatch
    ):
        """The unified child must reject score identity before its health request."""
        import sector_stock_bridge as bridge
        import unified_pipeline as pipeline

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        report_root = roots["sector_scores"].parent
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        payload = load_sector_scores(score_path)
        payload["as_of_date"] = "2026-07-01"
        write_json(score_path, payload)

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            pipeline,
            "_get_http_client",
            lambda: pytest.fail("health network must not run before score validation"),
        )

        result = pipeline.run_pipeline(as_of_date=as_of)

        assert result["status"] == "failed"
        assert result["as_of_date"] is None

    def test_pipeline_rejects_default_root_payload_before_health_network(
        self, tmp_path, monkeypatch
    ):
        """The legacy/default root must use the same pre-network score contract."""
        import sector_stock_bridge as bridge
        import unified_pipeline as pipeline

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        payload = load_sector_scores(score_path)
        payload["scores"][0]["trend_level"] = ["not", "text"]
        write_json(score_path, payload)
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", None)
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])
        monkeypatch.setattr(
            pipeline,
            "_get_http_client",
            lambda: pytest.fail("health network must not run before score validation"),
        )

        result = pipeline.run_pipeline(as_of_date=as_of)

        assert result["status"] == "failed"
        assert "trend_level" in result["warnings"][0]

    def test_explicit_override_rejects_linked_stable_roots(
        self, tmp_path, monkeypatch
    ):
        """Stable research and concept inputs may not escape an explicit root."""
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path / "inside", [as_of])
        report_root = roots["sector_scores"].parent
        outside = tmp_path / "outside"
        write_json(
            outside / "full90" / "sector_research" / as_of / "sector_research.json",
            {
                "research_results": [
                    {
                        "sector_name": "证券",
                        "sector_type": "industry",
                        "ranking_score": 80.0,
                    }
                ]
            },
        )
        concept_path = (
            outside
            / "full_concept"
            / "unified_rank"
            / as_of
            / "concept_unified_rank.csv"
        )
        concept_path.parent.mkdir(parents=True)
        concept_path.write_text(
            "sector_name,concept_final_rank_score,trend_continuation_score,"
            "short_term_burst_score,rank\nOutside Concept,90,80,70,1\n",
            encoding="utf-8",
        )
        _link_directory_or_skip(report_root / "full90", outside / "full90")
        _link_directory_or_skip(
            report_root / "full_concept", outside / "full_concept"
        )

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", report_root / "full90" / "sector_research"
        )
        monkeypatch.setattr(
            bridge,
            "STABLE_CONCEPT_DIR",
            report_root / "full_concept" / "unified_rank",
        )

        stable = bridge.load_stable_sector_inputs(as_of)

        assert stable["available"] is False
        assert stable["industries"] == []
        assert stable["concepts"] == []

    def test_explicit_override_rejects_linked_cache_root(
        self, tmp_path, monkeypatch
    ):
        """Explicit-root cache reads and writes may not follow links outside it."""
        import sector_stock_bridge as bridge

        report_root = tmp_path / "reports"
        report_root.mkdir()
        outside_cache = tmp_path / "outside-cache"
        outside_cache.mkdir()
        _link_directory_or_skip(report_root / ".cache", outside_cache)
        cache_dir = report_root / ".cache" / "sector_stocks"
        outside_file = outside_cache / "sector_stocks" / "linked.json"
        write_json(outside_file, {"source": "outside"})

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "CACHE_DIR", cache_dir)

        assert bridge._load_cache("linked") is None
        bridge._save_cache("new", {"source": "must-not-write"})
        assert not (outside_cache / "sector_stocks" / "new.json").exists()

    def test_explicit_override_rejects_stable_root_linked_to_sibling(
        self, tmp_path, monkeypatch
    ):
        """A stable input root may not redirect to another report-root subtree."""
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        report_root = roots["sector_scores"].parent
        sibling_root = report_root / "unrelated-research"
        write_json(
            sibling_root / as_of / "sector_research.json",
            {
                "research_results": [
                    {
                        "sector_name": "Sibling Industry",
                        "sector_type": "industry",
                        "ranking_score": 99.0,
                    }
                ]
            },
        )
        roots["sector_research"].parent.mkdir(parents=True, exist_ok=True)
        _link_directory_or_skip(roots["sector_research"], sibling_root)

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])

        stable = bridge.load_stable_sector_inputs(
            as_of,
            score_data=load_sector_scores(
                roots["sector_scores"] / as_of / "sector_scores.json"
            ),
        )

        assert stable["available"] is False
        assert stable["industries"] == []

    def test_explicit_override_rejects_cache_root_linked_to_sibling(
        self, tmp_path, monkeypatch
    ):
        """An explicit cache root may not redirect to a sibling subtree."""
        import sector_stock_bridge as bridge

        report_root = tmp_path / "reports"
        sibling_cache = report_root / "unrelated-cache"
        write_json(sibling_cache / "linked.json", {"source": "sibling"})
        cache_root = report_root / ".cache" / "sector_stocks"
        cache_root.parent.mkdir(parents=True)
        _link_directory_or_skip(cache_root, sibling_cache)

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "CACHE_DIR", cache_root)

        assert bridge._load_cache("linked") is None

    def test_override_reader_rejects_non_regular_opened_file(
        self, tmp_path, monkeypatch
    ):
        """The handle-bound reader must reject non-regular file identities."""
        import stat

        import sector_stock_bridge as bridge

        report_root = tmp_path / "reports"
        stable_root = report_root / "full90" / "sector_research"
        input_path = stable_root / "2026-07-02" / "sector_research.json"
        write_json(input_path, {"research_results": []})
        real_stat = os.stat(input_path)
        non_regular_stat = os.stat_result(
            (stat.S_IFIFO | 0o600, *tuple(real_stat)[1:])
        )

        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge.os, "fstat", lambda _fd: non_regular_stat)

        assert bridge._read_override_confined_text(
            input_path, encoding="utf-8"
        ) is None

    def test_explicit_override_rejects_link_swap_after_stable_resolution(
        self, tmp_path, monkeypatch
    ):
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path / "inside", [as_of])
        report_root = roots["sector_scores"].parent
        inside_date = roots["sector_research"] / as_of
        outside_date = tmp_path / "outside" / as_of
        write_json(
            inside_date / "sector_research.json",
            {"research_results": []},
        )
        write_json(
            outside_date / "sector_research.json",
            {
                "research_results": [
                    {
                        "sector_name": "Outside Industry",
                        "sector_type": "industry",
                        "ranking_score": 99.0,
                    }
                ]
            },
        )
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])
        original_resolve = bridge._resolve_override_confined_path
        swapped = False

        def resolve_then_swap(path, **kwargs):
            nonlocal swapped
            resolved = original_resolve(path, **kwargs)
            if path.name == "sector_research.json" and not swapped:
                swapped = True
                shutil.rmtree(inside_date)
                _link_directory_or_skip(inside_date, outside_date)
            return resolved

        monkeypatch.setattr(bridge, "_resolve_override_confined_path", resolve_then_swap)

        stable = bridge.load_stable_sector_inputs(as_of)

        assert stable["available"] is False
        assert stable["industries"] == []

    def test_explicit_override_rejects_link_swap_before_cache_write(
        self, tmp_path, monkeypatch
    ):
        import sector_stock_bridge as bridge

        report_root = tmp_path / "reports"
        cache_dir = report_root / ".cache" / "sector_stocks"
        outside_cache = tmp_path / "outside-cache"
        cache_dir.mkdir(parents=True)
        outside_cache.mkdir()
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", str(report_root))
        monkeypatch.setattr(bridge, "CACHE_DIR", cache_dir)
        original_resolve = bridge._resolve_override_confined_path
        swapped = False

        def resolve_then_swap(path, **kwargs):
            nonlocal swapped
            resolved = original_resolve(path, **kwargs)
            if path.name == "race.json" and not swapped:
                swapped = True
                shutil.rmtree(cache_dir)
                _link_directory_or_skip(cache_dir, outside_cache)
            return resolved

        monkeypatch.setattr(bridge, "_resolve_override_confined_path", resolve_then_swap)

        bridge._save_cache("race", {"source": "must-not-write"})

        assert not (outside_cache / "race.json").exists()

    def test_load_sector_scores_structure(self, sample_scores_data):
        """加载的报告应有正确的结构"""
        assert "scores" in sample_scores_data
        assert len(sample_scores_data["scores"]) == 10
        first = sample_scores_data["scores"][0]
        assert "sector_name" in first
        assert "trend_continuation_score" in first
        assert "short_term_burst_score" in first

    def test_stable_inputs_use_injected_score_root(self, tmp_path, monkeypatch):
        """Stable inputs must not mix an injected root with machine-local scores."""
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        injected = build_sector_score_tree(tmp_path / "injected", [as_of])
        write_json(
            injected["sector_research"] / as_of / "sector_research.json",
            {
                **_valid_industry_research_payload(as_of),
                "research_results": [
                    {
                        **_valid_industry_research_payload(as_of)[
                            "research_results"
                        ][0],
                        "sector_name": "证券",
                    }
                ],
            },
        )
        machine = build_sector_score_tree(tmp_path / "machine", [as_of])
        machine_scores = load_sector_scores(
            machine["sector_scores"] / as_of / "sector_scores.json"
        )
        machine_scores["scores"][0]["trend_continuation_score"] = 1.0
        write_json(
            machine["sector_scores"] / as_of / "sector_scores.json",
            machine_scores,
        )

        monkeypatch.setattr(bridge, "PROJECT_ROOT", tmp_path / "machine")
        monkeypatch.setattr(bridge, "SCORES_DIR", injected["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", injected["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", injected["concept_rank"])

        stable = bridge.load_stable_sector_inputs(as_of)

        assert stable["available"] is True
        assert stable["industries"][0]["trend_score"] == 72.0

    @pytest.mark.parametrize(
        "malformation",
        [
            "wrong_date",
            "wrong_top_sector_type",
            "wrong_report_type",
            "missing_required_field",
            "empty_required_number",
            "mixed_sector_type",
        ],
    )
    def test_stable_industry_source_rejects_incomplete_or_mismatched_schema(
        self, tmp_path, monkeypatch, malformation
    ):
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        payload = _valid_industry_research_payload(as_of)
        if malformation == "wrong_date":
            payload["as_of_date"] = "2026-07-01"
        elif malformation == "wrong_top_sector_type":
            payload["sector_type"] = "concept"
        elif malformation == "wrong_report_type":
            payload["report_type"] = "other"
        elif malformation == "missing_required_field":
            payload["research_results"][0].pop("evidence_score")
        elif malformation == "empty_required_number":
            payload["research_results"][0]["ranking_score"] = ""
        else:
            payload["research_results"].append(
                {
                    **payload["research_results"][0],
                    "sector_name": "Wrong Type",
                    "sector_type": "concept",
                }
            )
        write_json(
            roots["sector_research"] / as_of / "sector_research.json", payload
        )
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])

        stable = bridge.load_stable_sector_inputs(as_of)

        assert stable["industries"] == []
        assert stable["available"] is False

    def test_stable_industry_source_rejects_all_rows_after_late_schema_error(
        self, tmp_path, monkeypatch
    ):
        """A late malformed industry row must invalidate the whole source."""
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        write_json(
            roots["sector_research"] / as_of / "sector_research.json",
            {
                **_valid_industry_research_payload(as_of),
                "research_results": [
                    {
                        **_valid_industry_research_payload(as_of)[
                            "research_results"
                        ][0],
                    },
                    {
                        **_valid_industry_research_payload(as_of)[
                            "research_results"
                        ][0],
                        "sector_name": "Overflow Industry",
                        "ranking_score": 10**1000,
                    },
                ]
            },
        )
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])

        stable = bridge.load_stable_sector_inputs(
            as_of,
            score_data=load_sector_scores(
                roots["sector_scores"] / as_of / "sector_scores.json"
            ),
        )

        assert stable["industries"] == []
        assert stable["available"] is False

    def test_stable_concept_source_rejects_all_rows_after_nonfinite_value(
        self, tmp_path, monkeypatch
    ):
        """A late NaN/Inf concept value must invalidate the whole CSV source."""
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        concept_path = (
            roots["concept_rank"] / as_of / "concept_unified_rank.csv"
        )
        concept_path.parent.mkdir(parents=True)
        concept_path.write_text(
            "sector_name,concept_final_rank_score,trend_continuation_score,"
            "short_term_burst_score,rank,agent_consensus_label\n"
            "Valid Concept,90,80,70,1,observe\n"
            "Invalid Concept,NaN,80,70,2,observe\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])

        stable = bridge.load_stable_sector_inputs(as_of)

        assert stable["concepts"] == []
        assert stable["available"] is False

    @pytest.mark.parametrize("malformation", ["missing_header", "empty_number"])
    def test_stable_concept_source_rejects_incomplete_schema(
        self, tmp_path, monkeypatch, malformation
    ):
        import sector_stock_bridge as bridge

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        concept_path = roots["concept_rank"] / as_of / "concept_unified_rank.csv"
        concept_path.parent.mkdir(parents=True)
        if malformation == "missing_header":
            csv_text = (
                "rank,sector_name,concept_final_rank_score,trend_continuation_score,"
                "agent_consensus_label\n"
                "1,Incomplete Concept,90,80,observe\n"
            )
        else:
            csv_text = (
                "rank,sector_name,concept_final_rank_score,trend_continuation_score,"
                "short_term_burst_score,agent_consensus_label\n"
                "1,Empty Concept,,80,70,observe\n"
            )
        concept_path.write_text(csv_text, encoding="utf-8")
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])
        monkeypatch.setattr(
            bridge, "STABLE_RESEARCH_DIR", roots["sector_research"]
        )
        monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", roots["concept_rank"])

        stable = bridge.load_stable_sector_inputs(as_of)

        assert stable["concepts"] == []
        assert stable["available"] is False

    @pytest.mark.parametrize(
        "malformation",
        ["identity", "status", "weight", "source", "missing_field"],
    )
    def test_cache_loader_rejects_malformed_or_mismatched_payloads(
        self, tmp_path, monkeypatch, malformation
    ):
        """Cache hits must satisfy the constituent result contract and identity."""
        import sector_stock_bridge as bridge

        cache_dir = tmp_path / "cache"
        key = "2026-07-02_industry_证券"
        payload = {
            "status": "ok",
            "as_of_date": "2026-07-02",
            "sector_name": "证券",
            "sector_type": "industry",
            "stocks": [{"code": "600030", "name": "中信证券", "weight": 1.0}],
            "error": None,
            "fallback_used": False,
            "source": "http_em",
        }
        if malformation == "identity":
            payload["sector_name"] = "银行"
        elif malformation == "status":
            payload["status"] = "unknown"
        elif malformation == "weight":
            payload["stocks"][0]["weight"] = -0.1
        elif malformation == "source":
            payload["source"] = "untrusted"
        else:
            payload.pop("fallback_used")
        write_json(cache_dir / f"{key}.json", payload)
        monkeypatch.setattr(bridge, "CACHE_DIR", cache_dir)

        assert bridge._load_cache(
            key,
            expected_sector_name="证券",
            expected_sector_type="industry",
        ) is None

    def test_cache_loader_rejects_payload_from_another_request_date(
        self, tmp_path, monkeypatch
    ):
        import sector_stock_bridge as bridge

        cache_dir = tmp_path / "cache"
        key = "2026-07-02_industry_证券"
        write_json(
            cache_dir / f"{key}.json",
            {
                "status": "ok",
                "as_of_date": "2026-07-01",
                "sector_name": "证券",
                "sector_type": "industry",
                "stocks": [
                    {"code": "600030", "name": "中信证券", "weight": 1.0}
                ],
                "error": None,
                "fallback_used": False,
                "source": "http_em",
            },
        )
        monkeypatch.setattr(bridge, "CACHE_DIR", cache_dir)

        assert bridge._load_cache(
            key,
            expected_sector_name="证券",
            expected_sector_type="industry",
            expected_as_of_date="2026-07-02",
        ) is None


# ============================================================
# 测试：板块提取
# ============================================================

class TestSectorExtraction:

    def test_extract_top_sectors_trend(self, sample_scores_data):
        """趋势 Top5 应按趋势分排序"""
        trend, burst = extract_top_sectors(sample_scores_data, 5, 5)
        assert len(trend) == 5
        assert trend[0]["sector_name"] == "证券"
        assert trend[0]["trend_score"] == 40.35
        # 趋势分应递减
        for i in range(len(trend) - 1):
            assert trend[i]["trend_score"] >= trend[i + 1]["trend_score"]

    def test_extract_top_sectors_burst(self, sample_scores_data):
        """短线 Top5 应按爆发分排序"""
        trend, burst = extract_top_sectors(sample_scores_data, 5, 5)
        assert len(burst) == 5
        assert burst[0]["sector_name"] in ("医疗服务", "生物制品")
        # 短线分应递减
        for i in range(len(burst) - 1):
            assert burst[i]["burst_score"] >= burst[i + 1]["burst_score"]

    def test_find_cross_sectors(self, sample_scores_data):
        """重叠板块应正确识别"""
        trend, burst = extract_top_sectors(sample_scores_data, 5, 5)
        cross = find_cross_sectors(trend, burst)
        # 医学制药、保险、养殖业应同时出现在两个列表
        assert "保险" in cross
        assert "化学制药" in cross
        assert "养殖业" in cross


# ============================================================
# 测试：关联度计算
# ============================================================

class TestRelevanceComputation:

    def test_normalize_weights(self, sample_stocks):
        """权重归一化"""
        normalized = _normalize_weights(sample_stocks)
        weights = [s["weight_normalized"] for s in normalized]
        assert max(weights) == 1.0
        assert min(weights) > 0

    def test_compute_rank_scores(self, sample_stocks):
        """涨幅排名分应正确计算"""
        ranked = _compute_rank_scores(sample_stocks)
        # 最高涨幅应排名第一
        top = max(ranked, key=lambda x: x.get("rank_score", 0))
        assert top["code"] == "600030"  # 中信证券 +2.3%
        assert top["rank_in_sector"] == 1
        # 排名分应在 0~1 之间
        for s in ranked:
            assert 0 <= s["rank_score"] <= 1

    def test_flow_alignment_both_inflow(self):
        """板块流入 + 个股流入 → 最高对齐"""
        result = _compute_flow_alignment("inflow", "inflow")
        assert result == 1.0

    def test_flow_alignment_both_outflow(self):
        """板块流出 + 个股流出 → 中等对齐"""
        result = _compute_flow_alignment("outflow", "outflow")
        assert result == pytest.approx(0.8 / 1.2, abs=0.01)

    def test_flow_alignment_individual逆势(self):
        """板块流出 + 个股流入 → 谨慎对齐"""
        result = _compute_flow_alignment("inflow", "outflow")
        assert result == pytest.approx(0.5 / 1.2, abs=0.01)

    def test_flow_alignment_individual背离(self):
        """板块流入 + 个股流出 → 低对齐"""
        result = _compute_flow_alignment("outflow", "inflow")
        assert result == pytest.approx(0.3 / 1.2, abs=0.01)

    def test_flow_alignment_neutral_fallback(self):
        """资金流不可用时应降级到中性值"""
        result = _compute_flow_alignment("neutral", "inflow")
        assert result == pytest.approx(1.0 / 1.2, abs=0.01)

        result = _compute_flow_alignment("inflow", "neutral")
        assert result == pytest.approx(1.0 / 1.2, abs=0.01)

    def test_compute_relevance_scores(self, sample_stocks):
        """关联度应正确计算并过滤"""
        sector_flow = {"direction": "inflow"}
        filtered = compute_relevance_scores(sample_stocks, sector_flow, min_relevance=0.0)
        assert len(filtered) > 0
        # 每只股票应有完整的关联度字段
        for s in filtered:
            assert "relevance_score" in s
            assert "relevance_breakdown" in s
            assert "rank_score" in s
            assert "weight_normalized" in s
            assert 0 <= s["relevance_score"] <= 1

    def test_relevance_filtering(self, sample_stocks):
        """高阈值应过滤掉更多股票"""
        sector_flow = {"direction": "neutral"}
        low_thresh = compute_relevance_scores(sample_stocks, sector_flow, min_relevance=0.0)
        high_thresh = compute_relevance_scores(sample_stocks, sector_flow, min_relevance=0.8)
        assert len(high_thresh) <= len(low_thresh)

    def test_relevance_formula_weights(self, sample_stocks):
        """关联度应遵循三维度加权公式"""
        sector_flow = {"direction": "neutral"}
        result = compute_relevance_scores(sample_stocks, sector_flow, min_relevance=0.0)
        for s in result:
            bd = s["relevance_breakdown"]
            expected = 0.2 * bd["weight_score"] + 0.4 * bd["rank_score"] + 0.4 * bd["flow_alignment"]
            assert s["relevance_score"] == pytest.approx(expected, abs=0.01)

    def test_run_bridge_preserves_constituent_weight_for_normalization(
        self, isolated_bridge_reports, monkeypatch
    ):
        import sector_stock_bridge as bridge

        monkeypatch.setattr(
            bridge,
            "fetch_sector_constituents",
            lambda *_args, **_kwargs: {
                "status": "ok",
                "stocks": [
                    {"code": "600001", "name": "Heavy", "weight": 0.8},
                    {"code": "600002", "name": "Light", "weight": 0.2},
                ],
                "error": None,
                "fallback_used": False,
                "source": "http_em",
            },
        )
        monkeypatch.setattr(
            bridge,
            "fetch_tencent_quotes",
            lambda _codes: {
                "600001": {"change_pct": 0.0},
                "600002": {"change_pct": 0.0},
            },
        )
        monkeypatch.setattr(
            bridge,
            "fetch_sector_fund_flow",
            lambda _name: {"status": "ok", "direction": "neutral", "error": None},
        )
        monkeypatch.setattr(bridge, "fetch_individual_fund_flow", lambda _codes: {})

        result = bridge.run_bridge(
            as_of_date="2026-07-01",
            trend_top_n=1,
            burst_top_n=1,
            min_relevance=0.0,
        )

        stocks = {
            stock["code"]: stock for stock in result["trend_sectors"][0]["stocks"]
        }
        assert stocks["600001"]["weight"] == pytest.approx(0.8)
        assert stocks["600001"]["sector_weight"] == pytest.approx(0.8)
        assert stocks["600001"]["weight_normalized"] == pytest.approx(1.0)
        assert stocks["600002"]["weight_normalized"] == pytest.approx(0.25)
        research = result["linkage_research"]
        assert research["mode"] == "paper_shadow_research_only"
        assert research["legacy_policy"]["status"] == "frozen_baseline"
        assert len(research["legacy_policy"]["policy_sha256"]) == 64
        assert len(research["score_input"]["sha256"]) == 64
        assert research["sector_funnel"][0]["raw_constituent_count"] == 2
        assert research["sector_funnel"][0]["legacy_relevance_pass_count"] == 2
        research = result["linkage_research"]
        assert research["mode"] == "paper_shadow_research_only"
        assert research["legacy_policy"]["status"] == "frozen_baseline"
        assert len(research["legacy_policy"]["policy_sha256"]) == 64
        assert len(research["score_input"]["sha256"]) == 64
        assert research["sector_funnel"][0]["raw_constituent_count"] == 2
        assert research["sector_funnel"][0]["legacy_relevance_pass_count"] == 2


# ============================================================
# 测试：降级处理
# ============================================================

class TestDegradation:

    def test_flow_alignment_all_neutral(self):
        """所有资金流数据不可用时，关联度仍可计算"""
        stocks = [
            {"code": "600030", "name": "中信证券", "weight": 0.15, "change_pct": 2.3,
             "individual_flow_direction": "neutral"},
        ]
        sector_flow = {"direction": "neutral"}
        result = compute_relevance_scores(stocks, sector_flow, min_relevance=0.0)
        assert len(result) == 1
        # 中性值下，关联度主要由涨幅排名决定
        assert result[0]["relevance_score"] > 0

    def test_fallback_quant_score(self):
        """降级量化评分应产生合理分数"""
        stock = {
            "change_pct": 2.0,
            "total_mv": 200,
            "pe": 15,
            "pb": 2.0,
            "sector_trend_score": 60,
            "sector_burst_score": 50,
        }
        score, breakdown = _compute_fallback_quant_score(stock)
        assert 0 <= score <= 100
        assert score > 30  # 应该有不错的分数
        assert "raw_total" in breakdown
        assert "normalized" in breakdown

    def test_fallback_quant_score_poor_stock(self):
        """差股票应得低分"""
        stock = {
            "change_pct": -5.0,
            "total_mv": 5,
            "pe": 500,
            "pb": 50,
        }
        score, breakdown = _compute_fallback_quant_score(stock)
        assert score < 30


# ============================================================
# 测试：输出结构
# ============================================================

class TestOutputStructure:

    def test_bridge_output_has_required_fields(self, sample_scores_data):
        """桥接输出应包含所有必需字段"""
        trend, burst = extract_top_sectors(sample_scores_data, 5, 5)
        cross = find_cross_sectors(trend, burst)

        # 验证趋势板块结构
        for s in trend:
            assert "sector_name" in s
            assert "trend_score" in s
            assert "burst_score" in s
            assert "sector_type" in s

        # 验证短线板块结构
        for s in burst:
            assert "sector_name" in s
            assert "burst_score" in s

        # 验证重叠
        assert isinstance(cross, list)

    def test_final_score_computation(self):
        """综合分应正确计算（v2公式）"""
        stocks = [
            {"code": "600030", "quant_score": 80, "relevance_score": 0.9, "sector_trend_score": 70, "sector_burst_score": 60},
            {"code": "601211", "quant_score": 60, "relevance_score": 0.7, "sector_trend_score": 50, "sector_burst_score": 40},
        ]
        result = compute_final_scores(stocks)
        assert len(result) == 2
        # v2 公式: quant*0.5 + relevance*30 + sector_momentum*20
        # sector_momentum = (trend + burst) / 200
        sm1 = (70 + 60) / 200
        expected_1 = (80 / 100 * 0.5 + 0.9 * 0.3 + sm1 * 0.2) * 100
        assert result[0]["final_score"] == pytest.approx(expected_1, abs=0.1)
        # 应按综合分降序排列
        assert result[0]["final_score"] >= result[1]["final_score"]

    def test_unified_report_json_fields(self):
        """unified JSON 报告应包含所有必需字段"""
        # 模拟一个最小报告
        report = {
            "report_type": "unified_pipeline",
            "version": "0.1.0",
            "as_of_date": "2026-07-01",
            "trend_top_stocks": [],
            "burst_top_stocks": [],
            "bridge_summary": {},
            "scoring_method": {},
        }
        required = ["report_type", "version", "as_of_date", "trend_top_stocks", "burst_top_stocks"]
        for field in required:
            assert field in report


# ============================================================
# 测试：HTTP 增强量化评分
# ============================================================


class TestEnhancedQuantScore:
    """Test _compute_enhanced_quant_score with sample bar data."""

    def test_enhanced_score_with_full_bars(self):
        """提供 20 根 K 线应计算所有因子。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": 3.0, "total_mv": 200, "pe": 15}
        bars = [
            {"date": f"2026-06-{d:02d}", "open": 20, "high": 21, "low": 19, "close": 20 + i * 0.1, "amount": 3e8}
            for i, d in enumerate(range(1, 21))
        ]
        score, breakdown = _compute_enhanced_quant_score(stock, bars)
        assert 0 <= score <= 100
        # With positive returns, decent MV, good PE, should be reasonably good
        assert score > 30
        assert "raw_total" in breakdown
        assert "1d_momentum" in breakdown

    def test_enhanced_score_with_poor_bars(self):
        """下跌+高回撤应得低分。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": -5.0, "total_mv": 5, "pe": 500}
        bars = [
            {"date": f"2026-06-{d:02d}", "open": 20, "high": 21, "low": 19,
             "close": 20 - i * 0.8, "amount": 1e6}
            for i, d in enumerate(range(1, 21))
        ]
        score, breakdown = _compute_enhanced_quant_score(stock, bars)
        assert score < 30

    def test_enhanced_score_min_bars(self):
        """只有 5 根 K 线时，应跳过 10 日因子但仍能正常计算。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": 2.0, "total_mv": 100, "pe": 20}
        bars = [
            {"date": f"2026-07-0{i}", "open": 20, "high": 21, "low": 19, "close": 21 + i * 0.2, "amount": 2e8}
            for i in range(5)
        ]
        score, breakdown = _compute_enhanced_quant_score(stock, bars)
        assert 0 <= score <= 100

    def test_enhanced_score_with_zero_bars(self):
        """零根 K 线时不抛异常。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": 0, "total_mv": 0, "pe": 0}
        score, breakdown = _compute_enhanced_quant_score(stock, [])
        assert 0 <= score <= 100


class TestQuantScoreFallback:
    """Test quant score fallback behaviour."""

    def test_quant_scores_falls_back_without_http(self, monkeypatch):
        """无 HTTP 客户端时 compute_quant_scores 应回退到 fallback。"""
        import unified_pipeline as up

        # Ensure no HTTP client is available
        monkeypatch.setattr(up, "_get_http_client", lambda: None)

        stocks = [
            {"code": "600030", "change_pct": 2.0, "total_mv": 200, "pe": 15},
            {"code": "601211", "change_pct": -1.0, "total_mv": 150, "pe": 25},
        ]
        result = up.compute_quant_scores(stocks, as_of_date="2026-07-02")
        for s in result:
            assert "quant_score" in s
            assert "fallback_v2" in s["quant_source"]
            assert 0 <= s["quant_score"] <= 100

    def test_quant_scores_uses_http_when_available(self):
        """当 HTTP 返回 >5 根 K 线时，应使用 enhanced scorer。"""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up

        sample_bars = [
            {"date": f"2026-06-{d:02d}", "open": 20, "high": 21, "low": 19, "close": 20 + i * 0.1, "amount": 3e8}
            for i, d in enumerate(range(5, 30))
        ]

        mock_client = MagicMock()
        mock_client.get_stock_bars.return_value = sample_bars
        mock_client.get_stock_fund_flow.return_value = None  # no fund flow
        mock_client.get_stock_fund_flow_batch.return_value = None  # batch also none

        monkeypatch = __import__("pytest").MonkeyPatch()
        # We can't use monkeypatch fixture inside a non-fixture context,
        # so test this differently — inject via module attribute

        # Use patch context manager
        with patch.object(up, "_get_http_client", return_value=mock_client):
            stocks = [
                {"code": "600633", "change_pct": 3.0, "total_mv": 300, "pe": 20},
            ]
            result = up.compute_quant_scores(stocks, as_of_date="2026-07-02")
            assert len(result) == 1
            assert "http_enhanced_v2" in result[0]["quant_source"]
            assert 0 <= result[0]["quant_score"] <= 100

    def test_quant_scores_falls_back_on_http_error(self):
        """HTTP API 报错时，应回退到 fallback。"""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up

        mock_client = MagicMock()
        mock_client.get_stock_bars.side_effect = ConnectionError("down")

        with patch.object(up, "_get_http_client", return_value=mock_client):
            stocks = [
                {"code": "600633", "change_pct": 2.0, "total_mv": 200, "pe": 20},
            ]
            result = up.compute_quant_scores(stocks, as_of_date="2026-07-02")
            assert "fallback_v2" in result[0]["quant_source"]

    def test_quant_scores_skips_http_calls_when_health_fails(self):
        """HTTP health 失败时，不应继续逐股请求 bars/fund-flow。"""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up

        mock_client = MagicMock()
        mock_client.health_check.side_effect = ConnectionError("api down")

        with patch.object(up, "_get_http_client", return_value=mock_client):
            stocks = [
                {"code": "600633", "change_pct": 2.0, "total_mv": 200, "pe": 20},
                {"code": "000001", "change_pct": 1.0, "total_mv": 300, "pe": 10},
            ]
            result = up.compute_quant_scores(stocks, as_of_date="2026-07-02")

        assert all("fallback_v2" in s["quant_source"] for s in result)
        mock_client.get_stock_bars.assert_not_called()
        mock_client.get_stock_fund_flow_batch.assert_not_called()
        mock_client.get_stock_fund_flow.assert_not_called()
    def test_enhanced_score_drawdown_calculation(self):
        """验证最大回撤因子：先涨后跌应产生非零回撤。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": -2.0, "total_mv": 200, "pe": 20}
        # Peak at index 5, then drops
        bars = []
        for i in range(10):
            close = 20 + min(i, 5) * 2 - max(i - 5, 0) * 1.5
            bars.append({"date": f"2026-07-0{i}", "open": close, "high": close + 0.5,
                         "low": close - 0.5, "close": close, "amount": 2e8})

        score, breakdown = _compute_enhanced_quant_score(stock, bars)
        assert 0 <= score <= 100
        # Should be lower than a stock with no drawdown
        bars_no_dd = [
            {"date": f"2026-07-0{i}", "open": 20, "high": 21, "low": 19,
             "close": 20 + i * 0.5, "amount": 2e8}
            for i in range(10)
        ]
        score_no_dd, _ = _compute_enhanced_quant_score(stock, bars_no_dd)
        assert score_no_dd > score  # no drawdown should be higher


# ============================================================
# 测试：桥接层 HTTP 集成
# ============================================================


class TestBridgeHttpIntegration:
    """Test that fetch_sector_constituents uses simplified Phase 3 fallback."""

    @pytest.fixture(autouse=True)
    def _disable_live_sina(self, monkeypatch):
        import sector_stock_bridge as bridge

        monkeypatch.setattr(bridge, "_fetch_sina_constituents", lambda _name: [])

    # ------------------------------------------------------------------
    # HTTP success scenarios
    # ------------------------------------------------------------------

    def test_http_200_em_source(self):
        """HTTP 200 + stocks have source='em' → result.source='http_em'."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "688981", "name": "中芯国际", "market_cap": 500e9, "source": "em"},
            {"code": "002371", "name": "北方华创", "market_cap": 300e9, "source": "em"},
        ]

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.fetch_sector_constituents("半导体")
                    assert result["source"] == "http_em"
                    assert result["status"] == "ok"
                    assert result["fallback_used"] is False
                    assert len(result["stocks"]) == 2
                    assert result["stocks"][0]["code"] == "688981"

    def test_requested_as_of_binds_cache_key_and_saved_payload(self, monkeypatch):
        from unittest.mock import MagicMock
        import sector_stock_bridge as bridge

        requested_as_of = "2026-07-02"
        observed = {}

        def load_cache(key, **kwargs):
            observed["load_key"] = key
            observed["load_kwargs"] = kwargs
            return None

        def save_cache(key, payload):
            observed["save_key"] = key
            observed["payload"] = payload.copy()

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "600030", "name": "中信证券", "market_cap": 1.0, "source": "em"}
        ]
        monkeypatch.setattr(bridge, "_get_http_client", lambda: mock_client)
        monkeypatch.setattr(bridge, "_load_cache", load_cache)
        monkeypatch.setattr(bridge, "_save_cache", save_cache)

        result = bridge.fetch_sector_constituents(
            "证券", sector_type="industry", as_of=requested_as_of
        )

        expected_key = f"{requested_as_of}_industry_证券"
        assert observed["load_key"] == expected_key
        assert observed["save_key"] == expected_key
        assert observed["load_kwargs"]["expected_as_of_date"] == requested_as_of
        assert observed["payload"]["as_of_date"] == requested_as_of
        assert result["as_of_date"] == requested_as_of

    def test_http_200_mapping_source(self):
        """HTTP 200 + stocks have source='mapping' → trust it, no local fallback."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "600030", "name": "中信证券", "market_cap": 300e9, "source": "mapping"},
            {"code": "601211", "name": "国泰君安", "market_cap": 250e9, "source": "mapping"},
        ]

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.fetch_sector_constituents("证券")
                    # Trust HTTP — the market_data_service already did its fallback
                    assert result["source"] == "http_mapping"
                    assert result["status"] == "ok"
                    assert result["fallback_used"] is False
                    assert len(result["stocks"]) == 2

    def test_http_200_empty_list(self):
        """HTTP 200 + empty list → trust it, source='http_em'."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = []

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.fetch_sector_constituents("未知板块X")
                    assert result["source"] == "http_em"
                    assert result["stocks"] == []

    # ------------------------------------------------------------------
    # HTTP failure scenarios — emergency local fallback
    # ------------------------------------------------------------------

    def test_connection_refused_falls_back_to_local_mapping(self):
        """HTTP ConnectionError → use local SECTOR_STOCK_MAPPING."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.side_effect = ConnectionError("refused")

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.fetch_sector_constituents("半导体")
                    assert result["source"] == "local_emergency_mapping"
                    assert result["fallback_used"] is True
                    assert len(result["stocks"]) > 0
                    # Should come from SECTOR_STOCK_MAPPING or Sina
                    codes = [s["code"] for s in result["stocks"]]
                    assert "688981" in codes or len(codes) > 0

    def test_timeout_falls_back_to_local_mapping(self):
        """HTTP TimeoutError → use local SECTOR_STOCK_MAPPING."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.side_effect = TimeoutError("timed out")

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.fetch_sector_constituents("证券")
                    assert result["source"] == "local_emergency_mapping"
                    assert len(result["stocks"]) > 0
                    codes = [s["code"] for s in result["stocks"]]
                    assert "600030" in codes or len(codes) > 0

    def test_connection_failure_unknown_sector(self):
        """HTTP fails + sector NOT in local mapping → unavailable."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.side_effect = ConnectionError("refused")

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.fetch_sector_constituents("完全不存在的板块XYZ")
                    assert result["source"] == "unavailable"
                    assert result["status"] == "degraded"
                    assert len(result["stocks"]) == 0

    # ------------------------------------------------------------------
    # No HTTP client at all
    # ------------------------------------------------------------------

    def test_no_http_client_falls_back_to_local_mapping(self):
        """No HTTP client available → use local SECTOR_STOCK_MAPPING."""
        from unittest.mock import patch
        import sector_stock_bridge as bridge

        with patch.object(bridge, "_get_http_client", return_value=None):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.fetch_sector_constituents("半导体")
                    assert result["source"] == "local_emergency_mapping"
                    assert len(result["stocks"]) > 0

    # ------------------------------------------------------------------
    # Source field contract
    # ------------------------------------------------------------------

    def test_source_field_values(self):
        """Verify all accepted source values."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        # HTTP em
        mock_ok = MagicMock()
        mock_ok.get_board_constituents.return_value = [
            {"code": "688981", "name": "中芯国际", "market_cap": 1e9, "source": "em"},
        ]
        with patch.object(bridge, "_get_http_client", return_value=mock_ok):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    r = bridge.fetch_sector_constituents("半导体")
                    assert r["source"] in ("http_em", "http_mapping", "local_emergency_mapping", "unavailable")

        # HTTP mapping
        mock_map = MagicMock()
        mock_map.get_board_constituents.return_value = [
            {"code": "600030", "name": "中信证券", "market_cap": 1e9, "source": "mapping"},
        ]
        with patch.object(bridge, "_get_http_client", return_value=mock_map):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    r = bridge.fetch_sector_constituents("证券")
                    assert r["source"] == "http_mapping"

        # Local emergency
        mock_fail = MagicMock()
        mock_fail.get_board_constituents.side_effect = ConnectionError("refused")
        with patch.object(bridge, "_get_http_client", return_value=mock_fail):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    r = bridge.fetch_sector_constituents("半导体")
                    assert r["source"] == "local_emergency_mapping"

        # Unavailable
        mock_fail2 = MagicMock()
        mock_fail2.get_board_constituents.side_effect = ConnectionError("refused")
        with patch.object(bridge, "_get_http_client", return_value=mock_fail2):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    r = bridge.fetch_sector_constituents("不存在XYZ板块")
                    assert r["source"] == "unavailable"


# ============================================================
# 测试：数据来源透明化（Phase 5）
# ============================================================


class TestSourceTransparency:
    """Test that output reports include source distribution summaries."""

    def test_direction_linkage_summary_is_machine_readable(self):
        import unified_pipeline as up

        summary = up._build_direction_linkage_summary(
            [
                {
                    "sector_name": "Core A",
                    "candidate_tier": "core",
                    "linkage_v2_shadow": {"status": "unavailable"},
                },
                {
                    "sector_name": "Core A",
                    "candidate_tier": "core",
                    "linkage_v2_shadow": {"status": "ok"},
                },
                {
                    "sector_name": "Supplemental B",
                    "candidate_tier": "supplemental",
                    "linkage_v2_shadow": {"status": "partial"},
                },
            ],
            {"selected_count": 2},
            {"sector_count": 17},
            [{"sector_name": "Confirm C"}],
        )

        assert summary == {
            "sector_groups": {
                "core": ["Core A"],
                "supplemental": ["Supplemental B"],
                "confirmation_required": ["Confirm C"],
            },
            "sector_group_counts": {
                "core": 1,
                "supplemental": 1,
                "confirmation_required": 1,
            },
            "candidate_count": 3,
            "linkage_v2_status_counts": {"ok": 1, "partial": 1, "unavailable": 1},
            "selected_count": 2,
            "history_sector_count": 17,
        }

    def test_sector_cluster_map_loader_is_sha_bound(self, tmp_path):
        import unified_pipeline as up

        path = write_json(
            tmp_path / "clusters.json",
            {
                "schema_version": "path_a_sector_cluster_map.v1",
                "mode": "paper_shadow_research_only",
                "clusters": {
                    "Health": ["Medical", "Pharma"],
                    "Agriculture": ["Breeding"],
                },
            },
        )

        mapping, audit = up.load_sector_cluster_map(path)

        assert mapping == {
            "Medical": "Health",
            "Pharma": "Health",
            "Breeding": "Agriculture",
        }
        assert audit["status"] == "ok"
        assert audit["mapped_sector_count"] == 3
        assert len(audit["sha256"]) == 64
        assert len(audit["mapping_sha256"]) == 64

    def test_default_cluster_map_can_form_40pct_capped_portfolio(self):
        import unified_pipeline as up

        mapping, _audit = up.load_sector_cluster_map(
            up.DEFAULT_SECTOR_CLUSTER_MAP_PATH
        )
        current_direction_sectors = {
            "医疗服务",
            "中药",
            "化学制药",
            "生物制品",
            "医药商业",
            "养殖业",
        }

        assert current_direction_sectors <= set(mapping)
        assert len({mapping[name] for name in current_direction_sectors}) >= 3

    def test_direction_shadow_runtime_stats_do_not_overwrite_legacy_stats(
        self, tmp_path, monkeypatch
    ):
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up

        client = MagicMock()
        client.health_check.side_effect = ConnectionError("offline")
        legacy_stock = {
            "code": "600001",
            "name": "Legacy",
            "change_pct": 1.0,
            "total_mv": 100.0,
            "pe": 10.0,
            "pb": 1.0,
            "relevance_score": 0.8,
        }
        shadow_stock = {
            "code": "600002",
            "name": "Shadow",
            "change_pct": 1.0,
            "total_mv": 100.0,
            "pe": 10.0,
            "pb": 1.0,
            "relevance_score": 0.8,
        }
        bridge_result = {
            "status": "ok",
            "as_of_date": "2026-07-01",
            "trend_sectors": [
                {
                    "sector_name": "Legacy",
                    "trend_score": 60.0,
                    "burst_score": 50.0,
                    "high_relevance_count": 1,
                    "stocks": [legacy_stock],
                }
            ],
            "burst_sectors": [],
            "direction_shadow_sectors": [
                {
                    "sector_name": "Shadow",
                    "sector_type": "industry",
                    "trend_score": 0.0,
                    "burst_score": 0.0,
                    "candidate_tier": "core",
                    "shadow_prefilter_stocks": [shadow_stock],
                }
            ],
            "direction_confirmation_sectors": [],
            "cross_sectors": [],
            "constituent_source_summary": {},
            "api_status": {},
            "linkage_research": {},
        }
        validated = (
            "2026-07-01",
            tmp_path / "sector_scores.json",
            {
                "as_of_date": "2026-07-01",
                "scores": [
                    {
                        "sector_name": "Legacy",
                        "sector_type": "industry",
                        "trend_continuation_score": 60.0,
                        "short_term_burst_score": 50.0,
                    }
                ],
            },
        )

        def fake_quant(stocks, **_kwargs):
            source = "shadow_source" if stocks[0]["sector_name"] == "Shadow" else "legacy_source"
            fake_quant._last_fund_flow_source = source
            up.compute_quant_scores._last_fund_flow_source = source
            for stock in stocks:
                stock["quant_score"] = 50.0
                stock["quant_breakdown"] = {}
                stock["quant_source"] = "fallback_v2"
                stock["linkage_v2_shadow"] = {
                    "status": "unavailable",
                    "score": None,
                }
            return stocks

        with patch.object(
            up, "validate_explicit_score_report", return_value=(True, validated, None)
        ), patch.object(up, "run_bridge", return_value=bridge_result), patch.object(
            up, "_get_http_client", return_value=client
        ), patch.object(up, "compute_quant_scores", side_effect=fake_quant) as quant:
            quant._last_fund_flow_source = "fund_flow_neutral"
            result = up.run_pipeline(
                as_of_date="2026-07-01",
                output_dir=str(tmp_path / "out"),
            )
            bridge_result["trend_sectors"] = []
            second_result = up.run_pipeline(
                as_of_date="2026-07-01",
                output_dir=str(tmp_path / "out-second"),
            )

        assert result["data_source"]["fund_flow_source"] == "legacy_source"
        assert result["data_source"]["stock_info_sources"]["unknown"] == 1
        assert result["direction_shadow_runtime_audit"]["fund_flow_source"] == "shadow_source"
        assert result["direction_shadow_runtime_audit"]["stock_info_sources"]["unknown"] == 1
        assert second_result["data_source"]["fund_flow_source"] == "not_evaluated"

    def test_direction_shadow_uses_stockdb_bars_without_changing_legacy_path(
        self, tmp_path, monkeypatch
    ):
        from unittest.mock import patch
        import unified_pipeline as up

        bars = [
            {
                "date": f"202607{day:02d}",
                "open": 10.0 + day,
                "high": 11.0 + day,
                "low": 9.0 + day,
                "close": 10.0 + day,
                "volume": 1_000_000,
                "amount": 100_000_000,
            }
            for day in range(1, 22)
        ]

        class OfflineHttp:
            def health_check(self):
                raise ConnectionError("offline")

        class StockDbBars:
            selection = {
                "source": "stockdb-sdk",
                "reason": "http_unavailable",
                "http_latest_daily_date": None,
                "sdk_latest_daily_date": "20260721",
                "expected_min_date": "20260721",
                "http_error": "offline",
                "sdk_error": None,
            }

            def get_stock_bars(self, *_args, **_kwargs):
                return bars

        auto_calls = []

        def fake_auto_bars_client(**kwargs):
            auto_calls.append(kwargs)
            return StockDbBars()

        legacy_stock = {
            "code": "600001",
            "name": "Legacy",
            "change_pct": 1.0,
            "total_mv": 100.0,
            "pe": 10.0,
            "pb": 1.0,
            "relevance_score": 0.8,
        }
        shadow_stock = {
            "code": "600002",
            "name": "Shadow",
            "change_pct": 1.0,
            "total_mv": 100.0,
            "pe": 10.0,
            "pb": 1.0,
            "relevance_score": 0.8,
            "quote_available": True,
            "constituent_source": "http_em",
        }
        bridge_result = {
            "status": "ok",
            "as_of_date": "2026-07-21",
            "trend_sectors": [
                {
                    "sector_name": "Legacy",
                    "trend_score": 60.0,
                    "burst_score": 50.0,
                    "high_relevance_count": 1,
                    "stocks": [legacy_stock],
                }
            ],
            "burst_sectors": [],
            "direction_shadow_sectors": [
                {
                    "sector_name": "Shadow",
                    "sector_type": "industry",
                    "trend_score": 70.0,
                    "burst_score": 60.0,
                    "candidate_tier": "core",
                    "shadow_prefilter_stocks": [shadow_stock],
                }
            ],
            "direction_confirmation_sectors": [],
            "cross_sectors": [],
            "constituent_source_summary": {},
            "api_status": {},
            "linkage_research": {},
        }
        validated = (
            "2026-07-21",
            tmp_path / "sector_scores.json",
            {"as_of_date": "2026-07-21", "scores": []},
        )
        stock_returns = up.returns_by_date_from_bars(
            [
                {**bar, "date": f"2026-07-{index:02d}"}
                for index, bar in enumerate(bars, 1)
            ],
            as_of_date="2026-07-21",
        )
        history = {
            "Shadow": {
                "recent_dates": list(stock_returns),
                "recent_returns": [value * 0.8 for value in stock_returns.values()],
            }
        }
        monkeypatch.setattr(up, "AutoBarsClient", fake_auto_bars_client, raising=False)

        with patch.object(
            up, "validate_explicit_score_report", return_value=(True, validated, None)
        ), patch.object(up, "run_bridge", return_value=bridge_result), patch.object(
            up, "_get_http_client", return_value=OfflineHttp()
        ), patch.object(
            up, "load_sector_trend_history", return_value=(history, [])
        ):
            result = up.run_pipeline(
                as_of_date="2026-07-21",
                sector_history_root=str(tmp_path / "history"),
                output_dir=str(tmp_path / "out"),
            )

        assert len(auto_calls) == 1
        assert auto_calls[0]["expected_min_date"] == "2026-07-21"
        assert result["trend_top_stocks"][0]["quant_source"] == "fallback_v2"
        shadow = result["direction_shadow_candidates_all"][0]
        assert shadow["quant_source"] == "stockdb_sdk_enhanced_v2"
        assert shadow["linkage_v2_shadow"]["status"] == "partial"
        audit = result["direction_shadow_runtime_audit"]
        assert audit["bars_source"] == "stockdb-sdk"
        assert audit["bars_reason"] == "http_unavailable"
        assert audit["latest_daily_date"] == "20260721"
        assert audit["stock_bar_coverage"] == {
            "requested_stock_count": 1,
            "usable_stock_count": 1,
            "requested_relation_count": 1,
            "usable_relation_count": 1,
            "coverage_ratio": 1.0,
            "minimum_bars": 5,
        }
        assert audit["fund_flow_source"] == "fund_flow_neutral"

    def test_direction_shadow_keeps_http_audit_when_auto_bars_init_fails(
        self, tmp_path
    ):
        from unittest.mock import patch
        import unified_pipeline as up

        class HealthyHttp:
            def health_check(self):
                return {"latest_daily_date": "20260716"}

            def get_stock_info_batch(self, _codes):
                return None

            def get_stock_info(self, _code):
                return None

        bridge_result = {
            "status": "ok",
            "as_of_date": "2026-07-16",
            "trend_sectors": [],
            "burst_sectors": [],
            "direction_shadow_sectors": [
                {
                    "sector_name": "Shadow",
                    "sector_type": "industry",
                    "trend_score": 70.0,
                    "burst_score": 60.0,
                    "candidate_tier": "core",
                    "shadow_prefilter_stocks": [
                        {
                            "code": "600002",
                            "name": "Shadow",
                            "change_pct": 1.0,
                            "relevance_score": 0.8,
                        }
                    ],
                }
            ],
            "direction_confirmation_sectors": [],
            "cross_sectors": [],
            "constituent_source_summary": {},
            "api_status": {},
            "linkage_research": {},
        }
        validated = (
            "2026-07-16",
            tmp_path / "sector_scores.json",
            {"as_of_date": "2026-07-16", "scores": []},
        )

        def fake_quant(stocks, **_kwargs):
            up.compute_quant_scores._last_fund_flow_source = "fund_flow_neutral"
            up.compute_quant_scores._last_bars_audit = {
                "source": "http",
                "reason": "direct_client",
                "latest_daily_date": "20260716",
                "requested_stock_count": 1,
                "usable_stock_count": 1,
                "requested_relation_count": 1,
                "usable_relation_count": 1,
                "coverage_ratio": 1.0,
                "minimum_bars": 5,
            }
            stocks[0]["linkage_v2_shadow"] = {
                "status": "partial",
                "score": 0.8,
            }
            stocks[0]["quant_score"] = 50.0
            return stocks

        with patch.object(
            up, "validate_explicit_score_report", return_value=(True, validated, None)
        ), patch.object(up, "run_bridge", return_value=bridge_result), patch.object(
            up, "_get_http_client", return_value=HealthyHttp()
        ), patch.object(
            up, "load_sector_trend_history",
            return_value=({"Shadow": {"recent_dates": [], "recent_returns": []}}, []),
        ), patch.object(
            up, "AutoBarsClient", side_effect=ImportError("SDK missing")
        ), patch.object(up, "compute_quant_scores", side_effect=fake_quant):
            result = up.run_pipeline(
                as_of_date="2026-07-16",
                sector_history_root=str(tmp_path / "history"),
                output_dir=str(tmp_path / "out"),
            )

        audit = result["direction_shadow_runtime_audit"]
        assert audit["bars_source"] == "http"
        assert audit["latest_daily_date"] == "20260716"
        assert audit["stock_bar_coverage"]["usable_stock_count"] == 1
        assert "bars_error" not in audit

    def test_bridge_output_has_constituent_source_summary(
        self, isolated_bridge_reports, offline_bridge_io
    ):
        """Bridge result should include constituent_source_summary dict."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "688981", "name": "中芯国际", "market_cap": 500e9, "source": "em"},
        ]

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.run_bridge(as_of_date="2026-07-01")
                    assert isinstance(result, dict)
                    assert "constituent_source_summary" in result
                    summary = result["constituent_source_summary"]
                    assert isinstance(summary, dict)
                    # Should have at least one key
                    assert len(summary) > 0
                    # Total should match number of unique sectors
                    total = sum(summary.values())
                    assert total > 0

    def test_source_summary_fields_are_valid(
        self, isolated_bridge_reports, offline_bridge_io
    ):
        """All keys in source summary should be known source labels."""
        from unittest.mock import MagicMock, patch
        import sector_stock_bridge as bridge

        valid_labels = {"http_em", "http_stale", "http_mapping", "http_local_industry",
                        "http_local_concept_members",
                        "local_emergency_mapping", "unavailable"}

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "600030", "name": "中信证券", "market_cap": 300e9, "source": "mapping"},
        ]

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(bridge, "_load_cache", return_value=None):
                with patch.object(bridge, "_save_cache"):
                    result = bridge.run_bridge(as_of_date="2026-07-01")
                    assert isinstance(result, dict)
                    summary = result["constituent_source_summary"]
                    for key in summary:
                        assert key in valid_labels, f"Unknown source label: {key}"

    def test_unified_json_has_data_source_field(
        self, tmp_path, isolated_bridge_reports, offline_bridge_io
    ):
        """Unified JSON report should include data_source section."""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up
        import sector_stock_bridge as bridge

        # Mock HTTP for both bridge and pipeline
        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "600030", "name": "中信证券", "market_cap": 300e9, "source": "em"},
        ]
        # Mock stock bars for quant scoring
        mock_bars = [
            {"date": "2026-06-15", "open": 20, "high": 21, "low": 19, "close": 21, "amount": 3e8},
            {"date": "2026-06-16", "open": 21, "high": 22, "low": 20, "close": 21.5, "amount": 3.1e8},
            {"date": "2026-06-17", "open": 21.5, "high": 22, "low": 21, "close": 22, "amount": 3.2e8},
            {"date": "2026-06-18", "open": 22, "high": 23, "low": 21.5, "close": 22.5, "amount": 3e8},
            {"date": "2026-06-19", "open": 22.5, "high": 23, "low": 22, "close": 23, "amount": 3.3e8},
        ]
        mock_client.get_stock_bars.return_value = mock_bars

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(up, "_get_http_client", return_value=mock_client):
                with patch.object(bridge, "_load_cache", return_value=None):
                    with patch.object(bridge, "_save_cache"):
                        result = up.run_pipeline(
                            as_of_date="2026-07-01",
                            mode="quick",
                            output_dir=str(tmp_path / "unified"),
                        )
                        assert isinstance(result.get("bridge_result"), dict)
                        assert "data_source" in result
                        ds = result["data_source"]
                        assert "constituent_sources" in ds
                        assert "quant_score_sources" in ds
                        assert "has_unavailable_sectors" in ds
                        assert "has_emergency_fallback" in ds

    def test_unified_json_has_bridge_source_summary(
        self, tmp_path, isolated_bridge_reports, offline_bridge_io
    ):
        """Bridge summary in unified JSON should include constituent_source_summary."""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "600030", "name": "中信证券", "market_cap": 300e9, "source": "em"},
        ]
        mock_bars = [
            {"date": "2026-06-20", "open": 20, "high": 21, "low": 19, "close": 21, "amount": 3e8},
            {"date": "2026-06-21", "open": 21, "high": 22, "low": 20, "close": 21.5, "amount": 3e8},
            {"date": "2026-06-22", "open": 21.5, "high": 22, "low": 21, "close": 22, "amount": 3e8},
            {"date": "2026-06-23", "open": 22, "high": 23, "low": 21.5, "close": 22.5, "amount": 3e8},
            {"date": "2026-06-24", "open": 22.5, "high": 23, "low": 22, "close": 23, "amount": 3e8},
        ]
        mock_client.get_stock_bars.return_value = mock_bars

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(up, "_get_http_client", return_value=mock_client):
                with patch.object(bridge, "_load_cache", return_value=None):
                    with patch.object(bridge, "_save_cache"):
                        result = up.run_pipeline(
                            as_of_date="2026-07-01",
                            mode="quick",
                            output_dir=str(tmp_path / "unified"),
                        )
                        bs = result.get("bridge_result")
                        assert isinstance(bs, dict)
                        assert "constituent_source_summary" in bs

    def test_pipeline_reuses_single_failed_api_health_check(self, tmp_path):
        """run_pipeline should decide API availability once and skip all per-stock HTTP calls."""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up

        mock_client = MagicMock()
        mock_client.health_check.side_effect = ConnectionError("api down")
        fake_bridge_result = {
            "status": "ok",
            "as_of_date": "2026-07-01",
            "trend_sectors": [
                {
                    "sector_name": "VPN",
                    "trend_score": 60,
                    "burst_score": 50,
                    "high_relevance_count": 1,
                    "total_constituents": 1,
                    "stocks": [
                        {"code": "600633", "name": "测试股份", "change_pct": 2.0, "total_mv": 200, "pe": 20, "relevance_score": 0.8}
                    ],
                }
            ],
            "burst_sectors": [],
            "cross_sectors": [],
            "constituent_source_summary": {"http_mapping": 1},
            "sector_input_source": "test",
            "api_status": {"mock": "down"},
        }

        validated_score = (
            "2026-07-01",
            tmp_path / "sector_scores.json",
            {
                "as_of_date": "2026-07-01",
                "scores": [
                    {
                        "sector_name": "VPN",
                        "sector_type": "concept",
                        "trend_continuation_score": 60.0,
                        "short_term_burst_score": 50.0,
                    }
                ],
            },
        )
        with patch.object(
            up,
            "validate_explicit_score_report",
            return_value=(True, validated_score, None),
        ):
            with patch.object(up, "run_bridge", return_value=fake_bridge_result), patch.object(
                up, "_get_http_client", return_value=mock_client
            ):
                result = up.run_pipeline(
                    as_of_date="2026-07-02",
                    mode="quick",
                    output_dir=str(tmp_path),
                )

        assert result["data_source"]["market_data_service_reachable"] is False
        assert "api_unavailable_fast_path" in result["warnings"]
        assert mock_client.health_check.call_count == 1
        mock_client.get_stock_info_batch.assert_not_called()
        mock_client.get_stock_info.assert_not_called()
        mock_client.get_stock_bars.assert_not_called()
        mock_client.get_stock_fund_flow_batch.assert_not_called()
        mock_client.get_stock_fund_flow.assert_not_called()
        assert result["as_of_date"] == "2026-07-02"
        assert result["score_as_of_date"] == "2026-07-01"
        report = json.loads((tmp_path / "unified_report.json").read_text(encoding="utf-8"))
        assert report["as_of_date"] == "2026-07-02"
        assert report["score_as_of_date"] == "2026-07-01"
        assert report["bridge_summary"]["score_as_of_date"] == "2026-07-01"
        markdown = (tmp_path / "unified_report.md").read_text(encoding="utf-8")
        assert "2026-07-01" in markdown

    def test_pipeline_maps_short_term_burst_score_to_stock_burst_score(self, tmp_path):
        """Stocks should inherit short_term_burst_score when bridge sectors do not expose burst_score."""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up

        mock_client = MagicMock()
        mock_client.health_check.side_effect = ConnectionError("api down")
        fake_bridge_result = {
            "status": "ok",
            "as_of_date": "2026-07-07",
            "trend_sectors": [
                {
                    "sector_name": "工程机械",
                    "trend_score": 47.25,
                    "short_term_burst_score": 63.1,
                    "high_relevance_count": 1,
                    "total_constituents": 1,
                    "stocks": [
                        {"code": "601038", "name": "一拖股份", "change_pct": 2.0, "total_mv": 200, "pe": 20, "relevance_score": 0.8}
                    ],
                }
            ],
            "burst_sectors": [],
            "cross_sectors": [],
            "constituent_source_summary": {"http_mapping": 1},
            "sector_input_source": "test",
            "api_status": {"mock": "down"},
        }

        validated_score = (
            "2026-07-07",
            tmp_path / "sector_scores.json",
            {
                "as_of_date": "2026-07-07",
                "scores": [
                    {
                        "sector_name": "工程机械",
                        "sector_type": "industry",
                        "trend_continuation_score": 47.25,
                        "short_term_burst_score": 63.1,
                    }
                ],
            },
        )
        with patch.object(
            up,
            "validate_explicit_score_report",
            return_value=(True, validated_score, None),
        ):
            with patch.object(up, "run_bridge", return_value=fake_bridge_result), patch.object(
                up, "_get_http_client", return_value=mock_client
            ):
                result = up.run_pipeline(
                    as_of_date="2026-07-07",
                    mode="quick",
                    output_dir=str(tmp_path),
                )

        assert result["trend_candidates_all"][0]["sector_burst_score"] == 63.1

    def test_markdown_report_has_data_source_section(
        self, tmp_path, isolated_bridge_reports, offline_bridge_io
    ):
        """Markdown report should contain '数据来源状态' section."""
        from unittest.mock import MagicMock, patch
        import unified_pipeline as up
        import sector_stock_bridge as bridge

        mock_client = MagicMock()
        mock_client.get_board_constituents.return_value = [
            {"code": "600030", "name": "中信证券", "market_cap": 300e9, "source": "mapping"},
        ]
        mock_bars = [
            {"date": f"2026-06-{d:02d}", "open": 20, "high": 21, "low": 19, "close": 21, "amount": 3e8}
            for d in range(15, 30)
        ]
        mock_client.get_stock_bars.return_value = mock_bars

        with patch.object(bridge, "_get_http_client", return_value=mock_client):
            with patch.object(up, "_get_http_client", return_value=mock_client):
                with patch.object(bridge, "_load_cache", return_value=None):
                    with patch.object(bridge, "_save_cache"):
                        result = up.run_pipeline(
                            as_of_date="2026-07-01",
                            mode="quick",
                            output_dir=str(tmp_path / "unified"),
                        )

                        bridge_result = result.get("bridge_result")
                        assert isinstance(bridge_result, dict)

                        # Generate markdown directly
                        md = up.generate_markdown_report(
                            as_of_date="2026-07-01",
                            trend_stocks=result.get("trend_top_stocks", []),
                            burst_stocks=result.get("burst_top_stocks", []),
                            bridge_result=bridge_result,
                        )
                        assert "数据来源状态" in md
                        assert "http_mapping" in md

    def test_run_log_json_structure(self):
        """Verify run_log JSON can include source tracking fields."""
        import json
        run_log = {
            "command_args": "--daily --as-of 2026-07-02",
            "started_at": "2026-07-04T10:00:00",
            "finished_at": "2026-07-04T10:00:30",
            "duration_ms": 30000,
            "provider": "fixture",
            "status": "ok",
            "comparison_status": "none",
            "cache_fallback_used": False,
            "warnings": [],
            "output_files": [],
            # Phase 5 new fields
            "market_data_service_reachable": True,
            "stockdb_available": True,
            "constituent_source_summary": {
                "http_em": 0,
                "http_stale": 0,
                "http_mapping": 10,
                "local_emergency_mapping": 0,
                "unavailable": 0,
            },
            "quant_score_source_summary": {
                "http_enhanced": 41,
                "fallback": 0,
            },
        }
        assert run_log["market_data_service_reachable"] is True
        assert run_log["stockdb_available"] is True
        assert run_log["constituent_source_summary"]["http_mapping"] == 10
        assert run_log["quant_score_source_summary"]["http_enhanced"] == 41
        # Verify JSON serializable
        dumped = json.dumps(run_log, ensure_ascii=False)
        assert "constituent_source_summary" in dumped


# ============================================================
# 测试：运行健康门禁（Phase 6）
# ============================================================


class TestRunHealthGate:
    """Test evaluate_run_health pass/warn/fail logic."""

    def test_pass_all_healthy(self):
        """All sources healthy → PASS (mapping < 50%)."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 6, "http_stale": 0, "http_mapping": 4,
                "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "pass"
        assert len(result["reasons"]) > 0

    def test_pass_with_http_em(self):
        """Having http_em with mapping < 50% → PASS."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 6, "http_stale": 0, "http_mapping": 4,
                "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "pass"

    def test_warn_all_http_mapping_no_em(self):
        """All http_mapping with no EM → WARN (offline mapping dependency)."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_mapping": 10,
                "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "warn"
        assert any("离线映射" in r for r in result["reasons"])

    def test_warn_some_unavailable(self):
        """Few unavailable (< 30%) → WARN."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_mapping": 8,
                "local_emergency_mapping": 0, "unavailable": 2,
            },
            "quant_score_sources": {"http_enhanced": 35},
            "has_unavailable_sectors": True,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "warn"
        assert any("unavailable" in r for r in result["reasons"])

    def test_warn_some_emergency(self):
        """Few emergency fallback (< 50%) → WARN."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_mapping": 5,
                "local_emergency_mapping": 3, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 35},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": True,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "warn"
        assert any("emergency" in r for r in result["reasons"])

    def test_warn_some_fallback_quant(self):
        """Some fallback quant (< 50%) → WARN."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 5, "http_stale": 0, "http_mapping": 5,
                "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 30, "fallback": 10},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "warn"
        assert any("fallback" in r for r in result["reasons"])

    def test_fail_unavailable_over_threshold(self):
        """Unavailable >= 30% → FAIL."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_mapping": 3,
                "local_emergency_mapping": 0, "unavailable": 3,
            },
            "quant_score_sources": {"http_enhanced": 20},
            "has_unavailable_sectors": True,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "fail"
        assert any("unavailable" in r for r in result["reasons"])

    def test_fail_emergency_over_threshold(self):
        """Emergency fallback >= 50% → FAIL."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_mapping": 2,
                "local_emergency_mapping": 5, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 20},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": True,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "fail"
        assert any("emergency" in r for r in result["reasons"])

    def test_fail_fallback_quant_over_threshold(self):
        """Fallback quant >= 50% → FAIL."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_mapping": 10,
                "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 10, "fallback": 20},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        assert result["status"] == "fail"
        assert any("fallback" in r for r in result["reasons"])

    def test_health_metrics_fields(self):
        """Health result should include all required metrics."""
        from unified_pipeline import evaluate_run_health

        ds = {
            "constituent_sources": {
                "http_em": 2, "http_stale": 0, "http_mapping": 7,
                "local_emergency_mapping": 0, "unavailable": 1,
            },
            "quant_score_sources": {"http_enhanced": 38, "fallback": 2},
            "has_unavailable_sectors": True,
            "has_emergency_fallback": False,
        }
        result = evaluate_run_health(ds)
        m = result["metrics"]
        assert m["total_constituent_sectors"] == 10
        assert m["unavailable_sectors"] == 1
        assert m["emergency_fallback_sectors"] == 0
        assert m["http_enhanced_stocks"] == 38
        assert m["fallback_quant_stocks"] == 2


# ============================================================
# 测试：每日运行脚本（Phase 7）
# ============================================================


@pytest.fixture
def offline_daily_runner(tmp_path, monkeypatch):
    """Run the daily wrapper against a real, deterministic child process."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import run_daily_unified_pipeline as daily

    as_of = "2026-07-02"
    fallback_as_of = "2026-07-01"
    roots = build_sector_score_tree(tmp_path, [fallback_as_of, as_of])
    report_root = roots["sector_scores"].parent
    exact_score = roots["sector_scores"] / as_of / "sector_scores.json"
    exact_payload = json.loads(exact_score.read_text(encoding="utf-8"))
    exact_payload["scores"][0]["sector_name"] = "Exact Bound"
    write_json(exact_score, exact_payload)
    fallback_score = roots["sector_scores"] / fallback_as_of / "sector_scores.json"
    fallback_payload = json.loads(fallback_score.read_text(encoding="utf-8"))
    fallback_payload["scores"][0]["sector_name"] = "Fallback Only"
    write_json(fallback_score, fallback_payload)
    output_dir = tmp_path / "unified-output"
    index_path = tmp_path / "unified_runs_index.jsonl"
    child_script = tmp_path / "offline_unified_pipeline.py"
    child_script.write_text(
        f"""\
import os
import runpy
import socket
import sys
import urllib.request
from pathlib import Path

def deny_network(*_args, **_kwargs):
    raise AssertionError("offline child attempted network access")


socket.create_connection = deny_network
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.socket.sendto = deny_network
urllib.request.urlopen = deny_network

try:
    import requests
except ImportError:
    requests = None
if requests is not None:
    requests.api.request = deny_network
    requests.Session.request = deny_network
    requests.sessions.Session.request = deny_network

try:
    import http.client
    http.client.HTTPConnection.connect = deny_network
    http.client.HTTPSConnection.connect = deny_network
except ImportError:
    pass

sys.path.insert(0, {str(PROJECT_ROOT)!r})
import sector_stock_bridge as bridge

report_root = Path(os.environ["THEME_SECTOR_RADAR_REPORT_ROOT"]).resolve()
expected_scores = report_root / "sector_scores"
if bridge.SCORES_DIR.resolve() != expected_scores:
    raise SystemExit(21)
if bridge.STABLE_RESEARCH_DIR.resolve() != report_root / "full90" / "sector_research":
    raise SystemExit(22)
if bridge.STABLE_CONCEPT_DIR.resolve() != report_root / "full_concept" / "unified_rank":
    raise SystemExit(23)
if bridge.CACHE_DIR.resolve() != report_root / ".cache" / "sector_stocks":
    raise SystemExit(24)

def offline_constituents(sector_name, sector_type="industry", as_of=None):
    return {{
        "status": "degraded",
        "sector_name": sector_name,
        "sector_type": sector_type,
        "stocks": [{{
            "code": "600000",
            "name": "Offline Bank",
            "weight": 1.0,
        }}],
        "error": None,
        "fallback_used": False,
        "source": "unavailable",
    }}


def offline_quotes(codes):
    return {{
        code: {{
            "name": "Offline Bank",
            "change_pct": 1.0,
            "price": 10.0,
            "total_mv": 1000000000.0,
            "pe": 10.0,
            "pb": 1.0,
        }}
        for code in codes
    }}


def offline_sector_flow(_sector_name):
    return {{
        "status": "degraded",
        "net_flow": 0.0,
        "direction": "neutral",
        "error": "offline fixture",
    }}


def offline_individual_flows(codes):
    return {{
        code: {{"net_flow": 0.0, "direction": "neutral"}}
        for code in codes
    }}


bridge.fetch_sector_constituents = offline_constituents
bridge.fetch_tencent_quotes = offline_quotes
bridge.fetch_sector_fund_flow = offline_sector_flow
bridge.fetch_individual_fund_flow = offline_individual_flows

pipeline = runpy.run_path(
    str(Path({str(PROJECT_ROOT)!r}) / "unified_pipeline.py"),
    run_name="offline_unified_pipeline",
)
def offline_http_client():
    return None


pipeline["_get_http_client"] = offline_http_client
pipeline["run_pipeline"].__globals__["_get_http_client"] = pipeline["_get_http_client"]
pipeline["main"]()
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(daily, "UNIFIED_PIPELINE", child_script)
    monkeypatch.setattr(daily, "_check_tcp_port", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        daily,
        "_check_http_health",
        lambda *_args, **_kwargs: (True, '{"stockdb": "offline_fixture"}'),
    )

    def run(*extra_args: str, output_dir_arg: str | None = None):
        selected_output_dir = (
            str(output_dir) if output_dir_arg is None else output_dir_arg
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_daily_unified_pipeline.py",
                "--as-of", as_of,
                "--mode", "quick",
                "--report-root", str(report_root),
                "--output-dir", selected_output_dir,
                "--index-path", str(index_path),
                *extra_args,
            ],
        )
        return daily.main()

    return {
        "run": run,
        "module": daily,
        "as_of": as_of,
        "fallback_as_of": fallback_as_of,
        "report_root": report_root,
        "output_dir": output_dir,
        "index_path": index_path,
    }


class TestDailyRunScript:
    """Test scripts/run_daily_unified_pipeline.py utilities."""

    def test_canonical_report_root_redirects_all_bridge_paths(
        self, tmp_path
    ):
        """The canonical report-root env must redirect every bridge path."""
        import subprocess

        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        report_root = (tmp_path / "reports").resolve()
        child_env = os.environ.copy()
        child_env["THEME_SECTOR_RADAR_REPORT_ROOT"] = str(report_root)
        probe = """
import json
import sector_stock_bridge as bridge

print(json.dumps({
    "scores": str(bridge.SCORES_DIR.resolve()),
    "research": str(bridge.STABLE_RESEARCH_DIR.resolve()),
    "concept": str(bridge.STABLE_CONCEPT_DIR.resolve()),
    "cache": str(bridge.CACHE_DIR.resolve()),
}))
"""

        proc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(PROJECT_ROOT),
            env=child_env,
            check=True,
        )
        paths = json.loads(proc.stdout)

        assert daily.REPORT_ROOT_ENV == "THEME_SECTOR_RADAR_REPORT_ROOT"
        assert paths == {
            "scores": str(report_root / "sector_scores"),
            "research": str(report_root / "full90" / "sector_research"),
            "concept": str(report_root / "full_concept" / "unified_rank"),
            "cache": str(report_root / ".cache" / "sector_stocks"),
        }

    def test_default_bridge_paths_without_canonical_env(self):
        """Without the canonical env, a fresh import keeps production defaults."""
        import subprocess

        child_env = os.environ.copy()
        child_env.pop("THEME_SECTOR_RADAR_REPORT_ROOT", None)
        probe = """
import json
import sector_stock_bridge as bridge

print(json.dumps({
    "scores": str(bridge.SCORES_DIR.resolve()),
    "research": str(bridge.STABLE_RESEARCH_DIR.resolve()),
    "concept": str(bridge.STABLE_CONCEPT_DIR.resolve()),
    "cache": str(bridge.CACHE_DIR.resolve()),
}))
"""

        proc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(PROJECT_ROOT),
            env=child_env,
            check=True,
        )
        paths = json.loads(proc.stdout)

        assert paths == {
            "scores": str(PROJECT_ROOT / "reports" / "sector_scores"),
            "research": str(
                PROJECT_ROOT / "reports" / "full90" / "sector_research"
            ),
            "concept": str(
                PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
            ),
            "cache": str(PROJECT_ROOT / "data_cache" / "sector_stocks"),
        }

    def test_empty_inherited_report_root_is_explicit_and_fails_closed(self):
        """An inherited empty override may not become the default report root."""
        import subprocess

        child_env = os.environ.copy()
        child_env["THEME_SECTOR_RADAR_REPORT_ROOT"] = ""
        probe = """
import sector_stock_bridge as bridge

ok, payload, error = bridge.validate_explicit_score_report("2026-07-02")
assert ok is False
assert payload is None
assert error
"""
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(PROJECT_ROOT),
            env=child_env,
        )

        assert proc.returncode == 0, proc.stderr

    def test_run_unified_pipeline_without_report_root_does_not_inject_env(self):
        """The default child process must inherit its environment untouched."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        with patch.object(daily.subprocess, "run") as run:
            daily._run_unified_pipeline(
                as_of="2026-07-02",
                mode="quick",
                output_dir=None,
                report_root=None,
            )

        assert "env" not in run.call_args.kwargs

    def test_run_unified_pipeline_passes_sector_history_root_to_child(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        with patch.object(daily.subprocess, "run") as run:
            daily._run_unified_pipeline(
                as_of="2026-07-02",
                mode="quick",
                sector_history_root="data_cache/sector_history",
            )

        command = run.call_args.args[0]
        assert command[-2:] == [
            "--sector-history-root",
            "data_cache/sector_history",
        ]

    def test_run_unified_pipeline_passes_sector_cluster_map_to_child(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        with patch.object(daily.subprocess, "run") as run:
            daily._run_unified_pipeline(
                as_of="2026-07-02",
                mode="quick",
                sector_cluster_map="config/path_a_sector_clusters.json",
            )

        assert run.call_args.args[0][-2:] == [
            "--sector-cluster-map",
            "config/path_a_sector_clusters.json",
        ]

    def test_default_child_consumes_parent_bound_score_payload_without_report_root(
        self,
        tmp_path,
        monkeypatch,
    ):
        """A real default child consumes stdin without changing its report/cache roots."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        empty_scores = tmp_path / "empty-sector-scores"
        empty_scores.mkdir()
        child_script = tmp_path / "bound_payload_probe.py"
        child_script.write_text(
            f"""\
import json
import os
import sys
from pathlib import Path

if {daily.REPORT_ROOT_ENV!r} in os.environ:
    raise SystemExit(20)

sys.path.insert(0, {str(PROJECT_ROOT)!r})
import sector_stock_bridge as bridge
bridge.SCORES_DIR = Path({str(empty_scores)!r})
ok, validated, error = bridge.validate_explicit_score_report("2026-07-02")
if not ok:
    raise SystemExit(error or "missing parent-bound payload")
print(json.dumps(validated[2]))
""",
            encoding="utf-8",
        )
        payload = {
            "as_of_date": "2026-07-02",
            "scores": [
                {
                    "sector_name": "Parent Bound",
                    "sector_type": "industry",
                    "trend_continuation_score": 1.0,
                    "short_term_burst_score": 2.0,
                }
            ],
        }
        monkeypatch.setattr(daily, "UNIFIED_PIPELINE", child_script)

        proc = daily._run_unified_pipeline(
            as_of="2026-07-02",
            mode="quick",
            report_root=None,
            score_payload=payload,
            score_payload_as_of="2026-07-02",
        )

        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["scores"][0]["sector_name"] == "Parent Bound"

    def test_run_unified_pipeline_passes_parent_validated_score_payload(self):
        """The child must consume the exact payload authorized by parent preflight."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        payload = {
            "as_of_date": "2026-07-02",
            "scores": [
                {
                    "sector_name": "证券",
                    "sector_type": "industry",
                    "trend_continuation_score": 1.0,
                    "short_term_burst_score": 2.0,
                }
            ],
        }
        with patch.object(daily.subprocess, "run") as run:
            daily._run_unified_pipeline(
                as_of="2026-07-02",
                mode="quick",
                report_root=str(PROJECT_ROOT / "reports"),
                score_payload=payload,
            )

        kwargs = run.call_args.kwargs
        assert kwargs["env"][daily.SCORE_PAYLOAD_STDIN_ENV] == "1"
        assert json.loads(kwargs["input"]) == payload
        assert all(ord(ch) < 128 for ch in kwargs["input"])
        assert "\\u" in kwargs["input"]

    def test_normalize_output_dir_resolves_relative_to_parent_cwd(
        self, tmp_path, monkeypatch
    ):
        """Relative output paths use the daily wrapper caller's cwd."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        caller_cwd = tmp_path / "caller"
        caller_cwd.mkdir()
        monkeypatch.chdir(caller_cwd)

        ok, normalized = daily._normalize_output_dir("relative-output")

        assert ok is True
        assert normalized == str((caller_cwd / "relative-output").resolve())

    def test_normalize_output_dir_rejects_explicit_blank(self):
        """An explicitly blank output path must fail closed."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        ok, detail = daily._normalize_output_dir("   ")

        assert ok is False
        assert "不能为空" in detail

    def test_normalize_output_dir_rejects_existing_file(self, tmp_path):
        """An existing non-directory output path must fail closed."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        output_file = tmp_path / "not-a-directory"
        output_file.write_text("fixture", encoding="utf-8")

        ok, detail = daily._normalize_output_dir(str(output_file))

        assert ok is False
        assert "不是目录" in detail

    @pytest.mark.parametrize(
        "as_of",
        [
            "2026-7-02",
            "2026-07-2",
            "2026-02-29",
            "../2026-07-02",
            "2026-07-02 ",
        ],
    )
    def test_validate_as_of_rejects_invalid_or_non_round_trip_dates(self, as_of):
        """Daily dates must be real, zero-padded YYYY-MM-DD values."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        ok, detail = daily._validate_as_of(as_of)

        assert ok is False
        assert "YYYY-MM-DD" in detail

    def test_explicit_report_root_rejects_as_of_traversal(self, tmp_path):
        """An as_of segment must not escape the canonical sector score root."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        report_root = tmp_path / "reports"
        write_json(
            report_root / "escape" / "sector_scores.json",
            {"as_of_date": "escape"},
        )

        ok, _detail = daily._validate_report_root(str(report_root), "../escape")

        assert ok is False

    def test_explicit_report_root_rejects_symlink_escape(self, tmp_path):
        """A linked date directory may not escape the canonical score root."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        report_root = tmp_path / "reports"
        score_root = report_root / "sector_scores"
        score_root.mkdir(parents=True)
        outside_date = tmp_path / "outside-date"
        write_json(
            outside_date / "sector_scores.json",
            {"as_of_date": "2026-07-02"},
        )
        linked_date = score_root / "2026-07-02"
        _link_directory_or_skip(linked_date, outside_date)

        ok, _detail = daily._validate_report_root(str(report_root), "2026-07-02")

        assert ok is False

    def test_explicit_report_root_rejects_link_swap_before_score_open(
        self, tmp_path, monkeypatch
    ):
        """Parent preflight must bind validation to the file it actually opens."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path / "inside", [as_of])
        report_root = roots["sector_scores"].parent
        inside_date = roots["sector_scores"] / as_of
        score_path = inside_date / "sector_scores.json"
        resolved_score_path = score_path.resolve()
        outside = build_sector_score_tree(tmp_path / "outside", [as_of])
        outside_date = outside["sector_scores"] / as_of
        swapped = False
        original_read_text = Path.read_text
        original_os_open = os.open

        def swap_date_directory():
            nonlocal swapped
            if swapped:
                return
            swapped = True
            shutil.rmtree(inside_date)
            _link_directory_or_skip(inside_date, outside_date)

        def read_text_then_swap(path, *args, **kwargs):
            if path == resolved_score_path:
                swap_date_directory()
            return original_read_text(path, *args, **kwargs)

        def os_open_then_swap(path, flags, *args, **kwargs):
            if Path(path) == resolved_score_path:
                swap_date_directory()
            return original_os_open(path, flags, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", read_text_then_swap)
        monkeypatch.setattr(daily.os, "open", os_open_then_swap)

        ok, _detail = daily._validate_report_root(str(report_root), as_of)

        assert ok is False

    def test_explicit_report_root_rejects_payload_date_mismatch(self, tmp_path):
        """The exact-date path must contain a score payload for that same date."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        payload = load_sector_scores(score_path)
        payload["as_of_date"] = "2026-07-01"
        write_json(score_path, payload)

        ok, detail = daily._validate_report_root(
            str(roots["sector_scores"].parent), as_of
        )

        assert ok is False
        assert "as_of_date" in detail

    def test_explicit_report_root_rejects_invalid_score_json(self, tmp_path):
        """Malformed exact-date score JSON must fail closed in parent preflight."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        score_path.write_text("{not-json", encoding="utf-8")

        ok, detail = daily._validate_report_root(
            str(roots["sector_scores"].parent), as_of
        )

        assert ok is False
        assert "JSON" in detail

    def test_explicit_report_root_rejects_incomplete_score_payload(self, tmp_path):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        write_json(
            roots["sector_scores"] / as_of / "sector_scores.json",
            {"as_of_date": as_of},
        )

        ok, detail = daily._validate_report_root(
            str(roots["sector_scores"].parent), as_of
        )

        assert ok is False
        assert "scores" in detail

    @pytest.mark.parametrize(
        ("mutation", "expected_fragment"),
        [
            (lambda payload: payload.update(scores=[]), "scores"),
            (lambda payload: payload["scores"][0].update(sector_name=""), "sector_name"),
            (lambda payload: payload["scores"][0].update(sector_type="other"), "sector_type"),
            (
                lambda payload: payload["scores"][0].pop(
                    "trend_continuation_score"
                ),
                "trend_continuation_score",
            ),
            (
                lambda payload: payload["scores"][0].update(
                    short_term_burst_score=True
                ),
                "short_term_burst_score",
            ),
            (
                lambda payload: payload["scores"][0].update(
                    trend_continuation_score=10 ** 1000
                ),
                "trend_continuation_score",
            ),
        ],
    )
    def test_explicit_report_root_rejects_invalid_score_contract_fields(
        self, tmp_path, mutation, expected_fragment
    ):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        payload = load_sector_scores(score_path)
        mutation(payload)
        write_json(score_path, payload)

        ok, detail = daily._validate_report_root(
            str(roots["sector_scores"].parent), as_of
        )

        assert ok is False
        assert expected_fragment in detail

    def test_explicit_report_root_rejects_non_finite_score_before_network(
        self, tmp_path
    ):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        raw = score_path.read_text(encoding="utf-8")
        score_path.write_text(
            raw.replace('"trend_continuation_score": 72.0',
                        '"trend_continuation_score": Infinity', 1),
            encoding="utf-8",
        )

        ok, detail = daily._validate_report_root(
            str(roots["sector_scores"].parent), as_of
        )

        assert ok is False
        assert "non-finite" in detail

    def test_score_level_type_is_rejected_before_http_preflight(
        self, tmp_path, monkeypatch
    ):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        score_path = roots["sector_scores"] / as_of / "sector_scores.json"
        payload = load_sector_scores(score_path)
        payload["scores"][0]["trend_level"] = ["not", "text"]
        write_json(score_path, payload)
        monkeypatch.setattr(
            daily,
            "_check_tcp_port",
            lambda *_args, **_kwargs: pytest.fail("TCP preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: pytest.fail("HTTP preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child process must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_daily_unified_pipeline.py",
                "--as-of",
                as_of,
                "--report-root",
                str(roots["sector_scores"].parent),
            ],
        )

        assert daily.main() == 1

    def test_check_tcp_port_localhost(self):
        """_check_tcp_port with a likely-open port should work."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_tcp_port

        with patch("socket.create_connection"):
            result = _check_tcp_port("127.0.0.1", 7899, timeout=1.0)
        assert isinstance(result, bool)

    def test_check_tcp_port_closed(self):
        """_check_tcp_port with a closed port should return False."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_tcp_port

        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            result = _check_tcp_port("127.0.0.1", 59999, timeout=0.5)
        assert result is False

    def test_check_http_health_api_url(self):
        """_check_http_health with market_data_service should return True."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_http_health

        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"stockdb": "offline_fixture"}'
        with patch("urllib.request.urlopen", return_value=response):
            ok, body = _check_http_health("http://fixture.invalid", timeout=3)
        assert ok is True
        assert "stockdb" in body

    def test_check_http_health_unreachable(self):
        """_check_http_health with unreachable URL should return False."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_http_health

        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            ok, error = _check_http_health("http://fixture.invalid", timeout=1)
        assert ok is False
        assert isinstance(error, str)

    def test_find_latest_report(self, tmp_path):
        """_find_latest_report should locate existing report."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _find_latest_report

        expected = write_json(tmp_path / "unified_report.json", {"status": "ok"})
        path = _find_latest_report("2026-07-02", output_dir=str(tmp_path))
        assert path == expected
        assert path.exists()

    def test_load_report_has_required_fields(self, tmp_path):
        """Loaded report should have run_health and data_source."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _find_latest_report, _load_report

        write_json(
            tmp_path / "unified_report.json",
            {"run_health": {"status": "warn"}, "data_source": {}},
        )
        path = _find_latest_report("2026-07-02", output_dir=str(tmp_path))
        assert path is not None
        result = _load_report(path)
        assert "run_health" in result
        assert "data_source" in result
        health = result["run_health"]
        assert "status" in health
        assert health["status"] in ("pass", "warn", "fail")

    def test_main_help_does_not_crash(self):
        """python run_daily_unified_pipeline.py --help should exit 0."""
        import subprocess, sys as _sys

        proc = subprocess.run(
            [_sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_unified_pipeline.py"), "--help"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(PROJECT_ROOT),
        )
        assert proc.returncode == 0
        assert "每日一键运行" in (proc.stdout or "")

    def test_main_api_unreachable(self, tmp_path, monkeypatch, capsys):
        """API unreachable → exit 1."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        build_sector_score_tree(tmp_path, ["2026-07-02"])
        monkeypatch.setattr(daily, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(daily, "_check_tcp_port", lambda *_args, **_kwargs: False)
        monkeypatch.setattr(
            daily, "_check_http_health", lambda *_args, **_kwargs: (False, "offline")
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["run_daily_unified_pipeline.py", "--as-of", "2026-07-02"],
        )
        assert daily.main() == 1
        output = capsys.readouterr().out
        assert "API 未启动" in output or "无法访问" in output

    def test_main_invalid_as_of_fails_before_preflight(self, monkeypatch, capsys):
        """An invalid calendar date is rejected entirely in the parent."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        monkeypatch.setattr(
            daily,
            "_check_tcp_port",
            lambda *_args, **_kwargs: pytest.fail("preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["run_daily_unified_pipeline.py", "--as-of", "2026-02-29"],
        )

        assert daily.main() == 1
        assert "YYYY-MM-DD" in capsys.readouterr().out

    def test_main_blank_output_dir_fails_before_preflight(self, monkeypatch, capsys):
        """An explicitly blank output path is rejected entirely in the parent."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        monkeypatch.setattr(
            daily,
            "_check_tcp_port",
            lambda *_args, **_kwargs: pytest.fail("preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_daily_unified_pipeline.py",
                "--as-of", "2026-07-02",
                "--output-dir", "   ",
            ],
        )

        assert daily.main() == 1
        assert "不能为空" in capsys.readouterr().out

    def test_main_child_zero_without_report_returns_one(
        self, tmp_path, monkeypatch, capsys
    ):
        """A successful child code without its report is still a failed run."""
        import subprocess

        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        output_dir = tmp_path / "missing-output"
        build_sector_score_tree(tmp_path, ["2026-07-02"])
        monkeypatch.setattr(daily, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(daily, "_check_tcp_port", lambda *_args, **_kwargs: False)
        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: (True, '{"status": "offline_fixture"}'),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
        )
        monkeypatch.setattr(
            daily,
            "_load_report",
            lambda *_args, **_kwargs: pytest.fail("missing report must not load"),
        )
        monkeypatch.setattr(
            daily,
            "_append_index",
            lambda *_args, **_kwargs: pytest.fail("missing report must not index"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_daily_unified_pipeline.py",
                "--as-of", "2026-07-02",
                "--output-dir", str(output_dir),
                "--fail-on-health-fail",
                "--index-path", str(tmp_path / "must-not-exist.jsonl"),
            ],
        )

        assert daily.main() == 1
        assert "未生成预期报告" in capsys.readouterr().out
        assert not (tmp_path / "must-not-exist.jsonl").exists()

    def test_main_api_ok_runs_pipeline(self, offline_daily_runner, capsys):
        """API reachable → should run pipeline and exit 0 (integration test)."""
        assert offline_daily_runner["run"]() == 0
        report_path = offline_daily_runner["output_dir"] / "unified_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["report_type"] == "unified_pipeline"
        assert report["as_of_date"] == offline_daily_runner["as_of"]
        assert report["mode"] == "quick"
        assert report["data_source"]["market_data_service_reachable"] is False
        assert report["data_source"]["api_fast_path"] == "api_unavailable_fast_path"
        assert "健康门禁" in capsys.readouterr().out

    def test_relative_output_dir_uses_parent_cwd_and_absolute_index_path(
        self, tmp_path, offline_daily_runner, monkeypatch
    ):
        """Child output and index report paths share the parent's absolute path."""
        caller_cwd = tmp_path / "caller"
        caller_cwd.mkdir()
        monkeypatch.chdir(caller_cwd)
        relative_output = "relative-unified"
        expected_output = (caller_cwd / relative_output).resolve()

        assert offline_daily_runner["run"](
            output_dir_arg=relative_output
        ) == 0

        report_path = expected_output / "unified_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["trend_candidates_all"]
        index_entry = json.loads(
            offline_daily_runner["index_path"].read_text(encoding="utf-8").strip()
        )
        assert index_entry["report_path"] == str(report_path)
        assert Path(index_entry["report_path"]).is_absolute()

    def test_main_fail_on_health_fail_flag(self, offline_daily_runner, capsys):
        """--fail-on-health-fail flag integration test."""
        assert offline_daily_runner["run"]("--fail-on-health-fail") == 2
        assert "健康门禁" in capsys.readouterr().out

    def test_child_uses_parent_payload_after_exact_score_is_removed(
        self, offline_daily_runner, monkeypatch
    ):
        """The child must use the bound payload instead of an older score file."""
        daily = offline_daily_runner["module"]
        exact_score = (
            offline_daily_runner["report_root"]
            / "sector_scores"
            / offline_daily_runner["as_of"]
            / "sector_scores.json"
        )
        fallback_score = (
            offline_daily_runner["report_root"]
            / "sector_scores"
            / offline_daily_runner["fallback_as_of"]
            / "sector_scores.json"
        )

        def remove_exact_after_parent_validation(*_args, **_kwargs):
            exact_score.unlink()
            return True, '{"status": "offline_fixture"}'

        monkeypatch.setattr(
            daily, "_check_http_health", remove_exact_after_parent_validation
        )

        assert offline_daily_runner["run"]("--no-append-index") == 0
        assert not exact_score.exists()
        assert fallback_score.is_file()
        report_path = offline_daily_runner["output_dir"] / "unified_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["as_of_date"] == offline_daily_runner["as_of"]
        sector_names = {
            item["name"]
            for group in ("trend_sectors", "burst_sectors")
            for item in report["bridge_summary"][group]
        }
        assert "Exact Bound" in sector_names
        assert "Fallback Only" not in sector_names

    def test_missing_explicit_report_root_fails_closed(self, tmp_path, monkeypatch):
        """An explicit missing root must fail before API or child-process work."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: pytest.fail("API preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child process must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_daily_unified_pipeline.py",
                "--as-of", "2026-07-02",
                "--report-root", str(tmp_path / "missing"),
            ],
        )
        assert daily.main() == 1

    def test_inherited_report_root_fails_before_preflight_network(
        self, tmp_path, monkeypatch
    ):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        monkeypatch.setenv(
            "THEME_SECTOR_RADAR_REPORT_ROOT", str(tmp_path / "missing-inherited")
        )
        monkeypatch.setattr(
            daily,
            "_check_tcp_port",
            lambda *_args, **_kwargs: pytest.fail("TCP preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: pytest.fail("HTTP preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child process must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["run_daily_unified_pipeline.py", "--as-of", "2026-07-02"],
        )

        assert daily.main() == 1

    def test_default_report_root_fails_before_preflight_network(
        self, tmp_path, monkeypatch
    ):
        """The default report root must validate its exact score before TCP or HTTP."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        score_path = tmp_path / "reports" / "sector_scores" / as_of / "sector_scores.json"
        score_path.parent.mkdir(parents=True)
        score_path.write_text('{"as_of_date":', encoding="utf-8")
        monkeypatch.delenv("THEME_SECTOR_RADAR_REPORT_ROOT", raising=False)
        monkeypatch.setattr(daily, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(
            daily,
            "_check_tcp_port",
            lambda *_args, **_kwargs: pytest.fail("TCP preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: pytest.fail("HTTP preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child process must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["run_daily_unified_pipeline.py", "--as-of", as_of],
        )

        assert daily.main() == 1

    def test_default_report_root_preserves_valid_historical_fallback(
        self, tmp_path, monkeypatch, capsys
    ):
        """A missing exact date may use the latest prior valid score on the default root."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        build_sector_score_tree(tmp_path, ["2026-07-01"])
        monkeypatch.delenv("THEME_SECTOR_RADAR_REPORT_ROOT", raising=False)
        monkeypatch.setattr(daily, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(daily, "_check_tcp_port", lambda *_args, **_kwargs: False)
        health_calls = []

        def offline_health(api_url, *_args, **_kwargs):
            health_calls.append(api_url)
            return False, "offline"

        monkeypatch.setattr(daily, "_check_http_health", offline_health)
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child must not run when health is down"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["run_daily_unified_pipeline.py", "--as-of", "2026-07-02"],
        )

        assert daily.main() == 1
        assert health_calls == ["http://127.0.0.1:8000"]
        assert "API" in capsys.readouterr().out

    def test_bridge_default_fallback_never_reads_after_as_of(self, tmp_path, monkeypatch):
        """The child fallback must not select a report newer than the research date."""
        import sector_stock_bridge as bridge

        roots = build_sector_score_tree(tmp_path, ["2026-07-04", "2026-07-10"])
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", None)
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])

        actual_date, report_path = bridge.find_latest_report("2026-07-05")

        assert actual_date == "2026-07-04"
        assert report_path == roots["sector_scores"] / "2026-07-04" / "sector_scores.json"

    def test_bridge_default_fallback_skips_corrupt_newest_prior_report(
        self, tmp_path, monkeypatch
    ):
        """Direct bridge validation selects the newest valid prior score payload."""
        import sector_stock_bridge as bridge

        roots = build_sector_score_tree(tmp_path, ["2026-07-01", "2026-07-02"])
        corrupt = roots["sector_scores"] / "2026-07-02" / "sector_scores.json"
        corrupt.write_text("{", encoding="utf-8")
        monkeypatch.setattr(bridge, "_REPORT_ROOT_OVERRIDE", None)
        monkeypatch.setattr(bridge, "SCORES_DIR", roots["sector_scores"])

        ok, validated, error = bridge.validate_explicit_score_report("2026-07-03")

        assert ok is True, error
        assert validated is not None
        assert validated[0] == "2026-07-01"
        assert validated[2]["as_of_date"] == "2026-07-01"

    def test_default_fallback_passes_parent_bound_payload_and_actual_date(
        self, tmp_path, monkeypatch
    ):
        """The wrapper binds fallback bytes without turning the default root into an override."""
        import subprocess

        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        roots = build_sector_score_tree(tmp_path, ["2026-07-04", "2026-07-10"])
        monkeypatch.delenv("THEME_SECTOR_RADAR_REPORT_ROOT", raising=False)
        monkeypatch.setattr(daily, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(daily, "_check_tcp_port", lambda *_args, **_kwargs: False)
        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: (True, "offline"),
        )
        captured = {}

        def fake_run(**kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess([], 9, "", "")

        monkeypatch.setattr(daily, "_run_unified_pipeline", fake_run)
        monkeypatch.setattr(
            sys,
            "argv",
            ["run_daily_unified_pipeline.py", "--as-of", "2026-07-05"],
        )

        assert daily.main() == 9
        assert captured["report_root"] is None
        assert captured["score_payload"]["as_of_date"] == "2026-07-04"
        assert captured["score_payload_as_of"] == "2026-07-04"

    def test_default_fallback_skips_corrupt_newest_prior_report(self, tmp_path):
        """Fallback selects the newest valid history, not merely the newest file."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        roots = build_sector_score_tree(tmp_path, ["2026-07-01", "2026-07-02"])
        corrupt = roots["sector_scores"] / "2026-07-02" / "sector_scores.json"
        corrupt.write_text("{", encoding="utf-8")

        ok, _detail, payload, fallback_date = daily._load_validated_default_report_root(
            str(roots["sector_scores"].parent),
            "2026-07-03",
        )

        assert ok is True
        assert fallback_date == "2026-07-01"
        assert payload["as_of_date"] == "2026-07-01"

    def test_empty_explicit_report_root_fails_closed(self, tmp_path, monkeypatch):
        """An explicit empty root must not resolve to a populated working directory."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        as_of = "2026-07-02"
        roots = build_sector_score_tree(tmp_path, [as_of])
        monkeypatch.chdir(roots["sector_scores"].parent)
        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: pytest.fail("API preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child process must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_daily_unified_pipeline.py",
                "--as-of", as_of,
                "--report-root", "",
            ],
        )

        assert daily.main() == 1

    def test_explicit_report_root_does_not_fallback_to_another_date(
        self, tmp_path, monkeypatch
    ):
        """A populated root without the exact date must not use its latest report."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import run_daily_unified_pipeline as daily

        roots = build_sector_score_tree(tmp_path, ["2026-07-01"])
        report_root = roots["sector_scores"].parent
        monkeypatch.setattr(
            daily,
            "_check_http_health",
            lambda *_args, **_kwargs: pytest.fail("API preflight must not run"),
        )
        monkeypatch.setattr(
            daily,
            "_run_unified_pipeline",
            lambda *_args, **_kwargs: pytest.fail("child process must not run"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "run_daily_unified_pipeline.py",
                "--as-of", "2026-07-02",
                "--report-root", str(report_root),
            ],
        )
        assert daily.main() == 1


# ============================================================
# 测试：运行索引与归档（Phase 8）
# ============================================================


class TestRunArchive:
    """Test index append, --show-history, --no-append-index."""

    def test_build_index_entry_structure(self):
        """Index entry should have all required fields."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _build_index_entry

        result = {
            "run_health": {"status": "warn", "reasons": ["test"]},
            "data_source": {
                "constituent_sources": {"http_mapping": 10},
                "quant_score_sources": {"http_enhanced": 40},
            },
            "trend_top_stocks": [
                {"code": "600030", "name": "中信证券", "final_score": 82.5},
                {"code": "601881", "name": "中国银河", "final_score": 78.0},
            ],
            "burst_top_stocks": [
                {"code": "002422", "name": "科伦药业", "final_score": 84.5},
            ],
        }
        entry = _build_index_entry("2026-07-02", "quick", "reports/u/2026-07-02/unified_report.json", result)
        assert entry["as_of"] == "2026-07-02"
        assert entry["mode"] == "quick"
        assert entry["run_health_status"] == "warn"
        assert len(entry["trend_top_candidates"]) == 2
        assert entry["trend_top_candidates"][0]["code"] == "600030"
        assert len(entry["burst_top_candidates"]) == 1
        assert "constituent_sources" in entry
        assert "run_at" in entry

    def test_append_index_creates_file(self, tmp_path):
        """Append should create the index file."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _append_index

        idx = tmp_path / "test_index.jsonl"
        entry = {"run_at": "2026-07-04T15:00:00", "as_of": "2026-07-02", "mode": "quick"}
        _append_index(idx, entry)
        assert idx.exists()
        lines = idx.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["as_of"] == "2026-07-02"

    def test_append_index_multiple_runs_same_date(self, tmp_path):
        """Same as_of repeated runs should append, not overwrite."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _append_index

        idx = tmp_path / "test_index.jsonl"
        _append_index(idx, {"run_at": "T1", "as_of": "2026-07-02"})
        _append_index(idx, {"run_at": "T2", "as_of": "2026-07-02"})
        _append_index(idx, {"run_at": "T3", "as_of": "2026-07-02"})
        lines = idx.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0])["run_at"] == "T1"
        assert json.loads(lines[2])["run_at"] == "T3"

    def test_append_index_write_failure_no_crash(self, tmp_path, monkeypatch):
        """Write failure should print warning but NOT crash."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _append_index

        # Make open() fail by using a path that can't be written
        import builtins
        original_open = builtins.open

        def _failing_open(path, mode, *a, **kw):
            if "jsonl" in str(path) and "a" in mode:
                raise OSError("disk full")
            return original_open(path, mode, *a, **kw)

        monkeypatch.setattr(builtins, "open", _failing_open)
        idx = tmp_path / "test_index.jsonl"
        # Should not raise
        _append_index(idx, {"run_at": "T1"})

    def test_show_history_empty(self, tmp_path, capsys):
        """--show-history with no index should print placeholder."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _show_history

        idx = tmp_path / "nonexistent.jsonl"
        _show_history(idx, 5)
        captured = capsys.readouterr()
        assert "暂无历史记录" in captured.out

    def test_show_history_with_data(self, tmp_path, capsys):
        """--show-history should print a table with recent runs."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _show_history

        idx = tmp_path / "test_index.jsonl"
        for i in range(5):
            entry = json.dumps({
                "run_at": f"2026-07-0{i}T10:00",
                "as_of": f"2026-07-0{i}",
                "run_health_status": "warn",
                "trend_top_candidates": [{"code": "600030"} for _ in range(5)],
                "burst_top_candidates": [{"code": "002422"}],
                "constituent_sources": {"http_mapping": 10},
            }, ensure_ascii=False) + "\n"
            with open(idx, "a", encoding="utf-8") as f:
                f.write(entry)

        _show_history(idx, 3)
        captured = capsys.readouterr()
        assert "2026-07-04" in captured.out
        assert "2026-07-03" in captured.out
        assert "2026-07-02" in captured.out
        # New Phase 9: should show Summary block instead of raw total count line
        assert "Summary" in captured.out

    def test_no_append_index_skips_write(self, offline_daily_runner):
        """Running with --no-append-index should not write to index (integration)."""
        idx = offline_daily_runner["index_path"]
        assert offline_daily_runner["run"]("--no-append-index") == 0
        report = json.loads(
            (
                offline_daily_runner["output_dir"] / "unified_report.json"
            ).read_text(encoding="utf-8")
        )
        assert report["trend_candidates_all"]
        assert not idx.exists()

    def test_show_history_cli(self, tmp_path):
        """--show-history CLI should exit 0."""
        import subprocess, sys as _sys

        idx = tmp_path / "test_index.jsonl"
        # Write one entry
        idx.write_text(json.dumps({"as_of": "2026-07-02", "run_health_status": "warn",
                                    "trend_top_candidates": [], "burst_top_candidates": [],
                                    "constituent_sources": {}}, ensure_ascii=False) + "\n", encoding="utf-8")

        proc = subprocess.run(
            [_sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_unified_pipeline.py"),
             "--show-history", "5", "--index-path", str(idx)],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(PROJECT_ROOT),
        )
        assert proc.returncode == 0
        assert "2026-07-02" in (proc.stdout or "")


# ============================================================
# 测试：运行历史摘要与连续健康状态（Phase 9）
# ============================================================


def _make_history_entry(as_of, status, csrc=None, trend_codes=None, burst_codes=None, qsrc=None):
    """Helper to build a minimal index entry."""
    return {
        "run_at": f"{as_of}T10:00:00",
        "as_of": as_of,
        "run_health_status": status,
        "constituent_sources": csrc or {"http_mapping": 10},
        "quant_score_sources": qsrc or {"http_enhanced": 40},
        "trend_top_candidates": [{"code": c, "name": f"股票{c}"} for c in (trend_codes or ["600030"])],
        "burst_top_candidates": [{"code": c, "name": f"股票{c}"} for c in (burst_codes or ["002422"])],
    }


class TestLoadRunHistory:
    """Test load_run_history function."""

    def test_empty_file(self, tmp_path):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import load_run_history
        idx = tmp_path / "empty.jsonl"
        idx.write_text("", encoding="utf-8")
        assert load_run_history(idx) == []

    def test_nonexistent_file(self, tmp_path):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import load_run_history
        assert load_run_history(tmp_path / "nope.jsonl") == []

    def test_load_with_limit(self, tmp_path):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import load_run_history, _append_index

        idx = tmp_path / "index.jsonl"
        for i in range(10):
            _append_index(idx, {"as_of": f"2026-07-{i:02d}", "run_health_status": "warn"})
        records = load_run_history(idx, limit=3)
        assert len(records) == 3
        assert records[-1]["as_of"] == "2026-07-09"

    def test_corrupt_lines_skipped(self, tmp_path):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import load_run_history

        idx = tmp_path / "index.jsonl"
        idx.write_text('{"as_of": "ok"}\nnot json\n{"as_of": "also ok"}\n', encoding="utf-8")
        records = load_run_history(idx)
        assert len(records) == 2


class TestSummarizeRunHistory:
    """Test summarize_run_history function."""

    def test_empty(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history
        s = summarize_run_history([])
        assert s["total"] == 0
        assert s["latest_status"] == "unknown"

    def test_pass_warn_fail_counts(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history

        records = [
            _make_history_entry("07-01", "pass"),
            _make_history_entry("07-02", "warn"),
            _make_history_entry("07-03", "warn"),
            _make_history_entry("07-04", "fail"),
            _make_history_entry("07-05", "warn"),
        ]
        s = summarize_run_history(records)
        assert s["total"] == 5
        assert s["pass_count"] == 1
        assert s["warn_count"] == 3
        assert s["fail_count"] == 1

    def test_consecutive_warn(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history

        records = [
            _make_history_entry("07-01", "pass"),
            _make_history_entry("07-02", "warn"),
            _make_history_entry("07-03", "warn"),
            _make_history_entry("07-04", "warn"),
            _make_history_entry("07-05", "warn"),
        ]
        s = summarize_run_history(records)
        assert s["consecutive_warn_count"] == 4
        assert s["consecutive_fail_count"] == 0
        assert s["latest_status"] == "warn"

    def test_consecutive_fail(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history

        records = [
            _make_history_entry("07-01", "warn"),
            _make_history_entry("07-02", "fail"),
            _make_history_entry("07-03", "fail"),
        ]
        s = summarize_run_history(records)
        assert s["consecutive_fail_count"] == 2
        assert s["latest_status"] == "fail"

    def test_all_http_mapping_detection(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history

        # All runs have only http_mapping
        records = [
            _make_history_entry("07-01", "warn", csrc={"http_em": 0, "http_stale": 0, "http_mapping": 10}),
            _make_history_entry("07-02", "warn", csrc={"http_em": 0, "http_stale": 0, "http_mapping": 10}),
        ]
        s = summarize_run_history(records)
        assert s["all_http_mapping"] is True

    def test_not_all_http_mapping_when_em_present(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history

        records = [
            _make_history_entry("07-01", "warn", csrc={"http_em": 0, "http_stale": 0, "http_mapping": 10}),
            _make_history_entry("07-02", "pass", csrc={"http_em": 5, "http_stale": 0, "http_mapping": 5}),
        ]
        s = summarize_run_history(records)
        assert s["all_http_mapping"] is False

    def test_repeated_stocks(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history

        # 600030 appears in 3 runs, 601881 in 2 runs
        records = [
            _make_history_entry("07-01", "warn", trend_codes=["600030", "601881"]),
            _make_history_entry("07-02", "warn", trend_codes=["600030", "601881", "600999"]),
            _make_history_entry("07-03", "warn", trend_codes=["600030", "601688"]),
        ]
        s = summarize_run_history(records)
        rt = s["repeated_trend_stocks"]
        assert len(rt) >= 1
        # 600030 should be top repeated (3 times)
        codes = [c for c, n, cnt in rt]
        assert "600030" in codes

    def test_merged_sources(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history

        records = [
            _make_history_entry("07-01", "warn", csrc={"http_mapping": 10}, qsrc={"http_enhanced": 40}),
            _make_history_entry("07-02", "warn", csrc={"http_mapping": 10}, qsrc={"http_enhanced": 40}),
        ]
        s = summarize_run_history(records)
        assert s["merged_constituent_sources"]["http_mapping"] == 20
        assert s["merged_quant_sources"]["http_enhanced"] == 80


class TestHistorySummaryOutput:
    """Test _print_history_summary output."""

    def test_summary_contains_health_distribution(self, capsys):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history, _print_history_summary

        records = [
            _make_history_entry("07-01", "pass"),
            _make_history_entry("07-02", "warn"),
            _make_history_entry("07-03", "warn"),
        ]
        s = summarize_run_history(records)
        _print_history_summary(records, s)
        out = capsys.readouterr().out
        assert "PASS=1" in out
        assert "WARN=2" in out

    def test_summary_warns_consecutive(self, capsys):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history, _print_history_summary

        records = [_make_history_entry(f"07-0{i}", "warn") for i in range(1, 5)]
        s = summarize_run_history(records)
        _print_history_summary(records, s)
        out = capsys.readouterr().out
        assert "连续 WARN 4 次" in out

    def test_summary_warns_all_mapping(self, capsys):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import summarize_run_history, _print_history_summary

        records = [
            _make_history_entry("07-01", "warn", csrc={"http_em": 0, "http_mapping": 10}),
        ]
        s = summarize_run_history(records)
        _print_history_summary(records, s)
        out = capsys.readouterr().out
        assert "离线映射" in out

    def test_show_history_integration(self, tmp_path):
        """End-to-end: write JSONL, run --show-history, check output."""
        import subprocess, sys as _sys

        idx = tmp_path / "index.jsonl"
        # Write 5 history entries
        for i in range(1, 6):
            entry = json.dumps({
                "run_at": f"2026-07-0{i}T10:00",
                "as_of": f"2026-07-0{i}",
                "run_health_status": "warn" if i < 5 else "pass",
                "constituent_sources": {"http_mapping": 10},
                "quant_score_sources": {"http_enhanced": 40},
                "trend_top_candidates": [{"code": "600030", "name": "中信证券"}],
                "burst_top_candidates": [{"code": "002422", "name": "科伦药业"}],
            }, ensure_ascii=False) + "\n"
            with open(idx, "a", encoding="utf-8") as f:
                f.write(entry)

        proc = subprocess.run(
            [_sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_unified_pipeline.py"),
             "--show-history", "10", "--index-path", str(idx)],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(PROJECT_ROOT), timeout=30,
        )
        assert proc.returncode == 0
        stdout = proc.stdout or ""
        assert "Summary" in stdout
        assert "PASS=1" in stdout
        assert "WARN=4" in stdout
        assert "连续依赖离线映射" in stdout or "离线映射" in stdout


# ============================================================
# 测试：Phase 11 健康门禁升级 — http_local_industry
# ============================================================


class TestHealthGateLocalIndustry:
    """Test evaluate_run_health with http_local_industry source."""

    def test_all_local_industry_pass(self):
        """All http_local_industry with no mapping → PASS."""
        from unified_pipeline import evaluate_run_health
        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_local_industry": 10,
                "http_mapping": 0, "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        r = evaluate_run_health(ds)
        assert r["status"] == "pass"

    def test_all_mapping_warn(self):
        """All http_mapping with no local_industry → WARN (legacy behavior)."""
        from unified_pipeline import evaluate_run_health
        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_local_industry": 0,
                "http_mapping": 10, "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        r = evaluate_run_health(ds)
        assert r["status"] == "warn"
        assert any("离线映射" in reason or "mapping" in reason for reason in r["reasons"])

    def test_mixed_mapping_below_50_percent_pass(self):
        """http_mapping < 50% with local_industry majority → PASS."""
        from unified_pipeline import evaluate_run_health
        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_local_industry": 7,
                "http_mapping": 3, "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        r = evaluate_run_health(ds)
        assert r["status"] == "pass"

    def test_mixed_mapping_above_50_percent_warn(self):
        """http_mapping >= 50% → WARN."""
        from unified_pipeline import evaluate_run_health
        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_local_industry": 4,
                "http_mapping": 6, "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        r = evaluate_run_health(ds)
        assert r["status"] == "warn"
        assert any("离线映射占比" in reason for reason in r["reasons"])

    def test_local_industry_with_em_pass(self):
        """http_em + http_local_industry mixed → PASS."""
        from unified_pipeline import evaluate_run_health
        ds = {
            "constituent_sources": {
                "http_em": 3, "http_stale": 0, "http_local_industry": 7,
                "http_mapping": 0, "local_emergency_mapping": 0, "unavailable": 0,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": False,
            "has_emergency_fallback": False,
        }
        r = evaluate_run_health(ds)
        assert r["status"] == "pass"

    def test_local_industry_with_small_unavailable_warn(self):
        """local_industry + some unavailable (<30%) → WARN."""
        from unified_pipeline import evaluate_run_health
        ds = {
            "constituent_sources": {
                "http_em": 0, "http_stale": 0, "http_local_industry": 8,
                "http_mapping": 0, "local_emergency_mapping": 0, "unavailable": 2,
            },
            "quant_score_sources": {"http_enhanced": 40},
            "has_unavailable_sectors": True,
            "has_emergency_fallback": False,
        }
        r = evaluate_run_health(ds)
        assert r["status"] == "warn"

    def test_show_history_short_label_local_industry(self, tmp_path, capsys):
        """--show-history should display 'local_ind' short label for local_industry."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _show_history

        idx = tmp_path / "index.jsonl"
        entry = json.dumps({
            "run_at": "2026-07-04T10:00",
            "as_of": "2026-07-04",
            "run_health_status": "pass",
            "trend_top_candidates": [{"code": "600030"}],
            "burst_top_candidates": [{"code": "002422"}],
            "constituent_sources": {"http_local_industry": 10},
            "quant_score_sources": {"http_enhanced": 44},
        }, ensure_ascii=False) + "\n"
        idx.write_text(entry, encoding="utf-8")

        _show_history(idx, 5)
        out = capsys.readouterr().out
        assert "local_ind=10" in out


# ============================================================
# 测试：数据质量面板（Phase 19）
# ============================================================


class TestDataQualityPanel:
    """Test build_data_quality_summary function."""

    def test_all_real_sources_pass(self):
        from unified_pipeline import build_data_quality_summary

        ds = {
            "constituent_sources": {"http_local_industry": 10},
            "quant_score_sources": {"http_enhanced+ff_batch": 40},
            "stock_info_sources": {"ok": 38, "filtered_st": 2, "unknown": 0},
            "fund_flow_source": "fund_flow_ths_batch",
        }
        rh = {"status": "pass"}
        dq = build_data_quality_summary(ds, rh)
        assert dq["status"] == "pass"
        assert dq["summary"]["constituents"]["status"] == "pass"
        assert dq["summary"]["quant_scores"]["status"] == "pass"
        assert dq["summary"]["stock_info"]["status"] == "pass"
        assert len(dq["warnings"]) == 0

    def test_constituents_mapping_warn(self):
        from unified_pipeline import build_data_quality_summary

        ds = {
            "constituent_sources": {"http_mapping": 10},
            "quant_score_sources": {"http_enhanced": 40},
            "stock_info_sources": {"ok": 40, "unknown": 0},
            "fund_flow_source": "fund_flow_neutral",
        }
        dq = build_data_quality_summary(ds)
        assert dq["summary"]["constituents"]["status"] == "warn"
        assert dq["coverage"]["constituents_real_ratio"] == 0.0

    def test_fund_flow_neutral_warn(self):
        from unified_pipeline import build_data_quality_summary

        ds = {
            "constituent_sources": {"http_local_industry": 10},
            "quant_score_sources": {"http_enhanced": 40},
            "stock_info_sources": {"ok": 40, "unknown": 0},
            "fund_flow_source": "fund_flow_neutral",
        }
        dq = build_data_quality_summary(ds)
        assert dq["summary"]["fund_flow"]["status"] == "warn"
        assert "资金流数据全部 neutral" in " ".join(dq["warnings"])

    def test_stock_info_unknown_warn(self):
        from unified_pipeline import build_data_quality_summary

        ds = {
            "constituent_sources": {"http_local_industry": 10},
            "quant_score_sources": {"http_enhanced": 40},
            "stock_info_sources": {"ok": 20, "unknown": 20, "filtered_st": 0},
            "fund_flow_source": "fund_flow_ths_batch",
        }
        dq = build_data_quality_summary(ds)
        assert dq["summary"]["stock_info"]["status"] == "warn"
        assert dq["coverage"]["stock_info_known_ratio"] == pytest.approx(0.5)

    def test_empty_source_no_crash(self):
        from unified_pipeline import build_data_quality_summary

        ds = {"constituent_sources": {}, "quant_score_sources": {},
              "stock_info_sources": {}, "fund_flow_source": "fund_flow_neutral"}
        dq = build_data_quality_summary(ds)
        assert dq["status"] == "unknown"
        assert "coverage" in dq

    def test_coverage_ratios_range(self):
        from unified_pipeline import build_data_quality_summary

        ds = {
            "constituent_sources": {"http_local_industry": 7, "http_mapping": 3},
            "quant_score_sources": {"http_enhanced+ff_batch": 35, "fallback": 5},
            "stock_info_sources": {"ok": 38, "unknown": 2, "filtered_st": 0},
            "fund_flow_source": "fund_flow_ths_batch",
        }
        dq = build_data_quality_summary(ds)
        c = dq["coverage"]
        assert 0 <= c["constituents_real_ratio"] <= 1
        assert 0 <= c["quant_http_ratio"] <= 1
        assert 0 <= c["stock_info_known_ratio"] <= 1
        assert 0 <= c["fund_flow_available_ratio"] <= 1


# ============================================================
# 测试：评分拆解（Phase 20）
# ============================================================


class TestScoreBreakdown:
    """Test build_score_breakdown function."""

    def test_full_fields(self):
        from unified_pipeline import build_score_breakdown

        stock = {"quant_score": 82.0, "relevance_score": 0.833, "final_score": 82.5,
                 "quant_source": "http_enhanced_v2+ff_batch",
                 "sector_trend_score": 70, "sector_burst_score": 60,
                 "sector_momentum_component": 13.0,
                 "data_quality_score": 85.0, "factor_coverage": 0.8}
        bd = build_score_breakdown(stock)
        assert bd["final_score"] == 82.5
        assert bd["quant_score_component"] == pytest.approx(41.0, abs=0.1)   # 82.0 * 0.5
        assert bd["relevance_score_component"] == pytest.approx(24.99, abs=0.1)  # 0.833 * 30
        assert bd["data_quality_score"] == 85.0
        assert "formula" in bd

    def test_missing_fields_no_crash(self):
        from unified_pipeline import build_score_breakdown

        bd = build_score_breakdown({})
        assert bd["final_score"] == 0.0
        assert bd["quant_score_component"] == 0.0
        assert bd["data_quality_score"] == 0.0

    def test_final_score_unchanged(self):
        from unified_pipeline import build_score_breakdown

        stock = {"final_score": 82.5, "quant_score": 82.0, "relevance_score": 0.833}
        bd = build_score_breakdown(stock)
        assert bd["final_score"] == stock["final_score"]

    def test_no_fund_flow(self):
        from unified_pipeline import build_score_breakdown

        stock = {"quant_score": 60.0, "relevance_score": 0.7, "final_score": 64.0,
                 "quant_source": "http_enhanced_v2"}
        bd = build_score_breakdown(stock)
        assert bd["final_score"] == 64.0

    def test_annotate_adds_breakdown(self):
        from unified_pipeline import _annotate_score_breakdown

        stocks = [{"final_score": 80.0, "quant_score": 80.0, "relevance_score": 0.8}]
        _annotate_score_breakdown(stocks)
        assert "score_breakdown" in stocks[0]
        assert stocks[0]["score_breakdown"]["final_score"] == 80.0
