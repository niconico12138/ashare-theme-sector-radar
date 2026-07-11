# Factor Catalog

> Version: 1.0 | Date: 2026-07-11 | Scope: three-project joint stock-selection system

## 1. Purpose

This catalog is the management layer for the current factor library. It records what each factor means, where it comes from, how it is allowed to be used, and whether it affects the official candidate ranking.

The catalog complements:

- `theme_sector_radar/factors/registry.py`: executable factor metadata.
- `docs/runbooks/factor_semantics_contract.md`: semantic guardrails for bars factors and report wording.
- `factor_snapshot`: per-candidate factor payload used by reports, backfills, and evaluations.

## 2. Usage Layers

| Usage layer | Meaning | Can affect official ranking |
|---|---|---|
| `official_score` | Official candidate score or primary pool construction field. | Yes |
| `pool_signal` | Used to form trend/short observation pools or candidate groups. | Partial |
| `selection_quality` | Used to describe observation quality, not to reorder the official pool. | No |
| `shadow_score` | Used for shadow validation, independent discovery, or monitoring. | No |
| `stock_profile` | Used to build stock profile states and context fields. | No |
| `risk_review` | Used for warning, review, or risk context. | No |
| `explanation_only` | Used in reason codes, report explanation, or AIHF context. | No |
| `research_only` | Kept for research or attribution; not wired into the daily decision flow. | No |

Global rule: only `official_score` and selected `pool_signal` fields may shape the current official candidate flow. All other layers remain `watch_only` / shadow-only unless a later, tested stage explicitly promotes them.

## 3. Current System Factor Catalog

These factors are registered in `FACTOR_REGISTRY` and are part of the current engineering factor library.

| factor_id | Display name | Category | Source | Direction | Lookback | Usage layer | Official ranking | Current status |
|---|---|---|---|---|---:|---|---|---|
| `final_score` | 最终综合分 | composite | theme-sector-radar-dev | already_scored | - | official_score | Yes | Primary official ranking score. |
| `stock_trend_score` | 个股趋势分 | trend | theme-sector-radar-dev | already_scored | 20 | pool_signal | Partial | Trend observation pool and profile input. |
| `stock_short_score` | 个股短线分 | momentum | theme-sector-radar-dev | already_scored | 5 | pool_signal | Partial | Legacy short momentum score. |
| `stock_short_score_v2` | 个股短线分V2 | momentum | theme-sector-radar-dev | already_scored | 5 | pool_signal | Partial | Short observation pool and shadow-improved short score. |
| `sector_support_score` | 板块支持评分 | sector | theme-sector-radar-dev | higher_is_better | 20 | selection_quality | No | Validated as useful for `trend_follow`; does not change official sorting. |
| `factor_composite_shadow_score_v2` | V2 composite shadow score | composite/shadow | theme-sector-radar-dev | already_scored | - | shadow_score | No | Independent opportunity discovery; low correlation with `final_score`. |
| `factor_composite_shadow_score` | V1 composite shadow score | composite/shadow | theme-sector-radar-dev | already_scored | - | shadow_score | No | Kept as a comparison baseline. |
| `display_score_shadow_90_10` | Display shadow 90/10 | composite/shadow | theme-sector-radar-dev | already_scored | - | shadow_score | No | Blend experiment; not promoted. |
| `display_score_shadow_80_20` | Display shadow 80/20 | composite/shadow | theme-sector-radar-dev | already_scored | - | shadow_score | No | Blend experiment; not promoted. |
| `display_score_shadow_70_30` | Display shadow 70/30 | composite/shadow | theme-sector-radar-dev | already_scored | - | shadow_score | No | Blend experiment; not promoted. |
| `drawdown_risk_score` | 回撤风险分 | risk | theme-sector-radar-dev | lower_is_better | 10 | risk_review | No | Important contributor to V2 defensive information. |
| `risk_penalty_score` | 风险惩罚分 | risk | theme-sector-radar-dev | lower_is_better | - | risk_review | No | Hard-risk and data-quality context. |
| `regime_router_shadow_score_v5` | Regime路由影子分V5 | agent | theme-sector-radar-dev | already_scored | - | shadow_score | No | Regime-aware shadow monitor. |
| `sector_trend_score` | 板块趋势分 | sector | theme-sector-radar-dev | already_scored | 20 | explanation_only | No | Fallback/input for sector support. |
| `sector_burst_score` | 板块短线分 | sector | theme-sector-radar-dev | already_scored | 5 | explanation_only | No | Fallback/input for sector support. |
| `agent_score` | Agent综合分 | agent | ai-hedge-fund | already_scored | - | explanation_only | No | AIHF aggregate score, passed through for context. |
| `trend_agent_score` | 趋势Agent分 | agent | ai-hedge-fund | already_scored | - | explanation_only | No | AIHF trend agent context. |
| `short_agent_score` | 短线Agent分 | agent | ai-hedge-fund | already_scored | - | explanation_only | No | AIHF short agent context. |
| `ma20_slope_5` | MA20斜率(5日) | trend | theme-sector-radar-dev | higher_is_better | 5 | stock_profile | No | Trend strength and medium-term direction. |
| `near_high_250` | 距250日新高 | trend | theme-sector-radar-dev | higher_is_better | 250 | stock_profile | No | Long-term trend-position context. |
| `contraction_score` | 收缩评分 | volatility | theme-sector-radar-dev | higher_is_better | 20 | stock_profile | No | Volatility contraction context. |
| `atr10_atr50` | ATR10/ATR50 | volatility | theme-sector-radar-dev | neutral | 50 | stock_profile | No | Short/long volatility ratio. |
| `range10_range20` | 振幅10/振幅20 | volatility | theme-sector-radar-dev | neutral | 20 | stock_profile | No | Short/medium range ratio. |
| `range20_range60` | 振幅20/振幅60 | volatility | theme-sector-radar-dev | neutral | 60 | stock_profile | No | Medium/long range ratio. |
| `amount_ratio_20` | 成交额比(20日) | volume | theme-sector-radar-dev | higher_is_better | 20 | stock_profile | No | Recent amount activity context. |
| `liquidity_score` | 流动性评分 | liquidity | theme-sector-radar-dev | higher_is_better | 20 | stock_profile | No | Profile-only liquidity context. |
| `breakout_distance_20` | 距20日高点距离 | trend | theme-sector-radar-dev | already_scored | 20 | stock_profile | No | Structure position only; not a standalone trigger. |
| `drawdown_depth_20` | 20日回撤深度 | risk | theme-sector-radar-dev | already_scored | 20 | stock_profile | No | Pullback/repair context; not a standalone negative conclusion. |
| `chasing_risk_score` | 追高风险评分 | risk | theme-sector-radar-dev | already_scored | 10 | risk_review | No | Overheat shadow warning. |

## 4. Registered Shadow / Research Factor Extensions

These registered factors extend the factor library for shadow validation, intraday observation, and news/emotion research. They are cataloged for traceability, but they do not affect official ranking.

### 4.1 Shadow V2 Extension Factors

| factor_id | Category | Direction | Lookback | Usage layer | Official ranking |
|---|---|---|---:|---|---|
| `relative_strength_20` | momentum | already_scored | 20 | shadow_score | No |
| `relative_strength_60` | momentum | already_scored | 60 | shadow_score | No |
| `risk_adjusted_return_20` | risk | already_scored | 20 | shadow_score | No |
| `volume_stability_score` | volume | already_scored | 20 | shadow_score | No |
| `trend_persistence_score` | trend | already_scored | 40 | shadow_score | No |
| `sector_peer_rank_score` | sector | already_scored | - | shadow_score | No |

### 4.2 Intraday Atomic Shadow Factors

| factor_id | Category | Direction | Lookback | Usage layer | Official ranking |
|---|---|---|---:|---|---|
| `late_return_30m_score` | intraday | already_scored | 1 | research_only | No |
| `late_vwap_support_score` | intraday | already_scored | 1 | research_only | No |
| `late_volume_share_score` | intraday | already_scored | 1 | research_only | No |
| `late_high_near_close_score` | intraday | already_scored | 1 | research_only | No |
| `high_to_close_drawdown_score` | intraday | lower_is_better | 1 | risk_review | No |
| `morning_spike_fade_score` | intraday | lower_is_better | 1 | risk_review | No |
| `afternoon_fade_score` | intraday | lower_is_better | 1 | risk_review | No |
| `max_gain_giveback_ratio` | intraday | lower_is_better | 1 | risk_review | No |
| `close_vs_vwap_score` | intraday | already_scored | 1 | research_only | No |
| `late_price_above_vwap_ratio` | intraday | already_scored | 1 | research_only | No |
| `vwap_slope_score` | intraday | already_scored | 1 | research_only | No |
| `vwap_reclaim_score` | intraday | already_scored | 1 | research_only | No |
| `volume_without_price_progress_risk` | intraday | lower_is_better | 1 | risk_review | No |
| `late_volume_efficiency_score` | intraday | already_scored | 1 | research_only | No |
| `amount_acceleration_score` | intraday | already_scored | 1 | research_only | No |
| `volume_spike_exhaustion_score` | intraday | lower_is_better | 1 | risk_review | No |
| `opening_drive_score` | intraday | already_scored | 1 | research_only | No |
| `morning_strength_persist_score` | intraday | already_scored | 1 | research_only | No |
| `morning_pullback_repair_score` | intraday | already_scored | 1 | research_only | No |
| `open_to_midday_resilience_score` | intraday | already_scored | 1 | research_only | No |
| `sector_intraday_breadth_change` | intraday | already_scored | 1 | research_only | No |
| `sector_late_breadth_score` | intraday | already_scored | 1 | research_only | No |
| `leader_follower_sync_score` | intraday | already_scored | 1 | research_only | No |
| `stock_vs_sector_intraday_alpha` | intraday | already_scored | 1 | research_only | No |

### 4.3 Market / News Emotion Shadow Factors

| factor_id | Category | Direction | Lookback | Usage layer | Official ranking |
|---|---|---|---:|---|---|
| `market_short_emotion_score` | market_emotion | already_scored | 3 | research_only | No |
| `limit_up_breadth_score` | market_emotion | already_scored | 3 | research_only | No |
| `limit_up_failure_risk` | market_emotion | lower_is_better | 3 | risk_review | No |
| `leader_continuation_score` | market_emotion | already_scored | 3 | research_only | No |
| `short_burst_environment_score` | market_emotion | already_scored | 3 | research_only | No |
| `crowding_heat_score` | market_emotion | lower_is_better | 3 | risk_review | No |
| `news_heat_score` | catalyst | already_scored | 3 | research_only | No |
| `policy_catalyst_score` | catalyst | already_scored | 3 | research_only | No |
| `earnings_catalyst_score` | catalyst | already_scored | 3 | research_only | No |
| `event_freshness_score` | catalyst | already_scored | 3 | research_only | No |
| `event_continuation_score` | catalyst | already_scored | 3 | research_only | No |
| `negative_news_risk_score` | catalyst | lower_is_better | 3 | risk_review | No |
| `rumor_hype_risk_score` | catalyst | lower_is_better | 3 | risk_review | No |
| `short_burst_news_emotion_score_shadow` | short_emotion | already_scored | 3 | shadow_score | No |

## 5. Research / External Factor Reserve

These factors are part of the broader research pool from the three-project history. They are not all registered in `FACTOR_REGISTRY` yet, and most should remain research-only until mapped, backfilled, and validated.

| factor_id / name | Source project | Type | Current use | Notes |
|---|---|---|---|---|
| `RS_Return` | industry_rotation | momentum | research_only | Industry/relative momentum reserve. |
| `RS_Breadth` | industry_rotation | breadth | research_only | Breadth signal; useful for rotation context. |
| `RS_Flow` | industry_rotation | volume/flow | research_only | Flow signal; needs data-quality review. |
| `RotationBonus` | industry_rotation | momentum | research_only | Historically lagged; keep weak or disabled. |
| `Excess_Return_20` | ma20_breakout | momentum | research_only | Relative strength reserve; can be mapped later. |
| `Amount_Ratio` | ma20_breakout | volume | research_only | Similar family to `amount_ratio_20`; avoid duplicate weighting. |
| `BreakoutAmountScore` | ma20_breakout | volume | research_only | Breakout-volume confirmation reserve. |
| `MA20_Rising` | ma20_breakout | trend | research_only | Previously too restrictive; do not restore without new evidence. |
| `NearHighScore` | VCB | trend | research_only | Related to `near_high_250`; avoid duplicate interpretation. |
| `ContractionScore` | VCB | volatility | research_only | Related to `contraction_score`; avoid duplicate weighting. |
| `MKT` | weekly_residual | risk | research_only | Market factor for attribution. |
| `IND` | weekly_residual | risk | research_only | Industry factor for attribution. |
| `SMB` | weekly_residual | risk/style | research_only | Style factor; not daily selection input. |
| `HML` | weekly_residual | risk/style | research_only | Weak recent value signal; keep low priority. |
| `LIQ` | weekly_residual | risk/liquidity | research_only | Risk attribution context. |
| `Cum_Residual` | weekly_residual | reversal | research_only | Reversal reserve; needs separate validation. |

## 6. Promotion Rules

Before a factor can move to a stronger usage layer, it must satisfy all relevant checks:

1. It must exist in the registry or have a documented external mapping.
2. Its raw value, score, direction, and lookback must be documented.
3. Its current use must be explicitly one of the usage layers in this catalog.
4. Its effect must be evaluated by historical forward returns.
5. It must not duplicate another factor without a clear semantic reason.
6. It must not change official ranking unless a dedicated promotion phase and tests approve it.
7. It must not create an entry/exit action directly from `profile_only`, `structure_candidate`, `repair_context`, or `soft_warning`.

## 7. Short Burst Shadow Factor Reserve

These factors separate short-term emotion from trend-style scoring. They are registered and backtestable, but remain `research_only` / `shadow_only` until 1d validation proves stable value.

| factor_id | Purpose | Initial use |
|---|---|---|
| `short_emotion_heat_score` | Same-day short-term emotion heat from attention, volume quality, sector breadth, and short momentum. | research_only |
| `sector_burst_breadth_score` | Whether a short burst is supported by sector spread instead of an isolated stock move. | research_only |
| `limit_attention_score` | Same-day attention proxy from price strength; not an entry signal. | research_only |
| `intraday_reversal_risk_score` | Long upper shadow, high-to-close giveback, and weak close location. | risk_review |
| `close_strength_score` | Close location inside the daily range. | research_only |
| `volume_burst_quality_score` | Healthy amount expansion versus one-day extreme spikes. | research_only |
| `single_name_overheat_score` | Isolated stock strength without sector spread. | risk_review |
| `next_day_cashout_risk_score` | Next-day profit-taking risk after overheated or fading moves. | risk_review |
| `short_burst_emotion_score_v1` | Independent short-burst shadow score for 1d validation. | shadow_score |
| `short_burst_emotion_score_v2` | Shadow score that lowers pure heat weight and emphasizes volume quality, close strength, and risk control. | shadow_score |

Design intent:

```text
short_burst_emotion_score_v1
= short emotion
+ sector breadth
+ close strength
+ volume quality
- intraday reversal risk
- isolated overheat
- next-day cashout risk

short_burst_emotion_score_v2
= healthy volume quality
+ close strength
+ sector burst breadth
+ low-weight short emotion heat
+ low-weight limit attention
- next-day cashout / reversal / overheat risk
```

These fields must not modify `final_score`, `v2_score`, `selection_score`, or `selection_score_adjusted`.

## 8. Intraday Shadow Factor Pipeline

Intraday factors are added as a four-stage shadow-only pipeline. They are designed to reduce the short-burst model's dependence on daily trend factors, but they must not create trade actions or modify official scores.

| Stage | Output | Status |
|---|---|---|
| 1. Intraday factor snapshot | `intraday_factor_snapshot` | Implemented, missing-safe |
| 2. Short-burst intraday emotion score | `short_burst_intraday_emotion_score_shadow` | Implemented, shadow-only |
| 3. Forward-return validation fields | default factor backtest specs for 1d/3d/5d/10d | Implemented; depends on intraday data coverage |
| 4. Observation rank shadow | `short_burst_observation_rank_shadow` | Implemented; does not drive current sort |

Registered intraday factors:

- `intraday_close_position_score`
- `intraday_high_pullback_risk_score`
- `intraday_volume_price_confirm_score`
- `intraday_sector_breadth_score`
- `intraday_late_strength_score`
- `short_burst_intraday_emotion_score_shadow`

These fields use `shadow_observation_only`, `does_not_drive_current_sort`, and `no_execution_signals` until rolling forward-return validation shows stable value.

## 9. Current Priority

High-confidence factors to keep using:

- `final_score`
- `stock_trend_score`
- `stock_short_score_v2`
- `sector_support_score`
- `factor_composite_shadow_score_v2`
- `drawdown_risk_score`
- `chasing_risk_score`

Useful profile/context factors:

- `liquidity_score`
- `breakout_distance_20`
- `drawdown_depth_20`
- `amount_ratio_20`
- `contraction_score`
- `near_high_250`
- `ma20_slope_5`

Keep as research reserve:

- `MKT`, `IND`, `SMB`, `HML`, `LIQ`, `Cum_Residual`
- `RS_Return`, `RS_Breadth`, `RS_Flow`, `RotationBonus`
- `MA20_Rising`, `Inv_Market_Cap`
