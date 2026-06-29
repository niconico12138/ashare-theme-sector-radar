"""
离线 Fixture 数据提供者

提供本地测试数据，不依赖网络。
支持 full/minimal/rotation-day1/rotation-day2 多种 profile。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from ..models import ConstituentSnapshot, SectorSnapshot, SectorType
from .providers import DataProvider


class FixtureProvider(DataProvider):
    """离线 Fixture 数据提供者"""

    def __init__(self, fixture_dir: str = None, profile: str = "full"):
        """
        初始化 Fixture 提供者

        Args:
            fixture_dir: Fixture 数据目录
            profile: 数据 profile (full/minimal/rotation-day1/rotation-day2)
        """
        if fixture_dir is None:
            fixture_dir = str(Path(__file__).parent / "fixtures")
        self.fixture_dir = fixture_dir
        self.profile = profile
        self._ensure_fixtures()

    def _ensure_fixtures(self):
        """确保 fixture 数据存在"""
        os.makedirs(self.fixture_dir, exist_ok=True)

        # 检查是否需要创建 fixture 文件
        full_industry_file = os.path.join(self.fixture_dir, "full_industry_sectors.json")
        if not os.path.exists(full_industry_file):
            self._create_full_fixtures()
            self._create_minimal_fixtures()
            self._create_rotation_fixtures()

    def _create_full_fixtures(self):
        """创建完整 fixture 数据（用于 ok 报告测试）"""
        # 行业板块数据 - 25 个
        industry_sectors = [
            {"sector_id": "BK0428", "name": "半导体", "price_change_pct": 3.21, "turnover": 12345678900, "main_net_inflow": 1234560000, "data_sources": ["akshare"], "data_quality_score": 88.0},
            {"sector_id": "BK0437", "name": "人工智能", "price_change_pct": 4.56, "turnover": 18765432100, "main_net_inflow": 2345670000, "data_sources": ["akshare"], "data_quality_score": 85.0},
            {"sector_id": "BK0447", "name": "新能源汽车", "price_change_pct": 2.15, "turnover": 9876543210, "main_net_inflow": 876540000, "data_sources": ["akshare"], "data_quality_score": 82.0},
            {"sector_id": "BK0476", "name": "光伏", "price_change_pct": -1.23, "turnover": 5432109876, "main_net_inflow": -321000000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK0493", "name": "医药生物", "price_change_pct": 1.89, "turnover": 7654321098, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK0456", "name": "锂电池", "price_change_pct": 3.45, "turnover": 8765432100, "main_net_inflow": 987650000, "data_sources": ["akshare"], "data_quality_score": 83.0},
            {"sector_id": "BK0462", "name": "芯片", "price_change_pct": 2.78, "turnover": 11234567800, "main_net_inflow": 1567800000, "data_sources": ["akshare"], "data_quality_score": 86.0},
            {"sector_id": "BK0471", "name": "新能源", "price_change_pct": 1.56, "turnover": 6543210000, "main_net_inflow": 432100000, "data_sources": ["akshare"], "data_quality_score": 79.0},
            {"sector_id": "BK0485", "name": "白酒", "price_change_pct": 0.89, "turnover": 5432100000, "main_net_inflow": 234500000, "data_sources": ["akshare"], "data_quality_score": 77.0},
            {"sector_id": "BK0498", "name": "银行", "price_change_pct": 0.45, "turnover": 4321000000, "main_net_inflow": 123400000, "data_sources": ["akshare"], "data_quality_score": 75.0},
            {"sector_id": "BK0501", "name": "保险", "price_change_pct": 0.67, "turnover": 3210000000, "main_net_inflow": 98700000, "data_sources": ["akshare"], "data_quality_score": 74.0},
            {"sector_id": "BK0512", "name": "证券", "price_change_pct": 1.23, "turnover": 4567000000, "main_net_inflow": 345600000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK0523", "name": "房地产", "price_change_pct": -0.34, "turnover": 2345000000, "main_net_inflow": -123000000, "data_sources": ["akshare"], "data_quality_score": 72.0},
            {"sector_id": "BK0534", "name": "钢铁", "price_change_pct": 0.78, "turnover": 3456000000, "main_net_inflow": 234000000, "data_sources": ["akshare"], "data_quality_score": 73.0},
            {"sector_id": "BK0545", "name": "有色金属", "price_change_pct": 2.34, "turnover": 5678000000, "main_net_inflow": 456700000, "data_sources": ["akshare"], "data_quality_score": 81.0},
            {"sector_id": "BK0556", "name": "煤炭", "price_change_pct": 1.12, "turnover": 4321000000, "main_net_inflow": 321000000, "data_sources": ["akshare"], "data_quality_score": 77.0},
            {"sector_id": "BK0567", "name": "石油石化", "price_change_pct": 0.56, "turnover": 3890000000, "main_net_inflow": 210000000, "data_sources": ["akshare"], "data_quality_score": 74.0},
            {"sector_id": "BK0578", "name": "电力设备", "price_change_pct": 2.89, "turnover": 7890000000, "main_net_inflow": 678000000, "data_sources": ["akshare"], "data_quality_score": 84.0},
            {"sector_id": "BK0589", "name": "机械设备", "price_change_pct": 1.67, "turnover": 5430000000, "main_net_inflow": 432000000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK0600", "name": "电子", "price_change_pct": 2.45, "turnover": 8760000000, "main_net_inflow": 765000000, "data_sources": ["akshare"], "data_quality_score": 82.0},
            {"sector_id": "BK0611", "name": "计算机", "price_change_pct": 3.12, "turnover": 9870000000, "main_net_inflow": 876000000, "data_sources": ["akshare"], "data_quality_score": 85.0},
            {"sector_id": "BK0622", "name": "通信", "price_change_pct": 1.89, "turnover": 6540000000, "main_net_inflow": 543000000, "data_sources": ["akshare"], "data_quality_score": 79.0},
            {"sector_id": "BK0633", "name": "传媒", "price_change_pct": 2.23, "turnover": 4320000000, "main_net_inflow": 321000000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK0644", "name": "社会服务", "price_change_pct": 0.98, "turnover": 3210000000, "main_net_inflow": 198000000, "data_sources": ["akshare"], "data_quality_score": 73.0},
            {"sector_id": "BK0655", "name": "食品饮料", "price_change_pct": 1.34, "turnover": 5430000000, "main_net_inflow": 432000000, "data_sources": ["akshare"], "data_quality_score": 77.0},
            {"sector_id": "BK0666", "name": "纺织服饰", "price_change_pct": 0.45, "turnover": 2100000000, "main_net_inflow": 98000000, "data_sources": ["akshare"], "data_quality_score": 70.0},
        ]

        # 概念板块数据 - 25 个
        concept_sectors = [
            {"sector_id": "BK1036", "name": "ChatGPT概念", "price_change_pct": 5.67, "turnover": 23456789012, "main_net_inflow": 3456780000, "data_sources": ["akshare"], "data_quality_score": 87.0},
            {"sector_id": "BK1038", "name": "CPO概念", "price_change_pct": 6.78, "turnover": 15678901234, "main_net_inflow": 2876540000, "data_sources": ["akshare"], "data_quality_score": 84.0},
            {"sector_id": "BK1040", "name": "机器人概念", "price_change_pct": 3.45, "turnover": 12345678901, "main_net_inflow": 1567890000, "data_sources": ["akshare"], "data_quality_score": 81.0},
            {"sector_id": "BK1042", "name": "锂矿", "price_change_pct": -0.89, "turnover": 8765432109, "main_net_inflow": -234560000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK1044", "name": "白酒", "price_change_pct": 1.23, "turnover": 6543210987, "main_net_inflow": 432100000, "data_sources": ["akshare"], "data_quality_score": 79.0},
            {"sector_id": "BK1046", "name": "光伏概念", "price_change_pct": 2.34, "turnover": 9876543210, "main_net_inflow": 765430000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK1048", "name": "储能", "price_change_pct": 3.56, "turnover": 8765432100, "main_net_inflow": 654320000, "data_sources": ["akshare"], "data_quality_score": 82.0},
            {"sector_id": "BK1050", "name": "新能源车", "price_change_pct": 2.89, "turnover": 11234567800, "main_net_inflow": 987650000, "data_sources": ["akshare"], "data_quality_score": 83.0},
            {"sector_id": "BK1052", "name": "芯片概念", "price_change_pct": 4.12, "turnover": 13456789000, "main_net_inflow": 1234560000, "data_sources": ["akshare"], "data_quality_score": 86.0},
            {"sector_id": "BK1054", "name": "人工智能概念", "price_change_pct": 5.23, "turnover": 15678901200, "main_net_inflow": 1456780000, "data_sources": ["akshare"], "data_quality_score": 88.0},
            {"sector_id": "BK1056", "name": "大数据", "price_change_pct": 2.67, "turnover": 7654321000, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK1058", "name": "云计算", "price_change_pct": 3.34, "turnover": 8765432100, "main_net_inflow": 654320000, "data_sources": ["akshare"], "data_quality_score": 81.0},
            {"sector_id": "BK1060", "name": "物联网", "price_change_pct": 1.78, "turnover": 5432109800, "main_net_inflow": 432100000, "data_sources": ["akshare"], "data_quality_score": 77.0},
            {"sector_id": "BK1062", "name": "区块链", "price_change_pct": 2.45, "turnover": 6543210000, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 79.0},
            {"sector_id": "BK1064", "name": "元宇宙", "price_change_pct": 3.89, "turnover": 7654321000, "main_net_inflow": 654320000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK1066", "name": "虚拟现实", "price_change_pct": 2.12, "turnover": 5432109800, "main_net_inflow": 432100000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK1068", "name": "增强现实", "price_change_pct": 1.56, "turnover": 4321098700, "main_net_inflow": 321090000, "data_sources": ["akshare"], "data_quality_score": 75.0},
            {"sector_id": "BK1070", "name": "数字货币", "price_change_pct": 2.78, "turnover": 6543210000, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 79.0},
            {"sector_id": "BK1072", "name": "网络安全", "price_change_pct": 3.45, "turnover": 7654321000, "main_net_inflow": 654320000, "data_sources": ["akshare"], "data_quality_score": 81.0},
            {"sector_id": "BK1074", "name": "国产软件", "price_change_pct": 2.89, "turnover": 6543210000, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK1076", "name": "工业互联网", "price_change_pct": 1.98, "turnover": 5432109800, "main_net_inflow": 432100000, "data_sources": ["akshare"], "data_quality_score": 77.0},
            {"sector_id": "BK1078", "name": "智能制造", "price_change_pct": 2.34, "turnover": 6543210000, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 79.0},
            {"sector_id": "BK1080", "name": "碳中和", "price_change_pct": 1.67, "turnover": 5432109800, "main_net_inflow": 432100000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK1082", "name": "氢能源", "price_change_pct": 2.89, "turnover": 6543210000, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK1084", "name": "预制菜", "price_change_pct": 1.45, "turnover": 4321098700, "main_net_inflow": 321090000, "data_sources": ["akshare"], "data_quality_score": 74.0},
        ]

        # 成分股数据
        constituents = {
            "BK0428": [
                {"code": "688981", "name": "中芯国际", "change_pct": 5.2, "turnover": 1234567890, "is_core": True},
                {"code": "002371", "name": "北方华创", "change_pct": 3.8, "turnover": 987654321, "is_core": True},
                {"code": "603501", "name": "韦尔股份", "change_pct": 2.5, "turnover": 876543210, "is_core": False},
                {"code": "688012", "name": "中微公司", "change_pct": 4.1, "turnover": 765432109, "is_core": True},
                {"code": "300661", "name": "圣邦股份", "change_pct": 1.8, "turnover": 654321098, "is_core": False},
            ],
            "BK0437": [
                {"code": "002230", "name": "科大讯飞", "change_pct": 6.5, "turnover": 1567890123, "is_core": True},
                {"code": "688787", "name": "海天瑞声", "change_pct": 8.2, "turnover": 1234567890, "is_core": True},
                {"code": "300496", "name": "中科创达", "change_pct": 4.3, "turnover": 987654321, "is_core": False},
                {"code": "688111", "name": "金山办公", "change_pct": 3.9, "turnover": 876543210, "is_core": True},
                {"code": "300033", "name": "同花顺", "change_pct": 5.1, "turnover": 765432109, "is_core": False},
            ],
            "BK1036": [
                {"code": "002230", "name": "科大讯飞", "change_pct": 6.5, "turnover": 1567890123, "is_core": True},
                {"code": "688787", "name": "海天瑞声", "change_pct": 8.2, "turnover": 1234567890, "is_core": True},
                {"code": "300496", "name": "中科创达", "change_pct": 4.3, "turnover": 987654321, "is_core": False},
                {"code": "688111", "name": "金山办公", "change_pct": 3.9, "turnover": 876543210, "is_core": True},
                {"code": "300033", "name": "同花顺", "change_pct": 5.1, "turnover": 765432109, "is_core": True},
            ],
            "BK1038": [
                {"code": "300308", "name": "中际旭创", "change_pct": 7.8, "turnover": 2345678901, "is_core": True},
                {"code": "002281", "name": "光迅科技", "change_pct": 5.6, "turnover": 1234567890, "is_core": True},
                {"code": "300502", "name": "新易盛", "change_pct": 6.3, "turnover": 987654321, "is_core": False},
            ],
        }

        # 市场概览
        market_overview = {
            "advance_count": 2800,
            "decline_count": 1800,
            "limit_up_count": 65,
            "limit_down_count": 8,
            "total_turnover": 1234567890123,
            "index_change_pct": 1.23,
        }

        # 保存 fixture 数据
        self._save_json("full_industry_sectors.json", industry_sectors)
        self._save_json("full_concept_sectors.json", concept_sectors)
        self._save_json("full_constituents.json", constituents)
        self._save_json("full_market_overview.json", market_overview)

    def _create_minimal_fixtures(self):
        """创建最小 fixture 数据（用于 degraded 测试）"""
        # 行业板块数据 - 5 个
        industry_sectors = [
            {"sector_id": "BK0428", "name": "半导体", "price_change_pct": 3.21, "turnover": 12345678900, "main_net_inflow": 1234560000, "data_sources": ["akshare"], "data_quality_score": 88.0},
            {"sector_id": "BK0437", "name": "人工智能", "price_change_pct": 4.56, "turnover": 18765432100, "main_net_inflow": 2345670000, "data_sources": ["akshare"], "data_quality_score": 85.0},
            {"sector_id": "BK0447", "name": "新能源汽车", "price_change_pct": 2.15, "turnover": 9876543210, "main_net_inflow": 876540000, "data_sources": ["akshare"], "data_quality_score": 82.0},
            {"sector_id": "BK0476", "name": "光伏", "price_change_pct": -1.23, "turnover": 5432109876, "main_net_inflow": -321000000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK0493", "name": "医药生物", "price_change_pct": 1.89, "turnover": 7654321098, "main_net_inflow": 543210000, "data_sources": ["akshare"], "data_quality_score": 80.0},
        ]

        # 概念板块数据 - 5 个
        concept_sectors = [
            {"sector_id": "BK1036", "name": "ChatGPT概念", "price_change_pct": 5.67, "turnover": 23456789012, "main_net_inflow": 3456780000, "data_sources": ["akshare"], "data_quality_score": 87.0},
            {"sector_id": "BK1038", "name": "CPO概念", "price_change_pct": 6.78, "turnover": 15678901234, "main_net_inflow": 2876540000, "data_sources": ["akshare"], "data_quality_score": 84.0},
            {"sector_id": "BK1040", "name": "机器人概念", "price_change_pct": 3.45, "turnover": 12345678901, "main_net_inflow": 1567890000, "data_sources": ["akshare"], "data_quality_score": 81.0},
            {"sector_id": "BK1042", "name": "锂矿", "price_change_pct": -0.89, "turnover": 8765432109, "main_net_inflow": -234560000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK1044", "name": "白酒", "price_change_pct": 1.23, "turnover": 6543210987, "main_net_inflow": 432100000, "data_sources": ["akshare"], "data_quality_score": 79.0},
        ]

        # 成分股数据
        constituents = {
            "BK0428": [
                {"code": "688981", "name": "中芯国际", "change_pct": 5.2, "turnover": 1234567890, "is_core": True},
                {"code": "002371", "name": "北方华创", "change_pct": 3.8, "turnover": 987654321, "is_core": True},
            ],
            "BK0437": [
                {"code": "002230", "name": "科大讯飞", "change_pct": 6.5, "turnover": 1567890123, "is_core": True},
                {"code": "688787", "name": "海天瑞声", "change_pct": 8.2, "turnover": 1234567890, "is_core": True},
            ],
            "BK1036": [
                {"code": "002230", "name": "科大讯飞", "change_pct": 6.5, "turnover": 1567890123, "is_core": True},
                {"code": "688787", "name": "海天瑞声", "change_pct": 8.2, "turnover": 1234567890, "is_core": True},
            ],
        }

        # 市场概览
        market_overview = {
            "advance_count": 2800,
            "decline_count": 1800,
            "limit_up_count": 65,
            "limit_down_count": 8,
            "total_turnover": 1234567890123,
            "index_change_pct": 1.23,
        }

        # 保存 fixture 数据
        self._save_json("minimal_industry_sectors.json", industry_sectors)
        self._save_json("minimal_concept_sectors.json", concept_sectors)
        self._save_json("minimal_constituents.json", constituents)
        self._save_json("minimal_market_overview.json", market_overview)

    def _create_rotation_fixtures(self):
        """创建轮动测试 fixture 数据"""
        # rotation-day1 行业板块 (2026-06-27)
        rotation_day1_industry = [
            {"sector_id": "BK0437", "name": "人工智能", "price_change_pct": 3.56, "turnover": 15000000000, "main_net_inflow": 1800000000, "data_sources": ["akshare"], "data_quality_score": 85.0},
            {"sector_id": "BK0428", "name": "半导体", "price_change_pct": 2.89, "turnover": 12000000000, "main_net_inflow": 1200000000, "data_sources": ["akshare"], "data_quality_score": 83.0},
            {"sector_id": "BK0611", "name": "计算机", "price_change_pct": 2.45, "turnover": 9000000000, "main_net_inflow": 800000000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK0447", "name": "新能源汽车", "price_change_pct": 1.89, "turnover": 8000000000, "main_net_inflow": 600000000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK0600", "name": "电子", "price_change_pct": 1.56, "turnover": 7000000000, "main_net_inflow": 500000000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK0578", "name": "电力设备", "price_change_pct": 1.23, "turnover": 6000000000, "main_net_inflow": 400000000, "data_sources": ["akshare"], "data_quality_score": 75.0},
            {"sector_id": "BK0545", "name": "有色金属", "price_change_pct": 0.98, "turnover": 5000000000, "main_net_inflow": 300000000, "data_sources": ["akshare"], "data_quality_score": 74.0},
            {"sector_id": "BK0456", "name": "锂电池", "price_change_pct": 0.78, "turnover": 4500000000, "main_net_inflow": 250000000, "data_sources": ["akshare"], "data_quality_score": 73.0},
            {"sector_id": "BK0622", "name": "通信", "price_change_pct": 0.56, "turnover": 4000000000, "main_net_inflow": 200000000, "data_sources": ["akshare"], "data_quality_score": 72.0},
            {"sector_id": "BK0633", "name": "传媒", "price_change_pct": 0.45, "turnover": 3500000000, "main_net_inflow": 150000000, "data_sources": ["akshare"], "data_quality_score": 71.0},
        ]

        # rotation-day1 概念板块
        rotation_day1_concept = [
            {"sector_id": "BK1036", "name": "ChatGPT概念", "price_change_pct": 4.56, "turnover": 20000000000, "main_net_inflow": 2500000000, "data_sources": ["akshare"], "data_quality_score": 86.0},
            {"sector_id": "BK1054", "name": "人工智能概念", "price_change_pct": 4.12, "turnover": 18000000000, "main_net_inflow": 2200000000, "data_sources": ["akshare"], "data_quality_score": 84.0},
            {"sector_id": "BK1038", "name": "CPO概念", "price_change_pct": 3.89, "turnover": 15000000000, "main_net_inflow": 1800000000, "data_sources": ["akshare"], "data_quality_score": 82.0},
            {"sector_id": "BK1052", "name": "芯片概念", "price_change_pct": 3.45, "turnover": 12000000000, "main_net_inflow": 1500000000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK1040", "name": "机器人概念", "price_change_pct": 2.89, "turnover": 10000000000, "main_net_inflow": 1200000000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK1048", "name": "储能", "price_change_pct": 2.34, "turnover": 8000000000, "main_net_inflow": 900000000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK1072", "name": "网络安全", "price_change_pct": 1.89, "turnover": 7000000000, "main_net_inflow": 700000000, "data_sources": ["akshare"], "data_quality_score": 75.0},
            {"sector_id": "BK1058", "name": "云计算", "price_change_pct": 1.56, "turnover": 6000000000, "main_net_inflow": 600000000, "data_sources": ["akshare"], "data_quality_score": 74.0},
            {"sector_id": "BK1056", "name": "大数据", "price_change_pct": 1.23, "turnover": 5500000000, "main_net_inflow": 500000000, "data_sources": ["akshare"], "data_quality_score": 73.0},
            {"sector_id": "BK1064", "name": "元宇宙", "price_change_pct": 0.98, "turnover": 5000000000, "main_net_inflow": 400000000, "data_sources": ["akshare"], "data_quality_score": 72.0},
        ]

        # rotation-day2 行业板块 (2026-06-28) - 与 day1 有变化
        rotation_day2_industry = [
            {"sector_id": "BK0428", "name": "半导体", "price_change_pct": 4.21, "turnover": 14000000000, "main_net_inflow": 2000000000, "data_sources": ["akshare"], "data_quality_score": 88.0},
            {"sector_id": "BK0437", "name": "人工智能", "price_change_pct": 3.89, "turnover": 13000000000, "main_net_inflow": 1600000000, "data_sources": ["akshare"], "data_quality_score": 86.0},
            {"sector_id": "BK0462", "name": "芯片", "price_change_pct": 3.56, "turnover": 11000000000, "main_net_inflow": 1400000000, "data_sources": ["akshare"], "data_quality_score": 84.0},
            {"sector_id": "BK0611", "name": "计算机", "price_change_pct": 2.89, "turnover": 9500000000, "main_net_inflow": 900000000, "data_sources": ["akshare"], "data_quality_score": 82.0},
            {"sector_id": "BK0600", "name": "电子", "price_change_pct": 2.45, "turnover": 8500000000, "main_net_inflow": 750000000, "data_sources": ["akshare"], "data_quality_score": 80.0},
            {"sector_id": "BK0578", "name": "电力设备", "price_change_pct": 2.12, "turnover": 7500000000, "main_net_inflow": 650000000, "data_sources": ["akshare"], "data_quality_score": 78.0},
            {"sector_id": "BK0447", "name": "新能源汽车", "price_change_pct": 1.78, "turnover": 7000000000, "main_net_inflow": 550000000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK0545", "name": "有色金属", "price_change_pct": 1.45, "turnover": 6000000000, "main_net_inflow": 450000000, "data_sources": ["akshare"], "data_quality_score": 75.0},
            {"sector_id": "BK0456", "name": "锂电池", "price_change_pct": 1.12, "turnover": 5500000000, "main_net_inflow": 400000000, "data_sources": ["akshare"], "data_quality_score": 74.0},
            {"sector_id": "BK0622", "name": "通信", "price_change_pct": 0.89, "turnover": 5000000000, "main_net_inflow": 350000000, "data_sources": ["akshare"], "data_quality_score": 73.0},
        ]

        # rotation-day2 概念板块 - 与 day1 有变化
        rotation_day2_concept = [
            {"sector_id": "BK1038", "name": "CPO概念", "price_change_pct": 6.78, "turnover": 18000000000, "main_net_inflow": 2800000000, "data_sources": ["akshare"], "data_quality_score": 87.0},
            {"sector_id": "BK1036", "name": "ChatGPT概念", "price_change_pct": 5.23, "turnover": 16000000000, "main_net_inflow": 2400000000, "data_sources": ["akshare"], "data_quality_score": 85.0},
            {"sector_id": "BK1054", "name": "人工智能概念", "price_change_pct": 4.56, "turnover": 14000000000, "main_net_inflow": 2000000000, "data_sources": ["akshare"], "data_quality_score": 83.0},
            {"sector_id": "BK1046", "name": "光伏概念", "price_change_pct": 3.89, "turnover": 12000000000, "main_net_inflow": 1600000000, "data_sources": ["akshare"], "data_quality_score": 81.0},
            {"sector_id": "BK1052", "name": "芯片概念", "price_change_pct": 3.45, "turnover": 10000000000, "main_net_inflow": 1300000000, "data_sources": ["akshare"], "data_quality_score": 79.0},
            {"sector_id": "BK1040", "name": "机器人概念", "price_change_pct": 2.89, "turnover": 9000000000, "main_net_inflow": 1100000000, "data_sources": ["akshare"], "data_quality_score": 77.0},
            {"sector_id": "BK1048", "name": "储能", "price_change_pct": 2.34, "turnover": 8000000000, "main_net_inflow": 950000000, "data_sources": ["akshare"], "data_quality_score": 76.0},
            {"sector_id": "BK1072", "name": "网络安全", "price_change_pct": 1.89, "turnover": 7000000000, "main_net_inflow": 800000000, "data_sources": ["akshare"], "data_quality_score": 75.0},
            {"sector_id": "BK1058", "name": "云计算", "price_change_pct": 1.56, "turnover": 6500000000, "main_net_inflow": 650000000, "data_sources": ["akshare"], "data_quality_score": 74.0},
            {"sector_id": "BK1064", "name": "元宇宙", "price_change_pct": 1.23, "turnover": 5500000000, "main_net_inflow": 500000000, "data_sources": ["akshare"], "data_quality_score": 73.0},
        ]

        # 成分股数据
        constituents = {
            "BK0428": [
                {"code": "688981", "name": "中芯国际", "change_pct": 5.2, "turnover": 1234567890, "is_core": True},
                {"code": "002371", "name": "北方华创", "change_pct": 3.8, "turnover": 987654321, "is_core": True},
            ],
            "BK0437": [
                {"code": "002230", "name": "科大讯飞", "change_pct": 6.5, "turnover": 1567890123, "is_core": True},
                {"code": "688787", "name": "海天瑞声", "change_pct": 8.2, "turnover": 1234567890, "is_core": True},
            ],
            "BK1036": [
                {"code": "002230", "name": "科大讯飞", "change_pct": 6.5, "turnover": 1567890123, "is_core": True},
                {"code": "688787", "name": "海天瑞声", "change_pct": 8.2, "turnover": 1234567890, "is_core": True},
            ],
            "BK1038": [
                {"code": "300308", "name": "中际旭创", "change_pct": 7.8, "turnover": 2345678901, "is_core": True},
                {"code": "002281", "name": "光迅科技", "change_pct": 5.6, "turnover": 1234567890, "is_core": True},
            ],
        }

        # 市场概览
        market_overview = {
            "advance_count": 2800,
            "decline_count": 1800,
            "limit_up_count": 65,
            "limit_down_count": 8,
            "total_turnover": 1234567890123,
            "index_change_pct": 1.23,
        }

        # 保存 fixture 数据
        self._save_json("rotation-day1_industry_sectors.json", rotation_day1_industry)
        self._save_json("rotation-day1_concept_sectors.json", rotation_day1_concept)
        self._save_json("rotation-day1_constituents.json", constituents)
        self._save_json("rotation-day1_market_overview.json", market_overview)

        self._save_json("rotation-day2_industry_sectors.json", rotation_day2_industry)
        self._save_json("rotation-day2_concept_sectors.json", rotation_day2_concept)
        self._save_json("rotation-day2_constituents.json", constituents)
        self._save_json("rotation-day2_market_overview.json", market_overview)

    def _save_json(self, filename: str, data: Any):
        """保存 JSON 文件"""
        filepath = os.path.join(self.fixture_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_json(self, filename: str) -> Any:
        """加载 JSON 文件"""
        filepath = os.path.join(self.fixture_dir, filename)
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_sector_snapshot(self, data: Dict[str, Any], sector_type: SectorType) -> SectorSnapshot:
        """解析板块快照"""
        constituents_data = data.get("constituents", [])
        constituents = [
            ConstituentSnapshot(
                code=c.get("code", ""),
                name=c.get("name", ""),
                change_pct=c.get("change_pct", 0.0),
                turnover=c.get("turnover", 0.0),
                is_core=c.get("is_core", False),
            )
            for c in constituents_data
        ]

        return SectorSnapshot(
            sector_id=data.get("sector_id", ""),
            name=data.get("name", ""),
            type=sector_type,
            price_change_pct=data.get("price_change_pct", 0.0),
            turnover=data.get("turnover", 0.0),
            main_net_inflow=data.get("main_net_inflow", 0.0),
            constituents=constituents,
            data_sources=data.get("data_sources", ["fixture"]),
            updated_at=data.get("updated_at", "2026-06-28T15:30:00+08:00"),
            data_quality_score=data.get("data_quality_score", 80.0),
        )

    def _get_prefix(self) -> str:
        """获取 profile 前缀"""
        return self.profile

    def get_industry_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """获取行业板块列表"""
        prefix = self._get_prefix()
        data = self._load_json(f"{prefix}_industry_sectors.json")
        if not data:
            return []

        sectors = []
        for item in data[:top_n]:
            # 加载成分股
            constituents_data = self._load_json(f"{prefix}_constituents.json")
            sector_id = item.get("sector_id", "")
            if constituents_data and sector_id in constituents_data:
                item["constituents"] = constituents_data[sector_id]

            sectors.append(self._parse_sector_snapshot(item, SectorType.INDUSTRY))

        return sectors

    def get_concept_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """获取概念板块列表"""
        prefix = self._get_prefix()
        data = self._load_json(f"{prefix}_concept_sectors.json")
        if not data:
            return []

        sectors = []
        for item in data[:top_n]:
            # 加载成分股
            constituents_data = self._load_json(f"{prefix}_constituents.json")
            sector_id = item.get("sector_id", "")
            if constituents_data and sector_id in constituents_data:
                item["constituents"] = constituents_data[sector_id]

            sectors.append(self._parse_sector_snapshot(item, SectorType.CONCEPT))

        return sectors

    def get_market_overview(self, as_of_date: str) -> Dict[str, Any]:
        """获取市场概览"""
        prefix = self._get_prefix()
        data = self._load_json(f"{prefix}_market_overview.json")
        if not data:
            return {
                "advance_count": 0,
                "decline_count": 0,
                "limit_up_count": 0,
                "limit_down_count": 0,
                "total_turnover": 0,
                "index_change_pct": 0,
            }
        return data

    def get_sector_constituents(
        self,
        sector_id: str,
        sector_type: SectorType
    ) -> List[Dict[str, Any]]:
        """获取板块成分股"""
        prefix = self._get_prefix()
        data = self._load_json(f"{prefix}_constituents.json")
        if not data:
            return []
        return data.get(sector_id, [])

    def get_sector_flows(
        self,
        as_of_date: str,
        sector_type: SectorType
    ) -> List[Dict[str, Any]]:
        """获取板块资金流向"""
        # Fixture 数据中资金流已包含在板块数据中
        return []
