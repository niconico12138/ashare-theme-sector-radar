"""
排名逻辑测试

测试板块排名生成。
"""

import pytest

import theme_sector_radar.agents.ranking_report.sector_ranking_agent as ranking_module

from theme_sector_radar.agents.ranking_report.sector_ranking_agent import (
    generate_sector_ranking,
)
from theme_sector_radar.models import (
    FocusLevel,
    RiskLevel,
    SectorSnapshot,
    SectorType,
)


class TestSectorRanking:
    """测试板块排名"""

    def _create_sector(self, **kwargs) -> SectorSnapshot:
        """创建测试板块"""
        defaults = {
            "sector_id": "BK0428",
            "name": "半导体",
            "type": SectorType.INDUSTRY,
            "price_change_pct": 3.0,
            "turnover": 10_000_000_000,
            "main_net_inflow": 1_000_000_000,
            "data_quality_score": 80.0,
        }
        defaults.update(kwargs)
        return SectorSnapshot(**defaults)

    def test_ranking_output_structure(self):
        """测试排名输出结构"""
        sectors = [
            self._create_sector(sector_id="BK0428", name="半导体"),
            self._create_sector(sector_id="BK0437", name="人工智能"),
        ]

        output = generate_sector_ranking(sectors, [], top_n=10)

        assert "industry_top" in output.data
        assert "concept_top" in output.data
        assert len(output.data["industry_top"]) == 2

    def test_ranking_history_counts_exclude_industries_that_failed_scoring(
        self, monkeypatch
    ):
        sectors = [
            self._create_sector(sector_id="BK0001", name="正常行业"),
            self._create_sector(sector_id="BK0002", name="失败行业"),
        ]
        history = {
            sector.name: {"recent_returns": [0.5] * 20}
            for sector in sectors
        }
        real_calculate = ranking_module.calculate_industry_score_breakdown

        def fail_one(snapshot, *args, **kwargs):
            if snapshot.name == "失败行业":
                raise ValueError("synthetic scoring failure")
            return real_calculate(snapshot, *args, **kwargs)

        monkeypatch.setattr(
            ranking_module,
            "calculate_industry_score_breakdown",
            fail_one,
        )

        output = generate_sector_ranking(
            sectors,
            [],
            top_n=10,
            industry_history=history,
        )

        metadata = output.data["industry_trend_history"]
        assert output.status.value == "degraded"
        assert metadata["input_score_count"] == 2
        assert metadata["successful_score_count"] == 1
        assert metadata["failed_score_count"] == 1
        assert metadata["effective_5d_count"] == 1

    def test_ranking_sorted_by_score(self):
        """测试排名按分数排序"""
        sectors = [
            self._create_sector(sector_id="BK0428", name="半导体", price_change_pct=2.0),
            self._create_sector(sector_id="BK0437", name="人工智能", price_change_pct=5.0),
            self._create_sector(sector_id="BK0447", name="新能源", price_change_pct=3.0),
        ]

        output = generate_sector_ranking(
            sectors,
            [],
            top_n=10,
            industry_history={
                "半导体": {"recent_returns": [-0.2] * 20},
                "人工智能": {"recent_returns": [0.5] * 20},
                "新能源": {"recent_returns": [0.2] * 20},
            },
        )

        scores = output.data["industry_top"]
        assert scores[0]["name"] == "人工智能"
        assert scores[1]["name"] == "新能源"
        assert scores[2]["name"] == "半导体"

    def test_ranking_builds_cross_sectional_multi_day_trend_features(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="稳定走强", price_change_pct=1.0),
            self._create_sector(sector_id="BK0002", name="持续走弱", price_change_pct=1.0),
        ]
        history_data = {
            "稳定走强": {"recent_returns": [0.5] * 20},
            "持续走弱": {"recent_returns": [-0.5] * 20},
        }

        output = generate_sector_ranking(
            sectors,
            [],
            top_n=10,
            industry_history=history_data,
        )

        rows = output.data["industry_top"]
        assert rows[0]["name"] == "稳定走强"
        assert rows[0]["score_breakdown"]["trend_history_status"] == "ok"
        assert rows[0]["score_breakdown"]["trend_strength"] > rows[1]["score_breakdown"]["trend_strength"]

    def test_ranking_exposes_three_layer_shadow_without_changing_formal_score(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
        ]
        history_data = {
            "Industry A": {"recent_returns": [0.5] * 20},
            "Industry B": {"recent_returns": [-0.2] * 20},
        }

        output = generate_sector_ranking(
            sectors,
            [],
            top_n=10,
            industry_history=history_data,
        )

        for row in output.data["industry_top"]:
            shadow = row["score_breakdown"]["three_layer_shadow"]
            assert shadow["mode"] == "paper_shadow_research_only"
            assert set(shadow) >= {
                "time_series",
                "cross_section",
                "rank_momentum",
                "direction_score_shadow",
                "direction_state",
            }
            assert row["score"] == pytest.approx(
                row["positive_score"] - row["risk_penalty"]
            )

    def test_ranking_summarizes_three_layer_shadow_coverage_and_states(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
            self._create_sector(sector_id="BK0003", name="Industry C"),
        ]
        output = generate_sector_ranking(
            sectors,
            [],
            top_n=3,
            industry_history={
                "Industry A": {"recent_returns": [0.5] * 20},
                "Industry B": {"recent_returns": [-0.2] * 20},
            },
        )

        metadata = output.data["industry_trend_history"]
        state_counts = metadata["three_layer_shadow_state_counts"]
        assert metadata["three_layer_shadow_available_count"] == 2
        assert sum(state_counts.values()) == 3
        assert state_counts["unavailable"] == 1

    def test_ranking_exposes_direction_candidates_without_changing_formal_order(
        self, monkeypatch
    ):
        sectors = [
            self._create_sector(sector_id=f"BK{rank:04d}", name=f"Industry {rank}")
            for rank in range(1, 9)
        ]
        baseline = generate_sector_ranking(sectors, [], top_n=8)

        def synthetic_shadow(snapshot, *args, **kwargs):
            rank = int(snapshot.sector_id.removeprefix("BK"))
            return {
                "mode": "paper_shadow_research_only",
                "time_series": {"score": 45.0, "status": "ok"},
                "cross_section": {"score": 80.0, "status": "ok"},
                "rank_momentum": {"score": 70.0, "status": "ok"},
                "direction_score_shadow": 90.0 - rank,
                "direction_state": "watch",
                "risk_flags_observed": [],
            }

        monkeypatch.setattr(
            ranking_module,
            "calculate_industry_three_layer_shadow",
            synthetic_shadow,
        )
        output = generate_sector_ranking(sectors, [], top_n=8)

        assert [row["sector_id"] for row in output.data["industry_top"]] == [
            row["sector_id"] for row in baseline.data["industry_top"]
        ]
        selection = output.data["industry_direction_candidates_shadow"]
        assert len(selection["core_candidates"]) == 5
        assert len(selection["supplemental_candidates"]) == 2
        assert selection["observations"][0]["candidate_rank"] == 8
        assert output.data["industry_trend_history"][
            "three_layer_shadow_candidate_counts"
        ] == selection["selection_counts"]

    def test_direction_candidate_failure_cannot_remove_formal_industry_scores(
        self, monkeypatch
    ):
        sectors = [
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
        ]

        def fail_selection(*args, **kwargs):
            raise ValueError("synthetic candidate selection failure")

        monkeypatch.setattr(
            ranking_module,
            "select_industry_direction_candidates",
            fail_selection,
        )
        output = generate_sector_ranking(sectors, [], top_n=2)

        assert len(output.data["industry_top"]) == 2
        assert output.status.value == "ok"
        selection = output.data["industry_direction_candidates_shadow"]
        assert selection["error_status"] == "calculation_failed"
        assert sum(selection["selection_counts"].values()) == 0

    def test_three_layer_shadow_failure_cannot_remove_a_formal_industry_score(
        self, monkeypatch
    ):
        sector = self._create_sector(sector_id="BK0001", name="Industry A")

        def fail_shadow(*args, **kwargs):
            raise ValueError("synthetic shadow failure")

        monkeypatch.setattr(
            ranking_module,
            "calculate_industry_three_layer_shadow",
            fail_shadow,
        )
        output = generate_sector_ranking(
            [sector],
            [],
            top_n=1,
            industry_history={"Industry A": {"recent_returns": [0.5] * 20}},
        )

        assert output.status.value == "ok"
        assert len(output.data["industry_top"]) == 1
        row = output.data["industry_top"][0]
        assert row["score"] == pytest.approx(
            row["positive_score"] - row["risk_penalty"]
        )
        shadow = row["score_breakdown"]["three_layer_shadow"]
        assert shadow["direction_state"] == "unavailable"
        assert shadow["error_status"] == "calculation_failed"
        assert output.data["industry_trend_history"][
            "three_layer_shadow_error_count"
        ] == 1

    def test_three_layer_shadow_values_cannot_change_existing_formal_order(
        self, monkeypatch
    ):
        sectors = [
            self._create_sector(sector_id="BK0003", name="Industry C"),
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
        ]
        baseline = generate_sector_ranking(sectors, [], top_n=3)

        def synthetic_shadow(snapshot, *args, **kwargs):
            value = 100.0 if snapshot.sector_id == "BK0003" else 0.0
            return {
                "mode": "paper_shadow_research_only",
                "direction_score_shadow": value,
                "direction_state": "watch",
            }

        monkeypatch.setattr(
            ranking_module,
            "calculate_industry_three_layer_shadow",
            synthetic_shadow,
        )
        changed_shadow = generate_sector_ranking(sectors, [], top_n=3)

        formal_fields = ("sector_id", "score", "current_rank", "rank_tied")
        assert [
            tuple(row[field] for field in formal_fields)
            for row in changed_shadow.data["industry_top"]
        ] == [
            tuple(row[field] for field in formal_fields)
            for row in baseline.data["industry_top"]
        ]

    def test_relative_strength_uses_the_full_history_reference_universe(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="候选行业", price_change_pct=1.0),
        ]
        history_data = {
            "候选行业": {"recent_returns": [0.5] * 20},
            "参照行业A": {"recent_returns": [0.1] * 20},
            "参照行业B": {"recent_returns": [-0.2] * 20},
        }

        output = generate_sector_ranking(
            sectors,
            [],
            top_n=10,
            industry_history=history_data,
        )

        row = output.data["industry_top"][0]
        assert row["score_breakdown"]["trend_strength"] > 20.0

    def test_relative_strength_does_not_compare_misaligned_date_windows(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="完整日期", price_change_pct=1.0),
            self._create_sector(sector_id="BK0002", name="缺口日期", price_change_pct=1.0),
        ]
        aligned_dates = [f"2026-01-{day:02d}" for day in range(2, 22)]
        gap_dates = ["2026-01-01", *aligned_dates[1:]]
        history_data = {
            "完整日期": {
                "recent_returns": [0.5] * 20,
                "recent_dates": aligned_dates,
            },
            "缺口日期": {
                "recent_returns": [-0.5] * 20,
                "recent_dates": gap_dates,
            },
        }

        output = generate_sector_ranking(
            sectors,
            [],
            top_n=10,
            industry_history=history_data,
        )

        for row in output.data["industry_top"]:
            percentiles = row["score_breakdown"]["trend_relative_strength_percentiles"]
            assert 20 not in percentiles
            assert percentiles[5] in {0.0, 1.0}
            assert percentiles[10] in {0.0, 1.0}

    def test_relative_strength_signature_includes_the_first_return_anchor(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="正常锚点"),
            self._create_sector(sector_id="BK0002", name="跨期锚点"),
        ]
        end_dates = [f"2026-01-{day:02d}" for day in range(2, 22)]
        normal_periods = [
            [f"2026-01-{day - 1:02d}", f"2026-01-{day:02d}"]
            for day in range(2, 22)
        ]
        cross_periods = [["2025-12-31", "2026-01-02"], *normal_periods[1:]]
        history_data = {
            "正常锚点": {
                "recent_returns": [0.5] * 20,
                "recent_dates": end_dates,
                "recent_periods": normal_periods,
            },
            "跨期锚点": {
                "recent_returns": [-0.5] * 20,
                "recent_dates": end_dates,
                "recent_periods": cross_periods,
            },
        }

        output = generate_sector_ranking(
            sectors,
            [],
            top_n=10,
            industry_history=history_data,
        )

        for row in output.data["industry_top"]:
            assert 20 not in row["score_breakdown"]["trend_relative_strength_percentiles"]

        assert output.data["industry_trend_history"]["effective_20d_count"] == 0

    def test_rank_momentum_history_preserves_missing_endpoint_slots(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
        ]
        periods = [
            [f"2026-01-{day - 1:02d}", f"2026-01-{day:02d}"]
            for day in range(2, 22)
        ]
        mismatched = [list(period) for period in periods]
        mismatched[17] = ["2025-12-01", periods[17][1]]
        features = ranking_module._build_industry_trend_features(
            sectors,
            {
                "Industry A": {
                    "recent_returns": [0.5] * 20,
                    "recent_periods": periods,
                },
                "Industry B": {
                    "recent_returns": [0.4] * 20,
                    "recent_periods": mismatched,
                },
            },
        )

        for item in features.values():
            slots = item["daily_rank_percentile_slots"]
            assert len(slots) == 10
            assert any(value is None for value in slots[-5:])

    def test_untrusted_direct_history_fails_closed_without_dropping_industries(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
        ]
        output = generate_sector_ranking(
            sectors,
            [],
            top_n=2,
            industry_history={
                "Industry A": {"recent_returns": [1e10] * 20},
                "Industry B": {"recent_returns": [0.2] * 20},
            },
        )

        assert output.status.value == "ok"
        assert len(output.data["industry_top"]) == 2
        row = next(row for row in output.data["industry_top"] if row["name"] == "Industry A")
        assert row["score_breakdown"]["trend_history_status"] == "insufficient_history"
        assert row["score_breakdown"]["three_layer_shadow"][
            "direction_state"
        ] == "unavailable"

    def test_malformed_period_axis_does_not_abort_formal_ranking(self):
        sectors = [
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
        ]
        output = generate_sector_ranking(
            sectors,
            [],
            top_n=2,
            industry_history={
                "Industry A": {
                    "recent_returns": [0.2] * 20,
                    "recent_periods": [["bad"]] * 20,
                },
                "Industry B": {"recent_returns": [0.1] * 20},
            },
        )

        assert output.status.value == "ok"
        assert len(output.data["industry_top"]) == 2
        row = next(row for row in output.data["industry_top"] if row["name"] == "Industry A")
        assert row["score_breakdown"]["trend_history_status"] == "insufficient_history"

    @pytest.mark.parametrize(
        "bad_history",
        [
            {"recent_returns": None, "recent_dates": None, "recent_periods": None},
            {
                "recent_returns": [0.2] * 20,
                "recent_dates": ["not-a-date"] * 20,
            },
            {
                "recent_returns": [0.2] * 20,
                "recent_dates": [f"2026-01-{day:02d}" for day in range(2, 22)],
                "recent_periods": [
                    ["2025-12-01", f"2026-01-{day:02d}"]
                    for day in range(2, 22)
                ],
            },
        ],
    )
    def test_invalid_history_axes_fail_closed_per_industry(
        self, bad_history
    ):
        sectors = [
            self._create_sector(sector_id="BK0001", name="Industry A"),
            self._create_sector(sector_id="BK0002", name="Industry B"),
        ]
        output = generate_sector_ranking(
            sectors,
            [],
            top_n=2,
            industry_history={
                "Industry A": bad_history,
                "Industry B": {"recent_returns": [0.1] * 20},
            },
        )

        assert output.status.value == "ok"
        assert len(output.data["industry_top"]) == 2
        row = next(row for row in output.data["industry_top"] if row["name"] == "Industry A")
        assert row["score_breakdown"]["trend_history_status"] == "insufficient_history"

    def test_ranking_top_n_limit(self):
        """测试 Top N 限制"""
        sectors = [
            self._create_sector(sector_id=f"BK{i}", name=f"板块{i}")
            for i in range(20)
        ]

        output = generate_sector_ranking(sectors, [], top_n=5)

        assert len(output.data["industry_top"]) == 5

    def test_focus_level_assignment(self):
        """测试关注等级分配"""
        # 高分板块
        high_sector = self._create_sector(
            sector_id="BK0428",
            name="半导体",
            price_change_pct=5.0,
            turnover=20_000_000_000,
            main_net_inflow=3_000_000_000,
            data_quality_score=90.0,
        )

        # 低分板块
        low_sector = self._create_sector(
            sector_id="BK0476",
            name="光伏",
            price_change_pct=-3.0,
            turnover=2_000_000_000,
            main_net_inflow=-500_000_000,
            data_quality_score=50.0,
        )

        output = generate_sector_ranking([high_sector, low_sector], [], top_n=10)

        industry_top = output.data["industry_top"]
        # 高分板块应该有更高的关注等级
        high_score_item = next(s for s in industry_top if s["name"] == "半导体")
        low_score_item = next(s for s in industry_top if s["name"] == "光伏")

        # 高分板块的 score 应该更高
        assert high_score_item["score"] > low_score_item["score"]

    def test_risk_flags_in_output(self):
        """测试风险标志在输出中"""
        sector = self._create_sector(
            sector_id="BK0428",
            name="半导体",
            price_change_pct=18.0,  # 过热
            turnover=25_000_000_000,
        )

        output = generate_sector_ranking([sector], [], top_n=10)

        industry_top = output.data["industry_top"]
        assert len(industry_top) == 1
        # 应该有过热风险标志
        assert "overheat" in industry_top[0]["risk_flags"]

    def test_ranking_preserves_market_activity_for_downstream_scores(self):
        sector = self._create_sector(
            turnover=12_345_000_000,
            main_net_inflow=678_000_000,
        )

        output = generate_sector_ranking([sector], [], top_n=10)
        row = output.data["industry_top"][0]

        assert row["turnover"] == 12_345_000_000
        assert row["main_net_inflow"] == 678_000_000

    def test_equal_scores_have_stable_order_and_explicit_tie_rank(self):
        sectors = [
            self._create_sector(sector_id="BK0003", name="板块C"),
            self._create_sector(sector_id="BK0001", name="板块A"),
            self._create_sector(sector_id="BK0002", name="板块B"),
        ]

        output = generate_sector_ranking(sectors, [], top_n=2)
        rows = output.data["industry_top"]

        assert [row["sector_id"] for row in rows] == ["BK0001", "BK0002"]
        assert [row["current_rank"] for row in rows] == [1, 1]
        assert all(row["rank_tied"] is True for row in rows)
        assert all(row["rank_tie_count"] == 3 for row in rows)
