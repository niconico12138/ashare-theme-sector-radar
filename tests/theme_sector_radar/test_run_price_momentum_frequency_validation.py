import json

from scripts.run_price_momentum_frequency_validation import run_price_momentum_frequency_validation


def _write_candidates(root, scores):
    date_dir = root / "2026-07-07"
    date_dir.mkdir(parents=True)
    candidates = [
        {"code": f"60000{index}", "opening_drive_score": score, "forward_return_pct": forward_return}
        for index, (score, forward_return) in enumerate(scores, start=1)
    ]
    (date_dir / "top30_candidates.intraday_backfilled.json").write_text(
        json.dumps({"candidates": candidates}), encoding="utf-8"
    )


def test_frequency_validation_writes_paper_only_combined_report(tmp_path):
    root_5m = tmp_path / "five"
    root_1m = tmp_path / "one"
    _write_candidates(root_5m, [(90.0, 3.0), (80.0, 2.0), (30.0, -1.0), (20.0, -2.0)])
    _write_candidates(root_1m, [(90.0, 2.0), (80.0, 1.5), (30.0, -0.5), (20.0, -1.5)])

    result = run_price_momentum_frequency_validation(
        candidate_root_5m=root_5m,
        candidate_root_1m=root_1m,
        output_dir=tmp_path / "out",
        as_of="2026-07-10",
        snapshot_label="unit",
        min_labeled_samples=4,
    )

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    assert result["report"]["paper_trading_only"] is True
    assert result["report"]["no_execution_signals"] is True
    assert result["report"]["does_not_modify_official_scores"] is True
    assert result["report"]["comparison"]["eligible_factor_ids"] == ["opening_drive_score"]
    assert result["report"]["comparison"]["factors"]["opening_drive_score"]["confirmation_status"] == "1m_confirmed"
