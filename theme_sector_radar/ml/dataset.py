"""Strict identity join and manifests for ML shadow training data."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contract import canonical_sha256, require_finite
from .schema import (
    DATASET_SCHEMA_VERSION,
    DISCLAIMER,
    FEATURE_SCHEMA_VERSION,
    FORBIDDEN_FEATURE_KEY_FRAGMENTS,
    LABEL_DEFINITION,
    MODE,
    V1_FEATURE_NAMES,
    feature_schema_sha256,
)
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256


def _identity(row: Mapping[str, Any], *, context: str) -> tuple[str, str]:
    day = str(row.get("as_of_date") or "")
    code = str(row.get("stock_code") or "").zfill(6)
    if len(day) != 10 or len(code) != 6 or not code.isdigit():
        raise ValueError(f"{context} has invalid (as_of_date, stock_code) identity")
    return day, code


def _index_unique(
    rows: Sequence[Mapping[str, Any]], *, context: str
) -> dict[tuple[str, str], Mapping[str, Any]]:
    indexed: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        identity = _identity(row, context=context)
        if identity in indexed:
            raise ValueError(f"duplicate {context} identity: {identity[0]} {identity[1]}")
        indexed[identity] = row
    return indexed


def _validated_features(row: Mapping[str, Any]) -> dict[str, float]:
    if row.get("schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("feature schema version mismatch")
    raw = row.get("features")
    if not isinstance(raw, Mapping):
        raise ValueError("feature row is missing features")
    if tuple(raw) != V1_FEATURE_NAMES:
        raise ValueError("feature order/schema mismatch")
    for name in raw:
        lowered = name.casefold()
        if any(fragment in lowered for fragment in FORBIDDEN_FEATURE_KEY_FRAGMENTS):
            raise ValueError(f"forbidden feature name: {name}")
    features = {name: float(raw[name]) for name in V1_FEATURE_NAMES}
    require_finite(features, context="features")
    return features


def _validate_training_label_contract(
    row: Mapping[str, Any], *, as_of_date: str
) -> tuple[dict[str, Any], dict[str, Any], float | None, str | None]:
    labels = row.get("labels")
    label_dates = row.get("label_dates")
    if not isinstance(labels, Mapping) or not isinstance(label_dates, Mapping):
        raise ValueError("label values and dates must be objects")
    labels = dict(labels)
    label_dates = dict(label_dates)
    training_key = "future_excess_return_5d"
    if training_key not in labels or training_key not in label_dates:
        raise ValueError("5-day training label and maturity date are required")
    raw_training = row.get("training_label")
    raw_end = row.get("training_label_end_date")
    expected_training = labels[training_key]
    expected_end = label_dates[training_key]
    if raw_training != expected_training:
        raise ValueError("training label must equal future_excess_return_5d")
    if raw_end != expected_end:
        raise ValueError("training label end date must equal the 5-day label date")
    require_finite(labels, context="labels")
    if expected_training is None:
        if expected_end is not None:
            raise ValueError("missing training label cannot claim a maturity date")
        return labels, label_dates, None, None
    training_label = float(expected_training)
    end_text = str(expected_end or "")
    try:
        parsed_end = date.fromisoformat(end_text)
        parsed_signal = date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise ValueError("training label maturity date is invalid") from exc
    if parsed_end.isoformat() != end_text or parsed_end <= parsed_signal:
        raise ValueError("training label maturity must follow as_of_date")
    require_finite(training_label, context="training_label")
    return labels, label_dates, training_label, end_text


def _safety_envelope(*, fixture_only: bool) -> dict[str, Any]:
    return _safety_envelope_with_pit(
        fixture_only=fixture_only,
        strict_pit_eligible=False,
    )


def _safety_envelope_with_pit(
    *, fixture_only: bool, strict_pit_eligible: bool
) -> dict[str, Any]:
    return {
        "mode": MODE,
        "strict_pit_eligible": bool(strict_pit_eligible),
        "pit_evidence_status": (
            "verified_prospective_archive"
            if strict_pit_eligible
            else "unverified_no_trusted_verifier"
        ),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "fixture_only": bool(fixture_only),
    }


def _validate_pit_evidence_for_rows(
    pit_evidence: Mapping[str, Any],
    *,
    feature_rows: Sequence[Mapping[str, Any]],
    label_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(pit_evidence, Mapping):
        raise ValueError("PIT evidence must be an object")
    core = {key: value for key, value in pit_evidence.items() if key != "evidence_sha256"}
    if canonical_sha256(core) != pit_evidence.get("evidence_sha256"):
        raise ValueError("PIT evidence SHA mismatch")
    if (
        pit_evidence.get("schema_version") != "ml-stock-pit-evidence-v1"
        or pit_evidence.get("mode") != MODE
        or pit_evidence.get("status") != "verified"
        or pit_evidence.get("verifier")
        != "theme_sector_radar.ml.accumulation.verify_accumulation_archive"
        or pit_evidence.get("strict_pit_eligible") is not True
        or pit_evidence.get("minimum_60_dates_satisfied") is not True
    ):
        raise ValueError("PIT evidence is not strict training evidence")
    verified_dates = {
        str(value) for value in pit_evidence.get("verified_training_dates") or []
    }
    feature_dates = {str(row.get("as_of_date") or "") for row in feature_rows}
    label_dates = {str(row.get("as_of_date") or "") for row in label_rows}
    if not feature_dates or not feature_dates.issubset(verified_dates):
        raise ValueError("feature rows are outside verified PIT training dates")
    if not label_dates or not label_dates.issubset(verified_dates):
        raise ValueError("label rows are outside verified PIT training dates")
    archive_root = pit_evidence.get("archive_root")
    if not isinstance(archive_root, str) or not archive_root:
        raise ValueError("PIT evidence archive root is missing")
    from .accumulation import load_verified_training_inputs

    loaded = load_verified_training_inputs(archive_root)
    verified_evidence = loaded["evidence"]
    if verified_evidence.get("evidence_sha256") != pit_evidence.get(
        "evidence_sha256"
    ):
        raise ValueError("PIT evidence is not bound to the verified archive")
    return loaded


def build_training_dataset(
    feature_rows: Sequence[Mapping[str, Any]],
    label_rows: Sequence[Mapping[str, Any]],
    *,
    strict_pit_eligible: bool,
    source_manifest: Mapping[str, Any] | None = None,
    fixture_only: bool = False,
    pit_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Join independently built features and labels without weakening identity."""

    if strict_pit_eligible:
        raise ValueError(
            "self-attested strict PIT is not accepted in ML Shadow Stage 1"
        )
    if fixture_only and pit_evidence is not None:
        raise ValueError("synthetic fixture cannot carry strict PIT evidence")
    strict_pit_verified = pit_evidence is not None
    if pit_evidence is not None:
        loaded = _validate_pit_evidence_for_rows(
            pit_evidence,
            feature_rows=feature_rows,
            label_rows=label_rows,
        )
        if canonical_sha256(list(feature_rows)) != canonical_sha256(
            loaded["feature_rows"]
        ) or canonical_sha256(list(label_rows)) != canonical_sha256(
            loaded["label_rows"]
        ):
            raise ValueError("strict PIT rows do not match the verified archive")
    features_by_id = _index_unique(feature_rows, context="feature")
    labels_by_id = _index_unique(label_rows, context="label")
    feature_universe_records: list[dict[str, Any]] = []
    for identity in sorted(features_by_id):
        feature_row = features_by_id[identity]
        feature_universe_records.append(
            {
                "as_of_date": identity[0],
                "stock_code": identity[1],
                "sector_name": str(feature_row.get("sector_name") or ""),
                "features": _validated_features(feature_row),
                "feature_coverage": float(
                    feature_row.get("feature_coverage")
                    if feature_row.get("feature_coverage") is not None
                    else 0.0
                ),
            }
        )
    records: list[dict[str, Any]] = []
    evaluation_label_records: list[dict[str, Any]] = []
    for identity in sorted(features_by_id.keys() & labels_by_id.keys()):
        feature_row = features_by_id[identity]
        label_row = labels_by_id[identity]
        if str(feature_row.get("sector_name") or "") != str(
            label_row.get("sector_name") or ""
        ):
            raise ValueError(f"sector identity mismatch for {identity[0]} {identity[1]}")
        if label_row.get("label_definition") != LABEL_DEFINITION:
            raise ValueError("label definition mismatch")
        if int(label_row.get("max_label_horizon") or 0) != 5:
            raise ValueError("max label horizon must be 5")
        features = _validated_features(feature_row)
        labels, label_dates, training_label, end_text = (
            _validate_training_label_contract(
                label_row, as_of_date=identity[0]
            )
        )
        evaluation_label_records.append(
            {
                "as_of_date": identity[0],
                "stock_code": identity[1],
                "sector_name": str(feature_row.get("sector_name") or ""),
                "labels": labels,
                "label_dates": label_dates,
            }
        )
        if training_label is None or end_text is None:
            continue
        records.append(
            {
                "as_of_date": identity[0],
                "stock_code": identity[1],
                "sector_name": str(feature_row.get("sector_name") or ""),
                "features": features,
                "feature_coverage": float(feature_row.get("feature_coverage") or 0.0),
                "labels": labels,
                "label_dates": label_dates,
                "training_label": training_label,
                "training_label_end_date": end_text,
            }
        )
    core_manifest = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_schema_sha256": feature_schema_sha256(),
        "feature_names": list(V1_FEATURE_NAMES),
        "label_definition": LABEL_DEFINITION,
        "max_label_horizon": 5,
        **_safety_envelope_with_pit(
            fixture_only=fixture_only,
            strict_pit_eligible=strict_pit_verified,
        ),
        "feature_universe_records": feature_universe_records,
        "evaluation_label_records": evaluation_label_records,
        "records": records,
    }
    dataset_sha256 = canonical_sha256(core_manifest)
    persisted_source_manifest = dict(source_manifest or {})
    persisted_source_manifest["fixture_only"] = bool(fixture_only)
    dates = sorted({row["as_of_date"] for row in records})
    report = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ok" if records else "insufficient_data",
        "strict_pit_eligible": strict_pit_verified,
        "pit_evidence_status": (
            "verified_prospective_archive"
            if strict_pit_verified
            else "unverified_no_trusted_verifier"
        ),
        "fixture_only": bool(fixture_only),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_schema_sha256": feature_schema_sha256(),
        "feature_names": list(V1_FEATURE_NAMES),
        "label_definition": LABEL_DEFINITION,
        "max_label_horizon": 5,
        "dataset_sha256": dataset_sha256,
        "source_manifest": persisted_source_manifest,
        "pit_evidence": dict(pit_evidence) if pit_evidence is not None else None,
        "date_range": {
            "start": dates[0] if dates else None,
            "end": dates[-1] if dates else None,
            "date_count": len(dates),
        },
        "feature_universe_date_range": {
            "start": (
                feature_universe_records[0]["as_of_date"]
                if feature_universe_records
                else None
            ),
            "end": (
                feature_universe_records[-1]["as_of_date"]
                if feature_universe_records
                else None
            ),
            "date_count": len(
                {row["as_of_date"] for row in feature_universe_records}
            ),
        },
        "counts": {
            "feature_rows": len(feature_rows),
            "label_rows": len(label_rows),
            "joined_rows": len(records),
            "feature_universe_rows": len(feature_universe_records),
            "evaluation_label_rows": len(evaluation_label_records),
            "unmatched_feature_rows": len(features_by_id.keys() - labels_by_id.keys()),
            "unmatched_label_rows": len(labels_by_id.keys() - features_by_id.keys()),
        },
        "feature_universe_records": feature_universe_records,
        "evaluation_label_records": evaluation_label_records,
        "records": records,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    require_finite(report, context="training dataset")
    return report


def validate_training_dataset(dataset: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Verify a persisted dataset's schema, feature order, labels, and SHA."""

    if dataset.get("schema_version") != DATASET_SCHEMA_VERSION:
        raise ValueError("training dataset schema mismatch")
    if dataset.get("mode") != MODE or dataset.get("status") != "ok":
        raise ValueError("training dataset is not ready")
    strict_pit_eligible = bool(dataset.get("strict_pit_eligible", False))
    expected_envelope = _safety_envelope_with_pit(
        fixture_only=bool(dataset.get("fixture_only", False)),
        strict_pit_eligible=strict_pit_eligible,
    )
    if any(dataset.get(key) != value for key, value in expected_envelope.items()):
        raise ValueError("training dataset safety envelope mismatch")
    if strict_pit_eligible:
        pit_evidence = dataset.get("pit_evidence")
        if not isinstance(pit_evidence, Mapping):
            raise ValueError("training dataset strict PIT evidence is unavailable")
        loaded = _validate_pit_evidence_for_rows(
            pit_evidence,
            feature_rows=list(dataset.get("feature_universe_records") or []),
            label_rows=list(dataset.get("evaluation_label_records") or []),
        )
        source_manifest = dataset.get("source_manifest")
        if not isinstance(source_manifest, Mapping):
            raise ValueError("strict training dataset source manifest is missing")
        source_archive = str(source_manifest.get("archive_root") or "")
        evidence_archive = str(pit_evidence.get("archive_root") or "")
        if (
            not source_archive
            or not evidence_archive
            or str(Path(source_archive).resolve()).casefold()
            != str(Path(evidence_archive).resolve()).casefold()
        ):
            raise ValueError("strict dataset source and PIT archives do not match")
        baseline_source = source_manifest.get("baseline_source")
        if not isinstance(baseline_source, Mapping):
            raise ValueError("strict dataset baseline source manifest is missing")
        baseline_path = Path(str(baseline_source.get("path") or ""))
        baseline_doc, baseline_sha = load_strict_json_with_sha256(baseline_path)
        if baseline_sha != str(baseline_source.get("sha256") or "").lower():
            raise ValueError("strict dataset baseline source SHA mismatch")
        if (
            not isinstance(baseline_doc, Mapping)
            or baseline_doc.get("pit_evidence_sha256")
            != pit_evidence.get("evidence_sha256")
            or baseline_doc.get("records") != loaded["baseline_rows"]
        ):
            raise ValueError("strict dataset baseline source does not match archive")
        expected = build_training_dataset(
            loaded["feature_rows"],
            loaded["label_rows"],
            strict_pit_eligible=False,
        )
        for field in (
            "feature_universe_records",
            "evaluation_label_records",
            "records",
        ):
            if dataset.get(field) != expected.get(field):
                raise ValueError(
                    f"strict PIT dataset {field} does not match the verified archive"
                )
    source_manifest = dataset.get("source_manifest")
    if isinstance(source_manifest, Mapping) and "fixture_only" in source_manifest:
        if bool(source_manifest.get("fixture_only")) != bool(
            dataset.get("fixture_only")
        ):
            raise ValueError("training dataset fixture identity mismatch")
    if dataset.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("training dataset feature schema mismatch")
    if dataset.get("feature_schema_sha256") != feature_schema_sha256():
        raise ValueError("training dataset feature schema SHA mismatch")
    if tuple(dataset.get("feature_names") or ()) != V1_FEATURE_NAMES:
        raise ValueError("training dataset feature order mismatch")
    if dataset.get("label_definition") != LABEL_DEFINITION:
        raise ValueError("training dataset label definition mismatch")
    if int(dataset.get("max_label_horizon") or 0) != 5:
        raise ValueError("training dataset max label horizon mismatch")
    raw_records = dataset.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise ValueError("training dataset records are unavailable")
    seen: set[tuple[str, str]] = set()
    records: list[dict[str, Any]] = []
    for raw in raw_records:
        if not isinstance(raw, Mapping):
            raise ValueError("training dataset record must be an object")
        identity = _identity(raw, context="dataset")
        if identity in seen:
            raise ValueError(f"duplicate dataset identity: {identity[0]} {identity[1]}")
        seen.add(identity)
        features = raw.get("features")
        if not isinstance(features, Mapping) or tuple(features) != V1_FEATURE_NAMES:
            raise ValueError("training dataset record feature order mismatch")
        require_finite(raw, context=f"dataset record {identity[0]} {identity[1]}")
        _validate_training_label_contract(raw, as_of_date=identity[0])
        records.append(dict(raw))
    feature_universe = dataset.get("feature_universe_records")
    evaluation_labels = dataset.get("evaluation_label_records")
    if not isinstance(feature_universe, list) or not feature_universe:
        raise ValueError("training dataset feature universe is unavailable")
    if not isinstance(evaluation_labels, list):
        raise ValueError("training dataset evaluation labels are unavailable")
    for context, rows in (
        ("feature universe", feature_universe),
        ("evaluation label", evaluation_labels),
    ):
        seen_rows: set[tuple[str, str]] = set()
        for raw in rows:
            if not isinstance(raw, Mapping):
                raise ValueError(f"{context} row must be an object")
            identity = _identity(raw, context=context)
            if identity in seen_rows:
                raise ValueError(f"duplicate {context} identity: {identity}")
            seen_rows.add(identity)
            if context == "feature universe":
                features = raw.get("features")
                if not isinstance(features, Mapping) or tuple(features) != V1_FEATURE_NAMES:
                    raise ValueError("feature universe order mismatch")
            require_finite(raw, context=f"{context} {identity[0]} {identity[1]}")
    feature_universe_by_id = _index_unique(
        feature_universe, context="feature universe"
    )
    evaluation_labels_by_id = _index_unique(
        evaluation_labels, context="evaluation label"
    )
    records_by_id = _index_unique(records, context="dataset")
    for identity, record in records_by_id.items():
        feature_view = feature_universe_by_id.get(identity)
        if feature_view is None:
            raise ValueError(
                "cross-view feature mismatch: dataset record is absent from feature universe"
            )
        if (
            record.get("sector_name") != feature_view.get("sector_name")
            or record.get("features") != feature_view.get("features")
            or record.get("feature_coverage") != feature_view.get("feature_coverage")
        ):
            raise ValueError("cross-view feature mismatch")

        label_view = evaluation_labels_by_id.get(identity)
        if label_view is None:
            raise ValueError(
                "cross-view label mismatch: dataset record is absent from evaluation labels"
            )
        if (
            record.get("sector_name") != label_view.get("sector_name")
            or record.get("labels") != label_view.get("labels")
            or record.get("label_dates") != label_view.get("label_dates")
        ):
            raise ValueError("cross-view label mismatch")
    core_manifest = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_schema_sha256": feature_schema_sha256(),
        "feature_names": list(V1_FEATURE_NAMES),
        "label_definition": LABEL_DEFINITION,
        "max_label_horizon": 5,
        **expected_envelope,
        "feature_universe_records": feature_universe,
        "evaluation_label_records": evaluation_labels,
        "records": records,
    }
    if canonical_sha256(core_manifest) != dataset.get("dataset_sha256"):
        raise ValueError("training dataset SHA mismatch")
    return records
