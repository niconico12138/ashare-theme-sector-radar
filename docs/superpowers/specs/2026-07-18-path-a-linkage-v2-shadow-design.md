# Path A Linkage V2 Shadow Design

## Scope

This change improves only the sector-to-stock linkage portion of Path A. It does
not change the sector data architecture, Path B/C architecture, production
trend/burst selection, or protected scoring fields. The local bars adapter gains
strict SDK discovery for this shadow branch. It is paper/shadow research only.

## Frozen control

Group A retains the existing trend Top5 + burst Top5 universe and requires
legacy relevance of at least 0.60. The legacy formula and its stable policy SHA
are emitted in every bridge report. A separate effective-policy contract binds
the Top-N and threshold actually executed, so research overrides cannot masquerade
as the frozen baseline.

## Shadow branch

Direction candidates are loaded from a date-bound strict JSON artifact. Core and
supplemental sectors may fetch constituents; confirmation-required sectors remain
metadata only. Parse or provenance failure degrades only the shadow branch.
Direction-only quote and individual-flow requests are executed separately from
legacy requests; shadow failures cannot alter legacy candidate inputs or health.

Every pre-filter constituent row records source, weight usefulness, quote and
fund-flow availability, and legacy linkage details. Linkage V2 combines return
co-movement, relative strength, constituent weight, fund-flow alignment, and data
quality. Missing evidence is not rewarded, non-finite values fail closed, and
less than 50% available configured weight yields `unavailable`.

The selector ranks only usable V2 rows with 70% V2 linkage and 30% existing quant
score, then applies core/supplemental sector quotas, a 30-stock cap, and a 40%
cluster cap measured against the actual final selected count. When the available
clusters cannot form a non-empty portfolio within that ratio, selection fails
closed to zero. This selection is emitted only as
`direction_linkage_v2_selection_shadow`.

Sector clusters come from a strict, SHA-bound paper-only configuration. Unmapped
sectors share a conservative `__unmapped__` cluster; a missing map cannot silently
fall back to independent sector-name buckets. Legacy and V2 concentration are
evaluated using the same cluster mapping. Every replay date must carry the same
source and canonical-mapping SHA; row-level cached cluster labels are overwritten
from that contract. The promotion gate compares worst-date maximum cluster share,
while the average daily maximum remains descriptive only.

## Evaluation and promotion

The evaluator compares A legacy, B membership-only, and C linkage V2 using
1/3/5-day returns, positive-label rate, coverage, 1-day pseudo-equity drawdown,
turnover, and maximum sector concentration. Promotion requires every gate listed
in `.planning/path-a-linkage-v2/task_plan.md`; failing any gate leaves
`promotion_status=insufficient_evidence`.

The coverage gate applies to both A and C on every compared horizon. Strict PIT
eligibility is derived only from a verified, date-aligned evidence contract; a
caller-supplied boolean is not accepted as proof.
The C path must also provide labeled observations on at least 60 dates and at
least 90% of replay dates. Empty-selection dates do not lower measured concentration.

Legacy stock-info and fund-flow source statistics are snapshotted before the
direction branch runs. Direction runtime statistics are reported separately and
cannot overwrite legacy health or provenance output.

## Direction-only StockDB bars

The direction V2 branch may route daily bars through `AutoBarsClient`. The
desktop SDK is discovered at runtime from an explicit path,
`STOCKDB_SDK_PATH`, or `~/Desktop/stockdb/pybao`; both `stock_sdk.py` and
`stockdb.pyd` must exist, and the unrelated PyPI package named `stock_sdk` is
never imported as a fallback. HTTP remains the only fund-flow client.

This bars override is passed only to direction shadow scoring. Production
trend/burst calls retain their previous HTTP/fallback behavior. Compact
StockDB dates are adapted to canonical ISO only at the strict V2 return
boundary. Runtime audit fields identify the selected bars source, reason,
latest date, unique-stock coverage, and stock-sector relation coverage. If
both sources fail, bars remain unavailable and V2 fails closed.
When an expected minimum date is present, a source is eligible only when its
reported latest daily date meets that boundary; two stale sources also fail
closed. SDK initialization errors remain source metadata and cannot overwrite a
successful HTTP bars audit.

## Safety

There is no broker adapter, order object, or live instruction in this design.
Reports carry `paper_shadow_research_only` and a no-broker/no-live-order disclaimer.
