# Path A Linkage V2 Shadow Runbook

## Guardrails

Run only for paper/shadow research. These commands do not connect to a broker and
must not be used to generate live orders. Do not replace the frozen legacy path
until the evaluator reports every promotion gate as true.

## 1. Direction candidates

```powershell
python scripts/select_industry_direction_candidates.py `
  --input reports/paper_shadow/industry_direction_START_to_END/industry_direction_scores.json `
  --output reports/paper_shadow/industry_direction_END/industry_direction_candidates.json
```

## 2. Unified shadow pipeline

The local StockDB SDK is discovered from an explicit constructor path,
`STOCKDB_SDK_PATH`, or `~/Desktop/stockdb/pybao`. The selected directory must
contain both `stock_sdk.py` and `stockdb.pyd`. When HTTP bars are unavailable or
older than the requested date, only the direction V2 shadow branch uses StockDB;
HTTP remains the sole fund-flow source.

```powershell
$unifiedRoot = "reports/paper_shadow/linkage_v2_unified_stockdb"
```

```powershell
python unified_pipeline.py `
  --as-of YYYY-MM-DD `
  --mode quick `
  --sector-history-root data_cache/sector_history `
  --sector-cluster-map config/path_a_sector_clusters.json `
  --output "$unifiedRoot/YYYY-MM-DD"
```

Use a distinct output root while validating a new bars source. Do not overwrite
the preserved HTTP-offline baseline until the strict JSON, coverage, paper-only,
legacy-equality, and independent review gates pass.

The daily wrapper accepts the same history input:

```powershell
python scripts/run_daily_unified_pipeline.py `
  --as-of YYYY-MM-DD `
  --sector-history-root data_cache/sector_history `
  --sector-cluster-map config/path_a_sector_clusters.json
```

### Legacy relevance status

The direction-primary path keeps the complete enriched constituent set after
identity validation. The legacy `relevance_score >= 0.60` threshold is not an
active gate for direction candidates. The bridge still computes the frozen
legacy score on every constituent and records it as `legacy_relevance_score`
for historical comparison only. Formal board-to-stock association is decided
by Linkage V2, followed by the fixed `70% Linkage V2 + 30% Quant` ranking and
the sector/cluster quotas. Explicit `legacy` research mode retains the old
threshold for compatibility and comparison.

## 3. Forward returns

Run this only after the requested future 1/3/5 trading-day labels exist:

```powershell
python scripts/build_a_share_trading_calendar.py `
  --output-path reports/paper_shadow/trading_calendars/a_share_START_to_END.json `
  --start YYYY-MM-DD `
  --end YYYY-MM-DD
$calendarSha = (Get-FileHash reports/paper_shadow/trading_calendars/a_share_START_to_END.json -Algorithm SHA256).Hash.ToLower()
```

```powershell
python scripts/build_forward_returns.py `
  --as-of YYYY-MM-DD `
  --candidate-path "$unifiedRoot/YYYY-MM-DD/unified_report.json" `
  --output-dir reports/paper_shadow/linkage_v2_forward_returns `
  --horizons 1,3,5 `
  --source auto `
  --trading-calendar-path reports/paper_shadow/trading_calendars/a_share_START_to_END.json `
  --expected-calendar-sha256 $calendarSha
```

The builder reads the union of legacy, membership-only, and V2 candidate codes.
Targets come only from the versioned exchange calendar. Missing/suspended target
bars remain missing labels and are never rolled to the next stock bar. Each
available label persists its signal/target QFQ closes, query parameters and bar
snapshot SHA so the evaluator can recompute it.

## 4. A/B/C evaluation

```powershell
python scripts/evaluate_stock_sector_linkage_shadow.py `
  --start YYYY-MM-DD `
  --end YYYY-MM-DD `
  --unified-root $unifiedRoot `
  --forward-root reports/paper_shadow/linkage_v2_forward_returns `
  --trading-calendar-path reports/paper_shadow/trading_calendars/a_share_START_to_END.json `
  --expected-calendar-sha256 $calendarSha `
  --output reports/paper_shadow/linkage_v2_evaluation_YYYY-MM-DD/stock_sector_linkage_shadow_evaluation.json
```

Strict PIT promotion additionally requires an independently verified
`stock_sector_linkage_pit_evidence.v1` document:

```powershell
python scripts/evaluate_stock_sector_linkage_shadow.py `
  --start YYYY-MM-DD `
  --end YYYY-MM-DD `
  --unified-root $unifiedRoot `
  --forward-root reports/paper_shadow/linkage_v2_forward_returns `
  --pit-evidence reports/paper_shadow/linkage_v2_pit_evidence.json `
  --trading-calendar-path reports/paper_shadow/trading_calendars/a_share_START_to_END.json `
  --expected-calendar-sha256 $calendarSha `
  --output reports/paper_shadow/linkage_v2_evaluation_YYYY-MM-DD/stock_sector_linkage_shadow_evaluation.json
```

The evaluator does not self-certify PIT evidence. The independent provenance
auditor must bind the exact document dates and canonical source-manifest SHA.
Without that file the gate remains `strict_pit_eligible=false`.

Treat missing labels as missing coverage. Never silently drop dates, relax the
minimum evidence weight, or call a non-PIT replay strict PIT.
