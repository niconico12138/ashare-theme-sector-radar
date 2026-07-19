"""Strict JSON readers that reject non-finite numeric values."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import tempfile
from typing import Any


def loads_strict_json(text: str, *, context: str) -> Any:
    """Parse JSON while rejecting NaN, infinities, and overflowed floats."""

    def reject_constant(value: str) -> None:
        raise ValueError(f"{context} contains non-finite JSON number: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{context} contains duplicate JSON key: {key}")
            result[key] = value
        return result

    data = json.loads(
        text,
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_keys,
    )
    _validate_finite(data, context=context)
    return data


def load_strict_json(path: Path | str) -> Any:
    data, _sha256 = load_strict_json_with_sha256(path)
    return data


def load_strict_json_with_sha256(path: Path | str) -> tuple[Any, str]:
    """Parse and hash one immutable byte snapshot from a JSON path."""
    source = Path(path)
    raw = source.read_bytes()
    return (
        loads_strict_json(raw.decode("utf-8-sig"), context=str(source)),
        hashlib.sha256(raw).hexdigest(),
    )


def write_text_atomic(path: Path | str, text: str) -> None:
    """Write UTF-8 text through a same-directory fsynced atomic replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_strict_json_atomic(path: Path | str, payload: Any) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )
    write_text_atomic(path, serialized)


def load_confined_strict_json_with_sha256(
    path: Path | str,
    *,
    root: Path | str,
) -> tuple[Any, str]:
    """Read one strict JSON snapshot whose opened file remains under root."""
    data, sha256, _resolved_path = load_confined_strict_json_snapshot(
        path,
        root=root,
    )
    return data, sha256


def load_confined_strict_json_snapshot(
    path: Path | str,
    *,
    root: Path | str,
) -> tuple[Any, str, Path]:
    """Bind containment, opened-file identity, parsing, and SHA to one read."""
    requested_root = Path(root)
    requested_source = Path(path)
    try:
        resolved_root = requested_root.resolve(strict=True)
        root_stat_before = resolved_root.stat()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"confined JSON root does not exist: {requested_root}") from exc
    if not stat.S_ISDIR(root_stat_before.st_mode):
        raise ValueError(f"confined JSON root is not a directory: {requested_root}")

    try:
        resolved_source = requested_source.resolve(strict=True)
        source_stat_before = resolved_source.stat()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"confined JSON source does not exist: {requested_source}") from exc
    _require_within_root(resolved_source, resolved_root, source=requested_source)
    if not stat.S_ISREG(source_stat_before.st_mode):
        raise ValueError(f"confined JSON source is not a regular file: {requested_source}")

    try:
        with resolved_source.open("rb") as handle:
            opened_stat_before = os.fstat(handle.fileno())
            if not os.path.samestat(source_stat_before, opened_stat_before):
                raise ValueError(
                    f"confined JSON source changed before it was opened: {requested_source}"
                )
            raw = handle.read()
            opened_stat_after = os.fstat(handle.fileno())
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(f"confined JSON source could not be read: {requested_source}") from exc
    if _stat_fingerprint(opened_stat_before) != _stat_fingerprint(opened_stat_after):
        raise ValueError(f"confined JSON source changed while it was read: {requested_source}")

    try:
        resolved_root_after = requested_root.resolve(strict=True)
        root_stat_after = resolved_root_after.stat()
        resolved_source_after = requested_source.resolve(strict=True)
        source_stat_after = resolved_source_after.stat()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"confined JSON path changed while it was read: {requested_source}") from exc
    if (
        resolved_root_after != resolved_root
        or not os.path.samestat(root_stat_before, root_stat_after)
    ):
        raise ValueError(f"confined JSON root changed while source was read: {requested_root}")
    _require_within_root(
        resolved_source_after,
        resolved_root_after,
        source=requested_source,
    )
    if (
        resolved_source_after != resolved_source
        or not os.path.samestat(opened_stat_after, source_stat_after)
        or _stat_fingerprint(opened_stat_after) != _stat_fingerprint(source_stat_after)
    ):
        raise ValueError(f"confined JSON source changed while it was read: {requested_source}")

    return (
        loads_strict_json(raw.decode("utf-8-sig"), context=str(resolved_source)),
        hashlib.sha256(raw).hexdigest(),
        resolved_source,
    )


def _require_within_root(path: Path, root: Path, *, source: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"confined JSON source is outside confined root: {source}") from exc


def _stat_fingerprint(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _validate_finite(value: Any, *, context: str) -> None:
    if isinstance(value, int) and not isinstance(value, bool):
        try:
            finite_integer = math.isfinite(float(value))
        except OverflowError:
            finite_integer = False
        if not finite_integer:
            raise ValueError(f"{context} contains non-finite JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{context} contains non-finite JSON number")
    if isinstance(value, dict):
        for key, child in value.items():
            _validate_finite(child, context=f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_finite(child, context=f"{context}[{index}]")
