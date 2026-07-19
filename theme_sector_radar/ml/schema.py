"""Frozen schemas for the ML stock-ranker shadow path."""

from __future__ import annotations

import hashlib
import json


FEATURE_SCHEMA_VERSION = "ml-stock-features-v1"
OUTPUT_SCHEMA_VERSION = "ml-stock-shadow-output-v1"
DATASET_SCHEMA_VERSION = "ml-stock-dataset-v1"
LABEL_SCHEMA_VERSION = "ml-stock-forward-labels-v1"
MODEL_REGISTRY_SCHEMA_VERSION = "ml-stock-model-registry-v1"
MODE = "paper_shadow_research_only"
DISCLAIMER = "Research output only; no broker connection and no live order instruction."
LABEL_DEFINITION = "future_5d_stock_return_minus_same_sector_return"
MODEL_MAX_AGE_DAYS = 45

V1_FEATURE_NAMES = (
    "momentum_1d",
    "momentum_3d",
    "momentum_5d",
    "momentum_10d",
    "momentum_20d",
    "ma5_distance",
    "ma10_distance",
    "ma20_distance",
    "volume_ratio_5_20",
    "log_avg_amount_5d",
    "volatility_5d",
    "volatility_20d",
    "max_drawdown_20d",
    "pe",
    "pb",
    "log_market_cap",
    "pe_sector_relative",
    "pb_sector_relative",
    "market_cap_sector_percentile",
    "sector_trend_score",
    "sector_burst_score",
    "sector_direction_score",
    "linkage_comovement_20d",
    "linkage_relative_strength_5d",
    "linkage_relative_strength_10d",
    "linkage_weight",
    "linkage_fund_flow",
    "linkage_data_quality",
    "data_quality_score",
    "factor_coverage",
    "missing_valuation",
    "missing_sector_context",
    "missing_linkage",
    "missing_amount",
)

FUTURE_OR_LABEL_FIELD_PREFIXES = (
    "future",
    "forward",
)

FUTURE_OR_LABEL_FIELD_NAMES = frozenset({
    "label",
    "labels",
    "label_date",
    "label_dates",
    "target",
    "targets",
    "outcome",
    "outcomes",
    "training_label",
    "training_label_end_date",
})

FORBIDDEN_FEATURE_KEY_FRAGMENTS = (
    *FUTURE_OR_LABEL_FIELD_PREFIXES,
    *tuple(FUTURE_OR_LABEL_FIELD_NAMES),
    "final_score",
    "quant_score",
    "v2_score",
    "selection_score",
)


def feature_schema_sha256(feature_names: tuple[str, ...] = V1_FEATURE_NAMES) -> str:
    payload = {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "feature_names": list(feature_names),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
