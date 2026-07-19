import json
import zipfile

import pytest

from scripts.run_local_stop_loss_sample import main, run_local_stop_loss_sample


def test_run_local_stop_loss_sample_writes_event_dataset(tmp_path):
    archive_path = tmp_path / "2024_1min.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "sz000001_2024.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024-01-02 09:30:00,sz000001,a,10,10,10,10,1,1\n"
            "2024-01-02 15:00:00,sz000001,a,9.5,9.5,9.6,9.4,1,1\n",
        )
        archive.writestr(
            "sz000002_2024.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024-01-02 09:30:00,sz000002,b,10,10,10,10,1,1\n"
            "2024-01-02 15:00:00,sz000002,b,10.1,10.1,10.2,10,1,1\n",
        )

    result = run_local_stop_loss_sample(
        stock_archives=[archive_path],
        codes=["000001", "000002"],
        output_dir=tmp_path / "out",
        as_of="2026-07-13",
    )

    data = json.loads(result["json_path"].read_text(encoding="utf-8"))
    assert data["summary"]["negative_event_count"] == 1
    assert data["events"][0]["control_code"] == "000002"
    assert result["markdown_path"].exists()


def test_run_local_stop_loss_sample_excludes_rows_after_as_of(tmp_path):
    archive_path = tmp_path / "2024_1min.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "sz000001_2024.csv",
            "时间,代码,名称,开盘价,收盘价,最高价,最低价,成交量,成交额\n"
            "2024-01-02 09:30:00,sz000001,a,10,10,10,10,1,1\n"
            "2024-01-02 15:00:00,sz000001,a,9.5,9.5,9.6,9.4,1,1\n"
            "2024-01-03 09:30:00,sz000001,a,10,10,10,10,1,1\n"
            "2024-01-03 15:00:00,sz000001,a,9,9,9.1,8.9,1,1\n",
        )

    result = run_local_stop_loss_sample(
        stock_archives=[archive_path],
        codes=["000001"],
        output_dir=tmp_path / "out",
        as_of="2024-01-02",
    )

    report = result["report"]
    assert report["summary"]["record_count"] == 1
    assert report["year_record_counts"] == {"2024": 1}


def test_run_local_stop_loss_sample_cli_rejects_nonfinite_codes_json(tmp_path):
    codes_path = tmp_path / "codes.json"
    codes_path.write_text('{"codes": NaN}', encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        main(
            [
                "--stock-archive",
                str(tmp_path / "unused.zip"),
                "--codes-json",
                str(codes_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--as-of",
                "2026-07-13",
            ]
        )
