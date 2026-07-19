"""Shared paper-only output contract helpers for reporting tests."""

FORBIDDEN_WORDS = (
    "buy", "sell", "hold",
    "买入", "卖出", "持有", "推荐",
    "建仓", "加仓", "减仓",
    "止盈", "止损", "目标价",
)

from theme_sector_radar.reporting.paper_only_contract import (
    EXECUTABLE_INSTRUCTION_KEYS,
    extract_executable_instructions,
)
