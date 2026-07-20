"""Terms-gated read-only adapters for primary official documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

from .official_announcements import archive_raw_announcement, infer_effective_from


CSRC_PROVIDER_VERSION = "csrc-official-html-document-v1"
CSRC_ALLOWED_HOST = "www.csrc.gov.cn"
_ARTICLE_TITLE = re.compile(
    r'<meta\s+name=["\']ArticleTitle["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_VISIBLE_DATE = re.compile(r"日期\s*[：:]\s*(\d{4}-\d{2}-\d{2})")


def _blocked(*, url: str, reason: str, retrieved_at: str | None = None) -> dict[str, Any]:
    return {
        "provider_id": "csrc_notices",
        "provider_version": CSRC_PROVIDER_VERSION,
        "status": "blocked",
        "retrieval_status": "blocked",
        "event_state": "unknown_not_no_event",
        "official_url": url,
        "retrieved_at": retrieved_at,
        "reason": reason,
        "manifest": None,
        "promotion_allowed": False,
        "live_trading_allowed": False,
    }


def parse_csrc_document_metadata(raw_content: bytes) -> dict[str, str | None]:
    text = raw_content.decode("utf-8", errors="replace")
    title_match = _ARTICLE_TITLE.search(text)
    date_match = _VISIBLE_DATE.search(text)
    return {
        "title": title_match.group(1).strip() if title_match else None,
        "published_at": date_match.group(1) if date_match else None,
    }


@dataclass
class CsrcOfficialDocumentProvider:
    """Fetch one explicit CSRC document URL; list crawling is intentionally absent."""

    terms_verified: bool = False
    timeout_seconds: float = 15.0
    max_response_bytes: int = 5_000_000
    session: Any = None
    provider_id: str = "csrc_notices"
    provider_version: str = CSRC_PROVIDER_VERSION

    def fetch_document(
        self,
        url: str,
        *,
        archive_root: Path | str,
        retrieved_at: str | None = None,
    ) -> dict[str, Any]:
        timestamp = retrieved_at or datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != CSRC_ALLOWED_HOST or not parsed.path.startswith("/csrc/"):
            return _blocked(url=url, reason="official_url_not_allowlisted", retrieved_at=timestamp)
        if not self.terms_verified:
            return _blocked(url=url, reason="source_terms_not_verified", retrieved_at=timestamp)
        client = self.session or requests.Session()
        try:
            response = client.get(
                url,
                timeout=self.timeout_seconds,
                allow_redirects=True,
                headers={"User-Agent": "theme-sector-radar-research/0.1"},
            )
        except (requests.RequestException, RuntimeError) as exc:
            return _blocked(url=url, reason=f"retrieval_failed:{type(exc).__name__}", retrieved_at=timestamp)
        final_url = str(getattr(response, "url", url))
        if urlparse(final_url).hostname != CSRC_ALLOWED_HOST:
            return _blocked(url=url, reason="redirect_left_official_host", retrieved_at=timestamp)
        status_code = int(getattr(response, "status_code", 0))
        if status_code != 200:
            reason = "rate_limited" if status_code == 429 else f"http_status_{status_code}"
            return _blocked(url=final_url, reason=reason, retrieved_at=timestamp)
        content = bytes(getattr(response, "content", b""))
        content_type = str(getattr(response, "headers", {}).get("Content-Type", "")).casefold()
        if not content or len(content) > self.max_response_bytes or "html" not in content_type:
            return _blocked(url=final_url, reason="invalid_official_response", retrieved_at=timestamp)
        metadata = parse_csrc_document_metadata(content)
        pit = (
            infer_effective_from(metadata["published_at"])
            if metadata["published_at"]
            else {"effective_from": None, "inference_status": "published_at_parse_failed"}
        )
        manifest = archive_raw_announcement(
            archive_root,
            source_id=self.provider_id,
            source_url_or_path=final_url,
            published_at=metadata["published_at"],
            captured_at=timestamp,
            effective_from=pit["effective_from"],
            raw_content=content,
            provider_version=self.provider_version,
        )
        if not metadata["title"] or not metadata["published_at"]:
            return {
                **_blocked(url=final_url, reason="official_document_parse_failed", retrieved_at=timestamp),
                "retrieval_status": "parse_failed",
                "manifest": manifest,
            }
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "status": "observed",
            "retrieval_status": "retrieved",
            "event_state": "observed",
            "official_url": final_url,
            "retrieved_at": timestamp,
            "published_at": metadata["published_at"],
            "effective_from": pit["effective_from"],
            "effective_inference_status": pit["inference_status"],
            "title": metadata["title"],
            "raw_sha256": manifest["raw_sha256"],
            "manifest": manifest,
            "promotion_allowed": False,
            "live_trading_allowed": False,
        }


__all__ = [
    "CSRC_PROVIDER_VERSION",
    "CsrcOfficialDocumentProvider",
    "parse_csrc_document_metadata",
]
