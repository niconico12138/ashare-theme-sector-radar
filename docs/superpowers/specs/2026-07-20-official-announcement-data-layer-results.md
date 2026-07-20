# Official Announcement Data Layer Results

Implemented the isolated announcement data layer in
`theme_sector_radar/data/official_announcements.py`.

- Added a versioned source-capability registry for the requested official authorities,
  issuer announcements, and fund disclosures, with primary/secondary/research-only
  tiers and explicit pending-verification fields.
- Added no-network source probing. Real sources report `blocked`; only the offline
  fixture reports `fixture_ready`.
- Added immutable SHA-256 raw-byte archives and strict manifests with publication,
  capture, effective-date, version, revision, and retrieval fields.
- Added conservative after-close effective-date inference and explicit `date_only`
  handling.
- Added a structured event ledger with evidence references, exact deduplication,
  revision preservation, conflict surfacing, and rejection of score/action fields.
- Added source health reporting that keeps retrieval, parse, and mapping failures
  visible and rejects `no_event` as an unsupported shortcut.
- Added focused offline tests in
  `tests/theme_sector_radar/test_official_announcements.py`.

No LLM, event factor, sector ML, formal selection, broker, order, or protected score
path was changed by this data layer.

## Risk Event Extension

The risk extension is exposed through
`theme_sector_radar/data/risk_events.py`, with independent schema, provider, detector,
ledger, and monitoring modules. It adds:

- unified risk-event/ledger/report schemas with source, evidence SHA, provenance, PIT,
  severity, status, and individual/sector/market scope;
- deterministic and statistical market anomaly detection for limit-down/near-limit,
  large gaps, abnormal volume, and stock-sector correlation breaks;
- an `adapt_policy_macro_fixture` public facade, offline policy/macro fixture archival,
  and an explicitly blocked real-source registry;
- disabled LLM Shadow extraction (`enabled=false`, `reserved_not_run`);
- evidence fusion, duplicate/conflict handling, three-level aggregation, and human-review
  risk alert payloads.

Missing market inputs become `blocked` or `unknown`; failed retrieval, parsing, or
fixture mapping is never represented as `no_event`. No formal score, Linkage, ML,
broker, order, or live path is used.

## Verification

- `tests/theme_sector_radar/test_risk_events.py`: `9 passed`.
- Risk events, official announcements, strict JSON, and existing catalyst regressions:
  `77 passed`.
- Scoped `compileall`: passed.
- `git diff --check`: passed before the full-suite run.
- Full `pytest -q`: collection completed with zero ImportErrors; final result was
  `3315 passed, 19 deselected`.

## Real-Source And Commodity Research Stage

Implemented:

- `official_source_providers.py`: a CSRC explicit-document, primary-source, read-only
  adapter with official-host enforcement, raw response archival, SHA-256, provider
  version, publication date parsing, PIT metadata, rate-limit handling, and fail-closed
  status.
- `commodity_prices.py`: commodity source registry, provider contract, immutable raw
  evidence, canonical spot/futures observation, health report, quality downgrade, and
  duplicate/revision/conflict ledger.
- `event_impact_shadow.py`: independent evidence-bound event-to-sector mapping with
  value-chain stage, direction, validity, decay metadata, human review, and recursive
  protected-field rejection.
- A research-only copper price increase case showing `upstream/positive` for producers
  and `downstream/negative` for consumers.

External read-only reachability probes on 2026-07-20 returned HTTP 200 for the CSRC,
NDRC, and Ministry of Finance public pages. A sampled CSRC article exposed an official
ArticleTitle and a visible date-only publication date. These probes were not persisted
as project data and do not establish automation terms. The CSRC implementation therefore
defaults to `terms_verified=false` and returns `blocked`; NDRC, SHFE, and all other real
commodity adapters remain blocked. No fixture is reported as real-source success.

Stage verification:

- Primary-provider, commodity, impact, announcement, and unified-risk focused set:
  `24 passed`.
- Related risk, announcement, strict-JSON, and catalyst regression set: `87 passed`.
- Ordinary tests use injected HTTP responses; no test performs network I/O.
- The full-suite result supersedes the earlier dirty-worktree snapshot that recorded
  three ML provenance failures; the current run has no failures and no collection errors.
