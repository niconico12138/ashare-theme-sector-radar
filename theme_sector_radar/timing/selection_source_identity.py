"""Content identity for dated next-session selection labels."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from theme_sector_radar.reporting.strict_json import load_confined_strict_json_snapshot


SELECTION_FILE_NAME = "next_day_selection_validation.json"


def validate_selection_source_identity(
    selection_validation_root: Path,
    *,
    start: str | None,
    end: str | None,
    document_snapshots: dict[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a deterministic content manifest for the selected date range."""
    try:
        root = selection_validation_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            "selection source identity cannot be validated without selection documents"
        ) from exc
    normalized_start = _optional_iso_date(start, context="selection source start")
    normalized_end = _optional_iso_date(end, context="selection source end")
    if normalized_start and normalized_end and normalized_start > normalized_end:
        raise ValueError("selection source start must not be after end")

    manifest: list[dict[str, str]] = []
    captured_documents: dict[str, Mapping[str, Any]] = {}
    if root.exists():
        for date_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            path = date_dir / SELECTION_FILE_NAME
            if not path.exists():
                continue
            document_date = _iso_date(date_dir.name, context="selection source directory")
            if normalized_start and document_date < normalized_start:
                continue
            if normalized_end and document_date > normalized_end:
                continue
            document, document_sha256, resolved_path = load_confined_strict_json_snapshot(
                path,
                root=root,
            )
            if not isinstance(document, Mapping):
                raise ValueError(f"selection source document must be a JSON object: {path}")
            payload_date = _iso_date(
                document.get("as_of"),
                context=f"selection source payload date: {path}",
            )
            if payload_date != document_date:
                raise ValueError(
                    f"selection source payload date does not match directory date: {path}"
                )
            captured_documents[document_date] = document
            manifest.append(
                {
                    "date": document_date,
                    "relative_path": resolved_path.relative_to(root).as_posix(),
                    "sha256": document_sha256,
                }
            )
    if not manifest:
        raise ValueError("selection source identity cannot be validated without selection documents")

    payload = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if document_snapshots is not None:
        document_snapshots.clear()
        document_snapshots.update(captured_documents)
    return {
        "status": "validated",
        "selection_validation_root": str(selection_validation_root),
        "start": normalized_start,
        "end": normalized_end,
        "document_count": len(manifest),
        "document_dates": [item["date"] for item in manifest],
        "manifest_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def revalidate_records_selection_source_identity(
    identity: Mapping[str, Any] | None,
    *,
    selection_validation_root: Path,
    start: str | None,
    end: str | None,
    context: str,
    document_snapshots: dict[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recompute a recorded selection manifest from caller-bound inputs."""
    if not isinstance(identity, Mapping) or identity.get("status") != "validated":
        raise ValueError(f"{context} selection source identity is missing or unvalidated")
    if not _same_path(identity.get("selection_validation_root"), selection_validation_root):
        raise ValueError(f"{context} selection source root mismatch")
    normalized_start = _optional_iso_date(start, context=f"{context} selection source start")
    normalized_end = _optional_iso_date(end, context=f"{context} selection source end")
    if identity.get("start") != normalized_start or identity.get("end") != normalized_end:
        raise ValueError(f"{context} selection source range mismatch")

    current = validate_selection_source_identity(
        selection_validation_root,
        start=normalized_start,
        end=normalized_end,
        document_snapshots=document_snapshots,
    )
    for field in ("manifest_sha256", "document_count", "document_dates"):
        if identity.get(field) != current.get(field):
            label = "manifest SHA" if field == "manifest_sha256" else field.replace("_", " ")
            raise ValueError(f"{context} selection source {label} mismatch")
    return current


def _iso_date(value: str, *, context: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{context} must be a canonical ISO date")
    return value


def _optional_iso_date(value: str | None, *, context: str) -> str | None:
    return _iso_date(value, context=context) if value is not None else None


def _same_path(left: Any, right: Path) -> bool:
    if not str(left or ""):
        return False
    return str(Path(str(left)).resolve()).casefold() == str(right.resolve()).casefold()
