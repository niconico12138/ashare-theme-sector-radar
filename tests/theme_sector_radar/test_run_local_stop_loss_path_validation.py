import hashlib
import importlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.run_local_stop_loss_path_validation import (
    reaudit_local_stop_loss_path_validation,
    run_local_stop_loss_path_validation,
)


HEADER = "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"


def test_run_local_stop_loss_path_validation_writes_trigger_dataset(tmp_path):
    stock_archive = tmp_path / "2024_1min.zip"
    falling_rows = [
        "2024-01-02 09:30:00,sz000001,a,10,10,10,10,100,1000",
        "2024-01-02 09:31:00,sz000001,a,10,9.6,9.7,9.5,200,2000",
        "2024-01-02 09:32:00,sz000001,a,9.5,9.4,9.5,9.3,100,1000",
        "2024-01-02 09:33:00,sz000001,a,9.4,9.3,9.4,9.2,100,1000",
        "2024-01-02 09:34:00,sz000001,a,9.3,9.2,9.3,9.1,100,1000",
        "2024-01-02 09:35:00,sz000001,a,9.2,9.1,9.2,9.0,100,1000",
        "2024-01-02 09:36:00,sz000001,a,9.1,9.0,9.1,8.9,100,1000",
    ]
    flat_rows = [
        f"2024-01-02 09:{30 + index:02d}:00,sz000002,b,10,10,10.1,9.9,100,1000"
        for index in range(7)
    ]
    with zipfile.ZipFile(stock_archive, "w") as archive:
        archive.writestr("sz000001_2024.csv", HEADER + "\n".join(falling_rows) + "\n")
        archive.writestr("sz000002_2024.csv", HEADER + "\n".join(flat_rows) + "\n")

    board_root = tmp_path / "boards" / "2024-01"
    board_root.mkdir(parents=True)
    board_archive = board_root / "20240102_1min.zip"
    with zipfile.ZipFile(board_archive, "w") as archive:
        archive.writestr(
            "880001.csv",
            HEADER
            + "2024-01-02 09:31:00,880001,board,100,98.5,100,98,100,1000\n"
            + "2024-01-02 09:32:00,880001,board,98.5,98,99,97.5,100,1000\n",
        )

    result = run_local_stop_loss_path_validation(
        stock_archives=[stock_archive],
        codes=["000001", "000002", "000003"],
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
        board_archive_root=tmp_path / "boards",
        stock_to_board_codes={"000001": ["880001"]},
        horizons=(5,),
        fold_count=1,
        min_signals=1,
    )

    data = json.loads(result["json_path"].read_text(encoding="utf-8"))
    assert data["summary"]["triggered_record_count"] == 1
    assert data["summary"]["board_labeled_trigger_count"] == 1
    assert data["summary"]["requested_code_count"] == 3
    assert data["summary"]["observed_code_count"] == 2
    assert data["summary"]["code_count"] == 2
    assert data["sample_scope"] == "unconditional_stock_day_stress"
    assert data["strategy_linked_entry_paths"] is False
    assert data["bar_interval"] == "1m"
    assert data["input_archive_identities"]["stock_archives"] == [
        {"path": str(stock_archive), "sha256": hashlib.sha256(stock_archive.read_bytes()).hexdigest()}
    ]
    assert data["input_archive_identities"]["board_archives"] == [
        {"path": str(board_archive), "sha256": hashlib.sha256(board_archive.read_bytes()).hexdigest()}
    ]
    assert "trigger_events" not in data
    event_lines = result["events_path"].read_text(encoding="utf-8").splitlines()
    event = json.loads(event_lines[0])
    assert event["no_execution_signals"] is True
    assert event["does_not_modify_official_scores"] is True
    assert event["trigger_factor_features"]["relative_weakness"] is True
    assert event["trigger_factor_features"]["money_flow_deterioration"] is True
    assert event["trigger_factor_features"]["board_synchronous_weakness"] is True
    relative = data["factors"]["relative_weakness"]["by_horizon"]["5"]
    assert relative["continuation_tail_rate"] == 1.0
    assert result["markdown_path"].exists()

    refreshed = reaudit_local_stop_loss_path_validation(
        existing_report_path=result["json_path"],
        output_dir=tmp_path / "refreshed",
        as_of="2026-07-13",
        horizons=(5,),
        fold_count=1,
        min_signals=1,
    )
    refreshed_data = json.loads(refreshed["json_path"].read_text(encoding="utf-8"))
    assert refreshed_data["factors"]["board_synchronous_weakness"]["eligible_baseline"]["by_horizon"]["5"]["signal_count"] == 1


def test_stock_archive_identity_is_bound_to_bytes_used_for_analysis(
    tmp_path,
    monkeypatch,
):
    module = importlib.import_module("scripts.run_local_stop_loss_path_validation")
    stock_archive = tmp_path / "2024_1min.zip"
    with zipfile.ZipFile(stock_archive, "w") as archive:
        archive.writestr(
            "sz000001_2024.csv",
            HEADER
            + "2024-01-02 09:30:00,sz000001,a,10,10,10,10,100,1000\n",
        )
    analyzed_sha256 = hashlib.sha256(stock_archive.read_bytes()).hexdigest()
    original_scan = module.scan_stock_daily_paths_batch

    def scan_then_replace(source, codes, **kwargs):
        result = original_scan(source, codes, **kwargs)
        with zipfile.ZipFile(stock_archive, "w") as archive:
            archive.writestr(
                "sz000001_2024.csv",
                HEADER
                + "2024-01-02 09:30:00,sz000001,replaced,99,99,99,99,1,1\n",
            )
        return result

    monkeypatch.setattr(module, "scan_stock_daily_paths_batch", scan_then_replace)

    with pytest.raises(ValueError, match="archive changed while being analyzed"):
        module.run_local_stop_loss_path_validation(
            stock_archives=[stock_archive],
            codes=["000001"],
            output_dir=tmp_path / "out",
            as_of="2026-07-13",
            horizons=(5,),
            fold_count=1,
            min_signals=1,
        )

    assert analyzed_sha256 != hashlib.sha256(stock_archive.read_bytes()).hexdigest()
    assert not (tmp_path / "out").exists()


def test_local_stop_path_rejects_declared_interval_that_disagrees_with_archive(tmp_path):
    stock_archive = tmp_path / "2024_1min.zip"
    with zipfile.ZipFile(stock_archive, "w") as archive:
        archive.writestr("sz000001_2024.csv", HEADER)

    with pytest.raises(ValueError, match="bar interval"):
        run_local_stop_loss_path_validation(
            stock_archives=[stock_archive],
            codes=["000001"],
            output_dir=tmp_path / "out",
            as_of="2026-07-13",
            bar_interval="5m",
        )


def test_reaudit_rejects_tampered_trigger_event_file_before_loading(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text('{"date":"2024-01-02","code":"000001"}\n', encoding="utf-8")
    existing_report_path = tmp_path / "long-history.json"
    existing_report_path.write_text(
        json.dumps(
            {
                "paper_trading_only": True,
                "no_execution_signals": True,
                "does_not_modify_official_scores": True,
                "bar_interval": "1m",
                "sample_scope": "unconditional_stock_day_stress",
                "strategy_linked_entry_paths": False,
                "trigger_events_path": str(events_path),
                "trigger_events_sha256": hashlib.sha256(events_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    events_path.write_text('{"date":"2024-01-02","code":"tampered"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="trigger events SHA mismatch"):
        reaudit_local_stop_loss_path_validation(
            existing_report_path=existing_report_path,
            output_dir=tmp_path / "reaudit",
            as_of="2026-07-13",
            horizons=(5,),
            fold_count=1,
            min_signals=1,
        )


def test_reaudit_rejects_embedded_trigger_events_bypass(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text('', encoding="utf-8")
    existing_report_path = tmp_path / "long-history.json"
    existing_report_path.write_text(
        json.dumps(
            {
                "bar_interval": "1m",
                "sample_scope": "unconditional_stock_day_stress",
                "strategy_linked_entry_paths": False,
                "trigger_events_path": str(events_path),
                "trigger_events_sha256": hashlib.sha256(events_path.read_bytes()).hexdigest(),
                "trigger_events": [{"date": "2024-01-02", "code": "embedded-bypass"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="embedded trigger_events"):
        reaudit_local_stop_loss_path_validation(
            existing_report_path=existing_report_path,
            output_dir=tmp_path / "reaudit",
            as_of="2026-07-13",
            horizons=(5,),
            fold_count=1,
            min_signals=1,
        )


def test_reaudit_parses_the_same_trigger_event_bytes_it_hashes(tmp_path, monkeypatch):
    events_path = tmp_path / "events.jsonl"
    original_event = {
        "date": "2024-01-02",
        "code": "original",
        "fixed_stop_path": {"trigger_price": 9.7},
        "paper_research_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    replacement_event = {**original_event, "code": "replacement"}
    original_bytes = (json.dumps(original_event) + "\n").encode("utf-8")
    events_path.write_bytes(original_bytes)
    existing_report_path = tmp_path / "long-history.json"
    existing_report_path.write_text(
        json.dumps(
            {
                "paper_trading_only": True,
                "no_execution_signals": True,
                "does_not_modify_official_scores": True,
                "bar_interval": "1m",
                "sample_scope": "unconditional_stock_day_stress",
                "strategy_linked_entry_paths": False,
                "trigger_events_path": str(events_path),
                "trigger_events_sha256": hashlib.sha256(original_bytes).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    captured = []

    def analyze(events, **_kwargs):
        captured.extend(events)
        return {"summary": {}, "baseline": {}, "factors": {}}

    monkeypatch.setattr(
        "scripts.run_local_stop_loss_path_validation.validate_stop_trigger_factor_paths",
        analyze,
    )
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        if self == events_path:
            self.write_text(json.dumps(replacement_event) + "\n", encoding="utf-8")
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    reaudit_local_stop_loss_path_validation(
        existing_report_path=existing_report_path,
        output_dir=tmp_path / "reaudit",
        as_of="2026-07-13",
        horizons=(5,),
        fold_count=1,
        min_signals=1,
    )

    assert captured[0]["code"] == "original"


def test_reaudit_final_gate_failure_creates_no_output_files(tmp_path, monkeypatch):
    module = importlib.import_module("scripts.run_local_stop_loss_path_validation")
    events_path = tmp_path / "events.jsonl"
    event = {
        "date": "2024-01-02",
        "code": "000001",
        "fixed_stop_path": {"trigger_price": 9.7},
        "paper_research_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    event_bytes = (json.dumps(event) + "\n").encode("utf-8")
    events_path.write_bytes(event_bytes)
    existing_report_path = tmp_path / "long-history.json"
    existing_report_path.write_text(
        json.dumps(
            {
                "paper_trading_only": True,
                "no_execution_signals": True,
                "does_not_modify_official_scores": True,
                "bar_interval": "1m",
                "sample_scope": "unconditional_stock_day_stress",
                "strategy_linked_entry_paths": False,
                "trigger_events_path": str(events_path),
                "trigger_events_sha256": hashlib.sha256(event_bytes).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "validate_stop_trigger_factor_paths",
        lambda *_args, **_kwargs: {"summary": {}, "baseline": {}, "factors": {}},
    )
    original_validate = module.validate_no_executable_instructions

    def reject_final_report(payload, *, context):
        if context == "reaudited stop-loss report":
            raise ValueError("final report rejected")
        return original_validate(payload, context=context)

    monkeypatch.setattr(module, "validate_no_executable_instructions", reject_final_report)
    output_dir = tmp_path / "reaudit"

    with pytest.raises(ValueError, match="final report rejected"):
        module.reaudit_local_stop_loss_path_validation(
            existing_report_path=existing_report_path,
            output_dir=output_dir,
            as_of="2026-07-13",
            horizons=(5,),
            fold_count=1,
            min_signals=1,
        )

    assert not output_dir.exists()


def test_reaudit_rejects_nested_executable_event_fields_before_analysis(
    tmp_path, monkeypatch
):
    events_path = tmp_path / "events.jsonl"
    event = {
        "date": "2024-01-02",
        "code": "000001",
        "fixed_stop_path": {"trigger_price": 9.7},
        "evidence": {"orders": [{"side": "sell", "quantity": 100}]},
        "paper_research_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    existing_report_path = tmp_path / "long-history.json"
    existing_report_path.write_text(
        json.dumps(
            {
                "trigger_events_path": str(events_path),
                "trigger_events_sha256": hashlib.sha256(events_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "scripts.run_local_stop_loss_path_validation.validate_stop_trigger_factor_paths",
        lambda *_args, **_kwargs: pytest.fail("unsafe event reached analysis"),
    )

    with pytest.raises(ValueError, match="executable instruction"):
        reaudit_local_stop_loss_path_validation(
            existing_report_path=existing_report_path,
            output_dir=tmp_path / "reaudit",
            as_of="2026-07-13",
            horizons=(5,),
            fold_count=1,
            min_signals=1,
        )


def test_reaudit_requires_complete_guards_for_nonlegacy_events(tmp_path, monkeypatch):
    events_path = tmp_path / "events.jsonl"
    event = {
        "date": "2024-01-02",
        "code": "000001",
        "fixed_stop_path": {"trigger_price": 9.7},
        "paper_research_only": True,
    }
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    existing_report_path = tmp_path / "long-history.json"
    existing_report_path.write_text(
        json.dumps(
            {
                "trigger_events_path": str(events_path),
                "trigger_events_sha256": hashlib.sha256(events_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "scripts.run_local_stop_loss_path_validation.validate_stop_trigger_factor_paths",
        lambda *_args, **_kwargs: pytest.fail("unguarded event reached analysis"),
    )

    with pytest.raises(ValueError, match="no_execution_signals"):
        reaudit_local_stop_loss_path_validation(
            existing_report_path=existing_report_path,
            output_dir=tmp_path / "reaudit",
            as_of="2026-07-13",
            horizons=(5,),
            fold_count=1,
            min_signals=1,
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("broker_order", {"side": "sell", "quantity": 100}, "executable instruction"),
        ("paper_trading_only", False, "paper_trading_only"),
    ],
)
def test_reaudit_rejects_unsafe_preserved_top_level_fields_before_analysis(
    tmp_path,
    monkeypatch,
    field,
    value,
    match,
):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    existing_report = {
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "trigger_events_path": str(events_path),
        "trigger_events_sha256": hashlib.sha256(events_path.read_bytes()).hexdigest(),
        field: value,
    }
    existing_report_path = tmp_path / "long-history.json"
    existing_report_path.write_text(json.dumps(existing_report), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.run_local_stop_loss_path_validation.validate_stop_trigger_factor_paths",
        lambda *_args, **_kwargs: pytest.fail("unsafe report reached analysis"),
    )

    with pytest.raises(ValueError, match=match):
        reaudit_local_stop_loss_path_validation(
            existing_report_path=existing_report_path,
            output_dir=tmp_path / "reaudit",
            as_of="2026-07-13",
            horizons=(5,),
            fold_count=1,
            min_signals=1,
        )
