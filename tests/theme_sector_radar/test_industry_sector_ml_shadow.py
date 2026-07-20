from __future__ import annotations

from datetime import date, timedelta
import copy
import json

import pytest


def _source_root(tmp_path, *, dates=40, sectors=12):
    root = tmp_path / "sector_history"
    industry = root / "industry"
    industry.mkdir(parents=True)
    start = date(2026, 1, 2)
    days = [(start + timedelta(days=i)).isoformat() for i in range(dates)]
    for sector_index in range(sectors):
        records = []
        for index, day in enumerate(days):
            close = 100.0 + sector_index + index * (0.2 + sector_index * 0.01)
            records.append(
                {
                    "date": day,
                    "close": close,
                    "volume": 1000.0 + sector_index * 10 + index,
                    "amount": 100000.0 + sector_index * 100 + index * 10,
                }
            )
        payload = {
            "sector_name": f"industry-{sector_index:02d}",
            "sector_type": "industry",
            "source": "unit_test_source",
            "fetched_at": "2026-07-20T12:00:00+08:00",
            "records": records,
        }
        (industry / f"industry_{sector_index:02d}.json").write_text(
            json.dumps(payload, sort_keys=True), encoding="utf-8"
        )
    return root


def test_industry_dataset_has_real_feature_groups_and_shadow_guards(tmp_path, monkeypatch):
    from theme_sector_radar.ml import industry_sector_shadow as shadow

    monkeypatch.setattr(shadow, "MIN_MATURE_DATES", 10)
    monkeypatch.setattr(shadow, "MIN_SECTORS", 10)
    dataset = shadow.build_industry_sector_dataset(_source_root(tmp_path))

    assert dataset["counts"]["sector_count"] == 12
    assert dataset["counts"]["mature_dates"] >= 10
    assert dataset["feature_profiles"]["all_v1"]
    assert len(dataset["feature_profiles"]["no_rule_direction_v1"]) < len(
        dataset["feature_profiles"]["all_v1"]
    )
    assert all(dataset[key] is False for key in (
        "strict_pit_eligible",
        "eligible_for_oos_claim",
        "promotion_allowed",
        "live_trading_allowed",
        "formal_predictor_compatible",
    ))
    assert dataset["agent_interface"] == {
        "enabled": False,
        "status": "reserved_not_run",
    }
    row = dataset["records"][0]
    assert {name for name in row["features"] if name.startswith("rule_")} == set(
        shadow.RULE_DIRECTION_FEATURES
    )
    assert "market_breadth_1d" in row["features"]
    assert "rank_momentum_5d" in row["features"]
    assert row["training_label_end_date"] > row["as_of_date"]


def test_industry_dataset_rejects_rehashed_row_tampering(tmp_path, monkeypatch):
    from theme_sector_radar.ml import industry_sector_shadow as shadow
    from theme_sector_radar.ml.contract import canonical_sha256

    monkeypatch.setattr(shadow, "MIN_MATURE_DATES", 10)
    monkeypatch.setattr(shadow, "MIN_SECTORS", 10)
    dataset = shadow.build_industry_sector_dataset(_source_root(tmp_path))
    forged = copy.deepcopy(dataset)
    forged["records"][0]["training_label"] = 99.0
    core = {
        key: forged.get(key)
        for key in (
            "schema_version", "mode", "status", "dataset_classification",
            "feature_names", "feature_profiles", "label_definition",
            "source_manifest", "counts", "feature_universe_records", "records",
            "strict_pit_eligible", "eligible_for_oos_claim", "promotion_allowed",
            "live_trading_allowed", "formal_predictor_compatible", "agent_interface",
        )
    }
    forged["dataset_sha256"] = canonical_sha256(core)
    with pytest.raises(ValueError, match="source manifest"):
        shadow.validate_industry_sector_dataset(forged)


def test_industry_evaluation_emits_topk_regime_metrics(tmp_path, monkeypatch):
    from theme_sector_radar.ml import industry_sector_shadow as shadow

    monkeypatch.setattr(shadow, "MIN_MATURE_DATES", 10)
    monkeypatch.setattr(shadow, "MIN_SECTORS", 10)
    dataset = shadow.build_industry_sector_dataset(_source_root(tmp_path))
    predictions = [
        {
            "as_of_date": row["as_of_date"],
            "sector_name": row["sector_name"],
            "prediction": row["rule_direction_score"],
        }
        for row in dataset["records"]
    ]
    report = shadow.evaluate_industry_sector_shadow(
        dataset,
        {"predictions": predictions},
    )

    assert report["metrics"]["rule_top3"]["date_count"] > 0
    assert report["metrics"]["ml_top5"]["rank_ic"] is not None
    assert report["metrics"]["ml_top7"]["ndcg"] is not None
    assert set(report["metrics"]["rule_gate_ml_top3"]["regime"]) == {
        "risk_on", "mixed", "risk_off"
    }
    assert all(report[key] is False for key in (
        "strict_pit_eligible",
        "eligible_for_oos_claim",
        "promotion_allowed",
        "live_trading_allowed",
        "formal_predictor_compatible",
    ))

    stressed = shadow.evaluate_industry_sector_shadow(
        dataset,
        {"predictions": predictions},
        rule_gate_threshold=70.0,
        top_k_values=(1, 3),
        evaluation_regimes=("risk_on",),
        transaction_cost_bps=25.0,
    )
    assert stressed["top_k_values"] == [1, 3]
    assert stressed["rule_gate_threshold"] == 70.0
    assert stressed["evaluation_regimes"] == ["risk_on"]
    assert "ml_top1" in stressed["metrics"]
    assert "ml_top5" not in stressed["metrics"]
    assert stressed["metrics"]["ml_top3"]["mean_net_excess_return"] <= stressed["metrics"]["ml_top3"]["mean_excess_return"]


def test_industry_source_rejects_fixture_history(tmp_path):
    root = _source_root(tmp_path)
    path = next((root / "industry").glob("*.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source"] = "synthetic_fixture"
    path.write_text(json.dumps(payload), encoding="utf-8")
    from theme_sector_radar.ml.industry_sector_shadow import build_industry_sector_dataset

    with pytest.raises(ValueError, match="fixture or synthetic"):
        build_industry_sector_dataset(root)


def test_industry_shadow_has_forty_registered_rounds_and_forbids_formal_or_order_fields():
    from theme_sector_radar.ml import industry_sector_shadow as shadow

    assert len(shadow.ROUND_SPECS) == 40
    assert len({spec["name"] for spec in shadow.ROUND_SPECS}) == 40
    round_numbers = {
        int(spec["name"].split("_", 1)[0].removeprefix("round"))
        for spec in shadow.ROUND_SPECS
    }
    assert round_numbers == set(range(1, 41))
    assert all("hypothesis" in spec for spec in shadow.ROUND_SPECS)
    assert all(
        set(shadow.feature_names_for_profile(spec["feature_profile"])).issubset(shadow.FEATURE_NAMES)
        for spec in shadow.ROUND_SPECS
    )
    with pytest.raises(ValueError, match="forbidden"):
        shadow.validate_shadow_prediction_fields({"predictions": [{"order_id": "fake"}]})
    with pytest.raises(ValueError, match="forbidden"):
        shadow.validate_shadow_prediction_fields({"quant_score": 1.0, "predictions": []})


def test_industry_feature_stress_modes_are_deterministic():
    from theme_sector_radar.ml import industry_sector_shadow as shadow

    rows = [
        {
            "as_of_date": f"2026-01-{index + 1:02d}",
            "stock_code": f"{index:06d}",
            "features": {name: 5.0 for name in shadow.FEATURE_NAMES},
        }
        for index in range(20)
    ]
    clipped = shadow.prepare_round_records(rows, shadow.FEATURE_NAMES, feature_value_mode="fixed_clip_v1")
    assert all(row["features"]["momentum_5d"] == 1.0 for row in clipped)
    first = shadow.prepare_round_records(
        rows, shadow.FEATURE_NAMES, feature_value_mode="deterministic_missing_zero_10pct_v1"
    )
    second = shadow.prepare_round_records(
        rows, shadow.FEATURE_NAMES, feature_value_mode="deterministic_missing_zero_10pct_v1"
    )
    assert first == second
    assert any(value == 0.0 for row in first for value in row["features"].values())


def test_industry_oos_readiness_contract_and_drawdown(tmp_path):
    from theme_sector_radar.ml.industry_sector_oos_readiness import (
        CANDIDATE_CONFIGS,
        STRICT_SPLIT_CONTRACT,
        build_oos_readiness_report,
        calculate_drawdown_metrics,
    )

    report = build_oos_readiness_report(
        _source_root(tmp_path),
        dataset_counts={"sector_count": 12, "date_end": "2026-07-09"},
    )
    assert report["status"] == "blocked_pending_label_maturity"
    assert report["event_enhancement_ab"]["event_source_read"] is False
    assert len(CANDIDATE_CONFIGS) == 4
    assert STRICT_SPLIT_CONTRACT["label_horizon_days"] == 5
    assert all(report["readiness"][key] is False for key in (
        "strict_pit_eligible",
        "eligible_for_oos_claim",
        "promotion_allowed",
        "live_trading_allowed",
        "formal_predictor_compatible",
    ))
    metrics = calculate_drawdown_metrics([0.10, -0.20, 0.05])
    assert metrics["observations"] == 3
    assert metrics["max_drawdown"] == pytest.approx(0.20)
    assert metrics["cumulative_return"] == pytest.approx(-0.076)
