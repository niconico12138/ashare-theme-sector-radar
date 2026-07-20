"""Immutable prospective raw-feature capture for the stock ML shadow."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .contract import canonical_sha256
from .historical_factor_source_rebuild import FORBIDDEN_FIELDS
from .schema import DISCLAIMER, MODE


SOURCE_SCHEMA_VERSION = "ml-stock-prospective-source-v1"
CAPTURE_REQUEST_SCHEMA_VERSION = "ml-stock-prospective-capture-request-v1"
DAILY_SNAPSHOT_SCHEMA_VERSION = "ml-stock-prospective-daily-snapshot-v1"
SCHEMA_A_VERSION = "ml-stock-prospective-schema-a-v1"
SCHEMA_B_VERSION = "ml-stock-prospective-schema-b-v1"
DAILY_MANIFEST_SCHEMA_VERSION = "ml-stock-prospective-daily-manifest-v1"
ARCHIVE_INDEX_SCHEMA_VERSION = "ml-stock-prospective-archive-index-v1"
REPORT_SCHEMA_VERSION = "ml-stock-prospective-readiness-v1"

SOURCE_TYPES = (
    "candidate_pool",
    "factor_snapshot",
    "bars_1m_identity",
    "bars_1d_identity",
    "sector_membership",
    "direction_inputs",
    "linkage_v2_inputs",
    "trading_calendar",
    "calculation_contract",
    "stock_event_adjustment",
    "stock_event_features",
)
CORE_SOURCE_TYPES = frozenset(
    {
        "candidate_pool",
        "factor_snapshot",
        "bars_1m_identity",
        "bars_1d_identity",
        "sector_membership",
        "trading_calendar",
        "calculation_contract",
    }
)
OPTIONAL_FACTOR_SOURCE_TYPES = frozenset({"direction_inputs", "linkage_v2_inputs"})
OPTIONAL_EVENT_SOURCE_TYPES = frozenset(
    {"stock_event_adjustment", "stock_event_features"}
)

RAW_FEATURE_FAMILIES: dict[str, tuple[str, ...]] = {
    "technical_price_structure": (
        "ma20_slope_5",
        "relative_strength_20",
        "relative_strength_60",
        "risk_adjusted_return_20",
    ),
    "support_resistance": (
        "near_high_250",
        "drawdown_depth_20",
        "breakout_distance_20",
        "close_strength_score",
    ),
    "volume_liquidity": (
        "amount_ratio_20",
        "liquidity_score",
        "volume_stability_score",
        "volume_burst_quality_score",
    ),
    "volatility_risk": (
        "atr10_atr50",
        "chasing_risk_score",
        "intraday_reversal_risk_score",
        "single_name_overheat_score",
    ),
    "sector_context": ("sector_support_score",),
}
RAW_FEATURE_NAMES = tuple(
    feature
    for family in RAW_FEATURE_FAMILIES.values()
    for feature in family
)
FEATURE_FAMILY_BY_NAME = {
    feature: family
    for family, features in RAW_FEATURE_FAMILIES.items()
    for feature in features
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PROTECTED_FIELDS = frozenset(
    set(FORBIDDEN_FIELDS)
    | {
        "direction_score_shadow",
        "linkage_selection_score",
        "quant_baseline_score_shadow",
        "linkage_v2_baseline_score_shadow",
        "ml_quant_score_shadow",
        "training_label",
        "training_label_end_date",
    }
)
_FUTURE_CONTROL_FIELDS = frozenset({"future_comparison_ready"})


def _capture_now() -> datetime:
    return datetime.now().astimezone()


def _safe_flags() -> dict[str, bool]:
    return {
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }


def _canonical_date(value: Any, *, context: str) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{context} must be a canonical ISO date") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{context} must be a canonical ISO date")
    return text


def _aware_datetime(value: Any, *, context: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError as exc:
        raise ValueError(f"{context} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{context} must be timezone-aware")
    return parsed


def _physical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _logical_artifact(core: Mapping[str, Any], field: str) -> dict[str, Any]:
    return {**dict(core), field: canonical_sha256(core), "disclaimer": DISCLAIMER}


def _reject_protected_fields(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if (
                key in _PROTECTED_FIELDS
                or (key.startswith("future_") and key not in _FUTURE_CONTROL_FIELDS)
                or key.startswith(("label_", "training_label"))
            ):
                raise ValueError(f"protected or future field rejected: {path}.{raw_key}")
            _reject_protected_fields(child, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_protected_fields(child, path=f"{path}[{index}]")


def _reject_future_values(value: Any, *, as_of_date: str, path: str = "records") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if isinstance(child, str) and (
                key.endswith("_date")
                or key.endswith("_at")
                or key in {"date", "first_date", "last_date", "max_date", "query_end"}
            ):
                try:
                    observed = datetime.fromisoformat(child).date().isoformat()
                except ValueError:
                    observed = _canonical_date(child, context=f"{path}.{raw_key}")
                if observed > as_of_date:
                    raise ValueError(f"future data rejected: {path}.{raw_key}")
            _reject_future_values(child, as_of_date=as_of_date, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_future_values(child, as_of_date=as_of_date, path=f"{path}[{index}]")


def _stock_code(record: Mapping[str, Any], *, context: str) -> str:
    code = str(record.get("stock_code") or record.get("code") or "").zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"{context} stock code is invalid")
    return code


def _unique_codes(records: Sequence[Mapping[str, Any]], *, context: str) -> list[str]:
    codes = [_stock_code(record, context=context) for record in records]
    if len(codes) != len(set(codes)):
        raise ValueError(f"duplicate {context} stock identity")
    return sorted(codes)


def _source_identity_for_missing(
    raw: Mapping[str, Any], *, source_type: str, as_of_date: str
) -> tuple[dict[str, Any], None]:
    status = str(raw.get("status") or "")
    if status not in {"unknown", "blocked"}:
        raise ValueError(f"{source_type} source status is invalid")
    reason = str(raw.get("reason") or "")
    if not reason:
        raise ValueError(f"{source_type} {status} source requires a reason")
    if raw.get("value") is not None and raw.get("value") != "":
        raise ValueError(f"{source_type} missing source cannot carry a replacement value")
    return (
        {
            "source_type": source_type,
            "status": status,
            "as_of_date": as_of_date,
            "available_at": None,
            "path": None,
            "sha256": None,
            "source_version": None,
            "reason": reason,
        },
        None,
    )


def _load_observed_source(
    raw: Mapping[str, Any],
    *,
    source_type: str,
    as_of_date: str,
    captured_at: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(str(raw.get("path") or ""))
    sha256 = str(raw.get("sha256") or "").lower()
    if not path.is_absolute() or not path.is_file() or not _SHA256.fullmatch(sha256):
        raise ValueError(f"{source_type} observed source requires an absolute path and SHA")
    if _physical_sha256(path) != sha256:
        raise ValueError(f"{source_type} source SHA mismatch")
    payload, loaded_sha = load_strict_json_with_sha256(path)
    if loaded_sha != sha256 or not isinstance(payload, Mapping):
        raise ValueError(f"{source_type} source payload is invalid")
    source_available_at = _aware_datetime(
        payload.get("available_at"), context=f"{source_type}.available_at"
    )
    if (
        payload.get("schema_version") != SOURCE_SCHEMA_VERSION
        or payload.get("source_type") != source_type
        or payload.get("as_of_date") != as_of_date
        or raw.get("as_of_date") != as_of_date
        or str(raw.get("available_at") or "") != str(payload.get("available_at") or "")
        or str(raw.get("source_version") or "") != str(payload.get("source_version") or "")
    ):
        raise ValueError(f"{source_type} source identity mismatch")
    if source_available_at > captured_at:
        raise ValueError(f"{source_type} available_at is after archive capture")
    if not str(payload.get("source_version") or ""):
        raise ValueError(f"{source_type} source version is required")
    records = payload.get("records")
    if not isinstance(records, list) or any(not isinstance(row, Mapping) for row in records):
        raise ValueError(f"{source_type} source records must be objects")
    _reject_protected_fields(records, path=f"{source_type}.records")
    if source_type != "trading_calendar":
        _reject_future_values(records, as_of_date=as_of_date, path=f"{source_type}.records")
    identity = {
        "source_type": source_type,
        "status": "observed",
        "as_of_date": as_of_date,
        "available_at": source_available_at.isoformat(),
        "path": str(path.resolve()),
        "sha256": sha256,
        "source_version": str(payload["source_version"]),
        "reason": None,
        "records_sha256": canonical_sha256(records),
    }
    return identity, dict(payload)


def _load_sources(
    request: Mapping[str, Any], *, as_of_date: str, captured_at: datetime
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    sources = request.get("sources")
    if not isinstance(sources, Mapping) or set(sources) != set(SOURCE_TYPES):
        raise ValueError("prospective capture source set mismatch")
    identities: dict[str, dict[str, Any]] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for source_type in SOURCE_TYPES:
        raw = sources[source_type]
        if not isinstance(raw, Mapping):
            raise ValueError(f"{source_type} source identity must be an object")
        status = str(raw.get("status") or "")
        if source_type == "stock_event_features" and status == "observed":
            adjustment_identity = identities.get("stock_event_adjustment")
            adjustment_payload = payloads.get("stock_event_adjustment")
            if (
                not isinstance(adjustment_identity, Mapping)
                or adjustment_identity.get("status") != "observed"
                or not isinstance(adjustment_payload, Mapping)
            ):
                raise ValueError(
                    "stock_event_features require an observed stock_event_adjustment manifest"
                )
            _require_approved_event_manifest(adjustment_payload)
        if status == "observed":
            identity, payload = _load_observed_source(
                raw,
                source_type=source_type,
                as_of_date=as_of_date,
                captured_at=captured_at,
            )
            identities[source_type] = identity
            payloads[source_type] = payload
        else:
            identity, _payload = _source_identity_for_missing(
                raw, source_type=source_type, as_of_date=as_of_date
            )
            identities[source_type] = identity
    return identities, payloads


def _require_approved_event_manifest(payload: Mapping[str, Any]) -> None:
    manifest = payload.get("adjustment_manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("stock_event_adjustment approved manifest is missing")
    if manifest.get("review_status") != "approved":
        raise ValueError("unreviewed stock_event_adjustment manifest rejected")
    manifest_sha256 = str(manifest.get("manifest_sha256") or "")
    if not _SHA256.fullmatch(manifest_sha256):
        raise ValueError("approved stock_event_adjustment manifest SHA is invalid")
    if manifest.get("enabled") is not False:
        raise ValueError("stock_event_adjustment must remain disabled in prospective capture")


def _validate_calendar(payload: Mapping[str, Any], *, as_of_date: str) -> tuple[list[str], str]:
    records = payload.get("records") or []
    dates = []
    for record in records:
        if record.get("is_trading_day") is not True:
            continue
        dates.append(_canonical_date(record.get("date"), context="trading calendar date"))
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("trading calendar must be sorted and unique")
    if as_of_date not in dates:
        raise ValueError("trading calendar does not contain as_of_date")
    position = dates.index(as_of_date)
    target_5d = dates[position + 5] if len(dates) > position + 5 else ""
    return dates, target_5d


def _validate_source_coverage(
    *,
    as_of_date: str,
    identities: Mapping[str, Mapping[str, Any]],
    payloads: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[str], str]:
    candidate_payload = payloads.get("candidate_pool")
    if not isinstance(candidate_payload, Mapping):
        raise ValueError("candidate_pool must be observed for daily capture")
    candidate_records = list(candidate_payload.get("records") or [])
    candidate_codes = _unique_codes(candidate_records, context="candidate pool")
    if not candidate_codes:
        raise ValueError("candidate pool is empty")

    factor_payload = payloads.get("factor_snapshot")
    if not isinstance(factor_payload, Mapping):
        raise ValueError("factor_snapshot must be observed for daily capture")
    factor_codes = _unique_codes(
        list(factor_payload.get("records") or []), context="factor snapshot"
    )
    if factor_codes != candidate_codes:
        raise ValueError("factor snapshot candidate coverage mismatch")

    for source_type in ("bars_1m_identity", "bars_1d_identity"):
        payload = payloads.get(source_type)
        if not isinstance(payload, Mapping):
            raise ValueError(f"{source_type} must be observed for daily capture")
        if _unique_codes(list(payload.get("records") or []), context=source_type) != candidate_codes:
            raise ValueError(f"{source_type} candidate coverage mismatch")

    membership = payloads.get("sector_membership")
    if not isinstance(membership, Mapping):
        raise ValueError("sector_membership must be observed for daily capture")
    membership_codes = {
        _stock_code(record, context="sector membership")
        for record in membership.get("records") or []
    }
    if not set(candidate_codes).issubset(membership_codes):
        raise ValueError("sector membership does not cover the candidate pool")

    calculation = payloads.get("calculation_contract")
    if not isinstance(calculation, Mapping) or not calculation.get("records"):
        raise ValueError("calculation_contract must be observed and non-empty")
    calendar = payloads.get("trading_calendar")
    if not isinstance(calendar, Mapping):
        raise ValueError("trading_calendar must be observed for daily capture")
    _calendar_dates, target_5d = _validate_calendar(calendar, as_of_date=as_of_date)

    event_features = payloads.get("stock_event_features")
    if isinstance(event_features, Mapping):
        adjustment = payloads.get("stock_event_adjustment")
        if not isinstance(adjustment, Mapping):
            raise ValueError("stock_event_features require stock_event_adjustment")
        _require_approved_event_manifest(adjustment)
        if _unique_codes(
            list(event_features.get("records") or []), context="stock event features"
        ) != candidate_codes:
            raise ValueError("stock event features candidate coverage mismatch")

    missing_optional = [
        source_type
        for source_type in sorted(OPTIONAL_FACTOR_SOURCE_TYPES)
        if identities[source_type]["status"] != "observed"
    ]
    return candidate_codes, missing_optional, target_5d


def _finite_or_none(value: Any, *, context: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be numeric or null")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{context} must be finite or null")
    return result


def _build_schema_rows(
    *,
    as_of_date: str,
    factor_payload: Mapping[str, Any],
    factor_identity: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    schema_a_rows: list[dict[str, Any]] = []
    schema_b_rows: list[dict[str, Any]] = []
    for raw in factor_payload.get("records") or []:
        code = _stock_code(raw, context="factor snapshot")
        features = raw.get("features")
        if not isinstance(features, Mapping):
            raise ValueError(f"factor features are missing: {code}")
        unknown_features = set(features) - set(RAW_FEATURE_NAMES)
        if unknown_features:
            raise ValueError(f"unregistered raw feature rejected: {sorted(unknown_features)}")
        max_dates = raw.get("feature_max_dates")
        if not isinstance(max_dates, Mapping):
            max_dates = {}
        normalized_features: dict[str, float | None] = {}
        missing: dict[str, bool] = {}
        normalized_max_dates: dict[str, str | None] = {}
        for feature_name in RAW_FEATURE_NAMES:
            value = _finite_or_none(
                features.get(feature_name), context=f"{code}.{feature_name}"
            )
            is_missing = value is None
            max_date = max_dates.get(feature_name)
            if is_missing:
                if max_date not in {None, ""}:
                    raise ValueError(f"missing feature cannot carry feature_max_date: {code}.{feature_name}")
                normalized_date = None
            else:
                normalized_date = _canonical_date(
                    max_date, context=f"{code}.{feature_name}.feature_max_date"
                )
                if normalized_date > as_of_date:
                    raise ValueError(f"future feature_max_date rejected: {code}.{feature_name}")
            normalized_features[feature_name] = value
            missing[feature_name] = is_missing
            normalized_max_dates[feature_name] = normalized_date
            schema_b_rows.append(
                {
                    "as_of_date": as_of_date,
                    "stock_code": code,
                    "sector_name": str(raw.get("sector_name") or ""),
                    "feature_name": feature_name,
                    "feature_family": FEATURE_FAMILY_BY_NAME[feature_name],
                    "value": value,
                    "missing": is_missing,
                    "feature_max_date": normalized_date,
                    "source_ref": {
                        "path": factor_identity["path"],
                        "sha256": factor_identity["sha256"],
                        "available_at": factor_identity["available_at"],
                        "source_version": factor_identity["source_version"],
                    },
                    "eligibility_state": "missing" if is_missing else "prospective_observed",
                }
            )
        schema_a_rows.append(
            {
                "as_of_date": as_of_date,
                "stock_code": code,
                "sector_name": str(raw.get("sector_name") or ""),
                "features": normalized_features,
                "missing_indicators": missing,
                "feature_max_dates": normalized_max_dates,
                "source_ref": {
                    "path": factor_identity["path"],
                    "sha256": factor_identity["sha256"],
                    "available_at": factor_identity["available_at"],
                    "source_version": factor_identity["source_version"],
                },
                "eligibility_state": (
                    "partial_missing_raw_features" if any(missing.values()) else "prospective_observed"
                ),
            }
        )
    schema_a_rows.sort(key=lambda row: row["stock_code"])
    schema_b_rows.sort(key=lambda row: (row["stock_code"], row["feature_name"]))
    return schema_a_rows, schema_b_rows


def _merge_event_feature_rows(
    *,
    as_of_date: str,
    schema_a_rows: list[dict[str, Any]],
    schema_b_rows: list[dict[str, Any]],
    event_payload: Mapping[str, Any],
    event_identity: Mapping[str, Any],
    adjustment_payload: Mapping[str, Any],
) -> list[str]:
    by_code = {str(row["stock_code"]): row for row in schema_a_rows}
    event_names: set[str] = set()
    seen_codes: set[str] = set()
    for raw in event_payload.get("records") or []:
        code = _stock_code(raw, context="stock event features")
        if code in seen_codes:
            raise ValueError(f"duplicate stock event feature identity: {code}")
        seen_codes.add(code)
        if code not in by_code:
            raise ValueError(f"stock event feature is outside candidate pool: {code}")
        features = raw.get("features")
        if not isinstance(features, Mapping):
            raise ValueError(f"stock event features are missing: {code}")
        names = {str(name) for name in features}
        if any(not name.startswith("event_") for name in names):
            raise ValueError(f"stock event feature name is not event-prefixed: {code}")
        event_names.update(names)
        normalized: dict[str, float | None] = {}
        missing: dict[str, bool] = {}
        max_dates = raw.get("feature_max_dates")
        max_dates = max_dates if isinstance(max_dates, Mapping) else {}
        for name in sorted(names):
            value = _finite_or_none(features.get(name), context=f"{code}.{name}")
            max_date = max_dates.get(name)
            if value is None:
                if max_date not in {None, ""}:
                    raise ValueError(f"missing event feature has a max date: {code}.{name}")
                normalized_date = None
            else:
                normalized_date = _canonical_date(
                    max_date, context=f"{code}.{name}.feature_max_date"
                )
                if normalized_date > as_of_date:
                    raise ValueError(f"future event feature max date rejected: {code}.{name}")
            normalized[name] = value
            missing[name] = value is None
            schema_b_rows.append(
                {
                    "as_of_date": as_of_date,
                    "stock_code": code,
                    "sector_name": str(raw.get("sector_name") or ""),
                    "feature_name": name,
                    "feature_family": "stock_event",
                    "value": value,
                    "missing": value is None,
                    "feature_max_date": normalized_date,
                    "source_ref": {
                        "path": event_identity["path"],
                        "sha256": event_identity["sha256"],
                        "available_at": event_identity["available_at"],
                        "source_version": event_identity["source_version"],
                        "adjustment_manifest_sha256": (
                            adjustment_payload["adjustment_manifest"]["manifest_sha256"]
                        ),
                    },
                    "eligibility_state": "missing" if value is None else "prospective_observed",
                }
            )
        row = by_code[code]
        row["event_features"] = normalized
        row["event_missing_indicators"] = missing
        row["event_feature_max_dates"] = {
            name: (
                _canonical_date(max_dates.get(name), context=f"{code}.{name}.feature_max_date")
                if normalized[name] is not None
                else None
            )
            for name in sorted(names)
        }
        row["event_source_ref"] = {
            "path": event_identity["path"],
            "sha256": event_identity["sha256"],
            "available_at": event_identity["available_at"],
            "source_version": event_identity["source_version"],
            "adjustment_manifest_sha256": adjustment_payload["adjustment_manifest"]["manifest_sha256"],
        }
    if seen_codes != set(by_code):
        raise ValueError("stock event features must cover the candidate pool")
    schema_b_rows.sort(key=lambda row: (row["stock_code"], row["feature_name"]))
    return sorted(event_names)


def _write_or_verify(path: Path, artifact: Mapping[str, Any]) -> tuple[str, bool]:
    if path.exists():
        existing, sha256 = load_strict_json_with_sha256(path)
        if existing != dict(artifact):
            raise ValueError(f"immutable artifact revision rejected: {path.name}")
        return sha256, False
    write_strict_json_atomic(path, dict(artifact))
    _loaded, sha256 = load_strict_json_with_sha256(path)
    return sha256, True


def capture_prospective_daily_snapshot(
    *, archive_root: Path | str, request: Mapping[str, Any]
) -> dict[str, Any]:
    """Capture one same-day raw snapshot; no model or score is produced."""

    captured_at = _capture_now()
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("archive capture clock must be timezone-aware")
    if request.get("schema_version") != CAPTURE_REQUEST_SCHEMA_VERSION:
        raise ValueError("prospective capture request schema mismatch")
    as_of_date = _canonical_date(request.get("as_of_date"), context="capture as_of_date")
    if captured_at.date().isoformat() != as_of_date:
        raise ValueError("prospective capture must occur on as_of_date; backfill is forbidden")
    _reject_protected_fields(request, path="capture_request")
    identities, payloads = _load_sources(
        request, as_of_date=as_of_date, captured_at=captured_at
    )
    candidate_codes, missing_optional, target_5d = _validate_source_coverage(
        as_of_date=as_of_date, identities=identities, payloads=payloads
    )
    schema_a_rows, schema_b_rows = _build_schema_rows(
        as_of_date=as_of_date,
        factor_payload=payloads["factor_snapshot"],
        factor_identity=identities["factor_snapshot"],
    )
    event_feature_names: list[str] = []
    if isinstance(payloads.get("stock_event_features"), Mapping):
        event_feature_names = _merge_event_feature_rows(
            as_of_date=as_of_date,
            schema_a_rows=schema_a_rows,
            schema_b_rows=schema_b_rows,
            event_payload=payloads["stock_event_features"],
            event_identity=identities["stock_event_features"],
            adjustment_payload=payloads["stock_event_adjustment"],
        )
    if [row["stock_code"] for row in schema_a_rows] != candidate_codes:
        raise ValueError("Schema A candidate identity mismatch")

    source_status_counts = Counter(identity["status"] for identity in identities.values())
    observed_feature_count = sum(
        not row["missing"] for row in schema_b_rows
    )
    expected_feature_count = len(schema_b_rows)
    data_quality_status = "ready" if not missing_optional else "partial"
    quality_reasons = [f"{source_type}_unknown_or_blocked" for source_type in missing_optional]
    if observed_feature_count != expected_feature_count:
        data_quality_status = "partial"
        quality_reasons.append("raw_feature_coverage_incomplete")
    prospective_pit_eligible = not missing_optional and bool(target_5d)
    if not target_5d:
        data_quality_status = "blocked"
        quality_reasons.append("trading_calendar_missing_5d_target")
        prospective_pit_eligible = False

    immutable_input = {
        "as_of_date": as_of_date,
        "sources": identities,
        "source_payload_sha256": {
            source_type: canonical_sha256(payload)
            for source_type, payload in sorted(payloads.items())
        },
        "schema_a_rows": schema_a_rows,
        "schema_b_rows": schema_b_rows,
        "target_5d": target_5d or None,
    }
    immutable_input_sha256 = canonical_sha256(immutable_input)
    root = Path(archive_root).resolve()
    day_root = root / "daily" / as_of_date
    manifest_path = day_root / "manifest.json"
    if manifest_path.exists():
        existing, existing_sha = load_strict_json_with_sha256(manifest_path)
        if existing.get("immutable_input_sha256") != immutable_input_sha256:
            raise ValueError("immutable daily snapshot revision rejected")
        verify_prospective_archive(root)
        return {
            "created": False,
            "as_of_date": as_of_date,
            "manifest_path": str(manifest_path),
            "manifest_sha256": existing_sha,
            "manifest": existing,
        }
    if day_root.exists() and any(day_root.iterdir()):
        raise ValueError("partial daily archive directory exists")

    index_path = root / "index.json"
    entries: list[dict[str, Any]] = []
    if index_path.exists():
        index, _index_sha = load_strict_json_with_sha256(index_path)
        if index.get("schema_version") != ARCHIVE_INDEX_SCHEMA_VERSION:
            raise ValueError("prospective archive index schema mismatch")
        entries = list(index.get("entries") or [])
        if entries and str(entries[-1].get("as_of_date") or "") >= as_of_date:
            raise ValueError("prospective archive requires strictly increasing trading dates")

    schema_a_core = {
        "schema_version": SCHEMA_A_VERSION,
        "mode": MODE,
        "status": "raw_features_only",
        "as_of_date": as_of_date,
        "row_count": len(schema_a_rows),
        "feature_names": list(RAW_FEATURE_NAMES),
        "event_feature_names": event_feature_names,
        "rows": schema_a_rows,
        **_safe_flags(),
    }
    schema_b_core = {
        "schema_version": SCHEMA_B_VERSION,
        "mode": MODE,
        "status": "raw_features_only",
        "as_of_date": as_of_date,
        "row_count": len(schema_b_rows),
        "rows": schema_b_rows,
        **_safe_flags(),
    }
    schema_a = _logical_artifact(schema_a_core, "schema_a_sha256")
    schema_b = _logical_artifact(schema_b_core, "schema_b_sha256")
    validate_no_executable_instructions(schema_a, context="prospective Schema A")
    validate_no_executable_instructions(schema_b, context="prospective Schema B")
    schema_a_path = day_root / "schema_a.json"
    schema_b_path = day_root / "schema_b.json"
    schema_a_file_sha, _ = _write_or_verify(schema_a_path, schema_a)
    schema_b_file_sha, _ = _write_or_verify(schema_b_path, schema_b)

    snapshot_core = {
        "schema_version": DAILY_SNAPSHOT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "captured_raw_only",
        "as_of_date": as_of_date,
        "captured_at": captured_at.isoformat(),
        "candidate_count": len(candidate_codes),
        "candidate_codes": candidate_codes,
        "source_manifest": identities,
        "source_payloads": payloads,
        "feature_observation_count": observed_feature_count,
        "feature_expected_count": expected_feature_count,
        "feature_coverage_ratio": (
            observed_feature_count / expected_feature_count if expected_feature_count else 0.0
        ),
        "target_5d": target_5d or None,
        "data_quality_status": data_quality_status,
        "data_quality_reasons": quality_reasons,
        "prospective_pit_eligible": prospective_pit_eligible,
        "immutable_input_sha256": immutable_input_sha256,
        "schema_artifacts": {
            "schema_a": {"path": "schema_a.json", "sha256": schema_a_file_sha},
            "schema_b": {"path": "schema_b.json", "sha256": schema_b_file_sha},
        },
        **_safe_flags(),
    }
    snapshot = _logical_artifact(snapshot_core, "snapshot_sha256")
    validate_no_executable_instructions(snapshot, context="prospective daily snapshot")
    snapshot_path = day_root / "snapshot.json"
    snapshot_file_sha, _ = _write_or_verify(snapshot_path, snapshot)

    manifest_core = {
        "schema_version": DAILY_MANIFEST_SCHEMA_VERSION,
        "mode": MODE,
        "status": "captured_raw_only",
        "as_of_date": as_of_date,
        "captured_at": captured_at.isoformat(),
        "immutable_input_sha256": immutable_input_sha256,
        "data_quality_status": data_quality_status,
        "prospective_pit_eligible": prospective_pit_eligible,
        "source_status_counts": dict(sorted(source_status_counts.items())),
        "target_5d": target_5d or None,
        "artifacts": {
            "snapshot": {"path": "snapshot.json", "sha256": snapshot_file_sha},
            "schema_a": {"path": "schema_a.json", "sha256": schema_a_file_sha},
            "schema_b": {"path": "schema_b.json", "sha256": schema_b_file_sha},
        },
        **_safe_flags(),
    }
    manifest = _logical_artifact(manifest_core, "daily_manifest_sha256")
    validate_no_executable_instructions(manifest, context="prospective daily manifest")
    manifest_file_sha, _ = _write_or_verify(manifest_path, manifest)

    previous = entries[-1]["entry_sha256"] if entries else None
    entry_core = {
        "as_of_date": as_of_date,
        "manifest_path": str(manifest_path.relative_to(root)),
        "manifest_sha256": manifest_file_sha,
        "previous_entry_sha256": previous,
    }
    entries.append({**entry_core, "entry_sha256": canonical_sha256(entry_core)})
    index_core = {
        "schema_version": ARCHIVE_INDEX_SCHEMA_VERSION,
        "mode": MODE,
        "status": "active_raw_capture_only",
        "entry_count": len(entries),
        "chain_head_sha256": entries[-1]["entry_sha256"],
        "entries": entries,
        **_safe_flags(),
    }
    index = _logical_artifact(index_core, "index_sha256")
    validate_no_executable_instructions(index, context="prospective archive index")
    write_strict_json_atomic(index_path, index)
    verify_prospective_archive(root)
    return {
        "created": True,
        "as_of_date": as_of_date,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_file_sha,
        "manifest": manifest,
    }


def _validate_logical_sha(artifact: Mapping[str, Any], field: str, *, context: str) -> None:
    core = {key: value for key, value in artifact.items() if key not in {field, "disclaimer"}}
    if artifact.get(field) != canonical_sha256(core):
        raise ValueError(f"{context} logical SHA mismatch")
    if any(artifact.get(key) is not False for key in _safe_flags()):
        raise ValueError(f"{context} safety flags mismatch")
    _reject_protected_fields(artifact, path=context)


def verify_prospective_archive(archive_root: Path | str) -> dict[str, Any]:
    root = Path(archive_root).resolve()
    index_path = root / "index.json"
    if not index_path.exists():
        return {"archive_root": str(root), "entries": [], "entry_count": 0}
    index, index_file_sha = load_strict_json_with_sha256(index_path)
    if index.get("schema_version") != ARCHIVE_INDEX_SCHEMA_VERSION:
        raise ValueError("prospective archive index schema mismatch")
    _validate_logical_sha(index, "index_sha256", context="prospective archive index")
    entries = index.get("entries")
    if not isinstance(entries, list) or index.get("entry_count") != len(entries):
        raise ValueError("prospective archive index count mismatch")
    previous = None
    verified_entries: list[dict[str, Any]] = []
    prior_date = ""
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("prospective archive entry is invalid")
        day = _canonical_date(entry.get("as_of_date"), context="archive entry date")
        if day <= prior_date or entry.get("previous_entry_sha256") != previous:
            raise ValueError("prospective archive chain order mismatch")
        entry_core = {key: value for key, value in entry.items() if key != "entry_sha256"}
        if entry.get("entry_sha256") != canonical_sha256(entry_core):
            raise ValueError("prospective archive entry SHA mismatch")
        manifest_path = root / str(entry.get("manifest_path") or "")
        manifest, manifest_file_sha = load_strict_json_with_sha256(manifest_path)
        if manifest_file_sha != entry.get("manifest_sha256"):
            raise ValueError("prospective daily manifest physical SHA mismatch")
        if manifest.get("as_of_date") != day:
            raise ValueError("prospective daily manifest date mismatch")
        _validate_logical_sha(
            manifest, "daily_manifest_sha256", context="prospective daily manifest"
        )
        day_root = manifest_path.parent
        for name, logical_field in (
            ("snapshot", "snapshot_sha256"),
            ("schema_a", "schema_a_sha256"),
            ("schema_b", "schema_b_sha256"),
        ):
            reference = (manifest.get("artifacts") or {}).get(name)
            if not isinstance(reference, Mapping):
                raise ValueError("prospective daily artifact reference is missing")
            path = day_root / str(reference.get("path") or "")
            artifact, physical_sha = load_strict_json_with_sha256(path)
            if physical_sha != reference.get("sha256"):
                raise ValueError("prospective daily artifact physical SHA mismatch")
            _validate_logical_sha(
                artifact, logical_field, context=f"prospective {name}"
            )
            if artifact.get("as_of_date") != day:
                raise ValueError("prospective daily artifact date mismatch")
        snapshot, _ = load_strict_json_with_sha256(day_root / "snapshot.json")
        for source_type, identity in (snapshot.get("source_manifest") or {}).items():
            if identity.get("status") != "observed":
                continue
            source_path = Path(str(identity.get("path") or ""))
            if not source_path.is_file() or _physical_sha256(source_path) != identity.get("sha256"):
                raise ValueError(f"prospective source changed after capture: {source_type}")
            payload, _ = load_strict_json_with_sha256(source_path)
            if canonical_sha256(payload) != canonical_sha256(
                (snapshot.get("source_payloads") or {}).get(source_type)
            ):
                raise ValueError(f"prospective source payload replay mismatch: {source_type}")
        verified_entries.append(
            {
                "as_of_date": day,
                "manifest_path": str(manifest_path),
                "manifest_sha256": manifest_file_sha,
                "data_quality_status": manifest.get("data_quality_status"),
                "prospective_pit_eligible": manifest.get("prospective_pit_eligible") is True,
                "target_5d": manifest.get("target_5d"),
            }
        )
        previous = str(entry["entry_sha256"])
        prior_date = day
    if previous != index.get("chain_head_sha256"):
        raise ValueError("prospective archive chain head mismatch")
    return {
        "archive_root": str(root),
        "index_path": str(index_path),
        "index_sha256": index_file_sha,
        "entries": verified_entries,
        "entry_count": len(verified_entries),
    }


def build_prospective_archive_reports(
    archive_root: Path | str, *, report_as_of_date: str
) -> dict[str, dict[str, Any]]:
    report_as_of = _canonical_date(report_as_of_date, context="report as_of_date")
    verified = verify_prospective_archive(archive_root)
    root = Path(archive_root).resolve()
    entries = list(verified["entries"])
    source_counts = {source_type: Counter() for source_type in SOURCE_TYPES}
    candidate_rows = 0
    observed_features = 0
    expected_features = 0
    quality_counts = Counter()
    queue: list[dict[str, Any]] = []
    latest_source_by_type: dict[str, dict[str, Any] | None] = {
        source_type: None for source_type in SOURCE_TYPES
    }
    for entry in entries:
        day_root = Path(entry["manifest_path"]).parent
        snapshot, _ = load_strict_json_with_sha256(day_root / "snapshot.json")
        candidate_rows += int(snapshot.get("candidate_count") or 0)
        observed_features += int(snapshot.get("feature_observation_count") or 0)
        expected_features += int(snapshot.get("feature_expected_count") or 0)
        quality_counts[str(snapshot.get("data_quality_status") or "unknown")] += 1
        for source_type in SOURCE_TYPES:
            identity = (snapshot.get("source_manifest") or {}).get(source_type) or {}
            status = str(identity.get("status") or "missing")
            source_counts[source_type][status] += 1
            latest_source_by_type[source_type] = {
                "as_of_date": entry["as_of_date"],
                "status": status,
                "available_at": identity.get("available_at"),
                "path": identity.get("path"),
                "sha256": identity.get("sha256"),
                "source_version": identity.get("source_version"),
                "reason": identity.get("reason"),
            }
        target = str(snapshot.get("target_5d") or "")
        queue.append(
            {
                "signal_date": entry["as_of_date"],
                "target_5d": target or None,
                "status": (
                    "pending_calendar_coverage"
                    if not target
                    else "pending_label_maturity"
                    if report_as_of < target
                    else "mature_unlabeled"
                ),
                "label_capture_allowed": bool(target and report_as_of >= target),
            }
        )
    prospective_dates = sum(entry["prospective_pit_eligible"] for entry in entries)
    mature_unlabeled = sum(row["status"] == "mature_unlabeled" for row in queue)
    snapshot_manifest = _logical_artifact(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "daily_snapshot_manifest",
            "mode": MODE,
            "status": "active" if entries else "awaiting_first_new_trading_day",
            "report_as_of_date": report_as_of,
            "archive_root": str(root),
            "archive_index_sha256": verified.get("index_sha256"),
            "entry_count": len(entries),
            "entries": entries,
            **_safe_flags(),
        },
        "report_sha256",
    )
    coverage = _logical_artifact(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "coverage",
            "mode": MODE,
            "status": "collecting" if entries else "awaiting_first_new_trading_day",
            "report_as_of_date": report_as_of,
            "snapshot_dates": len(entries),
            "candidate_rows": candidate_rows,
            "prospective_pit_snapshot_dates": prospective_dates,
            "source_status_by_type": {
                source_type: dict(sorted(counts.items()))
                for source_type, counts in source_counts.items()
            },
            "feature_observation_count": observed_features,
            "feature_expected_count": expected_features,
            "feature_coverage_ratio": (
                observed_features / expected_features if expected_features else 0.0
            ),
            **_safe_flags(),
        },
        "report_sha256",
    )
    queue_report = _logical_artifact(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "label_maturity_queue",
            "mode": MODE,
            "status": "active" if entries else "empty",
            "report_as_of_date": report_as_of,
            "queue": queue,
            "pending_count": sum(row["status"] == "pending_label_maturity" for row in queue),
            "mature_unlabeled_count": mature_unlabeled,
            **_safe_flags(),
        },
        "report_sha256",
    )
    readiness_reasons = []
    if not entries:
        readiness_reasons.append("no_prospective_snapshot_dates")
    if prospective_dates != len(entries):
        readiness_reasons.append("incomplete_daily_source_coverage")
    if len(entries) < 60:
        readiness_reasons.append("minimum_60_prospective_dates_not_met")
    if any(row["status"] != "mature_unlabeled" for row in queue):
        readiness_reasons.append("five_day_labels_not_mature")
    readiness_reasons.append("mature_labels_not_archived_by_this_capture_stage")
    readiness = _logical_artifact(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "readiness",
            "mode": MODE,
            "status": "blocked",
            "report_as_of_date": report_as_of,
            "future_comparison_ready": False,
            "model_training_allowed": False,
            "snapshot_dates": len(entries),
            "prospective_pit_snapshot_dates": prospective_dates,
            "mature_unlabeled_dates": mature_unlabeled,
            "blocking_reasons": sorted(set(readiness_reasons)),
            **_safe_flags(),
        },
        "report_sha256",
    )
    data_quality = _logical_artifact(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "data_quality",
            "mode": MODE,
            "status": (
                "awaiting_first_new_trading_day"
                if not entries
                else "ready"
                if quality_counts == {"ready": len(entries)}
                else "partial_or_blocked"
            ),
            "report_as_of_date": report_as_of,
            "daily_status_counts": dict(sorted(quality_counts.items())),
            "direction_missing_dates": source_counts["direction_inputs"].get("unknown", 0)
            + source_counts["direction_inputs"].get("blocked", 0),
            "linkage_v2_missing_dates": source_counts["linkage_v2_inputs"].get("unknown", 0)
            + source_counts["linkage_v2_inputs"].get("blocked", 0),
            "stock_event_features_missing_dates": source_counts["stock_event_features"].get("unknown", 0)
            + source_counts["stock_event_features"].get("blocked", 0),
            "stock_event_adjustment_missing_dates": source_counts["stock_event_adjustment"].get("unknown", 0)
            + source_counts["stock_event_adjustment"].get("blocked", 0),
            "missing_value_policy": "unknown remains null with explicit missing indicator; no zero backfill",
            **_safe_flags(),
        },
        "report_sha256",
    )
    source_status = _logical_artifact(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "daily_source_status",
            "mode": MODE,
            "status": "awaiting_first_new_trading_day" if not entries else "active",
            "report_as_of_date": report_as_of,
            "sources": {
                source_type: {
                    "observed_dates": counts.get("observed", 0),
                    "unknown_dates": counts.get("unknown", 0),
                    "blocked_dates": counts.get("blocked", 0),
                    "status": (
                        "observed"
                        if counts.get("observed", 0) == len(entries) and entries
                        else "unknown_or_blocked"
                    ),
                    "latest": latest_source_by_type[source_type],
                }
                for source_type, counts in source_counts.items()
            },
            "refresh_policy": "latest verified daily manifest only; no historical source backfill",
            **_safe_flags(),
        },
        "report_sha256",
    )
    reports = {
        "daily_snapshot_manifest": snapshot_manifest,
        "coverage_report": coverage,
        "label_maturity_queue": queue_report,
        "readiness_report": readiness,
        "data_quality_status": data_quality,
        "source_status_report": source_status,
    }
    for name, report in reports.items():
        validate_no_executable_instructions(report, context=f"prospective {name}")
    return reports


def write_prospective_archive_reports(
    archive_root: Path | str,
    output_root: Path | str,
    *,
    report_as_of_date: str,
) -> dict[str, Any]:
    reports = build_prospective_archive_reports(
        archive_root, report_as_of_date=report_as_of_date
    )
    destination = Path(output_root).resolve()
    artifacts: dict[str, dict[str, str]] = {}
    for name, report in reports.items():
        path = destination / f"{name}.json"
        write_strict_json_atomic(path, report)
        artifacts[name] = {
            "path": str(path),
            "sha256": _physical_sha256(path),
            "logical_sha256": str(report["report_sha256"]),
        }
    return {
        "status": reports["readiness_report"]["status"],
        "future_comparison_ready": False,
        "artifacts": artifacts,
    }


def validate_prospective_report_artifacts(
    archive_root: Path | str,
    output_root: Path | str,
    *,
    report_as_of_date: str,
) -> dict[str, Any]:
    expected = build_prospective_archive_reports(
        archive_root, report_as_of_date=report_as_of_date
    )
    destination = Path(output_root).resolve()
    expected_files = {f"{name}.json" for name in expected}
    actual_files = {path.name for path in destination.iterdir() if path.is_file()}
    if actual_files != expected_files or any(path.is_dir() for path in destination.iterdir()):
        raise ValueError("prospective report artifact file contract mismatch")
    physical_sha256: dict[str, str] = {}
    for name, rebuilt in expected.items():
        path = destination / f"{name}.json"
        stored, physical_sha = load_strict_json_with_sha256(path)
        _validate_logical_sha(stored, "report_sha256", context=f"prospective {name}")
        if stored != rebuilt:
            raise ValueError(f"prospective {name} does not reproduce from archive")
        physical_sha256[name] = physical_sha
    return {
        "report_as_of_date": report_as_of_date,
        "snapshot_dates": expected["coverage_report"]["snapshot_dates"],
        "candidate_rows": expected["coverage_report"]["candidate_rows"],
        "future_comparison_ready": False,
        "physical_sha256": physical_sha256,
    }
