"""
历史快照加载器

提供历史快照读取功能。
"""

import json
import os
import warnings
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def load_previous_snapshot(
    current_date: str,
    compare_to: str = None,
    lookback_days: int = 5,
    report_dirs: List[str] = None,
    cache_dirs: List[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    加载历史快照

    Args:
        current_date: 当前日期 (YYYY-MM-DD)
        compare_to: 指定比较日期
        lookback_days: 回溯天数
        report_dirs: 报告目录列表
        cache_dirs: 缓存目录列表

    Returns:
        历史快照数据，如果找不到返回 None
    """
    if report_dirs is None:
        report_dirs = ["reports/theme_sector_radar"]
    if cache_dirs is None:
        cache_dirs = ["data_cache"]

    # 如果指定了 compare-to，直接查找该日期
    if compare_to:
        snapshot = _find_snapshot_by_date(
            compare_to, report_dirs, cache_dirs
        )
        if snapshot:
            return snapshot
        else:
            warnings.warn(f"未找到指定日期 {compare_to} 的历史快照")
            return None

    # 在 lookback_days 内查找最近可用快照
    current = datetime.strptime(current_date, "%Y-%m-%d")
    for days_back in range(1, lookback_days + 1):
        check_date = (current - timedelta(days=days_back)).strftime("%Y-%m-%d")
        snapshot = _find_snapshot_by_date(
            check_date, report_dirs, cache_dirs
        )
        if snapshot:
            return snapshot

    return None


def _find_snapshot_by_date(
    date_str: str,
    report_dirs: List[str],
    cache_dirs: List[str],
) -> Optional[Dict[str, Any]]:
    """
    按日期查找快照

    Args:
        date_str: 日期字符串 (YYYY-MM-DD)
        report_dirs: 报告目录列表
        cache_dirs: 缓存目录列表

    Returns:
        快照数据，如果找不到返回 None
    """
    # 优先从报告目录查找
    for report_dir in report_dirs:
        # 尝试直接匹配日期目录
        json_path = os.path.join(report_dir, date_str, "theme_sector_radar.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
            except Exception as e:
                warnings.warn(f"读取报告快照失败: {json_path} - {str(e)}")

        # 尝试查找包含日期的目录（如 rotation-day1, phase4-fixture-full 等）
        if os.path.exists(report_dir):
            # 收集所有匹配的目录
            matching_dirs = []
            for dirname in os.listdir(report_dir):
                # 检查目录名是否以日期开头或包含日期
                if dirname.startswith(date_str) or date_str in dirname:
                    json_path = os.path.join(report_dir, dirname, "theme_sector_radar.json")
                    if os.path.exists(json_path):
                        matching_dirs.append((dirname, json_path))

            # 优先查找有数据的报告
            for dirname, json_path in matching_dirs:
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # 优先返回有数据的报告
                    if data.get("industry_top") or data.get("concept_top"):
                        return data
                except Exception as e:
                    warnings.warn(f"读取报告快照失败: {json_path} - {str(e)}")

            # 如果没有有数据的报告，返回第一个
            if matching_dirs:
                _, json_path = matching_dirs[0]
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return data
                except Exception as e:
                    warnings.warn(f"读取报告快照失败: {json_path} - {str(e)}")

    # 备选从缓存目录查找
    for cache_dir in cache_dirs:
        cache_path = os.path.join(cache_dir, date_str, "raw_snapshot.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
            except Exception as e:
                warnings.warn(f"读取缓存快照失败: {cache_path} - {str(e)}")

    return None


def find_available_dates(
    lookback_days: int = 30,
    report_dirs: List[str] = None,
    cache_dirs: List[str] = None,
) -> List[str]:
    """
    查找可用的历史日期

    Args:
        lookback_days: 回溯天数
        report_dirs: 报告目录列表
        cache_dirs: 缓存目录列表

    Returns:
        可用日期列表（降序）
    """
    if report_dirs is None:
        report_dirs = ["reports/theme_sector_radar"]
    if cache_dirs is None:
        cache_dirs = ["data_cache"]

    available_dates = []
    today = datetime.now()

    for days_back in range(lookback_days):
        check_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        snapshot = _find_snapshot_by_date(
            check_date, report_dirs, cache_dirs
        )
        if snapshot:
            available_dates.append(check_date)

    return available_dates
