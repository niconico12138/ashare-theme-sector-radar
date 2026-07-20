"""MCP facade for Theme Sector Radar paper/shadow research.

The scoring and data modules remain the source of truth. This module only
provides stable, structured tool boundaries for Codex or another MCP client.
It deliberately has no broker, order, or live-trading tool.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

try:  # Keep the research functions importable when an optional SDK is broken.
    from mcp.server.fastmcp import FastMCP
    _MCP_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - depends on local optional SDK
    _MCP_IMPORT_ERROR = exc

    class FastMCP:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def tool(self):
            return lambda function: function

        def run(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError(
                "MCP SDK could not be loaded; install a compatible mcp package"
            ) from _MCP_IMPORT_ERROR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAPER_MODE = "paper_shadow_research_only"

TOOL_SPECS = [
    {
        "name": "check_data_health",
        "description": "Check configured market data dependencies without changing data.",
        "read_only": True,
        "mode": PAPER_MODE,
    },
    {
        "name": "get_direction_candidates",
        "description": "Read a dated direction-score candidate artifact.",
        "read_only": True,
        "mode": PAPER_MODE,
    },
    {
        "name": "get_stock_ranking",
        "description": "Read a dated formal paper/shadow stock ranking artifact.",
        "read_only": True,
        "mode": PAPER_MODE,
    },
    {
        "name": "run_full_paper_pipeline",
        "description": "Run the existing unified research pipeline in paper/shadow mode.",
        "read_only": False,
        "mode": PAPER_MODE,
    },
]


def safety_envelope() -> dict[str, Any]:
    return {
        "mode": PAPER_MODE,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "broker_connected": False,
        "order_instruction_generated": False,
    }


def _validate_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of_date must be canonical ISO YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError("as_of_date must be canonical ISO YYYY-MM-DD")
    return value


def _read_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    target = Path(path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("research artifact must be a JSON object")
    return payload


def _resolve_report_path(path: str | None, default: Path) -> Path:
    target = Path(path) if path else default
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    return target


def _date_guard(payload: dict[str, Any], as_of_date: str) -> None:
    actual = payload.get("as_of_date") or payload.get("as_of")
    if actual != as_of_date:
        raise ValueError(
            f"report date mismatch: expected {as_of_date}, got {actual!r}"
        )


def check_data_health() -> dict[str, Any]:
    """Return data-service health; failures are reported, not hidden."""
    result: dict[str, Any] = {**safety_envelope(), "status": "unavailable"}
    try:
        from theme_sector_radar.data.market_data_http_client import MarketDataHttpClient

        health = MarketDataHttpClient().health_check()
        result.update({"status": "ok", "health": health})
    except Exception as exc:  # pragma: no cover - dependency/service boundary
        result.update({"status": "unavailable", "error": str(exc)})
    return result


def get_direction_candidates(
    as_of_date: str,
    *,
    candidates_path: str | None = None,
) -> dict[str, Any]:
    """Read direction candidates without recalculating or mutating artifacts."""
    as_of_date = _validate_date(as_of_date)
    path = _resolve_report_path(
        candidates_path,
        PROJECT_ROOT
        / "reports"
        / "paper_shadow"
        / f"industry_direction_{as_of_date}"
        / "industry_direction_candidates.json",
    )
    if not path.is_file():
        return {
            **safety_envelope(),
            "status": "unavailable",
            "as_of_date": as_of_date,
            "selected_count": 0,
            "path": str(path),
            "error": "direction candidate artifact is missing",
        }
    payload = _read_json(path)
    _date_guard(payload, as_of_date)
    selected = []
    for key in ("core_candidates", "supplemental_candidates", "confirmation_required"):
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            raise ValueError(f"{key} must be an array")
        selected.extend(rows)
    return {
        **safety_envelope(),
        "status": "ok",
        "as_of_date": as_of_date,
        "selected_count": len(selected),
        "selected": selected,
        "path": str(path),
    }


def get_stock_ranking(
    as_of_date: str,
    *,
    report_path: str | None = None,
) -> dict[str, Any]:
    """Read formal paper/shadow ranking and preserve its provenance fields."""
    as_of_date = _validate_date(as_of_date)
    path = _resolve_report_path(
        report_path,
        PROJECT_ROOT / "reports" / "unified" / as_of_date / "unified_report.json",
    )
    if not path.is_file():
        return {
            **safety_envelope(),
            "status": "unavailable",
            "as_of_date": as_of_date,
            "selected_count": 0,
            "path": str(path),
            "error": "unified report is missing",
        }
    payload = _read_json(path)
    _date_guard(payload, as_of_date)
    formal = payload.get("formal_candidate_selection")
    if not isinstance(formal, dict):
        raise ValueError("formal_candidate_selection must be an object")
    rows = formal.get("selected", [])
    if not isinstance(rows, list):
        raise ValueError("formal candidate selected must be an array")
    return {
        **safety_envelope(),
        "status": formal.get("status", "unavailable"),
        "as_of_date": as_of_date,
        "selected_count": len(rows),
        "selected": rows,
        "run_health": payload.get("run_health", {}),
        "data_quality": payload.get("data_quality", {}),
        "path": str(path),
    }


def run_full_paper_pipeline(
    as_of_date: str,
    *,
    mode: str = "quick",
    sector_history_root: str | None = None,
    sector_cluster_map_path: str | None = None,
) -> dict[str, Any]:
    """Run the existing unified pipeline; never enables live execution."""
    as_of_date = _validate_date(as_of_date)
    if mode not in {"quick", "deep"}:
        raise ValueError("mode must be quick or deep")
    from unified_pipeline import run_pipeline

    result = run_pipeline(
        as_of_date=as_of_date,
        mode=mode,
        sector_history_root=sector_history_root,
        sector_cluster_map_path=sector_cluster_map_path,
        candidate_chain="direction_linkage_v2",
    )
    return {
        **safety_envelope(),
        "status": result.get("run_health", {}).get("status", "unknown"),
        "as_of_date": as_of_date,
        "selected_count": result.get("formal_candidate_selection", {}).get(
            "selected_count", 0
        ),
        "report": result,
    }


mcp = FastMCP(
    "theme-sector-radar",
    instructions=(
        "Paper/shadow research only. Use dated artifacts and fail closed on "
        "missing or mismatched evidence. Never connect to a broker or create orders."
    ),
)
mcp.tool()(check_data_health)
mcp.tool()(get_direction_candidates)
mcp.tool()(get_stock_ranking)
mcp.tool()(run_full_paper_pipeline)


def main() -> None:
    if _MCP_IMPORT_ERROR is not None:
        raise RuntimeError(
            "MCP SDK could not be loaded; install a compatible mcp package"
        ) from _MCP_IMPORT_ERROR
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
