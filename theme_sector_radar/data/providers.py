"""
数据提供者抽象接口

定义数据获取的标准接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import SectorSnapshot, SectorType


class DataProvider(ABC):
    """数据提供者抽象基类"""

    @abstractmethod
    def get_industry_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """
        获取行业板块列表

        Args:
            as_of_date: 分析日期
            top_n: 返回数量

        Returns:
            行业板块快照列表
        """
        pass

    @abstractmethod
    def get_concept_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """
        获取概念板块列表

        Args:
            as_of_date: 分析日期
            top_n: 返回数量

        Returns:
            概念板块快照列表
        """
        pass

    @abstractmethod
    def get_market_overview(self, as_of_date: str) -> Dict[str, Any]:
        """
        获取市场概览

        Args:
            as_of_date: 分析日期

        Returns:
            市场概览数据
        """
        pass

    @abstractmethod
    def get_sector_constituents(
        self,
        sector_id: str,
        sector_type: SectorType
    ) -> List[Dict[str, Any]]:
        """
        获取板块成分股

        Args:
            sector_id: 板块ID
            sector_type: 板块类型

        Returns:
            成分股列表
        """
        pass

    @abstractmethod
    def get_sector_flows(
        self,
        as_of_date: str,
        sector_type: SectorType
    ) -> List[Dict[str, Any]]:
        """
        获取板块资金流向

        Args:
            as_of_date: 分析日期
            sector_type: 板块类型

        Returns:
            资金流向列表
        """
        pass
