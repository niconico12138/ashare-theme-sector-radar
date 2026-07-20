import json


def _enhanced_breakdown(momentum=20.0, valuation=8.0, liquidity=15.0,
                        risk=10.0, fund_flow=0.0, sector=8.0):
    return {
        "raw_total": momentum + valuation + liquidity + risk + fund_flow + sector,
        "raw_max": 104.0,
        "1d_momentum": momentum / 4.0,
        "5d_momentum_quality": momentum / 4.0,
        "ma_alignment": momentum / 4.0,
        "continuity": momentum / 4.0,
        "pe_score": valuation / 2.0,
        "pb_score": valuation / 2.0,
        "market_cap": liquidity,
        "volume_trend": 0.0,
        "avg_amount": 0.0,
        "drawdown": risk,
        "volatility": 0.0,
        "fund_flow": fund_flow,
        "fund_flow_persistence": 0.0,
        "sector_trend": sector,
        "sector_burst": 0.0,
    }


def _stock(code, raw_total, *, fund_flow_available=False):
    available = [
        "1d_momentum", "5d_momentum_quality", "ma_alignment", "continuity",
        "pe_relative", "pb_score", "market_cap", "volume_trend",
        "avg_amount", "drawdown", "volatility", "sector_match",
    ]
    missing = [] if fund_flow_available else ["fund_flow"]
    if fund_flow_available:
        available.append("fund_flow")
    return {
        "code": code,
        "quant_score": 50.0,
        "quant_source": "stockdb_sdk_enhanced_v2",
        "quant_breakdown": _enhanced_breakdown(),
        "available_factors": available,
        "missing_factors": missing,
        "degraded_factors": [],
        "_shadow_raw_total": raw_total,
        "sector_trend_score": 70.0,
        "sector_burst_score": 60.0,
    }


def test_shadow_score_recalibrates_missing_fund_flow_without_touching_formal_score():
    from unified_pipeline import annotate_quant_score_shadow

    stock = _stock("600001", 61.0)
    stock["quant_breakdown"]["raw_total"] = 61.0
    stock.update({
        "final_score": 61.0,
        "v2_score": 62.0,
        "selection_score": 63.0,
        "selection_score_adjusted": 64.0,
    })
    protected = {
        key: stock[key]
        for key in (
            "quant_score", "final_score", "v2_score",
            "selection_score", "selection_score_adjusted",
        )
    }

    audit = annotate_quant_score_shadow([stock])

    assert {key: stock[key] for key in protected} == protected
    assert stock["quant_score_shadow_quality_adjusted"] == 67.78
    assert "fund_flow" in stock["quant_score_shadow_missing_factor_groups"]
    assert "fund_flow" not in stock["quant_score_shadow_available_factor_groups"]
    assert stock["quant_score_shadow_confidence"] < 100.0
    assert stock["quant_score_shadow_cross_sectional_percentile"] == 50.0
    assert stock["quant_score_shadow_cross_sectional_candidate_chain"] == "not_provided"
    assert audit["status"] == "ok"


def test_shadow_cross_sectional_percentiles_are_ranked_independently():
    from unified_pipeline import annotate_quant_score_shadow

    stocks = []
    for code, raw in (("600001", 40.0), ("600002", 60.0), ("600003", 80.0)):
        stock = _stock(code, raw)
        stock["quant_breakdown"]["raw_total"] = raw
        stock["quant_breakdown"]["market_cap"] = raw / 10.0
        stocks.append(stock)

    annotate_quant_score_shadow(stocks)

    percentiles = {s["code"]: s["quant_score_shadow_cross_sectional_percentile"]
                   for s in stocks}
    assert percentiles == {"600001": 16.67, "600002": 50.0, "600003": 83.33}


def test_shadow_keeps_persistence_and_sector_burst_availability_independent():
    from unified_pipeline import annotate_quant_score_shadow

    stock = _stock("600010", 61.0, fund_flow_available=True)
    stock["sector_burst_score"] = None
    stock["_fund_flow"] = {"available": True, "main_net_inflow": 1e8}
    stock["quant_breakdown"]["fund_flow"] = 2.0

    annotate_quant_score_shadow([stock])

    groups = stock["quant_score_shadow_factor_groups"]
    assert "fund_flow_persistence" in groups["fund_flow"]["degraded_factors"]
    assert "sector_burst" in groups["sector_fit"]["missing_factors"]
    assert "fund_flow" in stock["quant_score_shadow_degraded_factor_groups"]
    assert "sector_fit" in stock["quant_score_shadow_degraded_factor_groups"]
    assert groups["fund_flow"]["status"] == "partial"
    assert groups["sector_fit"]["status"] == "partial"


def test_shadow_redundancy_diagnosis_is_observational_and_json_safe():
    from unified_pipeline import annotate_quant_score_shadow

    stocks = []
    for index in range(1, 21):
        raw = float(index + 20)
        stock = _stock(f"60{index:04d}", raw)
        stock["quant_breakdown"]["raw_total"] = raw
        stock["quant_breakdown"]["1d_momentum"] = raw / 10.0
        stock["quant_breakdown"]["sector_trend"] = raw / 10.0
        stocks.append(stock)

    audit = annotate_quant_score_shadow(stocks)

    assert audit["redundancy_diagnostics"]["status"] == "ok"
    assert audit["redundancy_diagnostics"]["high_redundancy_pairs"]
    assert all(s["quant_score"] == 50.0 for s in stocks)
    json.dumps(audit, ensure_ascii=False, allow_nan=False)


def test_shadow_redundancy_reports_insufficient_evidence_below_pair_sample_floor():
    from unified_pipeline import annotate_quant_score_shadow

    stocks = [_stock("600001", 40.0), _stock("600002", 60.0)]

    audit = annotate_quant_score_shadow(stocks)

    diagnostics = audit["redundancy_diagnostics"]
    assert diagnostics["status"] == "insufficient_evidence"
    assert diagnostics["valid_pair_count"] == 0


def test_shadow_rejects_nonfinite_factor_from_available_score_and_stays_json_safe():
    from unified_pipeline import annotate_quant_score_shadow

    stock = _stock("600099", 60.0)
    stock["quant_breakdown"]["1d_momentum"] = float("nan")

    audit = annotate_quant_score_shadow([stock])

    assert "1d_momentum" in stock["quant_score_shadow_factor_groups"][
        "momentum_quality"
    ]["missing_factors"]
    json.dumps(audit, ensure_ascii=False, allow_nan=False)
    json.dumps(stock, ensure_ascii=False, allow_nan=False)
