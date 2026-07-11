"""
Report Filename 构造模块

提供安全的文件名构造函数，支持 label 参数。
label 只允许字母数字、下划线、短横线；空 label 不改变文件名。
"""

from __future__ import annotations

import re


def sanitize_label(label: str) -> str:
    """安全化 label，只保留字母数字、下划线、短横线。"""
    if not label:
        return ""
    # 只保留字母数字、下划线、短横线
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', label)
    return sanitized


def build_report_filename(
    base_name: str,
    start_date: str,
    end_date: str,
    label: str = "",
) -> str:
    """构造报告文件名。

    Args:
        base_name: 基础文件名，如 "bars_group_discrimination"
        start_date: 开始日期，如 "2026-04-01"
        end_date: 结束日期，如 "2026-07-10"
        label: 可选标签，如 "phase41"

    Returns:
        文件名，如 "bars_group_discrimination_2026-04-01_2026-07-10_phase41"
    """
    sanitized_label = sanitize_label(label)
    if sanitized_label:
        return f"{base_name}_{start_date}_{end_date}_{sanitized_label}"
    else:
        return f"{base_name}_{start_date}_{end_date}"
