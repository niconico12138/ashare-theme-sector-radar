"""
市场基准数据缓存

提供市场基准数据的缓存读写能力。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .benchmark_provider import BenchmarkData, BenchmarkRecord


class BenchmarkCache:
    """
    市场基准数据缓存

    支持将基准数据缓存到本地 JSON 文件。
    """

    def __init__(self, cache_dir: str = "data_cache/benchmarks"):
        """
        初始化缓存

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir

    def _get_cache_path(
        self,
        benchmark_id: str,
        start_date: str,
        end_date: str,
    ) -> str:
        """
        获取缓存文件路径

        Args:
            benchmark_id: 基准 ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            缓存文件路径
        """
        # 格式化日期范围
        start_fmt = start_date.replace("-", "")
        end_fmt = end_date.replace("-", "")
        filename = f"{start_fmt}_to_{end_fmt}.json"

        return os.path.join(self.cache_dir, benchmark_id, filename)

    def has_cache(
        self,
        benchmark_id: str,
        start_date: str,
        end_date: str,
    ) -> bool:
        """
        检查是否有缓存

        Args:
            benchmark_id: 基准 ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            是否有缓存
        """
        cache_path = self._get_cache_path(benchmark_id, start_date, end_date)
        return os.path.exists(cache_path)

    def get_cache(
        self,
        benchmark_id: str,
        start_date: str,
        end_date: str,
    ) -> Optional[BenchmarkData]:
        """
        获取缓存数据

        Args:
            benchmark_id: 基准 ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            BenchmarkData 对象，不存在返回 None
        """
        cache_path = self._get_cache_path(benchmark_id, start_date, end_date)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 转换为 BenchmarkData 对象
            records = [
                BenchmarkRecord(
                    date=r["date"],
                    close=r["close"],
                    pct_change=r.get("pct_change", 0.0),
                )
                for r in data.get("records", [])
            ]

            return BenchmarkData(
                benchmark_id=data["benchmark_id"],
                benchmark_name=data["benchmark_name"],
                source=data["source"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                fetched_at=data["fetched_at"],
                status=data["status"],
                records=records,
                warnings=data.get("warnings", []),
            )

        except Exception as e:
            warnings.warn(f"Failed to load benchmark cache: {str(e)}")
            return None

    def set_cache(self, benchmark_data: BenchmarkData):
        """
        保存基准数据到缓存

        Args:
            benchmark_data: 基准数据
        """
        # 创建目录
        benchmark_dir = os.path.join(self.cache_dir, benchmark_data.benchmark_id)
        os.makedirs(benchmark_dir, exist_ok=True)

        # 获取缓存路径
        cache_path = self._get_cache_path(
            benchmark_data.benchmark_id,
            benchmark_data.start_date,
            benchmark_data.end_date,
        )

        # 转换为字典
        data = {
            "benchmark_id": benchmark_data.benchmark_id,
            "benchmark_name": benchmark_data.benchmark_name,
            "source": benchmark_data.source,
            "start_date": benchmark_data.start_date,
            "end_date": benchmark_data.end_date,
            "fetched_at": benchmark_data.fetched_at,
            "status": benchmark_data.status,
            "records": [
                {
                    "date": r.date,
                    "close": r.close,
                    "pct_change": r.pct_change,
                }
                for r in benchmark_data.records
            ],
            "warnings": benchmark_data.warnings,
        }

        # 保存文件
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_cache(
        self,
        benchmark_id: str,
        start_date: str,
        end_date: str,
    ):
        """
        删除缓存

        Args:
            benchmark_id: 基准 ID
            start_date: 开始日期
            end_date: 结束日期
        """
        cache_path = self._get_cache_path(benchmark_id, start_date, end_date)
        if os.path.exists(cache_path):
            os.remove(cache_path)

    def list_cached_benchmarks(self) -> List[Dict[str, str]]:
        """
        列出已缓存的基准

        Returns:
            基准信息列表
        """
        benchmarks = []

        if not os.path.exists(self.cache_dir):
            return benchmarks

        for benchmark_id in os.listdir(self.cache_dir):
            benchmark_dir = os.path.join(self.cache_dir, benchmark_id)
            if not os.path.isdir(benchmark_dir):
                continue

            for filename in os.listdir(benchmark_dir):
                if filename.endswith(".json"):
                    # 解析文件名获取日期范围
                    parts = filename.replace(".json", "").split("_to_")
                    if len(parts) == 2:
                        benchmarks.append({
                            "benchmark_id": benchmark_id,
                            "start_date": parts[0],
                            "end_date": parts[1],
                            "file": os.path.join(benchmark_dir, filename),
                        })

        return benchmarks
