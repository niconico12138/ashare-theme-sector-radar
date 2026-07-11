"""Shadow-only factor value backtesting utilities.

This module evaluates factor usefulness against historical forward returns. It
only produces research artifacts and never mutates production scores or emits
trade triggers.
"""

from __future__ import annotations

import ast
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from theme_sector_radar.factors.access import get_factor_value

DEFAULT_HORIZONS = ("1d", "3d", "5d", "10d")


@dataclass(frozen=True)
class FactorSpec:
    factor_id: str
    source_fields: tuple[str, ...]
    direction: str = "higher_is_better"


@dataclass(frozen=True)
class FactorSample:
    sample_id: str
    signal_date: str
    code: str
    candidate: dict[str, Any]
    returns: dict[str, float]


@dataclass(frozen=True)
class FactorBacktestDataset:
    samples: list[FactorSample]
    dates: list[str]
    coverage: dict[str, Any]
    date_summary: dict[str, dict[str, Any]]


DEFAULT_FACTOR_SPECS: tuple[FactorSpec, ...] = (
    FactorSpec("final_score", ("final_score", "v3_final_score")),
    FactorSpec("selection_score", ("selection_score",)),
    FactorSpec("selection_score_adjusted", ("selection_score_adjusted",)),
    FactorSpec("optimized_watch_score", ("optimized_watch_score",)),
    FactorSpec("risk_adjusted_watch_score_shadow", ("risk_adjusted_watch_score_shadow",)),
    FactorSpec("short_burst_risk_adjusted_score_shadow", ("short_burst_risk_adjusted_score_shadow",)),
    FactorSpec("optimized_watch_score_v2_shadow", ("optimized_watch_score_v2_shadow",)),
    FactorSpec("factor_composite_shadow_score_v2", ("factor_composite_shadow_score_v2", "v2_score")),
    FactorSpec("factor_composite_shadow_score", ("factor_composite_shadow_score",)),
    FactorSpec("display_score_shadow_90_10", ("display_score_shadow_90_10",)),
    FactorSpec("display_score_shadow_80_20", ("display_score_shadow_80_20",)),
    FactorSpec("display_score_shadow_70_30", ("display_score_shadow_70_30",)),
    FactorSpec("decision_score", ("decision_score",)),
    FactorSpec("trend_score", ("trend_score", "stock_trend_score", "sector_trend_score")),
    FactorSpec("burst_score", ("burst_score", "sector_burst_score")),
    FactorSpec("quant_score", ("quant_score",)),
    FactorSpec("relevance_score", ("relevance_score",)),
    FactorSpec("ma20_slope_5", ("ma20_slope_5",)),
    FactorSpec("stock_trend_score", ("stock_trend_score",)),
    FactorSpec("stock_short_score", ("stock_short_score",)),
    FactorSpec("stock_short_score_v2", ("stock_short_score_v2",)),
    FactorSpec("near_high_250", ("near_high_250",)),
    FactorSpec("relative_strength_20", ("relative_strength_20",)),
    FactorSpec("relative_strength_60", ("relative_strength_60",)),
    FactorSpec("risk_adjusted_return_20", ("risk_adjusted_return_20",)),
    FactorSpec("volume_stability_score", ("volume_stability_score",)),
    FactorSpec("trend_persistence_score", ("trend_persistence_score",)),
    FactorSpec("short_emotion_heat_score", ("short_emotion_heat_score",)),
    FactorSpec("sector_burst_breadth_score", ("sector_burst_breadth_score",)),
    FactorSpec("limit_attention_score", ("limit_attention_score",)),
    FactorSpec("intraday_reversal_risk_score", ("intraday_reversal_risk_score",), direction="lower_is_better"),
    FactorSpec("close_strength_score", ("close_strength_score",)),
    FactorSpec("volume_burst_quality_score", ("volume_burst_quality_score",)),
    FactorSpec("single_name_overheat_score", ("single_name_overheat_score",), direction="lower_is_better"),
    FactorSpec("next_day_cashout_risk_score", ("next_day_cashout_risk_score",), direction="lower_is_better"),
    FactorSpec("short_burst_emotion_score_v1", ("short_burst_emotion_score_v1",)),
    FactorSpec("short_burst_emotion_score_v2", ("short_burst_emotion_score_v2",)),
    FactorSpec("market_short_emotion_score", ("market_short_emotion_score",)),
    FactorSpec("limit_up_breadth_score", ("limit_up_breadth_score",)),
    FactorSpec("limit_up_failure_risk", ("limit_up_failure_risk",), direction="lower_is_better"),
    FactorSpec("leader_continuation_score", ("leader_continuation_score",)),
    FactorSpec("short_burst_environment_score", ("short_burst_environment_score",)),
    FactorSpec("crowding_heat_score", ("crowding_heat_score",), direction="lower_is_better"),
    FactorSpec("news_heat_score", ("news_heat_score",)),
    FactorSpec("policy_catalyst_score", ("policy_catalyst_score",)),
    FactorSpec("earnings_catalyst_score", ("earnings_catalyst_score",)),
    FactorSpec("event_freshness_score", ("event_freshness_score",)),
    FactorSpec("event_continuation_score", ("event_continuation_score",)),
    FactorSpec("negative_news_risk_score", ("negative_news_risk_score",), direction="lower_is_better"),
    FactorSpec("rumor_hype_risk_score", ("rumor_hype_risk_score",), direction="lower_is_better"),
    FactorSpec("short_burst_news_emotion_score_shadow", ("short_burst_news_emotion_score_shadow",)),
    FactorSpec("intraday_close_position_score", ("intraday_close_position_score",)),
    FactorSpec("intraday_high_pullback_risk_score", ("intraday_high_pullback_risk_score",), direction="lower_is_better"),
    FactorSpec("intraday_volume_price_confirm_score", ("intraday_volume_price_confirm_score",)),
    FactorSpec("intraday_sector_breadth_score", ("intraday_sector_breadth_score",)),
    FactorSpec("intraday_late_strength_score", ("intraday_late_strength_score",)),
    FactorSpec("short_burst_intraday_emotion_score_shadow", ("short_burst_intraday_emotion_score_shadow",)),
    FactorSpec("late_return_30m_score", ("late_return_30m_score",)),
    FactorSpec("late_vwap_support_score", ("late_vwap_support_score",)),
    FactorSpec("late_volume_share_score", ("late_volume_share_score",)),
    FactorSpec("late_high_near_close_score", ("late_high_near_close_score",)),
    FactorSpec("high_to_close_drawdown_score", ("high_to_close_drawdown_score",), direction="lower_is_better"),
    FactorSpec("morning_spike_fade_score", ("morning_spike_fade_score",), direction="lower_is_better"),
    FactorSpec("afternoon_fade_score", ("afternoon_fade_score",), direction="lower_is_better"),
    FactorSpec("max_gain_giveback_ratio", ("max_gain_giveback_ratio",), direction="lower_is_better"),
    FactorSpec("close_vs_vwap_score", ("close_vs_vwap_score",)),
    FactorSpec("late_price_above_vwap_ratio", ("late_price_above_vwap_ratio",)),
    FactorSpec("vwap_slope_score", ("vwap_slope_score",)),
    FactorSpec("vwap_reclaim_score", ("vwap_reclaim_score",)),
    FactorSpec("volume_without_price_progress_risk", ("volume_without_price_progress_risk",), direction="lower_is_better"),
    FactorSpec("late_volume_efficiency_score", ("late_volume_efficiency_score",)),
    FactorSpec("amount_acceleration_score", ("amount_acceleration_score",)),
    FactorSpec("volume_spike_exhaustion_score", ("volume_spike_exhaustion_score",), direction="lower_is_better"),
    FactorSpec("opening_drive_score", ("opening_drive_score",)),
    FactorSpec("morning_strength_persist_score", ("morning_strength_persist_score",)),
    FactorSpec("morning_pullback_repair_score", ("morning_pullback_repair_score",)),
    FactorSpec("open_to_midday_resilience_score", ("open_to_midday_resilience_score",)),
    FactorSpec("sector_intraday_breadth_change", ("sector_intraday_breadth_change",)),
    FactorSpec("sector_late_breadth_score", ("sector_late_breadth_score",)),
    FactorSpec("leader_follower_sync_score", ("leader_follower_sync_score",)),
    FactorSpec("stock_vs_sector_intraday_alpha", ("stock_vs_sector_intraday_alpha",)),
    FactorSpec("contraction_score", ("contraction_score",)),
    FactorSpec("atr10_atr50", ("atr10_atr50",), direction="neutral"),
    FactorSpec("range10_range20", ("range10_range20",), direction="neutral"),
    FactorSpec("range20_range60", ("range20_range60",), direction="neutral"),
    FactorSpec("amount_ratio_20", ("amount_ratio_20",)),
    FactorSpec("liquidity_score", ("liquidity_score",)),
    FactorSpec("chasing_risk_score", ("chasing_risk_score",), direction="lower_is_better"),
    FactorSpec("drawdown_depth_20", ("drawdown_depth_20",), direction="contextual"),
    FactorSpec("breakout_distance_20", ("breakout_distance_20",), direction="lower_is_better"),
    FactorSpec("drawdown_risk_score", ("drawdown_risk_score",), direction="lower_is_better"),
    FactorSpec("risk_penalty_score", ("risk_penalty_score",), direction="lower_is_better"),
    FactorSpec("risk_score", ("risk_score",), direction="lower_is_better"),
    FactorSpec("sector_trend_score", ("sector_trend_score",)),
    FactorSpec("sector_burst_score", ("sector_burst_score",)),
    FactorSpec("sector_support_score", ("sector_support_score",)),
    FactorSpec("sector_peer_rank_score", ("sector_peer_rank_score",)),
    FactorSpec("sector_leader_score", ("sector_leader_score",)),
    FactorSpec("agent_score", ("agent_score",)),
    FactorSpec("risk_adjusted_score", ("risk_adjusted_score",)),
    FactorSpec("trend_agent_score", ("trend_agent_score",)),
    FactorSpec("short_agent_score", ("short_agent_score",)),
    FactorSpec("regime_router_shadow_score_v5", ("regime_router_shadow_score_v5",)),
    FactorSpec("defensive_shadow_score", ("defensive_shadow_score",)),
    FactorSpec("shadow_decision_score_v2", ("shadow_decision_score_v2",)),
    FactorSpec("shadow_decision_score_v3", ("shadow_decision_score_v3",)),
    FactorSpec("shadow_decision_score_v4", ("shadow_decision_score_v4",)),
)

def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_candidates(date: str, candidate_root: Path) -> list[dict[str, Any]] | None:
    paths = (
        candidate_root / date / "top30_candidates.news_emotion_backfilled.json",
        candidate_root / date / "top30_candidates.intraday_backfilled.json",
        candidate_root / date / "top30_candidates.analysis_backfilled.json",
        candidate_root / date / "top30_candidates.factor_backfilled.json",
        candidate_root / date / "top30_candidates.json",
    )
    for path in paths:
        if not path.exists():
            continue
        data = _read_json(path)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict) and isinstance(data.get("candidates"), list):
            return [item for item in data["candidates"] if isinstance(item, dict)]
    return None


def _load_forward_returns(date: str, returns_root: Path, horizons: Iterable[str]) -> dict[str, dict[str, float]] | None:
    horizons = tuple(horizons)
    paths = (
        returns_root / date / "forward_returns.json",
        returns_root / f"{date}.json",
    )
    for path in paths:
        if not path.exists():
            continue
        data = _read_json(path)
        raw: Mapping[str, Any] | list[Any]
        if isinstance(data, dict) and isinstance(data.get("forward_returns"), dict):
            raw = data["forward_returns"]
        elif isinstance(data, dict) and isinstance(data.get("returns"), dict):
            raw = data["returns"]
        elif isinstance(data, dict) and isinstance(data.get("items"), list):
            raw = data["items"]
        elif isinstance(data, dict):
            raw = data
        else:
            raw = []

        result: dict[str, dict[str, float]] = {}
        if isinstance(raw, Mapping):
            for code, item in raw.items():
                if not isinstance(item, Mapping):
                    continue
                returns = {h: value for h in horizons if (value := _coerce_float(item.get(h))) is not None}
                if returns:
                    result[str(code).strip()] = returns
        elif isinstance(raw, list):
            for item in raw:
                if not isinstance(item, Mapping):
                    continue
                code = str(item.get("code", "")).strip()
                if not code:
                    continue
                returns = {h: value for h in horizons if (value := _coerce_float(item.get(h))) is not None}
                if returns:
                    result[code] = returns
        if result:
            return result
    return None


def _date_range(start_date: str, end_date: str) -> list[str]:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def load_factor_backtest_dataset(
    dates: Sequence[str],
    candidate_root: Path,
    returns_root: Path,
    horizons: Iterable[str] = DEFAULT_HORIZONS,
) -> FactorBacktestDataset:
    samples: list[FactorSample] = []
    date_summary: dict[str, dict[str, Any]] = {}
    candidate_count = 0
    candidate_with_return_count = 0

    for date in sorted(dict.fromkeys(dates)):
        candidates = _load_candidates(date, candidate_root)
        returns_by_code = _load_forward_returns(date, returns_root, horizons)
        if not candidates:
            date_summary[date] = {"status": "missing_candidates", "candidate_count": 0, "usable_sample_count": 0}
            continue
        candidate_count += len(candidates)
        if not returns_by_code:
            date_summary[date] = {"status": "missing_forward_returns", "candidate_count": len(candidates), "usable_sample_count": 0}
            continue

        usable = 0
        for candidate in candidates:
            code = str(candidate.get("code", "")).strip()
            if not code:
                continue
            returns = returns_by_code.get(code)
            if not returns:
                continue
            usable += 1
            candidate_with_return_count += 1
            samples.append(
                FactorSample(
                    sample_id=f"{date}:{code}",
                    signal_date=date,
                    code=code,
                    candidate=dict(candidate),
                    returns=dict(returns),
                )
            )
        date_summary[date] = {"status": "ok", "candidate_count": len(candidates), "usable_sample_count": usable}

    return FactorBacktestDataset(
        samples=samples,
        dates=sorted(dict.fromkeys(dates)),
        coverage={
            "candidate_count": candidate_count,
            "usable_sample_count": candidate_with_return_count,
            "coverage_ratio": round(candidate_with_return_count / candidate_count, 4) if candidate_count else 0.0,
        },
        date_summary=date_summary,
    )


def extract_factor_value(candidate: Mapping[str, Any], factor_id: str, source_fields: Iterable[str] | None = None) -> float | None:
    fields = tuple(source_fields or (factor_id,))
    for field in fields:
        direct = get_factor_value(candidate, field, prefer="score")
        if direct is not None:
            return direct

    snapshot = candidate.get("factor_snapshot")
    if not isinstance(snapshot, Mapping):
        return None
    factors = snapshot.get("factors")
    if not isinstance(factors, list):
        return None
    wanted = set(fields) | {factor_id}
    for item in factors:
        if not isinstance(item, Mapping):
            continue
        if item.get("factor_id") not in wanted:
            continue
        if item.get("quality") == "missing":
            return None
        return _coerce_float(item.get("score")) or _coerce_float(item.get("raw_value"))
    return None


def _rank(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(indexed):
        end = pos + 1
        while end < len(indexed) and indexed[end][1] == indexed[pos][1]:
            end += 1
        avg_rank = (pos + 1 + end) / 2
        for idx in range(pos, end):
            ranks[indexed[idx][0]] = avg_rank
        pos = end
    return ranks


def calc_rank_ic(scores: Sequence[float], returns: Sequence[float]) -> float | None:
    if len(scores) != len(returns) or len(scores) < 3:
        return None
    ranked_scores = _rank(scores)
    ranked_returns = _rank(returns)
    return calc_correlation(ranked_scores, ranked_returns)


def calc_correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 3:
        return None
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    cov = sum((l - mean_l) * (r - mean_r) for l, r in zip(left, right)) / len(left)
    std_l = math.sqrt(sum((l - mean_l) ** 2 for l in left) / len(left))
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in right) / len(right))
    if std_l == 0 or std_r == 0:
        return 0.0
    return cov / (std_l * std_r)


def _as_sample_dict(sample: FactorSample | Mapping[str, Any]) -> tuple[str, Mapping[str, Any], Mapping[str, Any]]:
    if isinstance(sample, FactorSample):
        return sample.sample_id, sample.candidate, sample.returns
    sample_id = str(sample.get("sample_id", ""))
    candidate = sample.get("candidate", {})
    returns = sample.get("returns", {})
    return sample_id, candidate if isinstance(candidate, Mapping) else {}, returns if isinstance(returns, Mapping) else {}


def _summarize_pairs(pairs: list[tuple[float, float]], min_samples: int) -> dict[str, Any]:
    if len(pairs) < min_samples:
        return {"sample_count": len(pairs), "rank_ic": None, "insufficient_sample": True}
    scores = [score for score, _ in pairs]
    returns = [ret for _, ret in pairs]
    ranked_pairs = sorted(pairs, key=lambda item: item[0])
    bucket_size = max(1, len(ranked_pairs) // 5)
    bottom = [ret for _, ret in ranked_pairs[:bucket_size]]
    top = [ret for _, ret in ranked_pairs[-bucket_size:]]
    quintiles = []
    for idx in range(5):
        start = idx * bucket_size
        end = (idx + 1) * bucket_size if idx < 4 else len(ranked_pairs)
        values = [ret for _, ret in ranked_pairs[start:end]]
        quintiles.append({"quintile": idx + 1, "sample_count": len(values), "avg_return_pct": round(sum(values) / len(values), 4) if values else None})
    top_avg = sum(top) / len(top) if top else None
    bottom_avg = sum(bottom) / len(bottom) if bottom else None
    spread = top_avg - bottom_avg if top_avg is not None and bottom_avg is not None else None
    rank_ic = calc_rank_ic(scores, returns)
    return {
        "sample_count": len(pairs),
        "rank_ic": round(rank_ic, 4) if rank_ic is not None else None,
        "insufficient_sample": False,
        "top20_avg_return_pct": round(top_avg, 4) if top_avg is not None else None,
        "bottom20_avg_return_pct": round(bottom_avg, 4) if bottom_avg is not None else None,
        "top_bottom_spread": round(spread, 4) if spread is not None else None,
        "quintiles": quintiles,
    }


def _value_label(best_ic: float | None, best_spread: float | None) -> str:
    if best_ic is None:
        return "insufficient"
    spread = best_spread or 0.0
    if best_ic >= 0.08 and spread > 0:
        return "strong_positive"
    if best_ic >= 0.03:
        return "watch_positive"
    if best_ic <= -0.08 and spread < 0:
        return "strong_inverse"
    if best_ic <= -0.03:
        return "watch_inverse"
    return "weak_or_noisy"


def _suggested_usage(label: str) -> str:
    if label == "strong_positive":
        return "positive_research_factor"
    if label == "watch_positive":
        return "monitor_only_positive"
    if label == "strong_inverse":
        return "risk_filter_or_penalty"
    if label == "watch_inverse":
        return "monitor_only_inverse"
    if label == "insufficient":
        return "insufficient_data"
    return "profile_only"


def evaluate_factor_value(
    samples: Sequence[FactorSample | Mapping[str, Any]],
    factor_id: str,
    horizons: Iterable[str] = DEFAULT_HORIZONS,
    min_samples: int = 30,
    source_fields: Iterable[str] | None = None,
) -> dict[str, Any]:
    horizons = tuple(horizons)
    values: list[float] = []
    horizon_pairs: dict[str, list[tuple[float, float]]] = {horizon: [] for horizon in horizons}
    for sample in samples:
        _, candidate, returns = _as_sample_dict(sample)
        score = extract_factor_value(candidate, factor_id, source_fields=source_fields)
        if score is None:
            continue
        values.append(score)
        for horizon in horizons:
            ret = _coerce_float(returns.get(horizon))
            if ret is not None:
                horizon_pairs[horizon].append((score, ret))

    horizon_results = {horizon: _summarize_pairs(pairs, min_samples=min_samples) for horizon, pairs in horizon_pairs.items()}
    best_horizon = None
    best_ic = None
    best_spread = None
    for horizon, result in horizon_results.items():
        ic = result.get("rank_ic")
        if ic is None:
            continue
        if best_ic is None or abs(ic) > abs(best_ic):
            best_horizon = horizon
            best_ic = ic
            best_spread = result.get("top_bottom_spread")
    label = _value_label(best_ic, best_spread)
    return {
        "factor_id": factor_id,
        "coverage": {
            "input_sample_count": len(samples),
            "valid_factor_count": len(values),
            "coverage_ratio": round(len(values) / len(samples), 4) if samples else 0.0,
        },
        "distribution": {
            "min": round(min(values), 4) if values else None,
            "max": round(max(values), 4) if values else None,
            "mean": round(sum(values) / len(values), 4) if values else None,
        },
        "horizon_results": horizon_results,
        "best_horizon": best_horizon,
        "best_rank_ic": best_ic,
        "best_spread": best_spread,
        "value_label": label,
        "suggested_usage": _suggested_usage(label),
    }


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)


def _eval_expr(node: ast.AST, variables: Mapping[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_expr(node.body, variables)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        return float(variables.get(node.id, 0.0))
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left = _eval_expr(node.left, variables)
        right = _eval_expr(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                return 0.0
            return left / right
        return left ** right
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
        value = _eval_expr(node.operand, variables)
        return value if isinstance(node.op, ast.UAdd) else -value
    raise ValueError("formula only supports numeric fields and arithmetic operators")


def _formula_variables(formula: str) -> set[str]:
    tree = ast.parse(formula, mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Subscript, ast.Compare, ast.BoolOp, ast.IfExp, ast.Lambda)):
            raise ValueError("formula only supports numeric fields and arithmetic operators")
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def evaluate_formula_value(
    samples: Sequence[FactorSample | Mapping[str, Any]],
    formula_name: str,
    formula: str,
    horizons: Iterable[str] = DEFAULT_HORIZONS,
    min_samples: int = 30,
) -> dict[str, Any]:
    names = _formula_variables(formula)
    tree = ast.parse(formula, mode="eval")
    formula_samples: list[dict[str, Any]] = []
    for sample in samples:
        sample_id, candidate, returns = _as_sample_dict(sample)
        variables = {name: extract_factor_value(candidate, name) or 0.0 for name in names}
        score = _eval_expr(tree, variables)
        formula_samples.append({"sample_id": sample_id, "candidate": {"__formula_score__": score}, "returns": dict(returns)})
    result = evaluate_factor_value(
        formula_samples,
        factor_id="__formula_score__",
        horizons=horizons,
        min_samples=min_samples,
    )
    result["factor_id"] = f"formula:{formula_name}"
    result["formula"] = formula
    result["source_fields"] = sorted(names)
    return result


def run_factor_backtest(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    returns_root: Path,
    horizons: Iterable[str] = DEFAULT_HORIZONS,
    factor_specs: Sequence[FactorSpec] = DEFAULT_FACTOR_SPECS,
    min_samples: int = 30,
) -> dict[str, Any]:
    dates = _date_range(start_date, end_date)
    dataset = load_factor_backtest_dataset(dates, candidate_root=candidate_root, returns_root=returns_root, horizons=horizons)
    factor_results = {}
    for spec in factor_specs:
        factor_results[spec.factor_id] = evaluate_factor_value(
            dataset.samples,
            factor_id=spec.factor_id,
            horizons=horizons,
            min_samples=min_samples,
            source_fields=spec.source_fields,
        )
        factor_results[spec.factor_id]["direction"] = spec.direction
        factor_results[spec.factor_id]["source_fields"] = list(spec.source_fields)

    ranked = sorted(
        factor_results.values(),
        key=lambda item: (abs(item.get("best_rank_ic") or 0), abs(item.get("best_spread") or 0)),
        reverse=True,
    )
    return {
        "schema_version": "factor_backtest.v1",
        "mode": "shadow_only",
        "start_date": start_date,
        "end_date": end_date,
        "horizons": list(horizons),
        "generated_at": datetime.now().isoformat(),
        "coverage": dataset.coverage,
        "date_summary": dataset.date_summary,
        "factor_results": factor_results,
        "ranked_factors": [
            {
                "factor_id": item["factor_id"],
                "value_label": item["value_label"],
                "suggested_usage": item["suggested_usage"],
                "best_horizon": item.get("best_horizon"),
                "best_rank_ic": item.get("best_rank_ic"),
                "best_spread": item.get("best_spread"),
                "valid_factor_count": item.get("coverage", {}).get("valid_factor_count", 0),
            }
            for item in ranked
        ],
        "guardrails": {
            "does_not_modify_scores": True,
            "does_not_emit_trade_triggers": True,
            "trade_decision_allowed": False,
        },
    }


def _window_start_from_lookback(end_date: str, lookback_days: int) -> str:
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return (end - timedelta(days=lookback_days - 1)).strftime("%Y-%m-%d")


def _best_metric(result: Mapping[str, Any], factor_id: str) -> dict[str, Any]:
    factor = result.get("factor_results", {}).get(factor_id, {})
    best_horizon = factor.get("best_horizon")
    horizon = factor.get("horizon_results", {}).get(best_horizon, {}) if best_horizon else {}
    return {
        "best_horizon": best_horizon,
        "rank_ic": horizon.get("rank_ic"),
        "spread": horizon.get("top_bottom_spread"),
        "sample_count": horizon.get("sample_count"),
        "value_label": factor.get("value_label"),
    }


def run_shadow_score_validation(
    end_date: str,
    candidate_root: Path,
    returns_root: Path,
    windows: Iterable[int] = (30, 60, 90, 120),
    horizons: Iterable[str] = DEFAULT_HORIZONS,
    baseline_factor_id: str = "optimized_watch_score",
    shadow_factor_id: str = "optimized_watch_score_v2_shadow",
    min_samples: int = 30,
    min_ic_improvement: float = 0.02,
    min_pass_windows: int = 3,
) -> dict[str, Any]:
    """Compare current and shadow watch scores across rolling windows."""
    window_results: list[dict[str, Any]] = []
    for lookback_days in windows:
        start_date = _window_start_from_lookback(end_date, int(lookback_days))
        result = run_factor_backtest(
            start_date=start_date,
            end_date=end_date,
            candidate_root=candidate_root,
            returns_root=returns_root,
            horizons=horizons,
            min_samples=min_samples,
        )
        baseline = _best_metric(result, baseline_factor_id)
        shadow = _best_metric(result, shadow_factor_id)
        baseline_ic = baseline.get("rank_ic")
        shadow_ic = shadow.get("rank_ic")
        ic_delta = None if baseline_ic is None or shadow_ic is None else round(shadow_ic - baseline_ic, 4)
        passed = bool(
            ic_delta is not None
            and shadow_ic is not None
            and shadow_ic > 0
            and ic_delta >= min_ic_improvement
        )
        window_results.append({
            "lookback_days": int(lookback_days),
            "start_date": start_date,
            "end_date": end_date,
            "baseline_factor_id": baseline_factor_id,
            "shadow_factor_id": shadow_factor_id,
            "baseline_best_horizon": baseline.get("best_horizon"),
            "shadow_best_horizon": shadow.get("best_horizon"),
            "baseline_rank_ic": baseline_ic,
            "shadow_rank_ic": shadow_ic,
            "ic_delta": ic_delta,
            "baseline_spread": baseline.get("spread"),
            "shadow_spread": shadow.get("spread"),
            "sample_count": shadow.get("sample_count"),
            "passed": passed,
            "coverage": result.get("coverage", {}),
        })

    pass_window_count = sum(1 for item in window_results if item["passed"])
    positive_shadow_count = sum(1 for item in window_results if (item.get("shadow_rank_ic") or 0) > 0)
    recommendation = "promote_shadow_candidate" if pass_window_count >= min_pass_windows else "keep_current_observe_shadow"
    return {
        "schema_version": "shadow_score_validation.v1",
        "mode": "shadow_validation_only",
        "baseline_factor_id": baseline_factor_id,
        "shadow_factor_id": shadow_factor_id,
        "end_date": end_date,
        "horizons": list(horizons),
        "windows": list(windows),
        "min_ic_improvement": min_ic_improvement,
        "min_pass_windows": min_pass_windows,
        "window_results": window_results,
        "summary": {
            "window_count": len(window_results),
            "positive_shadow_count": positive_shadow_count,
            "pass_window_count": pass_window_count,
        },
        "recommendation": recommendation,
        "guardrails": {
            "does_not_modify_scores": True,
            "does_not_emit_trade_triggers": True,
            "trade_decision_allowed": False,
        },
    }


def generate_markdown_report(result: Mapping[str, Any]) -> str:
    lines = [
        "# Factor Value Backtest",
        "",
        f"- Window: {result.get('start_date')} to {result.get('end_date')}",
        f"- Mode: {result.get('mode')}",
        f"- Horizons: {', '.join(result.get('horizons', []))}",
        f"- Usable samples: {result.get('coverage', {}).get('usable_sample_count', 0)}/{result.get('coverage', {}).get('candidate_count', 0)}",
        "",
        "## Ranked Factors",
        "",
        "| Factor | Label | Usage | Best Horizon | Rank IC | Spread | N |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for item in result.get("ranked_factors", []):
        lines.append(
            "| {factor_id} | {value_label} | {suggested_usage} | {best_horizon} | {best_rank_ic} | {best_spread} | {valid_factor_count} |".format(
                factor_id=item.get("factor_id"),
                value_label=item.get("value_label"),
                suggested_usage=item.get("suggested_usage"),
                best_horizon=item.get("best_horizon") or "-",
                best_rank_ic="-" if item.get("best_rank_ic") is None else f"{item.get('best_rank_ic'):.4f}",
                best_spread="-" if item.get("best_spread") is None else f"{item.get('best_spread'):.4f}%",
                valid_factor_count=item.get("valid_factor_count", 0),
            )
        )
    lines.extend([
        "",
        "## Guardrails",
        "",
        "This report is research-only. It does not modify final_score, v2_score, selection_score, or emit buy/sell triggers.",
    ])
    return "\n".join(lines)

