from scripts.backfill_news_emotion_factors import (
    _candidate_event_tokens,
    _event_stats_by_token,
    _merge_event_stats,
)


def test_event_mapping_matches_candidate_board_by_normalized_substring():
    events = [
        {
            "event_date": "2026-07-02",
            "title": "工程机械ETF走强",
            "related_symbols": ["工程机械"],
        }
    ]
    candidate = {
        "code": "600001",
        "name": "Sample",
        "boards": ["高端工程机械"],
    }

    stats = _event_stats_by_token(events, "2026-07-02")
    merged = _merge_event_stats(_candidate_event_tokens(candidate), stats)

    assert merged["news_count_3d"] == 1
    assert merged["event_age_days"] == 0


def test_event_mapping_matches_candidate_name_in_event_title():
    events = [
        {
            "event_date": "2026-07-02",
            "title": "Sample发布重大订单公告",
            "related_symbols": ["unknown"],
        }
    ]
    candidate = {
        "code": "600001",
        "name": "Sample",
        "boards": ["Unrelated"],
    }

    stats = _event_stats_by_token(events, "2026-07-02")
    merged = _merge_event_stats(_candidate_event_tokens(candidate), stats)

    assert merged["news_count_3d"] == 1
    assert merged["earnings_catalyst_count"] == 1
