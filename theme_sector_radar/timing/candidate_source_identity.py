"""Validate derived intraday candidate roots before timing research."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from theme_sector_radar.data.local_minute_archive import (
    aggregate_complete_1m_session_to_5m,
    bar_timestamp,
    security_bound_bars_sha256,
    validate_bar_security_identity,
    validate_complete_a_share_session,
)
from theme_sector_radar.factors.calculators import calculate_intraday_factors
from theme_sector_radar.reporting.strict_json import load_confined_strict_json_snapshot


CANDIDATE_FILE_NAMES = (
    "top30_candidates.intraday_backfilled.json",
    "top30_candidates.analysis_backfilled.json",
    "top30_candidates.factor_backfilled.json",
    "top30_candidates.json",
)
LEGACY_SECURITY_BOUND_MANIFESTS = frozenset({
    "49c79ea2916369461d99a975ddb3ef734317eb0b9937ea3878f1fbf8e422ad2d",
    "2bf9cfa23512fb141db6343592fafc4b75629ddc9eecd82998b07c85eb69176e",
})


def validate_records_candidate_source_identity(
    identity: Mapping[str, Any] | None,
    *,
    candidate_root: Path,
    source_root: Path,
    timeframe: str,
    context: str,
) -> dict[str, Any]:
    """Bind a records artifact to one previously validated candidate root."""
    expected_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    if not expected_source:
        raise ValueError(f"unsupported candidate timeframe: {timeframe}")
    if not isinstance(identity, Mapping):
        raise ValueError(f"{context} candidate source identity is missing")
    if identity.get("status") != "validated":
        raise ValueError(f"{context} candidate source identity status is not validated")
    if identity.get("bar_interval") != timeframe:
        raise ValueError(f"{context} candidate source identity timeframe mismatch")
    if identity.get("bar_source") != expected_source:
        raise ValueError(f"{context} candidate source identity bar source mismatch")
    manifest_sha256 = str(identity.get("manifest_sha256") or "")
    if len(manifest_sha256) != 64 or any(character not in "0123456789abcdefABCDEF" for character in manifest_sha256):
        raise ValueError(f"{context} candidate source identity manifest SHA is invalid")
    recorded_candidate_root = str(identity.get("candidate_root") or "")
    if not recorded_candidate_root or _normalized_path(recorded_candidate_root) != _normalized_path(candidate_root):
        raise ValueError(f"{context} candidate source identity candidate root mismatch")
    recorded_source_root = str(identity.get("source_root") or "")
    if not recorded_source_root or _normalized_path(recorded_source_root) != _normalized_path(source_root):
        raise ValueError(f"{context} candidate source identity source root mismatch")
    return dict(identity)


def revalidate_records_candidate_source_identity(
    identity: Mapping[str, Any] | None,
    *,
    candidate_root: Path,
    source_root: Path,
    timeframe: str,
    start: str | None,
    end: str | None,
    context: str,
    document_snapshots: dict[Path, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    recorded = validate_records_candidate_source_identity(
        identity,
        candidate_root=candidate_root,
        source_root=source_root,
        timeframe=timeframe,
        context=context,
    )
    current = validate_candidate_root_identity(
        candidate_root,
        source_root=source_root,
        timeframe=timeframe,
        start=start,
        end=end,
        document_snapshots=document_snapshots,
    )
    for field in (
        "manifest_sha256",
        "document_count",
        "complete_candidate_count",
        "invalid_candidate_count",
    ):
        if field in recorded and recorded.get(field) != current.get(field):
            raise ValueError(f"{context} candidate source {field.replace('_', ' ')} mismatch")
    return current


def validate_candidate_root_identity(
    candidate_root: Path,
    *,
    source_root: Path,
    timeframe: str,
    start: str | None = None,
    end: str | None = None,
    document_snapshots: dict[Path, Mapping[str, Any]] | None = None,
    source_snapshot_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        candidate_root_resolved = candidate_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            "candidate source identity cannot be validated without candidate documents"
        ) from exc
    source_root_resolved = source_root.resolve()
    if _is_within(source_root_resolved, candidate_root_resolved) or _is_within(
        candidate_root_resolved,
        source_root_resolved,
    ):
        raise ValueError("candidate source root and derived root must be separate sibling trees")
    expected_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    expected_count = {"1m": 241, "5m": 48}.get(timeframe)
    expected_interval = {"1m": 1, "5m": 5}.get(timeframe)
    if not expected_source or expected_count is None or expected_interval is None:
        raise ValueError(f"unsupported candidate timeframe: {timeframe}")
    paths = _discover_candidate_files(candidate_root_resolved, start=start, end=end)
    if not paths:
        raise ValueError("candidate source identity cannot be validated without candidate documents")
    complete_count = 0
    invalid_count = 0
    complete_dates: set[str] = set()
    manifest = []
    source_manifest = []
    captured_documents: dict[Path, Mapping[str, Any]] | None = (
        {} if document_snapshots is not None else None
    )
    missing_security_bound_identity = False
    factor_ids = tuple(calculate_intraday_factors({}))
    for path in paths:
        document_has_complete_candidate = False
        document, derived_sha256, derived_resolved_path = load_confined_strict_json_snapshot(
            path,
            root=candidate_root_resolved,
        )
        if not isinstance(document, Mapping):
            raise ValueError(f"candidate document identity requires a JSON object: {path}")
        directory_date = _iso_document_date(
            path.parent.name,
            context=f"candidate directory date: {path}",
        )
        payload_date = _iso_document_date(
            document.get("as_of"),
            context=f"candidate payload date: {path}",
        )
        if payload_date != directory_date:
            raise ValueError(f"candidate payload date does not match directory date: {path}")
        if captured_documents is not None:
            captured_documents[path] = document
        identity = document.get("intraday_bar_identity")
        if not isinstance(identity, Mapping):
            raise ValueError(f"candidate document identity is missing: {path}")
        if (
            identity.get("bar_interval") != timeframe
            or identity.get("bar_source") != expected_source
            or identity.get("source_bar_interval") != "1m"
            or identity.get("complete_1m_session_required") is not True
            or identity.get("derived_output") is not True
        ):
            raise ValueError(f"candidate document identity mismatch: {path}")
        source_path = Path(str(identity.get("source_path") or ""))
        source_sha256 = str(identity.get("source_sha256") or "")
        if len(source_sha256) != 64:
            raise ValueError(f"candidate document source SHA identity mismatch: {path}")
        try:
            source_document, actual_source_sha256, source_resolved_path = (
                load_confined_strict_json_snapshot(
                    source_path,
                    root=source_root_resolved,
                )
            )
        except ValueError as exc:
            if (
                "outside confined root" in str(exc)
                or "confined JSON root does not exist" in str(exc)
            ):
                raise ValueError(
                    f"candidate document source path is outside caller-bound source root: {path}"
                ) from exc
            raise
        source_relative = source_resolved_path.relative_to(source_root_resolved)
        derived_relative = derived_resolved_path.relative_to(candidate_root_resolved)
        if source_relative != derived_relative:
            raise ValueError(f"candidate document source path does not match derived relative path: {path}")
        if actual_source_sha256 != source_sha256:
            raise ValueError(f"candidate document source SHA identity mismatch: {path}")
        if not isinstance(source_document, Mapping) or not isinstance(source_document.get("candidates"), list):
            raise ValueError(f"candidate document source is invalid: {path}")
        source_manifest.append(
            {
                "date": directory_date,
                "relative_path": source_relative.as_posix(),
                "sha256": source_sha256,
            }
        )
        source_document_fields = {
            key: value for key, value in source_document.items() if key != "candidates"
        }
        derived_document_fields = {
            key: value
            for key, value in document.items()
            if key not in {"candidates", "intraday_bar_identity"}
        }
        if derived_document_fields != source_document_fields:
            raise ValueError(f"candidate document inherited fields mismatch source: {path}")
        source_candidates = _candidate_index(source_document["candidates"], context=f"source {source_path}")
        candidates = document.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"candidate document identity requires a candidates list: {path}")
        derived_candidates = _candidate_index(candidates, context=f"derived {path}")
        if set(derived_candidates) != set(source_candidates):
            raise ValueError(f"candidate document source candidate set mismatch: {path}")
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            code = str(candidate.get("code") or "")
            source_candidate = source_candidates[code]
            source_name = str(source_candidate.get("name") or "").strip()
            if not code.strip() or not source_name:
                raise ValueError(f"candidate source security identity is missing: {path}")
            if _inherited_candidate_fields(candidate, factor_ids) != _inherited_candidate_fields(
                source_candidate,
                factor_ids,
            ):
                raise ValueError(f"candidate inherited fields mismatch source: {path}")
            raw_source_bars = source_candidate.get("intraday_bars") or []
            if not isinstance(raw_source_bars, list) or any(
                not isinstance(row, Mapping) for row in raw_source_bars
            ):
                raise ValueError(f"candidate source bars must contain only objects: {path}")
            source_bars = [dict(row) for row in raw_source_bars]
            validate_bar_security_identity(
                source_bars,
                code=code,
                name=source_name,
                context=f"source candidate {code}",
            )
            expected_security_bars_sha256 = security_bound_bars_sha256(
                source_bars,
                code=code,
                name=source_name,
            )
            source_dates = {_bar_date(row) for row in source_bars if _bar_date(row)}
            source_session_complete = validate_complete_a_share_session(
                source_bars,
                interval_minutes=1,
            )
            expected_complete = source_session_complete and source_dates == {path.parent.name}
            expected_invalid_reason = (
                None
                if expected_complete
                else (
                    "session_date_mismatch"
                    if source_session_complete
                    else "incomplete_1m_session"
                )
            )
            candidate_identity = candidate.get("intraday_bar_identity")
            if not isinstance(candidate_identity, Mapping):
                raise ValueError(f"candidate row identity is missing: {path}")
            if (
                candidate_identity.get("bar_interval") != timeframe
                or candidate_identity.get("bar_source") != expected_source
            ):
                raise ValueError(f"candidate row identity mismatch: {path}")
            raw_bars = candidate.get("intraday_bars") or []
            if not isinstance(raw_bars, list) or any(
                not isinstance(row, Mapping) for row in raw_bars
            ):
                raise ValueError(f"candidate derived bars must contain only objects: {path}")
            bars = [dict(row) for row in raw_bars]
            source_bar_count = candidate_identity.get("source_1m_bar_count")
            bar_count = candidate_identity.get("bar_count")
            identity_label = (
                "complete-session identity"
                if expected_complete
                else "invalid candidate identity"
            )
            if (
                not isinstance(source_bar_count, int)
                or isinstance(source_bar_count, bool)
                or source_bar_count != len(source_bars)
                or not isinstance(bar_count, int)
                or isinstance(bar_count, bool)
                or bar_count != len(bars)
                or candidate_identity.get("invalid_reason") != expected_invalid_reason
            ):
                raise ValueError(f"candidate {identity_label} mismatch: {path}")
            recorded_security_bars_sha256 = candidate_identity.get(
                "source_security_bars_sha256"
            )
            if recorded_security_bars_sha256 is None:
                missing_security_bound_identity = True
            elif recorded_security_bars_sha256 != expected_security_bars_sha256:
                raise ValueError(f"candidate source bar security identity mismatch: {path}")
            if candidate_identity.get("complete_session") is not expected_complete:
                raise ValueError(f"candidate row source completeness mismatch: {path}")
            if candidate_identity.get("complete_session") is True:
                expected_bars = source_bars if timeframe == "1m" else aggregate_complete_1m_session_to_5m(source_bars)
                expected_bars = [
                    _canonical_derived_bar(
                        row,
                        code=code,
                        name=source_name,
                    )
                    for row in expected_bars
                ]
                if (
                    len(source_bars) != 241
                    or len(bars) != expected_count
                    or not validate_complete_a_share_session(bars, interval_minutes=expected_interval)
                ):
                    raise ValueError(f"candidate complete-session identity mismatch: {path}")
                if not _same_derived_bars(bars, expected_bars):
                    raise ValueError(f"candidate derived bars mismatch bound 1m source: {path}")
                expected_candidate = dict(source_candidate)
                expected_candidate["intraday_bars"] = expected_bars
                expected_factors = calculate_intraday_factors(expected_candidate)
                if any(
                    not _same_factor_value(candidate.get(factor_id), expected_factors.get(factor_id))
                    for factor_id in factor_ids
                ):
                    raise ValueError(f"candidate derived factor mismatch bound bars: {path}")
                complete_count += 1
                document_has_complete_candidate = True
            else:
                if bars or any(candidate.get(factor_id) is not None for factor_id in factor_ids):
                    raise ValueError(f"invalid candidate retained bars or intraday factor values: {path}")
                invalid_count += 1
        if document_has_complete_candidate:
            complete_dates.add(path.parent.name)
        manifest.append(
            {
                "date": path.parent.name,
                "path": str(path),
                "sha256": derived_sha256,
                "source_path": str(source_path),
                "source_sha256": source_sha256,
            }
        )
    manifest_payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    manifest_sha256 = hashlib.sha256(manifest_payload.encode("utf-8")).hexdigest()
    source_manifest_payload = json.dumps(
        source_manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if (
        missing_security_bound_identity
        and manifest_sha256 not in LEGACY_SECURITY_BOUND_MANIFESTS
    ):
        raise ValueError("candidate source bar security identity is missing")
    if document_snapshots is not None:
        document_snapshots.clear()
        document_snapshots.update(captured_documents or {})
    if source_snapshot_identity is not None:
        source_snapshot_identity.clear()
        source_snapshot_identity.update(
            {
                "source_root": str(source_root),
                "document_count": len(source_manifest),
                "document_dates": [item["date"] for item in source_manifest],
                "manifest_sha256": hashlib.sha256(
                    source_manifest_payload.encode("utf-8")
                ).hexdigest(),
            }
        )
    return {
        "status": "validated",
        "candidate_root": str(candidate_root),
        "source_root": str(source_root),
        "bar_interval": timeframe,
        "bar_source": expected_source,
        "document_count": len(paths),
        "document_dates": sorted({path.parent.name for path in paths}),
        "complete_candidate_dates": sorted(complete_dates),
        "complete_candidate_count": complete_count,
        "invalid_candidate_count": invalid_count,
        "manifest_sha256": manifest_sha256,
    }


def _discover_candidate_files(root: Path, *, start: str | None, end: str | None) -> list[Path]:
    if not root.exists():
        return []
    paths = []
    for date_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        candidate_path = next(
            (
                date_dir / name
                for name in CANDIDATE_FILE_NAMES
                if (date_dir / name).exists()
            ),
            None,
        )
        if candidate_path is None:
            continue
        date = _iso_document_date(
            date_dir.name,
            context=f"candidate directory date: {date_dir}",
        )
        if start and date < start:
            continue
        if end and date > end:
            continue
        paths.append(candidate_path)
    return paths


def _normalized_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve()).casefold()


def _iso_document_date(value: Any, *, context: str) -> str:
    try:
        normalized = date.fromisoformat(str(value)).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be an ISO date") from exc
    if normalized != value:
        raise ValueError(f"{context} must be a canonical ISO date")
    return normalized


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _inherited_candidate_fields(
    candidate: Mapping[str, Any],
    factor_ids: tuple[str, ...],
) -> dict[str, Any]:
    derived_fields = {"intraday_bars", "intraday_bar_identity", *factor_ids}
    return {key: value for key, value in candidate.items() if key not in derived_fields}


def _candidate_index(candidates: list[Any], *, context: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError(f"candidate row must be an object: {context}")
        code = str(candidate.get("code") or "").strip()
        if not code or code in result:
            raise ValueError(f"candidate code identity is missing or duplicated: {context}")
        result[code] = candidate
    return result


def _canonical_derived_bar(row: Mapping[str, Any], *, code: str, name: str) -> dict[str, Any]:
    timestamp = str(bar_timestamp(row) or row.get("date") or "")
    close = row.get("close")
    return {
        "date": timestamp,
        "time": timestamp,
        "code": code,
        "name": name,
        "price": close,
        "close": close,
        "open": row.get("open"),
        "high": row.get("high"),
        "low": row.get("low"),
        "amount": row.get("amount") or 0.0,
        "volume": row.get("volume") or 0.0,
    }


def _same_derived_bars(actual: list[Mapping[str, Any]], expected: list[Mapping[str, Any]]) -> bool:
    if len(actual) != len(expected):
        return False
    fields = ("open", "high", "low", "close", "amount", "volume")
    return all(
        bar_timestamp(left) == bar_timestamp(right)
        and str(left.get("code") or "") == str(right.get("code") or "")
        and str(left.get("name") or "") == str(right.get("name") or "")
        and all(_same_factor_value(left.get(field), right.get(field)) for field in fields)
        for left, right in zip(actual, expected)
    )


def _same_factor_value(actual: Any, expected: Any) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    try:
        left = float(actual)
        right = float(expected)
    except (TypeError, ValueError):
        return actual == expected
    return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=0.0, abs_tol=1e-9)


def _bar_date(row: Mapping[str, Any]) -> str:
    digits = "".join(character for character in str(bar_timestamp(row) or "") if character.isdigit())
    if len(digits) < 8:
        return ""
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
