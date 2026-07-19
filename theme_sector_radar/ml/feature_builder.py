"""Build strictly as-of features for the independent ML shadow ranker."""

from __future__ import annotations

from datetime import date, datetime
import math
from statistics import pstdev
from typing import Any, Mapping, Sequence

from .schema import (
    FEATURE_SCHEMA_VERSION,
    FUTURE_OR_LABEL_FIELD_NAMES,
    FUTURE_OR_LABEL_FIELD_PREFIXES,
    V1_FEATURE_NAMES,
    feature_schema_sha256,
)


def _canonical_date(value: Any, *, field: str) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date: {text!r}") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{field} must be a canonical ISO date: {text!r}")
    return text


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def _candidate_number(candidate: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _finite(candidate.get(key))
        if value is not None:
            return value
    return None


def _returns(closes: Sequence[float]) -> list[float]:
    return [
        closes[index] / closes[index - 1] - 1.0
        for index in range(1, len(closes))
        if closes[index - 1] > 0
    ]


def _momentum(closes: Sequence[float], horizon: int) -> float:
    if len(closes) <= horizon or closes[-horizon - 1] <= 0:
        return 0.0
    return closes[-1] / closes[-horizon - 1] - 1.0


def _ma_distance(closes: Sequence[float], window: int) -> float:
    if len(closes) < window:
        return 0.0
    mean = sum(closes[-window:]) / window
    return closes[-1] / mean - 1.0 if mean > 0 else 0.0


def _volatility(closes: Sequence[float], window: int) -> float:
    values = _returns(closes[-(window + 1) :])
    return pstdev(values) if len(values) >= 2 else 0.0


def _max_drawdown(closes: Sequence[float], window: int) -> float:
    values = closes[-window:]
    peak = 0.0
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return abs(worst)


def _linkage(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    value = candidate.get("linkage_v2")
    if not isinstance(value, Mapping):
        value = candidate.get("linkage_v2_shadow")
    if not isinstance(value, Mapping):
        value = candidate.get("linkage_v2_breakdown")
    return value if isinstance(value, Mapping) else {}


def _linkage_component(
    linkage: Mapping[str, Any],
    flat_name: str,
    component_name: str,
    *,
    feature_input_name: str | None = None,
) -> float | None:
    """Read either the persisted flat contract or production components."""
    feature_inputs = linkage.get("feature_inputs")
    if feature_input_name and isinstance(feature_inputs, Mapping):
        value = _finite(feature_inputs.get(feature_input_name))
        if value is not None:
            return value
    flat = _finite(linkage.get(flat_name))
    if flat is not None:
        return flat
    components = linkage.get("components")
    if not isinstance(components, Mapping):
        return None
    component = components.get(component_name)
    if not isinstance(component, Mapping) or component.get("status") != "ok":
        return None
    return _finite(component.get("score"))


def _reject_future_or_label_fields(value: Any, *, path: str = "candidate") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if key in FUTURE_OR_LABEL_FIELD_NAMES or key.startswith(
                FUTURE_OR_LABEL_FIELD_PREFIXES
            ):
                raise ValueError(f"forbidden future/label field at {path}.{raw_key}")
            _reject_future_or_label_fields(child, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_future_or_label_fields(child, path=f"{path}[{index}]")


def build_feature_row(
    candidate: Mapping[str, Any],
    bars: Sequence[Mapping[str, Any]],
    *,
    as_of_date: str,
) -> dict[str, Any]:
    """Return one ordered, finite feature row using data at or before ``as_of``."""

    _reject_future_or_label_fields(candidate)
    as_of = _canonical_date(as_of_date, field="as_of_date")
    code = str(candidate.get("code") or candidate.get("stock_code") or "").zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"stock code must contain six digits: {code!r}")

    normalized_bars: list[tuple[str, Mapping[str, Any]]] = []
    seen_dates: set[str] = set()
    for bar in bars:
        bar_date = _canonical_date(bar.get("date"), field="bar.date")
        if bar_date > as_of:
            continue
        if bar_date in seen_dates:
            raise ValueError(f"duplicate bar date for {code}: {bar_date}")
        close = _finite(bar.get("close"))
        if close is None or close <= 0:
            raise ValueError(f"bar close must be finite and positive for {code} on {bar_date}")
        seen_dates.add(bar_date)
        normalized_bars.append((bar_date, bar))
    normalized_bars.sort(key=lambda item: item[0])
    if len(normalized_bars) < 5:
        raise ValueError(f"at least 5 as-of bars are required for {code}")
    if normalized_bars[-1][0] != as_of:
        raise ValueError(
            f"latest bar must equal as_of_date for {code}: "
            f"{normalized_bars[-1][0]} != {as_of}"
        )

    closes = [float(item[1]["close"]) for item in normalized_bars]
    volumes = [_finite(item[1].get("volume")) or 0.0 for item in normalized_bars]
    amounts = [_finite(item[1].get("amount")) or 0.0 for item in normalized_bars]
    volume_5 = sum(volumes[-5:]) / min(5, len(volumes))
    volume_20 = sum(volumes[-20:]) / min(20, len(volumes))
    valid_amounts = [value for value in amounts[-5:] if value > 0]

    pe = _candidate_number(candidate, "pe")
    pb = _candidate_number(candidate, "pb")
    market_cap = _candidate_number(candidate, "total_mv", "market_cap")
    pe_relative = _candidate_number(candidate, "pe_sector_relative")
    pb_relative = _candidate_number(candidate, "pb_sector_relative")
    market_cap_percentile = _candidate_number(candidate, "market_cap_sector_percentile")
    trend = _candidate_number(candidate, "sector_trend_score")
    burst = _candidate_number(candidate, "sector_burst_score")
    direction = _candidate_number(
        candidate, "sector_direction_score", "direction_score_shadow"
    )
    data_quality = _candidate_number(candidate, "data_quality_score")
    factor_coverage = _candidate_number(candidate, "factor_coverage")
    linkage = _linkage(candidate)
    linkage_values = {
        "comovement_20d": _linkage_component(
            linkage, "comovement_20d", "return_comovement_20d"
        ),
        "relative_strength_5d": _linkage_component(
            linkage,
            "relative_strength_5d",
            "relative_strength_5d_10d",
            feature_input_name="relative_strength_5d",
        ),
        "relative_strength_10d": _linkage_component(
            linkage,
            "relative_strength_10d",
            "relative_strength_5d_10d",
            feature_input_name="relative_strength_10d",
        ),
        "weight": _linkage_component(
            linkage, "weight", "constituent_weight"
        ),
        "fund_flow": _linkage_component(
            linkage, "fund_flow", "fund_flow_alignment"
        ),
        "data_quality": _linkage_component(
            linkage, "data_quality", "data_quality"
        ),
    }

    values = {
        "momentum_1d": _momentum(closes, 1),
        "momentum_3d": _momentum(closes, 3),
        "momentum_5d": _momentum(closes, 5),
        "momentum_10d": _momentum(closes, 10),
        "momentum_20d": _momentum(closes, 20),
        "ma5_distance": _ma_distance(closes, 5),
        "ma10_distance": _ma_distance(closes, 10),
        "ma20_distance": _ma_distance(closes, 20),
        "volume_ratio_5_20": volume_5 / volume_20 if volume_20 > 0 else 0.0,
        "log_avg_amount_5d": math.log1p(sum(valid_amounts) / len(valid_amounts)) if valid_amounts else 0.0,
        "volatility_5d": _volatility(closes, 5),
        "volatility_20d": _volatility(closes, 20),
        "max_drawdown_20d": _max_drawdown(closes, 20),
        "pe": pe or 0.0,
        "pb": pb or 0.0,
        "log_market_cap": math.log1p(market_cap) if market_cap is not None and market_cap > 0 else 0.0,
        "pe_sector_relative": pe_relative or 0.0,
        "pb_sector_relative": pb_relative or 0.0,
        "market_cap_sector_percentile": market_cap_percentile or 0.0,
        "sector_trend_score": (trend or 0.0) / 100.0,
        "sector_burst_score": (burst or 0.0) / 100.0,
        "sector_direction_score": (direction or 0.0) / 100.0,
        "linkage_comovement_20d": linkage_values["comovement_20d"] or 0.0,
        "linkage_relative_strength_5d": linkage_values["relative_strength_5d"] or 0.0,
        "linkage_relative_strength_10d": linkage_values["relative_strength_10d"] or 0.0,
        "linkage_weight": linkage_values["weight"] or 0.0,
        "linkage_fund_flow": linkage_values["fund_flow"] or 0.0,
        "linkage_data_quality": linkage_values["data_quality"] or 0.0,
        "data_quality_score": (data_quality or 0.0) / 100.0,
        "factor_coverage": factor_coverage or 0.0,
        "missing_valuation": float(pe is None or pb is None or market_cap is None),
        "missing_sector_context": float(trend is None or burst is None or direction is None),
        "missing_linkage": float(not linkage),
        "missing_amount": float(not valid_amounts),
    }
    ordered = {name: float(values[name]) for name in V1_FEATURE_NAMES}
    if not all(math.isfinite(value) for value in ordered.values()):
        raise ValueError(f"feature row contains non-finite values for {code}")
    recent_volumes = normalized_bars[-20:]
    complete_volume_window = len(recent_volumes) >= 20 and all(
        _finite(bar.get("volume")) is not None for _day, bar in recent_volumes
    )
    availability = {
        "momentum_1d": len(closes) > 1,
        "momentum_3d": len(closes) > 3,
        "momentum_5d": len(closes) > 5,
        "momentum_10d": len(closes) > 10,
        "momentum_20d": len(closes) > 20,
        "ma5_distance": len(closes) >= 5,
        "ma10_distance": len(closes) >= 10,
        "ma20_distance": len(closes) >= 20,
        "volume_ratio_5_20": complete_volume_window and volume_20 > 0,
        "log_avg_amount_5d": len(valid_amounts) == 5,
        "volatility_5d": len(closes) > 5,
        "volatility_20d": len(closes) > 20,
        "max_drawdown_20d": len(closes) >= 20,
        "pe": pe is not None,
        "pb": pb is not None,
        "log_market_cap": market_cap is not None,
        "pe_sector_relative": pe_relative is not None,
        "pb_sector_relative": pb_relative is not None,
        "market_cap_sector_percentile": market_cap_percentile is not None,
        "sector_trend_score": trend is not None,
        "sector_burst_score": burst is not None,
        "sector_direction_score": direction is not None,
        "linkage_comovement_20d": linkage_values["comovement_20d"] is not None,
        "linkage_relative_strength_5d": linkage_values["relative_strength_5d"] is not None,
        "linkage_relative_strength_10d": linkage_values["relative_strength_10d"] is not None,
        "linkage_weight": linkage_values["weight"] is not None,
        "linkage_fund_flow": linkage_values["fund_flow"] is not None,
        "linkage_data_quality": linkage_values["data_quality"] is not None,
        "data_quality_score": data_quality is not None,
        "factor_coverage": factor_coverage is not None,
    }
    observed = sum(availability.values())
    measured = len(availability)
    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "as_of_date": as_of,
        "stock_code": code,
        "sector_name": str(candidate.get("sector_name") or ""),
        "features": ordered,
        "feature_coverage": round(observed / measured, 6) if measured else 0.0,
        "provenance": {
            "latest_bar_date": normalized_bars[-1][0],
            "as_of_bar_count": len(normalized_bars),
            "feature_schema_sha256": feature_schema_sha256(),
            "built_at": datetime.now().astimezone().isoformat(),
        },
    }
