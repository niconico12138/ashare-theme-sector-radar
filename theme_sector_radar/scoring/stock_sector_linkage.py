"""Paper-only stock-to-sector linkage research contracts and scoring."""

from __future__ import annotations

import hashlib
import json
import copy
import math
from datetime import date
from typing import Any, Mapping, Sequence


LINKAGE_V2_WEIGHTS = {
    "return_comovement_20d": 0.40,
    "relative_strength_5d_10d": 0.20,
    "constituent_weight": 0.15,
    "fund_flow_alignment": 0.15,
    "data_quality": 0.10,
}
MINIMUM_AVAILABLE_WEIGHT = 0.50


def legacy_linkage_policy_contract() -> dict[str, Any]:
    """Return the immutable legacy baseline used by Path A."""
    policy = {
        "schema_version": "stock_sector_linkage_legacy_policy.v1",
        "mode": "paper_shadow_research_only",
        "formula": {
            "constituent_weight": 0.20,
            "same_day_sector_rank": 0.40,
            "fund_flow_alignment": 0.40,
        },
        "minimum_relevance": 0.60,
        "trend_sector_top_n": 5,
        "burst_sector_top_n": 5,
        "status": "frozen_baseline",
    }
    canonical = json.dumps(
        policy, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return {**policy, "policy_sha256": hashlib.sha256(canonical).hexdigest()}


def effective_legacy_linkage_policy_contract(
    *,
    trend_top_n: int,
    burst_top_n: int,
    minimum_relevance: float,
) -> dict[str, Any]:
    """Bind the legacy formula to the parameters executed by this run."""
    policy = {
        "schema_version": "stock_sector_linkage_effective_policy.v1",
        "mode": "paper_shadow_research_only",
        "formula": {
            "constituent_weight": 0.20,
            "same_day_sector_rank": 0.40,
            "fund_flow_alignment": 0.40,
        },
        "minimum_relevance": _unit_interval(
            minimum_relevance, field="minimum_relevance"
        ),
        "trend_sector_top_n": int(trend_top_n),
        "burst_sector_top_n": int(burst_top_n),
    }
    if policy["trend_sector_top_n"] <= 0 or policy["burst_sector_top_n"] <= 0:
        raise ValueError("legacy Top-N parameters must be positive")
    frozen = legacy_linkage_policy_contract()
    policy["matches_frozen_baseline"] = all(
        policy[key] == frozen[key]
        for key in (
            "formula",
            "minimum_relevance",
            "trend_sector_top_n",
            "burst_sector_top_n",
        )
    )
    canonical = json.dumps(
        policy, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return {**policy, "policy_sha256": hashlib.sha256(canonical).hexdigest()}


def _finite(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _unit_interval(value: Any, *, field: str) -> float:
    number = _finite(value, field=field)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be within [0, 1]")
    return number


def _aligned_returns(
    stock_returns: Mapping[str, Any] | None,
    sector_returns: Mapping[str, Any] | None,
) -> tuple[list[float], list[float]]:
    if stock_returns is None or sector_returns is None:
        return [], []
    common_dates = sorted(set(stock_returns) & set(sector_returns))[-20:]
    stock_values = [
        _finite(stock_returns[day], field=f"stock_returns[{day}]")
        for day in common_dates
    ]
    sector_values = [
        _finite(sector_returns[day], field=f"sector_returns[{day}]")
        for day in common_dates
    ]
    return stock_values, sector_values


def _correlation_score(stock_values: Sequence[float], sector_values: Sequence[float]) -> float | None:
    if len(stock_values) < 12 or len(stock_values) != len(sector_values):
        return None
    stock_mean = sum(stock_values) / len(stock_values)
    sector_mean = sum(sector_values) / len(sector_values)
    stock_centered = [value - stock_mean for value in stock_values]
    sector_centered = [value - sector_mean for value in sector_values]
    denominator = math.sqrt(
        sum(value * value for value in stock_centered)
        * sum(value * value for value in sector_centered)
    )
    if denominator == 0.0:
        return None
    correlation = sum(
        stock * sector
        for stock, sector in zip(stock_centered, sector_centered)
    ) / denominator
    return max(0.0, min(1.0, (correlation + 1.0) / 2.0))


def returns_by_date_from_bars(
    bars: Sequence[Mapping[str, Any]], *, as_of_date: str
) -> dict[str, float]:
    """Build strict close-to-close percentage returns through one as-of date."""
    cutoff = date.fromisoformat(as_of_date)
    dated = []
    seen = set()
    for bar in bars:
        if not isinstance(bar, Mapping):
            raise ValueError("stock bar must be an object")
        raw_date = str(bar.get("date") or bar.get("trade_date") or "")
        parsed = date.fromisoformat(raw_date)
        if parsed.isoformat() != raw_date:
            raise ValueError("stock bar date must be canonical ISO")
        if parsed > cutoff:
            continue
        if raw_date in seen:
            raise ValueError("stock bar dates must be unique")
        seen.add(raw_date)
        close = _finite(bar.get("close"), field="stock bar close")
        if close <= 0:
            raise ValueError("stock bar close must be positive")
        dated.append((raw_date, close))
    dated.sort(key=lambda item: item[0])
    if dated and dated[-1][0] != cutoff.isoformat():
        raise ValueError("latest stock bar must equal as_of_date")
    return {
        current_date: (current_close / previous_close - 1.0) * 100.0
        for (_previous_date, previous_close), (current_date, current_close)
        in zip(dated, dated[1:])
    }


def relative_strength_score_from_returns(
    stock_returns: Mapping[str, Any] | None,
    sector_returns: Mapping[str, Any] | None,
) -> float | None:
    """Map average 5/10-day excess return from [-10%, +10%] into [0, 1]."""
    if stock_returns is None or sector_returns is None:
        return None
    common_dates = sorted(set(stock_returns) & set(sector_returns))
    window_scores = []
    for window in (5, 10):
        if len(common_dates) < window:
            continue
        dates = common_dates[-window:]
        stock_wealth = 1.0
        sector_wealth = 1.0
        for day in dates:
            stock_return = _finite(
                stock_returns[day], field=f"stock_returns[{day}]"
            )
            sector_return = _finite(
                sector_returns[day], field=f"sector_returns[{day}]"
            )
            stock_wealth *= 1.0 + stock_return / 100.0
            sector_wealth *= 1.0 + sector_return / 100.0
        excess_return = (stock_wealth - sector_wealth) * 100.0
        window_scores.append(max(0.0, min(1.0, (excess_return + 10.0) / 20.0)))
    if not window_scores:
        return None
    return sum(window_scores) / len(window_scores)


def calculate_stock_sector_linkage_v2_shadow(
    *,
    stock_returns: Mapping[str, Any] | None = None,
    sector_returns: Mapping[str, Any] | None = None,
    relative_strength_score: float | None = None,
    constituent_weight_score: float | None = None,
    fund_flow_alignment_score: float | None = None,
    data_quality_score: float | None = None,
) -> dict[str, Any]:
    """Calculate linkage V2 without rewarding unavailable factors.

    Available factors are reweighted to sum to one. A score remains unavailable
    until at least half of the configured evidence weight is present.
    """
    stock_values, sector_values = _aligned_returns(stock_returns, sector_returns)
    components: dict[str, dict[str, Any]] = {}

    correlation_score = _correlation_score(stock_values, sector_values)
    raw_values = {
        "return_comovement_20d": correlation_score,
        "relative_strength_5d_10d": relative_strength_score,
        "constituent_weight": constituent_weight_score,
        "fund_flow_alignment": fund_flow_alignment_score,
        "data_quality": data_quality_score,
    }
    available_weight = 0.0
    weighted_total = 0.0
    for name, configured_weight in LINKAGE_V2_WEIGHTS.items():
        raw_value = raw_values[name]
        if raw_value is None:
            components[name] = {
                "status": "unavailable",
                "score": None,
                "configured_weight": configured_weight,
                "effective_weight": 0.0,
            }
            continue
        score = _unit_interval(raw_value, field=name)
        available_weight += configured_weight
        weighted_total += configured_weight * score
        components[name] = {
            "status": "ok",
            "score": round(score, 6),
            "configured_weight": configured_weight,
            "effective_weight": None,
        }

    status = "unavailable"
    score = None
    if available_weight >= MINIMUM_AVAILABLE_WEIGHT:
        score = round(weighted_total / available_weight, 6)
        status = "ok" if math.isclose(available_weight, 1.0) else "partial"
        for component in components.values():
            if component["status"] == "ok":
                component["effective_weight"] = round(
                    component["configured_weight"] / available_weight, 6
                )

    return {
        "schema_version": "stock_sector_linkage_v2_shadow.v1",
        "mode": "paper_shadow_research_only",
        "status": status,
        "score": score,
        "available_weight": round(available_weight, 6),
        "minimum_available_weight": MINIMUM_AVAILABLE_WEIGHT,
        "aligned_return_days": len(stock_values),
        "components": components,
        "disclaimer": "No broker connection and no live order instruction.",
    }


def build_constituent_linkage_input_contract(
    stocks: Sequence[Mapping[str, Any]],
    *,
    as_of_date: str,
    sector_name: str,
    sector_type: str,
    constituent_source: str,
    sector_flow_status: str,
) -> dict[str, Any]:
    """Preserve complete pre-filter linkage inputs with explicit availability."""
    copied = [copy.deepcopy(dict(stock)) for stock in stocks]
    positive_weights = []
    for stock in copied:
        raw_weight = stock.get("weight")
        if isinstance(raw_weight, (int, float)) and not isinstance(raw_weight, bool):
            number = _finite(raw_weight, field="weight")
            if number > 0:
                positive_weights.append(number)
    weight_signal_status = "unavailable"
    if positive_weights:
        weight_signal_status = (
            "ok" if len(set(positive_weights)) > 1 else "constant_uninformative"
        )

    rows = []
    for stock in copied:
        code = str(stock.get("code") or "").strip()
        if not code:
            raise ValueError("constituent code is required")
        row = {
            "code": code,
            "name": str(stock.get("name") or "").strip(),
            "weight": stock.get("weight"),
            "weight_normalized": stock.get("weight_normalized"),
            "weight_signal_available": weight_signal_status == "ok",
            "quote_available": bool(stock.get("quote_available")),
            "change_pct": stock.get("change_pct"),
            "individual_flow_available": bool(
                stock.get("individual_flow_available")
            ),
            "individual_flow_direction": stock.get(
                "individual_flow_direction", "neutral"
            ),
            "legacy_relevance_score": stock.get("relevance_score"),
            "legacy_relevance_breakdown": copy.deepcopy(
                stock.get("relevance_breakdown")
            ),
        }
        rows.append(row)

    return {
        "schema_version": "stock_sector_linkage_input.v1",
        "mode": "paper_shadow_research_only",
        "as_of_date": as_of_date,
        "sector_name": sector_name,
        "sector_type": sector_type,
        "constituent_source": constituent_source,
        "sector_flow_status": sector_flow_status,
        "weight_signal_status": weight_signal_status,
        "raw_constituent_count": len(rows),
        "quote_available_count": sum(row["quote_available"] for row in rows),
        "individual_flow_available_count": sum(
            row["individual_flow_available"] for row in rows
        ),
        "rows": rows,
        "disclaimer": "No broker connection and no live order instruction.",
    }


def select_direction_linkage_v2_shadow_stocks(
    stocks: Sequence[Mapping[str, Any]],
    *,
    core_sector_quota: int = 10,
    supplemental_sector_quota: int = 5,
    stock_limit: int = 30,
    maximum_cluster_ratio: float = 0.40,
    sector_cluster_map: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Apply sector and optional cluster quotas to linkage V2 candidates."""
    if core_sector_quota <= 0 or supplemental_sector_quota <= 0 or stock_limit <= 0:
        raise ValueError("direction linkage quotas must be positive")
    cluster_ratio = _unit_interval(
        maximum_cluster_ratio, field="maximum_cluster_ratio"
    )
    clusters = dict(sector_cluster_map or {})
    unmapped_sectors: set[str] = set()
    by_sector: dict[str, list[dict[str, Any]]] = {}
    rejected = {
        "linkage_unavailable": 0,
        "sector_quota": 0,
        "duplicate_stock_relation": 0,
        "cluster_quota": 0,
        "stock_limit": 0,
    }
    for source in stocks:
        item = copy.deepcopy(dict(source))
        linkage = item.get("linkage_v2_shadow")
        if not isinstance(linkage, Mapping) or linkage.get("status") not in {
            "ok",
            "partial",
        } or linkage.get("score") is None:
            rejected["linkage_unavailable"] += 1
            continue
        linkage_score = _unit_interval(
            linkage.get("score"), field="linkage_v2_shadow.score"
        )
        sector_name = str(item.get("sector_name") or "").strip()
        if not sector_name:
            raise ValueError("direction linkage candidate sector_name is required")
        tier = str(item.get("candidate_tier") or "")
        if tier not in {"core", "supplemental"}:
            raise ValueError("direction linkage candidate tier is invalid")
        item["linkage_selection_score"] = round(
            0.70 * linkage_score * 100.0
            + 0.30 * _finite(item.get("quant_score", 0.0), field="quant_score"),
            6,
        )
        cluster = str(clusters.get(sector_name) or "").strip()
        if not cluster:
            cluster = "__unmapped__"
            unmapped_sectors.add(sector_name)
        item["sector_cluster"] = cluster
        by_sector.setdefault(sector_name, []).append(item)

    quota_selected = []
    for sector_name in sorted(by_sector):
        sector_rows = sorted(
            by_sector[sector_name],
            key=lambda row: (
                -row["linkage_selection_score"],
                str(row.get("code") or ""),
            ),
        )
        tier = sector_rows[0]["candidate_tier"]
        quota = core_sector_quota if tier == "core" else supplemental_sector_quota
        quota_selected.extend(sector_rows[:quota])
        rejected["sector_quota"] += max(0, len(sector_rows) - quota)

    quota_selected.sort(
        key=lambda row: (
            -row["linkage_selection_score"],
            str(row.get("code") or ""),
        )
    )
    unique_quota_selected = []
    seen_codes = set()
    for row in quota_selected:
        code = str(row.get("code") or "").strip()
        if code and code not in seen_codes:
            unique_quota_selected.append(row)
            seen_codes.add(code)
        else:
            rejected["duplicate_stock_relation"] += 1

    cluster_availability: dict[str, int] = {}
    for row in unique_quota_selected:
        cluster = row["sector_cluster"]
        cluster_availability[cluster] = cluster_availability.get(cluster, 0) + 1

    selection_target = 0
    cluster_cap = 0
    maximum_target = min(stock_limit, len(unique_quota_selected))
    for target in range(maximum_target, 0, -1):
        candidate_cap = int(math.floor(target * cluster_ratio))
        if candidate_cap <= 0:
            continue
        capacity = sum(
            min(available, candidate_cap)
            for available in cluster_availability.values()
        )
        if capacity >= target:
            selection_target = target
            cluster_cap = candidate_cap
            break

    selected = []
    cluster_counts: dict[str, int] = {}
    if selection_target:
        for row in unique_quota_selected:
            if len(selected) >= selection_target:
                rejected["stock_limit"] += 1
                continue
            cluster = row["sector_cluster"]
            if cluster_counts.get(cluster, 0) >= cluster_cap:
                rejected["cluster_quota"] += 1
                continue
            selected.append(row)
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
    else:
        rejected["cluster_quota"] += len(unique_quota_selected)
    for rank, row in enumerate(selected, 1):
        row["linkage_selection_rank"] = rank

    return {
        "schema_version": "direction_linkage_v2_selection_shadow.v1",
        "mode": "paper_shadow_research_only",
        "policy": {
            "core_sector_quota": core_sector_quota,
            "supplemental_sector_quota": supplemental_sector_quota,
            "stock_limit": stock_limit,
            "maximum_cluster_ratio": cluster_ratio,
            "cluster_cap": cluster_cap,
            "cluster_basis": (
                "explicit_map" if clusters else "unmapped_fail_closed"
            ),
            "ranking_weights": {"linkage_v2": 0.70, "quant_score": 0.30},
        },
        "selected_count": len(selected),
        "rejected_counts": rejected,
        "cluster_counts": dict(sorted(cluster_counts.items())),
        "unmapped_sectors": sorted(unmapped_sectors),
        "cluster_mapping_coverage": (
            (len(by_sector) - len(unmapped_sectors)) / len(by_sector)
            if by_sector
            else 0.0
        ),
        "actual_max_cluster_ratio": (
            max(cluster_counts.values()) / len(selected) if selected else 0.0
        ),
        "selected": selected,
        "disclaimer": "No broker connection and no live order instruction.",
    }


def build_formal_candidate_selection(
    *,
    direction_source: Mapping[str, Any],
    linkage_selection: Mapping[str, Any],
) -> dict[str, Any]:
    """Activate the verified direction + Linkage V2 candidate chain for research.

    This wrapper changes the active candidate source only. It deliberately does
    not recalculate or overwrite any protected stock score. The underlying
    inputs keep their ``shadow`` names so provenance remains explicit.
    """

    result: dict[str, Any] = {
        "schema_version": "formal_candidate_selection.v1",
        "mode": "paper_shadow_research_only",
        "candidate_chain": "direction_score_then_linkage_v2",
        "status": "unavailable",
        "fallback_used": False,
        "direction_source": {},
        "linkage_source": {},
        "selected_count": 0,
        "selected": [],
        "error": None,
        "disclaimer": "No broker connection and no live order instruction.",
    }

    if not isinstance(direction_source, Mapping):
        result["error"] = "direction source must be an object"
        return result
    result["direction_source"] = {
        key: direction_source.get(key)
        for key in ("status", "mode", "path", "sha256")
    }
    if direction_source.get("status") != "ok":
        result["error"] = "direction source is not verified"
        return result
    if direction_source.get("mode") != "paper_shadow_research_only":
        result["error"] = "direction source mode is not paper-only"
        return result

    if not isinstance(linkage_selection, Mapping):
        result["error"] = "Linkage V2 selection must be an object"
        return result
    result["linkage_source"] = {
        key: linkage_selection.get(key)
        for key in ("schema_version", "mode", "selected_count")
    }
    if linkage_selection.get("schema_version") != (
        "direction_linkage_v2_selection_shadow.v1"
    ):
        result["error"] = "Linkage V2 selection schema_version mismatch"
        return result
    if linkage_selection.get("mode") != "paper_shadow_research_only":
        result["error"] = "Linkage V2 selection mode is not paper-only"
        return result

    selected = linkage_selection.get("selected")
    if not isinstance(selected, list) or not selected:
        result["error"] = "Linkage V2 selection has no selected rows"
        return result
    declared_count = linkage_selection.get("selected_count")
    if declared_count is not None and declared_count != len(selected):
        result["error"] = "Linkage V2 selected_count mismatch"
        return result

    normalized: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for rank, source in enumerate(selected, 1):
        if not isinstance(source, Mapping):
            raise ValueError("formal candidate row must be an object")
        item = copy.deepcopy(dict(source))
        code = str(item.get("code") or "").strip()
        if not code or code in seen_codes:
            raise ValueError("formal candidate stock identity is invalid")
        seen_codes.add(code)

        direction_score = item.get("sector_direction_score")
        if direction_score is None:
            direction_score = item.get("direction_score_shadow")
        if direction_score is None:
            raise ValueError("formal candidate direction score is required")
        direction_score = _finite(
            direction_score, field="formal candidate direction score"
        )
        if not 0.0 <= direction_score <= 100.0:
            raise ValueError("formal candidate direction score must be within [0, 100]")

        linkage = item.get("linkage_v2_shadow")
        if not isinstance(linkage, Mapping):
            raise ValueError("formal candidate Linkage V2 result is required")
        if linkage.get("status") not in {"ok", "partial"}:
            raise ValueError("formal candidate Linkage V2 result is unavailable")
        _unit_interval(linkage.get("score"), field="formal candidate Linkage V2 score")

        item["formal_candidate_rank"] = rank
        item["formal_candidate_source"] = (
            "direction_score_shadow+linkage_v2_shadow"
        )
        normalized.append(item)

    result.update(
        {
            "status": "active_for_paper_research",
            "selected_count": len(normalized),
            "selected": normalized,
        }
    )
    return result
