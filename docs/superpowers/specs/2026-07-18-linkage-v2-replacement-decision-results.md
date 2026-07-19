# Linkage V2 Replacement Decision Results

## Scope

This document records the independent replacement decision for the formal
stock-sector linkage path. It is separate from the Stage 8 StockDB activation
report. All work is `paper_shadow_research_only`; no broker connection and no
live order instruction were generated.

## Evidence Window

- Evaluated signal date: `2026-07-16`
- Evaluated date count: `1`
- Same-day candidate universe: `590` stocks
- Mature 1-day forward-label coverage: `568/590` (`96.27%`)
- StockDB latest usable daily date at run time: `2026-07-17`
- Mature horizons: `1d` only; `3d` and `5d` are unavailable
- Historical constituent universe versioned: `false`
- Strict PIT eligible: `false`

The direction history has more dates, but no date-bound stock-sector unified
reports and no versioned historical constituent universes exist for those dates.
It is therefore not valid to relabel the direction-only history as an A/B/C
stock-bridge replay.

## A/B/C Results

| Group | Definition | Candidates | 1d coverage | Mean return | Same-day universe excess | Stock win rate |
|---|---|---:|---:|---:|---:|---:|
| A | Frozen Legacy relevance path | 448 | 431/448 (96.21%) | -4.9668% | +0.8829% | 3.71% |
| B | Direction membership-only control | 554 | 536/554 (96.75%) | -6.0421% | -0.1923% | 2.99% |
| C | Linkage V2 selection and quotas | 30 | 30/30 (100%) | -4.2784% | +1.5714% | 13.33% |

The paired C-minus-A difference is `+0.6885` percentage points on exactly one
date. This is an observation, not evidence of a stable strategy advantage.
All 30 C selections are `partial`; the `ok`-only sensitivity set is empty.
The maximum cluster share is 33.33% for C versus 79.24% for A on this date.

## Gate Decision

`promotion_status=insufficient_evidence`. The formal path was **not** switched.
Legacy remains the only formal linkage path; V2 remains paper/shadow.

Failed gates include:

- At least 60 dates and three months
- Historical constituent universe versioning
- Strict PIT evidence from a trusted verifier
- C observations on at least 90% of replay dates
- Joint 1/3/5-day label coverage
- 3/5-day excess return and stock win-rate comparisons
- Turnover comparison
- Market-regime stability
- Date and industry concentration stability
- Usable `ok`-only sensitivity evidence

Forward-label maturity, cluster-map consistency, one-day drawdown, and the
one-date concentration comparison pass. No gate was relaxed to obtain this
result, and caller-supplied PIT claims cannot promote the path.

## Artifact Provenance

- Unified StockDB report SHA256: `877efcc5bcaac814de3f76bdaa62443027f951af1c38cf57937680f9ecf1daae`
- Exchange-calendar artifact SHA256: `2bd31d69ab928e890c74dfd4b24122f6ca42e70bb9ce59211b604de3dc3233af`
- Forward-label v2 artifact SHA256: `d17e592c00f070de3e491b07d50ce3218177f052dfdef8bb1cefcdecd349c75a`
- Replacement evaluation JSON SHA256: `280d7861fc6c133444dfea9dbaee8f2259a76cc89be4c8a91c1742be798adb8d`
- Replacement evaluation Markdown SHA256: `a4666e4d1a54fdcee60646a1a7f1e98adac5327bdb3fa3425324e954e32af00d`

Forward v2 binds every horizon to the versioned exchange calendar, never to a
stock's next available bar. Available returns persist and revalidate signal and
target QFQ closes, source query parameters and per-stock bar snapshot SHA.

The earlier Stage 8 activation evaluation SHA `7d64f3d588130e9896be18793d13cddd1f54c5fe5b4260789e23e4fdc1ca8357`
remains a historical one-date StockDB activation artifact. It is not the
replacement-decision artifact and is not used as promotion evidence here.

## Formal Activity-Chain Activation (2026-07-19)

The promotion decision above remains intentionally unchanged: `promotion_status=insufficient_evidence`, Legacy remains the frozen scoring baseline, and V2 is not promoted as a production scoring policy. Separately, the unified Paper/Shadow candidate source is now formally wired as `direction_score_shadow -> linkage_v2_shadow -> formal_candidate_selection`.

- Unified report: `test_output/formal_replacement_2026-07-16-with-history-stockdb/unified_report.json`, SHA `6ebca8c3db369a357fac1f9d09e0f30223e58e0e6ba79988ea4afe1d5c701e73`.
- Direction input SHA: `44c776aec07052f9152ba634b7b9ac739f926704bcb66c14f936562134867152`; cluster-map SHA: `06cd454ce47cdb690a0a1c3f67a699528ca93e8e710935ae81be501a0fa4c77b`.
- Active result: `active_for_paper_research`, 30 selected rows, 1,001/1,029 relation coverage, 540/554 unique-stock coverage, maximum cluster ratio `0.333333`, all selected V2 rows `partial` or `ok`.
- Verification: full pytest `3137 passed, 19 deselected`; focused chain `287 passed`; strict JSON `261 + 1 JSONL/12 lines`; protected-field and paper-only checks pass; no broker or executable instruction path exists. Independent Review A and Review B both return `Critical=0, Important=0, Minor=0`.
