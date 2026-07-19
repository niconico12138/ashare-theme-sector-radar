"""Shared fail-closed contracts for ML shadow artifacts."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import platform
from typing import Any, Iterable


OPTIONAL_ML_PACKAGES = ("lightgbm", "numpy", "pandas", "sklearn")


def import_optional_ml_module(package: str):
    """Import an optional ML module without Windows shell platform probing."""

    if os.name != "nt":
        return importlib.import_module(package)
    original = {
        "system": platform.system,
        "machine": platform.machine,
        "processor": platform.processor,
        "release": platform.release,
        "version": platform.version,
    }
    platform.system = lambda: "Windows"
    platform.machine = lambda: "AMD64"
    platform.processor = lambda: "AMD64"
    platform.release = lambda: "10"
    platform.version = lambda: "10.0"
    try:
        return importlib.import_module(package)
    finally:
        for name, function in original.items():
            setattr(platform, name, function)


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_finite(value: Any, *, context: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{context} contains a non-finite value")
    if isinstance(value, dict):
        for key, child in value.items():
            require_finite(child, context=f"{context}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            require_finite(child, context=f"{context}[{index}]")


def optional_ml_dependency_readiness(
    packages: Iterable[str] = OPTIONAL_ML_PACKAGES,
) -> dict[str, Any]:
    versions: dict[str, str] = {}
    missing: list[str] = []
    errors: dict[str, str] = {}
    for package in packages:
        try:
            import_optional_ml_module(package)
            distribution = "scikit-learn" if package == "sklearn" else package
            versions[package] = importlib.metadata.version(distribution)
        except (
            ImportError,
            importlib.metadata.PackageNotFoundError,
            OSError,
            RuntimeError,
            ValueError,
        ) as exc:
            missing.append(package)
            errors[package] = f"{type(exc).__name__}: {exc}"
    return {
        "status": "ready" if not missing else "unavailable",
        "backend": "lightgbm_lambdarank" if not missing else None,
        "versions": versions,
        "missing_packages": missing,
        "import_errors": errors,
        "reason": "optional_ml_dependencies_ready" if not missing else "optional_ml_dependencies_missing",
    }
