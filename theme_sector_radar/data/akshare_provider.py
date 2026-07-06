"""
AkShare 数据提供者

提供真实 AkShare 行业/概念板块数据获取能力。
支持重试、降级和缓存 fallback。
支持东方财富 (EM) 和同花顺 (THS) 两个数据源。
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
    error_type: str = ""  # 异常类型摘要
    error_message: str = ""  # 异常信息摘要

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class ProviderStatusInfo:
    """数据提供者状态信息"""
    effective_provider: str = "akshare"  # akshare / ths / mixed
    industry_source: str = ""  # akshare/eastmoney_industry / akshare/ths_industry
    concept_source: str = ""  # akshare/eastmoney_concept / akshare/ths_concept
    fallback_used: bool = False
    fallback_provider: str = ""
    fallback_reason: str = ""
    industry_count: int = 0
    concept_count: int = 0
    em_industry_error: str = ""
    em_concept_error: str = ""
    concept_price_change_available: bool = True  # 概念涨跌幅是否可用


class AkShareProvider(DataProvider):
    """
    AkShare 数据提供者

    基于 AkShare 东方财富接口获取行业/概念板块数据。
    支持重试、降级和错误处理。
    """

    def __init__(self, retries: int = 3, retry_delay: float = 1.0, prefer_ths: bool = False):
        """
        初始化 AkShare 提供者

        Args:
            retries: 重试次数
            retry_delay: 重试延迟（秒）
            prefer_ths: 是否优先使用同花顺数据源（默认 False，先尝试东方财富）
        """
        self._client = None
        self.retries = retries
        self.retry_delay = retry_delay
        self.prefer_ths = prefer_ths
        # Provider status tracking
        self._status_info = ProviderStatusInfo()

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
        error_type = ""
        error_message = ""

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
                error_type = "ConnectionError"
                error_message = str(e)[:200]
                warnings_list.append(f"第 {attempt+1} 次网络连接错误: {str(e)[:100]}")
                if attempt < self.retries - 1:
                    time.sleep(self.retry_delay)

            except TimeoutError as e:
                elapsed_ms = (time.time() - start_time) * 1000
                last_error = e
                error_type = "TimeoutError"
                error_message = str(e)[:200]
                warnings_list.append(f"第 {attempt+1} 次超时错误: {str(e)[:100]}")
                if attempt < self.retries - 1:
                    time.sleep(self.retry_delay)

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                last_error = e
                error_type = type(e).__name__
                error_message = str(e)[:200]
                warnings_list.append(f"第 {attempt+1} 次异常: {type(e).__name__}: {str(e)[:100]}")
                # 非网络异常不重试
                break

        # 所有重试失败
        return CallResult(
            status="failed",
            data=None,
            warnings=warnings_list,
            elapsed_ms=0.0,
            error_type=error_type,
            error_message=error_message
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

    # ==================== THS (同花顺) 数据源方法 ====================

    def _get_ths_industry_summary(self) -> CallResult:
        """
        获取同花顺行业板块汇总数据（含涨跌幅）

        Returns:
            CallResult: 包含 DataFrame 的结果，列名为 [排名, 板块名称, 涨跌幅, ...]
        """
        ak = self._get_client()

        result = self._safe_call(ak.stock_board_industry_summary_ths)

        if result.status == "failed" or result.data is None:
            return CallResult(
                status="failed",
                data=None,
                warnings=[f"获取同花顺行业汇总失败: {'; '.join(result.warnings)}"]
            )

        df = result.data

        # 同花顺汇总列位置: 0=排名, 1=板块名称, 2=涨跌幅, 3=总成交额, 4=主力净流入
        # 将其标准化为 EM 风格的列名
        if len(df.columns) >= 3:
            df标准化 = df.rename(columns={
                df.columns[0]: '排名',
                df.columns[1]: '板块名称',
                df.columns[2]: '涨跌幅',
                df.columns[3]: '总成交额' if len(df.columns) > 3 else '成交额',
                df.columns[4]: '主力净流入' if len(df.columns) > 4 else 'main_net_inflow',
            })
            return CallResult(
                status="ok",
                data=df标准化,
                warnings=[],
                elapsed_ms=result.elapsed_ms
            )
        else:
            return CallResult(
                status="failed",
                data=None,
                warnings=["同花顺行业汇总列数不足"]
            )

    def _get_ths_concept_names(self) -> CallResult:
        """
        获取同花顺概念板块名称列表

        Returns:
            CallResult: 包含 DataFrame 的结果
        """
        ak = self._get_client()

        result = self._safe_call(ak.stock_board_concept_name_ths)

        if result.status == "failed" or result.data is None:
            return CallResult(
                status="failed",
                data=None,
                warnings=[f"获取同花顺概念名称失败: {'; '.join(result.warnings)}"]
            )

        return CallResult(
            status="ok",
            data=result.data,
            warnings=[],
            elapsed_ms=result.elapsed_ms
        )

    def _try_ths_industry(self, as_of_date: str, top_n: int) -> List[SectorSnapshot]:
        """
        尝试使用同花顺获取行业板块数据

        Args:
            as_of_date: 日期
            top_n: 获取前 N 个板块

        Returns:
            List[SectorSnapshot]: 板块列表
        """
        print("  尝试同花顺 (THS) 行业板块数据...")

        # 获取汇总数据（含涨跌幅）
        result = self._get_ths_industry_summary()

        if result.status == "failed" or result.data is None:
            warnings.warn(f"同花顺行业汇总获取失败: {'; '.join(result.warnings)}")
            return []

        df = result.data

        # 转换为字典列表
        sectors = []
        for _, row in df.head(top_n).iterrows():
            try:
                sector = self._normalize_ths_industry_sector(row.to_dict())
                sectors.append(sector)
            except Exception as e:
                warnings.warn(f"标准化同花顺行业板块失败: {str(e)}")

        if result.warnings:
            print(f"  同花顺行业板块警告: {'; '.join(result.warnings[:2])}")

        print(f"  从同花顺获取到 {len(sectors)} 个行业板块（原始 {len(df)} 个，取前 {top_n} 个）")
        return sectors

    def _try_ths_concept(self, as_of_date: str, top_n: int) -> List[SectorSnapshot]:
        """
        尝试使用同花顺获取概念板块数据

        Args:
            as_of_date: 日期
            top_n: 获取前 N 个板块

        Returns:
            List[SectorSnapshot]: 板块列表
        """
        print("  尝试同花顺 (THS) 概念板块数据...")

        result = self._get_ths_concept_names()

        if result.status == "failed" or result.data is None:
            warnings.warn(f"同花顺概念名称获取失败: {'; '.join(result.warnings)}")
            return []

        df = result.data

        # 转换为字典列表（同花顺概念列表无涨跌幅，设为 0）
        sectors = []
        for _, row in df.head(top_n).iterrows():
            try:
                sector = self._normalize_ths_concept_sector(row.to_dict())
                sectors.append(sector)
            except Exception as e:
                warnings.warn(f"标准化同花顺概念板块失败: {str(e)}")

        if result.warnings:
            print(f"  同花顺概念板块警告: {'; '.join(result.warnings[:2])}")

        print(f"  从同花顺获取到 {len(sectors)} 个概念板块（原始 {len(df)} 个，取前 {top_n} 个）")
        return sectors

    def _normalize_ths_industry_sector(self, row: Dict[str, Any]) -> SectorSnapshot:
        """标准化同花顺行业板块数据"""
        # 尝试获取板块名称（可能在不同列位置）
        name = str(row.get('板块名称', row.get('板块', '')))
        if not name:
            # 尝试第二列（通常是名称）
            for key in list(row.keys()):
                val = str(row[key])
                if len(val) > 1 and not val.isdigit():
                    name = val
                    break

        # 涨跌幅
        change_pct = 0.0
        for key in ['涨跌幅', '涨跌']:
            if key in row:
                try:
                    change_pct = float(row[key] or 0.0)
                    break
                except (ValueError, TypeError):
                    pass

        # 主力净流入
        main_net_inflow = 0.0
        for key in ['主力净流入', '主力净流入-净额']:
            if key in row:
                try:
                    main_net_inflow = float(row[key] or 0.0)
                    break
                except (ValueError, TypeError):
                    pass

        return SectorSnapshot(
            sector_id=f"ths_industry_{name}",
            name=name,
            type=SectorType.INDUSTRY,
            price_change_pct=change_pct,
            turnover=0.0,
            main_net_inflow=main_net_inflow,
            constituents=[],
            data_sources=["akshare/ths_industry"],
            updated_at=datetime.now().isoformat(),
            data_quality_score=80.0,  # THS 行业指数含涨跌幅，作为可用板块级数据
        )

    def _normalize_ths_concept_sector(self, row: Dict[str, Any]) -> SectorSnapshot:
        """标准化同花顺概念板块数据"""
        name = str(row.get('name', row.get('板块名称', '')))

        return SectorSnapshot(
            sector_id=f"ths_concept_{name}",
            name=name,
            type=SectorType.CONCEPT,
            price_change_pct=0.0,  # THS 概念列表无涨跌幅
            turnover=0.0,
            main_net_inflow=0.0,
            constituents=[],
            data_sources=["akshare/ths_concept"],
            updated_at=datetime.now().isoformat(),
            data_quality_score=50.0,  # 无涨跌幅数据，质量较低
            price_change_available=False,  # THS 概念列表无涨跌幅
        )

    def get_industry_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """
        获取行业板块列表

        优先使用东方财富 (EM)，如果失败则降级到同花顺 (THS)。
        """
        ak = self._get_client()

        # 如果优先使用 THS，直接调用
        if self.prefer_ths:
            sectors = self._try_ths_industry(as_of_date, top_n)
            self._status_info.industry_source = "akshare/ths_industry"
            self._status_info.industry_count = len(sectors)
            return sectors

        # 先尝试东方财富
        result = self._safe_call(ak.stock_board_industry_name_em)

        if result.status == "ok" and result.data is not None:
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

            print(f"  从东方财富获取到 {len(sectors)} 个行业板块（原始 {len(df)} 个，取前 {top_n} 个）")

            # 更新状态
            self._status_info.industry_source = "akshare/eastmoney_industry"
            self._status_info.industry_count = len(sectors)
            return sectors

        # 东方财富失败，降级到同花顺
        print("  东方财富行业板块接口不可用，降级到同花顺...")
        self._status_info.em_industry_error = f"{result.error_type}: {result.error_message[:100]}"
        sectors = self._try_ths_industry(as_of_date, top_n)

        # 更新状态
        self._status_info.fallback_used = True
        self._status_info.fallback_provider = "ths"
        self._status_info.fallback_reason = f"东方财富行业接口失败: {result.error_type}"
        self._status_info.industry_source = "akshare/ths_industry"
        self._status_info.industry_count = len(sectors)
        return sectors

    def get_concept_sectors(
        self,
        as_of_date: str,
        top_n: int = 50
    ) -> List[SectorSnapshot]:
        """
        获取概念板块列表

        优先使用东方财富 (EM)，如果失败则降级到同花顺 (THS)。
        """
        ak = self._get_client()

        # 如果优先使用 THS，直接调用
        if self.prefer_ths:
            sectors = self._try_ths_concept(as_of_date, top_n)
            self._status_info.concept_source = "akshare/ths_concept"
            self._status_info.concept_count = len(sectors)
            return sectors

        # 先尝试东方财富
        result = self._safe_call(ak.stock_board_concept_name_em)

        if result.status == "ok" and result.data is not None:
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

            print(f"  从东方财富获取到 {len(sectors)} 个概念板块（原始 {len(df)} 个，取前 {top_n} 个）")

            # 更新状态
            self._status_info.concept_source = "akshare/eastmoney_concept"
            self._status_info.concept_count = len(sectors)
            return sectors

        # 东方财富失败，降级到同花顺
        print("  东方财富概念板块接口不可用，降级到同花顺...")
        self._status_info.em_concept_error = f"{result.error_type}: {result.error_message[:100]}"
        sectors = self._try_ths_concept(as_of_date, top_n)

        # 更新状态
        self._status_info.fallback_used = True
        self._status_info.fallback_provider = "ths"
        if not self._status_info.fallback_reason:
            self._status_info.fallback_reason = f"东方财富概念接口失败: {result.error_type}"
        self._status_info.concept_source = "akshare/ths_concept"
        self._status_info.concept_count = len(sectors)
        self._status_info.concept_price_change_available = False  # THS 概念无涨跌幅
        return sectors

    def get_provider_status(self) -> ProviderStatusInfo:
        """
        获取数据提供者状态信息

        Returns:
            ProviderStatusInfo: 包含数据来源、fallback 状态等信息
        """
        # 确定 effective_provider：基于实际 source 字符串判断，而非仅 fallback_used
        ind_is_ths = "ths" in self._status_info.industry_source
        con_is_ths = "ths" in self._status_info.concept_source
        ind_is_em = "eastmoney" in self._status_info.industry_source
        con_is_em = "eastmoney" in self._status_info.concept_source

        if self._status_info.industry_source and self._status_info.concept_source:
            # 两个都有数据：检查实际 source
            if ind_is_ths and con_is_ths:
                self._status_info.effective_provider = "ths"
            elif ind_is_em and con_is_em:
                self._status_info.effective_provider = "akshare"
            else:
                # 一个是 THS，另一个是 EM → 混合
                self._status_info.effective_provider = "mixed"
        elif self._status_info.industry_source:
            self._status_info.effective_provider = "ths" if ind_is_ths else "akshare"
        elif self._status_info.concept_source:
            self._status_info.effective_provider = "ths" if con_is_ths else "akshare"
        elif self.prefer_ths:
            self._status_info.effective_provider = "ths"
        else:
            self._status_info.effective_provider = "akshare"

        return self._status_info

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
