from configparser import ConfigParser
import ast
import http.client
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

import pytest
import requests


def test_plain_pytest_excludes_network_marked_contracts():
    config = ConfigParser()
    config.read(Path(__file__).resolve().parents[2] / "pytest.ini", encoding="utf-8")

    addopts = config["pytest"].get("addopts", "")

    assert "-m" in addopts
    assert "not network" in addopts


@pytest.mark.parametrize(
    "attempt",
    [
        lambda: socket.create_connection(("127.0.0.1", 9), timeout=0.01),
        lambda: urllib.request.urlopen("http://127.0.0.1:9", timeout=0.01),
        lambda: http.client.HTTPConnection("127.0.0.1", 9, timeout=0.01).request("GET", "/"),
        lambda: requests.get("http://127.0.0.1:9", timeout=0.01),
    ],
)
def test_plain_pytest_denies_network_calls(attempt):
    with pytest.raises(RuntimeError, match="network access is disabled"):
        attempt()


def test_plain_pytest_denies_network_in_python_subprocess():
    probe = (
        "import socket,sys\n"
        "try:\n"
        " socket.create_connection(('127.0.0.1', 9), timeout=0.01)\n"
        "except RuntimeError as exc:\n"
        " sys.exit(0 if 'network access is disabled' in str(exc) else 3)\n"
        "except Exception:\n"
        " sys.exit(2)\n"
        "sys.exit(1)\n"
    )

    result = subprocess.run([sys.executable, "-c", probe], check=False)

    assert result.returncode == 0


def test_plain_pytest_rejects_unapproved_external_subprocesses():
    with pytest.raises(RuntimeError, match="external subprocess"):
        subprocess.run(["unapproved-network-capable-program"], check=False)


def test_plain_pytest_uses_isolated_default_roots():
    report_root = Path(os.environ["THEME_SECTOR_RADAR_REPORT_ROOT"]).resolve()
    cache_root = Path(os.environ["THEME_SECTOR_RADAR_CACHE_ROOT"]).resolve()
    project_root = Path(__file__).resolve().parents[2]

    assert project_root not in report_root.parents
    assert project_root not in cache_root.parents


def test_sensitive_root_snapshot_detects_created_file(tmp_path):
    conftest_path = Path(__file__).resolve().parents[1] / "conftest.py"
    spec = importlib.util.spec_from_file_location("suite_conftest", conftest_path)
    assert spec and spec.loader
    suite_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite_config)

    before = suite_config._snapshot_sensitive_roots([tmp_path])
    (tmp_path / "unexpected.json").write_text("{}", encoding="utf-8")
    after = suite_config._snapshot_sensitive_roots([tmp_path])

    assert suite_config._snapshot_changes(before, after) == ["unexpected.json"]


def test_local_retry_unit_tests_are_not_network_marked():
    path = Path(__file__).with_name("test_akshare_retry.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    local_tests = {
        "test_safe_call_returns_result",
        "test_safe_call_handles_exception",
        "test_safe_call_handles_none_return",
        "test_safe_call_handles_empty_dataframe",
    }
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for name in local_tests:
        decorators = [ast.unparse(item) for item in functions[name].decorator_list]
        assert all("network" not in decorator for decorator in decorators)
