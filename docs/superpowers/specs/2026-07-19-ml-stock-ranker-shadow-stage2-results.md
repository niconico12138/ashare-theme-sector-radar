# ML Stock Ranker Shadow Stage 2 Results

## Current Real Data

The new immutable archive contains one dated snapshot for 2026-07-16 with 30 active
direction+Linkage V2 selected candidates. It was captured after the signal date, so it
is explicitly `historical_reconstruction`, not strict PIT. There are zero prospective
candidate dates, zero mature 5-day stock-versus-sector excess-label dates, and 128
sector-history dates.

The archive verifier, archive-to-dataset CLI, and training cycle all fail closed at the
unchanged evidence gate. Current readiness is:

```text
model_training_ready=false
strict_pit_eligible=false
prospective_candidate_snapshot_dates=0
verified_training_dates=0
candidate_snapshot_dates=1
candidate_rows=30
promotion_allowed=false
```

Current artifact identities:

```text
archive index SHA: 88d5514e2b98bc3e75893aec2e0ab35a3af93054ccf4ab3bdb78979c73f6076c
archive evidence SHA: 128bd882036cb513d93256942e868f5c09db367ca1f26f9127a8439096bddfd9
archive build readiness SHA: a8b0ec6e62147453e5ffd09804ceed0cee6be4c1d329d3922e872d3358123121
archive build report SHA: 7198546cabdff318c20ad5a53fa2b0443dd4e634465e99b54363ea6db1e933ea
training-cycle readiness SHA: b570fa51cf9416a17142d578f02b62e054eabb445ef8cc657afde1207d999c36
training-cycle report SHA: 3d78052cf1af7049208a07b3136e8e73b09d521de13ecd05300e8799a9f1aaac
readiness audit SHA: f22ebf14444db2754c8d0163900e2b8263c2e863809546eca92a7573eb0c2c61
```

No real model was trained and no production/rule field was changed. Synthetic fixture
training remains architecture-only and cannot be used as real performance evidence.

## Verification

The stage2 focused suite covers naive-source witness handling, raw prediction drift,
immutable daily and mature-label archives, readiness blocking, archive-to-dataset
blocking and strict success, purged training, and Quant/Linkage/Hybrid/ML evaluation.
Final test and source-manifest numbers are recorded in the current planning progress
after the closing full-suite run.

The current verification is `3152 passed, 19 deselected in 59.09s`; focused ML/archive
coverage is `48 passed`. `compileall`, `git diff --check`, strict parsing
(`68 JSON + 1 JSONL/12 lines` inventory), paper-only validation, and the ML protected
field AST write scan (`0` hits) pass. Read-only machine acceptance passes with archive
status `verified`, `1` candidate snapshot, `0` prospective dates, `0` verified training
dates, dataset/cycle `blocked`, and no model directory.
