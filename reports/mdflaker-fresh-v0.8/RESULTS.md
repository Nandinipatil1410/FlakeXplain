# v0.8 MDFlaker on fresh CI failures: results

Status: **Empirically verified, 20 October 2026.** Computed by `scripts/mdflaker_v08_analyze.py`
(frozen rule, `PROTOCOL.md` §7 with amendments B1–B3) and `scripts/mdflaker_v08_diagnostics.py`
(post-hoc checks, **outside** the frozen rule). Raw numbers: `results.json`, `diagnostics.json`,
`labels_summary.json`, `features_summary.json`. Labels: `local-evidence/mdflaker-fresh-v0.8/labels.csv`
(SHA-256 `3d856bde…b4c2`), not committed.

## 1. Data

- **Candidates:** 1,659 frozen failed executions from 8 projects.
- **Reruns:** 30 per candidate, in 6 batches of GitHub Actions runs:
  - 39391984769, 39392001716, 39400858694 (batches 00–02);
  - 39416723189, 39432208752, 39432222851 (batches 03–05).

**Labelled:** 1,292 candidates — **409 flaky** (≥ 1 pass in 30) and **883 not flaky** (30/30 fail).
**Unlabelled:** 367, each with a recorded reason:

| Reason | Count |
|---|---:|
| Invalid node ID(s) in the rerun environment | 175 |
| Failed environment check | 86 |
| Setup failed | 38 |
| Mixed, skipped or missing outcomes | 35 |
| Cygwin environment (excluded by the planner) | 18 |
| Incomplete rounds | 11 |
| No artifact | 4 |

| Project | Labelled | Flaky | Flaky % |
|---|---:|---:|---:|
| hypothesis | 177 | 161 | 91.0 |
| prefect | 191 | 62 | 32.5 |
| conan | 181 | 17 | 9.4 |
| django-rest-framework | 27 | 5 | 18.5 |
| setuptools | 30 | 11 | 36.7 |
| pytest | 316 | 68 | 21.5 |
| Cirq | 158 | 22 | 13.9 |
| urllib3 | 212 | 63 | 29.7 |

- The minimum sample is met: ≥ 60 per class, across 8 projects, all with both classes.
- 1,459 of 1,659 candidates (88%) mapped to their test function's source.
- 761 candidates have a parsed traceback.

## 2. Frozen-rule results (MCC; pooled over test parts)

| Arm | E1 time-ordered | E2 leave-one-project-out | E3 transfer (secondary) |
|---|---:|---:|---:|
| MDF-paper-int | 0.033 | −0.054 | 0.156 |
| MDF-paper-float | 0.091 | −0.014 | — |
| KNN8-int | 0.180 | −0.095 | — |
| KNN8-float | 0.239 | −0.044 | 0.283 |
| ET-B | 0.569 | 0.346 | 0.264 |
| **ET-BF** | **0.755** | **0.357** | 0.173 |
| ET-BFC | 0.716 | 0.390 | 0.128 |

- **Comparator** (best baseline arm): KNN8-float in E1; MDF-paper-float in E2.
- **E1:** n = 516 (171 flaky). ET-BF F1 = 0.82, precision 0.91, recall 0.75.
- **E2:** n = 1,292. ET-BF F1 = 0.55.

| Rule term | Required | Observed | 95% project-bootstrap CI | Met |
|---|---|---:|---|---|
| ET-BF − comparator, E1 | ≥ +0.05, CI > 0 | +0.516 | [0.216, 0.919] | yes |
| ET-BF − comparator, E2 | ≥ +0.05, CI > 0 | +0.370 | [0.031, 0.698] | yes |
| ET-BF − ET-B, E1 | ≥ +0.02 | +0.186 | [−0.028, 0.543] | yes |
| ET-BFC − ET-BF, E1 (context) | ≥ +0.02 | −0.039 | [−0.134, 0.088] | no |
| ET-BFC − ET-BF, E2 (context) | ≥ 0 | +0.033 | [−0.052, 0.108] | yes |

**Headline met. Context claim not met.**

## 3. Post-hoc diagnostics (not part of the rule; they qualify how to read §2)

1. **Project base rates explain much of pooled E1.** Predicting each project's training-majority
   class gives E1 MCC **0.52**. ET-BF exceeds it by +0.24, CI [−0.01, 0.87]. Within projects, ET-BF
   averages 0.56 MCC versus 0.31 for ET-B. It is −0.07 on hypothesis, where 91% of failures are flaky.
2. **Test memorization inflates E1.** On E1 test failures whose test also occurs in training
   (n = 195), ET-BF scores 0.98. On **tests never seen in training** (n = 321, 91 flaky, 8 projects):
   - ET-BF **0.57**, ET-B 0.38, KNN8-float −0.08 and project prior 0.15;
   - ET-BF − KNN8 = +0.65, CI [0.22, 1.07].

   The signal survives, but the E1 headline magnitude does not.
3. **Traceback availability is not a label proxy here.** Its direction varies by project: pytest is
   71% flaky with a traceback and 3% without; Cirq is 6% with a traceback and 22% without. Dropping
   `traceback_frames` leaves E1 unchanged (0.755) and raises E2 from 0.357 to 0.496.
4. **Top features** (permutation importance, E1):
   - `flaky_frequency` (0.24);
   - then `same_file_cofailures`, `own_test_file_changed`, `frames_outside_repo`,
     `last_frame_in_test_file` and `previous_state`.

   `flaky_frequency` counts the test's failures up to the failure's timestamp. That includes sibling
   jobs of the same run that started at the same time, so it partly measures "failed in one job vs
   in many jobs". That information is only available once those jobs finish.
5. **E3 transfer is weak.** Models trained on MDFlaker's released 2020 Travis data reach at most
   MCC 0.28 (KNN8-float) on the fresh failures. ET-BF reaches 0.17.

## 4. MDFlaker vs ours, all metrics

The same labelled failures, splits and labels are used for every model:
- **MDFlaker:** the reimplemented rule plus KNN (k = 10, P > 0.7), on integer factors;
- **KNN8:** MDFlaker's 5 factors with k = 8;
- **Ours:** ET-BF.

The unseen-tests rows are the E1 test part restricted to tests absent from training (§3.2), computed
with the same code as `mdflaker_v08_diagnostics.py`.

| Evaluation | Model | MCC | F1 | Precision | Recall |
|---|---|---:|---:|---:|---:|
| Unseen tests (n = 321, 91 flaky) | MDFlaker | −0.160 | 0.134 | 0.151 | 0.121 |
| | KNN8 | −0.084 | 0.141 | 0.196 | 0.110 |
| | **Ours** | **0.568** | **0.654** | **0.806** | **0.549** |
| E1 time-ordered (n = 516, 171 flaky) | MDFlaker | 0.033 | 0.325 | 0.357 | 0.298 |
| | KNN8 | 0.239 | 0.424 | 0.551 | 0.345 |
| | **Ours** | **0.755** | **0.824** | **0.908** | **0.754** |
| E2 leave-one-project-out (n = 1,292, 409 flaky) | MDFlaker | −0.054 | 0.247 | 0.274 | 0.225 |
| | KNN8 | −0.044 | 0.207 | 0.274 | 0.166 |
| | **Ours** | **0.357** | **0.553** | **0.574** | **0.533** |
| E3 trained on MDFlaker's 2020 data | MDFlaker | 0.156 | 0.454 | 0.405 | 0.518 |
| | KNN8 | **0.283** | **0.541** | 0.465 | **0.648** |
| | Ours | 0.173 | 0.375 | **0.474** | 0.311 |

The Software Impacts article reports no precision, recall or F1 (`reports/q3q4-base-paper-v0.6/published_reference.json`).
Any numbers in the APSEC 2021 paper, which we have not read, would come from its own data and split, so they
would not be comparable with these. (Corrected 20 October 2026; the earlier sentence wrongly implied that
the MDFlaker paper reports F1 values.)

## 5. Reading

On newly collected failures with 30-rerun labels, adding failure-evidence features (F) to
MDFlaker's factors improves on MDFlaker's own classifiers under both frozen evaluations. This holds
on tests never seen in training (MCC 0.57 vs −0.08), which is the most conservative check.

The large pooled E1 numbers are inflated by project base rates and by repeated tests, so they
should not be quoted without §3. The E2 margin mostly reflects the baselines collapsing, with MCC
below 0 when the project is unseen.

The 66 static context features (C) do not help: the context claim fails in E1.

Limitations:
- reruns ran on different runners from the original CI;
- 22% of candidates are unlabelled;
- hypothesis dominates the flaky class;
- the diagnostics are post hoc.

## 6. Post-hoc robustness (not part of the rule; `robustness.json`, `scripts/mdflaker_v08_robustness.py`)

These analyses were added after the results above. They do not change the frozen rule or `results.json`.
The script reproduces the original numbers exactly before swapping the feature. It recomputes
`flaky_frequency` from the logs and matches the stored value on 1,292/1,292 rows, and its original
MCCs equal §4.

### 6.1 Strict history

`flaky_frequency_strict` counts only failures of the test in **earlier workflow runs**: a different
`run_id`, with the log's `created_at` before the failure's own. This excludes sibling jobs of the same
run, which may not have finished at prediction time. The original value is never 0, because it always
counts the failure itself. The strict value is 0 for 646 of the 1,292 rows and differs from the
original on 1,193 rows. Its mean is 0.23 for flaky rows and 0.06 for not-flaky rows; the original
means are 0.33 and 0.12.

MCC with the strict feature replacing the original (the same splits, labels and models):

| Evaluation | Model | Original | Strict |
|---|---|---:|---:|
| E1 time-ordered (n = 516, 171 flaky) | MDFlaker | 0.033 | 0.033 |
| | KNN8 | 0.239 | 0.225 |
| | ET-BF | 0.755 | 0.679 |
| E2 leave-one-project-out (n = 1,292, 409 flaky) | MDFlaker | −0.054 | −0.054 |
| | KNN8 | −0.044 | −0.126 |
| | ET-BF | 0.357 | **0.100** |
| Unseen tests, E1 (n = 321, 91 flaky) | MDFlaker | −0.160 | −0.160 |
| | KNN8 | −0.084 | −0.128 |
| | ET-BF | 0.568 | 0.469 |

ET-BF minus KNN8 (project bootstrap 95% CI):

| Evaluation | Original | Strict |
|---|---|---|
| E1 | +0.52 [0.22, 0.92] | +0.45 [0.21, 0.78] |
| E2 | +0.40 [0.16, 0.64] | +0.23 [−0.03, 0.48] |
| Unseen tests | +0.65 [0.25, 1.04] | +0.60 [0.14, 0.86] |

ET-BF minus MDFlaker is +0.65 [0.39, 0.93] for E1 and +0.15 [−0.11, 0.45] for E2.

MDFlaker is unchanged because it uses integer factors: `trunc(flaky_frequency)` is 0 for both
variants.

**Reading:**
- Within-project results (E1 and unseen tests) survive strict history, though they are smaller.
- The E2 advantage does **not** survive: ET-BF falls to 0.10 MCC and both CIs include 0.
- Much of the cross-project signal came from same-run sibling failures, which are not available at
  prediction time. Claims about unseen projects should use the strict numbers.

### 6.2 SHAP explanations (ET-BF, E1)

ET-BF was trained on the E1 training part and explained with `shap.TreeExplainer` (shap 0.51.0)
on the E1 test part. In that part there are 129 true positives, 332 true negatives, 13 false
positives and 42 false negatives. The base value is P(flaky) = 0.307, and SHAP values add up to
the predicted probability (maximum error < 1e-13).

Global ranking by mean |SHAP| (original feature; the full list and the strict-feature ranking are in
the JSON):

1. `flaky_frequency` 0.090
2. `last_frame_in_test_file` 0.068
3. `own_test_file_changed` 0.060
4. `traceback_frames` 0.036
5. `job_duration_s` 0.031
6. `frames_outside_repo` 0.031

With the strict feature, `flaky_frequency` drops to 4th (0.031). `own_test_file_changed` (0.076) and
`last_frame_in_test_file` (0.074) lead the strict ranking.

Local examples (the most confident case of each kind). Contributions are changes in P(flaky):

| Case | Test | P(flaky) | Largest contributions |
|---|---|---:|---|
| True positive (flaky) | hypothesis `test_observability.py::test_assume_has_status_reason` | 1.00 | `last_frame_in_test_file` = 1: +0.25; `flaky_frequency` = 0.51: +0.19; `job_duration_s` = 3618: +0.11 |
| True negative (not flaky) | prefect `test_schedules.py::…::test_rrule_schedule_preserves_and_localizes_rdates` | 0.00 | `own_test_file_changed` = 1: −0.08; `same_file_cofailures` = 4: −0.07; `last_frame_in_test_file` = 0: −0.05 |
| False positive | hypothesis `test_exceptiongroup.py::test_discard_multiple_frozen` | 0.86 | `last_frame_in_test_file` = 1: +0.27; `flaky_frequency` = 0.50: +0.17; `same_file_cofailures` = 1: −0.07 |

The negative example is what a real regression looks like: the test's own file changed and several
tests in the same file failed together. The false positive has the same profile as the
hypothesis true positive.

SHAP explains what the model uses, not what causes flakiness. These are post hoc and were not part
of the frozen protocol.

## 7. Extra post-hoc statistics (not part of the rule; `posthoc_extra.json`, `scripts/mdflaker_v08_posthoc_extra.py`)

Added on 20 October 2026, while drafting the paper, after everything above was known. The script
reproduces the §6.1 MCCs exactly. Each interval uses its own generator seeded with 20261020, so
intervals here differ slightly from `robustness.json` and `diagnostics.json`. Those files draw all
their intervals from one generator stream, so each interval depends on how many came before it. For
example, strict ET-BF − KNN8 on unseen tests is [0.14, 0.86] in §6.1 and [0.10, 0.85] here. The two
unseen-tests intervals in §3 and §6.1 ([0.22, 1.07] vs [0.25, 1.04]) differ for the same reason.
This is Monte Carlo variation, not a different analysis.

### 7.1 Missing intervals (strict history; MCC difference, 95% project bootstrap)

| Subset | ET-BF − MDFlaker | ET-BF − KNN8 | ET-BF − project prior |
|---|---|---|---|
| E1 (n = 516, 171 flaky) | +0.65 [0.38, 0.97] | +0.45 [0.17, 0.79] | +0.16 [−0.09, 0.71] |
| Unseen tests (n = 321, 91 flaky) | **+0.63 [0.14, 0.94]** | +0.60 [0.10, 0.85] | **+0.32 [−0.29, 0.61]** |

The project prior (each project's E1 training-majority class) scores 0.52 in E1 and 0.15 on unseen
tests. Under strict history, **ET-BF's advantage over the project prior is not significant**, either
in E1 or on unseen tests.

### 7.2 Unseen tests per project (strict history, MCC)

| Project | n | Flaky | MDFlaker | KNN8 | ET-BF |
|---|---:|---:|---:|---:|---:|
| hypothesis | 11 | 7 | −0.418 | −0.810 | −0.828 |
| prefect | 59 | 55 | −1.000 | 0.000 | 0.294 |
| conan | 52 | 2 | 0.039 | −0.049 | 0.214 |
| django-rest-framework | 8 | 2 | −0.149 | 0.447 | 0.000 |
| setuptools | 11 | 6 | 0.430 | 0.289 | 0.430 |
| pytest | 114 | 3 | 0.000 | 0.000 | 0.000 |
| Cirq | 48 | 12 | −0.348 | −0.320 | 0.364 |
| urllib3 | 18 | 4 | 0.209 | −0.426 | 1.000 |

Per project, ET-BF beats MDFlaker in 5 projects, ties in 2 and loses in 1 (hypothesis). Its median
is 0.25, against the pooled 0.469. Several subsets have 2–4 flaky failures. **Pooled MCC therefore
includes differences between projects**: for example, 55 of prefect's 59 unseen failures are flaky.
It is not only discrimination within projects.

### 7.3 Without hypothesis (same fitted models, scored on the other 7 projects)

| Subset (strict) | n | Flaky | MDFlaker | KNN8 | ET-BF | ET-BF − MDFlaker |
|---|---:|---:|---:|---:|---:|---|
| E1 | 445 | 104 | −0.102 | −0.056 | 0.594 | +0.70 [0.30, 1.05] |
| Unseen tests | 310 | 84 | −0.146 | −0.107 | 0.521 | +0.67 [0.19, 0.99] |

Without hypothesis the project prior is constant (not flaky everywhere), so its MCC is 0.

### 7.4 Timing audit of the features (code review of `scripts/mdflaker_v08_features.py`, no new run)

- **Available when the failed job finishes:** the job-log features (`build_failed_tests`,
  `same_file_cofailures`, `job_duration_s`, all traceback features), the change features (git diff
  of the tested tree) and the static features.
- **`same_file_cofailures`** counts other *candidates* from the same job. For a mass-failure job only
  1 test is sampled, so it is 0 there even when many tests failed. This is a sampling artifact, not a
  leak; `build_failed_tests` still gives the job's failure count.
- **`previous_state`** takes the conclusion, as returned by the API at collection time, of the
  latest earlier run of the same workflow on the same branch. That run may still have been in
  progress, or may have been rerun later, when the failure happened. This is a possible small leak,
  of the same kind as `flaky_frequency`; its size has not been measured.
- **`flaky_frequency_strict`** uses earlier runs' logs keyed by run creation time. An earlier run
  that was still running at prediction time is counted. This is a residual timing gap; its size has
  not been measured.
