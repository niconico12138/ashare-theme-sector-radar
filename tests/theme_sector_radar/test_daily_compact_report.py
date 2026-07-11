"""
Daily Compact Report 测试

覆盖：
- compact markdown 包含 4 个主要章节
- 空池显示"暂无数据"
- V2 潜力观察展示 low_final_high_v2
- V2 分歧复核展示 high_final_low_v2
- 不包含 forbidden trade words
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.daily_compact_report import build_daily_compact_markdown


# ============================================================
# Forbidden Words
# ============================================================

FORBIDDEN_WORDS = [
    "buy", "sell", "hold",
    "买入", "卖出", "持有", "推荐",
    "建仓", "加仓", "减仓",
    "止盈", "止损", "目标价",
]


# ============================================================
# Tests
# ============================================================

class TestDailyCompactReport:
    """测试 daily compact report。"""

    def test_compact_markdown_sections(self):
        """compact markdown 应包含 4 个主要章节。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {"trend_top": [], "burst_top": [], "v2_potential": [], "divergence_review": []},
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        assert "每日简报" in result
        assert "## 1. 今日状态" in result
        assert "## 2. 核心板块" in result
        assert "## 3. 核心个股池" in result
        assert "## 4. 复核与降级" in result

    def test_empty_pool_shows_no_data(self):
        """空池应显示"暂无数据"。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {"trend_top": [], "burst_top": [], "v2_potential": [], "divergence_review": []},
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        assert "暂无数据" in result

    def test_v2_potential_shows_low_final_high_v2(self):
        """V2 潜力观察应展示 low_final_high_v2。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {
                "trend_top": [],
                "burst_top": [],
                "v2_potential": [
                    {"rank": 1, "code": "600001", "name": "测试股", "final_score": 30.0, "v2_score": 80.0, "action_state": "watch_only"},
                ],
                "divergence_review": [],
            },
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        assert "V2 潜力观察" in result
        assert "600001" in result
        assert "测试股" in result

    def test_divergence_review_shows_high_final_low_v2(self):
        """V2 分歧复核应展示 high_final_low_v2。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {
                "trend_top": [],
                "burst_top": [],
                "v2_potential": [],
                "divergence_review": [
                    {"rank": 1, "code": "600002", "name": "分歧股", "final_score": 80.0, "v2_score": 30.0, "action_state": "watch_only"},
                ],
            },
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        assert "V2 分歧复核" in result
        assert "600002" in result
        assert "分歧股" in result

    def test_no_forbidden_trade_words(self):
        """不包含 forbidden trade words。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {"trend_top": [], "burst_top": [], "v2_potential": [], "divergence_review": []},
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        for word in FORBIDDEN_WORDS:
            assert word not in result, f"Found forbidden word: {word}"

    def test_usage_boundary_at_end(self):
        """末尾应包含使用边界。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {"trend_top": [], "burst_top": [], "v2_potential": [], "divergence_review": []},
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        assert "watch_only" in result
        assert "不构成任何交易建议" in result

    def test_final_score_none_shows_dash(self):
        """final_score None 时应显示 "-"。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {
                "trend_top": [],
                "burst_top": [],
                "v2_potential": [],
                "divergence_review": [
                    {"rank": 1, "code": "600001", "name": "测试股", "final_score": None, "v2_score": 30.0, "action_state": "watch_only"},
                ],
            },
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        # final_score None 应显示为 "-"
        assert "| - |" in result

    def test_v2_score_none_shows_dash(self):
        """v2_score None 时应显示 "-"。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {
                "trend_top": [],
                "burst_top": [],
                "v2_potential": [],
                "divergence_review": [
                    {"rank": 1, "code": "600001", "name": "测试股", "final_score": 80.0, "v2_score": None, "action_state": "watch_only"},
                ],
            },
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        # v2_score None 应显示为 "-"
        assert "| - |" in result

    def test_final_score_zero_shows_00(self):
        """final_score 0 应显示 "0.00"。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {
                "trend_top": [],
                "burst_top": [],
                "v2_potential": [],
                "divergence_review": [
                    {"rank": 1, "code": "600001", "name": "测试股", "final_score": 0.0, "v2_score": 30.0, "action_state": "watch_only"},
                ],
            },
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        # final_score 0 应显示为 "0.00"
        assert "| 0.00 |" in result

    def test_sector_name_none_shows_dash(self):
        """sector_name None 时应显示 "-"。"""
        summary = {
            "as_of": "2026-07-10",
            "run_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True, "market_regime": "unknown"},
            "sector_focus": {"industries": [], "concepts": []},
            "stock_pools": {
                "eligible_watchlist": [
                    {"rank": 1, "code": "600001", "name": "测试股", "sector_name": "", "source_pool": "trend_top", "final_score": 75.0, "v2_score": 60.0, "opportunity_type": "trend_follow", "reason_codes": ["core_watch"], "action_state": "watch_only", "selection_score": 70.0},
                ],
                "trend_top": [],
                "burst_top": [],
                "v2_potential": [],
                "divergence_review": [],
            },
            "risk_summary": {"data_quality_warnings": [], "run_health_reasons": [], "notes": []},
        }

        result = build_daily_compact_markdown(summary)

        # sector_name 为空应显示为 "-"
        assert "| - |" in result
