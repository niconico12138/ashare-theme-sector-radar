from datetime import date, timedelta

import pytest

from scripts.evaluate_stock_sector_linkage_shadow import (
    _canonical_sha256,
    _pit_source_manifest_sha256,
    evaluate_linkage_paths,
    render_markdown_report,
)
from theme_sector_radar.reporting.strict_json import write_strict_json_atomic


def _stock(code, sector="A"):
    return {"code": code, "sector_name": sector}


def _report(day_index):
    legacy = [_stock("600001", "A"), _stock("600002", "A")]
    membership = legacy + [_stock("600003", "B")]
    selected = [_stock("600002", "A"), _stock("600003", "B")]
    return {
        "as_of_date": f"2026-01-{day_index:02d}",
        "trend_candidates_all": legacy,
        "burst_candidates_all": legacy,
        "direction_shadow_candidates_all": membership,
        "direction_linkage_v2_selection_shadow": {"selected": selected},
    }


def _forward(day_index, report=None):
    signal = date(2026, 1, 1) + timedelta(days=day_index - 1)
    signal_text = signal.isoformat()
    rows = [
        {"code": "600001", "1d": -1.0, "3d": -1.0, "5d": -1.0},
        {"code": "600002", "1d": 1.0, "3d": 1.0, "5d": 1.0},
        {"code": "600003", "1d": 2.0, "3d": 2.0, "5d": 2.0},
    ]
    label_metadata = {}
    for row in rows:
        signal_close = 100.0
        label_metadata[row["code"]] = {
            "signal_date": signal_text,
            "frequency": "1d",
            "adjustment": "qfq",
            "signal_close": signal_close,
            "source_latest_bar_date": (signal + timedelta(days=5)).isoformat(),
            "bar_snapshot_sha256": row["code"][-1] * 64,
            "horizons": {
                f"{horizon}d": {
                    "horizon_trading_days": horizon,
                    "target_trading_date": (signal + timedelta(days=horizon)).isoformat(),
                    "target_close": signal_close * (1.0 + row[f"{horizon}d"] / 100.0),
                    "mature": True,
                    "return_available": True,
                }
                for horizon in (1, 3, 5)
            },
        }
    report = report or _report(day_index)
    return {
        "as_of": signal_text,
        "items": [
            *rows,
        ],
        "label_contract": {
            "schema_version": "forward-return-label-contract-v2",
            "frequency": "1d",
            "adjustment": "qfq",
            "target_date_basis": "versioned_exchange_calendar",
        },
        "trading_calendar": {
            "dates": [
                (signal + timedelta(days=offset)).isoformat()
                for offset in range(6)
            ],
            "source": "unit_test_calendar",
            "path": "unit_test_calendar.json",
            "sha256": "c" * 64,
            "requested_start": signal_text,
            "requested_end": (signal + timedelta(days=5)).isoformat(),
        },
        "label_metadata": label_metadata,
        "source_bar_manifest": {
            row["code"]: {
                "bar_snapshot_sha256": row["code"][-1] * 64,
                "bar_count": 6,
                "query": {
                    "start": signal_text,
                    "end": (signal + timedelta(days=5)).isoformat(),
                    "frequency": "1d",
                    "adjustment": "qfq",
                },
            }
            for row in rows
        },
        "candidate_input": {
            "sha256": _canonical_sha256(report),
            "sha256_basis": "canonical_json_payload_v1",
        },
    }


def _bind_forward(report, forward):
    day = report["as_of_date"]
    forward["as_of"] = day
    forward["candidate_input"] = {
        "sha256": _canonical_sha256(report),
        "sha256_basis": "canonical_json_payload_v1",
    }
    forward["trading_calendar"]["dates"] = [
        (date.fromisoformat(day) + timedelta(days=offset)).isoformat()
        for offset in range(6)
    ]
    for metadata in forward["label_metadata"].values():
        metadata["signal_date"] = day
        metadata["source_latest_bar_date"] = (
            date.fromisoformat(day) + timedelta(days=5)
        ).isoformat()
        for horizon in (1, 3, 5):
            metadata["horizons"][f"{horizon}d"]["target_trading_date"] = (
                date.fromisoformat(day) + timedelta(days=horizon)
            ).isoformat()
    return forward


def _set_forward_returns(forward, code, values):
    row = next(item for item in forward["items"] if item["code"] == code)
    metadata = forward["label_metadata"][code]
    signal_close = metadata["signal_close"]
    for horizon, value in values.items():
        row[horizon] = value
        metadata["horizons"][horizon]["target_close"] = signal_close * (
            1.0 + value / 100.0
        )


def _with_cluster_contract(report, mapping, source_sha="a" * 64):
    report["linkage_research"] = {
        "sector_cluster_map": {
            "status": "ok",
            "sha256": source_sha,
            "mapping_sha256": _canonical_sha256(mapping),
            "mapping": mapping,
        }
    }
    return report


def test_evaluation_compares_three_paths_and_blocks_short_non_pit_sample():
    reports = {f"2026-01-{day:02d}": _report(day) for day in range(1, 6)}
    forwards = {f"2026-01-{day:02d}": _forward(day) for day in range(1, 6)}

    result = evaluate_linkage_paths(reports, forwards)

    assert result["date_count"] == 5
    assert result["groups"]["A_legacy"]["horizons"]["3d"]["mean_return_pct"] == 0.0
    assert result["groups"]["C_linkage_v2"]["horizons"]["3d"]["mean_return_pct"] == 1.5
    assert result["groups"]["A_legacy"]["horizons"]["3d"][
        "positive_label_ratio"
    ] == 0.5
    assert result["groups"]["C_linkage_v2"]["horizons"]["3d"][
        "positive_label_ratio"
    ] == 1.0
    assert result["groups"]["A_legacy"]["horizons"]["3d"][
        "mean_excess_return_pct"
    ] == pytest.approx(-2 / 3)
    assert result["groups"]["C_linkage_v2"]["horizons"]["3d"][
        "mean_excess_return_pct"
    ] == pytest.approx(5 / 6)
    paired = result["paired_daily_differences"]["C_minus_A"]["3d"]
    assert paired["observation_count"] == 5
    assert paired["mean_difference_pct"] == 1.5
    assert paired["positive_difference_ratio"] == 1.0
    assert result["promotion_gates"]["minimum_60_dates"] is False
    assert result["promotion_gates"]["strict_pit_eligible"] is False
    assert result["promotion_status"] == "insufficient_evidence"


def test_missing_direction_forward_returns_reduce_coverage_instead_of_disappearing():
    report = _report(1)
    forward = _forward(1)
    forward["items"] = forward["items"][:2]

    result = evaluate_linkage_paths(
        {"2026-01-01": report}, {"2026-01-01": forward}
    )

    coverage = result["groups"]["C_linkage_v2"]["horizons"]["1d"]["coverage_ratio"]
    assert coverage == 0.5
    assert result["promotion_gates"]["coverage_90pct"] is False


def test_promotion_coverage_requires_both_legacy_and_linkage_labels():
    report = _report(1)
    forward = _forward(1)
    forward["items"] = [forward["items"][1], forward["items"][2]]

    result = evaluate_linkage_paths(
        {"2026-01-01": report}, {"2026-01-01": forward}
    )

    assert result["groups"]["A_legacy"]["horizons"]["1d"]["coverage_ratio"] == 0.5
    assert result["groups"]["C_linkage_v2"]["horizons"]["1d"]["coverage_ratio"] == 1.0
    assert result["promotion_gates"]["coverage_90pct"] is False


def test_strict_pit_gate_requires_verified_evidence_contract():
    reports = {"2026-01-01": _report(1)}
    forwards = {"2026-01-01": _forward(1)}

    result = evaluate_linkage_paths(
        reports,
        forwards,
        strict_pit_evidence=True,
    )

    assert result["promotion_gates"]["strict_pit_eligible"] is False
    assert result["pit_evidence_status"] == "unverified_no_trusted_verifier"


def test_strict_pit_gate_rejects_self_attested_verified_evidence():
    reports = {"2026-01-01": _report(1)}
    forwards = {"2026-01-01": _forward(1)}
    evidence = {
        "schema_version": "stock_sector_linkage_pit_evidence.v1",
        "status": "verified",
        "document_dates": ["2026-01-01"],
        "source_manifest_sha256": _pit_source_manifest_sha256(
            ["2026-01-01"], reports, forwards
        ),
    }

    result = evaluate_linkage_paths(
        reports,
        forwards,
        strict_pit_evidence=evidence,
    )

    assert result["promotion_gates"]["strict_pit_eligible"] is False
    assert result["pit_evidence_status"] == "unverified_no_trusted_verifier"


def test_unverified_label_metadata_is_excluded_and_blocks_promotion():
    forward = _forward(1)
    del forward["label_metadata"]

    result = evaluate_linkage_paths(
        {"2026-01-01": _report(1)}, {"2026-01-01": forward}
    )

    assert result["groups"]["C_linkage_v2"]["horizons"]["1d"][
        "coverage_ratio"
    ] == 0.0
    assert result["promotion_gates"]["forward_label_maturity_verified"] is False


def test_evaluator_rejects_cross_date_and_candidate_identity_mismatch():
    report = _report(1)
    forward = _forward(1)
    forward["as_of"] = "2026-01-02"

    with pytest.raises(ValueError, match="forward as_of date mismatch"):
        evaluate_linkage_paths({"2026-01-01": report}, {"2026-01-01": forward})

    forward = _forward(1)
    forward["candidate_input"] = {
        "sha256": "f" * 64,
        "sha256_basis": "canonical_json_payload_v1",
    }
    with pytest.raises(ValueError, match="candidate input SHA mismatch"):
        evaluate_linkage_paths({"2026-01-01": report}, {"2026-01-01": forward})


def test_evaluator_recomputes_forward_return_from_bound_source_closes():
    report = _report(1)
    forward = _forward(1)
    forward["candidate_input"] = {
        "sha256": _canonical_sha256(report),
        "sha256_basis": "canonical_json_payload_v1",
    }
    metadata = forward["label_metadata"]["600001"]
    metadata["signal_close"] = 100.0
    metadata["bar_snapshot_sha256"] = "a" * 64
    forward["source_bar_manifest"]["600001"]["bar_snapshot_sha256"] = "a" * 64
    metadata["horizons"]["1d"]["target_close"] = 101.0
    forward["items"][0]["1d"] = 50.0

    with pytest.raises(ValueError, match="does not match source closes"):
        evaluate_linkage_paths({"2026-01-01": report}, {"2026-01-01": forward})


def test_evaluator_rejects_bar_snapshot_that_does_not_match_bound_sha():
    report = _report(1)
    forward = _forward(1)
    forward["source_bar_manifest"]["600001"]["normalized_bars"] = [
        {"date": "2026-01-01", "close": 999.0}
    ]

    with pytest.raises(ValueError, match="bar snapshot SHA mismatch"):
        evaluate_linkage_paths({"2026-01-01": report}, {"2026-01-01": forward})


def test_unavailable_stability_and_ok_only_evidence_are_hard_gates():
    report = _with_cluster_contract(_report(1), {"A": "A", "B": "B"})
    for row in report["direction_linkage_v2_selection_shadow"]["selected"]:
        row["linkage_v2_shadow"] = {"status": "partial"}

    result = evaluate_linkage_paths(
        {"2026-01-01": report}, {"2026-01-01": _forward(1, report)}
    )

    assert result["promotion_gates"]["market_regime_stability_verified"] is False
    assert result["promotion_gates"]["date_and_industry_concentration_verified"] is False
    assert result["promotion_gates"]["ok_only_sensitivity_usable"] is False
    assert result["promotion_status"] == "insufficient_evidence"


def test_promotion_requires_c_observations_on_60_dates_and_90pct_of_replay():
    reports = {}
    forwards = {}
    for index in range(90):
        day_text = (date(2026, 1, 1) + timedelta(days=index)).isoformat()
        report = _with_cluster_contract(_report(1), {"A": "A", "B": "B"})
        report["as_of_date"] = day_text
        for row in report["direction_linkage_v2_selection_shadow"]["selected"]:
            row["sector_cluster"] = row["sector_name"]
        if index:
            report["direction_linkage_v2_selection_shadow"] = {"selected": []}
        forward = _bind_forward(report, _forward(1))
        reports[day_text] = report
        forwards[day_text] = forward

    result = evaluate_linkage_paths(reports, forwards)

    assert result["groups"]["C_linkage_v2"]["nonempty_candidate_dates"] == 1
    assert result["groups"]["C_linkage_v2"]["average_max_cluster_share"] == 0.5
    assert result["promotion_gates"]["minimum_c_observation_dates"] is False


def test_evaluator_uses_sector_cluster_instead_of_sector_name():
    report = _with_cluster_contract(
        _report(1), {"A": "Shared", "B": "Shared"}
    )
    selected = report["direction_linkage_v2_selection_shadow"]["selected"]
    selected[0]["sector_cluster"] = "Shared"
    selected[1]["sector_cluster"] = "Shared"

    result = evaluate_linkage_paths(
        {"2026-01-01": report}, {"2026-01-01": _forward(1, report)}
    )

    assert result["groups"]["C_linkage_v2"]["average_max_cluster_share"] == 1.0
    assert result["groups"]["C_linkage_v2"]["average_max_sector_share"] == 0.5


def test_evaluator_reports_worst_date_and_partial_linkage_sensitivity():
    report = _with_cluster_contract(_report(1), {"A": "A", "B": "B"})
    for row in report["direction_shadow_candidates_all"]:
        row["linkage_v2_shadow"] = {"status": "partial"}
    for row in report["direction_linkage_v2_selection_shadow"]["selected"]:
        row["linkage_v2_shadow"] = {"status": "partial"}

    result = evaluate_linkage_paths(
        {"2026-01-01": report}, {"2026-01-01": _forward(1, report)}
    )

    horizon = result["groups"]["C_linkage_v2"]["horizons"]["1d"]
    assert horizon["worst_date"] == "2026-01-01"
    assert horizon["worst_daily_return_pct"] == 1.5
    sensitivity = result["linkage_evidence_sensitivity"]
    assert sensitivity["all_candidate_status_counts"] == {"partial": 3}
    assert sensitivity["selected_status_counts"] == {"partial": 2}
    assert sensitivity["selected_partial_ratio"] == 1.0
    assert sensitivity["ok_only_candidate_count"] == 0
    assert sensitivity["ok_only_horizons"]["1d"]["mean_return_pct"] is None


def test_markdown_report_states_non_promotion_and_pit_limit():
    report = evaluate_linkage_paths(
        {"2026-01-01": _report(1)}, {"2026-01-01": _forward(1)}
    )

    markdown = render_markdown_report(report)

    assert "insufficient_evidence" in markdown
    assert "strict_pit_eligible=false" in markdown
    assert "No broker connection" in markdown


def test_raw_mean_gate_is_not_an_alias_for_excess_mean_gate():
    first_report = _with_cluster_contract(_report(1), {"A": "A", "B": "B"})
    second_report = _with_cluster_contract(_report(2), {"A": "A", "B": "B"})
    first_report["as_of_date"] = "2026-01-01"
    second_report["as_of_date"] = "2026-01-02"
    first_report["direction_linkage_v2_selection_shadow"] = {"selected": []}
    second_report["direction_linkage_v2_selection_shadow"] = {
        "selected": [_stock("600003", "B")]
    }
    first_forward = _forward(1, first_report)
    first_forward["items"] = first_forward["items"][:2]
    for row in first_forward["items"]:
        _set_forward_returns(
            first_forward, row["code"], {"1d": 0, "3d": 100, "5d": 100}
        )
    second_forward = _forward(2, second_report)
    for row in second_forward["items"]:
        value = -50 if row["code"] == "600003" else -90
        _set_forward_returns(
            second_forward,
            row["code"],
            {"1d": 0, "3d": value, "5d": value},
        )

    result = evaluate_linkage_paths(
        {"2026-01-01": first_report, "2026-01-02": second_report},
        {"2026-01-01": first_forward, "2026-01-02": second_forward},
    )

    assert result["promotion_gates"]["three_and_five_day_mean_excess_return_better"]
    assert not result["promotion_gates"]["three_and_five_day_mean_return_better"]
    assert not result["promotion_gates"]["historical_constituent_universe_versioned"]


def test_promotion_blocks_mixed_cluster_map_shas():
    first = _with_cluster_contract(_report(1), {"A": "One", "B": "Two"}, "a" * 64)
    second = _with_cluster_contract(_report(2), {"A": "One", "B": "Two"}, "b" * 64)
    first["as_of_date"] = "2026-01-01"
    second["as_of_date"] = "2026-01-02"
    first_forward = _forward(1, first)
    second_forward = _forward(2, second)

    result = evaluate_linkage_paths(
        {"2026-01-01": first, "2026-01-02": second},
        {"2026-01-01": first_forward, "2026-01-02": second_forward},
    )

    assert result["promotion_gates"]["cluster_map_consistent"] is False
    assert result["cluster_map_identity"] is None


def test_concentration_gate_compares_worst_date_not_daily_average():
    mapping = {
        "LA": "LA",
        "LB": "LB",
        "X": "X",
        "Y": "Y",
        "P": "P",
        "Q": "Q",
        "R": "R",
        "S": "S",
        "T": "T",
    }

    def report(day, c_sectors):
        legacy = [
            _stock(f"61{index:04d}", "LA" if index < 2 else "LB")
            for index in range(4)
        ]
        selected = [
            _stock(f"62{day}{index:03d}", sector)
            for index, sector in enumerate(c_sectors)
        ]
        return _with_cluster_contract(
            {
                "as_of_date": f"2026-01-0{day}",
                "trend_candidates_all": legacy,
                "burst_candidates_all": [],
                "direction_shadow_candidates_all": selected,
                "direction_linkage_v2_selection_shadow": {"selected": selected},
            },
            mapping,
        )

    first = report(1, ["X", "X", "X", "Y"])
    second = report(2, ["P", "Q", "R", "S", "T"])
    result = evaluate_linkage_paths(
        {"2026-01-01": first, "2026-01-02": second},
        {"2026-01-01": {**_forward(1, first), "items": []},
         "2026-01-02": {**_forward(2, second), "items": []}},
    )

    legacy = result["groups"]["A_legacy"]
    linkage = result["groups"]["C_linkage_v2"]
    assert linkage["average_max_cluster_share"] < legacy["average_max_cluster_share"]
    assert linkage["maximum_cluster_share"] > legacy["maximum_cluster_share"]
    assert result["promotion_gates"]["concentration_lower"] is False


def test_cli_loads_verified_pit_evidence(tmp_path, monkeypatch):
    import scripts.evaluate_stock_sector_linkage_shadow as evaluator
    from theme_sector_radar.data.trading_calendar import (
        build_trading_calendar_report,
        load_trading_calendar,
    )

    day = "2026-01-01"
    report = _report(1)
    calendar_path = tmp_path / "calendar.json"
    write_strict_json_atomic(
        calendar_path,
        build_trading_calendar_report(
            ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"],
            source="unit_test_calendar",
            requested_start="2026-01-01",
            requested_end="2026-01-07",
        ),
    )
    calendar = load_trading_calendar(
        calendar_path, as_of=day, include_future=True
    )
    forward = _forward(1)
    forward["trading_calendar"] = calendar
    target_dates = calendar["dates"]
    for metadata in forward["label_metadata"].values():
        for horizon in (1, 3, 5):
            target = (
                target_dates[horizon] if horizon < len(target_dates) else None
            )
            item = metadata["horizons"][f"{horizon}d"]
            item["target_trading_date"] = target
            if target is None:
                item["mature"] = False
                item["return_available"] = False
                item["target_close"] = None
    unified_root = tmp_path / "unified"
    forward_root = tmp_path / "forward"
    write_strict_json_atomic(unified_root / day / "unified_report.json", report)
    write_strict_json_atomic(forward_root / day / "forward_returns.json", forward)
    evidence = {
        "schema_version": "stock_sector_linkage_pit_evidence.v1",
        "status": "verified",
        "document_dates": [day],
        "source_manifest_sha256": _pit_source_manifest_sha256(
            [day], {day: report}, {day: forward}
        ),
    }
    evidence_path = tmp_path / "pit_evidence.json"
    output_path = tmp_path / "evaluation.json"
    write_strict_json_atomic(evidence_path, evidence)
    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluate_stock_sector_linkage_shadow.py",
            "--start", day,
            "--end", day,
            "--unified-root", str(unified_root),
            "--forward-root", str(forward_root),
            "--pit-evidence", str(evidence_path),
            "--output", str(output_path),
            "--trading-calendar-path", str(calendar_path),
            "--expected-calendar-sha256", calendar["sha256"],
        ],
    )

    assert evaluator.main() == 0
    assert evaluator.load_strict_json(output_path)["pit_evidence_status"] == (
        "unverified_no_trusted_verifier"
    )


def test_evaluator_accepts_project_forward_returns_format():
    forward = _forward(1)
    project_format = {
        "as_of": forward["as_of"],
        "forward_returns": {
            row["code"]: {key: row[key] for key in ("1d", "3d", "5d")}
            for row in forward["items"]
        },
        "label_contract": forward["label_contract"],
        "label_metadata": forward["label_metadata"],
        "trading_calendar": forward["trading_calendar"],
        "source_bar_manifest": forward["source_bar_manifest"],
        "candidate_input": forward["candidate_input"],
    }

    result = evaluate_linkage_paths(
        {"2026-01-01": _report(1)}, {"2026-01-01": project_format}
    )

    assert result["groups"]["C_linkage_v2"]["horizons"]["3d"][
        "mean_return_pct"
    ] == 1.5
