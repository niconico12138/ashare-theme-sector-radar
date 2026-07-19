"""Production guardrails for paper-only structured artifacts."""

from __future__ import annotations

import re
from typing import Any


EXECUTABLE_INSTRUCTION_KEYS = frozenset({
    "allocation_pct",
    "action_command",
    "action_commands",
    "action",
    "buy_point",
    "broker_order",
    "command",
    "commands",
    "entry_instruction",
    "entry_instructions",
    "entry_price",
    "execute_trade",
    "execution",
    "execution_instruction",
    "execution_instructions",
    "execution_side",
    "exit_instruction",
    "exit_instructions",
    "order",
    "order_instruction",
    "order_instructions",
    "order_request",
    "order_requests",
    "orders",
    "limit_price",
    "live_order",
    "position_instruction",
    "position_instructions",
    "position",
    "position_pct",
    "position_quantity",
    "position_size",
    "qty",
    "quantity",
    "sell_point",
    "side",
    "stop_loss",
    "submit_order",
    "submit_orders",
    "take_profit",
    "target_position",
    "target_price",
    "trade_instruction",
    "trade_instructions",
    "trade_action",
    "trade",
    "trade_direction",
    "trade_side",
    "trade_trigger",
    "trigger_price",
    "order_price",
    "shares",
})

_EXECUTABLE_COMPACT_KEYS = frozenset(
    re.sub(r"[^a-z0-9]+", "", key.casefold())
    for key in EXECUTABLE_INSTRUCTION_KEYS
)

_EXECUTABLE_KEY_TOKENS = frozenset({
    "broker",
    "command",
    "commands",
    "qty",
    "quantity",
    "shares",
})

_DIRECTION_KEYS = frozenset({"action", "direction", "executionside", "side", "tradedirection", "tradeside"})
_SIZING_KEYS = frozenset({
    "allocation",
    "allocationpct",
    "position",
    "positionpct",
    "positionsize",
    "qty",
    "quantity",
    "shares",
    "size",
    "units",
})
_IDENTITY_KEYS = frozenset({"code", "instrument", "security", "symbol", "ticker"})
_PRICE_KEYS = frozenset({"entryprice", "limitprice", "orderprice", "price", "targetprice", "triggerprice"})
_TIME_IN_FORCE_KEYS = frozenset({"tif", "timeinforce", "validity"})
_NEGATIVE_AUDIT_KEYS = frozenset({
    "brokerconnection",
    "liveorderinstructiongenerated",
})


def _compact_key(key: Any) -> str | None:
    if not isinstance(key, str):
        return None
    normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key).casefold()
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _subtree_compact_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested_value in value.items():
            compact = _compact_key(key)
            if compact is not None:
                keys.add(compact)
            keys.update(_subtree_compact_keys(nested_value))
    elif isinstance(value, (list, tuple)):
        for nested_value in value:
            keys.update(_subtree_compact_keys(nested_value))
    return keys


def _is_complete_execution_payload(value: dict[Any, Any]) -> bool:
    direct_keys = {_compact_key(key) for key in value}
    direct_keys.discard(None)
    subtree_keys = _subtree_compact_keys(value)
    return bool(
        (direct_keys & _DIRECTION_KEYS or direct_keys & _SIZING_KEYS)
        and subtree_keys & _DIRECTION_KEYS
        and subtree_keys & _SIZING_KEYS
        and subtree_keys & (_IDENTITY_KEYS | _PRICE_KEYS | _TIME_IN_FORCE_KEYS)
    )


def _is_executable_instruction_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key).casefold()
    compact = _compact_key(key)
    if (
        normalized in EXECUTABLE_INSTRUCTION_KEYS
        or compact in _EXECUTABLE_COMPACT_KEYS
    ):
        return True
    tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", normalized)
        if token
    }
    if tokens & _EXECUTABLE_KEY_TOKENS:
        return True
    if "action" in tokens and bool(tokens & {"execute", "execution", "order", "trade"}):
        return True
    if "side" in tokens and bool(tokens & {"execute", "execution", "order", "trade"}):
        return True
    if "position" in tokens and bool(
        tokens & {"pct", "percent", "quantity", "ratio", "size", "target"}
    ):
        return True
    return "side" in tokens and bool(tokens & {"buy", "sell", "trade"})


def extract_executable_instructions(payload: Any) -> tuple[set[str], list[str]]:
    """Return normalized executable keys and scalar values below those keys."""
    instruction_keys: set[str] = set()
    instruction_texts: list[str] = []

    def visit(value: Any, inside_instruction: bool = False) -> None:
        if isinstance(value, dict):
            complete_execution = _is_complete_execution_payload(value)
            structured_instruction = complete_execution and not any(
                _is_executable_instruction_key(key) for key in value
            )
            if structured_instruction:
                instruction_keys.add("structured_execution_payload")
            for key, nested_value in value.items():
                normalized_key = key.casefold() if isinstance(key, str) else key
                is_negative_audit = (
                    _compact_key(key) in _NEGATIVE_AUDIT_KEYS
                    and nested_value is False
                )
                is_instruction = (
                    _is_executable_instruction_key(key) and not is_negative_audit
                )
                if is_instruction:
                    instruction_keys.add(normalized_key)
                visit(
                    nested_value,
                    inside_instruction or complete_execution or is_instruction,
                )
        elif isinstance(value, (list, tuple)):
            for nested_value in value:
                visit(nested_value, inside_instruction)
        elif inside_instruction and isinstance(value, (str, int, float, bool)):
            instruction_texts.append(str(value))

    visit(payload)
    return instruction_keys, instruction_texts


def validate_no_executable_instructions(payload: Any, *, context: str) -> None:
    instruction_keys, _instruction_texts = extract_executable_instructions(payload)
    if instruction_keys:
        fields = ", ".join(sorted(instruction_keys))
        raise ValueError(f"{context} contains executable instruction fields: {fields}")
