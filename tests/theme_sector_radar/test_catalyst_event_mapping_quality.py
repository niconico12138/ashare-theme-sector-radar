"""
映射质量测试

测试 mapper.py 增强功能和 mapping_quality.py 模块。
"""

import pytest

from theme_sector_radar.data.catalyst_events.mapper import SymbolSectorMapper
from theme_sector_radar.data.catalyst_events.mapping_quality import (
    MappingQualityAnalyzer,
    generate_mapping_quality_md,
)


class TestSymbolNormalization:
    """测试 symbol 标准化"""

    def test_normalize_6digit(self):
        """测试 6 位代码"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_symbol("600519") == "600519"

    def test_normalize_sh_prefix(self):
        """测试 SH 前缀"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_symbol("SH600519") == "600519"
        assert mapper.normalize_symbol("sh600519") == "600519"

    def test_normalize_sh_suffix(self):
        """测试 .SH 后缀"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_symbol("600519.SH") == "600519"
        assert mapper.normalize_symbol("600519.XSHG") == "600519"

    def test_normalize_sz_prefix(self):
        """测试 SZ 前缀"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_symbol("SZ300750") == "300750"
        assert mapper.normalize_symbol("sz300750") == "300750"

    def test_normalize_sz_suffix(self):
        """测试 .SZ 后缀"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_symbol("300750.SZ") == "300750"
        assert mapper.normalize_symbol("300750.XSHE") == "300750"

    def test_normalize_with_spaces(self):
        """测试带空格"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_symbol(" 600519 ") == "600519"

    def test_normalize_invalid(self):
        """测试无效输入"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_symbol("ABC") is None
        assert mapper.normalize_symbol("") is None
        assert mapper.normalize_symbol(None) is None


class TestNameNormalization:
    """测试 name 标准化"""

    def test_normalize_simple(self):
        """测试简单名称"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_name("贵州茅台") == "贵州茅台"

    def test_normalize_with_suffix(self):
        """测试带后缀"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_name("贵州茅台股份有限公司") == "贵州茅台"
        assert mapper.normalize_name("宁德时代新能源科技股份有限公司") == "宁德时代新能源科技"

    def test_normalize_with_spaces(self):
        """测试带空格"""
        mapper = SymbolSectorMapper()
        assert mapper.normalize_name(" 贵州茅台 ") == "贵州茅台"


class TestMapperEnhanced:
    """测试增强的 mapper"""

    def test_map_symbol_by_symbol(self):
        """测试 symbol 直接匹配"""
        mapper = SymbolSectorMapper()
        result = mapper.map_symbol_to_sectors("600519", "贵州茅台")
        assert result["mapping_status"] == "mapped_by_symbol"
        assert "白酒" in result["industries"]

    def test_map_symbol_by_name(self):
        """测试 name 匹配"""
        mapper = SymbolSectorMapper()
        result = mapper.map_symbol_to_sectors("999999", "贵州茅台")
        assert result["mapping_status"] == "mapped_by_name"
        assert "白酒" in result["industries"]

    def test_map_symbol_by_alias(self):
        """测试 alias 匹配"""
        mapper = SymbolSectorMapper()
        result = mapper.map_symbol_to_sectors("999999", "茅台")
        assert result["mapping_status"] == "mapped_by_alias"
        assert "白酒" in result["industries"]

    def test_unmapped_returns_status(self):
        """测试 unmapped 返回正确状态"""
        mapper = SymbolSectorMapper()
        result = mapper.map_symbol_to_sectors("999999", "未知公司")
        assert result["mapping_status"] == "unmapped_symbol_not_found"

    def test_mapping_quality_analysis(self):
        """测试映射质量分析"""
        analyzer = MappingQualityAnalyzer()

        events = [
            {"mapping_status": "mapped_by_symbol", "related_industries": ["白酒"], "related_concepts": [], "related_symbols": ["600519"]},
            {"mapping_status": "mapped_by_name", "related_industries": ["电池"], "related_concepts": [], "related_symbols": ["999999"]},
            {"mapping_status": "unmapped_symbol_not_found", "related_industries": [], "related_concepts": [], "related_symbols": ["888888"], "related_symbol_names": ["未知"]},
        ]

        result = analyzer.analyze(events, "2026-06-01_to_2026-06-05")
        assert result["event_count"] == 3
        assert result["mapped_count"] == 2
        assert result["unmapped_count"] == 1
        assert abs(result["mapping_rate"] - 0.67) < 0.01

    def test_mapping_quality_report(self):
        """测试映射质量报告生成"""
        report_data = {
            "date_range": "2026-06-01_to_2026-06-05",
            "event_count": 25,
            "mapped_count": 15,
            "unmapped_count": 10,
            "mapping_rate": 0.60,
            "status_counts": {"mapped_by_symbol": 5, "mapped_by_name": 6, "unmapped_symbol_not_found": 8},
            "top_unmapped": [{"symbol": "999999", "name": "未知", "count": 5, "reason": "symbol_not_found"}],
        }

        md = generate_mapping_quality_md(report_data)
        assert "映射质量报告" in md
        assert "60%" in md
