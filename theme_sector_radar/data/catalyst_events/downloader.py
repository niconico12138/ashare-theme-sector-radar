"""
催化事件下载器

支持从 AkShare 下载个股新闻，并通过成分股映射到板块。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import CatalystEvent, EVENT_TYPE_NEWS, FRESHNESS_SAME_DAY, FRESHNESS_RECENT, FRESHNESS_STALE, FRESHNESS_UNKNOWN
from .cache import CatalystEventCache
from .mapper import SymbolSectorMapper


class CatalystEventDownloader:
    """
    催化事件下载器

    支持 offline_fixture 和 network 两种模式。
    """

    def __init__(
        self,
        cache_root: str = "data_cache/catalyst_events",
        history_root: str = "data_cache/sector_history",
    ):
        self.cache = CatalystEventCache(cache_root)
        self.mapper = SymbolSectorMapper(history_root)

    def download(
        self,
        as_of_date: str,
        symbols: List[str],
        symbol_names: Optional[List[str]] = None,
        max_events_per_symbol: int = 5,
        lookback_days: int = 7,
        network: bool = False,
        offline_fixture: bool = False,
        fixture_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        下载催化事件

        Args:
            as_of_date: 基准日期
            symbols: 股票代码列表
            symbol_names: 股票名称列表
            max_events_per_symbol: 每个股票最大新闻数
            lookback_days: 回溯天数
            network: 是否联网
            offline_fixture: 是否使用 fixture
            fixture_data: fixture 数据

        Returns:
            下载结果
        """
        source_status = []
        all_events = []

        if offline_fixture and fixture_data:
            # 使用 fixture 数据
            events = self._process_fixture_data(
                fixture_data, as_of_date, lookback_days
            )
            all_events.extend(events)
            source_status.append({
                "source_id": "fixture",
                "status": "fixture",
                "requested_symbols": len(symbols),
                "success_count": len(symbols),
                "failed_count": 0,
                "warnings": [],
            })
        elif network:
            # 网络模式
            for symbol in symbols:
                try:
                    events = self._download_symbol_news(
                        symbol, as_of_date, lookback_days, max_events_per_symbol
                    )
                    all_events.extend(events)
                    source_status.append({
                        "source_id": "akshare_stock_news_em",
                        "status": "ok",
                        "requested_symbols": 1,
                        "success_count": 1,
                        "failed_count": 0,
                        "warnings": [],
                    })
                except Exception as e:
                    source_status.append({
                        "source_id": "akshare_stock_news_em",
                        "status": "failed",
                        "requested_symbols": 1,
                        "success_count": 0,
                        "failed_count": 1,
                        "warnings": [str(e)[:100]],
                    })
        else:
            # 离线模式，不访问网络
            source_status.append({
                "source_id": "none",
                "status": "skipped",
                "requested_symbols": len(symbols),
                "success_count": 0,
                "failed_count": 0,
                "warnings": ["网络模式未启用，跳过下载"],
            })

        # 映射到板块
        mapped_events = self.mapper.map_events_to_sectors(
            [e.to_dict() for e in all_events]
        )

        # 转换回 CatalystEvent
        final_events = [CatalystEvent.from_dict(e) for e in mapped_events]

        # 去重
        final_events = self.cache.deduplicate_events(final_events)

        # 计算统计
        mapped_count = sum(1 for e in final_events if not e.related_industries and not e.related_concepts)
        unmapped_count = len(final_events) - mapped_count

        return {
            "as_of_date": as_of_date,
            "mode": "fixture" if offline_fixture else ("network" if network else "offline"),
            "requested_symbols": len(symbols),
            "total_events": len(final_events),
            "mapped_to_sectors": unmapped_count,
            "unmapped": mapped_count,
            "events": final_events,
            "source_status": source_status,
        }

    def _download_symbol_news(
        self,
        symbol: str,
        as_of_date: str,
        lookback_days: int,
        max_events: int,
    ) -> List[CatalystEvent]:
        """下载单个股票的新闻"""
        events = []

        try:
            import akshare as ak
            df = ak.stock_news_em(symbol=symbol)

            if df is None or len(df) == 0:
                return events

            # 转换为 CatalystEvent
            cutoff_date = (datetime.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

            for _, row in df.head(max_events).iterrows():
                # 提取日期
                pub_date = str(row.get("发布时间", ""))
                if len(pub_date) >= 10:
                    pub_date = pub_date[:10]
                else:
                    pub_date = as_of_date

                # 检查日期范围
                if pub_date < cutoff_date:
                    continue

                # 计算新鲜度
                freshness = self._compute_freshness(pub_date, as_of_date)

                # 计算哈希
                raw_payload = row.to_dict() if hasattr(row, 'to_dict') else dict(row)
                payload_hash = CatalystEvent.compute_hash(raw_payload)

                event = CatalystEvent(
                    event_id=f"news_{symbol}_{payload_hash[:8]}",
                    event_date=pub_date,
                    source="akshare_stock_news_em",
                    source_url=str(row.get("新闻链接", "")),
                    title=str(row.get("新闻标题", "")),
                    summary=str(row.get("新闻内容", ""))[:200],
                    event_type=EVENT_TYPE_NEWS,
                    related_symbols=[symbol],
                    related_symbol_names=[],
                    related_industries=[],
                    related_concepts=[],
                    confidence=0.6,
                    freshness=freshness,
                    raw_payload_hash=payload_hash,
                    raw_payload=raw_payload,
                )
                events.append(event)

        except Exception as e:
            raise Exception(f"下载 {symbol} 新闻失败: {str(e)[:100]}")

        return events

    def _process_fixture_data(
        self,
        fixture_data: List[Dict[str, Any]],
        as_of_date: str,
        lookback_days: int,
    ) -> List[CatalystEvent]:
        """处理 fixture 数据"""
        events = []

        for item in fixture_data:
            event = CatalystEvent.from_dict(item)
            events.append(event)

        return events

    def _compute_freshness(self, event_date: str, as_of_date: str) -> str:
        """计算新鲜度"""
        try:
            event_dt = datetime.strptime(event_date, "%Y-%m-%d")
            as_of_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
            days_diff = (as_of_dt - event_dt).days

            if days_diff <= 0:
                return FRESHNESS_SAME_DAY
            elif days_diff <= 3:
                return FRESHNESS_RECENT
            elif days_diff <= 7:
                return FRESHNESS_STALE
            else:
                return FRESHNESS_UNKNOWN
        except Exception:
            return FRESHNESS_UNKNOWN
