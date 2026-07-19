"""
板块综合评分 Agent 测试

测试 sector_scoring_agent.py 模块的各项功能。
"""

import pytest

from theme_sector_radar.agents.sector_scoring import calculate_sector_scores
from theme_sector_radar.data.benchmark_provider import BenchmarkData, BenchmarkRecord
from theme_sector_radar.models import AgentStatus, SectorScore, SectorType


class TestSectorScoringAgent:
    """测试板块综合评分 Agent"""

    def _create_mock_sector(
        self,
        name: str,
        score: float = 50.0,
        **kwargs,
    ) -> SectorScore:
        """创建模拟板块数据"""
        return SectorScore(
            sector_id=f"test_{name}",
            name=name,
            type=SectorType.INDUSTRY,
            score=score,
            positive_score=score,
            risk_penalty=0.0,
            data_quality_score=60.0,
            **kwargs,
        )

    def test_empty_sectors(self):
        """测试空板块列表"""
        result = calculate_sector_scores(
            radar_sectors=[],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert result.data["scores"] == []

    def test_single_sector(self):
        """测试单个板块"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert len(result.data["scores"]) == 1
        assert result.data["scores"][0]["sector_name"] == "test_sector"

    def test_multiple_sectors(self):
        """测试多个板块"""
        sectors = [
            self._create_mock_sector("sector_a", 80.0),
            self._create_mock_sector("sector_b", 60.0),
            self._create_mock_sector("sector_c", 40.0),
        ]
        result = calculate_sector_scores(
            radar_sectors=sectors,
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert len(result.data["scores"]) == 3
        # 验证按分数排序
        scores = [s["sector_selection_score"] for s in result.data["scores"]]
        assert scores == sorted(scores, reverse=True)

    def test_with_history_data(self):
        """测试有历史数据"""
        sector = self._create_mock_sector("test_sector", 70.0)
        history_data = {
            "test_sector": {
                "recent_returns": [2.0, 1.0, 0.5],
                "total_return": 3.5,
                "positive_days": 2,
                "total_days": 3,
                "max_drawdown": -0.02,
                "volatility": 1.0,
                "history_days": 3,
            }
        }
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data=history_data,
            sector_type=SectorType.INDUSTRY,
        )
        assert result.status == AgentStatus.OK
        assert len(result.data["scores"]) == 1
        assert result.data["scores"][0]["history_days"] == 3

    def test_score_breakdown(self):
        """测试评分拆解"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "score_breakdown" in score_data
        assert "radar_score_component" in score_data["score_breakdown"]
        assert "momentum_component" in score_data["score_breakdown"]
        assert "relative_strength_component" in score_data["score_breakdown"]
        assert "persistence_component" in score_data["score_breakdown"]
        assert "drawdown_component" in score_data["score_breakdown"]
        assert "volatility_component" in score_data["score_breakdown"]
        assert "data_quality_component" in score_data["score_breakdown"]
        assert "risk_penalty" in score_data["score_breakdown"]

    def test_selection_level(self):
        """测试选择等级"""
        sector = self._create_mock_sector("test_sector", 90.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "selection_level" in score_data
        assert score_data["selection_level"] in [
            "strong_watch",
            "watch",
            "neutral",
            "cooling",
            "avoid",
        ]

    def test_rotation_phase(self):
        """测试轮动阶段"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "rotation_phase" in score_data
        assert score_data["rotation_phase"] in [
            "leading",
            "improving",
            "weakening",
            "lagging",
        ]

    def test_diagnostic_info(self):
        """测试诊断信息"""
        sector = self._create_mock_sector("test_sector", 70.0)
        result = calculate_sector_scores(
            radar_sectors=[sector],
            history_data={},
            sector_type=SectorType.INDUSTRY,
        )
        score_data = result.data["scores"][0]
        assert "strength_reasons" in score_data
        assert "risk_reasons" in score_data
        assert "watch_points" in score_data
        assert "data_warnings" in score_data
        assert isinstance(score_data["strength_reasons"], list)
        assert isinstance(score_data["risk_reasons"], list)
        assert isinstance(score_data["watch_points"], list)
        assert isinstance(score_data["data_warnings"], list)

    def test_burst_uses_preserved_market_activity_and_previous_rank(self):
        sectors = [
            self._create_mock_sector(
                "hot_riser",
                70.0,
                turnover=12_000_000_000,
                main_net_inflow=600_000_000,
                previous_rank=10,
            ),
            self._create_mock_sector(
                "quiet_flat",
                70.0,
                turnover=100_000_000,
                main_net_inflow=-200_000_000,
                previous_rank=2,
            ),
        ]
        history_data = {
            name: {
                "recent_returns": [1.0, 1.0, 1.0, 1.0, 1.0],
                "total_return": 5.0,
                "positive_days": 5,
                "total_days": 5,
                "max_drawdown": 0.0,
                "volatility": 0.0,
                "history_days": 5,
            }
            for name in ("hot_riser", "quiet_flat")
        }

        result = calculate_sector_scores(sectors, history_data)
        by_name = {row["sector_name"]: row for row in result.data["scores"]}

        assert (
            by_name["hot_riser"]["burst_breakdown"]["volume_or_heat_component"]
            > by_name["quiet_flat"]["burst_breakdown"]["volume_or_heat_component"]
        )
        assert (
            by_name["hot_riser"]["burst_breakdown"]["rank_jump_component"]
            > by_name["quiet_flat"]["burst_breakdown"]["rank_jump_component"]
        )

    def test_burst_uses_actual_history_source_risk(self):
        sector = self._create_mock_sector("source_test", 70.0)
        history_data = {
            "source_test": {
                "recent_returns": [1.0, 1.0, 1.0, 1.0, 1.0],
                "total_return": 5.0,
                "positive_days": 5,
                "total_days": 5,
                "max_drawdown": 0.0,
                "volatility": 0.0,
                "history_days": 5,
            }
        }

        cached = calculate_sector_scores(
            [sector],
            history_data,
            history_source="sector_history_cache",
        ).data["scores"][0]
        fallback = calculate_sector_scores(
            [sector],
            history_data,
            history_source="raw_snapshot_fallback",
        ).data["scores"][0]

        assert (
            fallback["burst_breakdown"]["burst_risk_penalty"]
            == cached["burst_breakdown"]["burst_risk_penalty"] + 3.0
        )
        assert fallback["short_term_burst_score"] == cached["short_term_burst_score"] - 3.0

    def test_unavailable_industry_price_state_reaches_derived_scores(self):
        sector = self._create_mock_sector("missing_price", 70.0)
        sector.score_breakdown["price_change_available"] = False
        history_data = {
            "missing_price": {
                "recent_returns": [12.0, 12.0, 12.0],
                "history_days": 3,
            }
        }

        row = calculate_sector_scores([sector], history_data).data["scores"][0]

        assert row["trend_breakdown"]["price_change_available"] is False
        assert row["burst_breakdown"]["price_change_available"] is False
        assert any("涨跌幅" in warning for warning in row["data_warnings"])

    def test_relative_strength_uses_same_trend_window_for_all_sectors(self):
        sectors = [
            self._create_mock_sector("window_a", 70.0),
            self._create_mock_sector("window_b", 70.0),
        ]
        history_data = {
            "window_a": {
                "recent_returns": [20.0] * 5 + [1.0] * 5,
                "total_return": 100.0,
                "positive_days": 10,
                "total_days": 10,
                "max_drawdown": 0.0,
                "volatility": 0.0,
                "history_days": 10,
            },
            "window_b": {
                "recent_returns": [-20.0] * 5 + [2.0] * 5,
                "total_return": -100.0,
                "positive_days": 5,
                "total_days": 10,
                "max_drawdown": -100.0,
                "volatility": 20.0,
                "history_days": 10,
            },
        }

        result = calculate_sector_scores(sectors, history_data, trend_window=5)
        by_name = {row["sector_name"]: row for row in result.data["scores"]}

        assert (
            by_name["window_a"]["trend_breakdown"]["relative_strength_component"]
            < by_name["window_b"]["trend_breakdown"]["relative_strength_component"]
        )

    def test_half_window_is_reported_as_partial_without_hard_cap(self):
        sector = self._create_mock_sector("partial", 90.0)
        history_data = {
            "partial": {
                "recent_returns": [2.0] * 5,
                "history_days": 5,
            }
        }

        score = calculate_sector_scores(
            [sector], history_data, trend_window=10
        ).data["scores"][0]

        assert score["trend_window_status"] == "partial_history"
        assert score["history_coverage_ratio"] == 0.5
        assert score["trend_breakdown"].get("_history_cap_applied") is not True

    def test_incomplete_ten_day_benchmark_falls_back_to_sector_median(self):
        sector = self._create_mock_sector("benchmark_term", 70.0)
        history_data = {
            "benchmark_term": {
                "recent_returns": [1.0] * 10,
                "history_days": 10,
            }
        }
        benchmark_data = BenchmarkData(
            benchmark_id="hs300",
            benchmark_name="沪深300",
            source="test",
            start_date="2026-01-01",
            end_date="2026-01-06",
            fetched_at="2026-01-06T00:00:00",
            status="ok",
            records=[
                BenchmarkRecord(
                    date=f"2026-01-{day:02d}",
                    close=100.0 + day,
                    pct_change=1.0 if day > 1 else 0.0,
                )
                for day in range(1, 7)
            ],
        )

        score = calculate_sector_scores(
            [sector],
            history_data,
            benchmark_data=benchmark_data,
            trend_window=10,
        ).data["scores"][0]

        assert score["benchmark_mode"] == "sector_median"
        assert score["benchmark_id"] is None
        assert any("10d" in warning for warning in calculate_sector_scores(
            [sector],
            history_data,
            benchmark_data=benchmark_data,
            trend_window=10,
        ).warnings)

    def test_derived_score_ties_are_explicit_and_stably_ordered(self):
        sectors = [
            self._create_mock_sector("板块B", 70.0),
            self._create_mock_sector("板块A", 70.0),
        ]

        rows = calculate_sector_scores(sectors, {}).data["scores"]

        assert [row["sector_name"] for row in rows] == ["板块A", "板块B"]
        assert [row["trend_rank"] for row in rows] == [1, 1]
        assert all(row["trend_rank_tied"] is True for row in rows)
        assert all(row["trend_rank_tie_count"] == 2 for row in rows)
        assert [row["burst_rank"] for row in rows] == [1, 1]
