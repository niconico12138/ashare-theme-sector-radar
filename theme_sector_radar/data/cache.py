"""
数据缓存管理

提供基于日期的数据缓存功能，支持 fallback 策略。
"""

import json
import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class DataCache:
    """数据缓存"""

    def __init__(self, cache_dir: str = None):
        """
        初始化缓存

        Args:
            cache_dir: 缓存目录，默认为 data_cache/
        """
        if cache_dir is None:
            cache_dir = "data_cache"
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_date_dir(self, as_of_date: str) -> str:
        """获取日期目录"""
        date_dir = os.path.join(self.cache_dir, as_of_date)
        os.makedirs(date_dir, exist_ok=True)
        return date_dir

    def get(self, key: str, as_of_date: str = None) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            key: 缓存键
            as_of_date: 日期，默认使用当前日期

        Returns:
            缓存的数据，不存在返回 None
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        date_dir = self._get_date_dir(as_of_date)
        filepath = os.path.join(date_dir, f"{key}.json")

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            warnings.warn(f"读取缓存失败: {filepath} - {str(e)}")
            return None

    def set(self, key: str, data: Any, as_of_date: str = None, metadata: dict = None):
        """
        设置缓存数据

        Args:
            key: 缓存键
            data: 要缓存的数据
            as_of_date: 日期
            metadata: 元数据（provider, created_at 等）
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        date_dir = self._get_date_dir(as_of_date)
        filepath = os.path.join(date_dir, f"{key}.json")

        # 构建缓存内容
        cache_content = {
            "metadata": metadata or {
                "provider": "unknown",
                "created_at": datetime.now().isoformat(),
                "as_of_date": as_of_date,
                "data_sources": [],
            },
            "data": data,
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cache_content, f, ensure_ascii=False, indent=2)
        except IOError as e:
            warnings.warn(f"写入缓存失败: {filepath} - {str(e)}")

    def has(self, key: str, as_of_date: str = None) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键
            as_of_date: 日期

        Returns:
            是否存在
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        date_dir = self._get_date_dir(as_of_date)
        filepath = os.path.join(date_dir, f"{key}.json")
        return os.path.exists(filepath)

    def delete(self, key: str, as_of_date: str = None):
        """
        删除缓存

        Args:
            key: 缓存键
            as_of_date: 日期
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        date_dir = self._get_date_dir(as_of_date)
        filepath = os.path.join(date_dir, f"{key}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def clear(self, as_of_date: str = None):
        """
        清空缓存

        Args:
            as_of_date: 指定日期清空，None 则清空全部
        """
        if as_of_date is None:
            # 清空整个缓存目录
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isdir(filepath):
                    import shutil
                    shutil.rmtree(filepath)
        else:
            # 清空指定日期
            date_dir = self._get_date_dir(as_of_date)
            if os.path.exists(date_dir):
                import shutil
                shutil.rmtree(date_dir)

    def find_fallback_cache(
        self,
        key: str,
        as_of_date: str,
        max_days: int = 7,
        min_data_count: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        查找最近可用的缓存

        Args:
            key: 缓存键
            as_of_date: 目标日期
            max_days: 最大回退天数
            min_data_count: 最小数据数量门槛

        Returns:
            缓存数据，包含元数据；如果没有找到返回 None
        """
        target_date = datetime.strptime(as_of_date, "%Y-%m-%d")

        for days_back in range(1, max_days + 1):
            check_date = target_date - timedelta(days=days_back)
            check_date_str = check_date.strftime("%Y-%m-%d")

            cache_data = self.get(key, check_date_str)
            if cache_data is None:
                continue

            # 检查数据是否可用
            data = cache_data.get("data", {})
            industry_count = len(data.get("industry_sectors", []))
            concept_count = len(data.get("concept_sectors", []))

            # 如果有行业或概念数据，认为可用
            if industry_count >= min_data_count or concept_count >= min_data_count:
                # 标记为 fallback
                if "metadata" in cache_data:
                    cache_data["metadata"]["is_fallback"] = True
                    cache_data["metadata"]["source_as_of_date"] = check_date_str
                else:
                    cache_data["metadata"] = {
                        "is_fallback": True,
                        "source_as_of_date": check_date_str,
                    }

                print(f"  使用缓存 fallback: {check_date_str} (行业 {industry_count} 个, 概念 {concept_count} 个)")
                return cache_data

        return None

    def list_dates(self) -> List[str]:
        """列出所有缓存日期"""
        dates = []
        if os.path.exists(self.cache_dir):
            for item in os.listdir(self.cache_dir):
                item_path = os.path.join(self.cache_dir, item)
                if os.path.isdir(item_path):
                    # 验证是否为日期格式
                    try:
                        datetime.strptime(item, "%Y-%m-%d")
                        dates.append(item)
                    except ValueError:
                        continue
        return sorted(dates, reverse=True)

    def get_cache_info(self, as_of_date: str = None) -> dict:
        """
        获取缓存信息

        Returns:
            缓存信息字典
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime("%Y-%m-%d")

        date_dir = self._get_date_dir(as_of_date)
        info = {
            "as_of_date": as_of_date,
            "cache_dir": date_dir,
            "files": [],
        }

        if os.path.exists(date_dir):
            for filename in os.listdir(date_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(date_dir, filename)
                    file_info = {
                        "filename": filename,
                        "size": os.path.getsize(filepath),
                        "modified": datetime.fromtimestamp(
                            os.path.getmtime(filepath)
                        ).isoformat(),
                    }
                    info["files"].append(file_info)

        return info
