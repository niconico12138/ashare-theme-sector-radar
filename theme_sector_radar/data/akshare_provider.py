"""
AkShare 数据提供者

提供真实 AkShare 东方财富行业/概念板块数据获取能力。
支持重试、降级和缓存 fallback。
"""

import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import ConstituentSnapshot, SectorSnapshot, SectorType
from .providers import DataProvider


@dataclass
class CallResult:
    """接口调用结果"""
    status: str  # ok / degraded / failed
    data: Any = None
    warnings: List[str] = None
    elapsed_ms: float = 0.0

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class AkShareProvider(DataProvider):
    """
    AkShare 数据提供者

    基于 AkShare 东方财富接口获取行业/概念板块数据。
    支持重试、降级和错误处理。
    """

    def __init__(self, retries: int = 3, retry_delay: float = 1.0):
        """
        初始化 AkShare 提供者

        Args:
            retries: 重试次数
            retry_delay: 重试延迟（秒）
        """
        self._client = None
        self.retries = retries
        self.retry_delay = retry_delay

    def _get_client(self):
        """获取 AkShare 客户端"""
        if self._client is None:
            try:
                import akshare as ak
                self._client = ak
            except ImportError:
                raise ImportError(
                    "akshare 未安装，请运行: pip install akshare"
                )
        return self._client

    def _safe_call(self, func, *args, **kwargs) -> CallResult:
        """
        安全调用 AkShare 接口，支持重试

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            CallResult: 调用结果
        """
        warnings_list = []
        last_error = None

        for attempt in range(self.retries):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000

                # 检查结果是否有效
                if result is None:
                    warnings_list.append(f"第 {attempt+1} 次调用返回 None")
                    if attempt < self.retries - 1:
                        time.sleep(self.retry_delay)
                    continue

                # 检查是否为 DataFrame 且非空
                if hasattr(result, 'empty') and result.empty:
                    warnings_list.append(f"第 {attempt+1} 次调用返回空 DataFrame")
                    if attempt < self.retries - 1:
                        time.sleep(self.retry_delay)
                    continue

                # 成功
                return CallResult(
                    status="ok",
                    data=result,
                    warnings=warnings_list if warnings_list else [],
                    elapsed_ms=elapsed_ms
                )

            except ConnectionError as e:
                elapsed_ms = (time.time() - start_time) * 1000
                last_error = e
                warnings_list.append(f"第 {attempt+1} 次网络连接错误: {str(e)[:100]}")
                if attempt < self.retries - 1:
                    time.sleep(self.retry_delay)

            except TimeoutError as e:
                elapsed_ms = (time.time() - start_time) * 1000
                last_error = e
                warnings_list.append(f"第 {attempt+1} 次超时错误: {str(e)[:100]}")
                if attempt < self.retries - 1:
                    time.sleep(self.retry_delay)

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                last_error = e
                warnings_list.append(f"第 {attempt+1} 次异常: {type(e).__name__}: {str(e)[:100]}")
                # 非网络异常不重试
                break

        # 所有重试失败
        return CallResult(
            status="failed",
            data=None,
            warnings=warnings_list,
            elapsed_ms=0.0
        )

    def _normalize_industry_sector(self, row: Dict[str, Any]) -> SectorSnapshot:
        """标准化行业板块数据"""
        return SectorSnapshot(
            sector_id=str(row.get("板块代码", row.get("code", ""))),
            name=str(row.get("板块名称", row.get("name", ""))),
            type=SectorType.INDUSTRY,
            price_change_pct=float(row.get("涨跌幅", row.get("change_pct", 0.0)) or 0.0),
            turnover=0.0,
            main_net_inflow=0.0,
            constituents=[],
            data_sources=["akshare/eastmoney_industry"],
            updated_at=datetime.now().isoformat(),
            data_quality_score=70.0,
        )

    def _normalize_concept_sector(self, row: Dict[str, Any]) -> SectorSnapshot:
        """标准化概念板块数据"""
        return SectorSnapshot(
            sector_id=str(row.get("板块代码", row.get("code", ""))),
            name=str(row.get("板块名称", row.get("name", ""))),
            type=SectorType.CONCEPT,
            price_change_pct=float(row.get("涨跌幅", row.get("change_pct", 0.0)) or 0.0),
            turnover=0.0,
            main_net_inflow=0.0,
            constituents=[],
            data_sources=["akshare/eastmoney_concept"],
            updated_at=datetime.now().isoformat(),
            data_quality_score=70.0,
        )

    def _normalize_constituent(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """标准化成分股数据"""
        return {
            "code": str(row.get("代码", row.get("code", ""))),
            "name": str(row.get("名称", row.get("name", ""))),
            "change_pct": float(row.get("涨跌幅", row.get("change_pct", 0.0)) or 0.0),
            "turnover": 0.0,
            "is_core": False,
        }

    def get_industry_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """
        获取行业板块列表

        使用 AkShare 的 stock_board_industry_name_em 接口。
        """
        ak = self._get_client()

        # 调用接口（带重试）
        result = self._safe_call(ak.stock_board_industry_name_em)

        if result.status == "failed" or result.data is None:
            warnings.warn(f"无法获取行业板块数据: {'; '.join(result.warnings)}")
            return []

        df = result.data

        # 转换为字典列表
        sectors = []
        for _, row in df.head(top_n).iterrows():
            try:
                sector = self._normalize_industry_sector(row.to_dict())
                sectors.append(sector)
            except Exception as e:
                warnings.warn(f"标准化行业板块失败: {str(e)}")

        # 输出日志
        if result.warnings:
            print(f"  行业板块接口警告: {'; '.join(result.warnings[:2])}")

        print(f"  获取到 {len(sectors)} 个行业板块（原始 {len(df)} 个，取前 {top_n} 个）")
        return sectors

    def get_concept_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """
        获取概念板块列表

        使用 AkShare 的 stock_board_concept_name_em 接口。
        """
        ak = self._get_client()

        # 调用接口（带重试）
        result = self._safe_call(ak.stock_board_concept_name_em)

        if result.status == "failed" or result.data is None:
            warnings.warn(f"无法获取概念板块数据: {'; '.join(result.warnings)}")
            return []

        df = result.data

        # 转换为字典列表
        sectors = []
        for _, row in df.head(top_n).iterrows():
            try:
                sector = self._normalize_concept_sector(row.to_dict())
                sectors.append(sector)
            except Exception as e:
                warnings.warn(f"标准化概念板块失败: {str(e)}")

        # 输出日志
        if result.warnings:
            print(f"  概念板块接口警告: {'; '.join(result.warnings[:2])}")

        print(f"  获取到 {len(sectors)} 个概念板块（原始 {len(df)} 个，取前 {top_n} 个）")
        return sectors

    def get_market_overview(self, as_of_date: str) -> Dict[str, Any]:
        """
        获取市场概览

        使用 AkShare 的 stock_zh_a_spot_em 接口获取全市场数据。
        """
        ak = self._get_client()

        # 调用接口（带重试）
        result = self._safe_call(ak.stock_zh_a_spot_em)

        if result.status == "failed" or result.data is None:
            warnings.warn(f"无法获取市场概览数据: {'; '.join(result.warnings)}")
            return {
                "advance_count": 0,
                "decline_count": 0,
                "limit_up_count": 0,
                "limit_down_count": 0,
                "total_turnover": 0,
                "index_change_pct": 0,
            }

        df = result.data

        # 计算涨跌家数
        change_pct_col = "涨跌幅"
        if change_pct_col in df.columns:
            advance_count = int((df[change_pct_col] > 0).sum())
            decline_count = int((df[change_pct_col] < 0).sum())
            limit_up_count = int((df[change_pct_col] >= 9.9).sum())
            limit_down_count = int((df[change_pct_col] <= -9.9).sum())
        else:
            advance_count = 0
            decline_count = 0
            limit_up_count = 0
            limit_down_count = 0

        # 计算总成交额
        amount_col = "成交额"
        total_turnover = float(df[amount_col].sum()) if amount_col in df.columns else 0

        return {
            "advance_count": advance_count,
            "decline_count": decline_count,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "total_turnover": total_turnover,
            "index_change_pct": 0,
        }

    def get_sector_constituents(
        self,
        sector_name: str,
        sector_type: SectorType
    ) -> CallResult:
        """
        获取板块成分股

        Args:
            sector_name: 板块名称（如"半导体"）
            sector_type: 板块类型

        Returns:
            CallResult: 包含成分股列表的结果
        """
        ak = self._get_client()

        try:
            if sector_type == SectorType.INDUSTRY:
                result = self._safe_call(ak.stock_board_industry_cons_em, symbol=sector_name)
            else:
                result = self._safe_call(ak.stock_board_concept_cons_em, symbol=sector_name)

            if result.status == "failed" or result.data is None:
                return CallResult(
                    status="degraded",
                    data=[],
                    warnings=[f"获取 {sector_name} 成分股失败: {'; '.join(result.warnings)}"]
                )

            df = result.data

            # 标准化成分股数据
            constituents = []
            for _, row in df.iterrows():
                try:
                    constituent = self._normalize_constituent(row.to_dict())
                    constituents.append(constituent)
                except Exception as e:
                    warnings.warn(f"标准化成分股失败: {str(e)}")

            return CallResult(
                status="ok",
                data=constituents,
                warnings=[],
                elapsed_ms=result.elapsed_ms
            )

        except Exception as e:
            return CallResult(
                status="failed",
                data=[],
                warnings=[f"获取 {sector_name} 成分股异常: {str(e)}"]
            )

    def get_sector_flows(
        self,
        as_of_date: str,
        sector_type: SectorType
    ) -> CallResult:
        """
        获取板块资金流向

        Args:
            as_of_date: 日期
            sector_type: 板块类型

        Returns:
            CallResult: 包含资金流向列表的结果
        """
        ak = self._get_client()

        try:
            # 确定资金流类型
            flow_type = "行业资金流" if sector_type == SectorType.INDUSTRY else "概念资金流"

            # 调用接口（带重试）
            result = self._safe_call(
                ak.stock_sector_fund_flow_rank,
                indicator="今日",
                sector_type=flow_type
            )

            if result.status == "failed" or result.data is None:
                return CallResult(
                    status="degraded",
                    data=[],
                    warnings=[f"获取 {flow_type} 失败: {'; '.join(result.warnings)}"]
                )

            df = result.data

            # 转换为字典列表
            flows = []
            for _, row in df.iterrows():
                try:
                    flow = {
                        "sector_name": str(row.get("名称", "")),
                        "main_net_inflow": float(row.get("主力净流入-净额", 0.0) or 0.0),
                        "main_net_inflow_pct": float(row.get("主力净流入-净占比", 0.0) or 0.0),
                    }
                    flows.append(flow)
                except Exception as e:
                    warnings.warn(f"标准化资金流向失败: {str(e)}")

            return CallResult(
                status="ok",
                data=flows,
                warnings=result.warnings,
                elapsed_ms=result.elapsed_ms
            )

        except Exception as e:
            return CallResult(
                status="failed",
                data=[],
                warnings=[f"获取资金流向异常: {str(e)}"]
            )
