"""
数据完整性测试

测试最小数量门槛和降级状态。
"""

import pytest

from theme_sector_radar.pipeline import _determine_report_status


class TestDataCompleteness:
    """测试数据完整性"""

    def test_status_ok_when_sufficient_data(self):
        """测试数据充足时状态为 ok"""
        config = {"industry_min_count": 20, "concept_min_count": 20}

        status = _determine_report_status(
            industry_count=25,
            concept_count=30,
            config=config,
        )
        assert status == "ok"

    def test_status_degraded_when_industry_low(self):
        """测试行业数据不足时状态为 degraded"""
        config = {"industry_min_count": 20, "concept_min_count": 20}

        status = _determine_report_status(
            industry_count=15,
            concept_count=25,
            config=config,
        )
        assert status == "degraded"

    def test_status_degraded_when_concept_low(self):
        """测试概念数据不足时状态为 degraded"""
        config = {"industry_min_count": 20, "concept_min_count": 20}

        status = _determine_report_status(
            industry_count=25,
            concept_count=15,
            config=config,
        )
        assert status == "degraded"

    def test_status_failed_when_both_zero(self):
        """测试两者都为 0 时状态为 failed"""
        config = {"industry_min_count": 20, "concept_min_count": 20}

        status = _determine_report_status(
            industry_count=0,
            concept_count=0,
            config=config,
        )
        assert status == "failed"

    def test_status_degraded_when_both_very_low(self):
        """测试两者都极低时状态为 degraded"""
        config = {"industry_min_count": 20, "concept_min_count": 20}

        status = _determine_report_status(
            industry_count=5,
            concept_count=5,
            config=config,
        )
        assert status == "degraded"

    def test_status_ok_at_exact_threshold(self):
        """测试刚好达到阈值时状态为 ok"""
        config = {"industry_min_count": 20, "concept_min_count": 20}

        status = _determine_report_status(
            industry_count=20,
            concept_count=20,
            config=config,
        )
        assert status == "ok"

    def test_report_has_status_field(self):
        """测试报告包含 status 字段"""
        from theme_sector_radar.pipeline import run_pipeline

        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        assert hasattr(report, "status")
        assert report.status in ["ok", "degraded", "failed"]

    def test_report_has_data_completeness(self):
        """测试报告包含 data_completeness 字段"""
        from theme_sector_radar.pipeline import run_pipeline

        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        assert hasattr(report, "data_completeness")
        assert report.data_completeness.industry_count > 0
        assert report.data_completeness.concept_count > 0
