"""
量化打分 v2 + 数据核查 测试

覆盖：
- 数据核查模块（quant_data_validator）
- 新增因子（动量质量、量能趋势、波动率、板块匹配等）
- 最终排名公式 v2
"""

import pytest
from theme_sector_radar.quant_data_validator import (
    validate_stock_bars,
    validate_stock_quote,
    validate_fund_flow,
    validate_sector_data,
    validate_stock_full,
    compute_data_quality_for_stocks,
    StockDataQualityReport,
    ValidationResult,
)


# ============================================================
# 数据核查测试
# ============================================================

class TestStockQuoteValidation:
    """测试行情数据核查"""

    def test_valid_stock(self):
        """正常股票应全部通过"""
        stock = {"code": "600030", "change_pct": 2.5, "pe": 15, "pb": 2.0, "total_mv": 200}
        report = validate_stock_quote(stock)
        assert report.error_count == 0
        assert report.quality_score >= 80

    def test_missing_pe(self):
        """缺失 PE 应标记为 missing"""
        stock = {"code": "600030", "change_pct": 2.5, "total_mv": 200}
        report = validate_stock_quote(stock)
        assert report.missing_count >= 1

    def test_extreme_change(self):
        """超限涨幅应标记为 warning"""
        stock = {"code": "600030", "change_pct": 25.0, "pe": 15, "pb": 2.0, "total_mv": 200}
        report = validate_stock_quote(stock)
        assert report.warning_count >= 1

    def test_negative_pe(self):
        """负 PE（亏损股）应标记为 warning"""
        stock = {"code": "600030", "change_pct": 0, "pe": -10, "pb": 2.0, "total_mv": 200}
        report = validate_stock_quote(stock)
        assert report.warning_count >= 1

    def test_invalid_code(self):
        """异常代码格式应标记为 warning"""
        stock = {"code": "abc", "change_pct": 0, "pe": 15, "pb": 2.0, "total_mv": 200}
        report = validate_stock_quote(stock)
        assert report.warning_count >= 1


class TestBarsValidation:
    """测试 K 线数据核查"""

    def test_valid_bars(self):
        """正常 K 线应全部通过"""
        bars = [
            {"date": f"2026-07-{d:02d}", "close": 20 + i * 0.1, "amount": 3e8}
            for i, d in enumerate(range(1, 21))
        ]
        report = validate_stock_bars("600030", bars, "2026-07-20")
        assert report.error_count == 0

    def test_empty_bars(self):
        """空 K 线应标记为 missing"""
        report = validate_stock_bars("600030", [], "2026-07-20")
        assert report.missing_count >= 1

    def test_insufficient_bars(self):
        """不足 5 天应标记为 warning"""
        bars = [
            {"date": f"2026-07-{d:02d}", "close": 20, "amount": 3e8}
            for d in range(1, 4)
        ]
        report = validate_stock_bars("600030", bars, "2026-07-03")
        assert report.warning_count >= 1

    def test_date_not_covering_target(self):
        """K 线未覆盖目标日期应标记为 warning"""
        bars = [
            {"date": f"2026-06-{d:02d}", "close": 20, "amount": 3e8}
            for d in range(1, 21)
        ]
        report = validate_stock_bars("600030", bars, "2026-07-15")
        assert report.warning_count >= 1

    def test_zero_amount(self):
        """零成交额应标记为 missing"""
        bars = [
            {"date": f"2026-07-{d:02d}", "close": 20, "amount": 0}
            for d in range(1, 10)
        ]
        report = validate_stock_bars("600030", bars, "2026-07-09")
        assert report.missing_count >= 1


class TestFundFlowValidation:
    """测试资金流数据核查"""

    def test_valid_fund_flow(self):
        """正常资金流应通过"""
        stock = {"code": "600030", "_fund_flow": {"available": True, "main_net_inflow": 1e8, "direction": "inflow"}}
        report = validate_fund_flow(stock)
        assert report.error_count == 0

    def test_missing_fund_flow(self):
        """无资金流应标记为 missing"""
        stock = {"code": "600030"}
        report = validate_fund_flow(stock)
        assert report.missing_count >= 1

    def test_unavailable_fund_flow(self):
        """不可用资金流应标记为 warning"""
        stock = {"code": "600030", "_fund_flow": {"available": False}}
        report = validate_fund_flow(stock)
        assert report.warning_count >= 1


class TestSectorDataValidation:
    """测试板块数据核查"""

    def test_valid_sector_data(self):
        """正常板块数据应通过"""
        stock = {"code": "600030", "sector_trend_score": 65, "sector_burst_score": 55, "sector_name": "证券", "relevance_score": 0.8}
        report = validate_sector_data(stock)
        assert report.error_count == 0
        assert all(detail.field != "relevance_score" for detail in report.results)

    def test_legacy_relevance_is_not_a_quality_factor(self):
        stock = {
            "code": "600030",
            "sector_trend_score": 65,
            "sector_burst_score": 55,
            "sector_name": "证券",
            "legacy_relevance_score": 0.1,
        }
        report = validate_sector_data(stock)
        assert all(detail.field != "legacy_relevance_score" for detail in report.results)

    def test_missing_sector_name(self):
        """缺失板块名称应标记为 missing"""
        stock = {"code": "600030", "sector_trend_score": 65, "sector_burst_score": 55, "relevance_score": 0.8}
        report = validate_sector_data(stock)
        assert report.missing_count >= 1


class TestFullValidation:
    """测试完整核查"""

    def test_full_quality_report(self):
        """完整数据应有高质量分"""
        stock = {
            "code": "600030", "change_pct": 2.5, "pe": 15, "pb": 2.0, "total_mv": 200,
            "sector_trend_score": 65, "sector_burst_score": 55, "sector_name": "证券", "relevance_score": 0.8,
            "_fund_flow": {"available": True, "main_net_inflow": 1e8, "direction": "inflow"},
        }
        bars = [
            {"date": f"2026-07-{d:02d}", "close": 20 + i * 0.1, "amount": 3e8, "volume": 1e6, "open": 19.9}
            for i, d in enumerate(range(1, 21))
        ]
        report = validate_stock_full(stock, bars, "2026-07-20")
        assert report.quality_score >= 70
        assert report.factor_coverage >= 0.5
        assert len(report.available_factors) > 0

    def test_factor_classification(self):
        """因子分类应正确"""
        stock = {
            "code": "600030", "change_pct": 2.5, "pe": 15, "pb": 2.0, "total_mv": 200,
            "sector_trend_score": 65, "sector_burst_score": 55,
        }
        bars = [
            {"date": f"2026-07-{d:02d}", "close": 20 + i * 0.1, "amount": 3e8, "volume": 1e6, "open": 19.9}
            for i, d in enumerate(range(1, 21))
        ]
        report = validate_stock_full(stock, bars, "2026-07-20")
        assert "1d_momentum" in report.available_factors
        assert "market_cap" in report.available_factors
        assert "sector_match" in report.available_factors


class TestBatchValidation:
    """测试批量核查"""

    def test_batch_quality(self):
        """批量核查应返回每个股票的报告"""
        stocks = [
            {"code": "600030", "change_pct": 2.5, "pe": 15, "pb": 2.0, "total_mv": 200,
             "sector_trend_score": 65, "sector_burst_score": 55},
            {"code": "601211", "change_pct": -1.0, "pe": 25, "pb": 1.5, "total_mv": 150,
             "sector_trend_score": 50, "sector_burst_score": 40},
        ]
        reports = compute_data_quality_for_stocks(stocks)
        assert len(reports) == 2
        assert "600030" in reports
        assert "601211" in reports
