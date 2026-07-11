"""
Bars Data Lineage 测试

覆盖：
- 三个脚本的 summary 字段存在
- candidate_file_priority 正确
- forward_return_file_pattern 正确
- generated_at 存在
- candidate_root 和 forward_return_root 存在
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


# ============================================================
# Tests
# ============================================================

class TestDataLineage:
    """测试数据血缘字段。"""

    def test_diagnose_bars_group_discrimination_summary(self):
        """diagnose_bars_group_discrimination.py summary 应包含数据血缘字段。"""
        from diagnose_bars_group_discrimination import run_diagnosis
        from theme_sector_radar.reporting.report_filename import build_report_filename

        # 使用小范围测试
        candidate_root = PROJECT_ROOT / "reports" / "agent_bridge"
        forward_return_root = PROJECT_ROOT / "reports" / "forward_returns"

        diagnosis = run_diagnosis(
            start_date="2026-07-08",
            end_date="2026-07-08",
            candidate_root=candidate_root,
            forward_return_root=forward_return_root,
            horizons=["1d"],
        )

        summary = diagnosis["summary"]
        assert "candidate_root" in summary
        assert "forward_return_root" in summary
        assert "candidate_file_priority" in summary
        assert "forward_return_file_pattern" in summary
        assert "generated_at" in summary
        assert summary["candidate_file_priority"] == ["analysis_backfilled", "factor_backfilled", "original"]
        assert summary["forward_return_file_pattern"] == "{date}.json"

    def test_evaluate_bars_factor_shadow_policy_summary(self):
        """evaluate_bars_factor_shadow_policy.py summary 应包含数据血缘字段。"""
        from evaluate_bars_factor_shadow_policy import run_analysis

        candidate_root = PROJECT_ROOT / "reports" / "agent_bridge"
        forward_return_root = PROJECT_ROOT / "reports" / "forward_returns"

        analysis = run_analysis(
            start_date="2026-07-08",
            end_date="2026-07-08",
            candidate_root=candidate_root,
            forward_return_root=forward_return_root,
            horizons=["1d"],
        )

        summary = analysis["summary"]
        assert "candidate_root" in summary
        assert "forward_return_root" in summary
        assert "candidate_file_priority" in summary
        assert "forward_return_file_pattern" in summary
        assert "generated_at" in summary
        assert summary["candidate_file_priority"] == ["analysis_backfilled", "factor_backfilled", "original"]

    def test_validate_bars_factor_backfill_chain_summary(self):
        """validate_bars_factor_backfill_chain.py summary 应包含数据血缘字段。"""
        from validate_bars_factor_backfill_chain import run_validation

        candidate_root = PROJECT_ROOT / "reports" / "agent_bridge"
        forward_return_root = PROJECT_ROOT / "reports" / "forward_returns"

        validation = run_validation(
            start_date="2026-07-08",
            end_date="2026-07-08",
            candidate_root=candidate_root,
            forward_return_root=forward_return_root,
        )

        summary = validation["summary"]
        assert "candidate_root" in summary
        assert "forward_return_root" in summary
        assert "candidate_file_priority" in summary
        assert "forward_return_file_pattern" in summary
        assert "generated_at" in summary
        # 验证不再是误导性的 data_source
        assert "data_source" not in summary
        assert summary["candidate_file_priority"] == ["factor_backfilled", "analysis_backfilled", "original"]