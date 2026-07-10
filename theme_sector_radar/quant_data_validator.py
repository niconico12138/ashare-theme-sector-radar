"""
量化打分数据核查模块

在量化评分前校验数据的完整性和准确性，确保每个因子都有可靠的数据支撑。

核查项：
1. K线数据：日期连续性、价格合理性、成交量非零
2. 行情数据：PE/PB/市值范围合理性
3. 资金流数据：金额范围、方向一致性
4. 板块数据：趋势分/短线分范围
5. 数据新鲜度：K线是否覆盖到目标日期
"""

import math
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 数据范围常量
# ============================================================

# A股涨跌停限制（普通股 ±10%，科创/创业 ±20%）
MAX_DAILY_CHANGE_PCT = 20.0
MIN_DAILY_CHANGE_PCT = -20.0

# PE 合理范围
PE_MIN = 0.01
PE_MAX = 2000.0  # 亏损股 PE 为负，但极高 PE 需标记

# PB 合理范围
PB_MIN = 0.01
PB_MAX = 100.0

# 市值范围（亿元）
MV_MIN = 1.0       # 最小壳股
MV_MAX = 50000.0   # 工商银行级别

# 成交额范围（元）
AMOUNT_MIN = 1e5   # 10万（极低流动性）
AMOUNT_MAX = 1e12  # 1万亿（单日天量）

# 价格范围
PRICE_MIN = 0.01
PRICE_MAX = 5000.0  # 茅台级别

# 板块评分范围
SECTOR_SCORE_MIN = 0.0
SECTOR_SCORE_MAX = 100.0

# 资金流范围（元）
FUND_FLOW_ABS_MAX = 1e12  # 单股单日资金流不超过1万亿


# ============================================================
# 验证结果
# ============================================================

class ValidationResult:
    """单个数据项的验证结果"""

    def __init__(self, field: str, value: Any, status: str, message: str = ""):
        self.field = field
        self.value = value
        self.status = status  # "ok", "warning", "error", "missing"
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "status": self.status,
            "message": self.message,
        }

    def __repr__(self):
        return f"ValidationResult({self.field}, {self.status}, {self.message})"


class StockDataQualityReport:
    """单只股票的数据质量报告"""

    def __init__(self, code: str):
        self.code = code
        self.results: List[ValidationResult] = []
        self.available_factors: List[str] = []
        self.missing_factors: List[str] = []
        self.degraded_factors: List[str] = []

    def add(self, field: str, value: Any, status: str, message: str = ""):
        self.results.append(ValidationResult(field, value, status, message))

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.status == "warning")

    @property
    def missing_count(self) -> int:
        return sum(1 for r in self.results if r.status == "missing")

    @property
    def quality_score(self) -> float:
        """数据质量分 0~100"""
        if not self.results:
            return 0.0
        ok_count = sum(1 for r in self.results if r.status == "ok")
        return round(ok_count / len(self.results) * 100, 1)

    @property
    def factor_coverage(self) -> float:
        """因子覆盖率 0~1"""
        total = len(self.available_factors) + len(self.missing_factors) + len(self.degraded_factors)
        if total == 0:
            return 0.0
        return round(len(self.available_factors) / total, 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "quality_score": self.quality_score,
            "factor_coverage": self.factor_coverage,
            "available_factors": self.available_factors,
            "missing_factors": self.missing_factors,
            "degraded_factors": self.degraded_factors,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "missing_count": self.missing_count,
            "details": [r.to_dict() for r in self.results],
        }

    def summary_line(self) -> str:
        """一行摘要"""
        return (
            f"{self.code}: 质量={self.quality_score:.0f} "
            f"因子={len(self.available_factors)}/{len(self.available_factors)+len(self.missing_factors)} "
            f"覆盖={self.factor_coverage:.0%} "
            f"错误={self.error_count} 警告={self.warning_count}"
        )


# ============================================================
# 验证函数
# ============================================================

def _is_valid_number(v: Any) -> bool:
    """检查是否为有效数字（非 None/NaN/Inf）"""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return not (math.isnan(v) or math.isinf(v))
    return False


def _check_range(value: float, min_val: float, max_val: float, field: str, report: StockDataQualityReport):
    """检查数值是否在合理范围内"""
    if not _is_valid_number(value):
        report.add(field, value, "missing", f"{field} 为空或无效")
        return
    if value < min_val or value > max_val:
        report.add(field, value, "warning", f"{field}={value} 超出范围 [{min_val}, {max_val}]")
    else:
        report.add(field, value, "ok")


def validate_stock_bars(code: str, bars: List[Dict], as_of_date: Optional[str] = None) -> StockDataQualityReport:
    """
    校验 K 线数据的完整性和准确性

    核查项：
    - 数据条数是否足够（≥5天）
    - 日期是否连续（无缺失交易日）
    - 收盘价是否在合理范围
    - 成交量是否非零
    - 是否覆盖到目标日期

    Args:
        code: 股票代码
        bars: K 线数据列表
        as_of_date: 目标日期

    Returns:
        StockDataQualityReport
    """
    report = StockDataQualityReport(code)

    # 1. 数据条数
    if not bars:
        report.add("bars_count", 0, "missing", "无 K 线数据")
        return report

    report.add("bars_count", len(bars), "ok" if len(bars) >= 5 else "warning",
               f"K 线 {len(bars)} 条" + (" (不足5天)" if len(bars) < 5 else ""))

    # 2. 日期覆盖
    if as_of_date and bars:
        last_date = bars[-1].get("date", "")
        if last_date:
            last_date_str = str(last_date)
            as_of_str = str(as_of_date)
            if last_date_str >= as_of_str:
                report.add("date_coverage", last_date_str, "ok", f"覆盖到 {last_date_str}")
            else:
                report.add("date_coverage", last_date_str, "warning",
                           f"最新日期 {last_date_str} < 目标 {as_of_str}")

    # 3. 日期连续性（检查是否有缺失）
    dates = [str(b.get("date", "")) for b in bars if b.get("date")]
    if len(dates) >= 2:
        gaps = []
        for i in range(1, len(dates)):
            d1 = dates[i - 1]
            d2 = dates[i]
            if d1 and d2:
                # 简单检查：如果日期差 > 5天，可能有缺失（排除节假日）
                try:
                    from datetime import datetime as dt
                    # 兼容 "2026-07-02" 和 "20260702" 两种格式
                    fmt = "%Y-%m-%d" if "-" in d1 else "%Y%m%d"
                    dt1 = dt.strptime(d1, fmt)
                    dt2 = dt.strptime(d2, fmt)
                    delta = (dt2 - dt1).days
                    if delta > 5:
                        gaps.append(f"{d1}~{d2}({delta}天)")
                except (ValueError, TypeError):
                    pass
        if gaps:
            report.add("date_continuity", len(gaps), "warning",
                       f"疑似缺失: {', '.join(gaps[:3])}")
        else:
            report.add("date_continuity", len(dates), "ok")

    # 4. 价格合理性
    closes = [b.get("close", 0) for b in bars if _is_valid_number(b.get("close"))]
    if closes:
        avg_price = sum(closes) / len(closes)
        _check_range(avg_price, PRICE_MIN, PRICE_MAX, "avg_price", report)

        # 检查价格异常跳变（单日涨跌 > 20%）
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                change = (closes[i] - closes[i - 1]) / closes[i - 1] * 100
                if abs(change) > MAX_DAILY_CHANGE_PCT + 2:  # 留2%容差
                    report.add("price_spike", change, "warning",
                               f"第{i}天涨跌幅 {change:.1f}% 异常")
                    break
        else:
            report.add("price_stability", len(closes), "ok", "价格无异常跳变")
    else:
        report.add("close_prices", 0, "missing", "无有效收盘价")

    # 5. 成交量
    amounts = [b.get("amount", 0) or 0 for b in bars]
    valid_amounts = [a for a in amounts if a > 0]
    if valid_amounts:
        avg_amount = sum(valid_amounts) / len(valid_amounts)
        _check_range(avg_amount, AMOUNT_MIN, AMOUNT_MAX, "avg_amount", report)
    else:
        report.add("amount", 0, "missing", "无成交额数据")

    return report


def validate_stock_quote(stock: Dict) -> StockDataQualityReport:
    """
    校验个股行情数据（PE/PB/市值/涨幅）

    Args:
        stock: 个股数据字典

    Returns:
        StockDataQualityReport
    """
    code = stock.get("code", "unknown")
    report = StockDataQualityReport(code)

    # 1. 涨幅
    change = stock.get("change_pct")
    if _is_valid_number(change):
        if abs(change) > MAX_DAILY_CHANGE_PCT + 2:
            report.add("change_pct", change, "warning", f"涨幅 {change:.1f}% 超限")
        else:
            report.add("change_pct", change, "ok")
    else:
        report.add("change_pct", None, "missing", "无涨幅数据")

    # 2. PE
    pe = stock.get("pe")
    if _is_valid_number(pe):
        if pe < 0:
            report.add("pe", pe, "warning", "PE 为负（亏损股）")
        elif pe > PE_MAX:
            report.add("pe", pe, "warning", f"PE={pe:.1f} 极高")
        else:
            report.add("pe", pe, "ok")
    else:
        report.add("pe", None, "missing", "无 PE 数据")

    # 3. PB
    pb = stock.get("pb")
    if _is_valid_number(pb):
        if pb < 0:
            report.add("pb", pb, "warning", "PB 为负")
        elif pb > PB_MAX:
            report.add("pb", pb, "warning", f"PB={pb:.1f} 极高")
        else:
            report.add("pb", pb, "ok")
    else:
        report.add("pb", None, "missing", "无 PB 数据")

    # 4. 市值
    mv = stock.get("total_mv")
    if _is_valid_number(mv):
        _check_range(mv, MV_MIN, MV_MAX, "total_mv", report)
    else:
        report.add("total_mv", None, "missing", "无市值数据")

    # 5. 股票代码格式
    code_str = str(code)
    if len(code_str) == 6 and code_str.isdigit():
        report.add("code_format", code_str, "ok")
    else:
        report.add("code_format", code_str, "warning", f"代码格式异常: {code_str}")

    return report


def validate_fund_flow(stock: Dict) -> StockDataQualityReport:
    """
    校验资金流数据

    Args:
        stock: 个股数据字典（含 _fund_flow）

    Returns:
        StockDataQualityReport
    """
    code = stock.get("code", "unknown")
    report = StockDataQualityReport(code)

    ff = stock.get("_fund_flow")
    if ff is None:
        report.add("fund_flow", None, "missing", "无资金流数据")
        return report

    if not isinstance(ff, dict):
        report.add("fund_flow", type(ff).__name__, "error", "资金流格式错误")
        return report

    # 检查 available 标记
    available = ff.get("available")
    if available is False:
        report.add("fund_flow_available", False, "warning", "资金流不可用")
        return report

    # 主力净流入
    main_inflow = ff.get("main_net_inflow")
    if _is_valid_number(main_inflow):
        _check_range(main_inflow, -FUND_FLOW_ABS_MAX, FUND_FLOW_ABS_MAX, "main_net_inflow", report)
    else:
        report.add("main_net_inflow", None, "missing", "无主力净流入数据")

    # 方向
    direction = ff.get("direction")
    if direction in ("inflow", "outflow", "neutral"):
        report.add("direction", direction, "ok")
    else:
        report.add("direction", direction, "warning", f"方向值异常: {direction}")

    return report


def validate_sector_data(stock: Dict) -> StockDataQualityReport:
    """
    校验板块关联数据

    Args:
        stock: 个股数据字典（含 sector_trend_score, sector_burst_score）

    Returns:
        StockDataQualityReport
    """
    code = stock.get("code", "unknown")
    report = StockDataQualityReport(code)

    # 板块趋势分
    trend = stock.get("sector_trend_score")
    if _is_valid_number(trend):
        _check_range(trend, SECTOR_SCORE_MIN, SECTOR_SCORE_MAX, "sector_trend_score", report)
    else:
        report.add("sector_trend_score", None, "missing", "无板块趋势分")

    # 板块短线分
    burst = stock.get("sector_burst_score")
    if _is_valid_number(burst):
        _check_range(burst, SECTOR_SCORE_MIN, SECTOR_SCORE_MAX, "sector_burst_score", report)
    else:
        report.add("sector_burst_score", None, "missing", "无板块短线分")

    # 板块名称
    sector_name = stock.get("sector_name")
    if sector_name and isinstance(sector_name, str) and len(sector_name) > 0:
        report.add("sector_name", sector_name, "ok")
    else:
        report.add("sector_name", None, "missing", "无板块名称")

    # 关联度
    relevance = stock.get("relevance_score")
    if _is_valid_number(relevance):
        _check_range(relevance, 0.0, 1.0, "relevance_score", report)
    else:
        report.add("relevance_score", None, "missing", "无关联度数据")

    return report


def validate_stock_full(
    stock: Dict,
    bars: Optional[List[Dict]] = None,
    as_of_date: Optional[str] = None,
) -> StockDataQualityReport:
    """
    完整校验一只股票的所有数据

    Args:
        stock: 个股数据字典
        bars: K 线数据（可选）
        as_of_date: 目标日期

    Returns:
        StockDataQualityReport（合并四项校验）
    """
    merged = StockDataQualityReport(stock.get("code", "unknown"))

    # 1. 行情数据
    quote_report = validate_stock_quote(stock)
    for r in quote_report.results:
        merged.results.append(r)

    # 2. K 线数据
    if bars:
        bars_report = validate_stock_bars(stock.get("code", ""), bars, as_of_date)
        for r in bars_report.results:
            merged.results.append(r)
    else:
        merged.add("bars", None, "missing", "未提供 K 线数据")

    # 3. 资金流
    ff_report = validate_fund_flow(stock)
    for r in ff_report.results:
        merged.results.append(r)

    # 4. 板块数据
    sector_report = validate_sector_data(stock)
    for r in sector_report.results:
        merged.results.append(r)

    # 5. 标记可用/缺失因子
    _classify_factors(merged, stock, bars)

    return merged


def _classify_factors(
    report: StockDataQualityReport,
    stock: Dict,
    bars: Optional[List[Dict]],
):
    """根据验证结果分类因子可用性"""

    # 动量质量因子
    has_change = _is_valid_number(stock.get("change_pct"))
    has_bars_5 = bars is not None and len(bars) >= 5
    has_bars_10 = bars is not None and len(bars) >= 10
    has_bars_20 = bars is not None and len(bars) >= 20

    if has_change:
        report.available_factors.append("1d_momentum")
    else:
        report.missing_factors.append("1d_momentum")

    if has_bars_5:
        report.available_factors.append("5d_momentum_quality")
        report.available_factors.append("continuity")
    else:
        report.degraded_factors.append("5d_momentum_quality")
        report.degraded_factors.append("continuity")

    if has_bars_20:
        report.available_factors.append("ma_alignment")
    else:
        report.degraded_factors.append("ma_alignment")

    # 估值因子
    has_pe = _is_valid_number(stock.get("pe")) and stock.get("pe", 0) > 0
    has_pb = _is_valid_number(stock.get("pb")) and stock.get("pb", 0) > 0
    has_sector_pe_median = _is_valid_number(stock.get("_sector_pe_median"))

    if has_pe:
        if has_sector_pe_median:
            report.available_factors.append("pe_relative")
        else:
            report.degraded_factors.append("pe_relative")
    else:
        report.missing_factors.append("pe_relative")

    if has_pb:
        report.available_factors.append("pb_score")
    else:
        report.missing_factors.append("pb_score")

    # 流动性因子
    has_mv = _is_valid_number(stock.get("total_mv"))
    if has_mv:
        report.available_factors.append("market_cap")
    else:
        report.missing_factors.append("market_cap")

    if has_bars_5:
        report.available_factors.append("volume_trend")
        report.available_factors.append("avg_amount")
    else:
        report.degraded_factors.append("volume_trend")
        report.degraded_factors.append("avg_amount")

    # 风控因子
    if has_bars_20:
        report.available_factors.append("drawdown")
        report.available_factors.append("volatility")
    else:
        report.degraded_factors.append("drawdown")
        report.degraded_factors.append("volatility")

    # 资金面因子
    ff = stock.get("_fund_flow")
    if ff and isinstance(ff, dict) and ff.get("available") is not False:
        if _is_valid_number(ff.get("main_net_inflow")):
            report.available_factors.append("fund_flow")
        else:
            report.missing_factors.append("fund_flow")
    else:
        report.missing_factors.append("fund_flow")

    # 板块匹配因子
    has_sector = _is_valid_number(stock.get("sector_trend_score"))
    if has_sector:
        report.available_factors.append("sector_match")
    else:
        report.missing_factors.append("sector_match")


def compute_data_quality_for_stocks(
    stocks: List[Dict],
    bars_cache: Optional[Dict[str, List[Dict]]] = None,
    as_of_date: Optional[str] = None,
) -> Dict[str, StockDataQualityReport]:
    """
    批量计算数据质量报告

    Args:
        stocks: 个股列表
        bars_cache: K 线缓存 {code: bars}
        as_of_date: 目标日期

    Returns:
        {code: StockDataQualityReport}
    """
    reports = {}
    for s in stocks:
        code = s.get("code", "")
        bars = bars_cache.get(code) if bars_cache else None
        reports[code] = validate_stock_full(s, bars, as_of_date)
    return reports


def print_data_quality_summary(reports: Dict[str, StockDataQualityReport]):
    """打印数据质量摘要"""
    if not reports:
        print("  无数据质量报告")
        return

    total = len(reports)
    avg_quality = sum(r.quality_score for r in reports.values()) / total
    avg_coverage = sum(r.factor_coverage for r in reports.values()) / total
    high_quality = sum(1 for r in reports.values() if r.quality_score >= 80)
    low_quality = sum(1 for r in reports.values() if r.quality_score < 50)

    print(f"\n  📊 数据质量摘要 ({total} 只)")
    print(f"     平均质量分: {avg_quality:.1f}")
    print(f"     平均因子覆盖: {avg_coverage:.0%}")
    print(f"     高质量(≥80): {high_quality} 只")
    print(f"     低质量(<50): {low_quality} 只")

    # 找出最常见的缺失因子
    all_missing = []
    for r in reports.values():
        all_missing.extend(r.missing_factors)
    if all_missing:
        from collections import Counter
        common_missing = Counter(all_missing).most_common(5)
        print(f"     常见缺失因子:")
        for factor, count in common_missing:
            print(f"       {factor}: {count} 只 ({count/total:.0%})")
