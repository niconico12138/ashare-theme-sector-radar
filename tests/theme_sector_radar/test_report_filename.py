"""
Report Filename 测试

覆盖：
- sanitize_label 安全化处理
- build_report_filename 构造
- 空 label 不改变文件名
- 特殊字符被过滤
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.report_filename import sanitize_label, build_report_filename


# ============================================================
# Tests
# ============================================================

class TestSanitizeLabel:
    """测试 label 安全化。"""

    def test_sanitize_label_alphanumeric(self):
        """字母数字应保留。"""
        assert sanitize_label("phase41") == "phase41"

    def test_sanitize_label_with_underscore(self):
        """下划线应保留。"""
        assert sanitize_label("phase_41") == "phase_41"

    def test_sanitize_label_with_hyphen(self):
        """短横线应保留。"""
        assert sanitize_label("phase-41") == "phase-41"

    def test_sanitize_label_special_chars(self):
        """特殊字符应被过滤。"""
        assert sanitize_label("phase 41!") == "phase41"
        assert sanitize_label("phase@41#") == "phase41"

    def test_sanitize_label_empty(self):
        """空 label 应返回空字符串。"""
        assert sanitize_label("") == ""


class TestBuildReportFilename:
    """测试文件名构造。"""

    def test_build_filename_without_label(self):
        """无 label 时不应添加 label。"""
        result = build_report_filename("bars_group_discrimination", "2026-04-01", "2026-07-10")
        assert result == "bars_group_discrimination_2026-04-01_2026-07-10"

    def test_build_filename_with_label(self):
        """有 label 时应添加 label。"""
        result = build_report_filename("bars_group_discrimination", "2026-04-01", "2026-07-10", "phase41")
        assert result == "bars_group_discrimination_2026-04-01_2026-07-10_phase41"

    def test_build_filename_with_special_label(self):
        """特殊字符 label 应被安全化。"""
        result = build_report_filename("bars_group_discrimination", "2026-04-01", "2026-07-10", "phase 41!")
        assert result == "bars_group_discrimination_2026-04-01_2026-07-10_phase41"

    def test_build_filename_with_empty_label(self):
        """空 label 不应改变文件名。"""
        result = build_report_filename("bars_group_discrimination", "2026-04-01", "2026-07-10", "")
        assert result == "bars_group_discrimination_2026-04-01_2026-07-10"
