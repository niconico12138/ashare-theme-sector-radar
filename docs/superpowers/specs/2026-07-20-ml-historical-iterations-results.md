# ML Historical Shadow Follow-up Iterations

## Scope

This document records ten independent follow-up rounds after the existing v1
direction/Linkage V2 ablation. The rounds use the v9 source-rebuild-bound historical
dataset as a read-only input and remain paper/shadow research only. No formal model
bundle, predictor registration, broker, order, or live-trading output is produced.

Dataset logical SHA is `7c45de04b255d4b47ed4011fee1594705c10c85416893c26e9415f57c4e46cef`.
The source contains 99 candidate dates, 1,730 candidate rows, and 1,696 labeled rows.
Direction and Linkage V2 coverage are both `0/1730`; regime slicing has 1,353/1,730
rows. The fixed model contract is expanding date-grouped walk-forward with 60 train
dates, 5 purge dates, 5 test dates, and a 5-day label horizon. The corrected v2 suite
uses the baseline's 80 estimators for all non-estimator sensitivity rounds.

The first generated suite, `historical_iterations_v1_20260720`, is retained as an
audit artifact but is not used for conclusions because several controls changed tree
count together with their stated variable. The corrected conclusions below come from
`historical_iterations_v2_20260720`.

## Baseline

The existing v1 technical baseline is the comparator. Its aggregate metrics are:

| Top-k | Lift | Rank IC | Win rate |
| --- | ---: | ---: | ---: |
| Top1 | 0.011787 | -0.010209 | 0.529412 |
| Top3 | 0.003088 | -0.010209 | 0.500000 |
| Top5 | -0.000150 | -0.010209 | 0.500000 |

These are historical reconstruction statistics, not OOS or promotion evidence.

## Ten Rounds

1. **Complete-fold sensitivity**: first 95 dates, six complete 5-day test folds;
   Top1/3/5 lifts were `-0.000426/-0.002606/-0.004080`, Rank IC `-0.044675`,
   and win rates `0.466667/0.433333/0.433333`. Retain as a fold-integrity
   robustness control; no candidate adoption.
2. **Top-k sensitivity**: with the fixed baseline model, Top1/2/3/5/10 lifts were
   `0.011787/0.007175/0.003088/-0.000150/-0.007490`. Retain as reporting
   sensitivity; Top10 is eliminated as a preferred research target.
3. **Random-seed sensitivity**: seeds `20260719` and `20260720` produced identical
   Top1/3/5 metrics `0.011787/0.003088/-0.000150`, Rank IC `-0.010209`, and
   win rates `0.529412/0.500000/0.500000`. Retain as deterministic reproducibility
   evidence, not as a promotion result.
4. **Estimator sensitivity**: 40 estimators gave Top1/3/5 lifts
   `-0.012461/0.005209/-0.002612`, Rank IC `-0.011739`, and win rates
   `0.411765/0.588235/0.352941`; 120 estimators gave
   `0.012209/-0.001710/-0.000591`, Rank IC `-0.003128`, and win rates
   `0.529412/0.500000/0.529412`. Retain only as hyperparameter sensitivity;
   do not select 120 estimators from this same historical window.
5. **Drop sector support**: Top1/3/5 lifts were `0.043220/0.004937/-0.005537`,
   Rank IC `0.033902`, and win rates `0.676471/0.441176/0.411765`. Retain as a
   research hypothesis for a fresh window; do not promote from this reconstruction.
6. **Drop reversal risk**: Top1/3/5 lifts were `0.028380/0.011082/0.002521`,
   Rank IC `0.009590`, and win rates `0.558824/0.558824/0.470588`. Retain as a
   research control only; no promotion.
7. **Date-wise shuffle control**: Top1/3/5 lifts were
   `0.001659/-0.015673/-0.009988`, Rank IC `-0.086697`, and win rates
   `0.500000/0.323529/0.441176`. The null control is retained; the shuffled model
   is eliminated as a candidate.
8. **Daily bootstrap uncertainty**: 1,000 deterministic resamples of the 34 baseline
   evaluation dates produced Top1 lift p05/median/p95 of
   `-0.010566/0.010970/0.033479`; positive-lift fraction was `0.802`. Retain as
   uncertainty evidence only; the interval crosses zero.
9. **Source-manifest tamper rejection**: changing only the in-memory calendar SHA was
   rejected with `historical research calendar physical identity changed`. Gate
   retained; experiment passes as a negative control.
10. **Label-row tamper rejection**: changing one in-memory training label without
    changing the dataset identity was rejected with `historical research dataset SHA
    mismatch`. Gate retained; experiment passes as a negative control.

## Safety And Reproducibility

The v2 suite SHA is
`8d3c8ca05c9d59d4f0cea83a9fa3fc126fcb981745212dc01aa604ae9575a70`. It contains one
suite report plus ten independent iteration reports. All reports have
`strict_pit_eligible=false`, `eligible_for_oos_claim=false`, `promotion_allowed=false`,
`live_trading_allowed=false`, and `formal_predictor_compatible=false`.

The final read-only ML artifact inventory was rebuilt after concurrent dirty-worktree
artifacts appeared. It contains 172 artifacts, 22 model binaries, 139 superseded
legacy artifacts, and 11 current/compatible artifacts. Its SHA is
`877f3ee7ab8f52c090abad576d4dbbc31ca5eb94b795cf7e11fa57842cea36f6`, and
`--verify-existing` passed at the final check.

The current feature set has no `quant_score`, `final_score`, `v2_score`,
`selection_score`, `selection_score_adjusted`, `relevance_score`, or
`legacy_relevance_score` inputs. Missing direction/Linkage values remain explicit
through indicators. The suite adds no broker/order path and creates no formal model.

Focused tests for the new suite, factor ablation, and historical reconstruction passed
`19 passed`. The full `test_ml_*.py` set passed `106 passed in 37.57s` after the final
v2 artifact write.

## Limitations

The real archive contains no historical direction or Linkage V2 observations, so none
of the ten rounds measures those candidate factors. All metrics are conditional on the
same 99-day reconstructed window, and the bootstrap is not an independent OOS sample.
The results support reproducibility and rejection controls, not model promotion or
live trading.
