from datetime import date, timedelta

import pytest

from theme_sector_radar.timing.nonstationary_validation import (
    build_nonstationary_windows,
    concentration_summary,
    current_regime_summary,
    labeled_trading_dates,
    observed_evaluation_tail_summary,
)


def _observed_tail_report():
    current = date(2026, 7, 13)
    dates = []
    while len(dates) < 20:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current -= timedelta(days=1)
    dates = sorted(dates)
    source_dates = dates[:18]
    complete_dates = dates[:5]
    return {
        "as_of": dates[-1],
        "calendar_source": {"dates": dates},
        "label_source": {
            "revalidated_candidate_source_identity": {
                "status": "validated",
                "document_dates": source_dates,
                "complete_candidate_dates": complete_dates,
            }
        },
        "holdout_evidence": {
            "status": "observed_evaluation_tail",
            "blind": False,
            "eligible_for_oos_claim": False,
        },
        "windows": {
            "holdout": {
                "dates": dates,
                "date_count": 20,
                "source_document_date_count": 18,
                "complete_candidate_date_count": 5,
                "source_document_date_coverage_rate": 0.9,
                "complete_candidate_date_coverage_rate": 0.25,
                "candidate_date_coverage_status": "insufficient",
            }
        },
    }


def test_observed_tail_summary_requires_exact_dates_and_consistent_coverage():
    report = _observed_tail_report()

    summary = observed_evaluation_tail_summary(report)

    assert summary["date_count"] == 20
    assert summary["source_document_date_coverage_rate"] == 0.9


def test_observed_tail_summary_can_explicitly_report_short_insufficient_window():
    report = _observed_tail_report()
    short_dates = report["windows"]["holdout"]["dates"][-10:]
    report["calendar_source"]["dates"] = short_dates
    report["label_source"]["revalidated_candidate_source_identity"].update(
        document_dates=short_dates[:9],
        complete_candidate_dates=short_dates[:3],
    )
    report["windows"]["holdout"].update(
        dates=short_dates,
        date_count=10,
        source_document_date_count=9,
        complete_candidate_date_count=3,
        source_document_date_coverage_rate=0.9,
        complete_candidate_date_coverage_rate=0.3,
        candidate_date_coverage_status="insufficient",
    )

    with pytest.raises(ValueError, match="exactly 20"):
        observed_evaluation_tail_summary(report)

    summary = observed_evaluation_tail_summary(report, allow_short_window=True)

    assert summary["date_count"] == 10
    assert summary["candidate_date_coverage_status"] == "insufficient"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda report: report["windows"]["holdout"].update(source_document_date_count=21),
        lambda report: report["windows"]["holdout"].update(complete_candidate_date_coverage_rate=0.5),
        lambda report: report["windows"]["holdout"].update(
            source_document_date_count=4,
            source_document_date_coverage_rate=0.2,
        ),
        lambda report: report["windows"]["holdout"].update(dates=["2026-07-01"] * 20),
        lambda report: report["windows"]["holdout"]["dates"].__setitem__(-1, "2026-12-31"),
    ],
)
def test_observed_tail_summary_rejects_internally_inconsistent_metadata(mutate):
    report = _observed_tail_report()
    mutate(report)

    with pytest.raises(ValueError, match="observed evaluation tail"):
        observed_evaluation_tail_summary(report)


def test_observed_tail_summary_requires_verified_calendar_last_twenty_dates():
    report = _observed_tail_report()
    report["calendar_source"]["dates"] = ["2026-05-01", *report["calendar_source"]["dates"]]
    report["windows"]["holdout"]["dates"][0] = "2026-05-01"

    with pytest.raises(ValueError, match="last 20 trading dates"):
        observed_evaluation_tail_summary(report)


def test_observed_tail_summary_recomputes_coverage_from_candidate_manifest():
    report = _observed_tail_report()
    report["windows"]["holdout"].update(
        source_document_date_count=20,
        source_document_date_coverage_rate=1.0,
    )

    with pytest.raises(ValueError, match="candidate manifest"):
        observed_evaluation_tail_summary(report)


def test_current_regime_is_bound_to_latest_exchange_session():
    rows = [
        {"_sample_date": "2026-07-10", "market_regime_score": 30},
        {"_sample_date": "2026-07-13", "market_regime_score": 70},
        {"_sample_date": "2026-07-13", "market_regime_score": 65},
    ]

    summary = current_regime_summary(rows, calendar_dates=["2026-07-10", "2026-07-13"])

    assert summary == {
        "status": "ok",
        "date": "2026-07-13",
        "regime": "strong",
        "labeled_record_count": 2,
    }


def test_current_regime_does_not_fall_back_when_latest_session_is_unlabeled():
    summary = current_regime_summary(
        [{"_sample_date": "2026-07-10", "market_regime_score": 70}],
        calendar_dates=["2026-07-10", "2026-07-13"],
    )

    assert summary["status"] == "insufficient"
    assert summary["date"] == "2026-07-13"
    assert summary["regime"] is None


def test_current_regime_rejects_nonfinite_market_score():
    summary = current_regime_summary(
        [{"_sample_date": "2026-07-13", "market_regime_score": float("nan")}],
        calendar_dates=["2026-07-13"],
    )

    assert summary == {
        "status": "insufficient",
        "date": "2026-07-13",
        "regime": None,
        "labeled_record_count": 0,
    }


def test_nonstationary_windows_keep_holdout_disjoint_from_recent_windows():
    start = date(2025, 1, 1)
    records = []
    current = start
    while len(records) < 150:
        if current.weekday() < 5:
            records.append({"as_of": current.isoformat(), "value": len(records), "forward_return_pct": 1.0})
        current += timedelta(days=1)

    report = build_nonstationary_windows(records, holdout_days=20)

    assert report["recent_60"]["date_count"] == 60
    assert report["recent_120"]["date_count"] == 120
    assert report["holdout"]["date_count"] == 20
    assert set(report["recent_60"]["dates"]).isdisjoint(report["holdout"]["dates"])
    assert set(report["recent_120"]["dates"]).isdisjoint(report["holdout"]["dates"])
    assert report["holdout_evidence"] == {
        "status": "observed_evaluation_tail",
        "blind": False,
        "eligible_for_oos_claim": False,
        "reason": "strategy thresholds were observed and iterated before an immutable prospective freeze",
    }
    assert report["paper_trading_only"] is True


def test_nonstationary_windows_mark_missing_long_window_as_insufficient():
    records = [{"as_of": f"2026-01-{day:02d}", "forward_return_pct": 1.0} for day in range(1, 31)]

    report = build_nonstationary_windows(records, holdout_days=5)

    assert report["recent_60"]["status"] == "insufficient_sample"
    assert report["recent_120"]["status"] == "insufficient_sample"


def test_nonstationary_windows_use_labeled_dates_when_labels_exist():
    records = [
        {"as_of": "2026-01-01", "forward_return_pct": 1.0},
        {"as_of": "2026-01-02", "forward_return_pct": None},
        {"as_of": "2026-01-05", "forward_return_pct": -1.0},
    ]

    report = build_nonstationary_windows(records, holdout_days=1, recent_windows=(1,))

    assert report["recent_1"]["dates"] == ["2026-01-01"]
    assert report["holdout"]["dates"] == ["2026-01-05"]


def test_nonstationary_windows_use_explicit_calendar_and_cut_off_future_records():
    calendar_dates = [f"2026-01-{day:02d}" for day in range(1, 12)]
    records = [
        {"as_of": "2026-01-01", "value": 1},
        {"as_of": "2026-01-08", "value": 8},
        {"as_of": "2026-01-11", "value": 11},
    ]

    report = build_nonstationary_windows(
        records,
        as_of="2026-01-10",
        calendar_dates=calendar_dates,
        holdout_days=2,
        recent_windows=(3,),
    )

    assert report["holdout"]["dates"] == ["2026-01-09", "2026-01-10"]
    assert report["recent_3"]["dates"] == ["2026-01-06", "2026-01-07", "2026-01-08"]
    assert report["recent_3"]["record_count"] == 1
    assert report["all_history"]["record_count"] == 2
    assert report["as_of"] == "2026-01-10"


def test_concentration_uses_record_denominator_for_multi_board_rows():
    summary = concentration_summary(
        [
            {"as_of": "2026-01-01", "code": "1", "boards": ["A", "B"]},
            {"as_of": "2026-01-02", "code": "2", "boards": ["A", "C"]},
            {"as_of": "2026-01-03", "code": "3", "boards": []},
        ]
    )

    assert summary["top_board_share"] == 0.6667
    assert summary["board_coverage_rate"] == 0.6667


def test_labeled_trading_dates_excludes_unlabeled_weekend_snapshots():
    rows = [
        {"_sample_date": "2026-07-09", "forward_return_pct": 1.0, "_sample_mode": True},
        {"_sample_date": "2026-07-10", "forward_return_pct": 1.0},
        {"_sample_date": "2026-07-11", "forward_return_pct": 1.0, "_sample_mode": True},
        {"_sample_date": "2026-07-12", "forward_return_pct": -1.0, "_sample_mode": True},
        {"_sample_date": "2026-07-13", "forward_return_pct": -1.0},
    ]

    assert labeled_trading_dates(rows, as_of="2026-07-13") == ["2026-07-10", "2026-07-13"]


def test_nonstationary_windows_fail_closed_without_forward_labels():
    records = [
        {"as_of": "2026-07-10"},
        {"as_of": "2026-07-13"},
    ]

    report = build_nonstationary_windows(records, holdout_days=1, recent_windows=(1,))

    assert report["all_history"]["date_count"] == 0
    assert report["recent_1"]["status"] == "insufficient_sample"
    assert report["holdout"]["status"] == "insufficient_sample"
    assert report["calendar_source"] == "missing_labeled_records"
