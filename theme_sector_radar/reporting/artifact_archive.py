"""Preserve superseded research artifacts under content-addressed names."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile


def validate_file_sha256_identity(
    path_value: object,
    sha256_value: object,
    *,
    context: str,
) -> dict[str, str]:
    if not path_value or not sha256_value:
        raise ValueError(f"{context} path and SHA are required")
    path = Path(str(path_value))
    expected_sha256 = str(sha256_value).lower()
    if not path.is_file():
        raise ValueError(f"{context} path does not exist: {path}")
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"{context} SHA mismatch: expected {expected_sha256}, got {actual_sha256}")
    return {"path": str(path), "sha256": actual_sha256}


def write_text_preserving_previous(path: Path, content: str) -> Path | None:
    encoded = content.encode("utf-8")
    archived_path = None
    if path.exists():
        previous = path.read_bytes()
        if previous == encoded:
            return None
        digest = hashlib.sha256(previous).hexdigest()[:12]
        archived_path = path.with_name(f"{path.stem}.{digest}{path.suffix}")
        if archived_path.exists() and archived_path.read_bytes() != previous:
            raise ValueError(f"content-addressed archive collision: {archived_path}")
        if not archived_path.exists():
            _atomic_write(archived_path, previous)
    _atomic_write(path, encoded)
    return archived_path


def _atomic_write(path: Path, content: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
