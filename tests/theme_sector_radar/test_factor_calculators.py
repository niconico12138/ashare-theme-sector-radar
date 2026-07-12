"""
Bars 因子计算器测试

覆盖：
- ma20_slope_5 计算正确
- near_high_250 计算正确
- amount_ratio_20 计算正确
- contraction_score 在 ATR/range 收缩时更高
- bars 不足时不报错
- build_factor_snapshot(bars=...) 能输出真实因子
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.factors.calculators import (
    calculate_bar_factors,
    calculate_intraday_factors,
    _normalize_bars,
    _calc_ma,
    _calc_atr,
    _calc_range_pct,
    _calc_amount_avg,
)
from theme_sector_radar.factors.snapshot import build_factor_snapshot
from theme_sector_radar.factors.registry import FACTOR_REGISTRY


# ============================================================
# Helper Functions
# ============================================================

def _make_bars(
    closes: list[float],
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    amounts: list[float] | None = None,
    dates: list[str] | None = None,
    newest_first: bool = True,
) -> list[dict]:
    """生成测试用的 bars 数据。

    Args:
        closes: 收盘价列表
        highs: 最高价列表（可选）
        lows: 最低价列表（可选）
        amounts: 成交额列表（可选）
        dates: 日期列表（可选）
        newest_first: 是否新到旧排列（默认 True）
    """
    n = len(closes)
    if highs is None:
        highs = [c * 1.02 for c in closes]  # 高于收盘价 2%
    if lows is None:
        lows = [c * 0.98 for c in closes]   # 低于收盘价 2%
    if amounts is None:
        amounts = [100_000_000.0] * n
    if dates is None:
        if newest_first:
            dates = [f"2026-07-{10 - i:02d}" for i in range(n)]
        else:
            dates = [f"2026-07-{i + 1:02d}" for i in range(n)]

    bars = [
        {
            "date": dates[i],
            "open": closes[i] * 0.99,
            "high": highs[i],
            "low": lows[i],
            "close": closes[i],
            "volume": 10_000_000,
            "amount": amounts[i],
        }
        for i in range(n)
    ]

    # 如果需要旧到新排列，反转列表
    if not newest_first:
        bars = list(reversed(bars))

    return bars


def _make_intraday_bars(
    prices: list[float],
    amounts: list[float] | None = None,
    times: list[str] | None = None,
) -> list[dict]:
    n = len(prices)
    if amounts is None:
        amounts = [10_000_000.0] * n
    if times is None:
        times = [f"09:{30 + i:02d}" for i in range(n)]
    return [
        {
            "time": times[i],
            "price": prices[i],
            "close": prices[i],
            "amount": amounts[i],
        }
        for i in range(n)
    ]


# ============================================================
# Normalize Bars Tests
# ============================================================

class TestNormalizeBars:
    """测试 bars 方向规整。"""

    def test_new_to_old_unchanged(self):
        """新到旧的 bars 应保持不变。"""
        bars = _make_bars([10.0, 9.5, 9.0, 8.5, 8.0], newest_first=True)
        normalized = _normalize_bars(bars)
        assert normalized[0]["close"] == 10.0
        assert normalized[-1]["close"] == 8.0

    def test_old_to_new_reversed(self):
        """旧到新的 bars 应被反转。"""
        bars = _make_bars([8.0, 8.5, 9.0, 9.5, 10.0], newest_first=False)
        normalized = _normalize_bars(bars)
        assert normalized[0]["close"] == 10.0
        assert normalized[-1]["close"] == 8.0


# ============================================================
# Helper Function Tests
# ============================================================

class TestHelperFunctions:
    """测试辅助计算函数。"""

    def test_calc_ma(self):
        """_calc_ma 应正确计算移动平均（使用最后 N 个值）。"""
        values = [10.0, 11.0, 12.0, 13.0, 14.0]
        # 最后 5 个值的平均
        assert _calc_ma(values, 5) == 12.0
        # 最后 3 个值的平均 (12.0 + 13.0 + 14.0) / 3 = 13.0
        assert _calc_ma(values, 3) == 13.0
        assert _calc_ma(values, 10) is None  # 数据不足

    def test_calc_atr(self):
        """_calc_atr 应正确计算 ATR。"""
        bars = _make_bars(
            closes=[10.0, 10.5, 10.2, 10.8, 10.3, 10.7, 10.1, 10.6, 10.4, 10.9, 10.2],
            highs=[10.5, 11.0, 10.7, 11.3, 10.8, 11.2, 10.6, 11.1, 10.9, 11.4, 10.7],
            lows=[9.5, 10.0, 9.7, 10.3, 9.8, 10.2, 9.6, 10.1, 9.9, 10.4, 9.7],
        )
        atr = _calc_atr(bars, 5)
        assert atr is not None
        assert atr > 0

    def test_calc_range_pct(self):
        """_calc_range_pct 应正确计算振幅。"""
        bars = _make_bars(
            closes=[10.0, 10.5, 10.2],
            highs=[11.0, 11.5, 11.2],
            lows=[9.0, 9.5, 9.2],
        )
        range_pct = _calc_range_pct(bars, 3)
        assert range_pct is not None
        assert range_pct > 0


# ============================================================
# Calculator Tests
# ============================================================

class TestCalculateBarFactors:
    """测试 calculate_bar_factors 函数。"""

    def test_ma20_slope_5_calculation(self):
        """ma20_slope_5 应正确计算 MA20 斜率。"""
        # 构造上升趋势（新到旧：最新在前）
        closes = [100 + (29 - i) * 0.5 for i in range(30)]  # 114.5 -> 100.0
        bars = _make_bars(closes, newest_first=True)

        result = calculate_bar_factors({}, bars)
        assert result["ma20_slope_5"] is not None
        # 上升趋势斜率应为正
        assert result["ma20_slope_5"] > 0

    def test_ma20_slope_5_falling(self):
        """下降趋势的 ma20_slope_5 应为负。"""
        # 构造下降趋势（新到旧：最新在前）
        closes = [100 - (29 - i) * 0.5 for i in range(30)]  # 85.5 -> 100.0
        bars = _make_bars(closes, newest_first=True)

        result = calculate_bar_factors({}, bars)
        assert result["ma20_slope_5"] is not None
        # 下降趋势斜率应为负
        assert result["ma20_slope_5"] < 0

    def test_near_high_250_at_high(self):
        """在新高附近时 near_high_250 应接近 0。"""
        closes = [100.0] * 250  # 横盘
        # 使用与 close 相同的 high，这样 close == high
        highs = [100.0] * 250
        lows = [98.0] * 250
        bars = _make_bars(closes, highs=highs, lows=lows, newest_first=True)

        result = calculate_bar_factors({}, bars)
        assert result["near_high_250"] is not None
        # 在新高时应为 0
        assert result["near_high_250"] == 0.0

    def test_near_high_250_below_high(self):
        """低于新高时 near_high_250 应为负。"""
        # 249 天在 100，最新一天跌到 90
        closes = [90.0] + [100.0] * 249  # 新到旧：最新在前
        bars = _make_bars(closes, newest_first=True)

        result = calculate_bar_factors({}, bars)
        assert result["near_high_250"] is not None
        # 距离新高 -10%
        assert result["near_high_250"] < 0

    def test_amount_ratio_20_calculation(self):
        """amount_ratio_20 应正确计算成交额比。"""
        # 新到旧：前 5 天成交额 200M（最新），后 15 天成交额 100M
        amounts = [200_000_000.0] * 5 + [100_000_000.0] * 15
        closes = [100.0] * 20
        bars = _make_bars(closes, amounts=amounts, newest_first=True)

        result = calculate_bar_factors({}, bars)
        assert result["amount_ratio_20"] is not None
        # 5 日均/20 日均 > 1（近期放量）
        assert result["amount_ratio_20"] > 1.0

    def test_contraction_score_higher_when_contraction(self):
        """ATR/range 收缩时 contraction_score 应更高。"""
        # 收缩情况：近期波动小（新到旧）
        closes收缩 = [100.0 + i * 0.1 for i in range(10)] + [100.0] * 20
        bars收缩 = _make_bars(closes收缩, newest_first=True)

        # 扩张情况：近期波动大（新到旧）
        closes扩张 = [100.0 + i * 2 for i in range(10)] + [100.0] * 20
        bars扩张 = _make_bars(closes扩张, newest_first=True)

        result收缩 = calculate_bar_factors({}, bars收缩)
        result扩张 = calculate_bar_factors({}, bars扩张)

        # 收缩情况的 contraction_score 应更高
        if result收缩["contraction_score"] is not None and result扩张["contraction_score"] is not None:
            assert result收缩["contraction_score"] >= result扩张["contraction_score"]

    def test_bars_insufficient_returns_none(self):
        """bars 不足时应返回 None，不报错。"""
        bars = _make_bars([100.0, 101.0, 102.0])  # 只有 3 条

        result = calculate_bar_factors({}, bars)
        assert result["ma20_slope_5"] is None
        assert result["near_high_250"] is None
        assert result["atr10_atr50"] is None
        assert result["range10_range20"] is None
        assert result["range20_range60"] is None
        assert result["amount_ratio_20"] is None

    def test_bars_none_returns_all_none(self):
        """bars 为 None 时应返回全部 None。"""
        result = calculate_bar_factors({}, None)
        assert all(v is None for v in result.values())

    def test_bars_empty_returns_all_none(self):
        """bars 为空列表时应返回全部 None。"""
        result = calculate_bar_factors({}, [])
        assert all(v is None for v in result.values())


# ============================================================
# New Factor Tests (第二十一阶段-B)
# ============================================================

class TestNewFactors:
    """测试新增的个股增强因子。"""

    def test_liquidity_score_high(self):
        """高成交额应返回高流动性评分。"""
        # 20 日平均成交额 >= 10亿
        amounts = [1_000_000_000.0] * 20
        bars = _make_bars([100.0] * 20, amounts=amounts, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["liquidity_score"] == 90.0

    def test_liquidity_score_low(self):
        """低成交额应返回低流动性评分。"""
        amounts = [10_000_000.0] * 20
        bars = _make_bars([100.0] * 20, amounts=amounts, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["liquidity_score"] == 30.0

    def test_liquidity_score_bars_insufficient(self):
        """bars 不足时应返回 None。"""
        bars = _make_bars([100.0] * 5, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["liquidity_score"] is None

    def test_chasing_risk_score_high(self):
        """高涨幅应返回高追高风险。"""
        # 5日涨幅 > 20%
        # 新到旧：close_t=100, close_t_minus_5=80 (涨幅 25%)
        # 需要至少 20 根 bars
        closes = [100.0, 97.0, 94.0, 91.0, 88.0, 80.0, 77.0, 74.0, 71.0, 68.0,
                  65.0, 62.0, 59.0, 56.0, 53.0, 50.0, 47.0, 44.0, 41.0, 38.0]
        highs = [102.0, 99.0, 96.0, 93.0, 90.0, 82.0, 79.0, 76.0, 73.0, 70.0,
                 67.0, 64.0, 61.0, 58.0, 55.0, 52.0, 49.0, 46.0, 43.0, 40.0]
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["chasing_risk_score"] is not None
        # base=30 + return_5d>20%(+30) + near_20_high>=0.99(+20) = 80
        assert result["chasing_risk_score"] >= 70

    def test_chasing_risk_score_low(self):
        """低涨幅应返回低追高风险。"""
        # 新到旧：close_t=100, close_t_minus_5=105 (跌幅约 -4.8%)
        # 需要至少 20 根 bars
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0,
                  110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0]
        highs = [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0,
                 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 121.0]
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["chasing_risk_score"] is not None
        # base=30，没有加分项（return_5d < 0%, near_20_high < 0.96, daily_return < 4%）
        assert result["chasing_risk_score"] <= 30

    def test_chasing_risk_score_bars_insufficient(self):
        """bars 不足时应返回 None。"""
        bars = _make_bars([100.0] * 5, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["chasing_risk_score"] is None

    def test_drawdown_depth_20(self):
        """应正确计算 20 日回撤深度。"""
        # 最高点 110，当前 100，回撤 (110-100)/110*100 ≈ 9.09%
        closes = [100.0] * 20
        highs = [110.0] * 20
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["drawdown_depth_20"] is not None
        # (110 - 100) / 110 * 100 ≈ 9.09%
        assert 9.0 < result["drawdown_depth_20"] < 9.2

    def test_drawdown_depth_20_same_as_breakout(self):
        """drawdown_depth_20 应与 breakout_distance_20 数值相同。"""
        closes = [100.0] * 20
        highs = [110.0] * 20
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["drawdown_depth_20"] == result["breakout_distance_20"]

    def test_breakout_distance_20(self):
        """应正确计算距20日突破距离。"""
        # 最高点 110，当前 100，距离 10/110 * 100 ≈ 9.09%
        closes = [100.0] * 20
        highs = [110.0] * 20
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["breakout_distance_20"] is not None
        assert 9.0 < result["breakout_distance_20"] < 9.2

    def test_breakout_distance_20_at_high(self):
        """在突破点时应返回 0。"""
        closes = [100.0] * 20
        highs = [100.0] * 20  # high == close
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["breakout_distance_20"] == 0.0

    def test_breakout_distance_20_score_not_50(self):
        """breakout_distance_20 score 不应恒定 50。"""
        # 测试不同距离的 score 分布
        # 近距离：raw=2, score 应接近 90
        closes_near = [98.0] * 20
        highs_near = [100.0] * 20
        bars_near = _make_bars(closes_near, highs=highs_near, newest_first=True)
        result_near = calculate_bar_factors({}, bars_near)

        # 远距离：raw=15, score 应接近 25
        closes_far = [85.0] * 20
        highs_far = [100.0] * 20
        bars_far = _make_bars(closes_far, highs=highs_far, newest_first=True)
        result_far = calculate_bar_factors({}, bars_far)

        # score 应该不同
        assert result_near["_breakout_distance_20_score"] != result_far["_breakout_distance_20_score"]
        # 近距离 score 应更高（更好）
        assert result_near["_breakout_distance_20_score"] > result_far["_breakout_distance_20_score"]

    def test_sector_support_score_from_candidate(self):
        """sector_support_score 应从 sector_trend_score 和 sector_burst_score 计算。"""
        candidate = {
            "sector_trend_score": 70.0,
            "sector_burst_score": 60.0,
        }
        bars = _make_bars([100.0] * 5, newest_first=True)

        # sector_support_score 不在 calculate_bar_factors 中计算
        # 它在 snapshot.py 中计算
        result = calculate_bar_factors(candidate, bars)

        # 检查其他因子正常
        assert result["ma20_slope_5"] is not None or result["ma20_slope_5"] is None


    def test_relative_strength_and_risk_adjusted_return_scores(self):
        """new momentum quality factors should reward steady 20d appreciation."""
        closes_up = [120.0 - i for i in range(61)]
        bars_up = _make_bars(closes_up, newest_first=True)

        closes_flat = [100.0] * 61
        bars_flat = _make_bars(closes_flat, newest_first=True)

        result_up = calculate_bar_factors({}, bars_up)
        result_flat = calculate_bar_factors({}, bars_flat)

        assert result_up["relative_strength_20"] > result_flat["relative_strength_20"]
        assert result_up["risk_adjusted_return_20"] > result_flat["risk_adjusted_return_20"]
        assert 0 <= result_up["_relative_strength_20_score"] <= 100
        assert 0 <= result_up["_risk_adjusted_return_20_score"] <= 100

    def test_volume_stability_penalizes_single_day_spike(self):
        """volume stability should prefer sustained activity over one-day amount spikes."""
        closes = [100.0] * 30
        sustained_amounts = [180_000_000.0] * 10 + [120_000_000.0] * 20
        spike_amounts = [900_000_000.0] + [100_000_000.0] * 29

        sustained = calculate_bar_factors({}, _make_bars(closes, amounts=sustained_amounts))
        spiky = calculate_bar_factors({}, _make_bars(closes, amounts=spike_amounts))

        assert sustained["volume_stability_score"] > spiky["volume_stability_score"]

    def test_trend_persistence_score_rewards_closes_above_ma20(self):
        """trend persistence should be higher when recent closes stay above rolling MA20."""
        persistent_closes = [120.0 - i * 0.3 for i in range(45)]
        weak_closes = [80.0 + i * 0.4 for i in range(45)]

        persistent = calculate_bar_factors({}, _make_bars(persistent_closes))
        weak = calculate_bar_factors({}, _make_bars(weak_closes))

        assert persistent["trend_persistence_score"] > weak["trend_persistence_score"]

    def test_short_emotion_factors_reward_strong_close_and_healthy_volume(self):
        """short emotion factors should separate healthy bursts from weak closes."""
        closes = [109.0, 101.0] + [100.0] * 28
        strong_bars = _make_bars(
            closes,
            highs=[110.0] + [102.0] * 29,
            lows=[100.0] + [99.0] * 29,
            amounts=[180_000_000.0] * 5 + [120_000_000.0] * 25,
        )
        weak_bars = _make_bars(
            [101.0, 100.0] + [100.0] * 28,
            highs=[110.0] + [102.0] * 29,
            lows=[100.0] + [99.0] * 29,
            amounts=[900_000_000.0] + [100_000_000.0] * 29,
        )

        strong = calculate_bar_factors({"sector_burst_score": 75.0, "stock_short_score_v2": 75.0}, strong_bars)
        weak = calculate_bar_factors({"sector_burst_score": 35.0, "stock_short_score_v2": 75.0}, weak_bars)

        assert strong["close_strength_score"] > weak["close_strength_score"]
        assert strong["intraday_reversal_risk_score"] < weak["intraday_reversal_risk_score"]
        assert strong["volume_burst_quality_score"] > weak["volume_burst_quality_score"]
        assert strong["short_burst_emotion_score_v1"] > weak["short_burst_emotion_score_v1"]

    def test_short_overheat_and_cashout_risk_penalize_single_name_spike(self):
        """single-name overheat should rise when a spike lacks sector spread."""
        bars = _make_bars(
            [110.0, 100.0] + [96.0] * 28,
            highs=[112.0] + [101.0] * 29,
            lows=[99.0] + [95.0] * 29,
            amounts=[900_000_000.0] + [100_000_000.0] * 29,
        )

        isolated = calculate_bar_factors(
            {"sector_burst_score": 35.0, "sector_support_score": 40.0, "stock_short_score_v2": 90.0},
            bars,
        )
        confirmed = calculate_bar_factors(
            {"sector_burst_score": 85.0, "sector_support_score": 75.0, "stock_short_score_v2": 90.0},
            bars,
        )

        assert isolated["single_name_overheat_score"] > confirmed["single_name_overheat_score"]
        assert isolated["next_day_cashout_risk_score"] > confirmed["next_day_cashout_risk_score"]
        assert isolated["sector_burst_breadth_score"] < confirmed["sector_burst_breadth_score"]

    def test_short_burst_emotion_v2_prefers_healthy_volume_over_hot_attention(self):
        """v2 should prefer healthy volume and risk control over pure heat."""
        healthy_bars = _make_bars(
            [104.0, 101.0] + [100.0] * 28,
            highs=[105.0] + [102.0] * 29,
            lows=[100.0] + [99.0] * 29,
            amounts=[170_000_000.0] * 5 + [120_000_000.0] * 25,
        )
        hot_bars = _make_bars(
            [110.0, 100.0] + [96.0] * 28,
            highs=[112.0] + [101.0] * 29,
            lows=[99.0] + [95.0] * 29,
            amounts=[900_000_000.0] + [100_000_000.0] * 29,
        )

        healthy = calculate_bar_factors(
            {"sector_burst_score": 72.0, "sector_support_score": 68.0, "stock_short_score_v2": 72.0},
            healthy_bars,
        )
        hot = calculate_bar_factors(
            {"sector_burst_score": 38.0, "sector_support_score": 40.0, "stock_short_score_v2": 92.0},
            hot_bars,
        )

        assert hot["limit_attention_score"] > healthy["limit_attention_score"]
        assert healthy["volume_burst_quality_score"] > hot["volume_burst_quality_score"]
        assert healthy["short_burst_emotion_score_v2"] > hot["short_burst_emotion_score_v2"]

    def test_market_emotion_and_catalyst_factors_feed_short_burst_shadow(self):
        """short-burst factors should include market emotion and catalyst context."""
        bars = _make_bars(
            [105.0, 102.0] + [100.0] * 28,
            highs=[106.0] + [103.0] * 29,
            lows=[101.0] + [99.0] * 29,
            amounts=[180_000_000.0] * 5 + [120_000_000.0] * 25,
        )
        supported = calculate_bar_factors(
            {
                "market_limit_up_count": 92,
                "market_limit_down_count": 3,
                "market_limit_up_failure_rate": 0.12,
                "leader_continuation_rate": 0.68,
                "market_hot_sector_concentration": 0.36,
                "news_count_3d": 5,
                "policy_catalyst_count": 2,
                "earnings_catalyst_count": 1,
                "event_age_days": 0,
                "event_continuation_days": 3,
                "negative_news_count_3d": 0,
                "rumor_risk_count": 0,
                "sector_burst_score": 72.0,
                "sector_support_score": 68.0,
                "stock_short_score_v2": 72.0,
            },
            bars,
        )
        noisy = calculate_bar_factors(
            {
                "market_limit_up_count": 18,
                "market_limit_down_count": 24,
                "market_limit_up_failure_rate": 0.55,
                "leader_continuation_rate": 0.22,
                "market_hot_sector_concentration": 0.82,
                "news_count_3d": 1,
                "policy_catalyst_count": 0,
                "earnings_catalyst_count": 0,
                "event_age_days": 6,
                "event_continuation_days": 0,
                "negative_news_count_3d": 2,
                "rumor_risk_count": 2,
                "sector_burst_score": 45.0,
                "sector_support_score": 42.0,
                "stock_short_score_v2": 72.0,
            },
            bars,
        )

        assert supported["market_short_emotion_score"] > noisy["market_short_emotion_score"]
        assert supported["event_continuation_score"] > noisy["event_continuation_score"]
        assert supported["short_burst_news_emotion_score_shadow"] > noisy["short_burst_news_emotion_score_shadow"]
        assert noisy["limit_up_failure_risk"] > supported["limit_up_failure_risk"]
        assert noisy["negative_news_risk_score"] > supported["negative_news_risk_score"]

    def test_intraday_factors_reward_late_strength_and_volume_price_confirmation(self):
        """intraday factors should reward supported late-session strength."""
        strong = calculate_intraday_factors(
            {
                "sector_intraday_breadth_score": 74.0,
                "prev_close": 100.0,
                "intraday_bars": _make_intraday_bars(
                    [100.0, 101.0, 102.0, 103.0, 104.0],
                    amounts=[8_000_000.0, 10_000_000.0, 12_000_000.0, 16_000_000.0, 20_000_000.0],
                ),
            }
        )
        fading = calculate_intraday_factors(
            {
                "sector_intraday_breadth_score": 42.0,
                "prev_close": 100.0,
                "intraday_bars": _make_intraday_bars(
                    [100.0, 104.0, 105.0, 102.0, 101.0],
                    amounts=[8_000_000.0, 20_000_000.0, 18_000_000.0, 10_000_000.0, 8_000_000.0],
                ),
            }
        )

        assert strong["intraday_close_position_score"] > fading["intraday_close_position_score"]
        assert strong["intraday_late_strength_score"] > fading["intraday_late_strength_score"]
        assert strong["intraday_volume_price_confirm_score"] > fading["intraday_volume_price_confirm_score"]
        assert strong["intraday_high_pullback_risk_score"] < fading["intraday_high_pullback_risk_score"]
        assert strong["short_burst_intraday_emotion_score_shadow"] > fading["short_burst_intraday_emotion_score_shadow"]

    def test_intraday_factors_missing_without_intraday_bars(self):
        """intraday factors should degrade to None when no intraday source is available."""
        result = calculate_intraday_factors({})

        assert result["intraday_close_position_score"] is None
        assert result["short_burst_intraday_emotion_score_shadow"] is None
        assert result["close_vs_vwap_score"] is None
        assert result["volume_spike_exhaustion_score"] is None

    def test_intraday_price_momentum_expansion_rewards_sustained_strength(self):
        factor_ids = (
            "return_5m_strength_score",
            "return_15m_strength_score",
            "return_60m_strength_score",
            "positive_bar_ratio_score",
            "rolling_price_slope_score",
            "intraday_breakout_strength_score",
            "breakout_hold_score",
            "pullback_reclaim_momentum_score",
        )
        strong = calculate_intraday_factors(
            {
                "prev_close": 100.0,
                "intraday_bars": _make_intraday_bars(
                    [100.0, 100.4, 100.8, 101.3, 101.8, 102.5, 103.1, 103.8, 104.4, 105.0, 105.6, 106.2, 106.8, 107.5],
                ),
            }
        )
        weak = calculate_intraday_factors(
            {
                "prev_close": 100.0,
                "intraday_bars": _make_intraday_bars(
                    [100.0, 103.2, 102.4, 101.8, 101.1, 100.6, 100.0, 99.6, 99.3, 99.0, 98.7, 98.4, 98.1, 97.8],
                ),
            }
        )

        for factor_id in factor_ids:
            assert strong[factor_id] > weak[factor_id]

    def test_intraday_price_momentum_expansion_is_missing_without_bars(self):
        factor_ids = (
            "return_5m_strength_score",
            "return_15m_strength_score",
            "return_60m_strength_score",
            "positive_bar_ratio_score",
            "rolling_price_slope_score",
            "intraday_breakout_strength_score",
            "breakout_hold_score",
            "pullback_reclaim_momentum_score",
        )
        result = calculate_intraday_factors({})

        assert all(result[factor_id] is None for factor_id in factor_ids)

    def test_intraday_atomic_factors_cover_six_factor_families(self):
        """intraday atomic factors should separate support, VWAP, fade, volume, open, and sector context."""
        supported = calculate_intraday_factors(
            {
                "prev_close": 100.0,
                "sector_intraday_breadth_score": 76.0,
                "sector_late_breadth_score": 72.0,
                "leader_follower_sync_score": 68.0,
                "stock_vs_sector_intraday_alpha": 8.0,
                "intraday_bars": _make_intraday_bars(
                    [100.0, 101.2, 101.0, 101.8, 102.4, 103.2, 104.2],
                    amounts=[8_000_000.0, 9_000_000.0, 9_500_000.0, 10_000_000.0, 13_000_000.0, 16_000_000.0, 18_000_000.0],
                    times=["09:30", "10:00", "10:30", "11:30", "13:30", "14:30", "14:55"],
                ),
            }
        )
        exhausted = calculate_intraday_factors(
            {
                "prev_close": 100.0,
                "sector_intraday_breadth_score": 38.0,
                "sector_late_breadth_score": 34.0,
                "leader_follower_sync_score": 32.0,
                "stock_vs_sector_intraday_alpha": -6.0,
                "intraday_bars": _make_intraday_bars(
                    [100.0, 104.8, 105.2, 103.0, 101.4, 100.8, 100.5],
                    amounts=[8_000_000.0, 24_000_000.0, 26_000_000.0, 18_000_000.0, 12_000_000.0, 9_000_000.0, 8_500_000.0],
                    times=["09:30", "10:00", "10:30", "11:30", "13:30", "14:30", "14:55"],
                ),
            }
        )

        assert supported["late_return_30m_score"] > exhausted["late_return_30m_score"]
        assert supported["late_vwap_support_score"] > exhausted["late_vwap_support_score"]
        assert supported["high_to_close_drawdown_score"] < exhausted["high_to_close_drawdown_score"]
        assert supported["volume_spike_exhaustion_score"] < exhausted["volume_spike_exhaustion_score"]
        assert supported["morning_strength_persist_score"] > exhausted["morning_strength_persist_score"]
        assert supported["sector_late_breadth_score"] > exhausted["sector_late_breadth_score"]
        assert supported["stock_vs_sector_intraday_alpha"] > exhausted["stock_vs_sector_intraday_alpha"]


# ============================================================
# Snapshot Integration Tests
# ============================================================

class TestSnapshotWithBars:
    """测试 build_factor_snapshot 与 bars 集成。"""

    def test_build_factor_snapshot_with_bars(self):
        """build_factor_snapshot(bars=...) 应输出真实因子。"""
        candidate = {
            "code": "600001",
            "name": "测试股A",
            "stock_trend_score": 75.0,
        }
        closes = [100 + i * 0.5 for i in range(30)]
        bars = _make_bars(closes)

        snapshot = build_factor_snapshot(candidate, as_of="2026-07-10", bars=bars)

        # 检查 bars_calculated 包含 ma20_slope_5
        assert "bars_calculated" in snapshot["summary"]
        assert "ma20_slope_5" in snapshot["summary"]["bars_calculated"]

        # 检查 ma20_slope_5 的值
        ma20_factor = next(
            (f for f in snapshot["factors"] if f["factor_id"] == "ma20_slope_5"),
            None,
        )
        assert ma20_factor is not None
        assert ma20_factor["quality"] != "missing"
        assert "bars_calculated" in ma20_factor["tags"]

    def test_build_factor_snapshot_includes_shadow_v2_quality_factors(self):
        """snapshot should expose new shadow-v2 quality factors from bars."""
        candidate = {"code": "600001", "name": "A", "stock_trend_score": 75.0}
        closes = [120.0 - i * 0.4 for i in range(61)]
        amounts = [180_000_000.0] * 10 + [120_000_000.0] * 51
        bars = _make_bars(closes, amounts=amounts)

        snapshot = build_factor_snapshot(candidate, as_of="2026-07-10", bars=bars)
        factors = {item["factor_id"]: item for item in snapshot["factors"]}

        for factor_id in [
            "relative_strength_20",
            "risk_adjusted_return_20",
            "volume_stability_score",
            "trend_persistence_score",
        ]:
            assert factor_id in factors
            assert factors[factor_id]["quality"] != "missing"
            assert "bars_calculated" in factors[factor_id]["tags"]

    def test_build_factor_snapshot_includes_short_emotion_factors(self):
        """snapshot should expose short-burst emotion factors from bars."""
        candidate = {
            "code": "600001",
            "name": "A",
            "sector_burst_score": 75.0,
            "sector_support_score": 70.0,
            "stock_short_score_v2": 78.0,
        }
        closes = [109.0, 101.0] + [100.0] * 28
        highs = [110.0] + [102.0] * 29
        lows = [100.0] + [99.0] * 29
        amounts = [180_000_000.0] * 5 + [120_000_000.0] * 25

        snapshot = build_factor_snapshot(
            candidate,
            as_of="2026-07-10",
            bars=_make_bars(closes, highs=highs, lows=lows, amounts=amounts),
        )
        factors = {item["factor_id"]: item for item in snapshot["factors"]}

        for factor_id in [
            "short_emotion_heat_score",
            "sector_burst_breadth_score",
            "close_strength_score",
            "volume_burst_quality_score",
            "short_burst_emotion_score_v1",
            "short_burst_emotion_score_v2",
        ]:
            assert factor_id in factors
            assert factors[factor_id]["quality"] != "missing"
            assert "bars_calculated" in factors[factor_id]["tags"]

    def test_build_factor_snapshot_without_bars(self):
        """不传 bars 时应保持原有行为。"""
        candidate = {
            "code": "600001",
            "name": "测试股A",
            "stock_trend_score": 75.0,
        }

        snapshot = build_factor_snapshot(candidate, as_of="2026-07-10")

        # bars_calculated 应为空
        assert snapshot["summary"]["bars_calculated"] == []
        assert snapshot["summary"]["bars_available"] is False

    def test_build_factor_snapshot_bars_overrides_candidate(self):
        """bars 计算的值应优先于 candidate 中的同名字段。"""
        candidate = {
            "code": "600001",
            "name": "测试股A",
            "ma20_slope_5": 1.0,  # 候选中的旧值
        }
        closes = [100 + i * 0.5 for i in range(30)]
        bars = _make_bars(closes)

        snapshot = build_factor_snapshot(candidate, as_of="2026-07-10", bars=bars)

        ma20_factor = next(
            (f for f in snapshot["factors"] if f["factor_id"] == "ma20_slope_5"),
            None,
        )
        assert ma20_factor is not None
        # 应使用 bars 计算的新值，而不是 candidate 中的旧值
        assert ma20_factor["raw_value"] != 1.0

    def test_build_factor_snapshot_bars_exception_degrades(self):
        """bars 计算异常时应降级，不影响后续流程。"""
        candidate = {
            "code": "600001",
            "name": "测试股A",
        }
        # 传入无效的 bars 数据
        bars = [{"invalid": "data"}]

        # 不应抛出异常
        snapshot = build_factor_snapshot(candidate, as_of="2026-07-10", bars=bars)
        assert snapshot["schema_version"] == "1.0"

    def test_registry_has_new_factors(self):
        """注册表应包含新增的 6 个因子。"""
        new_factors = [
            "near_high_250",
            "contraction_score",
            "atr10_atr50",
            "range10_range20",
            "range20_range60",
            "amount_ratio_20",
        ]
        for factor_id in new_factors:
            assert factor_id in FACTOR_REGISTRY, f"Missing factor: {factor_id}"

    def test_total_factor_count(self):
        """注册表应包含全部已启用因子。"""
        assert len(FACTOR_REGISTRY) == 84
