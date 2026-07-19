"""
CLI 轮动参数测试

测试 CLI 的轮动相关参数。
"""

from pathlib import Path

import pytest

from theme_sector_radar.pipeline import run_pipeline


@pytest.fixture(autouse=True)
def _isolate_default_data_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def _run_day1_then_day2(
    report_root: Path,
    *,
    day1_date: str = "2026-06-27",
    compare_to: str | None = None,
    lookback_days: int = 5,
):
    run_pipeline(
        as_of_date=day1_date,
        top_n=5,
        output_dir=str(report_root / day1_date),
        offline_fixture=True,
        fixture_profile="rotation-day1",
        report_root=str(report_root),
    )

    return run_pipeline(
        as_of_date="2026-06-28",
        top_n=5,
        output_dir=str(report_root / "2026-06-28"),
        offline_fixture=True,
        fixture_profile="rotation-day2",
        compare_to=compare_to,
        lookback_days=lookback_days,
        report_root=str(report_root),
    )


class TestCliRotationArgs:
    """测试 CLI 轮动参数"""

    def test_cli_accepts_compare_to(self, tmp_path):
        """测试 CLI 接受 --compare-to 参数"""
        report_root = tmp_path / "reports" / "theme_sector_radar"
        report = _run_day1_then_day2(
            report_root,
            compare_to="2026-06-27",
        )

        assert report is not None
        assert report.comparison.get("compare_to_date") == "2026-06-27"
        assert report.comparison.get("comparison_status") == "ok"
        industry_rotation = report.rotation_summary["industry"]
        assert "芯片" in industry_rotation["new_entries"]
        assert "新能源汽车" in industry_rotation["dropped_out"]

    def test_cli_accepts_lookback_days(self, tmp_path):
        """测试 CLI 接受 --lookback-days 参数"""
        short_root = tmp_path / "short-lookback" / "theme_sector_radar"
        report_outside_lookback = _run_day1_then_day2(
            short_root,
            day1_date="2026-06-24",
            lookback_days=3,
        )
        boundary_root = tmp_path / "boundary-lookback" / "theme_sector_radar"
        report_at_boundary = _run_day1_then_day2(
            boundary_root,
            day1_date="2026-06-24",
            lookback_days=4,
        )

        assert report_outside_lookback is not None
        assert (
            report_outside_lookback.comparison.get("comparison_status")
            == "no_previous_data"
        )
        assert any(
            "所有板块标记为新晋" in warning
            for warning in report_outside_lookback.comparison.get("warnings", [])
        )
        assert report_at_boundary is not None
        assert report_at_boundary.comparison.get("comparison_status") == "ok"

    def test_compare_to_missing_does_not_crash(self, tmp_path):
        """测试 compare-to 缺失时 CLI 不崩溃"""
        report_root = tmp_path / "empty-reports" / "theme_sector_radar"
        with pytest.warns(
            UserWarning,
            match=r"未找到指定日期 2020-01-01 的历史快照",
        ):
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=str(report_root / "2026-06-28"),
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2020-01-01",  # 不存在的日期
                report_root=str(report_root),
            )

        assert report is not None
        # 应该有轮动数据，但所有板块标记为新条目
        assert report.rotation_summary is not None
        assert report.comparison.get("comparison_status") == "no_previous_data"
        assert any(
            "所有板块标记为新晋" in warning
            for warning in report.comparison.get("warnings", [])
        )
        assert Path.cwd() == tmp_path
        data_cache = tmp_path / "data_cache"
        assert not data_cache.exists() or not any(data_cache.iterdir())

    def test_lookback_no_history_does_not_crash(self, tmp_path):
        """测试 lookback 找不到历史时 CLI 不崩溃"""
        report_root = tmp_path / "empty-reports" / "theme_sector_radar"
        report = run_pipeline(
            as_of_date="2020-01-10",
            top_n=5,
            output_dir=str(report_root / "2020-01-10"),
            offline_fixture=True,
            fixture_profile="rotation-day2",
            lookback_days=5,
            report_root=str(report_root),
        )

        assert report is not None
        # 应该有轮动数据，但所有板块标记为新条目
        assert report.rotation_summary is not None
        assert report.comparison.get("comparison_status") == "no_previous_data"
        assert any(
            "所有板块标记为新晋" in warning
            for warning in report.comparison.get("warnings", [])
        )
        assert Path.cwd() == tmp_path
        data_cache = tmp_path / "data_cache"
        assert not data_cache.exists() or not any(data_cache.iterdir())

    def test_comparison_status_correct(self, tmp_path):
        """测试 comparison_status 正确"""
        # 有历史数据
        report_root = tmp_path / "with-history" / "theme_sector_radar"
        report_with_history = _run_day1_then_day2(
            report_root,
            compare_to="2026-06-27",
        )
        assert report_with_history.comparison.get("comparison_status") == "ok"

        # 无历史数据
        empty_report_root = tmp_path / "without-history" / "theme_sector_radar"
        with pytest.warns(
            UserWarning,
            match=r"未找到指定日期 2020-01-01 的历史快照",
        ):
            report_without_history = run_pipeline(
                as_of_date="2020-01-10",
                top_n=5,
                output_dir=str(empty_report_root / "2020-01-10"),
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2020-01-01",
                report_root=str(empty_report_root),
            )
        assert (
            report_without_history.comparison.get("comparison_status")
            == "no_previous_data"
        )
        assert any(
            "所有板块标记为新晋" in warning
            for warning in report_without_history.comparison.get("warnings", [])
        )
