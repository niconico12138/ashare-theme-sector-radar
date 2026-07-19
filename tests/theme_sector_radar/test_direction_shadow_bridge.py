import hashlib
import json

from sector_stock_bridge import load_direction_candidate_shadow


def _candidate(rank, name, tier):
    return {
        "sector_id": f"industry_{rank}",
        "sector_name": name,
        "direction_score_shadow": 80.0 - rank,
        "time_series_score": 45.0,
        "rank_momentum_score": 70.0,
        "direction_state": "watch",
        "candidate_tier": tier,
    }


def test_direction_shadow_loader_exposes_only_confirmed_core_and_supplemental(tmp_path):
    path = tmp_path / "industry_direction_candidates.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "industry_direction_candidate_selection.v1",
                "mode": "paper_shadow_research_only",
                "as_of_date": "2026-07-17",
                "core_candidates": [_candidate(1, "Core", "core")],
                "supplemental_candidates": [
                    _candidate(6, "Supplemental", "supplemental")
                ],
                "confirmation_required": [
                    _candidate(2, "Pulse", "confirmation_required")
                ],
            },
            allow_nan=False,
        ),
        encoding="utf-8",
    )

    result = load_direction_candidate_shadow(
        "2026-07-17", candidate_path=path
    )

    assert result["status"] == "ok"
    assert [row["sector_name"] for row in result["eligible_sectors"]] == [
        "Core",
        "Supplemental",
    ]
    assert result["eligible_sectors"][0]["candidate_tier"] == "core"
    assert result["confirmation_required"] == [
        {
            "sector_name": "Pulse",
            "direction_score_shadow": 78.0,
            "direction_state": "pulse_confirmation_required",
        }
    ]
    assert len(result["sha256"]) == 64


def test_direction_shadow_loader_fails_closed_on_wrong_date(tmp_path):
    path = tmp_path / "industry_direction_candidates.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "industry_direction_candidate_selection.v1",
                "mode": "paper_shadow_research_only",
                "as_of_date": "2026-07-16",
                "core_candidates": [],
                "supplemental_candidates": [],
                "confirmation_required": [],
            }
        ),
        encoding="utf-8",
    )

    result = load_direction_candidate_shadow(
        "2026-07-17", candidate_path=path
    )

    assert result["status"] == "unavailable"
    assert result["eligible_sectors"] == []
    assert "as_of_date" in result["error"]


def test_run_bridge_isolates_shadow_market_requests_and_binds_consumed_payload(
    tmp_path, monkeypatch
):
    import sector_stock_bridge as bridge

    payload = {
        "as_of_date": "2026-07-17",
        "scores": [
            {
                "sector_name": "Legacy",
                "sector_type": "industry",
                "trend_continuation_score": 70.0,
                "short_term_burst_score": 60.0,
            }
        ],
    }
    source_path = tmp_path / "sector_scores.json"
    source_path.write_text(json.dumps({**payload, "unused": True}), encoding="utf-8")
    monkeypatch.setattr(
        bridge,
        "load_stable_sector_inputs",
        lambda *_args, **_kwargs: {"available": False},
    )
    monkeypatch.setattr(
        bridge,
        "load_direction_candidate_shadow",
        lambda _day: {
            "status": "ok",
            "mode": "paper_shadow_research_only",
            "path": str(tmp_path / "direction.json"),
            "sha256": "a" * 64,
            "error": None,
            "eligible_sectors": [
                {
                    "sector_name": "Shadow",
                    "sector_type": "industry",
                    "candidate_tier": "core",
                }
            ],
            "confirmation_required": [],
        },
    )
    monkeypatch.setattr(
        bridge,
        "fetch_sector_constituents",
        lambda name, *_args, **_kwargs: {
            "status": "ok",
            "stocks": [
                {
                    "code": "600001" if name == "Legacy" else "600002",
                    "name": name,
                    "weight": 1.0,
                }
            ],
            "source": "test",
            "error": None,
        },
    )
    quote_calls = []
    flow_calls = []
    monkeypatch.setattr(
        bridge,
        "fetch_tencent_quotes",
        lambda codes: quote_calls.append(sorted(codes)) or {},
    )
    monkeypatch.setattr(
        bridge,
        "fetch_individual_fund_flow",
        lambda codes: flow_calls.append(sorted(codes)) or {},
    )
    monkeypatch.setattr(
        bridge,
        "fetch_sector_fund_flow",
        lambda _name: {
            "status": "degraded",
            "direction": "neutral",
            "error": "offline",
        },
    )

    result = bridge.run_bridge(
        as_of_date="2026-07-17",
        trend_top_n=1,
        burst_top_n=1,
        min_relevance=0.0,
        _validated_score_report=("2026-07-17", source_path, payload),
    )

    assert quote_calls == [["600001"], ["600002"]]
    assert flow_calls == [["600001"], ["600002"]]
    score_input = result["linkage_research"]["score_input"]
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert score_input["sha256"] == hashlib.sha256(canonical).hexdigest()
    assert score_input["sha256_basis"] == "canonical_validated_payload"
    assert score_input["source_file_sha256"] == hashlib.sha256(
        source_path.read_bytes()
    ).hexdigest()
    assert result["linkage_research"]["effective_policy"][
        "matches_frozen_baseline"
    ] is False

    quote_calls.clear()
    flow_calls.clear()
    direction_only = bridge.run_bridge(
        as_of_date="2026-07-17",
        trend_top_n=1,
        burst_top_n=1,
        min_relevance=0.0,
        include_legacy_sector_paths=False,
        _validated_score_report=("2026-07-17", source_path, payload),
    )

    assert direction_only["legacy_sector_paths_enabled"] is False
    assert direction_only["active_sector_path"] == "direction_shadow_only"
    assert direction_only["trend_sectors"] == []
    assert direction_only["burst_sectors"] == []
    assert quote_calls == [["600002"]]
    assert flow_calls == [["600002"]]
    assert direction_only["linkage_research"][
        "direction_constituent_source_summary"
    ]["test"] == 1
