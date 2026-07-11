"""Validation helpers for joint decision summary artifacts."""

from __future__ import annotations

import json
from typing import Any

from theme_sector_radar.joint_decision.schema import DECISION_MODE, SCHEMA_VERSION, STOCK_BUCKETS

FORBIDDEN_TRADE_FIELDS = [
    "buy_point",
    "entry_price",
    "trigger_price",
    "stop_loss",
    "take_profit",
    "order",
    "execute_trade",
]

REQUIRED_TOP_LEVEL_FIELDS = [
    "schema_version",
    "as_of",
    "decision_mode",
    "system_status",
    "risk_gate",
    "sector_decision",
    "stock_decision",
    "factor_context",
    "agent_review",
    "risk_review",
    "audit",
]

REQUIRED_GATE_DETAILS = [
    "data_quality_gate",
    "run_health_gate",
    "market_regime_gate",
    "factor_quality_gate",
    "agent_consensus_gate",
]

REQUIRED_STOCK_FIELDS = [
    "code",
    "name",
    "sector_name",
    "decision_bucket",
    "opportunity_type",
    "action_state",
    "scores",
    "factor_states",
    "reason_codes",
    "invalidation_flags",
    "manual_review_reason",
]

REQUIRED_SCORE_FIELDS = ["final_score", "v2_score", "selection_score", "selection_score_adjusted"]

REQUIRED_FACTOR_STATES = [
    "trend_state",
    "sector_support",
    "breakout_structure",
    "drawdown_state",
    "liquidity_state",
    "overheat_state",
]


def validate_joint_decision_summary(summary: dict[str, Any]) -> list[str]:
    """Return schema contract errors for a joint decision summary."""
    errors: list[str] = []

    _validate_top_level(summary, errors)
    _validate_risk_gate(summary.get("risk_gate"), errors)
    _validate_stock_decision(summary.get("stock_decision"), errors)
    _validate_audit(summary.get("audit"), errors)
    _validate_forbidden_trade_fields(summary, errors)

    return errors


def _validate_top_level(summary: dict[str, Any], errors: list[str]) -> None:
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in summary:
            errors.append(f"missing top-level field: {field}")

    if summary.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if summary.get("decision_mode") != DECISION_MODE:
        errors.append("decision_mode must be watch_only")


def _validate_risk_gate(risk_gate: Any, errors: list[str]) -> None:
    if not isinstance(risk_gate, dict):
        errors.append("risk_gate must be an object")
        return

    if risk_gate.get("allow_trade_candidate_generation") is not False:
        errors.append("risk_gate.allow_trade_candidate_generation must be false")
    if not isinstance(risk_gate.get("blockers"), list):
        errors.append("risk_gate.blockers must be a list")
    if not isinstance(risk_gate.get("warnings"), list):
        errors.append("risk_gate.warnings must be a list")

    gate_details = risk_gate.get("gate_details")
    if not isinstance(gate_details, dict):
        errors.append("risk_gate.gate_details must be an object")
        return

    for gate_name in REQUIRED_GATE_DETAILS:
        gate = gate_details.get(gate_name)
        if not isinstance(gate, dict):
            errors.append(f"risk_gate.gate_details.{gate_name} must be an object")
            continue
        for field in ["status", "allow_observation", "blockers", "warnings"]:
            if field not in gate:
                errors.append(f"risk_gate.gate_details.{gate_name}.{field} is required")


def _validate_stock_decision(stock_decision: Any, errors: list[str]) -> None:
    if not isinstance(stock_decision, dict):
        errors.append("stock_decision must be an object")
        return

    for bucket in STOCK_BUCKETS:
        items = stock_decision.get(bucket)
        if not isinstance(items, list):
            errors.append(f"stock_decision.{bucket} must be a list")
            continue
        for idx, item in enumerate(items):
            _validate_stock_item(bucket, idx, item, errors)


def _validate_stock_item(bucket: str, idx: int, item: Any, errors: list[str]) -> None:
    prefix = f"stock_decision.{bucket}[{idx}]"
    if not isinstance(item, dict):
        errors.append(f"{prefix} must be an object")
        return

    for field in REQUIRED_STOCK_FIELDS:
        if field not in item:
            errors.append(f"{prefix}.{field} is required")

    if item.get("action_state") != DECISION_MODE:
        errors.append(f"{prefix}.action_state must be watch_only")

    scores = item.get("scores")
    if isinstance(scores, dict):
        for field in REQUIRED_SCORE_FIELDS:
            if field not in scores:
                errors.append(f"{prefix}.scores.{field} is required")
    else:
        errors.append(f"{prefix}.scores must be an object")

    factor_states = item.get("factor_states")
    if isinstance(factor_states, dict):
        for field in REQUIRED_FACTOR_STATES:
            if field not in factor_states:
                errors.append(f"{prefix}.factor_states.{field} is required")
    else:
        errors.append(f"{prefix}.factor_states must be an object")


def _validate_audit(audit: Any, errors: list[str]) -> None:
    if not isinstance(audit, dict):
        errors.append("audit must be an object")
        return
    if audit.get("shadow_only") is not True:
        errors.append("audit.shadow_only must be true")
    if not isinstance(audit.get("source_artifacts"), dict):
        errors.append("audit.source_artifacts must be an object")
    generated_at = audit.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.endswith("Z"):
        errors.append("audit.generated_at must be a UTC timestamp ending with Z")


def _validate_forbidden_trade_fields(summary: dict[str, Any], errors: list[str]) -> None:
    text = json.dumps(summary, ensure_ascii=False).lower()
    for field in FORBIDDEN_TRADE_FIELDS:
        if field in text:
            errors.append(f"forbidden trade field present: {field}")
