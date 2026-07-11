"""Build the unified joint decision summary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from theme_sector_radar.joint_decision.policy import (
    build_agent_lookup,
    classify_sector,
    normalize_stock,
)
from theme_sector_radar.joint_decision.schema import (
    DECISION_MODE,
    OFFICIAL_SCORE_FACTORS,
    PROFILE_ONLY_FACTORS,
    SCHEMA_VERSION,
    SECTOR_BUCKETS,
    SHADOW_FACTORS,
    STOCK_BUCKETS,
)


def build_joint_decision_summary(
    as_of: str,
    unified_report: dict[str, Any],
    sectors: list[dict[str, Any]] | None = None,
    concepts: list[dict[str, Any]] | None = None,
    top30: dict[str, Any] | None = None,
    aihf_ranking: dict[str, Any] | None = None,
    v2_monitor: dict[str, Any] | None = None,
    top_n: int = 10,
    load_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build a watch-only decision summary from existing artifacts."""
    sectors = sectors or []
    concepts = concepts or []
    top30 = top30 or {}
    aihf_ranking = aihf_ranking or {}
    v2_monitor = v2_monitor or {}
    load_warnings = load_warnings or []

    sector_decision = _build_sector_decision(sectors, concepts, top_n)
    stock_decision = _build_stock_decision(unified_report, top30, aihf_ranking, top_n)
    agent_review = _build_agent_review(stock_decision)
    risk_review = _build_risk_review(unified_report, load_warnings, stock_decision)

    system_status = _build_system_status(unified_report, risk_review)
    source_artifacts = {
        "unified_report": bool(unified_report),
        "top30_candidates": bool(top30),
        "aihf_ranking": bool(aihf_ranking),
        "v2_monitor": bool(v2_monitor),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "decision_mode": DECISION_MODE,
        "system_status": system_status,
        "risk_gate": _build_risk_gate(system_status, risk_review, unified_report, v2_monitor, agent_review),
        "sector_decision": sector_decision,
        "stock_decision": stock_decision,
        "factor_context": _build_factor_context(v2_monitor),
        "agent_review": agent_review,
        "risk_review": risk_review,
        "source_artifacts": source_artifacts,
        "audit": {
            "source_artifacts": source_artifacts,
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "shadow_only": True,
        },
    }


def _build_system_status(unified_report: dict[str, Any], risk_review: dict[str, Any]) -> dict[str, Any]:
    run_health = unified_report.get("run_health", {}).get("status", "unknown")
    data_quality = unified_report.get("data_quality", {}).get("status", "unknown")
    blockers = risk_review.get("blockers", [])
    return {
        "run_health": run_health,
        "data_quality": data_quality,
        "market_regime": "unknown",
        "allow_observation": run_health != "fail" and data_quality != "fail" and not blockers,
    }


def _build_risk_gate(
    system_status: dict[str, Any],
    risk_review: dict[str, Any],
    unified_report: dict[str, Any],
    v2_monitor: dict[str, Any],
    agent_review: dict[str, Any],
) -> dict[str, Any]:
    gate_details = {
        "data_quality_gate": _build_data_quality_gate(unified_report),
        "run_health_gate": _build_run_health_gate(unified_report),
        "market_regime_gate": _build_market_regime_gate(system_status),
        "factor_quality_gate": _build_factor_quality_gate(v2_monitor),
        "agent_consensus_gate": _build_agent_consensus_gate(agent_review),
    }
    return {
        "allow_observation": bool(system_status.get("allow_observation", False)),
        "allow_trade_candidate_generation": False,
        "blockers": list(risk_review.get("blockers", [])),
        "warnings": list(risk_review.get("warnings", [])),
        "gate_details": gate_details,
    }


def _build_data_quality_gate(unified_report: dict[str, Any]) -> dict[str, Any]:
    data_quality = unified_report.get("data_quality", {})
    status = data_quality.get("status", "unknown")
    blockers = ["data_quality_fail"] if status == "fail" else []
    return _gate(status, status != "fail", blockers, data_quality.get("warnings", []))


def _build_run_health_gate(unified_report: dict[str, Any]) -> dict[str, Any]:
    run_health = unified_report.get("run_health", {})
    status = run_health.get("status", "unknown")
    blockers = ["run_health_fail"] if status == "fail" else []
    return _gate(status, status != "fail", blockers, run_health.get("reasons", []))


def _build_market_regime_gate(system_status: dict[str, Any]) -> dict[str, Any]:
    status = system_status.get("market_regime", "unknown")
    return _gate(status, True, [], [])


def _build_factor_quality_gate(v2_monitor: dict[str, Any]) -> dict[str, Any]:
    if not v2_monitor:
        return _gate("missing", True, [], ["v2_monitor_missing"])
    status = v2_monitor.get("status_light", {}).get("status", "unknown")
    warnings = [] if status in {"ok", "pass"} else [f"v2_monitor_{status}"]
    return _gate(status, True, [], warnings)


def _build_agent_consensus_gate(agent_review: dict[str, Any]) -> dict[str, Any]:
    coverage = agent_review.get("coverage", 0.0)
    if agent_review.get("risk_flagged"):
        return _gate("risk_flagged", True, [], ["agent_risk_flagged"])
    if agent_review.get("conflicted"):
        return _gate("conflicted", True, [], ["agent_conflicted"])
    if agent_review.get("confirmed"):
        return _gate("confirmed", True, [], [])
    if coverage == 0:
        return _gate("missing", True, [], ["agent_review_missing"])
    return _gate("reviewed", True, [], [])


def _gate(status: Any, allow_observation: bool, blockers: list[Any], warnings: list[Any]) -> dict[str, Any]:
    return {
        "status": str(status or "unknown"),
        "allow_observation": bool(allow_observation),
        "blockers": sorted(set(str(item) for item in blockers if item)),
        "warnings": sorted(set(str(item) for item in warnings if item)),
    }

def _build_sector_decision(
    sectors: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    top_n: int,
) -> dict[str, list[dict[str, Any]]]:
    result = {bucket: [] for bucket in SECTOR_BUCKETS}
    for raw in list(sectors) + list(concepts):
        item = classify_sector(raw)
        result[item["decision_bucket"]].append(item)

    for bucket in result:
        result[bucket].sort(key=lambda x: x.get("ranking_score", 0.0), reverse=True)
        result[bucket] = result[bucket][:top_n]
    return result


def _build_stock_decision(
    unified_report: dict[str, Any],
    top30: dict[str, Any],
    aihf_ranking: dict[str, Any],
    top_n: int,
) -> dict[str, list[dict[str, Any]]]:
    agent_lookup = build_agent_lookup(aihf_ranking)
    result = {bucket: [] for bucket in STOCK_BUCKETS}
    seen: set[str] = set()

    candidates: list[tuple[dict[str, Any], str]] = []
    for item in unified_report.get("trend_top_stocks", []):
        candidates.append((item, "trend_top"))
    for item in unified_report.get("burst_top_stocks", []):
        candidates.append((item, "burst_top"))
    for item in top30.get("candidates", []):
        candidates.append((item, item.get("source_pool", "top30")))

    for raw, source_pool in candidates:
        item = normalize_stock(raw, agent_lookup, source_pool)
        code = item.get("code")
        if not code or code in seen:
            continue
        seen.add(code)
        bucket = item["decision_bucket"]
        result[bucket].append(item)

    for bucket in result:
        result[bucket].sort(
            key=lambda x: (
                x.get("final_score") if x.get("final_score") is not None else -1,
                x.get("v2_score") if x.get("v2_score") is not None else -1,
            ),
            reverse=True,
        )
        result[bucket] = result[bucket][:top_n]
    return result


def _build_agent_review(stock_decision: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    all_items = [item for bucket in stock_decision.values() for item in bucket]
    reviewed = [item for item in all_items if item.get("agent_review_state") != "missing"]
    total = len(all_items)

    return {
        "coverage": round(len(reviewed) / total, 4) if total else 0.0,
        "confirmed": _agent_items(all_items, "confirmed"),
        "conflicted": _agent_items(all_items, "conflicted"),
        "risk_flagged": _agent_items(all_items, "risk_flagged"),
        "missing": _agent_items(all_items, "missing"),
    }


def _agent_items(items: list[dict[str, Any]], state: str) -> list[dict[str, Any]]:
    return [
        {
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "agent_score": item.get("agent_score"),
            "risk_level": item.get("risk_level", "unknown"),
        }
        for item in items
        if item.get("agent_review_state") == state
    ]


def _build_risk_review(
    unified_report: dict[str, Any],
    load_warnings: list[str],
    stock_decision: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    warnings = list(load_warnings)
    warnings.extend(unified_report.get("run_health", {}).get("reasons", []))
    warnings.extend(unified_report.get("data_quality", {}).get("warnings", []))

    blockers: list[str] = []
    if unified_report.get("run_health", {}).get("status") == "fail":
        blockers.append("run_health_fail")
    if unified_report.get("data_quality", {}).get("status") == "fail":
        blockers.append("data_quality_fail")
    if not any(stock_decision.get(bucket) for bucket in ["core_watch", "v2_opportunity", "short_burst"]):
        warnings.append("no_primary_stock_candidates")

    return {
        "warnings": sorted(set(str(w) for w in warnings if w)),
        "blockers": sorted(set(blockers)),
    }


def _build_factor_context(v2_monitor: dict[str, Any]) -> dict[str, Any]:
    return {
        "official_score_factors": list(OFFICIAL_SCORE_FACTORS),
        "shadow_factors": list(SHADOW_FACTORS),
        "profile_only_factors": list(PROFILE_ONLY_FACTORS),
        "v2_monitor_available": bool(v2_monitor),
        "v2_monitor_status": v2_monitor.get("status_light", {}).get("status", "unknown") if v2_monitor else "missing",
    }



