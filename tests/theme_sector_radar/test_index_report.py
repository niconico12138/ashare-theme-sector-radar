"""
报告索引测试

测试 index.json 和 index.md 生成。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.reports.index_report import generate_index_json, generate_index_md


class TestIndexReport:
    """测试报告索引"""

    def test_generate_index_json(self):
        """测试生成 index.json"""
        reports = [
            {
                "as_of_date": "2026-06-28",
                "status": "ok",
                "data_quality_score": 85.0,
                "market_temperature_label": "warm",
                "top_industries": ["人工智能", "半导体"],
                "top_concepts": ["CPO概念", "ChatGPT概念"],
                "new_entries": ["芯片"],
                "rising_fast": ["锂电池"],
                "persistent_strength": ["半导体"],
                "risk_up": [],
                "report_path": "reports/2026-06-28/theme_sector_radar.json",
                "markdown_path": "reports/2026-06-28/theme_sector_radar.md",
                "run_log_path": "reports/2026-06-28/run_log.json",
            }
        ]

        index = generate_index_json("reports", reports)

        assert "generated_at" in index
        assert "report_root" in index
        assert "reports" in index
        assert len(index["reports"]) == 1

    def test_generate_index_md(self):
        """测试生成 index.md"""
        reports = [
            {
                "as_of_date": "2026-06-28",
                "status": "ok",
                "data_quality_score": 85.0,
                "market_temperature_label": "warm",
                "top_industries": ["人工智能", "半导体"],
                "top_concepts": ["CPO概念", "ChatGPT概念"],
                "new_entries": ["芯片"],
                "rising_fast": ["锂电池"],
                "persistent_strength": ["半导体"],
                "risk_up": [],
                "report_path": "reports/2026-06-28/theme_sector_radar.json",
                "markdown_path": "reports/2026-06-28/theme_sector_radar.md",
                "run_log_path": "reports/2026-06-28/run_log.json",
            }
        ]

        md = generate_index_md("reports", reports)

        assert "A股行业/概念板块雷达日报索引" in md
        assert "2026-06-28" in md
        assert "人工智能" in md
        assert "CPO概念" in md

    def test_index_md_table_format(self):
        """测试 index.md 表格格式"""
        reports = [
            {
                "as_of_date": "2026-06-28",
                "status": "ok",
                "data_quality_score": 85.0,
                "market_temperature_label": "warm",
                "top_industries": ["人工智能", "半导体"],
                "top_concepts": ["CPO概念", "ChatGPT概念"],
                "new_entries": [],
                "rising_fast": [],
                "persistent_strength": [],
                "risk_up": [],
                "report_path": "reports/2026-06-28/theme_sector_radar.json",
                "markdown_path": "reports/2026-06-28/theme_sector_radar.md",
                "run_log_path": "reports/2026-06-28/run_log.json",
            }
        ]

        md = generate_index_md("reports", reports)

        # 验证表格格式
        assert "| 日期 | 状态 |" in md
        assert "|------|------|" in md
        assert "| 2026-06-28 | ok |" in md
