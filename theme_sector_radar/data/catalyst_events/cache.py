"""
催化事件缓存

提供催化事件的缓存读写功能。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import CatalystEvent


class CatalystEventCache:
    """
    催化事件缓存

    提供催化事件的缓存读写功能。
    """

    def __init__(self, cache_root: str = "data_cache/catalyst_events"):
        """
        初始化

        Args:
            cache_root: 缓存根目录
        """
        self.cache_root = cache_root

    def save_events(
        self,
        as_of_date: str,
        events: List[CatalystEvent],
        source_status: List[Dict[str, Any]],
    ) -> str:
        """
        保存事件到缓存

        Args:
            as_of_date: 日期
            events: 事件列表
            source_status: 数据源状态列表

        Returns:
            缓存目录路径
        """
        cache_dir = os.path.join(self.cache_root, as_of_date)
        os.makedirs(cache_dir, exist_ok=True)

        # 保存 events.json
        events_data = {
            "as_of_date": as_of_date,
            "generated_at": datetime.now().isoformat(),
            "event_count": len(events),
            "events": [e.to_dict() for e in events],
        }
        events_path = os.path.join(cache_dir, "events.json")
        with open(events_path, "w", encoding="utf-8") as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)

        # 保存 source_status.json
        status_data = {
            "as_of_date": as_of_date,
            "generated_at": datetime.now().isoformat(),
            "sources": source_status,
        }
        status_path = os.path.join(cache_dir, "source_status.json")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)

        return cache_dir

    def load_events(self, as_of_date: str) -> Optional[List[CatalystEvent]]:
        """
        从缓存加载事件

        Args:
            as_of_date: 日期

        Returns:
            事件列表，如果不存在返回 None
        """
        cache_dir = os.path.join(self.cache_root, as_of_date)
        events_path = os.path.join(cache_dir, "events.json")

        if not os.path.exists(events_path):
            return None

        try:
            with open(events_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            events = [CatalystEvent.from_dict(e) for e in data.get("events", [])]
            return events
        except Exception:
            return None

    def load_source_status(self, as_of_date: str) -> Optional[Dict[str, Any]]:
        """
        从缓存加载数据源状态

        Args:
            as_of_date: 日期

        Returns:
            数据源状态字典
        """
        cache_dir = os.path.join(self.cache_root, as_of_date)
        status_path = os.path.join(cache_dir, "source_status.json")

        if not os.path.exists(status_path):
            return None

        try:
            with open(status_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def exists(self, as_of_date: str) -> bool:
        """检查缓存是否存在"""
        cache_dir = os.path.join(self.cache_root, as_of_date)
        return os.path.exists(os.path.join(cache_dir, "events.json"))

    def deduplicate_events(self, events: List[CatalystEvent]) -> List[CatalystEvent]:
        """去重事件"""
        seen_hashes = set()
        unique_events = []

        for event in events:
            if event.raw_payload_hash not in seen_hashes:
                seen_hashes.add(event.raw_payload_hash)
                unique_events.append(event)

        return unique_events
