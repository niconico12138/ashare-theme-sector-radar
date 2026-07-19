"""Intraday timing factor catalog.

The catalog separates factor classification from factor calculation so buy and
exit timing experiments can select factor families without changing realtime
watch plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


TIMING_FACTOR_CATEGORIES = [
    "price_momentum",
    "volume_money_flow",
    "vwap_mean_price",
    "intraday_position",
    "sector_confirmation",
    "relative_strength",
    "risk_reversal",
    "time_structure",
    "execution_liquidity",
    "cashout_risk",
    "sector_continuation",
    "market_environment",
]


@dataclass(frozen=True)
class TimingFactorMetadata:
    factor_id: str
    category: str
    direction: str
    description: str
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


TIMING_FACTOR_REGISTRY: dict[str, TimingFactorMetadata] = {}


def _register(metadata: TimingFactorMetadata) -> None:
    if metadata.category not in TIMING_FACTOR_CATEGORIES:
        raise ValueError(f"unknown timing factor category: {metadata.category}")
    TIMING_FACTOR_REGISTRY[metadata.factor_id] = metadata


_register(
    TimingFactorMetadata(
        factor_id="intraday_momentum",
        category="price_momentum",
        direction="higher_is_better",
        description="Current intraday percentage change converted into a 0-100 momentum score.",
        tags=["buy_timing", "paper_only", "no_execution_signal"],
    )
)
_register(
    TimingFactorMetadata(
        factor_id="amount_strength",
        category="volume_money_flow",
        direction="higher_is_better",
        description="Realtime traded amount versus a configurable reference amount.",
        tags=["buy_timing", "paper_only", "no_execution_signal"],
    )
)
_register(
    TimingFactorMetadata(
        factor_id="sector_confirmation",
        category="sector_confirmation",
        direction="higher_is_better",
        description="Sector validity and intraday breadth confirmation for a candidate.",
        tags=["buy_timing", "paper_only", "no_execution_signal"],
    )
)
_register(
    TimingFactorMetadata(
        factor_id="vwap_position",
        category="vwap_mean_price",
        direction="higher_is_better",
        description="Current price position relative to intraday VWAP or mean transaction cost.",
        tags=["buy_timing", "paper_only", "no_execution_signal"],
    )
)
_register(
    TimingFactorMetadata(
        factor_id="anti_chasing",
        category="risk_reversal",
        direction="higher_is_better",
        description="Penalty-aware score that declines when price is extended near the intraday high.",
        tags=["buy_timing", "paper_only", "no_execution_signal"],
    )
)


def list_timing_factor_categories() -> list[str]:
    return list(TIMING_FACTOR_CATEGORIES)


def get_timing_factor_metadata(factor_id: str) -> TimingFactorMetadata | None:
    return TIMING_FACTOR_REGISTRY.get(factor_id)
