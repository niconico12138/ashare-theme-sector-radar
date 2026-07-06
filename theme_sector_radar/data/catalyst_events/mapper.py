"""
成分股到板块映射

建立 symbol -> industry/concept 映射。
支持 symbol/name 标准化和多来源映射索引。
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


# 常见公司名称后缀
NAME_SUFFIXES = [
    "股份", "集团", "有限公司", "控股", "科技", "A", "B",
    "股份有限公司", "有限责任公司", "集团股份有限公司",
]

# 常见简称映射
ALIAS_MAP = {
    "茅台": "贵州茅台",
    "宁德": "宁德时代",
    "比亚迪": "比亚迪",
    "中芯": "中芯国际",
    "隆基": "隆基绿能",
    "恒瑞": "恒瑞医药",
    "药明": "药明康德",
    "海天": "海天味业",
    "美的": "美的集团",
    "格力": "格力电器",
}


class SymbolSectorMapper:
    """
    成分股到板块映射

    支持 symbol/name 标准化和多来源映射索引。
    """

    def __init__(self, history_root: str = "data_cache/sector_history"):
        self.history_root = history_root
        self._mapping_index = None

    def build_mapping_index(self) -> Dict[str, Any]:
        """构建多来源映射索引"""
        if self._mapping_index is not None:
            return self._mapping_index

        symbol_to_sectors = {}
        name_to_symbols = {}
        name_alias_to_symbols = {}

        # 从 sector_history 构建 sector_name -> sector_type 映射
        sector_names = {}
        for sector_type in ["industry", "concept"]:
            type_dir = os.path.join(self.history_root, sector_type)
            if not os.path.exists(type_dir):
                continue
            for filename in os.listdir(type_dir):
                if filename.endswith(".json"):
                    sector_name = filename[:-5]
                    sector_names[sector_name] = sector_type

        # 从 fixture 构建映射
        fixture_mapping = self._load_fixture_mapping()
        for symbol, info in fixture_mapping.items():
            normalized = self.normalize_symbol(symbol)
            if normalized:
                symbol_to_sectors[normalized] = {
                    "symbol_name": info.get("name", ""),
                    "industries": info.get("industries", []),
                    "concepts": info.get("concepts", []),
                }
                name = info.get("name", "")
                if name:
                    normalized_name = self.normalize_name(name)
                    name_to_symbols[normalized_name] = [normalized]
                    # 添加别名
                    for alias, full_name in ALIAS_MAP.items():
                        if full_name == normalized_name:
                            name_alias_to_symbols[alias] = [normalized]

        self._mapping_index = {
            "symbol_to_sectors": symbol_to_sectors,
            "name_to_symbols": name_to_symbols,
            "name_alias_to_symbols": name_alias_to_symbols,
            "sector_names": sector_names,
        }

        return self._mapping_index

    def normalize_symbol(self, symbol: str) -> Optional[str]:
        """
        标准化股票代码

        支持格式：
        - 600519
        - SH600519 / sh600519
        - 600519.SH / 600519.XSHG
        - SZ300750 / sz300750
        - 300750.SZ / 300750.XSHE

        Returns:
            6 位代码，无法提取返回 None
        """
        if not symbol:
            return None

        # 去空格和特殊字符
        s = symbol.strip()

        # 提取 6 位连续数字
        match = re.search(r'\d{6}', s)
        if match:
            return match.group()

        return None

    def normalize_name(self, name: str) -> str:
        """
        标准化股票名称

        - 去空格
        - 去常见后缀
        """
        if not name:
            return ""

        # 去空格
        n = name.strip()

        # 去后缀
        for suffix in sorted(NAME_SUFFIXES, key=len, reverse=True):
            if n.endswith(suffix):
                n = n[:-len(suffix)]
                break

        return n

    def map_symbol_to_sectors(
        self,
        symbol: str,
        symbol_name: str = "",
    ) -> Dict[str, Any]:
        """
        将股票代码映射到板块

        Returns:
            映射结果，包含 mapping_status
        """
        result = {
            "symbol": symbol,
            "symbol_name": symbol_name,
            "industries": [],
            "concepts": [],
            "original_symbol": symbol,
            "normalized_symbol": None,
            "original_name": symbol_name,
            "normalized_name": None,
            "mapping_status": "unmapped_missing_symbol",
            "mapping_warnings": [],
        }

        index = self.build_mapping_index()
        symbol_to_sectors = index.get("symbol_to_sectors", {})
        name_to_symbols = index.get("name_to_symbols", {})
        name_alias_to_symbols = index.get("name_alias_to_symbols", {})

        # 1. 尝试 symbol 匹配
        normalized = self.normalize_symbol(symbol)
        result["normalized_symbol"] = normalized

        if normalized and normalized in symbol_to_sectors:
            info = symbol_to_sectors[normalized]
            result["industries"] = info.get("industries", [])
            result["concepts"] = info.get("concepts", [])
            result["symbol_name"] = info.get("symbol_name", symbol_name)
            result["mapping_status"] = "mapped_by_symbol"
            return result

        # 2. 尝试 name 匹配
        if symbol_name:
            normalized_name = self.normalize_name(symbol_name)
            result["normalized_name"] = normalized_name

            if normalized_name in name_to_symbols:
                matched_symbols = name_to_symbols[normalized_name]
                if len(matched_symbols) == 1:
                    # 唯一匹配
                    matched_symbol = matched_symbols[0]
                    if matched_symbol in symbol_to_sectors:
                        info = symbol_to_sectors[matched_symbol]
                        result["industries"] = info.get("industries", [])
                        result["concepts"] = info.get("concepts", [])
                        result["mapping_status"] = "mapped_by_name"
                        return result
                else:
                    result["mapping_status"] = "ambiguous_name_match"
                    result["mapping_warnings"].append(f"名称 '{normalized_name}' 匹配到多个 symbol: {matched_symbols}")
                    return result

            # 3. 尝试 alias 匹配
            if normalized_name in name_alias_to_symbols:
                matched_symbols = name_alias_to_symbols[normalized_name]
                if len(matched_symbols) == 1:
                    matched_symbol = matched_symbols[0]
                    if matched_symbol in symbol_to_sectors:
                        info = symbol_to_sectors[matched_symbol]
                        result["industries"] = info.get("industries", [])
                        result["concepts"] = info.get("concepts", [])
                        result["mapping_status"] = "mapped_by_alias"
                        return result

        # 4. 无法映射
        if not normalized:
            result["mapping_status"] = "unmapped_missing_symbol"
            result["mapping_warnings"].append("无法从 symbol 提取 6 位代码")
        elif not symbol_name:
            result["mapping_status"] = "unmapped_missing_name"
            result["mapping_warnings"].append("缺少 symbol_name")
        else:
            result["mapping_status"] = "unmapped_symbol_not_found"
            result["mapping_warnings"].append(f"symbol '{normalized}' 和 name '{symbol_name}' 均未找到映射")

        return result

    def map_events_to_sectors(
        self,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """将事件映射到板块"""
        mapped_events = []

        for event in events:
            symbols = event.get("related_symbols", [])
            symbol_names = event.get("related_symbol_names", [])

            all_industries = set()
            all_concepts = set()
            all_mapping_statuses = []
            all_warnings = []

            for i, sym in enumerate(symbols):
                name = symbol_names[i] if i < len(symbol_names) else ""
                mapping = self.map_symbol_to_sectors(sym, name)
                all_industries.update(mapping.get("industries", []))
                all_concepts.update(mapping.get("concepts", []))
                all_mapping_statuses.append(mapping.get("mapping_status", ""))
                all_warnings.extend(mapping.get("mapping_warnings", []))

            event["related_industries"] = list(all_industries)
            event["related_concepts"] = list(all_concepts)
            event["unmapped"] = len(all_industries) == 0 and len(all_concepts) == 0
            event["mapping_status"] = all_mapping_statuses[0] if all_mapping_statuses else "no_symbols"
            event["mapping_warnings"] = all_warnings

            mapped_events.append(event)

        return mapped_events

    def _load_fixture_mapping(self) -> Dict[str, Dict[str, Any]]:
        """加载 fixture 映射"""
        return {
            "600519": {"name": "贵州茅台", "industries": ["白酒"], "concepts": ["消费"]},
            "300750": {"name": "宁德时代", "industries": ["电池"], "concepts": ["新能源汽车", "储能"]},
            "000858": {"name": "五粮液", "industries": ["白酒"], "concepts": ["消费"]},
            "000001": {"name": "平安银行", "industries": ["银行"], "concepts": ["金融"]},
            "601318": {"name": "中国平安", "industries": ["保险"], "concepts": ["金融"]},
            "600036": {"name": "招商银行", "industries": ["银行"], "concepts": ["金融"]},
            "002594": {"name": "比亚迪", "industries": ["汽车整车"], "concepts": ["新能源汽车"]},
            "300059": {"name": "东方财富", "industries": ["证券"], "concepts": ["互联网金融"]},
            "002475": {"name": "立讯精密", "industries": ["消费电子"], "concepts": ["苹果概念"]},
            "601012": {"name": "隆基绿能", "industries": ["光伏设备"], "concepts": ["新能源"]},
        }
