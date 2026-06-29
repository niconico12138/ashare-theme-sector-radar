"""
数据质量评估测试

测试数据质量评估功能。
"""

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestDataQualityAssessment:
    """测试数据质量评估"""

    def test_data_quality_score_in_range(self):
        """测试数据质量分在有效范围内"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        assert 0 <= report.data_quality_score <= 100

    def test_data_completeness_fields(self):
        """测试数据完整性字段"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        assert hasattr(report, "data_completeness")
        assert report.data_completeness.industry_count >= 0
        assert report.data_completeness.concept_count >= 0

    def test_provider_status_fields(self):
        """测试 provider 状态字段"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        assert hasattr(report, "provider_status")
        assert report.provider_status.industry_sectors in ["ok", "degraded", "failed"]
        assert report.provider_status.concept_sectors in ["ok", "degraded", "failed"]

    def test_full_fixture_has_good_quality(self):
        """测试 full fixture 有较好的数据质量"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        # full fixture 应该有较好的数据质量
        assert report.data_quality_score >= 50

    def test_minimal_fixture_has_lower_quality(self):
        """测试 minimal fixture 数据质量较低"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="minimal",
        )

        # minimal fixture 数据质量应该较低
        assert report.data_quality_score < 80
