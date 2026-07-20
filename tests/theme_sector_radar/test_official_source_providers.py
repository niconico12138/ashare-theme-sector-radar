from __future__ import annotations

import hashlib


RETRIEVED_AT = "2026-07-20T16:00:00+08:00"
OFFICIAL_URL = "https://www.csrc.gov.cn/csrc/c100028/c1615676/content.shtml"


class FakeResponse:
    def __init__(self, content: bytes, *, status_code: int = 200, url: str = OFFICIAL_URL):
        self.content = content
        self.status_code = status_code
        self.url = url
        self.headers = {"Content-Type": "text/html; charset=UTF-8"}


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def _official_html():
    return (
        '<html><head><meta name="ArticleTitle" content="Official policy notice"/>'
        '</head><body><p class="fl">date placeholder</p>'
        '<p>date: ignored</p><p>\u65e5\u671f\uff1a2021-12-10 source: CSRC</p></body></html>'
    ).encode("utf-8")


def test_csrc_registry_is_adapter_ready_but_probe_remains_terms_blocked():
    from theme_sector_radar.data.official_announcements import default_source_registry, probe_source_registry

    registry = default_source_registry()
    csrc = next(row for row in registry["sources"] if row["source_id"] == "csrc_notices")
    assert csrc["adapter_status"] == "ready"
    assert csrc["authority_tier"] == "primary"
    probe = next(row for row in probe_source_registry(registry)["sources"] if row["source_id"] == "csrc_notices")
    assert probe["probe_status"] == "blocked"
    assert "terms" in probe["reason"]


def test_csrc_provider_defaults_to_blocked_without_touching_network(tmp_path):
    from theme_sector_radar.data.official_source_providers import CsrcOfficialDocumentProvider

    session = FakeSession(FakeResponse(_official_html()))
    result = CsrcOfficialDocumentProvider(session=session).fetch_document(
        OFFICIAL_URL, archive_root=tmp_path, retrieved_at=RETRIEVED_AT
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "source_terms_not_verified"
    assert result["event_state"] == "unknown_not_no_event"
    assert session.calls == []


def test_csrc_provider_archives_official_raw_bytes_sha_and_pit_metadata(tmp_path):
    from theme_sector_radar.data.official_source_providers import (
        CSRC_PROVIDER_VERSION,
        CsrcOfficialDocumentProvider,
    )

    raw = _official_html()
    session = FakeSession(FakeResponse(raw))
    result = CsrcOfficialDocumentProvider(terms_verified=True, session=session).fetch_document(
        OFFICIAL_URL, archive_root=tmp_path, retrieved_at=RETRIEVED_AT
    )
    manifest = result["manifest"]
    assert result["status"] == "observed"
    assert result["published_at"] == "2021-12-10"
    assert result["effective_from"] is None
    assert result["effective_inference_status"] == "date_only_unresolved"
    assert result["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert manifest["source_url_or_path"] == OFFICIAL_URL
    assert manifest["retrieved_at"] == RETRIEVED_AT
    assert manifest["provider_version"] == CSRC_PROVIDER_VERSION
    assert manifest["published_time_precision"] == "date_only"
    assert open(manifest["raw_path"], "rb").read() == raw
    assert session.calls[0][1]["allow_redirects"] is True


def test_csrc_provider_rate_limit_and_parse_failure_are_not_no_event(tmp_path):
    from theme_sector_radar.data.official_source_providers import CsrcOfficialDocumentProvider

    limited = CsrcOfficialDocumentProvider(
        terms_verified=True,
        session=FakeSession(FakeResponse(b"limited", status_code=429)),
    ).fetch_document(OFFICIAL_URL, archive_root=tmp_path / "limited", retrieved_at=RETRIEVED_AT)
    assert limited["status"] == "blocked"
    assert limited["reason"] == "rate_limited"
    assert limited["event_state"] == "unknown_not_no_event"

    raw = b"<html><body>no metadata</body></html>"
    failed = CsrcOfficialDocumentProvider(
        terms_verified=True,
        session=FakeSession(FakeResponse(raw)),
    ).fetch_document(OFFICIAL_URL, archive_root=tmp_path / "parse", retrieved_at=RETRIEVED_AT)
    assert failed["status"] == "blocked"
    assert failed["retrieval_status"] == "parse_failed"
    assert failed["manifest"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()

