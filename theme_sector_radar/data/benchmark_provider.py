"""
市场基准数据提供者

提供市场基准（如沪深300、中证500）的历史数据获取能力。
"""

import math
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkRecord:
    """基准记录"""
    date: str
    close: float
    pct_change: float = 0.0


@dataclass
class BenchmarkData:
    """基准数据"""
    benchmark_id: str
    benchmark_name: str
    source: str
    start_date: str
    end_date: str
    fetched_at: str
    status: str  # ok / degraded / failed
    records: List[BenchmarkRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BenchmarkProvider:
    """
    市场基准数据提供者

    支持获取沪深300、中证500等市场基准的历史数据。
    """

    # 支持的基准配置
    BENCHMARK_CONFIG = {
        "hs300": {
            "id": "hs300",
            "name": "沪深300",
            "symbol": "sh000300",
            "source": "akshare/stock_zh_index_daily",
        },
        "zz500": {
            "id": "zz500",
            "name": "中证500",
            "symbol": "sh000905",
            "source": "akshare/stock_zh_index_daily",
        },
        "zz1000": {
            "id": "zz1000",
            "name": "中证1000",
            "symbol": "sh000852",
            "source": "akshare/stock_zh_index_daily",
        },
    }

    def __init__(self, retries: int = 3, retry_delay: float = 1.0):
        """
        初始化基准提供者

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

    def _safe_call(self, func, *args, **kwargs) -> Optional[Any]:
        """
        安全调用 AkShare 接口

        Returns:
            调用结果，失败返回 None
        """
        for attempt in range(self.retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < self.retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    warnings.warn(f"AkShare call failed: {func.__name__} - {str(e)}")
                    return None

    def get_benchmark_config(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        """
        获取基准配置

        Args:
            benchmark_id: 基准 ID (hs300/zz500/zz1000)

        Returns:
            基准配置字典，不存在返回 None
        """
        return self.BENCHMARK_CONFIG.get(benchmark_id)

    def get_supported_benchmarks(self) -> List[str]:
        """获取支持的基准列表"""
        return list(self.BENCHMARK_CONFIG.keys())

    def fetch_benchmark_data(
        self,
        benchmark_id: str,
        start_date: str,
        end_date: str,
    ) -> BenchmarkData:
        """
        获取基准历史数据

        Args:
            benchmark_id: 基准 ID (hs300/zz500/zz1000)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            BenchmarkData 对象
        """
        config = self.get_benchmark_config(benchmark_id)
        if not config:
            return BenchmarkData(
                benchmark_id=benchmark_id,
                benchmark_name="unknown",
                source="unknown",
                start_date=start_date,
                end_date=end_date,
                fetched_at=datetime.now().isoformat(),
                status="failed",
                warnings=[f"Unknown benchmark: {benchmark_id}"],
            )

        # 获取数据
        df = self._safe_call(
            self._get_client().stock_zh_index_daily,
            symbol=config["symbol"]
        )

        if df is None or len(df) == 0:
            return BenchmarkData(
                benchmark_id=benchmark_id,
                benchmark_name=config["name"],
                source=config["source"],
                start_date=start_date,
                end_date=end_date,
                fetched_at=datetime.now().isoformat(),
                status="failed",
                warnings=["Failed to fetch benchmark data"],
            )

        # 转换日期格式
        import pandas as pd
        df['date'] = pd.to_datetime(df['date'])

        # 筛选日期范围
        df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        if len(df_filtered) == 0:
            return BenchmarkData(
                benchmark_id=benchmark_id,
                benchmark_name=config["name"],
                source=config["source"],
                start_date=start_date,
                end_date=end_date,
                fetched_at=datetime.now().isoformat(),
                status="degraded",
                warnings=[f"No data found for date range: {start_date} to {end_date}"],
            )

        # 转换为记录列表
        records = []
        for _, row in df_filtered.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
            records.append(BenchmarkRecord(
                date=date_str,
                close=float(row['close']),
                pct_change=0.0,  # 将在后续计算
            ))

        # 计算日收益率
        for i in range(len(records)):
            if i == 0:
                records[i].pct_change = 0.0
            else:
                prev_close = records[i-1].close
                curr_close = records[i].close
                if prev_close > 0:
                    records[i].pct_change = (curr_close - prev_close) / prev_close * 100

        return BenchmarkData(
            benchmark_id=benchmark_id,
            benchmark_name=config["name"],
            source=config["source"],
            start_date=start_date,
            end_date=end_date,
            fetched_at=datetime.now().isoformat(),
            status="ok",
            records=records,
        )

    def calculate_benchmark_returns(
        self,
        benchmark_data: BenchmarkData,
    ) -> Dict[str, float]:
        """
        计算基准收益率

        Args:
            benchmark_data: 基准数据

        Returns:
            仅包含拥有 N+1 个有效收盘价的期限收益率字典
        """
        records = sorted(benchmark_data.records, key=lambda record: record.date)
        if not records:
            return {}

        closes = [float(record.close) for record in records]
        if any(not math.isfinite(close) or close <= 0 for close in closes):
            raise ValueError("benchmark close values must be finite and positive")

        returns = {}
        for horizon in (1, 3, 5, 10, 20):
            if len(closes) < horizon + 1:
                continue
            start_close = closes[-(horizon + 1)]
            returns[f"{horizon}d"] = round(
                (closes[-1] / start_close - 1.0) * 100.0,
                4,
            )
        return returns
