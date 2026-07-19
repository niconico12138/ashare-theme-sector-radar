"""
板块排名 Agent

生成行业 Top N、概念 Top N、共振 Top N。
"""

from collections import Counter
from datetime import date
from math import ceil
from typing import Any, Dict, List, Optional

from ...models import (
    AgentOutput,
    AgentStatus,
    ConceptPhase,
    FocusLevel,
    RiskLevel,
    SectorScore,
    SectorSnapshot,
)
from ...data.return_validation import trusted_daily_returns
from ...scoring.concept_score import calculate_concept_phase, calculate_concept_score_breakdown
from ...scoring.focus_level import calculate_focus_level, explain_downgrade, generate_watch_points
from ...scoring.industry_score import calculate_industry_score_breakdown
from ...scoring.industry_three_layer_shadow import (
    calculate_industry_three_layer_shadow,
)
from ...scoring.industry_direction_candidates import (
    select_industry_direction_candidates,
)
from ...scoring.risk_score import calculate_risk_penalty, calculate_risk_breakdown


def _failed_three_layer_shadow(risk_flags: List[str]) -> Dict[str, Any]:
    unavailable_layer = {"score": None, "status": "unavailable"}
    return {
        "mode": "paper_shadow_research_only",
        "weights": {"time_series": 0.5, "cross_section": 0.3, "rank_momentum": 0.2},
        "time_series": dict(unavailable_layer),
        "cross_section": dict(unavailable_layer),
        "rank_momentum": dict(unavailable_layer),
        "direction_score_shadow": None,
        "direction_state": "unavailable",
        "risk_flags_observed": list(risk_flags),
        "error_status": "calculation_failed",
    }


def _failed_direction_candidate_selection() -> Dict[str, Any]:
    empty_counts = {
        "core_candidates": 0,
        "supplemental_candidates": 0,
        "confirmation_required": 0,
        "observations": 0,
    }
    return {
        "schema_version": "industry_direction_candidate_selection.v1",
        "mode": "paper_shadow_research_only",
        "disclaimer": "No broker connection and no live order instruction.",
        "selection_counts": empty_counts,
        **{key: [] for key in empty_counts},
        "error_status": "calculation_failed",
    }


def generate_sector_ranking(
    industry_sectors: List[SectorSnapshot],
    concept_sectors: List[SectorSnapshot],
    market_temperature: float = 50.0,
    top_n: int = 10,
    industry_history: Optional[Dict[str, Dict[str, Any]]] = None,
) -> AgentOutput:
    """
    生成板块排名

    Args:
        industry_sectors: 行业板块快照列表
        concept_sectors: 概念板块快照列表
        market_temperature: 市场温度
        top_n: Top N 数量

    Returns:
        排名结果 AgentOutput
    """
    industry_scores = []
    concept_scores = []
    warnings = []
    failed_industry_count = 0
    industry_trend_features = _build_industry_trend_features(
        industry_sectors,
        industry_history or {},
    )

    # 计算行业评分
    for sector in industry_sectors:
        try:
            # 计算评分 breakdown
            score_breakdown = calculate_industry_score_breakdown(
                sector,
                market_temperature,
                trend_features=industry_trend_features.get(sector.name),
            )
            positive_score = score_breakdown["positive_score"]

            # 计算风险 breakdown（risk_penalty 为正数）
            risk_breakdown = calculate_risk_breakdown(sector)
            risk_penalty = risk_breakdown["total_penalty"]  # 正数
            risk_level = risk_breakdown["risk_level"]
            risk_flags = risk_breakdown["risk_flags"]
            try:
                three_layer_shadow = calculate_industry_three_layer_shadow(
                    sector,
                    industry_trend_features.get(sector.name),
                    risk_flags=risk_flags,
                )
            except Exception:
                three_layer_shadow = _failed_three_layer_shadow(risk_flags)

            # 计算最终分数: final_score = positive_score - risk_penalty
            final_score = positive_score - risk_penalty

            score = SectorScore(
                sector_id=sector.sector_id,
                name=sector.name,
                type=sector.type,
                score=final_score,
                positive_score=positive_score,
                risk_penalty=risk_penalty,  # 正数
                risk_level=risk_level,
                risk_flags=risk_flags,
                constituents=sector.constituents,
                data_sources=sector.data_sources,
                updated_at=sector.updated_at,
                data_quality_score=sector.data_quality_score,
                turnover=sector.turnover,
                main_net_inflow=sector.main_net_inflow,
                score_breakdown={
                    **score_breakdown,
                    "risk_penalty": round(risk_penalty, 2),  # 正数
                    "final_score": round(final_score, 2),
                    "risk_breakdown": risk_breakdown,
                    "three_layer_shadow": three_layer_shadow,
                },
            )

            # 计算关注等级
            focus_level, downgrade_reasons = calculate_focus_level(
                positive_score=positive_score,
                risk_penalty=risk_penalty,
                risk_level=risk_level,
                data_quality_score=sector.data_quality_score,
            )
            score.focus_level = focus_level
            score.downgrade_reasons = downgrade_reasons

            # 生成观察要点
            score.watch_points = generate_watch_points(
                focus_level=focus_level,
                score_breakdown=score_breakdown,
                risk_breakdown=risk_breakdown,
            )

            industry_scores.append(score)
        except Exception as e:
            failed_industry_count += 1
            warnings.append(f"计算行业 {sector.name} 排名失败: {str(e)}")

    # 计算概念评分
    for sector in concept_sectors:
        try:
            # 计算阶段和评分 breakdown
            phase = calculate_concept_phase(sector)
            score_breakdown = calculate_concept_score_breakdown(sector, phase)
            positive_score = score_breakdown["positive_score"]

            # 计算风险 breakdown（risk_penalty 为正数）
            risk_breakdown = calculate_risk_breakdown(sector)
            risk_penalty = risk_breakdown["total_penalty"]  # 正数
            risk_level = risk_breakdown["risk_level"]
            risk_flags = risk_breakdown["risk_flags"]

            # 计算最终分数: final_score = positive_score - risk_penalty
            final_score = positive_score - risk_penalty

            score = SectorScore(
                sector_id=sector.sector_id,
                name=sector.name,
                type=sector.type,
                score=final_score,
                positive_score=positive_score,
                risk_penalty=risk_penalty,  # 正数
                phase=phase,
                risk_level=risk_level,
                risk_flags=risk_flags,
                constituents=sector.constituents,
                data_sources=sector.data_sources,
                updated_at=sector.updated_at,
                data_quality_score=sector.data_quality_score,
                turnover=sector.turnover,
                main_net_inflow=sector.main_net_inflow,
                score_breakdown={
                    **score_breakdown,
                    "risk_penalty": round(risk_penalty, 2),  # 正数
                    "final_score": round(final_score, 2),
                    "risk_breakdown": risk_breakdown,
                },
            )

            # 计算关注等级
            focus_level, downgrade_reasons = calculate_focus_level(
                positive_score=positive_score,
                risk_penalty=risk_penalty,
                risk_level=risk_level,
                data_quality_score=sector.data_quality_score,
                price_change_available=sector.price_change_available,
            )
            score.focus_level = focus_level
            score.downgrade_reasons = downgrade_reasons

            # 生成观察要点
            score.watch_points = generate_watch_points(
                focus_level=focus_level,
                score_breakdown=score_breakdown,
                risk_breakdown=risk_breakdown,
            )

            concept_scores.append(score)
        except Exception as e:
            warnings.append(f"计算概念 {sector.name} 排名失败: {str(e)}")

    _sort_and_assign_competition_ranks(industry_scores)
    _sort_and_assign_competition_ranks(concept_scores)

    direction_candidate_rows = []
    for score in industry_scores:
        shadow = score.score_breakdown["three_layer_shadow"]
        time_series = shadow.get("time_series") or {}
        direction_candidate_rows.append(
            {
                "sector_id": score.sector_id,
                "sector_name": score.name,
                "direction_score_shadow": shadow.get("direction_score_shadow"),
                "time_series_score": time_series.get("score"),
                "direction_state": shadow.get("direction_state", "unavailable"),
                "risk_flags_observed": list(
                    shadow.get("risk_flags_observed", [])
                ),
                "radar_base_score": round(float(score.positive_score), 2),
                "radar_rank": score.current_rank,
            }
        )
    try:
        direction_candidates_shadow = select_industry_direction_candidates(
            direction_candidate_rows
        )
    except Exception:
        direction_candidates_shadow = _failed_direction_candidate_selection()

    successful_industry_names = {score.name for score in industry_scores}
    trend_history_metadata = {
        "input_score_count": len(industry_sectors),
        "successful_score_count": len(industry_scores),
        "failed_score_count": failed_industry_count,
    }
    trend_history_metadata.update(
        {
            f"effective_{window}d_count": sum(
                window
                in industry_trend_features.get(sector.name, {}).get(
                    "relative_strength_percentiles", {}
                )
                for sector in industry_sectors
                if sector.name in successful_industry_names
            )
            for window in (5, 10, 20)
        }
    )
    shadow_states = Counter(
        score.score_breakdown["three_layer_shadow"]["direction_state"]
        for score in industry_scores
    )
    trend_history_metadata.update(
        {
            "three_layer_shadow_available_count": sum(
                score.score_breakdown["three_layer_shadow"][
                    "direction_score_shadow"
                ]
                is not None
                for score in industry_scores
            ),
            "three_layer_shadow_state_counts": dict(sorted(shadow_states.items())),
            "three_layer_shadow_error_count": sum(
                score.score_breakdown["three_layer_shadow"].get("error_status")
                == "calculation_failed"
                for score in industry_scores
            ),
            "three_layer_shadow_candidate_counts": direction_candidates_shadow[
                "selection_counts"
            ],
        }
    )
    return AgentOutput(
        agent_id="sector_ranking",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={
            "industry_top": [s.model_dump() for s in industry_scores[:top_n]],
            "concept_top": [s.model_dump() for s in concept_scores[:top_n]],
            "industry_trend_history": trend_history_metadata,
            "industry_direction_candidates_shadow": direction_candidates_shadow,
        },
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )


def _compound_return(recent_returns: List[float]) -> float:
    wealth = 1.0
    for daily_return in recent_returns:
        wealth *= 1.0 + float(daily_return) / 100.0
    return (wealth - 1.0) * 100.0


def _percentiles(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    if len(values) == 1:
        return {key: 0.5 for key in values}
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    result: Dict[str, float] = {}
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end][1] == ordered[position][1]:
            end += 1
        average_rank = (position + end - 1) / 2.0
        percentile = average_rank / (len(ordered) - 1)
        for key, _ in ordered[position:end]:
            result[key] = percentile
        position = end
    return result


def _build_industry_trend_features(
    sectors: List[SectorSnapshot],
    history: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    sanitized_history = {}
    for name, item in history.items():
        try:
            returns = trusted_daily_returns(
                item.get("recent_returns", [])
            )[-20:]
        except ValueError:
            returns = []
        raw_dates = item.get("recent_dates", [])
        raw_periods = item.get("recent_periods", [])
        dates_type_valid = isinstance(raw_dates, (list, tuple))
        periods_type_valid = isinstance(raw_periods, (list, tuple))
        dates = list(raw_dates)[-20:] if dates_type_valid else []
        periods = list(raw_periods)[-20:] if periods_type_valid else []
        parsed_dates = []
        try:
            parsed_dates = [date.fromisoformat(value) for value in dates]
            dates_valid = (
                dates_type_valid
                and (not dates or len(dates) == len(returns))
                and all(parsed.isoformat() == value for parsed, value in zip(parsed_dates, dates))
                and len(set(dates)) == len(dates)
                and parsed_dates == sorted(parsed_dates)
            )
        except (TypeError, ValueError):
            dates_valid = False
        periods_valid = periods_type_valid and (not periods or len(periods) == len(returns))
        parsed_periods = []
        if periods_valid:
            try:
                for period in periods:
                    if not isinstance(period, (list, tuple)) or len(period) != 2:
                        raise ValueError("invalid period")
                    start = date.fromisoformat(period[0])
                    end = date.fromisoformat(period[1])
                    if start.isoformat() != period[0] or end.isoformat() != period[1] or start >= end:
                        raise ValueError("invalid period")
                    parsed_periods.append((start, end))
                if any(
                    previous[1] != current[0]
                    for previous, current in zip(parsed_periods, parsed_periods[1:])
                ):
                    raise ValueError("non-contiguous periods")
                if dates and any(
                    period[1] != parsed_date
                    for period, parsed_date in zip(parsed_periods, parsed_dates)
                ):
                    raise ValueError("period/date mismatch")
            except (TypeError, ValueError):
                periods_valid = False
        if not returns or not dates_valid or not periods_valid:
            returns, dates, periods = [], [], []
        sanitized_history[name] = {
            "returns": returns,
            "dates": dates,
            "periods": periods,
        }
    reference_history = {
        name: dict(item) for name, item in sanitized_history.items()
    }
    features = {
        sector.name: {
            **history.get(sector.name, {}),
            "recent_returns": sanitized_history.get(sector.name, {}).get(
                "returns", []
            ),
            "recent_dates": sanitized_history.get(sector.name, {}).get("dates", []),
            "recent_periods": sanitized_history.get(sector.name, {}).get(
                "periods", []
            ),
            "relative_strength_percentiles": {},
            "daily_rank_percentiles": [],
            "daily_rank_percentile_slots": [],
        }
        for sector in sectors
    }

    for window in (5, 10, 20):
        grouped_returns: Dict[tuple[str, ...], Dict[str, float]] = {}
        dated_eligible_count = 0
        for name, item in reference_history.items():
            returns = item["returns"]
            dates = item["dates"]
            periods = item["periods"]
            if len(returns) < window:
                continue
            if len(periods) == len(returns):
                signature = tuple(
                    f"{period[0]}->{period[1]}" for period in periods[-window:]
                )
            elif len(dates) == len(returns):
                signature = tuple(dates[-window:])
            else:
                signature = (f"__positional_{window}",)
            if len(periods) == len(returns) or len(dates) == len(returns):
                dated_eligible_count += 1
            grouped_returns.setdefault(signature, {})[name] = _compound_return(
                returns[-window:]
            )
        for signature, group in grouped_returns.items():
            minimum_group_size = (
                2
                if signature[0].startswith("__positional_")
                else max(2, ceil(dated_eligible_count * 0.8))
            )
            if len(group) < minimum_group_size:
                continue
            for name, percentile in _percentiles(group).items():
                if name in features:
                    features[name]["relative_strength_percentiles"][window] = percentile

    rolling_rank_series: Dict[str, List[float]] = {name: [] for name in features}
    rolling_rank_slots: Dict[str, List[Optional[float]]] = {
        name: [None] * 10 for name in features
    }
    for offset in range(-10, 0):
        slot = offset + 10
        grouped_returns: Dict[tuple[str, ...], Dict[str, float]] = {}
        dated_eligible_count = 0
        for name, item in reference_history.items():
            returns = item["returns"]
            dates = item["dates"]
            periods = item["periods"]
            endpoint = len(returns) + offset + 1
            start = endpoint - 5
            if start >= 0 and endpoint <= len(returns):
                if len(periods) == len(returns):
                    signature = tuple(
                        f"{period[0]}->{period[1]}"
                        for period in periods[start:endpoint]
                    )
                elif len(dates) == len(returns):
                    signature = tuple(dates[start:endpoint])
                else:
                    signature = (f"__positional_{offset}",)
                if len(periods) == len(returns) or len(dates) == len(returns):
                    dated_eligible_count += 1
                grouped_returns.setdefault(signature, {})[name] = _compound_return(
                    returns[start:endpoint]
                )
        for signature, group in grouped_returns.items():
            minimum_group_size = (
                2
                if signature[0].startswith("__positional_")
                else max(2, ceil(dated_eligible_count * 0.8))
            )
            if len(group) < minimum_group_size:
                continue
            for name, percentile in _percentiles(group).items():
                if name in rolling_rank_series:
                    rolling_rank_series[name].append(percentile)
                    rolling_rank_slots[name][slot] = percentile

    for name, values in rolling_rank_series.items():
        features[name]["daily_rank_percentiles"] = values
        features[name]["daily_rank_percentile_slots"] = rolling_rank_slots[name]
    return features


def _sort_and_assign_competition_ranks(scores: List[SectorScore]) -> None:
    """Sort deterministically while preserving score ties as equal ranks."""
    scores.sort(key=lambda item: (-item.score, item.sector_id, item.name))
    score_keys = [round(item.score, 8) for item in scores]
    tie_counts = Counter(score_keys)
    current_rank = 0
    previous_key = None

    for position, (item, score_key) in enumerate(zip(scores, score_keys), start=1):
        if score_key != previous_key:
            current_rank = position
            previous_key = score_key
        item.current_rank = current_rank
        item.rank_tie_count = tie_counts[score_key]
        item.rank_tied = item.rank_tie_count > 1
