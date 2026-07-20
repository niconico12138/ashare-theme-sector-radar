"""Independent paper-only market anomaly detector."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Any, Mapping, Sequence

from .risk_event_schema import build_risk_event, canonical_sha256


DETECTOR_ID = "market_anomaly_detector"
DETECTOR_VERSION = "market-anomaly-v1"


@dataclass(frozen=True)
class MarketAnomalyThresholds:
    limit_down_return: float = -0.095
    near_limit_down_return: float = -0.08
    gap_abs_threshold: float = 0.07
    volume_ratio_threshold: float = 3.0
    volume_z_threshold: float = 3.0
    correlation_floor: float = 0.30
    correlation_break_delta: float = 0.50
    volume_window: int = 20
    correlation_window: int = 20


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 3:
        return None
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_scale = sum((value - left_mean) ** 2 for value in left) ** 0.5
    right_scale = sum((value - right_mean) ** 2 for value in right) ** 0.5
    if left_scale == 0 or right_scale == 0:
        return None
    return numerator / (left_scale * right_scale)


def _source(observation: Mapping[str, Any]) -> dict[str, Any]:
    value = observation.get("source")
    if isinstance(value, Mapping) and value.get("source_id"):
        return dict(value)
    return {
        "source_id": "market_observation_fixture",
        "authority_tier": "research_only",
        "source_kind": "market_data",
    }


def _common(
    observation: Mapping[str, Any], thresholds: MarketAnomalyThresholds, mode: str
) -> dict[str, Any]:
    return {
        "scope": str(observation.get("scope") or "individual"),
        "entity_id": str(
            observation.get("entity_id")
            or observation.get("stock_code")
            or "unknown"
        ),
        "event_time": observation.get("event_time") or observation.get("as_of_date"),
        "published_at": None,
        "effective_from": str(observation.get("as_of_date") or ""),
        "as_of_date": str(observation.get("as_of_date") or ""),
        "observed_at": observation.get("observed_at"),
        "source": _source(observation),
        "evidence_refs": observation.get("evidence_refs") or [],
        "detector": {
            "detector_id": DETECTOR_ID,
            "detector_version": DETECTOR_VERSION,
            "mode": mode,
            "window": {
                "volume": thresholds.volume_window,
                "correlation": thresholds.correlation_window,
            },
        },
        "provider": None,
    }


def _blocked(
    observation: Mapping[str, Any],
    thresholds: MarketAnomalyThresholds,
    *,
    event_type: str,
    missing_fields: Sequence[str],
    status: str = "blocked",
) -> dict[str, Any]:
    return build_risk_event(
        event_type=event_type,
        severity="unknown",
        status=status,
        structured_fields={
            "reason": "missing_or_untrusted_market_inputs",
            "missing_fields": sorted(missing_fields),
            "data_quality": str(observation.get("data_quality") or "unknown"),
        },
        provenance={
            "input_sha256": canonical_sha256(dict(observation)),
            "method": "blocked_market_anomaly_evaluation",
        },
        **_common(observation, thresholds, "deterministic"),
    )


def _volume_baseline(
    observation: Mapping[str, Any], thresholds: MarketAnomalyThresholds
) -> tuple[float | None, float | None]:
    ratio = _number(observation.get("volume_ratio"))
    z_value = _number(observation.get("volume_z"))
    current = _number(observation.get("current_volume"))
    history = observation.get("historical_volumes")
    if not isinstance(history, Sequence) or isinstance(history, (str, bytes)):
        return ratio, z_value
    values = [_number(value) for value in history[-thresholds.volume_window :]]
    if any(value is None for value in values) or not values or current is None:
        return ratio, z_value
    complete = [float(value) for value in values if value is not None]
    baseline = mean(complete)
    ratio = current / baseline if baseline > 0 else None
    deviation = pstdev(complete)
    z_value = (current - baseline) / deviation if deviation > 0 else None
    return ratio, z_value


def _correlation_baseline(
    observation: Mapping[str, Any], thresholds: MarketAnomalyThresholds
) -> tuple[float | None, float | None]:
    current = _number(observation.get("rolling_correlation"))
    baseline = _number(observation.get("correlation_baseline"))
    stock = observation.get("stock_return_history")
    sector = observation.get("sector_return_history")
    if current is None and isinstance(stock, Sequence) and isinstance(sector, Sequence):
        left = [_number(value) for value in stock[-thresholds.correlation_window :]]
        right = [_number(value) for value in sector[-thresholds.correlation_window :]]
        if not any(value is None for value in [*left, *right]):
            current = _pearson(
                [float(value) for value in left if value is not None],
                [float(value) for value in right if value is not None],
            )
    return current, baseline


def detect_market_anomalies(
    observation: Mapping[str, Any],
    *,
    thresholds: MarketAnomalyThresholds | None = None,
) -> list[dict[str, Any]]:
    thresholds = thresholds or MarketAnomalyThresholds()
    if not observation.get("as_of_date") or observation.get("observed_at") is None:
        raise ValueError("market observation requires as_of_date and observed_at")
    quality = str(observation.get("data_quality") or "unknown")
    if quality not in {"complete", "partial", "unknown", "blocked"}:
        raise ValueError("market observation data_quality is invalid")
    if quality in {"unknown", "blocked"}:
        return [
            _blocked(
                observation,
                thresholds,
                event_type="market_data_quality",
                missing_fields=["trusted_market_data"],
                status="unknown" if quality == "unknown" else "blocked",
            )
        ]
    output: list[dict[str, Any]] = []
    return_pct = _number(observation.get("return_pct"))
    limit_down = observation.get("limit_down")
    if return_pct is None and not isinstance(limit_down, bool):
        output.append(
            _blocked(
                observation,
                thresholds,
                event_type="limit_down",
                missing_fields=["return_pct", "limit_down"],
            )
        )
    elif limit_down is True or (
        return_pct is not None and return_pct <= thresholds.limit_down_return
    ):
        output.append(
            build_risk_event(
                event_type="limit_down",
                severity="high",
                status="observed",
                structured_fields={
                    "return_pct": return_pct,
                    "threshold_return_pct": thresholds.limit_down_return,
                },
                provenance={"method": "deterministic_limit_down_threshold"},
                **_common(observation, thresholds, "deterministic"),
            )
        )
    elif return_pct is not None and return_pct <= thresholds.near_limit_down_return:
        output.append(
            build_risk_event(
                event_type="near_limit_down",
                severity="elevated",
                status="observed",
                structured_fields={
                    "return_pct": return_pct,
                    "threshold_return_pct": thresholds.near_limit_down_return,
                },
                provenance={"method": "deterministic_near_limit_down_threshold"},
                **_common(observation, thresholds, "deterministic"),
            )
        )

    gap_pct = _number(observation.get("gap_pct"))
    if gap_pct is None:
        output.append(
            _blocked(
                observation,
                thresholds,
                event_type="large_gap",
                missing_fields=["gap_pct"],
            )
        )
    elif abs(gap_pct) >= thresholds.gap_abs_threshold:
        output.append(
            build_risk_event(
                event_type="large_gap",
                severity="elevated",
                status="observed",
                structured_fields={
                    "gap_pct": gap_pct,
                    "absolute_threshold": thresholds.gap_abs_threshold,
                },
                provenance={"method": "deterministic_gap_threshold"},
                **_common(observation, thresholds, "deterministic"),
            )
        )

    volume_ratio, volume_z = _volume_baseline(observation, thresholds)
    if volume_ratio is None and volume_z is None:
        output.append(
            _blocked(
                observation,
                thresholds,
                event_type="abnormal_volume",
                missing_fields=["volume_ratio_or_history"],
            )
        )
    elif (
        volume_ratio is not None
        and volume_ratio >= thresholds.volume_ratio_threshold
    ) or (volume_z is not None and volume_z >= thresholds.volume_z_threshold):
        output.append(
            build_risk_event(
                event_type="abnormal_volume",
                severity="elevated",
                status="observed",
                structured_fields={
                    "volume_ratio": volume_ratio,
                    "volume_z": volume_z,
                    "volume_ratio_threshold": thresholds.volume_ratio_threshold,
                    "volume_z_threshold": thresholds.volume_z_threshold,
                    "baseline_window": thresholds.volume_window,
                },
                provenance={"method": "historical_volume_baseline"},
                **_common(observation, thresholds, "statistical"),
            )
        )

    correlation, baseline = _correlation_baseline(observation, thresholds)
    sector_id = str(observation.get("sector_id") or "")
    if correlation is None or not sector_id:
        output.append(
            _blocked(
                observation,
                thresholds,
                event_type="sector_correlation_break",
                missing_fields=[
                    field
                    for field, missing in (
                        ("correlation_or_return_history", correlation is None),
                        ("sector_id", not sector_id),
                    )
                    if missing
                ],
            )
        )
    elif correlation <= thresholds.correlation_floor or (
        baseline is not None
        and baseline - correlation >= thresholds.correlation_break_delta
    ):
        output.append(
            build_risk_event(
                event_type="sector_correlation_break",
                severity="high",
                status="observed",
                structured_fields={
                    "sector_id": sector_id,
                    "rolling_correlation": correlation,
                    "historical_correlation": baseline,
                    "correlation_floor": thresholds.correlation_floor,
                    "break_delta": thresholds.correlation_break_delta,
                    "baseline_window": thresholds.correlation_window,
                },
                provenance={"method": "historical_correlation_baseline"},
                **_common(observation, thresholds, "statistical"),
            )
        )
    return output

