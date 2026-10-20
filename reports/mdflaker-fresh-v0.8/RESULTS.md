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

The F1 values in the MDFlaker paper come from its own data and split, so they are not comparable
with these.

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
