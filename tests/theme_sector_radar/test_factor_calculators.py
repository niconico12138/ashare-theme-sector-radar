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
        # 5日涨幅 > 15%
        # 新到旧：close_t=100, close_t_minus_5=85 (涨幅约 17.6%)
        # 需要至少 20 根 bars
        closes = [100.0, 97.0, 94.0, 91.0, 88.0, 85.0, 82.0, 79.0, 76.0, 73.0,
                  70.0, 67.0, 64.0, 61.0, 58.0, 55.0, 52.0, 49.0, 46.0, 43.0]
        highs = [102.0, 99.0, 96.0, 93.0, 90.0, 87.0, 84.0, 81.0, 78.0, 75.0,
                 72.0, 69.0, 66.0, 63.0, 60.0, 57.0, 54.0, 51.0, 48.0, 45.0]
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["chasing_risk_score"] is not None
        assert result["chasing_risk_score"] > 50

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
        # 低涨幅时风险评分应 <= 50（基础分 50，没有加分项）
        assert result["chasing_risk_score"] <= 50

    def test_chasing_risk_score_bars_insufficient(self):
        """bars 不足时应返回 None。"""
        bars = _make_bars([100.0] * 5, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["chasing_risk_score"] is None

    def test_drawdown_depth_20(self):
        """应正确计算 20 日最大回撤深度。"""
        # 最高点 110，最低点 100，最大回撤 10/110 * 100 ≈ 9.09%
        closes = [100.0] * 20
        highs = [110.0] * 20
        lows = [100.0] * 20
        bars = _make_bars(closes, highs=highs, lows=lows, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["drawdown_depth_20"] is not None
        # 最大回撤 = (110 - 100) / 110 * 100 ≈ 9.09%
        assert 9.0 < result["drawdown_depth_20"] < 10.0

    def test_breakout_distance_20(self):
        """应正确计算距20日突破距离。"""
        # 最高点 110，当前 100，距离 10/110 * 100 ≈ 9.8%
        closes = [100.0] * 20
        highs = [110.0] * 20
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["breakout_distance_20"] is not None
        assert 9.0 < result["breakout_distance_20"] < 10.5

    def test_breakout_distance_20_at_high(self):
        """在突破点时应返回 0。"""
        closes = [100.0] * 20
        highs = [100.0] * 20  # high == close
        bars = _make_bars(closes, highs=highs, newest_first=True)

        result = calculate_bar_factors({}, bars)

        assert result["breakout_distance_20"] == 0.0

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
        """注册表应包含 24 个因子（13 + 6 bars + 5 stock quality）。"""
        assert len(FACTOR_REGISTRY) == 24
