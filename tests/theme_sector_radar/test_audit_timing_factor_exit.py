import json

import pytest

from scripts.audit_timing_factor_exit import audit_factor_exit_report


def _record(code, version, close_return, strategies, forward_return=None):
    return {
        "code": code,
        "name": f"stock-{code}",
        "timing_version_id": version,
        "forward_return_pct": forward_return,
        "path_stats": {"close_return_pct": close_return},
        "factor_exit_triggers": {
            "strategies": strategies,
            "paper_trading_only": True,
            "no_execution_signals": True,
        },
    }


def _strategy(triggered, trigger_return, close_return, trigger_type="take_profit"):
    return {
        "triggered": triggered,
        "trigger_type": trigger_type if triggered else None,
        "trigger_time": "10:00" if triggered else None,
        "trigger_return_pct": trigger_return if triggered else None,
        "trigger_factors": ["unit"] if triggered else [],
        "close_return_pct": close_return,
        "saved_vs_close_pct": round(trigger_return - close_return, 4) if triggered else None,
        "missed_upside_pct": max(0.0, round(close_return - trigger_return, 4)) if triggered else 0.0,
        "exit_research_only": True,
    }


def _strategy_with_factors(trigger_return, close_return, factors):
    row = _strategy(True, trigger_return, close_return)
    row["trigger_factors"] = factors
    return row


def test_audit_factor_exit_report_summarizes_strategies(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            {
                "records": [
                    _record(
                        "600001",
                        "v31",
                        1.0,
                        {
                            "exit_v1_fixed": _strategy(True, 5.0, 1.0),
                            "exit_v2_factor_protect": _strategy(True, 3.0, 1.0),
                        },
                        forward_return=-6.0,
                    ),
                    _record(
                        "600002",
                        "v31",
                        6.0,
                        {
                            "exit_v1_fixed": _strategy(True, 5.0, 6.0),
                            "exit_v2_factor_protect": _strategy(False, None, 6.0),
                        },
                        forward_return=8.0,
                    ),
                    _record(
                        "600003",
                        "v31",
                        -7.0,
                        {
                            "exit_v1_fixed": _strategy(False, None, -7.0),
                            "exit_v2_factor_protect": _strategy(False, None, -7.0),
                        },
                    ),
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = audit_factor_exit_report(
        records_path=records_path,
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    report = result["report"]
    assert report["paper_trading_only"] is True
    assert report["summary"]["record_count"] == 3
    assert report["summary"]["labeled_record_count"] == 2
    assert report["summary"]["unlabeled_record_count"] == 1
    assert report["strategies"]["exit_v1_fixed"]["trigger_count"] == 2
    assert report["strategies"]["exit_v1_fixed"]["trigger_labeled_count"] == 2
    assert report["strategies"]["exit_v1_fixed"]["avg_trigger_return_pct"] == 5.0
    assert report["strategies"]["exit_v1_fixed"]["avg_saved_vs_close_pct"] == 1.5
    assert report["strategies"]["exit_v1_fixed"]["avg_forward_return_pct"] == 1.0
    assert report["strategies"]["exit_v1_fixed"]["avg_saved_vs_forward_pct"] == 4.0
    assert report["strategies"]["exit_v1_fixed"]["avg_missed_vs_forward_pct"] == 1.5
    assert report["strategies"]["exit_v1_fixed"]["forward_tail_loss_count"] == 1
    assert report["strategies"]["exit_v1_fixed"]["forward_tail_avoided_count"] == 1
    assert report["strategies"]["exit_v1_fixed"]["avg_missed_upside_pct"] == 0.5
    assert report["strategies"]["exit_v2_factor_protect"]["trigger_count"] == 1
    assert report["by_trigger_factor"]["single_factors"]["exit_v1_fixed:unit"]["trigger_count"] == 2
    assert "Timing Factor Exit Audit" in result["markdown_path"].read_text(encoding="utf-8")


def test_audit_factor_exit_report_rejects_nonfinite_json(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text('{"records": [], "forged": Infinity}', encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        audit_factor_exit_report(
            records_path=records_path,
            output_dir=tmp_path / "out",
            as_of="2026-07-13",
            snapshot_label="unit",
        )


def test_audit_factor_exit_report_summarizes_trigger_factor_attribution(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            {
                "records": [
                    _record(
                        "600001",
                        "v31",
                        1.0,
                        {"exit_v2_factor_protect": _strategy_with_factors(4.0, 1.0, ["price_below_vwap"])},
                        forward_return=-7.0,
                    ),
                    _record(
                        "600002",
                        "v31",
                        8.0,
                        {
                            "exit_v2_factor_protect": _strategy_with_factors(
                                5.0,
                                8.0,
                                ["price_below_vwap", "peak_giveback_from_profit"],
                            )
                        },
                        forward_return=10.0,
                    ),
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = audit_factor_exit_report(
        records_path=records_path,
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit_factors",
    )

    single = result["report"]["by_trigger_factor"]["single_factors"]
    combo = result["report"]["by_trigger_factor"]["factor_combinations"]
    assert single["exit_v2_factor_protect:price_below_vwap"]["trigger_count"] == 2
    assert single["exit_v2_factor_protect:price_below_vwap"]["forward_tail_avoided_count"] == 1
    assert single["exit_v2_factor_protect:peak_giveback_from_profit"]["avg_missed_vs_forward_pct"] == 5.0
    combo_key = "exit_v2_factor_protect:peak_giveback_from_profit+price_below_vwap"
    assert combo[combo_key]["trigger_count"] == 1
