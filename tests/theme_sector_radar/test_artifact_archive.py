from pathlib import Path

import theme_sector_radar.reporting.artifact_archive as artifact_archive
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous


def test_changed_canonical_artifact_preserves_previous_content_by_hash(tmp_path):
    path = tmp_path / "report.json"

    first_archive = write_text_preserving_previous(path, '{"version": 1}\n')
    second_archive = write_text_preserving_previous(path, '{"version": 2}\n')

    assert first_archive is None
    assert second_archive is not None
    assert second_archive.exists()
    assert second_archive.read_text(encoding="utf-8") == '{"version": 1}\n'
    assert path.read_text(encoding="utf-8") == '{"version": 2}\n'


def test_identical_rerun_does_not_create_archive(tmp_path):
    path = tmp_path / "report.md"
    write_text_preserving_previous(path, "same\n")

    archived = write_text_preserving_previous(path, "same\n")

    assert archived is None
    assert list(tmp_path.glob("report.*.md")) == []


def test_canonical_artifact_is_installed_with_atomic_replace(tmp_path, monkeypatch):
    path = tmp_path / "report.json"
    destinations = []
    real_replace = artifact_archive.os.replace

    def recording_replace(source, destination):
        destinations.append(Path(destination))
        return real_replace(source, destination)

    monkeypatch.setattr(artifact_archive.os, "replace", recording_replace)

    write_text_preserving_previous(path, '{"version": 1}\n')

    assert path in destinations
    assert list(tmp_path.glob("*.tmp")) == []
