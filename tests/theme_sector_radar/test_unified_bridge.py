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
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保项目根目录在 path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sector_stock_bridge import (
    _compute_flow_alignment,
    _compute_rank_scores,
    _normalize_weights,
    compute_relevance_scores,
    extract_top_sectors,
    find_cross_sectors,
    find_latest_report,
    load_sector_scores,
)
from unified_pipeline import (
    _compute_fallback_quant_score,
    compute_final_scores,
    compute_quant_scores,
)


# ============================================================
# Fixtures
# ============================================================

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


# ============================================================
# 测试：报告读取
# ============================================================

class TestReportReading:

    def test_find_latest_report_with_date(self):
        """指定日期读取报告"""
        date, path = find_latest_report("2026-07-01")
        assert date == "2026-07-01"
        assert path is not None
        assert path.exists()

    def test_find_latest_report_fallback(self):
        """不存在的日期应 fallback 到最新"""
        date, path = find_latest_report("2099-01-01")
        # 应该 fallback 到最新可用日期
        if date:
            assert date <= "2099-01-01"
            assert path is not None

    def test_find_latest_report_no_date(self):
        """不指定日期应找到最新"""
        date, path = find_latest_report(None)
        assert date is not None
        assert path is not None

    def test_load_sector_scores_structure(self, sample_scores_data):
        """加载的报告应有正确的结构"""
        assert "scores" in sample_scores_data
        assert len(sample_scores_data["scores"]) == 10
        first = sample_scores_data["scores"][0]
        assert "sector_name" in first
        assert "trend_continuation_score" in first
        assert "short_term_burst_score" in first


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
        }
        score = _compute_fallback_quant_score(stock)
        assert 0 <= score <= 100
        assert score > 30  # 应该有不错的分数

    def test_fallback_quant_score_poor_stock(self):
        """差股票应得低分"""
        stock = {
            "change_pct": -5.0,
            "total_mv": 5,
            "pe": 500,
            "pb": 50,
        }
        score = _compute_fallback_quant_score(stock)
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
        """综合分应正确计算"""
        stocks = [
            {"code": "600030", "quant_score": 80, "relevance_score": 0.9},
            {"code": "601211", "quant_score": 60, "relevance_score": 0.7},
        ]
        result = compute_final_scores(stocks)
        assert len(result) == 2
        # 综合分 = 量化分*0.6/100 + 关联度*0.4, 然后*100
        expected_1 = (80 / 100 * 0.6 + 0.9 * 0.4) * 100
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
        """提供 20 根 K 线应计算所有 7 个因子。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": 3.0, "total_mv": 200, "pe": 15}
        bars = [
            {"date": f"2026-06-{d:02d}", "open": 20, "high": 21, "low": 19, "close": 20 + i * 0.1, "amount": 3e8}
            for i, d in enumerate(range(1, 21))
        ]
        score = _compute_enhanced_quant_score(stock, bars)
        assert 0 <= score <= 100
        # With positive returns, decent MV, good PE, should be reasonably good
        assert score > 30

    def test_enhanced_score_with_poor_bars(self):
        """下跌+高回撤应得低分。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": -5.0, "total_mv": 5, "pe": 500}
        bars = [
            {"date": f"2026-06-{d:02d}", "open": 20, "high": 21, "low": 19,
             "close": 20 - i * 0.8, "amount": 1e6}
            for i, d in enumerate(range(1, 21))
        ]
        score = _compute_enhanced_quant_score(stock, bars)
        assert score < 30

    def test_enhanced_score_min_bars(self):
        """只有 5 根 K 线时，应跳过 10 日因子但仍能正常计算。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": 2.0, "total_mv": 100, "pe": 20}
        bars = [
            {"date": f"2026-07-0{i}", "open": 20, "high": 21, "low": 19, "close": 21 + i * 0.2, "amount": 2e8}
            for i in range(5)
        ]
        score = _compute_enhanced_quant_score(stock, bars)
        assert 0 <= score <= 100

    def test_enhanced_score_with_zero_bars(self):
        """零根 K 线时不抛异常。"""
        from unified_pipeline import _compute_enhanced_quant_score

        stock = {"change_pct": 0, "total_mv": 0, "pe": 0}
        score = _compute_enhanced_quant_score(stock, [])
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
            assert s["quant_source"] == "fallback"
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
            assert result[0]["quant_source"] == "http_enhanced"
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
            assert result[0]["quant_source"] == "fallback"

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

        score = _compute_enhanced_quant_score(stock, bars)
        assert 0 <= score <= 100
        # Should be lower than a stock with no drawdown
        bars_no_dd = [
            {"date": f"2026-07-0{i}", "open": 20, "high": 21, "low": 19,
             "close": 20 + i * 0.5, "amount": 2e8}
            for i in range(10)
        ]
        score_no_dd = _compute_enhanced_quant_score(stock, bars_no_dd)
        assert score_no_dd > score  # no drawdown should be higher


# ============================================================
# 测试：桥接层 HTTP 集成
# ============================================================


class TestBridgeHttpIntegration:
    """Test that fetch_sector_constituents uses simplified Phase 3 fallback."""

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
                    # Should come from SECTOR_STOCK_MAPPING
                    codes = [s["code"] for s in result["stocks"]]
                    assert "688981" in codes

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
                    assert "600030" in codes

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

    def test_bridge_output_has_constituent_source_summary(self):
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
                    assert "constituent_source_summary" in result
                    summary = result["constituent_source_summary"]
                    assert isinstance(summary, dict)
                    # Should have at least one key
                    assert len(summary) > 0
                    # Total should match number of unique sectors
                    total = sum(summary.values())
                    assert total > 0

    def test_source_summary_fields_are_valid(self):
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
                    summary = result["constituent_source_summary"]
                    for key in summary:
                        assert key in valid_labels, f"Unknown source label: {key}"

    def test_unified_json_has_data_source_field(self):
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
                        result = up.run_pipeline(as_of_date="2026-07-01", mode="quick")
                        assert "data_source" in result
                        ds = result["data_source"]
                        assert "constituent_sources" in ds
                        assert "quant_score_sources" in ds
                        assert "has_unavailable_sectors" in ds
                        assert "has_emergency_fallback" in ds

    def test_unified_json_has_bridge_source_summary(self):
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
                        result = up.run_pipeline(as_of_date="2026-07-01", mode="quick")
                        bs = result.get("bridge_result", {})
                        assert "constituent_source_summary" in bs

    def test_markdown_report_has_data_source_section(self):
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
                        result = up.run_pipeline(as_of_date="2026-07-01", mode="quick")

                        # Generate markdown directly
                        md = up.generate_markdown_report(
                            as_of_date="2026-07-01",
                            trend_stocks=result.get("trend_top_stocks", []),
                            burst_stocks=result.get("burst_top_stocks", []),
                            bridge_result=result.get("bridge_result", {}),
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


class TestDailyRunScript:
    """Test scripts/run_daily_unified_pipeline.py utilities."""

    def test_check_tcp_port_localhost(self):
        """_check_tcp_port with a likely-open port should work."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_tcp_port

        # StockDB should be running on 7899 in this environment
        # If not, this just checks the function doesn't crash
        result = _check_tcp_port("127.0.0.1", 7899, timeout=1.0)
        assert isinstance(result, bool)

    def test_check_tcp_port_closed(self):
        """_check_tcp_port with a closed port should return False."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_tcp_port

        result = _check_tcp_port("127.0.0.1", 59999, timeout=0.5)
        assert result is False

    def test_check_http_health_api_url(self):
        """_check_http_health with market_data_service should return True."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_http_health

        ok, body = _check_http_health("http://127.0.0.1:8000", timeout=3)
        if ok:
            assert "stockdb" in body
        # If not ok, the function still shouldn't crash

    def test_check_http_health_unreachable(self):
        """_check_http_health with unreachable URL should return False."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _check_http_health

        ok, error = _check_http_health("http://127.0.0.1:59998", timeout=1)
        assert ok is False
        assert isinstance(error, str)

    def test_find_latest_report(self):
        """_find_latest_report should locate existing report."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _find_latest_report

        path = _find_latest_report("2026-07-02")
        if path:
            assert path.exists()
            assert path.name == "unified_report.json"

    def test_load_report_has_required_fields(self):
        """Loaded report should have run_health and data_source."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from run_daily_unified_pipeline import _find_latest_report, _load_report

        path = _find_latest_report("2026-07-02")
        if path:
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

    @staticmethod
    def _api_available() -> bool:
        """Check if market_data_service API is reachable."""
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8000/health")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def test_main_api_unreachable(self):
        """API unreachable → exit 1."""
        import subprocess, sys as _sys

        proc = subprocess.run(
            [_sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_unified_pipeline.py"),
             "--as-of", "2026-07-02", "--api-url", "http://127.0.0.1:59999"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(PROJECT_ROOT),
        )
        assert proc.returncode == 1
        assert "API 未启动" in (proc.stdout or "") or "无法访问" in (proc.stdout or "")

    def test_main_api_ok_runs_pipeline(self):
        """API reachable → should run pipeline and exit 0 (integration test)."""
        if not self._api_available():
            pytest.skip("market_data_service API not available")

        import subprocess, sys as _sys
        proc = subprocess.run(
            [_sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_unified_pipeline.py"),
             "--as-of", "2026-07-02", "--mode", "quick"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(PROJECT_ROOT), timeout=300,
        )
        assert proc.returncode == 0
        assert "健康门禁" in (proc.stdout or "")

    def test_main_fail_on_health_fail_flag(self):
        """--fail-on-health-fail flag integration test."""
        if not self._api_available():
            pytest.skip("market_data_service API not available")

        import subprocess, sys as _sys
        proc = subprocess.run(
            [_sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_unified_pipeline.py"),
             "--as-of", "2026-07-02", "--mode", "quick", "--fail-on-health-fail"],
            capture_output=True, text=True, encoding="utf-8", cwd=str(PROJECT_ROOT), timeout=300,
        )
        assert proc.returncode in (0, 2)
        assert "健康门禁" in (proc.stdout or "")


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

    def test_no_append_index_skips_write(self, tmp_path):
        """Running with --no-append-index should not write to index (integration)."""
        if not TestDailyRunScript._api_available():
            pytest.skip("market_data_service API not available")

        import subprocess, sys as _sys

        idx = tmp_path / "test_index.jsonl"
        proc = subprocess.run(
            [_sys.executable, str(PROJECT_ROOT / "scripts" / "run_daily_unified_pipeline.py"),
             "--as-of", "2026-07-02", "--mode", "quick",
             "--index-path", str(idx), "--no-append-index"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(PROJECT_ROOT), timeout=300,
        )
        assert proc.returncode == 0
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
                 "quant_source": "http_enhanced+ff_batch"}
        bd = build_score_breakdown(stock)
        assert bd["final_score"] == 82.5
        assert bd["quant_score_component"] == pytest.approx(49.2, abs=0.1)   # 82.0 * 0.6
        assert bd["relevance_score_component"] == pytest.approx(33.32, abs=0.1)  # 0.833 * 40
        assert bd["has_fund_flow"] is True
        assert "formula" in bd

    def test_missing_fields_no_crash(self):
        from unified_pipeline import build_score_breakdown

        bd = build_score_breakdown({})
        assert bd["final_score"] == 0.0
        assert bd["quant_score_component"] == 0.0
        assert bd["has_fund_flow"] is False

    def test_final_score_unchanged(self):
        from unified_pipeline import build_score_breakdown

        stock = {"final_score": 82.5, "quant_score": 82.0, "relevance_score": 0.833}
        bd = build_score_breakdown(stock)
        assert bd["final_score"] == stock["final_score"]

    def test_no_fund_flow(self):
        from unified_pipeline import build_score_breakdown

        stock = {"quant_score": 60.0, "relevance_score": 0.7, "final_score": 64.0,
                 "quant_source": "http_enhanced"}
        bd = build_score_breakdown(stock)
        assert bd["has_fund_flow"] is False

    def test_annotate_adds_breakdown(self):
        from unified_pipeline import _annotate_score_breakdown

        stocks = [{"final_score": 80.0, "quant_score": 80.0, "relevance_score": 0.8}]
        _annotate_score_breakdown(stocks)
        assert "score_breakdown" in stocks[0]
        assert stocks[0]["score_breakdown"]["final_score"] == 80.0
