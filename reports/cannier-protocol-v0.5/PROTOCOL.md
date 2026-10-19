# CANNIER-protocol context experiment (v0.5): frozen protocol and success rule

Frozen 19 October 2026, **before any context-model prediction under this protocol was computed**.
The machine-readable copy is `protocol.json`; its SHA-256 is recorded in every run manifest.
Status of everything below: **Proposed** until `run_manifest.json` exists.

## Question

Under CANNIER's own published evaluation protocol, does adding 66 bounded static fixture/helper/
lifecycle/class-state context features (plus one context-availability indicator) to CANNIER's 18
released features improve (a) classification MCC and (b) the simulated hybrid-detection
cost/performance trade-off?

Base paper: Parry, Kapfhammer, Hilton, McMinn, "Empirically evaluating flaky test detection
techniques combining test case rerunning and machine learning models", Empirical Software
Engineering 28, 2023 (CANNIER). doi:10.1007/s10664-023-10307-w.

## Why this differs from v0.4

v0.4 used project-held-out folds; under it the 18-feature baseline itself collapsed (AP about 0.005
versus about 0.49 in the authors' release). That was a different, harder task. v0.5 instead copies the
authors' own `cannier_framework/model.py` protocol so results are comparable with the paper. v0.4
stays reported as the cross-project result. Neither replaces the other.

## Data (unchanged authors' release)

- `items.npy` (89,668 x 7) and `features.npy` (89,668 x 30 x 18) from the verified authors' archive
  (SHA-256 `07d714a7...f56f9f1`), revision `b96d6ed0`.
- Tasks and domains exactly as `PROBLEMS`: NOD-vs-Rest (all, label col 3), NOD-vs-Victim (domain col 5,
  label col 3), Victim-vs-Rest (all, col 4), Polluter-vs-Rest (all, col 6).
- Context: frozen v0.4 table `dataset/cannier-matched-v0.4/features_context.csv.gz` (66 columns),
  joined by `original_row`. The 2,887 unmapped cases receive zeros plus `context_available=0`;
  mapped cases have `context_available=1`. The indicator is a static extraction property, independent
  of outcomes.
- Pairwise dependencies are rebuilt read-only from the SQLite `dependency` tables (the authors'
  `dependencies.pkl` is never unpickled).

## Models (authors' BEST_MODELS, unchanged)

| Task | Classifier | Trees | Sampling |
|---|---|---:|---|
| NOD-vs-Rest | ExtraTrees | 100 | SMOTE |
| NOD-vs-Victim | RandomForest | 75 | SMOTE |
| Victim-vs-Rest | ExtraTrees | 75 | SMOTE |
| Polluter-vs-Rest | RandomForest | 100 | SMOTE |

All other hyperparameters are scikit-learn defaults, as in the authors' code. No hyperparameter search
for either arm. The context arm uses the same configuration; it is not retuned.

## Procedure (authors' `set_preds_i`, made paired and seeded)

For each task and repeat r = 0..29:
1. Draw one of the 30 stored feature measurements per case (n_F = 1), as the authors do.
2. StratifiedKFold(10, shuffle=True) over cases.
3. Within each training partition only: SMOTE (default k=5), then fit the classifier.
4. Predict held-out probabilities.

**Pairing:** in repeat r, the baseline and context arms share the same measurement draw, the same
fold split, and the same SMOTE/classifier random seeds. The only difference is the 67 added columns.
Seeds: base seed 20261019 + 1000*task_index + r.

Software: scikit-learn 1.7.2 and imbalanced-learn 0.14.0 (authors: 1.0.2). This is a disclosed
adaptation.

## Pre-run checks (must pass before any context result is interpreted)

1. **Reproduction gate:** for each task, our baseline mean absolute MCC at threshold 0.5 must be
   within +/-0.03 of the authors' released-prediction mean (NOD-vs-Rest 0.5321, NOD-vs-Victim 0.6926,
   Victim-vs-Rest 0.5195, Polluter-vs-Rest 0.9458). If a task fails, that task is reported as
   "baseline not reproduced" and excluded from any improvement claim.
2. **Cost-simulator check:** our reimplementation of `Rerun`, `iDFlakies` and `Pairwise`, run on the
   authors' released n_F=1 predictions, must reproduce every authors' released Pareto point with
   n_F = 1 (relative tolerance 1e-6).

## Primary endpoint and success rule

Metric: the paper's metric, absolute MCC at threshold 0.5 (signed MCC is also reported), averaged
over 30 repeats, per task. Difference D = context minus baseline, paired by repeat.

A task counts as **improved** only if all of the following hold:
- (a) mean D >= +0.05 absolute MCC (practical size, set in advance);
- (b) the paired 95% interval of D over the 30 repeats (t-interval) excludes 0;
- (c) the baseline passed the reproduction gate.

A task counts as **degraded** if mean D <= -0.02 and its paired interval excludes 0.

**Claim of considerable improvement over CANNIER's classifier** requires:
- at least 2 of the 4 tasks improved, including at least one of NOD-vs-Rest or Victim-vs-Rest; and
- no degraded task.

**Strength qualifier:** the claim is "strong" only if, for each improved task, a paired
project-cluster bootstrap (2,000 resamples of the 30 projects; predictions fixed) gives a 95% interval
for D excluding 0. Otherwise it is "supported within the CANNIER protocol only".

If the rule is not met, the result is reported as such. No changes to features, models, thresholds,
seeds or the rule are made after seeing context results. Any later variant is a new version.

## Secondary endpoint: hybrid cost (authors' cost model, n_F = 1 for both arms)

Using the authors' exact formulas (item run time = mean `time_exec`; Rerun expected reruns with
n_reruns = 2,500; iDFlakies project reruns; Pairwise victim x polluter run time), compute Pareto
fronts over the authors' threshold grid with n_F fixed to 1 for both arms.

Reported per technique:
- knee points (authors' `get_knee_point`) for both arms;
- **cost at matched performance:** the minimum front cost at which the context arm reaches the
  baseline knee-point performance. Relative saving = 1 - context cost / baseline knee cost.

Cost success: relative saving >= 20% for at least one technique, with no technique worse by 20% or
more. Restricting to n_F = 1 is a disclosed compute-budget adaptation. The authors' full multi-n_F
front is reported as a reference, not as a paired comparison.

## Secondary robustness analyses (reported whatever they show)

1. **Mapped-only cohort:** the 86,781 source-mapped cases, no indicator column, same protocol,
   10 repeats. Tests whether gains depend on the availability indicator.
2. **Source-family-grouped folds:** StratifiedGroupKFold(10) by `source_family_id`, so parameterized
   variants of one test function never straddle train/test, 10 repeats. Tests whether gains come
   from memorizing shared fixtures within a source family.
3. Per-project MCC tables for both arms.
4. AP, precision, recall and F1 at 0.5 for both arms.
5. The v0.4 project-held-out result remains the cross-project result.

## Interpretation limits (fixed now)

- The context design and these 30 projects influenced earlier FlakeXplain development; this is a
  retrospective ablation on the base paper's corpus, not untouched confirmation.
- Case-level cross-validation is the base paper's protocol. It lets models see other tests from the
  same project during training, so it does not measure cross-project generalization.
- Offline cost simulation uses the authors' recorded run times; it is not a measured CPU saving.
- Labels are the authors' 2,500-run labels; they are not merged with FlakeXplain's 25-round labels.
- Never claim improvement over CANNIER from comparisons with numbers on a different corpus.
