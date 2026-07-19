import importlib
import hashlib
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.parametrize("payload", ['{"value": NaN}', '{"value": Infinity}', '{"value": 1e999}'])
def test_strict_json_rejects_nonfinite_numbers(payload):
    module = importlib.import_module("theme_sector_radar.reporting.strict_json")

    with pytest.raises(ValueError, match="non-finite"):
        module.loads_strict_json(payload, context="unit payload")


def test_strict_json_accepts_finite_json():
    module = importlib.import_module("theme_sector_radar.reporting.strict_json")

    assert module.loads_strict_json('{"value": [1.0, null]}', context="unit payload") == {
        "value": [1.0, None]
    }


def test_strict_json_rejects_integer_that_overflows_float_consumers():
    module = importlib.import_module("theme_sector_radar.reporting.strict_json")
    payload = '{"outer": [' + ("9" * 1000) + "]}"

    with pytest.raises(ValueError, match=r"unit payload\.outer\[0\].*non-finite"):
        module.loads_strict_json(payload, context="unit payload")


def test_strict_json_rejects_duplicate_object_keys():
    module = importlib.import_module("theme_sector_radar.reporting.strict_json")

    with pytest.raises(ValueError, match="duplicate JSON key.*paper_trading_only"):
        module.loads_strict_json(
            '{"paper_trading_only": true, "paper_trading_only": false}',
            context="unit payload",
        )


def test_strict_json_load_with_sha_binds_digest_to_parsed_bytes(tmp_path, monkeypatch):
    module = importlib.import_module("theme_sector_radar.reporting.strict_json")
    path = tmp_path / "report.json"
    first_bytes = b'{"version":"first"}'
    path.write_bytes(first_bytes)
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        self.write_bytes(b'{"version":"replacement"}')
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    payload, sha256 = module.load_strict_json_with_sha256(path)

    assert payload == {"version": "first"}
    assert sha256 == hashlib.sha256(first_bytes).hexdigest()


def test_confined_strict_json_rejects_directory_link_escape(tmp_path):
    module = importlib.import_module("theme_sector_radar.reporting.strict_json")
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "report.json").write_text('{"value": 1}', encoding="utf-8")
    linked = root / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(linked), str(outside)],
            check=True,
            capture_output=True,
            text=True,
        )
    try:
        with pytest.raises(ValueError, match="outside confined root"):
            module.load_confined_strict_json_with_sha256(
                linked / "report.json",
                root=root,
            )
    finally:
        if linked.is_symlink():
            linked.unlink()
        elif linked.exists():
            linked.rmdir()


def test_confined_strict_json_rejects_path_swap_before_open(tmp_path, monkeypatch):
    module = importlib.import_module("theme_sector_radar.reporting.strict_json")
    root = tmp_path / "root"
    root.mkdir()
    path = root / "report.json"
    replacement = root / "replacement.json"
    path.write_text('{"version": "first"}', encoding="utf-8")
    replacement.write_text('{"version": "replacement"}', encoding="utf-8")
    resolved_path = path.resolve()
    original_open = Path.open
    swapped = False

    def open_after_swap(self, *args, **kwargs):
        nonlocal swapped
        if self == resolved_path and not swapped:
            replacement.replace(resolved_path)
            swapped = True
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_after_swap)

    with pytest.raises(ValueError, match="changed before it was opened"):
        module.load_confined_strict_json_with_sha256(path, root=root)


@pytest.mark.parametrize(
    "relative_path",
    [
        "theme_sector_radar/cli.py",
        "theme_sector_radar/reports/markdown_report.py",
    ],
)
def test_primary_cli_report_writers_do_not_overwrite_in_place(relative_path):
    project_root = Path(__file__).resolve().parents[2]
    source = (project_root / relative_path).read_text(encoding="utf-8")

    assert 'with open(run_log_path, "w"' not in source
    assert 'with open(json_path, "w"' not in source
    assert 'with open(md_path, "w"' not in source
    assert 'with open(filepath, "w"' not in source
