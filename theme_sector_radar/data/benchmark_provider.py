"""
市场基准数据提供者

提供市场基准（如沪深300、中证500）的历史数据获取能力。
"""

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
            包含 1d/3d/5d 收益率的字典
        """
        records = benchmark_data.records
        if not records:
            return {"1d": 0.0, "3d": 0.0, "5d": 0.0}

        # 计算累计收益率
        returns = [r.pct_change for r in records]

        # 1日收益率
        return_1d = returns[-1] if len(returns) >= 1 else 0.0

        # 3日收益率
        if len(returns) >= 3:
            return_3d = sum(returns[-3:])
        else:
            return_3d = sum(returns)

        # 5日收益率
        if len(returns) >= 5:
            return_5d = sum(returns[-5:])
        else:
            return_5d = sum(returns)

        # 10日收益率
        if len(returns) >= 10:
            return_10d = sum(returns[-10:])
        else:
            return_10d = sum(returns)

        # 20日收益率
        if len(returns) >= 20:
            return_20d = sum(returns[-20:])
        else:
            return_20d = sum(returns)

        return {
            "1d": round(return_1d, 4),
            "3d": round(return_3d, 4),
            "5d": round(return_5d, 4),
            "10d": round(return_10d, 4),
            "20d": round(return_20d, 4),
        }
