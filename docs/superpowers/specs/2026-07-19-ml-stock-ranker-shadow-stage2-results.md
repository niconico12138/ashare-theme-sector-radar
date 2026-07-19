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
archive build readiness SHA: ab2e067be40007a70598ef7ad471c54a0202b10083ea6fdfa1154320d91fbefa
training-cycle report SHA: dd1cfbf9eea0ef669e4bf0a27157f60238fa1481400c567a9d73edd23b89b052
readiness audit SHA: b3a8031df43f12a09e95c3f73f91737affdf1fb001079d80f41c64fc9d916060
```

No real model was trained and no production/rule field was changed. Synthetic fixture
training remains architecture-only and cannot be used as real performance evidence.

## Verification

The stage2 focused suite covers naive-source witness handling, raw prediction drift,
immutable daily and mature-label archives, readiness blocking, archive-to-dataset
blocking and strict success, purged training, and Quant/Linkage/Hybrid/ML evaluation.
Final test and source-manifest numbers are recorded in the current planning progress
after the closing full-suite run.

The current closing verification is `3149 passed, 19 deselected in 42.26s`; focused
ML/archive/release coverage is `49 passed`. `compileall`, `git diff --check`, strict parsing
(`54 JSON + 1 JSONL/12 lines` inventory), and the protected-field write scan (`0` hits) pass.
