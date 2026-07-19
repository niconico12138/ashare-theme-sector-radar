import copy

import pytest

from theme_sector_radar.scoring.stock_sector_linkage import (
    build_constituent_linkage_input_contract,
    calculate_stock_sector_linkage_v2_shadow,
    legacy_linkage_policy_contract,
    effective_legacy_linkage_policy_contract,
    relative_strength_score_from_returns,
    returns_by_date_from_bars,
    select_direction_linkage_v2_shadow_stocks,
)


def _returns(multiplier: float = 1.0) -> dict[str, float]:
    return {
        f"2026-06-{day:02d}": multiplier * ((day % 5) - 2) / 10.0
        for day in range(1, 21)
    }


def test_legacy_policy_is_versioned_and_hash_bound():
    policy = legacy_linkage_policy_contract()

    assert policy["status"] == "frozen_baseline"
    assert policy["minimum_relevance"] == 0.60
    assert policy["formula"] == {
        "constituent_weight": 0.20,
        "same_day_sector_rank": 0.40,
        "fund_flow_alignment": 0.40,
    }
    assert len(policy["policy_sha256"]) == 64
    assert policy["policy_sha256"] == (
        "216615494e369c7350da37debe4b5d8a06cf96d6bd6f6ae5319267498c6e62e7"
    )


def test_effective_legacy_policy_binds_runtime_overrides():
    effective = effective_legacy_linkage_policy_contract(
        trend_top_n=3,
        burst_top_n=7,
        minimum_relevance=0.55,
    )

    assert effective["trend_sector_top_n"] == 3
    assert effective["burst_sector_top_n"] == 7
    assert effective["minimum_relevance"] == 0.55
    assert effective["matches_frozen_baseline"] is False
    assert effective["policy_sha256"] != legacy_linkage_policy_contract()[
        "policy_sha256"
    ]


def test_linkage_v2_uses_aligned_comovement_and_all_available_components():
    result = calculate_stock_sector_linkage_v2_shadow(
        stock_returns=_returns(),
        sector_returns=_returns(),
        relative_strength_score=0.8,
        constituent_weight_score=0.6,
        fund_flow_alignment_score=0.7,
        data_quality_score=0.9,
    )

    assert result["status"] == "ok"
    assert result["aligned_return_days"] == 20
    assert result["components"]["return_comovement_20d"]["score"] == pytest.approx(1.0)
    assert result["available_weight"] == pytest.approx(1.0)
    assert 0.0 <= result["score"] <= 1.0


def test_missing_factors_are_not_given_neutral_or_high_scores():
    result = calculate_stock_sector_linkage_v2_shadow(
        relative_strength_score=0.8,
        data_quality_score=0.9,
    )

    assert result["status"] == "unavailable"
    assert result["score"] is None
    assert result["available_weight"] == pytest.approx(0.3)
    assert result["components"]["fund_flow_alignment"]["score"] is None
    assert result["components"]["constituent_weight"]["effective_weight"] == 0.0


def test_partial_evidence_reweights_only_available_components():
    result = calculate_stock_sector_linkage_v2_shadow(
        stock_returns=_returns(),
        sector_returns=_returns(-1.0),
        relative_strength_score=1.0,
        data_quality_score=0.5,
    )

    assert result["status"] == "partial"
    assert result["available_weight"] == pytest.approx(0.7)
    assert result["components"]["return_comovement_20d"]["score"] == pytest.approx(0.0)
    assert sum(
        component["effective_weight"]
        for component in result["components"].values()
    ) == pytest.approx(1.0)


def test_short_or_constant_history_cannot_fabricate_comovement():
    short = {f"2026-06-{day:02d}": 0.1 for day in range(1, 11)}
    result = calculate_stock_sector_linkage_v2_shadow(
        stock_returns=short,
        sector_returns=short,
        relative_strength_score=0.8,
        constituent_weight_score=0.7,
    )

    assert result["components"]["return_comovement_20d"]["status"] == "unavailable"
    assert result["status"] == "unavailable"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.01, 1.01])
def test_invalid_component_values_fail_closed(value):
    with pytest.raises(ValueError):
        calculate_stock_sector_linkage_v2_shadow(relative_strength_score=value)


def test_inputs_are_not_mutated():
    stock = _returns()
    sector = _returns()
    original = (copy.deepcopy(stock), copy.deepcopy(sector))

    calculate_stock_sector_linkage_v2_shadow(
        stock_returns=stock,
        sector_returns=sector,
        relative_strength_score=0.8,
        data_quality_score=0.9,
    )

    assert (stock, sector) == original


def test_constituent_contract_preserves_prefilter_rows_and_marks_constant_weight():
    stocks = [
        {
            "code": "600001",
            "name": "A",
            "weight": 1.0,
            "weight_normalized": 1.0,
            "quote_available": True,
            "change_pct": 1.0,
            "individual_flow_available": False,
            "individual_flow_direction": "neutral",
            "relevance_score": 0.8,
            "relevance_breakdown": {"rank_score": 0.7},
        },
        {
            "code": "600002",
            "name": "B",
            "weight": 1.0,
            "weight_normalized": 1.0,
            "quote_available": False,
            "change_pct": 0.0,
            "individual_flow_available": True,
            "individual_flow_direction": "inflow",
            "relevance_score": 0.5,
            "relevance_breakdown": {"rank_score": 0.2},
        },
    ]
    original = copy.deepcopy(stocks)

    contract = build_constituent_linkage_input_contract(
        stocks,
        as_of_date="2026-07-17",
        sector_name="Test",
        sector_type="industry",
        constituent_source="http_em",
        sector_flow_status="ok",
    )

    assert stocks == original
    assert contract["raw_constituent_count"] == 2
    assert contract["quote_available_count"] == 1
    assert contract["individual_flow_available_count"] == 1
    assert contract["weight_signal_status"] == "constant_uninformative"
    assert contract["rows"][1]["legacy_relevance_score"] == 0.5


def test_bars_returns_and_relative_strength_are_as_of_bounded():
    bars = [
        {"date": f"2026-07-{day:02d}", "close": 10.0 + day}
        for day in range(1, 13)
    ]
    stock_returns = returns_by_date_from_bars(
        bars, as_of_date="2026-07-11"
    )
    sector_returns = {day: value / 2.0 for day, value in stock_returns.items()}

    assert "2026-07-12" not in stock_returns
    score = relative_strength_score_from_returns(stock_returns, sector_returns)
    assert score is not None
    assert 0.5 < score <= 1.0


def test_duplicate_bar_date_fails_closed():
    with pytest.raises(ValueError, match="unique"):
        returns_by_date_from_bars(
            [
                {"date": "2026-07-01", "close": 10.0},
                {"date": "2026-07-01", "close": 11.0},
            ],
            as_of_date="2026-07-01",
        )


def test_stale_stock_bar_history_fails_closed_for_linkage_returns():
    with pytest.raises(ValueError, match="latest stock bar must equal as_of_date"):
        returns_by_date_from_bars(
            [
                {"date": "2026-07-15", "close": 10.0},
                {"date": "2026-07-16", "close": 11.0},
            ],
            as_of_date="2026-07-17",
        )


def test_quant_pipeline_attaches_linkage_v2_without_formal_score_changes(monkeypatch):
    import unified_pipeline as pipeline

    bars = [
        {
            "date": f"2026-07-{day:02d}",
            "open": 10.0 + day,
            "high": 11.0 + day,
            "low": 9.0 + day,
            "close": 10.0 + day,
            "volume": 1_000_000,
            "amount": 100_000_000,
        }
        for day in range(1, 22)
    ]

    class Client:
        def get_stock_bars(self, *_args, **_kwargs):
            return bars

        def get_stock_fund_flow_batch(self, *_args, **_kwargs):
            return None

        def get_stock_fund_flow(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(pipeline, "_get_http_client", lambda: Client())
    stocks = [
        {
            "code": "600001",
            "sector_name": "Test",
            "change_pct": 1.0,
            "weight_normalized": 0.8,
            "weight_signal_available": True,
            "quote_available": True,
            "constituent_source": "http_em",
            "linkage_flow_alignment_score": None,
            "final_score": 77.7,
        }
    ]
    stock_returns = returns_by_date_from_bars(
        bars, as_of_date="2026-07-21"
    )
    sector_returns = {
        day: value * 0.8 for day, value in stock_returns.items()
    }

    result = pipeline.compute_quant_scores(
        stocks,
        as_of_date="2026-07-21",
        http_enabled=True,
        sector_returns_by_name={"Test": sector_returns},
    )

    linkage = result[0]["linkage_v2_shadow"]
    assert linkage["status"] == "partial"
    assert linkage["components"]["return_comovement_20d"]["status"] == "ok"
    assert linkage["components"]["relative_strength_5d_10d"]["status"] == "ok"
    assert result[0]["final_score"] == 77.7


def test_quant_pipeline_uses_override_only_for_bars_and_http_only_for_fund_flow(
    monkeypatch,
):
    import unified_pipeline as pipeline

    bars = [
        {
            "date": f"2026-07-{day:02d}",
            "open": 10.0 + day,
            "high": 11.0 + day,
            "low": 9.0 + day,
            "close": 10.0 + day,
            "volume": 1_000_000,
            "amount": 100_000_000,
        }
        for day in range(1, 22)
    ]

    class BarsClient:
        selection = {
            "source": "stockdb-sdk",
            "reason": "http_unavailable",
            "sdk_latest_daily_date": "20260721",
        }

        def __init__(self):
            self.calls = 0

        def get_stock_bars(self, *_args, **_kwargs):
            self.calls += 1
            return bars

        def get_stock_fund_flow_batch(self, *_args, **_kwargs):
            raise AssertionError("bars override must not receive fund-flow calls")

    class FlowClient:
        def __init__(self):
            self.batch_calls = 0

        def get_stock_bars(self, *_args, **_kwargs):
            raise AssertionError("HTTP client must not receive bar calls when overridden")

        def get_stock_fund_flow_batch(self, *_args, **_kwargs):
            self.batch_calls += 1
            return {"items": {}}

    bars_client = BarsClient()
    flow_client = FlowClient()
    monkeypatch.setattr(pipeline, "_get_http_client", lambda: flow_client)
    stocks = [
        {
            "code": "600001",
            "sector_name": "Test",
            "change_pct": 1.0,
            "quote_available": True,
            "constituent_source": "http_em",
        }
    ]
    stock_returns = returns_by_date_from_bars(bars, as_of_date="2026-07-21")

    result = pipeline.compute_quant_scores(
        stocks,
        as_of_date="2026-07-21",
        http_enabled=True,
        sector_returns_by_name={
            "Test": {day: value * 0.8 for day, value in stock_returns.items()}
        },
        bars_client_override=bars_client,
    )

    assert bars_client.calls == 1
    assert flow_client.batch_calls == 1
    assert result[0]["linkage_v2_shadow"]["status"] == "partial"
    assert pipeline.compute_quant_scores._last_bars_audit == {
        "source": "stockdb-sdk",
        "reason": "http_unavailable",
        "latest_daily_date": "20260721",
        "requested_stock_count": 1,
        "usable_stock_count": 1,
        "requested_relation_count": 1,
        "usable_relation_count": 1,
        "coverage_ratio": 1.0,
        "minimum_bars": 5,
    }


def test_quant_pipeline_reports_unique_stock_and_relation_bar_coverage():
    import unified_pipeline as pipeline

    bars = [
        {
            "date": f"2026-07-{day:02d}",
            "open": 10.0 + day,
            "high": 11.0 + day,
            "low": 9.0 + day,
            "close": 10.0 + day,
            "volume": 1_000_000,
            "amount": 100_000_000,
        }
        for day in range(1, 8)
    ]

    class BarsClient:
        selection = {
            "source": "stockdb-sdk",
            "reason": "http_unavailable",
            "sdk_latest_daily_date": "20260707",
        }

        def __init__(self):
            self.calls = 0

        def get_stock_bars(self, *_args, **_kwargs):
            self.calls += 1
            return bars

    bars_client = BarsClient()
    stocks = [
        {
            "code": "600001",
            "sector_name": sector,
            "change_pct": 1.0,
            "quote_available": True,
            "constituent_source": "http_em",
        }
        for sector in ("A", "B")
    ]

    pipeline.compute_quant_scores(
        stocks,
        as_of_date="2026-07-07",
        http_enabled=False,
        bars_client_override=bars_client,
    )

    assert bars_client.calls == 1
    assert pipeline.compute_quant_scores._last_bars_audit == {
        "source": "stockdb-sdk",
        "reason": "http_unavailable",
        "latest_daily_date": "20260707",
        "requested_stock_count": 1,
        "usable_stock_count": 1,
        "requested_relation_count": 2,
        "usable_relation_count": 2,
        "coverage_ratio": 1.0,
        "minimum_bars": 5,
    }


def test_direction_linkage_selection_applies_sector_and_cluster_quotas():
    stocks = []
    for sector, tier, count in (("A1", "core", 12), ("A2", "core", 12), ("B", "supplemental", 8)):
        for index in range(count):
            stocks.append(
                {
                    "code": f"{len(stocks) + 1:06d}",
                    "sector_name": sector,
                    "candidate_tier": tier,
                    "quant_score": 80.0 - index,
                    "linkage_v2_shadow": {
                        "status": "partial",
                        "score": 0.9 - index / 100.0,
                    },
                }
            )

    result = select_direction_linkage_v2_shadow_stocks(
        stocks,
        stock_limit=20,
        sector_cluster_map={"A1": "A", "A2": "A", "B": "B"},
    )

    assert result["selected_count"] == 0
    assert result["policy"]["cluster_cap"] == 0
    assert result["cluster_counts"] == {}
    assert result["rejected_counts"]["sector_quota"] == 7
    assert [row["linkage_selection_rank"] for row in result["selected"]] == list(
        range(1, result["selected_count"] + 1)
    )


def test_direction_linkage_selection_caps_actual_final_cluster_ratio():
    stocks = []
    for cluster in ("A", "B", "C"):
        for index in range(10):
            stocks.append(
                {
                    "code": f"{len(stocks) + 1:06d}",
                    "sector_name": cluster,
                    "candidate_tier": "core",
                    "quant_score": 90.0 - index,
                    "linkage_v2_shadow": {"status": "ok", "score": 0.9},
                }
            )

    result = select_direction_linkage_v2_shadow_stocks(
        stocks,
        stock_limit=20,
        sector_cluster_map={"A": "A", "B": "B", "C": "C"},
    )

    assert result["selected_count"] == 20
    assert result["policy"]["cluster_cap"] == 8
    assert result["policy"]["cluster_basis"] == "explicit_map"
    assert result["actual_max_cluster_ratio"] <= 0.40


def test_direction_linkage_selection_fails_closed_without_cluster_map():
    result = select_direction_linkage_v2_shadow_stocks(
        [
            {
                "code": "600001",
                "sector_name": "Unmapped A",
                "candidate_tier": "core",
                "quant_score": 80.0,
                "linkage_v2_shadow": {"status": "ok", "score": 0.8},
            }
        ]
    )

    assert result["selected_count"] == 0
    assert result["policy"]["cluster_basis"] == "unmapped_fail_closed"
    assert result["unmapped_sectors"] == ["Unmapped A"]


def test_direction_linkage_selection_rejects_unavailable_linkage():
    result = select_direction_linkage_v2_shadow_stocks(
        [
            {
                "code": "600001",
                "sector_name": "A",
                "candidate_tier": "core",
                "quant_score": 80.0,
                "linkage_v2_shadow": {"status": "unavailable", "score": None},
            }
        ]
    )

    assert result["selected"] == []
    assert result["rejected_counts"]["linkage_unavailable"] == 1


def test_direction_linkage_selection_rejection_funnel_closes_with_duplicates_and_limit():
    stocks = []
    for sector in ("A", "B"):
        for code, score in (("600001", 0.90), (f"{len(stocks) + 2:06d}", 0.80), (f"{len(stocks) + 3:06d}", 0.70)):
            stocks.append(
                {
                    "code": code,
                    "sector_name": sector,
                    "candidate_tier": "core",
                    "quant_score": 80.0,
                    "linkage_v2_shadow": {"status": "partial", "score": score},
                }
            )

    result = select_direction_linkage_v2_shadow_stocks(
        stocks,
        stock_limit=3,
        maximum_cluster_ratio=1.0,
        sector_cluster_map={"A": "all", "B": "all"},
    )

    assert result["selected_count"] == 3
    assert result["rejected_counts"]["duplicate_stock_relation"] == 1
    assert result["rejected_counts"]["stock_limit"] == 2
    assert sum(result["rejected_counts"].values()) + result["selected_count"] == len(stocks)
