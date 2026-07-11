# Joint Decision Summary Schema

`joint_decision_summary` is the stable watch-only decision artifact produced at:

`reports/joint_decision/{as_of}/joint_decision_summary.json`

It is intended to become the pre-decision input for later automation. In the current system it is strictly observational. It must not produce trade candidates, buy points, price levels, or execution actions.

## Top-Level Contract

Required top-level fields:

- `schema_version`: currently `1.0`.
- `as_of`: trading date in `YYYY-MM-DD` format.
- `decision_mode`: always `watch_only`.
- `system_status`: run health and data quality summary.
- `risk_gate`: stable pre-decision gate summary.
- `sector_decision`: sector watch buckets.
- `stock_decision`: stock watch buckets.
- `factor_context`: official, shadow-only, and profile-only factor context.
- `agent_review`: optional Agent review coverage and state summary.
- `risk_review`: legacy-compatible warnings and blockers.
- `audit`: source artifact and generation audit metadata.

## Risk Gate

`risk_gate` must keep this stable shape:

```json
{
  "allow_observation": true,
  "allow_trade_candidate_generation": false,
  "blockers": [],
  "warnings": [],
  "gate_details": {
    "data_quality_gate": {"status": "pass", "allow_observation": true, "blockers": [], "warnings": []},
    "run_health_gate": {"status": "pass", "allow_observation": true, "blockers": [], "warnings": []},
    "market_regime_gate": {"status": "unknown", "allow_observation": true, "blockers": [], "warnings": []},
    "factor_quality_gate": {"status": "ok", "allow_observation": true, "blockers": [], "warnings": []},
    "agent_consensus_gate": {"status": "confirmed", "allow_observation": true, "blockers": [], "warnings": []}
  }
}
```

`allow_trade_candidate_generation` is always `false` in schema version `1.0`. A downstream consumer may observe and review the data, but must not treat this artifact as permission to generate orders or execution candidates.

## Stock Decision Item

Every stock item should include these machine-readable fields while preserving legacy top-level score fields for compatibility:

```json
{
  "code": "600001",
  "name": "Example",
  "sector_name": "Example Sector",
  "decision_bucket": "core_watch",
  "opportunity_type": "trend_follow",
  "action_state": "watch_only",
  "scores": {
    "final_score": 76.0,
    "v2_score": 61.0,
    "selection_score": 71.5,
    "selection_score_adjusted": 73.0
  },
  "factor_states": {
    "trend_state": "trend_follow",
    "sector_support": "confirmed",
    "breakout_structure": "near_breakout",
    "drawdown_state": "controlled",
    "liquidity_state": "available",
    "overheat_state": "normal"
  },
  "reason_codes": [],
  "invalidation_flags": [],
  "manual_review_reason": []
}
```

`scores.final_score`, `scores.v2_score`, `scores.selection_score`, and `scores.selection_score_adjusted` are copied from upstream artifacts. The joint decision layer must not recalculate or reweight them.

## Audit

`audit` must include:

- `source_artifacts`: booleans for `unified_report`, `top30_candidates`, `aihf_ranking`, and `v2_monitor`.
- `generated_at`: UTC timestamp ending in `Z`.
- `shadow_only`: always `true` for this stage.


## Validation And Consumption

The runner calls `validate_joint_decision_summary` before writing `joint_decision_summary.json`. The result is embedded under `audit.contract_validation`:

```json
{
  "status": "pass",
  "errors": []
}
```

A non-empty `errors` list means the artifact is not valid for downstream automated consumption. It is still a diagnostic artifact, but consumers must treat it as blocked.

`show_daily_result` must only prefer an existing `joint_decision_summary` when `validate_joint_decision_summary` returns no errors. If validation fails, `show_daily_result` falls back to the legacy daily summary path when a `unified_report` is available, or reports the missing input path when no valid source exists.

## Forbidden Fields And Meanings

The schema must not add execution semantics. These names are explicitly forbidden as active output fields or active policy meanings:

- `buy_point`
- `entry_price`
- `trigger_price`
- `stop_loss`
- `take_profit`
- `execute_trade`

Related concepts such as order creation, position sizing, broker submission, and trade execution remain out of scope for `schema_version = 1.0`.

