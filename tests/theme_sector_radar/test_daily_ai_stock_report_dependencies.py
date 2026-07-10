from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "run_daily_ai_stock_report.py"


def _load_daily_module():
    spec = importlib.util.spec_from_file_location("run_daily_ai_stock_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dependency_details_include_actions(monkeypatch, tmp_path):
    module = _load_daily_module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("MARKET_DATA_SERVICE_URL", "http://127.0.0.1:8000")

    def fake_connection(*args, **kwargs):
        raise OSError("connection refused")

    class FakeUrlLib:
        @staticmethod
        def urlopen(*args, **kwargs):
            raise TimeoutError("api timeout")

    monkeypatch.setattr(module, "_open_socket", fake_connection)
    monkeypatch.setattr(module, "_urllib_request", FakeUrlLib)

    details = module.check_dependency_details("2026-07-08")

    assert details["stockdb"]["ok"] is False
    assert "127.0.0.1:7899" in details["stockdb"]["detail"]
    assert "stockdb.exe" in details["stockdb"]["action"]
    assert details["api"]["ok"] is False
    assert "http://127.0.0.1:8000/health" in details["api"]["detail"]
    assert details["sector_research"]["ok"] is False
    assert details["concept_rank"]["ok"] is False

