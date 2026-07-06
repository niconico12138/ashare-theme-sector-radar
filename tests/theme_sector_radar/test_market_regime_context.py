"""
Market Regime Context 测试

测试市场状态解释层模块。
"""

import pytest

from theme_sector_radar.agents.sector_research.market_regime_context import MarketRegimeContext


class TestMarketRegimeContext:
    """测试 MarketRegimeContext"""

    def test_generate_regime_context_with_data(self):
        """测试有数据时生成 regime 上下文"""
        ctx = MarketRegimeContext()

        radar_data = {
            "market_breadth": {
                "breadth_label": "broad_rising",
                "industry_up_ratio": 0.70,
                "average_industry_change_pct": 1.5,
            },
            "market_temperature": {
                "score": 75,
                "label": "hot",
            },
        }

        result = ctx.generate_regime_context("2026-06-15", radar_data)
        assert result["regime_composite_label"] == "risk_on"
        assert result["benchmark_trend"] == "benchmark_uptrend"
        assert result["market_temperature_regime"] == "market_hot"
        assert result["breadth_regime"] == "broad_rising"
        assert result["decision_impact"] == "report_only"

    def test_generate_regime_context_without_data(self):
        """测试无数据时返回空上下文"""
        ctx = MarketRegimeContext()
        result = ctx.generate_regime_context("2026-06-15", None)
        assert result["regime_composite_label"] == "unknown_regime"
        assert result["decision_impact"] == "report_only"

    def test_generate_regime_interpretation_choppy(self):
        """测试 choppy_market 的 regime 解释"""
        ctx = MarketRegimeContext()

        regime_context = {
            "regime_composite_label": "choppy_market",
        }

        result = ctx.generate_regime_interpretation(regime_context, "low_signal_noise")
        assert "震荡" in result["summary"]
        assert len(result["watch_points"]) > 0
        assert result["label_context"] != ""

    def test_generate_regime_interpretation_risk_off(self):
        """测试 risk_off 的 regime 解释"""
        ctx = MarketRegimeContext()

        regime_context = {
            "regime_composite_label": "risk_off",
        }

        result = ctx.generate_regime_interpretation(regime_context, "oversold_rebound_candidate")
        assert "风险规避" in result["summary"]
        assert "成功率较低" in result["label_context"]

    def test_regime_does_not_affect_scores(self):
        """测试 regime 不影响评分"""
        ctx = MarketRegimeContext()

        regime_context = {
            "regime_composite_label": "risk_on",
        }

        result = ctx.generate_regime_interpretation(regime_context, "weak_or_avoid")
        # regime_interpretation 只包含文本解释，不包含分数
        assert "summary" in result
        assert "label_context" in result
        assert "watch_points" in result
        assert "warnings" in result
        # 不应包含任何分数修改
        assert "score_adjustment" not in result
        assert "ranking_modifier" not in result

    def test_all_regime_labels_have_interpretation(self):
        """测试所有 regime 标签都有解释"""
        ctx = MarketRegimeContext()

        for regime in ["risk_on", "risk_off", "weak_rebound", "choppy_market", "unknown_regime"]:
            regime_context = {"regime_composite_label": regime}
            result = ctx.generate_regime_interpretation(regime_context, "low_signal_noise")
            assert result["summary"] != "", f"Missing summary for {regime}"

    def test_report_no_trade_advice(self):
        """测试解释不包含交易建议词"""
        ctx = MarketRegimeContext()

        for regime in ["risk_on", "risk_off", "weak_rebound", "choppy_market"]:
            regime_context = {"regime_composite_label": regime}
            for label in ["low_signal_noise", "oversold_rebound_candidate", "conflicted", "weak_or_avoid"]:
                result = ctx.generate_regime_interpretation(regime_context, label)
                all_text = result["summary"] + result["label_context"]
                trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
                for word in trade_words:
                    assert word not in all_text.lower(), f"Found trade word '{word}' in {regime}/{label}"
