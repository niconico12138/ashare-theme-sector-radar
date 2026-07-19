"""Hermetic defaults for the ordinary pytest suite."""

from __future__ import annotations

import hashlib
import http.client
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request

import pytest
import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_NETWORK_TARGETS = (
    (socket, "create_connection"),
    (socket, "getaddrinfo"),
    (socket.socket, "connect"),
    (socket.socket, "connect_ex"),
    (socket.socket, "sendto"),
    (urllib.request, "urlopen"),
    (urllib.request.OpenerDirector, "open"),
    (http.client.HTTPConnection, "connect"),
    (http.client.HTTPSConnection, "connect"),
    (requests.sessions.Session, "request"),
    (requests.sessions.Session, "send"),
)
_ORIGINAL_NETWORK = {
    (owner, name): getattr(owner, name)
    for owner, name in _NETWORK_TARGETS
}
_ORIGINAL_POPEN = subprocess.Popen
_NETWORK_BLOCK_ACTIVE = False
_SESSION_TEMP_ROOT: Path | None = None
_ORIGINAL_ENV: dict[str, str | None] = {}
_SENSITIVE_ROOTS = (PROJECT_ROOT / "reports", PROJECT_ROOT / "data_cache")
_SENSITIVE_BEFORE: dict[str, str] | None = None


def _deny_network(*_args, **_kwargs):
    raise RuntimeError(
        "network access is disabled for ordinary pytest; mark the test network explicitly"
    )


def _install_network_block() -> None:
    global _NETWORK_BLOCK_ACTIVE
    for owner, name in _NETWORK_TARGETS:
        setattr(owner, name, _deny_network)
    subprocess.Popen = _guarded_popen
    _NETWORK_BLOCK_ACTIVE = True


def _restore_network() -> None:
    global _NETWORK_BLOCK_ACTIVE
    for (owner, name), original in _ORIGINAL_NETWORK.items():
        setattr(owner, name, original)
    subprocess.Popen = _ORIGINAL_POPEN
    _NETWORK_BLOCK_ACTIVE = False


def _guarded_popen(*popenargs, **kwargs):
    command = popenargs[0] if popenargs else kwargs.get("args")
    if kwargs.get("shell"):
        raise RuntimeError("external subprocess shell is disabled for ordinary pytest")
    if not isinstance(command, (list, tuple)) or not command:
        raise RuntimeError("external subprocess is disabled for ordinary pytest")
    executable = str(command[0])
    try:
        is_python = Path(executable).resolve() == Path(sys.executable).resolve()
    except OSError:
        is_python = False
    command_name = Path(executable).name.casefold()
    is_local_junction_command = (
        command_name in {"cmd", "cmd.exe"}
        and len(command) >= 3
        and str(command[1]).casefold() in {"/c", "-c"}
        and str(command[2]).casefold() == "mklink"
    )
    if not is_python and not is_local_junction_command:
        raise RuntimeError(
            f"external subprocess is disabled for ordinary pytest: {executable}"
        )
    if is_python:
        child_env = dict(os.environ if kwargs.get("env") is None else kwargs["env"])
        child_env["THEME_SECTOR_RADAR_PYTEST_DENY_NETWORK"] = "1"
        guard_pythonpath = os.environ.get("PYTHONPATH", "")
        if guard_pythonpath:
            child_env["PYTHONPATH"] = guard_pythonpath
        kwargs["env"] = child_env
    return _ORIGINAL_POPEN(*popenargs, **kwargs)


def _ordinary_suite(config) -> bool:
    expression = str(getattr(config.option, "markexpr", "") or "").casefold()
    return not expression or "not network" in expression


def _set_env(name: str, value: str) -> None:
    if name not in _ORIGINAL_ENV:
        _ORIGINAL_ENV[name] = os.environ.get(name)
    os.environ[name] = value


def _write_child_network_guard(root: Path) -> Path:
    guard_root = root / "child_network_guard"
    guard_root.mkdir(parents=True, exist_ok=True)
    (guard_root / "sitecustomize.py").write_text(
        "import os\n"
        "if os.environ.get('THEME_SECTOR_RADAR_PYTEST_DENY_NETWORK') == '1':\n"
        " import socket\n"
        " def _deny(*_args, **_kwargs):\n"
        "  raise RuntimeError('network access is disabled for ordinary pytest child process')\n"
        " socket.create_connection = _deny\n"
        " socket.getaddrinfo = _deny\n"
        " socket.socket.connect = _deny\n"
        " socket.socket.connect_ex = _deny\n"
        " socket.socket.sendto = _deny\n",
        encoding="ascii",
    )
    return guard_root


def _snapshot_sensitive_roots(roots) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for raw_root in roots:
        root = Path(raw_root)
        if not root.exists():
            continue
        for current_root, directory_names, file_names in os.walk(root, followlinks=False):
            directory_names[:] = sorted(directory_names)
            for file_name in sorted(file_names):
                path = Path(current_root) / file_name
                if path.is_symlink() or not path.is_file():
                    continue
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                snapshot[str(path.resolve())] = digest
    return snapshot


def _snapshot_changes(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed_paths = {
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    }
    return sorted(Path(path).name for path in changed_paths)


def pytest_configure(config):
    global _SESSION_TEMP_ROOT, _SENSITIVE_BEFORE
    if not _ordinary_suite(config):
        return
    _install_network_block()
    _SESSION_TEMP_ROOT = Path(tempfile.mkdtemp(prefix="theme-sector-radar-pytest-"))
    report_root = _SESSION_TEMP_ROOT / "reports"
    cache_root = _SESSION_TEMP_ROOT / "data_cache"
    report_root.mkdir()
    cache_root.mkdir()
    guard_root = _write_child_network_guard(_SESSION_TEMP_ROOT)
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = str(guard_root)
    if current_pythonpath:
        pythonpath = pythonpath + os.pathsep + current_pythonpath
    _set_env("PYTHONPATH", pythonpath)
    _set_env("THEME_SECTOR_RADAR_PYTEST_DENY_NETWORK", "1")
    _set_env("THEME_SECTOR_RADAR_REPORT_ROOT", str(report_root))
    _set_env("THEME_SECTOR_RADAR_CACHE_ROOT", str(cache_root))
    _SENSITIVE_BEFORE = _snapshot_sensitive_roots(_SENSITIVE_ROOTS)


def pytest_sessionfinish(session, exitstatus):
    if _SENSITIVE_BEFORE is None:
        return
    changes = _snapshot_changes(
        _SENSITIVE_BEFORE,
        _snapshot_sensitive_roots(_SENSITIVE_ROOTS),
    )
    if changes:
        session.config.issue_config_time_warning(
            pytest.PytestWarning(
                "ordinary pytest modified protected default roots: "
                + ", ".join(changes)
            ),
            stacklevel=2,
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_unconfigure(config):
    global _SESSION_TEMP_ROOT
    _restore_network()
    for name, original in _ORIGINAL_ENV.items():
        if original is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = original
    _ORIGINAL_ENV.clear()
    if _SESSION_TEMP_ROOT is not None:
        shutil.rmtree(_SESSION_TEMP_ROOT, ignore_errors=True)
        _SESSION_TEMP_ROOT = None


@pytest.fixture(autouse=True)
def deny_network_for_ordinary_tests(request, monkeypatch):
    if request.node.get_closest_marker("network") is not None:
        return
    for owner, name in _NETWORK_TARGETS:
        monkeypatch.setattr(owner, name, _deny_network)
