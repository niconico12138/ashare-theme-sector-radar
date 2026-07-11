# Stock Factor Catalog

This document defines stock-level factors for the three-project joint system.
Stock factors answer one question: within selected sector directions, which
stocks are worth observing and why?

Stock factors are separated into official scoring, shadow discovery, profile
explanation, and research-only layers.

## Factor Groups

| Group | Factor ids | Current usage | Notes |
|---|---|---|---|
| Official and pool score | `final_score`, `stock_trend_score`, `stock_short_score`, `stock_short_score_v2` | `official_score`, `pool_signal` | Current production candidate pool inputs. |
| V2 shadow discovery | `factor_composite_shadow_score_v2`, `factor_composite_shadow_score`, `display_score_shadow_90_10`, `display_score_shadow_80_20`, `display_score_shadow_70_30` | `shadow_score`, `stock_profile` | Independent opportunity discovery and disagreement review. |
| Trend and structure | `ma20_slope_5`, `near_high_250`, `breakout_distance_20` | `stock_profile`, `explanation_only` | Describes trend and structure position; not an execution signal. |
| Pullback and repair | `drawdown_depth_20`, `drawdown_risk_score` | `risk_review`, `stock_profile` | Describes drawdown context and repair state. |
| Overheat and risk | `chasing_risk_score`, `risk_penalty_score` | `risk_review`, `stock_profile` | Describes overheating or risk context. |
| Liquidity and volume | `liquidity_score`, `amount_ratio_20`, `Amount_Ratio`, `Volume_Ratio`, `BreakoutAmountScore` | `stock_profile`, `research_only` | Describes tradability and activity confirmation. |
| Volatility and contraction | `contraction_score`, `atr10_atr50`, `range10_range20`, `range20_range60` | `stock_profile`, `research_only` | Describes volatility compression or expansion. |
| AIHF agent context | `agent_score`, `trend_agent_score`, `short_agent_score` | `explanation_only`, `shadow_score` | Pass-through and explanation context; not official ordering. |

## Registered Stock Factors

| Factor id | Layer | Status | Rule |
|---|---|---|---|
| `final_score` | `official_score` | active | Current official candidate ranking score. |
| `stock_trend_score` | `pool_signal` | active | Used for trend observation pool. |
| `stock_short_score_v2` | `pool_signal` | active | Used for short observation pool. |
| `factor_composite_shadow_score_v2` | `shadow_score` | active shadow | Used for independent opportunity discovery; does not change official ranking. |
| `sector_support_score` | `selection_quality` | active | Adjusts observation quality for `trend_follow` only. |
| `breakout_distance_20` | `stock_profile` | active shadow | Structure context only. |
| `drawdown_depth_20` | `risk_review` | active shadow | Pullback and repair context only. |
| `chasing_risk_score` | `risk_review` | active shadow | Overheat context only. |
| `liquidity_score` | `stock_profile` | active shadow | Liquidity profile only. |

## Stock Profile States

| State | Inputs | Meaning | Forbidden interpretation |
|---|---|---|---|
| `trend_state` | `stock_trend_score`, `ma20_slope_5`, `breakout_distance_20` | Trend quality and repair state. | Not an automatic action. |
| `momentum_state` | `stock_short_score_v2`, `amount_ratio_20` | Short-term strength. | Not an automatic action. |
| `sector_support` | `sector_support_score` | Sector support for the stock. | Not official ranking by itself. |
| `liquidity_state` | `liquidity_score` | Liquidity condition. | Weak liquidity is review context, not automatic removal. |
| `breakout_structure` | `breakout_distance_20` | Distance to recent structure high. | Near structure is not an execution trigger. |
| `drawdown_state` | `drawdown_depth_20` | Pullback depth and repair context. | Deep drawdown is not automatic deterioration. |
| `overheat_state` | `chasing_risk_score` | Short-term overheating context. | High overheat is review context, not automatic removal. |

## Research Reserve

| Factor id | Intended group | Required validation |
|---|---|---|
| `Excess_Return_20` | Momentum | Forward-return IC and redundancy check. |
| `Return_10d` | Momentum | Horizon stability test. |
| `MOM` | Momentum | Market-regime slice test. |
| `RelativeStrengthScore` | Momentum | Redundancy check with `stock_trend_score`. |
| `MA20_Rising` | Trend | Re-test because earlier strict filter hurt returns. |
| `Inv_Market_Cap` | Size | Needs reliable market-cap data first. |
| `VOL`, `Residual_Vol` | Volatility | Risk-adjusted return test. |
| `Cum_Residual` | Residual/reversal | Mean-reversion and regime validation. |

## Promotion Rules

A stock factor may affect `selection_quality` only after it passes:

1. Definition stability.
2. Data coverage check.
3. Historical evaluation by horizon.
4. Opportunity-type slice analysis.
5. Shadow-only monitoring.
6. Contract documentation in `factor_usage_policy.md`.
