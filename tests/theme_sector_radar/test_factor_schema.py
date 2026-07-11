"""
统一因子 Schema 测试

覆盖：
- registry 中核心因子存在
- normalize_factor 对 already_scored / higher_is_better / lower_is_better / missing 正常工作
- build_factor_snapshot 能从 candidate 生成 factor_snapshot
- 缺失字段不会异常
- export_top30_candidates.enrich_candidates_with_scoring 后 candidate 包含 factor_snapshot
- generate_aihf_request 输出 stocks 中包含 factor_snapshot
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.factors.registry import FACTOR_REGISTRY, get_factor_metadata, list_enabled_factors
from theme_sector_radar.factors.normalizer import normalize_factor
from theme_sector_radar.factors.snapshot import build_factor_snapshot
from theme_sector_radar.factors.schema import FactorValue, FactorSnapshot

import export_top30_candidates as export_candidates


# ============================================================
# Registry Tests
# ============================================================

class TestRegistry:
    """测试因子元数据注册表。"""

    def test_registry_has_24_factors(self):
        """注册表应包含全部启用因子。"""
        assert len(FACTOR_REGISTRY) == 84

    def test_core_factors_exist(self):
        """核心因子必须存在。"""
        core_factors = [
            "ma20_slope_5",
            "stock_trend_score",
            "stock_short_score",
            "stock_short_score_v2",
            "drawdown_risk_score",
            "risk_penalty_score",
            "regime_router_shadow_score_v5",
            "sector_trend_score",
            "sector_burst_score",
            "final_score",
            "agent_score",
            "trend_agent_score",
            "short_agent_score",
        ]
        for factor_id in core_factors:
            assert factor_id in FACTOR_REGISTRY, f"Missing factor: {factor_id}"

    def test_get_factor_metadata(self):
        """get_factor_metadata 应返回正确的元数据。"""
        meta = get_factor_metadata("stock_trend_score")
        assert meta is not None
        assert meta.factor_id == "stock_trend_score"
        assert meta.category == "trend"
        assert meta.direction == "already_scored"

    def test_list_enabled_factors(self):
        """list_enabled_factors 应返回所有启用的因子。"""
        enabled = list_enabled_factors()
        assert len(enabled) == 84
        assert all(f.enabled for f in enabled)

    def test_short_emotion_factors_are_registered_as_shadow_only(self):
        """Short-burst emotion factors should be registered but shadow-only."""
        short_factors = [
            "short_emotion_heat_score",
            "sector_burst_breadth_score",
            "limit_attention_score",
            "intraday_reversal_risk_score",
            "close_strength_score",
            "volume_burst_quality_score",
            "single_name_overheat_score",
            "next_day_cashout_risk_score",
            "short_burst_emotion_score_v1",
            "short_burst_emotion_score_v2",
            "market_short_emotion_score",
            "limit_up_breadth_score",
            "limit_up_failure_risk",
            "leader_continuation_score",
            "short_burst_environment_score",
            "crowding_heat_score",
            "news_heat_score",
            "policy_catalyst_score",
            "earnings_catalyst_score",
            "event_freshness_score",
            "event_continuation_score",
            "negative_news_risk_score",
            "rumor_hype_risk_score",
            "short_burst_news_emotion_score_shadow",
        ]
        for factor_id in short_factors:
            meta = get_factor_metadata(factor_id)
            assert meta is not None
            assert meta.category in {"short_emotion", "risk", "volume", "market_emotion", "catalyst"}
            assert "short_burst_shadow" in meta.tags

    def test_intraday_factors_are_registered_as_shadow_only(self):
        """Intraday factors should be registered for shadow validation only."""
        intraday_factors = [
            "intraday_close_position_score",
            "intraday_high_pullback_risk_score",
            "intraday_volume_price_confirm_score",
            "intraday_sector_breadth_score",
            "intraday_late_strength_score",
            "short_burst_intraday_emotion_score_shadow",
            "late_return_30m_score",
            "late_vwap_support_score",
            "late_volume_share_score",
            "late_high_near_close_score",
            "high_to_close_drawdown_score",
            "morning_spike_fade_score",
            "afternoon_fade_score",
            "max_gain_giveback_ratio",
            "close_vs_vwap_score",
            "late_price_above_vwap_ratio",
            "vwap_slope_score",
            "vwap_reclaim_score",
            "volume_without_price_progress_risk",
            "late_volume_efficiency_score",
            "amount_acceleration_score",
            "volume_spike_exhaustion_score",
            "opening_drive_score",
            "morning_strength_persist_score",
            "morning_pullback_repair_score",
            "open_to_midday_resilience_score",
            "sector_intraday_breadth_change",
            "sector_late_breadth_score",
            "leader_follower_sync_score",
            "stock_vs_sector_intraday_alpha",
        ]
        for factor_id in intraday_factors:
            meta = get_factor_metadata(factor_id)
            assert meta is not None
            assert meta.category == "intraday"
            assert "intraday_shadow" in meta.tags
            assert "no_execution_signal" in meta.tags


# ============================================================
# Normalizer Tests
# ============================================================

class TestNormalizer:
    """测试因子归一化逻辑。"""

    def test_already_scored_clamps_to_0_100(self):
        """already_scored 方向应直接裁剪到 0-100。"""
        meta = get_factor_metadata("stock_trend_score")
        assert meta.direction == "already_scored"

        # 正常值
        score, quality = normalize_factor(75.0, meta)
        assert score == 75.0
        assert quality == "good"

        # 超过 100
        score, quality = normalize_factor(120.0, meta)
        assert score == 100.0

        # 低于 0
        score, quality = normalize_factor(-10.0, meta)
        assert score == 0.0

    def test_higher_is_better_linear_scale(self):
        """higher_is_better 方向应线性缩放。"""
        meta = get_factor_metadata("ma20_slope_5")
        assert meta.direction == "higher_is_better"

        # 假设 value_min=0, value_max=10
        score, quality = normalize_factor(5.0, meta, value_min=0.0, value_max=10.0)
        assert score == 50.0
        assert quality == "good"

        score, quality = normalize_factor(10.0, meta, value_min=0.0, value_max=10.0)
        assert score == 100.0

        score, quality = normalize_factor(0.0, meta, value_min=0.0, value_max=10.0)
        assert score == 0.0

    def test_lower_is_better_reverse_scale(self):
        """lower_is_better 方向应反向缩放。"""
        meta = get_factor_metadata("drawdown_risk_score")
        assert meta.direction == "lower_is_better"

        # 假设 value_min=0, value_max=50
        score, quality = normalize_factor(25.0, meta, value_min=0.0, value_max=50.0)
        assert score == 50.0
        assert quality == "good"

        score, quality = normalize_factor(0.0, meta, value_min=0.0, value_max=50.0)
        assert score == 100.0

        score, quality = normalize_factor(50.0, meta, value_min=0.0, value_max=50.0)
        assert score == 0.0

    def test_missing_value_returns_50(self):
        """缺失值应返回 score=50, quality=missing。"""
        meta = get_factor_metadata("stock_trend_score")
        score, quality = normalize_factor(None, meta)
        assert score == 50.0
        assert quality == "missing"

    def test_neutral_returns_50(self):
        """neutral 方向应返回 50。"""
        # 注册一个 neutral 因子用于测试
        from theme_sector_radar.factors.registry import FactorMetadata
        neutral_meta = FactorMetadata(
            factor_id="test_neutral",
            display_name="测试中性",
            category="trend",
            source_project="test",
            direction="neutral",
            lookback_days=None,
            enabled=True,
            description="测试用",
        )
        score, quality = normalize_factor(75.0, neutral_meta)
        assert score == 50.0
        assert quality == "good"


# ============================================================
# Schema Tests
# ============================================================

class TestSchema:
    """测试数据结构。"""

    def test_factor_value_to_dict(self):
        """FactorValue.to_dict 应返回普通 dict。"""
        fv = FactorValue(
            factor_id="test",
            raw_value=75.0,
            score=75.0,
            category="trend",
            source_project="test",
            direction="already_scored",
            lookback_days=5,
            quality="good",
            display_name="测试",
            description="测试因子",
            tags=["tag1"],
        )
        d = fv.to_dict()
        assert isinstance(d, dict)
        assert d["factor_id"] == "test"
        assert d["tags"] == ["tag1"]

    def test_factor_snapshot_to_dict(self):
        """FactorSnapshot.to_dict 应返回普通 dict。"""
        fs = FactorSnapshot(
            schema_version="1.0",
            as_of="2026-07-10",
            code="600001",
            name="测试股",
            factors=[],
            summary={"factor_count": 0},
        )
        d = fs.to_dict()
        assert isinstance(d, dict)
        assert d["schema_version"] == "1.0"
        assert d["code"] == "600001"

    def test_factor_snapshot_json_serializable(self):
        """FactorSnapshot 应可 JSON 序列化。"""
        fs = FactorSnapshot(
            schema_version="1.0",
            as_of="2026-07-10",
            code="600001",
            name="测试股",
            factors=[
                FactorValue(
                    factor_id="test",
                    raw_value=75.0,
                    score=75.0,
                    category="trend",
                    source_project="test",
                    direction="already_scored",
                    lookback_days=5,
                    quality="good",
                    display_name="测试",
                    description="测试因子",
                    tags=[],
                )
            ],
            summary={"factor_count": 1},
        )
        json_str = json.dumps(fs.to_dict(), ensure_ascii=False)
        assert "test" in json_str


# ============================================================
# Snapshot Tests
# ============================================================

class TestSnapshot:
    """测试因子快照构建。"""

    def test_build_factor_snapshot_basic(self):
        """build_factor_snapshot 应从 candidate 生成 factor_snapshot。"""
        candidate = {
            "code": "600001",
            "name": "测试股A",
            "stock_trend_score": 75.0,
            "stock_short_score": 68.0,
            "final_score": 72.0,
            "sector_trend_score": 70.0,
            "sector_burst_score": 65.0,
        }
        snapshot = build_factor_snapshot(candidate, as_of="2026-07-10")

        assert snapshot["schema_version"] == "1.0"
        assert snapshot["as_of"] == "2026-07-10"
        assert snapshot["code"] == "600001"
        assert snapshot["name"] == "测试股A"
        assert len(snapshot["factors"]) == 84

        # 检查 summary
        assert snapshot["summary"]["factor_count"] == 84
        assert snapshot["summary"]["missing_count"] >= 0

    def test_build_factor_snapshot_missing_fields(self):
        """缺失字段不会异常，标记为 missing。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
        }
        snapshot = build_factor_snapshot(candidate, as_of="2026-07-10")

        assert snapshot["schema_version"] == "1.0"
        assert len(snapshot["factors"]) == 84

        # 所有因子都应标记为 missing
        missing_factors = [f for f in snapshot["factors"] if f["quality"] == "missing"]
        assert len(missing_factors) == 84

    def test_build_factor_snapshot_empty_candidate(self):
        """空 candidate 不会异常。"""
        snapshot = build_factor_snapshot({}, as_of="2026-07-10")
        assert snapshot["schema_version"] == "1.0"
        assert len(snapshot["factors"]) == 84

    def test_build_factor_snapshot_returns_dict(self):
        """返回值应为普通 dict。"""
        candidate = {"code": "600001", "name": "测试股"}
        snapshot = build_factor_snapshot(candidate)
        assert isinstance(snapshot, dict)
        # 可 JSON 序列化
        json_str = json.dumps(snapshot, ensure_ascii=False)
        assert "600001" in json_str


# ============================================================
# Integration Tests with export_top30_candidates
# ============================================================

class TestExportTop30Integration:
    """测试与 export_top30_candidates 的集成。"""

    def test_enrich_candidates_adds_factor_snapshot(self):
        """enrich_candidates_with_scoring 后 candidate 应包含 factor_snapshot。"""
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
        ]
        enriched = export_candidates.enrich_candidates_with_scoring(candidates)

        assert len(enriched) == 1
        assert "factor_snapshot" in enriched[0]

        snapshot = enriched[0]["factor_snapshot"]
        assert snapshot["schema_version"] == "1.0"
        assert snapshot["code"] == "600001"
        assert len(snapshot["factors"]) == 84

    def test_enrich_empty_list(self):
        """空列表不应异常。"""
        result = export_candidates.enrich_candidates_with_scoring([])
        assert result == []

    def test_factor_snapshot_preserves_existing_fields(self):
        """factor_snapshot 不应改变 candidate 其他字段。"""
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
        ]
        enriched = export_candidates.enrich_candidates_with_scoring(candidates)

        c = enriched[0]
        assert c["code"] == "600001"
        assert c["name"] == "测试股A"
        assert c["final_score"] == 75.0
        assert c["stock_trend_score"] >= 0
        assert c["stock_short_score"] >= 0


class TestAIHFRequestIntegration:
    """测试与 generate_aihf_request 的集成。"""

    def test_aihf_request_includes_factor_snapshot(self, tmp_path, monkeypatch):
        """aihf_request.json stocks 应包含 factor_snapshot。"""
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
                        "factor_snapshot": {
                            "schema_version": "1.0",
                            "code": "600001",
                            "name": "测试股",
                            "factors": [],
                            "summary": {},
                        },
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
        assert "factor_snapshot" in stock
        assert stock["factor_snapshot"]["schema_version"] == "1.0"

    def test_aihf_request_missing_factor_snapshot(self, tmp_path, monkeypatch):
        """factor_snapshot 缺失时不应报错。"""
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
        assert "factor_snapshot" in stock
        assert stock["factor_snapshot"] is None
