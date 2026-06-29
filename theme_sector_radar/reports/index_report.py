"""
报告索引生成

生成 index.json 和 index.md。
只扫描标准日报目录 YYYY-MM-DD，不扫描实验目录。
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List


def generate_index_json(
    report_root: str,
    reports: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    生成 index.json

    Args:
        report_root: 报告根目录
        reports: 报告信息列表

    Returns:
        索引字典
    """
    return {
        "generated_at": datetime.now().isoformat(),
        "report_root": report_root,
        "reports": reports,
    }


def generate_index_md(
    report_root: str,
    reports: List[Dict[str, Any]]
) -> str:
    """
    生成 index.md

    Args:
        report_root: 报告根目录
        reports: 报告信息列表

    Returns:
        Markdown 字符串
    """
    lines = []

    # 标题
    lines.append("# A股行业/概念板块雷达日报索引")
    lines.append("")

    # 表格头
    lines.append("| 日期 | 状态 | 数据质量 | 市场温度 | 行业前三 | 概念前三 | 新晋 | 快速升温 | 风险升高 | 报告 |")
    lines.append("|------|------|---------|---------|---------|---------|------|---------|---------|------|")

    # 表格行
    for report in reports:
        date = report.get("as_of_date", "")
        status = report.get("status", "unknown")
        quality = report.get("data_quality_score", 0)
        temp = report.get("market_temperature_label", "unknown")

        # 行业前三
        industries = ", ".join(report.get("top_industries", [])[:3])
        if not industries:
            industries = "-"

        # 概念前三
        concepts = ", ".join(report.get("top_concepts", [])[:3])
        if not concepts:
            concepts = "-"

        # 新晋
        new_entries = ", ".join(report.get("new_entries", [])[:3])
        if not new_entries:
            new_entries = "-"

        # 快速升温
        rising = ", ".join(report.get("rising_fast", [])[:3])
        if not rising:
            rising = "-"

        # 风险升高
        risk_up = ", ".join(report.get("risk_up", [])[:3])
        if not risk_up:
            risk_up = "-"

        # 报告链接
        md_path = report.get("markdown_path", "")
        if md_path and os.path.exists(md_path):
            # 使用相对路径
            rel_path = os.path.relpath(md_path, report_root)
            report_link = f"[报告]({rel_path})"
        else:
            report_link = "-"

        lines.append(
            f"| {date} | {status} | {quality:.0f} | {temp} | "
            f"{industries} | {concepts} | {new_entries} | "
            f"{rising} | {risk_up} | {report_link} |"
        )

    lines.append("")

    # 说明
    lines.append("**说明**:")
    lines.append("- 状态: ok (正常) / degraded (降级) / failed (失败)")
    lines.append("- 新晋: 今日进入 Top N 的板块")
    lines.append("- 快速升温: 排名或评分大幅上升的板块")
    lines.append("- 风险升高: 风险扣分增加的板块")
    lines.append("")

    return "\n".join(lines)


def is_standard_daily_dir(dirname: str) -> bool:
    """
    检查是否为标准日报目录

    标准日报目录格式: YYYY-MM-DD
    不匹配: YYYY-MM-DD-phase*, YYYY-MM-DD-rotation*, YYYY-MM-DD-akshare* 等
    """
    # 标准格式: YYYY-MM-DD
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    return bool(re.match(pattern, dirname))


def scan_daily_reports(
    report_root: str,
    include_experiments: bool = False
) -> List[str]:
    """
    扫描日报目录

    Args:
        report_root: 报告根目录
        include_experiments: 是否包含实验目录

    Returns:
        标准日报日期列表
    """
    if not os.path.exists(report_root):
        return []

    dates = []
    for dirname in os.listdir(report_root):
        dirpath = os.path.join(report_root, dirname)

        # 只处理目录
        if not os.path.isdir(dirpath):
            continue

        # 检查是否为标准日报目录
        if is_standard_daily_dir(dirname):
            # 检查是否存在报告文件
            report_path = os.path.join(dirpath, "theme_sector_radar.json")
            if os.path.exists(report_path):
                dates.append(dirname)
        elif include_experiments:
            # 实验目录需要显式参数
            report_path = os.path.join(dirpath, "theme_sector_radar.json")
            if os.path.exists(report_path):
                dates.append(dirname)

    return sorted(dates)
