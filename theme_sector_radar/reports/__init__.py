"""
报告模块

生成 JSON 和 Markdown 报告。
"""

from .json_report import generate_json_report
from .markdown_report import generate_markdown_report

__all__ = [
    "generate_json_report",
    "generate_markdown_report",
]
