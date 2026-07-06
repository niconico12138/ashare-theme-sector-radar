"""
催化事件数据模型

定义 CatalystEvent 用于外部催化事件的数据结构。
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CatalystEvent:
    """
    催化事件

    用于存储从外部数据源获取的催化事件信息。
    """
    event_id: str
    event_date: str
    source: str
    source_url: Optional[str] = None
    title: str = ""
    summary: str = ""
    event_type: str = "unknown"  # stock_news / announcement / policy / macro / unknown
    related_symbols: List[str] = field(default_factory=list)
    related_symbol_names: List[str] = field(default_factory=list)
    related_industries: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    confidence: float = 0.5
    freshness: str = "unknown"  # same_day / recent / stale / unknown
    raw_payload_hash: str = ""
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    mapping_status: str = "unknown"
    mapping_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_date": self.event_date,
            "source": self.source,
            "source_url": self.source_url,
            "title": self.title,
            "summary": self.summary,
            "event_type": self.event_type,
            "related_symbols": self.related_symbols,
            "related_symbol_names": self.related_symbol_names,
            "related_industries": self.related_industries,
            "related_concepts": self.related_concepts,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "raw_payload_hash": self.raw_payload_hash,
            "raw_payload": self.raw_payload,
            "mapping_status": self.mapping_status,
            "mapping_warnings": self.mapping_warnings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalystEvent":
        """从字典创建"""
        return cls(
            event_id=data.get("event_id", ""),
            event_date=data.get("event_date", ""),
            source=data.get("source", ""),
            source_url=data.get("source_url"),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            event_type=data.get("event_type", "unknown"),
            related_symbols=data.get("related_symbols", []),
            related_symbol_names=data.get("related_symbol_names", []),
            related_industries=data.get("related_industries", []),
            related_concepts=data.get("related_concepts", []),
            confidence=data.get("confidence", 0.5),
            freshness=data.get("freshness", "unknown"),
            raw_payload_hash=data.get("raw_payload_hash", ""),
            raw_payload=data.get("raw_payload", {}),
            mapping_status=data.get("mapping_status", "unknown"),
            mapping_warnings=data.get("mapping_warnings", []),
        )

    @staticmethod
    def compute_hash(payload: Dict[str, Any]) -> str:
        """计算原始数据的哈希"""
        payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(payload_str.encode("utf-8")).hexdigest()


# 事件类型定义
EVENT_TYPE_NEWS = "stock_news"
EVENT_TYPE_ANNOUNCEMENT = "announcement"
EVENT_TYPE_POLICY = "policy"
EVENT_TYPE_MACRO = "macro"
EVENT_TYPE_UNKNOWN = "unknown"

# 新鲜度定义
FRESHNESS_SAME_DAY = "same_day"
FRESHNESS_RECENT = "recent"
FRESHNESS_STALE = "stale"
FRESHNESS_UNKNOWN = "unknown"
