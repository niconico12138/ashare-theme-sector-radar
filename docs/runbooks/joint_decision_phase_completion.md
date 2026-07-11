# Joint Decision Phase Completion

This document records the completion state for the `joint_decision_summary` refactor phase.

## Completion Level

The joint decision layer is considered 90% complete for the current watch-only automation-preparation milestone.

Completed scope:

- stable `joint_decision_summary` schema version `1.0`
- stable `risk_gate` with `gate_details`
- stable stock machine fields: `scores`, `factor_states`, `reason_codes`, `invalidation_flags`, and `manual_review_reason`
- `validate_joint_decision_summary` contract validator
- runner-level validation embedded as `audit.contract_validation`
- `show_daily_result` consumption guard for invalid joint summaries
- runbook documentation for schema and phase completion
- non-LLM regression coverage

## Operational Contract

The phase remains strictly `watch_only`.

Required invariants:

- `decision_mode` is `watch_only`
- `risk_gate.allow_trade_candidate_generation` is `false`
- stock `action_state` is `watch_only`
- `audit.shadow_only` is `true`
- generated summaries include `audit.contract_validation.status` and `audit.contract_validation.errors`

`show_daily_result` must prefer `joint_decision_summary` only when `validate_joint_decision_summary` returns no errors. Invalid joint summaries must be treated as blocked for machine consumption and should fall back to the legacy daily summary path when possible.

## Score Boundary

The joint decision layer does not recalculate or reweight these scores:

- `final_score`
- `v2_score`
- `selection_score`
- `selection_score_adjusted`

They are copied from upstream artifacts into the stable `scores` object for downstream readers.

## Explicit Non-Goals

The following are not implemented in this phase:

- automatic trading
- buy point generation
- entry or trigger price generation
- stop loss or take profit generation
- order creation
- broker submission
- position sizing

Any future automatic trading layer must be built as a separate approval layer and must not reinterpret this watch-only schema as execution permission.

## Verification Scope

Use non-LLM verification for this phase. Do not run LLM agent tests unless explicitly requested.

Current verification targets:

```text
python -m pytest tests\theme_sector_radar\test_run_daily_orchestrator.py tests\theme_sector_radar\test_show_daily_result.py tests\theme_sector_radar\test_joint_decision.py tests\theme_sector_radar\test_joint_decision_schema_contract.py tests\theme_sector_radar\test_daily_decision_summary.py tests\theme_sector_radar\test_daily_compact_report.py tests\theme_sector_radar\test_selection_quality.py -q
python run_daily.py --as-of 2026-07-10 --quick --dry-run
python scripts\run_joint_decision.py --as-of 2026-07-10 --top-n 5
python scripts\show_daily_result.py --as-of 2026-07-10 --format compact --top-n 5
```

## Remaining Work After 90%

Remaining work is operational hardening rather than schema design:

- decide commit split and staging strategy
- review real daily output with domain judgement
- add release notes if this is promoted to a tagged version
- decide whether a future trading approval layer is needed
