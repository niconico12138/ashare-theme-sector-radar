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
archive evidence SHA: 2c3f7058826e19a7d311942598435ad9e83b82692d2e863ca5c0e72eb449ffe2
archive build readiness SHA: a8b0ec6e62147453e5ffd09804ceed0cee6be4c1d329d3922e872d3358123121
archive build report SHA: 7198546cabdff318c20ad5a53fa2b0443dd4e634465e99b54363ea6db1e933ea
training-cycle readiness SHA: b570fa51cf9416a17142d578f02b62e054eabb445ef8cc657afde1207d999c36
training-cycle report SHA: 3d78052cf1af7049208a07b3136e8e73b09d521de13ecd05300e8799a9f1aaac
readiness audit SHA: f22ebf14444db2754c8d0163900e2b8263c2e863809546eca92a7573eb0c2c61
```

The iteration-1 observed-cycle artifacts are the current run products. The latest
rerun remains blocked at readiness:

```text
training-cycle readiness SHA: ed39a8aa0612857ee350a920a789c0e26c518a0977e831e832bc31f1ce5a84a
training-cycle report SHA: a23722201730cfc24c29cc04e1e652907c58cafe7acc6e82c3f20850ea5fcda5
experiment file SHA: b21f89c4b41f7ac903b412a0d1b245505a79b5adaad472601bb49a04cae92020
effective experiment SHA: a4d6e3c8fc705cc2363de0d419f14e752791403e8aca1a1613f6d44f6684e972
```

No real model was trained and no production/rule field was changed. Synthetic fixture
training remains architecture-only and cannot be used as real performance evidence.

## Verification

The stage2 focused suite covers naive-source witness handling, raw prediction drift,
immutable daily and mature-label archives, readiness blocking, archive-to-dataset
blocking and strict success, purged training, and Quant/Linkage/Hybrid/ML evaluation.
Final test and source-manifest numbers are recorded in the current planning progress
after the closing full-suite run.

The prior verification snapshot was `3253 passed, 19 deselected in 236.06s`; focused ML/archive/
experiment/inventory coverage is `82 passed`. `compileall`, `git diff --check`, strict parsing
(`379 JSON + 1 JSONL/12 lines` inventory), ML artifact identity validation (`68/68`, including 3 model.txt),
and the ML protected-field AST write scan (`0` hits) pass. Read-only machine acceptance passes with archive
status `verified`, `1` candidate snapshot, `0` prospective dates, `0` verified training
dates, dataset/cycle `blocked`, and no model directory.

The legacy bridge `relevance_score` and its `legacy_relevance_score` alias are not ML
features. They remain historical comparison fields only; the active formal association
path is Linkage V2 and the ML path remains an independent shadow reranker.

## Iteration 1: Experiment Contract

The first continuing-iteration pass added the registered configuration
`config/ml_stock_ranker_v1.json` and its validator in
`theme_sector_radar/ml/experiment.py`. Training artifacts now distinguish the physical
configuration file SHA from the canonical configuration-content SHA. The canonical
SHA is bound to model registration; the file SHA preserves byte-level provenance.
The contract fixes the current 34-feature schema, excludes both legacy relevance names,
uses the 5-day sector-excess label, requires at least 60 training dates and a 5-date
purge, and permanently keeps `promotion_allowed` and `live_trading_allowed` false.

The iteration was tested with the existing strict 66-date synthetic/prospective archive
path and the current observed archive. The strict path still trains only in its test
fixture; the observed path remains correctly blocked at readiness because it has 1
historical reconstruction date, 0 prospective dates, and 0 mature 5-day labels.

Controlled CLI overrides are merged into the effective experiment object before hashing,
so they cannot silently reuse the base configuration identity. Observed model bundles
must carry strict PIT evidence and the experiment contract at both save and load;
relaxed split settings remain limited to explicit synthetic fixtures with prediction
opt-in.

## Latest Verification After Parameter Binding

The latest observed-cycle rerun remains blocked at readiness. Current artifact identities
are:

```text
training-cycle readiness SHA: 41e8769e831e3cd9ce20200f13851d81daebb0d9afbe5141b33f0ebfa793d2bb
training-cycle report SHA: 2346cabab0b3b106d9fcfffbfe68189089a014097985ca7d077b6c16b6a24070
```

The final full suite is `3224 passed, 19 deselected in 247.74s`; the focused ML/archive
suite is `53 passed`. The experiment contract is now cross-bound to trained model
parameters at save, load, and prediction.

The final predictor-safety closure rerun is the latest verification: full pytest
`3224 passed, 19 deselected in 249.86s`; the latest observed-cycle readiness SHA is
`1626fd00a296676e7b195c44a664d1c694601044487d1927c0b0092afcf92c57`, and its cycle
report SHA is `192aaa6a7cd9421ee544bd458e033048a39192d70ee74562d4a493ad5493f388`.

After making `live_trading_allowed=false` explicit in the registry and predictor
contracts, the latest full suite is `3224 passed, 19 deselected in 238.66s`. The final
observed-cycle readiness SHA is
`2c9cd53707c4016c86c6774eb9f8eb8dc3f3edc00bb755495288c8ba123b3e55`; cycle report
SHA is `41cdcc6810854eff544997083fef1e3d128ce5f5e682b44196af855cc98692b2`.

The historical interrupted-run continuation superseded those earlier timing and artifact
identities at that time; it is itself superseded by the artifact-inventory result below: full pytest is
`3224 passed, 19 deselected in 250.84s`; readiness SHA is
`fae2a73cad95ef31f6ba50c89951c38af6cb77c13f09150fd5cf1c869857e527`; cycle report SHA is
`2fab11135deed739ea19622d1bdad082c765acc90c9b612afacb03274bc46497`. The registered
experiment file SHA is `b21f89c4b41f7ac903b412a0d1b245505a79b5adaad472601bb49a04cae92020`;
the effective experiment SHA is `a4d6e3c8fc705cc2363de0d419f14e752791403e8aca1a1613f6d44f6684e972`.
The readiness gate remains blocked with one candidate snapshot, zero prospective dates,
zero verified training dates, and zero mature five-day labels; no observed model directory
was created.

The latest artifact-contract continuation supersedes the earlier artifact identities for
the current record. Readiness SHA is
`80ea9944c6e2fea4978054fa3f1033c722a4172e559dc2b248b053105fd9ba87`; cycle report SHA is
`4d910f9657cb31aa285066deba324e7732400b8dd72ae5372eacbcdbc2aaa6af`; artifact inventory
SHA is `0655da8b5be1b71c1000a967a184537183f235bf490680cf2459d10274437ff1`; config file SHA is
`949101a2c1c7ee69bf235120fb11f720efeb448eccd27df591b2e14f778096cf`, effective experiment SHA is
`a315047c2783f174b068999733f27aa8d86fce38f292b3a814b5536f7d6a7b7d`; full pytest is
`3253 passed, 19 deselected in 236.06s`; focused ML coverage is `82 passed`. The new
contracts reject fixture sources in same-day PIT capture, require observed feature-source
archive identity, verify serialized booster parameters, require verified loaded model
objects for prediction, disable public raw predictions, and write explicit
`live_trading_allowed=false` across ML shadow artifacts.

The inventory binds 68 physical identities without rewriting history: 65 strict JSON
files and 3 model binaries. Sixty-three old JSON files that predate the explicit live flag are
`superseded_legacy` and ineligible as current evidence; the two current training-cycle
artifacts contain inline live false, and the current loader rejects old missing-live
registry/dataset payloads.

The latest credibility closure also replays observed label-price rows from verified
archive snapshots, makes readiness re-run the archive verifier, rejects non-false safety
flags throughout archive and inventory artifacts, requires registry/model pairs, scans
all known `test_output/ml_*` roots, and binds synthetic fixture bundles to the same
experiment/booster contract used at load and prediction. Historical artifacts missing
the newer archive safety fields remain immutable but are downgraded from strict evidence.

## Historical Verification Snapshot (superseded by v8)

The latest continuation supersedes all earlier current-value blocks in this document.
Fresh full pytest is `3258 passed, 19 deselected in 246.70s`; the four-file
ML/archive/experiment/inventory suite is `87 passed in 34.94s`, and the archive-focused
suite is `20 passed in 28.27s`. The observed training cycle remains
`status=blocked` with `reason=readiness_gate_blocked_training`; no observed model was
created.

Current readiness SHA is
`7d350962f51239869c66d667c12e932e76e0ad0cfd9a82d59a4fe3d9211797a6`; cycle report SHA
is `91443a9d7b42a47857e5b2827b946f3395f82bbd009e07474b99e25953e52753`; and verified
archive evidence SHA is `2c3f7058826e19a7d311942598435ad9e83b82692d2e863ca5c0e72eb449ffe2`.

Current artifact inventory SHA is
`c6d6f22c3412aaa43c32a30a8a4230d31c6b931f1c48d2c1e54487ccb1ec6e53`. It binds 69
physical artifacts: 66 strict JSON files and 3 model binaries; 64 immutable legacy JSON
files are `superseded_legacy`, and 2 current cycle JSON files are current research
evidence. Strict parsing remains `379 JSON + 1 JSONL/12 lines`; safety envelopes remain
false for strict PIT eligibility, OOS claims, promotion, and live trading.
Fresh independent read-only Review A and Review B both return
`Critical=0, Important=0, Minor=0`; the stage is closed without model promotion.

## Historical Reconstruction Iteration (2026-07-20)

The continuing iteration added `historical_research.py`, its CLI, and focused tests.
The corrected v6 stability-core run completed with 99 mature source dates, 1,696
label rows, and 7 walk-forward folds. Its evaluated slice contains 34 dates and 594
rows. Top3 mean return is 2.106%, versus 1.797% for the candidate universe, for a
0.309 percentage-point lift; ML wins against the universe on 50.0% of dates and the
mean Spearman Rank IC is -0.0102. The result is therefore a research signal, not
evidence of stable ranking power. Earlier full-factor expanding, rolling-60, and
stability-core runs remain preserved as comparison artifacts; rolling-60 was worse
and is not adopted.

The v6 registry now correctly contains 11 feature names. All safety flags remain
false, the formal loader rejects the historical-research bundle, and no protected
score field is used as a model feature. Focused regression is `95 passed`; the fresh
full suite is `3266 passed, 19 deselected in 250.33s`. Compileall and diff-check pass;
strict JSON parsing passes. No model promotion, production predictor replacement,
broker integration, or order generation occurred.

Next research iteration: select features using nested walk-forward stability,
evaluate cross-sectional excess-return labels and regime slices, and pre-register
Top1/Top3/Top5 selection criteria. No result from the same evaluation window may
promote the model.

## Final Current Override After v8 (2026-07-20)

This block supersedes every earlier block labeled current or latest in this document.
The replay-bound v8 preserves the v6 research metrics: 99 labeled dates, 1,696 rows,
7 folds, 34 evaluated dates, and 594 evaluated rows. Top3 mean return is 2.106%, the
candidate-universe mean is 1.797%, lift is +0.309 percentage points, win rate is 50.0%,
and mean Rank IC is -0.0102. These remain non-PIT research observations and do not
justify promotion.

Prediction metrics now require deterministic LightGBM walk-forward replay. Forged
scores, fold identities, parameters, dataset SHA, or prediction-row SHA are rejected.
Missing rule baselines no longer remove rows from the ML universe. Five-day returns
are replayed from `close_t` and `close_5d` and checked against the calendar maturity
boundary; source bars are still not content-addressed, which is explicit in every v8
dataset/evaluation/registry and keeps strict PIT and OOS eligibility false.

Current artifact identities:

```text
dataset SHA: 71b35469e51f712cb0acf46fde02848d3ed3475cf7a9f8b770fd1b6eb04bf095
walk-forward SHA: 88126c7871b9cb82081846aab4b30b06269c47bbf6a99b0d6738e15acd4a6e60
evaluation SHA: 0d333ebb8ad00c70de116af5b9369a9365b24e85d6ff281921087d56c15d61f0
cycle SHA: 9ddce6c5d04b923cfa5bac95974f3e6fb0f785704f7ce1bd005feaa600449d63
registry SHA: 60f7b91420867e7ba2d012038b4739637a4b9d6956e3c36b2ecdd06fbc5d0ae8
model SHA: eb3ecfaf3b92f5d433f0d9e539be4fbb559434344b9a2d6aa31c459a315490a1
inventory SHA: 980c5c2d1a3436e82284015c346a926397e9db616370f092f546d280f1d0c435
```

The inventory verifies 120 physical artifacts, including 11 model binaries. Focused
ML regression is `98 passed`; full pytest is `3269 passed, 19 deselected in 253.38s`.
All v8 safety flags remain false, the formal loader rejects the historical schema, and
no broker, order, or live-trading path was introduced.

## Final Current Override After v9 Source-Rebuild Binding (2026-07-20)

The v9 continuation adds source-manifest reconstruction to dataset validation. A
dataset whose rows are changed and whose top-level SHA is merely rehashed is now
rejected unless it exactly matches a fresh rebuild from the physical candidate,
forward-return, and calendar sources. The historical 5d label checks and deterministic
prediction replay remain active.

Current v9 artifacts are:

```text
dataset SHA: 71b35469e51f712cb0acf46fde02848d3ed3475cf7a9f8b770fd1b6eb04bf095
walk-forward SHA: adaef66ea8c73538d6824d4b3f1a476e4662c745fd1ba6688992e25108f9848a
evaluation SHA: 7f6878efef840c2c58e09a7f49a1e57b4c0583ccc497334e805f0aedcbae1316
cycle SHA: 1bb6d00a00a1a15336e58b49f26983508117c0819040f902073164f7cb4af442
registry SHA: 03aad5fff09d73f152121c822086ba228079424fcf5eb7a26ba05c11a0f90ac4
model SHA: eb3ecfaf3b92f5d433f0d9e539be4fbb559434344b9a2d6aa31c459a315490a1
inventory SHA: d77416eb6d23c540ed17f4d5187774c4d28a1c904dbf2d255bfd4c92f8fbe5bb
```

The inventory verifies 127 physical artifacts and 12 model binaries. Focused ML
regression is `99 passed`; the final full suite is `3270 passed, 19 deselected in
254.56s`. Historical reconstruction remains explicitly non-PIT, non-OOS,
non-promotable, and formal-predictor-incompatible.
