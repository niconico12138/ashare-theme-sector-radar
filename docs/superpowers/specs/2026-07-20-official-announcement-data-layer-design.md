# Official Announcement Data Layer Design

## Scope

This layer is paper/shadow/research-only. It stores source capability metadata, raw
announcement evidence, structured event records, and source health. It does not
calculate event scores, call an LLM, build event factors, feed sector ML, modify formal
selection, connect to a broker, or create orders.

## Source Registry

`theme_sector_radar/data/official_announcements.py` defines
`official-announcement-source-registry-v1`. The registry covers SSE, SZSE, BSE, CSRC,
MOF, STA, NDRC, MIIT, issuer official announcements, and fund disclosures. It also
records a secondary AkShare adapter and a research-only offline fixture so authority
tier is explicit. Historical coverage, time precision, source version, original-content
policy, SHA policy, retrieval frequency, and cost are separate fields. Real adapters are
metadata-only and `blocked` until network, terms, cadence, and cost are verified.

## Raw Evidence

`archive_raw_announcement()` stores exact bytes under a SHA-addressed path and a strict
JSON manifest. Existing bytes and manifests must match exactly; changed content or
metadata is rejected. The manifest records source URL/path, publication and capture
timestamps, effective date, raw SHA, document version, revision relationship, and
retrieval status.

After-close timestamped announcements can infer the next trading date when a supplied
calendar proves it. Date-only publication is explicitly `date_only` and remains
unresolved rather than being promoted to a precise PIT timestamp.

## Event Ledger And Health

`build_event_record()` stores structured fields and raw-document evidence references.
Score, ranking, signal, confidence, action, and trade fields are rejected. The ledger
deduplicates exact evidence, preserves explicit revisions, and marks same-key divergent
records as conflicts. Source health reports retain retrieval, parsing, and mapping
failures; an incomplete source can never be represented as `no_event`.

The current implementation is offline-fixture and metadata-probe ready. No network
adapter is enabled.

## Risk Event Extension

`theme_sector_radar/data/risk_events.py` is the public facade for the
`canonical-risk-event-v1` contract. Provider internals remain isolated in
`risk_event_providers.py`, `market_anomalies.py`, and `policy_macro_events.py`; every
accepted event passes through `risk_event_schema.py`. The facade accepts official
evidence, policy/macro fixture records, and market observations. The market detector
emits `limit_down`, `near_limit_down`, `large_gap`, `abnormal_volume`, and
`sector_correlation_break` evidence. It uses fixed thresholds and provided historical
baselines; absent or untrusted inputs produce `blocked` or `unknown` events rather than
`no_event`.

Risk events retain source, evidence SHA, provenance, publication precision, effective
date, severity, status, and individual/sector/market scope. The unified ledger performs
exact deduplication, preserves explicit revisions, and surfaces logical conflicts.
Individual, sector, and market aggregation and monitoring alerts remain paper-only and
require human review. The LLM extraction envelope is `enabled=false` and
`reserved_not_run`; it cannot contain score, rank, confidence, action, trade, order,
position, or price fields.

## Primary Official Document Provider

`official_source_providers.py` implements a read-only adapter for explicit CSRC
document URLs under `https://www.csrc.gov.cn/csrc/`. It enforces HTTPS and an exact
official-host allowlist, rejects redirects outside that host, limits response size,
requires HTML, parses the visible publication date, and archives the exact response
bytes before normalization. The immutable manifest records official URL,
`retrieved_at`, `published_at`, unresolved date-only `effective_from`, response SHA-256,
and provider version.

The adapter is runtime terms-gated and defaults to `blocked`. Endpoint reachability is
not treated as permission to automate retrieval. Rate limits, HTTP errors, parse
failures, redirects, and unverified terms all remain `unknown_not_no_event`.

## Commodity Price Evidence

`commodity_prices.py` defines a separate source registry, raw evidence archive,
provider protocol, canonical observation, source health report, and ledger. An
observation binds price date, commodity identity, unit, currency, spot/futures type,
source URL/path, evidence SHA, provider version, observed timestamp, publication
precision, and effective date. NDRC and SHFE are registered as primary candidates but
remain blocked until terms, machine-readable format, units, cadence, and contract
semantics are verified. AkShare is secondary discovery only. The only enabled source
in ordinary tests is an explicit `research_only` fixture.

Missing unit or currency and stale data downgrade to `unknown`; invalid/non-positive
prices and missing evidence are `blocked`. Exact duplicates, explicit revisions, and
logical conflicts remain visible in the commodity ledger.

## Event Impact Shadow

`event_impact_shadow.py` is downstream of the fact layer. It accepts validated risk
events and explicit evidence-bound mapping rules, then emits only
`event_impact_shadow`. Each mapping records sector, upstream/midstream/downstream stage,
positive/negative/mixed/unknown direction, evidence, validity, and decay metadata.
Unmapped or incomplete rules remain `unknown`; they do not mutate formal direction,
selection, Linkage, or ML fields. Protected score and execution fields are recursively
rejected.

The built-in copper increase case is deliberately `research_only`: the same observed
increase maps to a positive upstream producer impact and a negative downstream consumer
impact. It is a contract demonstration, not a factual market claim or trading signal.
