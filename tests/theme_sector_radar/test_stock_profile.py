"""
Stock Profile 测试

覆盖：
- 趋势 uptrend/repair/weak/unknown 判断
- momentum strong/neutral/weak/unknown 判断
- volume confirmed/dry_up/neutral/unknown 判断
- volatility contracting/expanding/normal/unknown 判断
- risk low/medium/high/unknown 判断
- sector_support strong/weak/neutral/unknown 判断
- v2_signal opportunity/confirmed/divergent/none 判断
- factor_snapshot missing quality 不参与判断
- 缺字段不报错
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.stock_profile import build_stock_profile


# ============================================================
# Tests
# ============================================================

class TestStockProfile:
    """测试个股画像。"""

    def test_trend_uptrend(self):
        """stock_trend_score >= 70 应判断为 uptrend。"""
        candidate = {"stock_trend_score": 75.0}

        result = build_stock_profile(candidate)

        assert result["trend_state"] == "uptrend"

    def test_trend_repair(self):
        """stock_trend_score >= 55 应判断为 repair。"""
        candidate = {"stock_trend_score": 60.0}

        result = build_stock_profile(candidate)

        assert result["trend_state"] == "repair"

    def test_trend_weak(self):
        """stock_trend_score < 45 应判断为 weak。"""
        candidate = {"stock_trend_score": 40.0}

        result = build_stock_profile(candidate)

        assert result["trend_state"] == "weak"

    def test_trend_unknown(self):
        """缺少 stock_trend_score 应判断为 unknown。"""
        candidate = {}

        result = build_stock_profile(candidate)

        assert result["trend_state"] == "unknown"

    def test_momentum_strong(self):
        """stock_short_score_v2 >= 70 应判断为 strong。"""
        candidate = {"stock_short_score_v2": 75.0}

        result = build_stock_profile(candidate)

        assert result["momentum_state"] == "strong"

    def test_momentum_neutral(self):
        """stock_short_score_v2 >= 50 应判断为 neutral。"""
        candidate = {"stock_short_score_v2": 55.0}

        result = build_stock_profile(candidate)

        assert result["momentum_state"] == "neutral"

    def test_momentum_weak(self):
        """stock_short_score_v2 < 45 应判断为 weak。"""
        candidate = {"stock_short_score_v2": 40.0}

        result = build_stock_profile(candidate)

        assert result["momentum_state"] == "weak"

    def test_volume_confirmed(self):
        """amount_ratio_20 >= 65 应判断为 confirmed。"""
        candidate = {"factor_snapshot": {"factors": [{"factor_id": "amount_ratio_20", "score": 70.0, "quality": "good"}]}}

        result = build_stock_profile(candidate)

        assert result["volume_state"] == "confirmed"

    def test_volume_dry_up(self):
        """amount_ratio_20 <= 40 应判断为 dry_up。"""
        candidate = {"factor_snapshot": {"factors": [{"factor_id": "amount_ratio_20", "score": 35.0, "quality": "good"}]}}

        result = build_stock_profile(candidate)

        assert result["volume_state"] == "dry_up"

    def test_volatility_contracting(self):
        """contraction_score >= 65 应判断为 contracting。"""
        candidate = {"factor_snapshot": {"factors": [{"factor_id": "contraction_score", "score": 70.0, "quality": "good"}]}}

        result = build_stock_profile(candidate)

        assert result["volatility_state"] == "contracting"

    def test_volatility_expanding(self):
        """contraction_score <= 40 应判断为 expanding。"""
        candidate = {"factor_snapshot": {"factors": [{"factor_id": "contraction_score", "score": 35.0, "quality": "good"}]}}

        result = build_stock_profile(candidate)

        assert result["volatility_state"] == "expanding"

    def test_risk_low(self):
        """drawdown_risk_score <= 35 且 risk_penalty_score <= 35 应判断为 low。"""
        candidate = {
            "factor_snapshot": {
                "factors": [
                    {"factor_id": "drawdown_risk_score", "score": 30.0, "quality": "good"},
                    {"factor_id": "risk_penalty_score", "score": 25.0, "quality": "good"},
                ]
            }
        }

        result = build_stock_profile(candidate)

        assert result["risk_state"] == "low"

    def test_risk_high(self):
        """drawdown_risk_score >= 70 应判断为 high。"""
        candidate = {
            "factor_snapshot": {
                "factors": [
                    {"factor_id": "drawdown_risk_score", "score": 75.0, "quality": "good"},
                    {"factor_id": "risk_penalty_score", "score": 30.0, "quality": "good"},
                ]
            }
        }

        result = build_stock_profile(candidate)

        assert result["risk_state"] == "high"

    def test_sector_support_strong(self):
        """sector_trend_score >= 65 应判断为 strong。"""
        candidate = {"sector_trend_score": 70.0}

        result = build_stock_profile(candidate)

        assert result["sector_support"] == "strong"

    def test_sector_support_weak(self):
        """sector_trend_score < 45 应判断为 weak。"""
        candidate = {"sector_trend_score": 40.0}

        result = build_stock_profile(candidate)

        assert result["sector_support"] == "weak"

    def test_v2_signal_opportunity(self):
        """selection_bucket == v2_opportunity 应判断为 opportunity。"""
        candidate = {"selection_bucket": "v2_opportunity"}

        result = build_stock_profile(candidate)

        assert result["v2_signal"] == "opportunity"

    def test_v2_signal_confirmed(self):
        """selection_bucket == core_watch 且 v2_score >= 50 应判断为 confirmed。"""
        candidate = {"selection_bucket": "core_watch", "v2_score": 55.0}

        result = build_stock_profile(candidate)

        assert result["v2_signal"] == "confirmed"

    def test_v2_signal_divergent(self):
        """selection_bucket == divergence_review 应判断为 divergent。"""
        candidate = {"selection_bucket": "divergence_review"}

        result = build_stock_profile(candidate)

        assert result["v2_signal"] == "divergent"

    def test_missing_factor_snapshot(self):
        """factor_snapshot 缺失时不报错。"""
        candidate = {}

        result = build_stock_profile(candidate)

        assert result["volume_state"] == "unknown"
        assert result["volatility_state"] == "unknown"
        assert result["risk_state"] == "unknown"

    def test_factor_quality_missing(self):
        """factor_snapshot 中 quality == missing 不参与判断。"""
        candidate = {
            "factor_snapshot": {
                "factors": [
                    {"factor_id": "amount_ratio_20", "score": 70.0, "quality": "missing"},
                ]
            }
        }

        result = build_stock_profile(candidate)

        assert result["volume_state"] == "unknown"


class TestNewFactorProfile:
    """测试新因子对 stock_profile 的影响。"""

    def test_chasing_risk_high_risk_state(self):
        """chasing_risk_score >= 75 应判断 risk_state 为 high。"""
        candidate = {"chasing_risk_score": 80.0}

        result = build_stock_profile(candidate)

        # chasing_risk >= 75 且其他风险字段缺失时，risk_state 应为 high
        # 但根据当前逻辑，需要 drawdown_risk 和 risk_penalty 都缺失
        # 所以这里检查的是：如果有 chasing_risk >= 75，应该触发 high
        # 但当前逻辑可能不完全匹配，让我们检查实际行为
        # 根据代码：if chasing_risk is not None and chasing_risk >= 75: risk_state = "high"
        # 所以这里应该返回 "high"
        assert result["risk_state"] == "high"

    def test_sector_support_score_strong(self):
        """sector_support_score >= 65 应判断 sector_support 为 strong。"""
        candidate = {"sector_support_score": 70.0}

        result = build_stock_profile(candidate)

        assert result["sector_support"] == "strong"

    def test_sector_support_score_weak(self):
        """sector_support_score < 50 应判断 sector_support 为 weak。"""
        candidate = {"sector_support_score": 40.0}

        result = build_stock_profile(candidate)

        assert result["sector_support"] == "weak"

    def test_sector_support_score_neutral(self):
        """sector_support_score 50-65 应判断 sector_support 为 neutral。"""
        candidate = {"sector_support_score": 55.0}

        result = build_stock_profile(candidate)

        assert result["sector_support"] == "neutral"

    def test_sector_support_score_from_trend_burst(self):
        """sector_support_score 应能从 trend_score 和 burst_score 计算。"""
        candidate = {"trend_score": 70.0, "burst_score": 60.0}

        result = build_stock_profile(candidate)

        # sector_support_score = 70 * 0.7 + 60 * 0.3 = 49 + 18 = 67
        assert result["sector_support"] == "strong"

    def test_breakout_distance_near_breakout(self):
        """breakout_distance_20 <= 5 应辅助判断 trend_state 为 repair。"""
        candidate = {
            "breakout_distance_20": 3.0,
            "stock_trend_score": 50.0,  # 不是 uptrend
        }

        result = build_stock_profile(candidate)

        # breakout_distance <= 5 应触发 repair
        assert result["trend_state"] == "repair"

    def test_drawdown_depth_high_risk(self):
        """drawdown_depth_20 > 30 应判断 risk_state 为 high。"""
        candidate = {"drawdown_depth_20": 35.0}

        result = build_stock_profile(candidate)

        assert result["risk_state"] == "high"

    def test_missing_new_factors_no_impact(self):
        """缺失新因子不影响旧逻辑。"""
        candidate = {
            "stock_trend_score": 75.0,  # uptrend
            "sector_trend_score": 70.0,  # strong
        }

        result = build_stock_profile(candidate)

        assert result["trend_state"] == "uptrend"
        assert result["sector_support"] == "strong"
