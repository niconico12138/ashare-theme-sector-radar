"""Independent orchestration for concept direction shadow research."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from .data.board_membership_snapshot import (
    capture_membership_snapshot,
    load_membership_snapshot,
    write_membership_snapshot_once,
)
from .reporting.strict_json import load_strict_json, write_text_atomic
from .reporting.paper_only_contract import validate_no_executable_instructions
from .scoring.concept_direction_shadow import (
    DISCLAIMER,
    PAPER_MODE,
    score_concept_directions,
    select_concept_shadow_candidates,
)


def run_concept_shadow_pipeline(
    *,
    as_of_date: str,
    membership_root: Path | str,
    report_root: Path | str,
    history_client: Any,
    board_client: Any = None,
    today: date | None = None,
    captured_at: str | None = None,
    history_lookback_days: int = 60,
    top_n: int = 10,
) -> dict[str, Any]:
    """Run the concept-only research path without touching the formal chain."""
    as_of = date.fromisoformat(as_of_date)
    current_date = today or date.today()
    if history_lookback_days < 30:
        raise ValueError("history_lookback_days must be at least 30")

    try:
        snapshot, snapshot_sha256 = load_membership_snapshot(
            membership_root,
            as_of.isoformat(),
        )
    except FileNotFoundError as exc:
        if as_of != current_date:
            raise FileNotFoundError(
                f"historical membership snapshot is required for {as_of.isoformat()}"
            ) from exc
        if board_client is None:
            from .data.stockdb_board_client import StockDBBoardClient

            board_client = StockDBBoardClient()
        captured = capture_membership_snapshot(
            board_client,
            as_of_date=as_of.isoformat(),
            captured_at=captured_at,
        )
        write_membership_snapshot_once(membership_root, captured)
        snapshot, snapshot_sha256 = load_membership_snapshot(
            membership_root,
            as_of.isoformat(),
        )

    start_date = (as_of - timedelta(days=history_lookback_days)).isoformat()
    histories = {}
    for board in snapshot["boards"]:
        code = board["board_code"]
        histories[code] = history_client.get_history(
            board_code=code,
            board_name=board["board_name"],
            start_date=start_date,
            end_date=as_of.isoformat(),
            as_of_date=as_of.isoformat(),
        )
    score_report = score_concept_directions(
        snapshot,
        histories,
        snapshot_sha256=snapshot_sha256,
        as_of_date=as_of.isoformat(),
        minimum_history_rows=max(20, history_lookback_days // 2),
    )
    selection = select_concept_shadow_candidates(score_report, top_n=top_n)
    bridge = _bridge_snapshot_members(
        snapshot,
        selection,
        membership_snapshot_sha256=snapshot_sha256,
    )
    report = {
        "schema_version": "concept_shadow_pipeline_report.v1",
        "status": "ok",
        "mode": PAPER_MODE,
        "disclaimer": DISCLAIMER,
        "as_of_date": as_of.isoformat(),
        "formal_candidate_eligible": False,
        "provenance": {
            "membership_snapshot_sha256": snapshot_sha256,
            "membership_as_of_date": snapshot["as_of_date"],
            "membership_boards_sha256": snapshot["boards_sha256"],
        },
        "concept_direction": score_report,
        "concept_selection": selection,
        "bridge": bridge,
        "downstream_interface": {
            "status": "not_run",
            "input_contract": "stock_code_with_concept_provenance.v1",
        },
    }
    validate_no_executable_instructions(report, context="concept shadow report")
    output_path = (
        Path(report_root)
        / f"concept_direction_{as_of.isoformat()}"
        / "concept_shadow_report.json"
    )
    serialized = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"
    write_text_atomic(output_path, serialized)
    loaded = load_strict_json(output_path)
    validate_no_executable_instructions(
        loaded, context="persisted concept shadow report"
    )
    if loaded != report:
        raise ValueError("concept shadow report verification failed")
    return report


def _bridge_snapshot_members(
    snapshot: dict[str, Any],
    selection: dict[str, Any],
    *,
    membership_snapshot_sha256: str,
) -> dict[str, Any]:
    boards_by_code = {
        board["board_code"]: board for board in snapshot["boards"]
    }
    stock_concepts: dict[str, list[dict[str, str]]] = {}
    selected = selection["concept_shadow_candidates"]
    for selected_board in selected:
        code = selected_board["board_code"]
        board = boards_by_code.get(code)
        if board is None or board["board_name"] != selected_board["board_name"]:
            raise ValueError(f"selected concept is absent from membership snapshot: {code}")
        provenance = {
            "board_code": code,
            "board_name": board["board_name"],
            "source_key": board["source_key"],
            "symbols_sha256": board["symbols_sha256"],
            "raw_sha256": board["raw_sha256"],
            "as_of_date": snapshot["as_of_date"],
            "membership_snapshot_sha256": membership_snapshot_sha256,
            "direction_score_shadow": selected_board["direction_score_shadow"],
            "direction_state": selected_board["direction_state"],
            "concept_shadow_rank": selected_board["concept_shadow_rank"],
            "history_rows_sha256": selected_board["provenance"][
                "history_rows_sha256"
            ],
            "history_query": dict(selected_board["provenance"]["history_query"]),
        }
        for stock_code in board["member_codes"]:
            stock_concepts.setdefault(stock_code, []).append(dict(provenance))
    stocks = []
    for stock_code in sorted(stock_concepts):
        provenance_rows = sorted(
            stock_concepts[stock_code],
            key=lambda item: (item["board_code"], item["board_name"]),
        )
        stocks.append(
            {
                "stock_code": stock_code,
                "concept_provenance": provenance_rows,
                "formal_candidate_eligible": False,
            }
        )
    return {
        "schema_version": "concept_snapshot_member_bridge.v1",
        "mode": PAPER_MODE,
        "formal_candidate_eligible": False,
        "selected_concept_count": len(selected),
        "unique_stock_count": len(stocks),
        "stocks": stocks,
    }
