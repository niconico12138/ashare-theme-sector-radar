"""
CLI 离线 Fixture 测试

测试 CLI 离线运行。
"""

import json
import os
import tempfile

import pytest

import theme_sector_radar.pipeline as pipeline_module
from theme_sector_radar.cli import main
from theme_sector_radar.data.fixture_provider import FixtureProvider
from theme_sector_radar.pipeline import run_pipeline


class TestCliOfflineFixture:
    """测试 CLI 离线 Fixture"""

    def test_pipeline_offline_fixture(self):
        """测试 Pipeline 离线运行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证报告生成
            assert report.report_type == "theme_sector_radar"
            assert report.as_of_date == "2026-06-28"
            assert len(report.industry_top) > 0
            assert len(report.concept_top) > 0
            summary = report.industry_three_layer_shadow_summary
            assert summary["three_layer_shadow_available_count"] == 0
            assert summary["three_layer_shadow_error_count"] == 0
            assert sum(summary["three_layer_shadow_state_counts"].values()) > 0

            # 验证文件生成
            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            snapshot_path = os.path.join(tmpdir, "raw_snapshot.json")

            assert os.path.exists(json_path)
            assert os.path.exists(md_path)
            assert os.path.exists(snapshot_path)

            # 验证 JSON 内容
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            assert json_data["report_type"] == "theme_sector_radar"
            assert json_data["industry_three_layer_shadow_summary"] == summary
            assert "disclaimer" in json_data
            assert "不作为个股操作依据" in json_data["disclaimer"]

            # 验证 Markdown 内容
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            assert "不作为个股操作依据或自动交易指令" in md_content

    def test_pipeline_feeds_as_of_sector_history_into_base_industry_score(
        self, tmp_path, monkeypatch
    ):
        history_root = tmp_path / "configured_sector_history"
        history_dir = history_root / "industry"
        history_dir.mkdir(parents=True)
        records = []
        close = 100.0
        for day in range(1, 22):
            close *= 1.005
            records.append(
                {
                    "date": f"2026-06-{day:02d}",
                    "close": close,
                    "turnover": 10_000_000_000,
                }
            )
        (history_dir / "半导体.json").write_text(
            json.dumps({"sector_name": "半导体", "records": records}),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

        report = run_pipeline(
            as_of_date="2026-06-21",
            top_n=10,
            output_dir=str(tmp_path / "report"),
            offline_fixture=True,
            history_root=str(history_root),
        )

        semiconductor = next(row for row in report.industry_top if row.name == "半导体")
        assert semiconductor.score_breakdown["trend_history_status"] == "reference_unavailable"
        assert semiconductor.score_breakdown["trend_history_days"] == 20

    def test_pipeline_degrades_when_formal_industry_history_root_is_missing(
        self, tmp_path
    ):
        report = run_pipeline(
            as_of_date="2026-06-21",
            top_n=5,
            output_dir=str(tmp_path / "report"),
            offline_fixture=True,
            history_root=str(tmp_path / "missing_sector_history"),
        )

        assert report.status == "degraded"
        assert any("历史目录不存在" in warning for warning in report.warnings)
        saved = json.loads((tmp_path / "report" / "theme_sector_radar.json").read_text(encoding="utf-8"))
        assert saved["warnings"] == report.warnings
        assert all(
            row.score_breakdown["trend_history_status"] == "insufficient_history"
            for row in report.industry_top
        )

    def test_pipeline_degrades_when_matched_history_is_not_five_day_mature(
        self, tmp_path
    ):
        history_root = tmp_path / "sector_history"
        history_dir = history_root / "industry"
        history_dir.mkdir(parents=True)
        sectors = FixtureProvider().get_industry_sectors("2026-06-21", 20)
        for sector in sectors:
            (history_dir / f"{sector.name}.json").write_text(
                json.dumps(
                    {
                        "sector_name": sector.name,
                        "records": [
                            {"date": "2026-06-20", "close": 100.0},
                            {"date": "2026-06-21", "close": 101.0},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        report = run_pipeline(
            as_of_date="2026-06-21",
            top_n=10,
            output_dir=str(tmp_path / "report"),
            offline_fixture=True,
            history_root=str(history_root),
        )

        assert report.status == "degraded"

    def test_pipeline_degrades_when_five_day_reference_coverage_is_fragmented(
        self, tmp_path
    ):
        history_root = tmp_path / "sector_history"
        history_dir = history_root / "industry"
        history_dir.mkdir(parents=True)
        sectors = FixtureProvider().get_industry_sectors("2026-06-21", 20)
        for index, sector in enumerate(sectors, start=1):
            dates = [
                f"2026-01-{index:02d}",
                "2026-06-17",
                "2026-06-18",
                "2026-06-19",
                "2026-06-20",
                "2026-06-21",
            ]
            (history_dir / f"{sector.name}.json").write_text(
                json.dumps(
                    {
                        "sector_name": sector.name,
                        "records": [
                            {"date": value, "close": 100.0 + offset}
                            for offset, value in enumerate(dates)
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        report = run_pipeline(
            as_of_date="2026-06-21",
            top_n=10,
            output_dir=str(tmp_path / "report"),
            offline_fixture=True,
            history_root=str(history_root),
        )

        assert report.status == "degraded"
        assert any("五日相对强度有效覆盖不足" in item for item in report.warnings)
        assert all(
            row.score_breakdown["trend_history_status"] == "reference_unavailable"
            for row in report.industry_top
        )

    def test_pipeline_propagates_degraded_ranking_agent_warnings(
        self, tmp_path, monkeypatch
    ):
        real_ranking = pipeline_module.generate_sector_ranking

        def degraded_ranking(*args, **kwargs):
            output = real_ranking(*args, **kwargs)
            output.status = type(output.status).DEGRADED
            output.warnings.append("synthetic ranking failure")
            return output

        monkeypatch.setattr(
            pipeline_module,
            "generate_sector_ranking",
            degraded_ranking,
        )

        report = run_pipeline(
            as_of_date="2026-06-21",
            top_n=5,
            output_dir=str(tmp_path / "report"),
            offline_fixture=True,
            history_root=str(tmp_path / "missing_sector_history"),
        )

        assert report.status == "degraded"
        assert "synthetic ranking failure" in report.warnings

    def test_pipeline_market_temperature(self):
        """测试市场温度计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证市场温度
            assert report.market_temperature.label in [
                "hot", "warm", "neutral", "cool", "cold"
            ]
            assert 0 <= report.market_temperature.score <= 100

    def test_pipeline_focus_levels(self):
        """测试关注等级"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证关注等级合法
            valid_levels = {"focus", "watch", "core_only", "caution", "avoid"}
            for score in report.industry_top + report.concept_top:
                assert score.focus_level.value in valid_levels

    def test_pipeline_risk_assessment(self):
        """测试风险评估"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证风险等级合法
            valid_risk_levels = {"low", "medium", "high"}
            for score in report.industry_top + report.concept_top:
                assert score.risk_level.value in valid_risk_levels

    def test_pipeline_data_quality(self):
        """测试数据质量"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证数据质量分
            assert 0 <= report.data_quality_score <= 100
