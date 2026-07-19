import json

import pytest

from scripts.audit_timing_dual_exit_validation import audit_dual_exit_validation


def test_audit_dual_exit_validation_writes_json_and_markdown(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "as_of": "2026-07-01",
                        "code": "600001",
                        "boards": ["gas"],
                        "timing_version_id": "v31",
                        "forward_return_pct": -6.0,
                        "paper_exit_candidates": {
                            "paper_take_profit_protect_candidate": {
                                "triggered": True,
                                "fill_available": True,
                                "simulated_exit_return_pct": 2.0,
                                "trigger_factors": ["price_below_vwap"],
                            },
                            "paper_stop_loss_risk_candidate": {
                                "triggered": False,
                                "fill_available": False,
                                "simulated_exit_return_pct": None,
                                "trigger_factors": [],
                            },
                        },
                    },
                    {
                        "as_of": "2026-07-14",
                        "code": "600002",
                        "boards": ["gas"],
                        "timing_version_id": "v31",
                        "forward_return_pct": -6.0,
                        "paper_exit_candidates": {
                            "paper_take_profit_protect_candidate": {
                                "triggered": True,
                                "fill_available": True,
                                "simulated_exit_return_pct": 2.0,
                                "trigger_factors": ["price_below_vwap"],
                            }
                        },
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = audit_dual_exit_validation(
        records_path=records_path,
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        snapshot_label="unit",
        fold_count=3,
        min_labeled_triggers=1,
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    assert result["report"]["promotion_status"] == "paper_research_only"
    assert result["report"]["candidates"]["paper_take_profit_protect_candidate"]["summary"]["record_count"] == 1
    markdown = result["markdown_path"].read_text(encoding="utf-8")
    assert "Walk-Forward" in markdown
    assert "price_below_vwap" in markdown


def test_audit_dual_exit_validation_rejects_nonfinite_json(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text('{"records": [], "forged": NaN}', encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        audit_dual_exit_validation(
            records_path=records_path,
            output_dir=tmp_path / "out",
            as_of="2026-07-13",
            snapshot_label="unit",
        )
