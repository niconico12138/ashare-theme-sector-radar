"""Independent, paper-only ML shadow research for industry sectors."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .contract import canonical_sha256
from .ranker import walk_forward_ranker_predictions


SCHEMA_VERSION = "ml-industry-sector-shadow-dataset-v1"
PREDICTION_SCHEMA_VERSION = "ml-industry-sector-shadow-predictions-v1"
EVALUATION_SCHEMA_VERSION = "ml-industry-sector-shadow-evaluation-v1"
MODEL_SCHEMA_VERSION = "ml-industry-sector-shadow-model-v1"
MODE = "paper_shadow_research_only"
CLASSIFICATION = "real_historical_reconstruction_research"
LABEL_DEFINITION = "future_5d_industry_return_minus_cross_sectional_median"
DISCLAIMER = "Research output only; no broker connection and no live order instruction."
FEATURE_PROFILE_ALL = "all_v1"
FEATURE_PROFILE_NO_RULE_DIRECTION = "no_rule_direction_v1"
RULE_GATE_THRESHOLD = 50.0
MIN_MATURE_DATES = 60
MIN_SECTORS = 30
MIN_ROWS_PER_DATE = 10

FEATURE_NAMES = (
    "momentum_1d",
    "momentum_3d",
    "momentum_5d",
    "momentum_10d",
    "momentum_20d",
    "volatility_5d",
    "volatility_20d",
    "drawdown_20d",
    "volume_change_5d",
    "amount_change_5d",
    "rank_pct_5d",
    "rank_pct_20d",
    "rank_momentum_5d",
    "market_return_1d",
    "market_return_5d",
    "market_breadth_1d",
    "market_dispersion_1d",
    "market_volatility_20d",
    "rule_time_series_score",
    "rule_cross_section_score",
    "rule_rank_momentum_score",
    "rule_direction_score",
)
RULE_DIRECTION_FEATURES = tuple(name for name in FEATURE_NAMES if name.startswith("rule_"))
FEATURE_PROFILES = {
    FEATURE_PROFILE_ALL: FEATURE_NAMES,
    FEATURE_PROFILE_NO_RULE_DIRECTION: tuple(
        name for name in FEATURE_NAMES if name not in RULE_DIRECTION_FEATURES
    ),
}
ROUND_FEATURE_PROFILES = {
    "time_series_only_v1": (
        "momentum_1d", "momentum_3d", "momentum_5d", "momentum_10d", "momentum_20d",
        "volatility_5d", "volatility_20d", "drawdown_20d", "volume_change_5d", "amount_change_5d",
    ),
    "cross_section_only_v1": ("rank_pct_5d", "rank_pct_20d", "rank_momentum_5d"),
    "rank_momentum_only_v1": ("rank_pct_5d", "rank_pct_20d", "rank_momentum_5d", "momentum_5d", "momentum_20d"),
    "market_state_only_v1": (
        "market_return_1d", "market_return_5d", "market_breadth_1d", "market_dispersion_1d", "market_volatility_20d",
    ),
    "no_market_state_v1": tuple(
        name for name in FEATURE_NAMES
        if name not in {"market_return_1d", "market_return_5d", "market_breadth_1d", "market_dispersion_1d", "market_volatility_20d"}
    ),
    "compact_v1": ("momentum_5d", "momentum_20d", "rank_pct_5d", "rank_momentum_5d", "market_return_1d"),
    "time_series_cross_v1": (
        "momentum_1d", "momentum_3d", "momentum_5d", "momentum_10d", "momentum_20d",
        "volatility_5d", "volatility_20d", "drawdown_20d", "rank_pct_5d", "rank_pct_20d", "rank_momentum_5d",
    ),
    "time_series_market_v1": (
        "momentum_1d", "momentum_3d", "momentum_5d", "momentum_10d", "momentum_20d",
        "volatility_5d", "volatility_20d", "drawdown_20d", "market_return_1d", "market_return_5d",
        "market_breadth_1d", "market_dispersion_1d", "market_volatility_20d",
    ),
    "cross_section_market_v1": (
        "rank_pct_5d", "rank_pct_20d", "rank_momentum_5d", "market_return_1d", "market_return_5d",
        "market_breadth_1d", "market_dispersion_1d", "market_volatility_20d",
    ),
    "no_volume_amount_v1": tuple(
        name for name in FEATURE_NAMES if name not in {"volume_change_5d", "amount_change_5d"}
    ),
    "no_volatility_drawdown_v1": tuple(
        name for name in FEATURE_NAMES if name not in {"volatility_5d", "volatility_20d", "drawdown_20d"}
    ),
    "rule_direction_only_v1": RULE_DIRECTION_FEATURES,
}

ROUND_SPECS = (
    {
        "name": "round1_all_v1", "feature_profile": "all_v1",
        "hypothesis": "完整时序、截面、排名动量、市场状态和 rule-direction 特征应优于方向分基线。",
    },
    {
        "name": "round2_no_rule_direction_v1", "feature_profile": "no_rule_direction_v1",
        "hypothesis": "移除 rule-direction 特征后，ML 仍应保留独立于方向分的增益。",
    },
    {
        "name": "round3_time_series_only_v1", "feature_profile": "time_series_only_v1",
        "hypothesis": "仅用时序动量、波动和成交活跃度即可解释主要的未来 5 日板块相对收益。",
    },
    {
        "name": "round4_cross_section_only_v1", "feature_profile": "cross_section_only_v1",
        "hypothesis": "仅用截面排名和排名动量可检验板块轮动是否主要来自相对强弱。",
    },
    {
        "name": "round5_rank_momentum_only_v1", "feature_profile": "rank_momentum_only_v1",
        "hypothesis": "短中期排名动量的窄特征集应在降低复杂度时保持排序质量。",
    },
    {
        "name": "round6_market_state_only_v1", "feature_profile": "market_state_only_v1",
        "hypothesis": "市场状态特征单独不能稳定完成行业截面排序，应作为淘汰对照。",
    },
    {
        "name": "round7_no_market_state_v1", "feature_profile": "no_market_state_v1",
        "hypothesis": "去除市场状态后，行业自身特征仍应提供可重复的截面信号。",
    },
    {
        "name": "round8_compact_v1", "feature_profile": "compact_v1",
        "hypothesis": "五个预注册核心特征可在较低维度下复现完整模型的方向。",
    },
    {
        "name": "round9_low_complexity_v1", "feature_profile": "all_v1",
        "hypothesis": "降低树数量和叶子数可减少过拟合，同时保留 walk-forward 增益。",
        "n_estimators": 20, "num_leaves": 7,
    },
    {
        "name": "round10_long_purge_v1", "feature_profile": "all_v1",
        "hypothesis": "将 purge 从 5 日延长至 10 日后，信号若仍存在才更可信。",
        "purge_dates": 10,
    },
    {
        "name": "round11_short_purge_v1", "feature_profile": "all_v1",
        "hypothesis": "A shorter two-day purge tests whether the baseline gain is sensitive to the minimum label separation.",
        "purge_dates": 2,
    },
    {
        "name": "round12_long_purge15_v1", "feature_profile": "all_v1",
        "hypothesis": "A fifteen-day purge is a stricter leakage-pressure test than the five-day baseline.",
        "purge_dates": 15,
    },
    {
        "name": "round13_short_test_window_v1", "feature_profile": "all_v1",
        "hypothesis": "Five-day test windows should reveal whether ten-day fold aggregation hides local instability.",
        "test_dates": 5,
    },
    {
        "name": "round14_long_test_window_v1", "feature_profile": "all_v1",
        "hypothesis": "Fifteen-day test windows should reduce fold noise without changing the label definition.",
        "test_dates": 15,
    },
    {
        "name": "round15_min_train50_v1", "feature_profile": "all_v1",
        "hypothesis": "A fifty-date minimum training window tests sensitivity to early sample size.",
        "min_train_dates": 50,
    },
    {
        "name": "round16_min_train70_v1", "feature_profile": "all_v1",
        "hypothesis": "A seventy-date minimum training window tests whether more history improves ranking stability.",
        "min_train_dates": 70,
    },
    {
        "name": "round17_rolling60_v1", "feature_profile": "all_v1",
        "hypothesis": "A rolling sixty-date training cap tests whether recent regimes dominate expanding history.",
        "max_train_dates": 60,
    },
    {
        "name": "round18_rolling80_v1", "feature_profile": "all_v1",
        "hypothesis": "An eighty-date training cap tests a wider recent-history compromise.",
        "max_train_dates": 80,
    },
    {
        "name": "round19_time_series_cross_v1", "feature_profile": "time_series_cross_v1",
        "hypothesis": "Combining intrinsic momentum with cross-sectional rank should retain signal without market context.",
    },
    {
        "name": "round20_time_series_market_v1", "feature_profile": "time_series_market_v1",
        "hypothesis": "Combining time-series behavior with market state tests contextual momentum.",
    },
    {
        "name": "round21_cross_section_market_v1", "feature_profile": "cross_section_market_v1",
        "hypothesis": "Cross-sectional rank plus market state tests whether relative strength needs regime context.",
    },
    {
        "name": "round22_no_volume_amount_v1", "feature_profile": "no_volume_amount_v1",
        "hypothesis": "Removing activity-change features tests whether price and rank features are sufficient.",
    },
    {
        "name": "round23_no_volatility_drawdown_v1", "feature_profile": "no_volatility_drawdown_v1",
        "hypothesis": "Removing risk-shape features tests robustness to volatility and drawdown measurement noise.",
    },
    {
        "name": "round24_rule_direction_only_v1", "feature_profile": "rule_direction_only_v1",
        "hypothesis": "A rule-direction-only LambdaRank model tests ML behavior using only existing direction inputs.",
    },
    {
        "name": "round25_fixed_clip_stress_v1", "feature_profile": "all_v1",
        "hypothesis": "Fixed semantic clipping tests sensitivity to extreme feature values without using future data.",
        "feature_value_mode": "fixed_clip_v1",
    },
    {
        "name": "round26_missing_zero_stress_v1", "feature_profile": "all_v1",
        "hypothesis": "Deterministic ten-percent zero imputation tests feature missingness robustness without label changes.",
        "feature_value_mode": "deterministic_missing_zero_10pct_v1",
    },
    {
        "name": "round27_seed_variant_v1", "feature_profile": "all_v1",
        "hypothesis": "A neighboring deterministic seed tests whether ranking metrics are seed-sensitive.",
        "random_state": 20260721,
    },
    {
        "name": "round28_low_complexity10_v1", "feature_profile": "all_v1",
        "hypothesis": "Ten estimators and three leaves test the lower model-capacity boundary.",
        "n_estimators": 10, "num_leaves": 3,
    },
    {
        "name": "round29_high_complexity_v1", "feature_profile": "all_v1",
        "hypothesis": "Eighty estimators and thirty-one leaves test sensitivity to excess model capacity.",
        "n_estimators": 80, "num_leaves": 31,
    },
    {
        "name": "round30_gate30_v1", "feature_profile": "all_v1",
        "hypothesis": "A rule gate threshold of thirty tests a broad gate before ML ranking.",
        "rule_gate_threshold": 30.0,
    },
    {
        "name": "round31_gate70_v1", "feature_profile": "all_v1",
        "hypothesis": "A rule gate threshold of seventy tests a selective gate before ML ranking.",
        "rule_gate_threshold": 70.0,
    },
    {
        "name": "round32_topk135_v1", "feature_profile": "all_v1",
        "hypothesis": "Top-1/3/5 evaluation tests concentration sensitivity.",
        "top_k_values": (1, 3, 5),
    },
    {
        "name": "round33_topk5710_v1", "feature_profile": "all_v1",
        "hypothesis": "Top-5/7/10 evaluation tests broader portfolio sensitivity.",
        "top_k_values": (5, 7, 10),
    },
    {
        "name": "round34_cost10_v1", "feature_profile": "all_v1",
        "hypothesis": "Ten basis points per unit turnover tests a moderate paper-cost deduction.",
        "transaction_cost_bps": 10.0,
    },
    {
        "name": "round35_cost25_v1", "feature_profile": "all_v1",
        "hypothesis": "Twenty-five basis points per unit turnover tests a harsher paper-cost deduction.",
        "transaction_cost_bps": 25.0,
    },
    {
        "name": "round36_early_window_v1", "feature_profile": "all_v1",
        "hypothesis": "The early evaluation slice tests whether aggregate lift is front-loaded.",
        "evaluation_start": "2026-05-18", "evaluation_end": "2026-06-12",
    },
    {
        "name": "round37_late_window_v1", "feature_profile": "all_v1",
        "hypothesis": "The late evaluation slice tests whether aggregate lift persists in recent dates.",
        "evaluation_start": "2026-06-15", "evaluation_end": "2026-07-09",
    },
    {
        "name": "round38_risk_on_v1", "feature_profile": "all_v1",
        "hypothesis": "Risk-on-only evaluation tests regime-specific stability.",
        "evaluation_regimes": ("risk_on",),
    },
    {
        "name": "round39_risk_off_v1", "feature_profile": "all_v1",
        "hypothesis": "Risk-off-only evaluation tests regime-specific stability.",
        "evaluation_regimes": ("risk_off",),
    },
    {
        "name": "round40_no_rule_low_complexity_v1", "feature_profile": "no_rule_direction_v1",
        "hypothesis": "A low-complexity model without rule-direction features tests independent compact robustness.",
        "n_estimators": 20, "num_leaves": 7,
    },
)

SHADOW_FORBIDDEN_OUTPUT_FIELDS = frozenset({
    "quant_score", "final_score", "v2_score", "selection_score", "selection_score_adjusted",
    "order_id", "broker", "account", "side", "quantity", "qty", "order_type", "price",
})


def feature_names_for_profile(feature_profile: str) -> tuple[str, ...]:
    feature_names = FEATURE_PROFILES.get(feature_profile) or ROUND_FEATURE_PROFILES.get(feature_profile)
    if feature_names is None:
        raise ValueError("unknown industry sector feature profile")
    return tuple(feature_names)


def validate_shadow_prediction_fields(prediction_report: Mapping[str, Any]) -> None:
    forbidden = SHADOW_FORBIDDEN_OUTPUT_FIELDS.intersection(prediction_report)
    if forbidden:
        raise ValueError(f"industry sector shadow contains forbidden output fields: {sorted(forbidden)}")
    for row in prediction_report.get("predictions") or []:
        forbidden = SHADOW_FORBIDDEN_OUTPUT_FIELDS.intersection(row)
        if forbidden:
            raise ValueError(f"industry sector shadow prediction contains forbidden fields: {sorted(forbidden)}")

_KEYS = {
    "date": ("\u65e5\u671f", "date", "trade_date"),
    "close": ("\u6536\u76d8\u4ef7", "close", "收盘价"),
    "volume": ("\u6210\u4ea4\u91cf", "volume", "成交量"),
    "amount": ("\u6210\u9898\u989d", "\u6210\u4ea4\u989d", "amount", "成交额"),
}


def _value(row: Mapping[str, Any], name: str) -> Any:
    for key in _KEYS[name]:
        if key in row:
            return row[key]
    return None


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _date(value: Any, *, context: str) -> str:
    text = str(value or "")
    parsed = date.fromisoformat(text)
    if parsed.isoformat() != text:
        raise ValueError(f"{context} must be canonical ISO date")
    return text


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(value: float, population: Sequence[float]) -> float:
    if len(population) <= 1:
        return 0.5
    ordered = sorted(population)
    rank = sum(item < value for item in ordered)
    return rank / (len(ordered) - 1)


def _returns(values: Sequence[float], horizon: int) -> float | None:
    if len(values) <= horizon or values[-horizon - 1] <= 0:
        return None
    return values[-1] / values[-horizon - 1] - 1.0


def _std(values: Sequence[float]) -> float:
    return pstdev(values) if len(values) >= 2 else 0.0


def _drawdown(values: Sequence[float]) -> float:
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return abs(worst)


def _load_histories(source_root: Path) -> tuple[dict[str, list[dict[str, float | str]]], list[dict[str, Any]]]:
    if not source_root.is_dir():
        raise ValueError("industry sector history root is missing")
    histories: dict[str, list[dict[str, float | str]]] = {}
    manifest: list[dict[str, Any]] = []
    for path in sorted((source_root / "industry").glob("*.json")):
        payload, source_sha = load_strict_json_with_sha256(path)
        if payload.get("sector_type") not in (None, "industry"):
            continue
        source_text = str(payload.get("source") or "").casefold()
        if payload.get("fixture_only") is True or "fixture" in source_text or "synthetic" in source_text:
            raise ValueError("industry sector ML shadow refuses fixture or synthetic history")
        name = str(payload.get("sector_name") or path.stem)
        normalized: list[dict[str, float | str]] = []
        for raw in payload.get("records") or []:
            if not isinstance(raw, Mapping):
                continue
            day = _date(_value(raw, "date"), context="industry history date")
            close = _finite(_value(raw, "close"))
            volume = _finite(_value(raw, "volume"))
            amount = _finite(_value(raw, "amount"))
            if close is None or close <= 0:
                continue
            normalized.append(
                {
                    "date": day,
                    "close": close,
                    "volume": volume if volume is not None and volume > 0 else 0.0,
                    "amount": amount if amount is not None and amount > 0 else 0.0,
                }
            )
        normalized.sort(key=lambda row: str(row["date"]))
        if len(normalized) < 25:
            continue
        histories[name] = normalized
        manifest.append(
            {
                "sector_name": name,
                "path": str(path.resolve()),
                "sha256": source_sha,
                "record_count": len(normalized),
                "source": str(payload.get("source") or "unknown"),
                "fetched_at": payload.get("fetched_at"),
            }
        )
    if len(histories) < MIN_SECTORS:
        raise ValueError(
            f"industry history coverage below minimum: {len(histories)} sectors"
        )
    return histories, manifest


def _build_feature_rows(
    histories: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    by_sector: dict[str, dict[str, Mapping[str, Any]]] = {
        name: {str(row["date"]): row for row in rows} for name, rows in histories.items()
    }
    all_dates = sorted({day for rows in by_sector.values() for day in rows})
    date_state: dict[str, dict[str, Any]] = {}
    for day in all_dates:
        current: dict[str, float] = {}
        for sector, rows in by_sector.items():
            row = rows.get(day)
            if row is None:
                continue
            prior = [rows[d] for d in sorted(rows) if d <= day]
            closes = [float(item["close"]) for item in prior]
            value = _returns(closes, 1)
            if value is not None:
                current[sector] = value
        if current:
            date_state[day] = {
                "returns_1d": current,
                "market_return_1d": mean(current.values()),
                "market_breadth_1d": sum(value > 0 for value in current.values()) / len(current),
                "market_dispersion_1d": _std(list(current.values())),
            }
    feature_rows: list[dict[str, Any]] = []
    labeled_rows: list[dict[str, Any]] = []
    mature_dates: list[str] = []
    sector_codes = {
        sector: f"{index:06d}"
        for index, sector in enumerate(sorted(by_sector), start=1)
    }
    for sector, rows in by_sector.items():
        dates = sorted(rows)
        for index, day in enumerate(dates):
            if index < 20 or day not in date_state:
                continue
            current = rows[day]
            prior_rows = [rows[d] for d in dates[: index + 1]]
            closes = [float(row["close"]) for row in prior_rows]
            volumes = [float(row["volume"]) for row in prior_rows]
            amounts = [float(row["amount"]) for row in prior_rows]
            returns = {h: _returns(closes, h) for h in (1, 3, 5, 10, 20)}
            if any(value is None for value in returns.values()):
                continue
            daily_returns = [
                _returns(closes[:offset + 1], 1)
                for offset in range(max(1, len(closes) - 20), len(closes))
            ]
            daily_returns = [value for value in daily_returns if value is not None]
            state = date_state[day]
            cross_values_5 = [
                _returns([float(rows[d]["close"]) for d in sorted(rows) if d <= day], 5)
                for rows in by_sector.values()
            ]
            cross_values_20 = [
                _returns([float(rows[d]["close"]) for d in sorted(rows) if d <= day], 20)
                for rows in by_sector.values()
            ]
            cross_values_5 = [value for value in cross_values_5 if value is not None]
            cross_values_20 = [value for value in cross_values_20 if value is not None]
            rank5 = _percentile(float(returns[5]), cross_values_5)
            rank20 = _percentile(float(returns[20]), cross_values_20)
            volatility_5 = _std(daily_returns[-5:])
            volatility_20 = _std(daily_returns[-20:])
            rule_time = max(0.0, min(100.0, 50.0 + 500.0 * float(returns[5])))
            rule_cross = rank5 * 100.0
            rule_rank = max(0.0, min(100.0, (rank5 - rank20 + 0.5) * 100.0))
            rule_direction = 0.5 * rule_time + 0.3 * rule_cross + 0.2 * rule_rank
            feature_values = {
                "momentum_1d": float(returns[1]),
                "momentum_3d": float(returns[3]),
                "momentum_5d": float(returns[5]),
                "momentum_10d": float(returns[10]),
                "momentum_20d": float(returns[20]),
                "volatility_5d": volatility_5,
                "volatility_20d": volatility_20,
                "drawdown_20d": _drawdown(closes[-20:]),
                "volume_change_5d": _returns(volumes, 5) or 0.0,
                "amount_change_5d": _returns(amounts, 5) or 0.0,
                "rank_pct_5d": rank5,
                "rank_pct_20d": rank20,
                "rank_momentum_5d": rank5 - rank20,
                "market_return_1d": float(state["market_return_1d"]),
                "market_return_5d": mean(
                    [_returns([float(by_sector[s][d]["close"]) for d in sorted(by_sector[s]) if d <= day], 5)
                     for s in by_sector if _returns([float(by_sector[s][d]["close"]) for d in sorted(by_sector[s]) if d <= day], 5) is not None]
                ),
                "market_breadth_1d": float(state["market_breadth_1d"]),
                "market_dispersion_1d": float(state["market_dispersion_1d"]),
                "market_volatility_20d": volatility_20,
                "rule_time_series_score": rule_time,
                "rule_cross_section_score": rule_cross,
                "rule_rank_momentum_score": rule_rank,
                "rule_direction_score": rule_direction,
            }
            if not all(math.isfinite(float(value)) for value in feature_values.values()):
                continue
            row = {
                "as_of_date": day,
                "sector_name": sector,
                "stock_code": sector_codes[sector],
                "features": {name: float(feature_values[name]) for name in FEATURE_NAMES},
                "rule_direction_score": round(rule_direction, 6),
                "market_regime": (
                    "risk_off" if state["market_return_1d"] < 0 and state["market_breadth_1d"] < 0.5
                    else "risk_on" if state["market_return_1d"] > 0 and state["market_breadth_1d"] >= 0.5
                    else "mixed"
                ),
            }
            feature_rows.append(row)
            if index + 5 < len(dates):
                future = rows[dates[index + 5]]
                future_return = float(future["close"]) / float(current["close"]) - 1.0
                future_returns = []
                for other, other_rows in by_sector.items():
                    if day in other_rows and dates[index + 5] in other_rows:
                        future_returns.append(
                            float(other_rows[dates[index + 5]]["close"])
                            / float(other_rows[day]["close"])
                            - 1.0
                        )
                if len(future_returns) < MIN_ROWS_PER_DATE:
                    continue
                median_future = sorted(future_returns)[len(future_returns) // 2]
                labeled = {
                    **row,
                    "future_return_5d": future_return,
                    "future_cross_section_median_5d": median_future,
                    "training_label": future_return - median_future,
                    "training_label_end_date": dates[index + 5],
                }
                labeled_rows.append(labeled)
                mature_dates.append(day)
    feature_rows.sort(key=lambda row: (row["as_of_date"], row["sector_name"]))
    labeled_rows.sort(key=lambda row: (row["as_of_date"], row["sector_name"]))
    return feature_rows, labeled_rows, sorted(set(mature_dates))


def build_industry_sector_dataset(
    source_root: Path | str, *, _validate: bool = True
) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    histories, sources = _load_histories(source_root)
    feature_rows, labeled_rows, mature_dates = _build_feature_rows(histories)
    if len(mature_dates) < MIN_MATURE_DATES:
        raise ValueError(f"industry sector history has only {len(mature_dates)} mature dates")
    if not labeled_rows:
        raise ValueError("industry sector dataset has no mature labels")
    core = {
        "schema_version": SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": CLASSIFICATION,
        "feature_names": list(FEATURE_NAMES),
        "feature_profiles": {key: list(value) for key, value in FEATURE_PROFILES.items()},
        "label_definition": LABEL_DEFINITION,
        "source_manifest": {
            "source_root": str(source_root),
            "sector_type": "industry",
            "documents": sources,
        },
        "counts": {
            "sector_count": len(histories),
            "feature_rows": len(feature_rows),
            "labeled_rows": len(labeled_rows),
            "mature_dates": len(mature_dates),
            "date_start": mature_dates[0],
            "date_end": mature_dates[-1],
        },
        "feature_universe_records": feature_rows,
        "records": labeled_rows,
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
    }
    dataset = {**core, "dataset_sha256": canonical_sha256(core), "disclaimer": DISCLAIMER}
    if _validate:
        validate_industry_sector_dataset(dataset)
    return dataset


def validate_industry_sector_dataset(dataset: Mapping[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "feature_universe_records", "records", "source_manifest", "counts",
    ):
        if not isinstance(dataset.get(key), (list, Mapping)):
            raise ValueError(f"industry sector dataset field is missing: {key}")
    if dataset.get("schema_version") != SCHEMA_VERSION or dataset.get("mode") != MODE:
        raise ValueError("industry sector dataset schema mismatch")
    if any(dataset.get(key) is not False for key in (
        "strict_pit_eligible", "eligible_for_oos_claim", "promotion_allowed",
        "live_trading_allowed", "formal_predictor_compatible",
    )):
        raise ValueError("industry sector dataset safety flags must be false")
    manifest = dataset["source_manifest"]
    if manifest.get("sector_type") != "industry":
        raise ValueError("industry sector source type mismatch")
    for source in manifest.get("documents") or []:
        path = Path(str(source.get("path") or ""))
        if not path.is_absolute() or not path.is_file() or _sha256(path) != source.get("sha256"):
            raise ValueError("industry sector source physical identity mismatch")
    rebuilt = build_industry_sector_dataset(manifest.get("source_root"), _validate=False)
    if rebuilt.get("dataset_sha256") != dataset.get("dataset_sha256"):
        raise ValueError("industry sector dataset does not match source manifest")
    for row in dataset["records"]:
        if tuple(row.get("features", {})) != FEATURE_NAMES:
            raise ValueError("industry sector feature order mismatch")
        if not math.isfinite(float(row.get("training_label"))):
            raise ValueError("industry sector label is non-finite")
    core = {key: dataset.get(key) for key in (
        "schema_version", "mode", "status", "dataset_classification", "feature_names",
        "feature_profiles", "label_definition", "source_manifest", "counts",
        "feature_universe_records", "records", "strict_pit_eligible",
        "eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed",
        "formal_predictor_compatible", "agent_interface",
    )}
    if canonical_sha256(core) != dataset.get("dataset_sha256"):
        raise ValueError("industry sector dataset SHA mismatch")
    return [dict(row) for row in dataset["records"]]


def _average_rank(values: Sequence[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=lambda index: (values[index], index))
    result = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2.0
        for index in ordered[cursor:end]:
            result[index] = rank
        cursor = end
    return result


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_rank, right_rank = _average_rank(left), _average_rank(right)
    lm, rm = mean(left_rank), mean(right_rank)
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left_rank, right_rank))
    denominator = math.sqrt(
        sum((a - lm) ** 2 for a in left_rank) * sum((b - rm) ** 2 for b in right_rank)
    )
    return numerator / denominator if denominator else None


def _ndcg(scores: Sequence[float], labels: Sequence[float], k: int) -> float | None:
    if not labels:
        return None
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]
    ideal = sorted(labels, reverse=True)[:k]
    low = min(labels)
    gains = [max(0.0, value - low) + 1e-9 for value in labels]
    dcg = sum(gains[i] / math.log2(pos + 2) for pos, i in enumerate(order))
    ideal_dcg = sum((max(0.0, value - low) + 1e-9) / math.log2(pos + 2) for pos, value in enumerate(ideal))
    return dcg / ideal_dcg if ideal_dcg else None


def _fixed_feature_bounds(name: str) -> tuple[float, float]:
    if name.startswith("rule_"):
        return 0.0, 100.0
    if name.startswith("rank_pct") or name == "market_breadth_1d":
        return 0.0, 1.0
    if name.startswith("volatility") or name == "drawdown_20d":
        return 0.0, 1.0
    return -1.0, 1.0


def prepare_round_records(
    records: Sequence[Mapping[str, Any]],
    feature_names: Sequence[str],
    *,
    feature_value_mode: str = "raw",
) -> list[dict[str, Any]]:
    if feature_value_mode not in {
        "raw", "fixed_clip_v1", "deterministic_missing_zero_10pct_v1",
    }:
        raise ValueError(f"unknown industry sector feature value mode: {feature_value_mode}")
    prepared: list[dict[str, Any]] = []
    for row in records:
        values = {}
        for name in feature_names:
            value = float(row["features"][name])
            if feature_value_mode == "fixed_clip_v1":
                low, high = _fixed_feature_bounds(name)
                value = min(high, max(low, value))
            elif feature_value_mode == "deterministic_missing_zero_10pct_v1":
                identity = f"{row.get('as_of_date')}|{row.get('stock_code')}|{name}"
                if hashlib.sha256(identity.encode("utf-8")).digest()[0] < 26:
                    value = 0.0
            values[name] = value
        prepared.append({**row, "features": values})
    return prepared


def evaluate_industry_sector_shadow(
    dataset: Mapping[str, Any],
    prediction_report: Mapping[str, Any],
    *,
    rule_gate_threshold: float = RULE_GATE_THRESHOLD,
    top_k_values: Sequence[int] = (3, 5, 7),
    evaluation_start: str | None = None,
    evaluation_end: str | None = None,
    evaluation_regimes: Sequence[str] | None = None,
    transaction_cost_bps: float = 0.0,
) -> dict[str, Any]:
    if not top_k_values or any(int(value) <= 0 for value in top_k_values):
        raise ValueError("industry sector evaluation top-k values must be positive")
    if transaction_cost_bps < 0:
        raise ValueError("industry sector transaction cost cannot be negative")
    allowed_regimes = {"risk_on", "mixed", "risk_off"}
    requested_regimes = set(evaluation_regimes or allowed_regimes)
    if not requested_regimes or not requested_regimes.issubset(allowed_regimes):
        raise ValueError("industry sector evaluation regimes are invalid")
    records = validate_industry_sector_dataset(dataset)
    validate_shadow_prediction_fields(prediction_report)
    predictions = prediction_report.get("predictions") or []
    labels = {(row["as_of_date"], row["sector_name"]): row for row in records}
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in predictions:
        identity = (str(row["as_of_date"]), str(row["sector_name"]))
        if evaluation_start and identity[0] < evaluation_start:
            continue
        if evaluation_end and identity[0] > evaluation_end:
            continue
        source = labels.get(identity)
        if source is None:
            continue
        if source["market_regime"] not in requested_regimes:
            continue
        by_date[identity[0]].append({
            "sector_name": identity[1],
            "ml_score": float(row["prediction"]),
            "rule_score": float(source["rule_direction_score"]),
            "label": float(source["training_label"]),
            "raw_return": float(source["future_return_5d"]),
            "regime": source["market_regime"],
        })
    metrics: dict[str, Any] = {}
    for method in ("rule", "ml", "rule_gate_ml"):
        for top_k in top_k_values:
            daily: list[dict[str, Any]] = []
            selected_by_date: dict[str, list[str]] = {}
            daily_rank_scores: list[tuple[list[float], list[float]]] = []
            for day, rows in sorted(by_date.items()):
                if method == "rule":
                    selected = sorted(rows, key=lambda x: (-x["rule_score"], x["sector_name"]))[:top_k]
                elif method == "rule_gate_ml":
                    gated = [row for row in rows if row["rule_score"] >= rule_gate_threshold]
                    selected = sorted(gated, key=lambda x: (-x["ml_score"], x["sector_name"]))[:top_k]
                else:
                    selected = sorted(rows, key=lambda x: (-x["ml_score"], x["sector_name"]))[:top_k]
                if not selected:
                    continue
                selected_by_date[day] = [row["sector_name"] for row in selected]
                ranking_rows = (
                    [row for row in rows if row["rule_score"] >= rule_gate_threshold]
                    if method == "rule_gate_ml"
                    else rows
                )
                score_key = "rule_score" if method == "rule" else "ml_score"
                daily_rank_scores.append(
                    (
                        [row[score_key] for row in ranking_rows],
                        [row["label"] for row in ranking_rows],
                    )
                )
                daily.append({
                    "date": day,
                    "mean_excess_return": mean(row["label"] for row in selected),
                    "mean_raw_return": mean(row["raw_return"] for row in selected),
                    "win_rate": sum(row["raw_return"] > 0 for row in selected) / len(selected),
                    "universe_mean_excess_return": mean(row["label"] for row in rows),
                    "universe_mean_raw_return": mean(row["raw_return"] for row in rows),
                    "regime": selected[0]["regime"],
                })
            returns = [row["mean_raw_return"] for row in daily]
            excess = [row["mean_excess_return"] for row in daily]
            universe_returns = [row["universe_mean_raw_return"] for row in daily]
            universe_excess = [row["universe_mean_excess_return"] for row in daily]
            daily_ics = [
                value for scores, labels_today in daily_rank_scores
                if (value := _spearman(scores, labels_today)) is not None
            ]
            daily_ndcgs = [
                value for scores, labels_today in daily_rank_scores
                if (value := _ndcg(scores, labels_today, top_k)) is not None
            ]
            turnovers: list[float] = []
            turnover_by_date: dict[str, float] = {}
            prior: set[str] | None = None
            for day, selected in selected_by_date.items():
                current = set(selected)
                turnover = (
                    1.0 - len(prior & current) / max(len(prior), len(current), 1)
                    if prior is not None else 0.0
                )
                turnover_by_date[day] = turnover
                turnovers.append(turnover)
                prior = current
            cost_rate = transaction_cost_bps / 10000.0
            net_raw_returns = [
                row["mean_raw_return"] - cost_rate * turnover_by_date.get(row["date"], 0.0)
                for row in daily
            ]
            net_excess_returns = [
                row["mean_excess_return"] - cost_rate * turnover_by_date.get(row["date"], 0.0)
                for row in daily
            ]
            regime_metrics: dict[str, Any] = {}
            for regime in ("risk_on", "mixed", "risk_off"):
                values = [row for row in daily if row["regime"] == regime]
                regime_metrics[regime] = {
                    "date_count": len(values),
                    "mean_raw_return": mean(row["mean_raw_return"] for row in values) if values else None,
                    "mean_excess_return": mean(row["mean_excess_return"] for row in values) if values else None,
                }
            metrics[f"{method}_top{top_k}"] = {
                "date_count": len(daily),
                "mean_raw_return": mean(returns) if returns else None,
                "mean_excess_return": mean(excess) if excess else None,
                "mean_net_raw_return": mean(net_raw_returns) if net_raw_returns else None,
                "mean_net_excess_return": mean(net_excess_returns) if net_excess_returns else None,
                "universe_mean_raw_return": mean(universe_returns) if universe_returns else None,
                "universe_mean_excess_return": mean(universe_excess) if universe_excess else None,
                "lift_vs_universe_raw_return": (
                    mean(returns) - mean(universe_returns) if returns and universe_returns else None
                ),
                "lift_vs_universe_excess_return": (
                    mean(excess) - mean(universe_excess) if excess and universe_excess else None
                ),
                "win_rate": mean(row["win_rate"] for row in daily) if daily else None,
                "turnover": mean(turnovers) if turnovers else None,
                "rank_ic": mean(daily_ics) if daily_ics else None,
                "ndcg": mean(daily_ndcgs) if daily_ndcgs else None,
                "regime": regime_metrics,
            }
    report = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_sha256": dataset["dataset_sha256"],
        "metrics": metrics,
        "rule_gate_threshold": rule_gate_threshold,
        "top_k_values": [int(value) for value in top_k_values],
        "evaluation_start": evaluation_start,
        "evaluation_end": evaluation_end,
        "evaluation_regimes": sorted(requested_regimes),
        "transaction_cost_bps": transaction_cost_bps,
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="industry sector ML evaluation")
    return report


def run_industry_sector_round(
    dataset: Mapping[str, Any],
    *,
    feature_profile: str,
    min_train_dates: int = 60,
    test_dates: int = 10,
    purge_dates: int = 5,
    max_train_dates: int | None = None,
    n_estimators: int = 40,
    learning_rate: float = 0.05,
    num_leaves: int = 15,
    random_state: int = 20260720,
    hypothesis: str | None = None,
    feature_value_mode: str = "raw",
    rule_gate_threshold: float = RULE_GATE_THRESHOLD,
    top_k_values: Sequence[int] = (3, 5, 7),
    evaluation_start: str | None = None,
    evaluation_end: str | None = None,
    evaluation_regimes: Sequence[str] | None = None,
    transaction_cost_bps: float = 0.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    feature_names = feature_names_for_profile(feature_profile)
    records = validate_industry_sector_dataset(dataset)
    train_rows = prepare_round_records(records, feature_names, feature_value_mode=feature_value_mode)
    universe = prepare_round_records(
        dataset["feature_universe_records"], feature_names, feature_value_mode=feature_value_mode
    )
    prediction = walk_forward_ranker_predictions(
        train_rows,
        prediction_universe_records=universe,
        feature_names=feature_names,
        min_train_dates=min_train_dates,
        test_dates=test_dates,
        purge_dates=purge_dates,
        max_train_dates=max_train_dates,
        max_label_horizon=5,
        n_estimators=n_estimators,
        relevance_levels=5,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        random_state=random_state,
    )
    if prediction.get("status") != "ok":
        raise ValueError(f"industry sector walk-forward blocked: {prediction.get('reason')}")
    document = {
        **prediction,
        "schema_version": PREDICTION_SCHEMA_VERSION,
        "dataset_classification": CLASSIFICATION,
        "feature_profile": feature_profile,
        "experiment": {
            "hypothesis": hypothesis or "unregistered industry-sector shadow configuration",
            "feature_profile": feature_profile,
            "max_train_dates": max_train_dates,
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "num_leaves": num_leaves,
            "random_state": random_state,
            "min_train_dates": min_train_dates,
            "test_dates": test_dates,
            "purge_dates": purge_dates,
            "feature_value_mode": feature_value_mode,
            "rule_gate_threshold": rule_gate_threshold,
            "top_k_values": list(top_k_values),
            "evaluation_start": evaluation_start,
            "evaluation_end": evaluation_end,
            "evaluation_regimes": list(evaluation_regimes) if evaluation_regimes else None,
            "transaction_cost_bps": transaction_cost_bps,
        },
        "dataset_sha256": dataset["dataset_sha256"],
        "prediction_rows_sha256": canonical_sha256(prediction["predictions"]),
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
    }
    validate_shadow_prediction_fields(document)
    validate_no_executable_instructions(document, context="industry sector ML predictions")
    evaluation = evaluate_industry_sector_shadow(
        dataset,
        document,
        rule_gate_threshold=rule_gate_threshold,
        top_k_values=top_k_values,
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
        evaluation_regimes=evaluation_regimes,
        transaction_cost_bps=transaction_cost_bps,
    )
    return document, evaluation


def write_industry_sector_model_artifact(
    model: Any,
    output_dir: Path | str,
    *,
    dataset_sha256: str,
    feature_profile: str,
    experiment: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    model_path = output / "model.txt"
    model.booster.save_model(str(model_path))
    model_sha = _sha256(model_path)
    registry = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": CLASSIFICATION,
        "feature_profile": feature_profile,
        "feature_names": list(feature_names_for_profile(feature_profile)),
        "dataset_sha256": dataset_sha256,
        "experiment": dict(experiment or {}),
        "model_artifact": {"path": "model.txt", "sha256": model_sha},
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(registry, context="industry sector ML model registry")
    registry_path = output / "registry.json"
    write_strict_json_atomic(registry_path, registry)
    return {
        "registry_path": str(registry_path.resolve()),
        "registry_sha256": _sha256(registry_path),
        "model_path": str(model_path.resolve()),
        "model_sha256": model_sha,
    }
