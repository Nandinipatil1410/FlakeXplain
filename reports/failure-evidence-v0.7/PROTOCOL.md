# v0.7 failure-evidence experiment: frozen protocol and success rule

Status: **Frozen 19 October 2026**, approved by the team (Nandini Patil) as drafted, before any
feature in section 3 was extracted. `protocol.json` holds this file's SHA-256. Everything below is
**Proposed** until `results.json` exists.

## 1. Why this is a new version

v0.6 (`reports/q3q4-base-paper-v0.6/`) found that FlakeXplain's static context features *reduce*
MCC on MDFlaker's failure-level task (C2: −0.036). The likely reason is that the features describe
the test, not the failure. v0.7 is designed **after** seeing v0.6 and uses the same 1,616 rows, so
it is an exploratory follow-up on inspected data. Any paper must say so, and an untouched
confirmation (section 7) is needed before calling it confirmed.

The feasibility checks below are label-blind and done on 19 October 2026:
- every spaCy and DRF build in the dataset has a failed-test list, a traceback dict, its previous
  state, duration, branch and compare URL;
- the row's own traceback exists for 661 of 1,616 rows (DRF 488 of 536, spaCy 173 of 1,080);
- a base..commit diff is computable for 127 of 128 builds. Push builds use their `compare` range.
  PR builds use the merge-base with `main` (DRF) or with the build branch / `master` / `develop`
  (spaCy).

## 2. Question

On MDFlaker's released spaCy and DRF failures, does a model that adds **failure-evidence features**
(co-failures, change content, traceback-to-change relations) beat MDFlaker under **both**
test-grouped CV and leave-one-project-out? Secondary questions: does FlakeXplain context help once
failure evidence is present, and does better ranking reduce reruns?

## 3. New failure-evidence features (F), all available when the build finishes

Sources are the released build history and the git clones. Labels are never read during extraction.

| Feature | Definition |
|---|---|
| `build_failed_tests` | number of entries in the build's `failed_info.failed_tests` |
| `same_file_cofailures` | other failed tests in the same test file in that build |
| `build_duration_s` | Travis build duration |
| `pr_build` | 1 if the compare URL is a pull request |
| `changed_files`, `changed_py_files`, `changed_test_py_files` | `git diff --name-only base..commit` counts (test file = path contains `test`) |
| `nonpy_only_change` | 1 if `changed_py_files == 0` |
| `changed_lines` | added + deleted lines in `.py` files (`--numstat`) |
| `own_test_file_changed` | 1 if the failing test's file is in the diff |
| `path_overlap_depth` | longest common directory-prefix depth between the test file and any changed `.py` file |
| `has_own_traceback` | 1 if the row's test has a traceback entry |
| `traceback_frames` | frames in that traceback (0 if absent) |
| `frames_in_changed_files` | frames whose file is in the diff |
| `last_frame_in_test_file` | 1 if the innermost frame is in the test's own file |
| `frames_outside_repo` | frames in site-packages or the interpreter |
| `min_line_distance_to_change` | smallest gap between a frame line and a changed hunk in the same file, capped at 1,000; 1,000 if there is none or no traceback |

Unresolved diffs (1 spaCy build) get zeros and `diff_available=0`. Any change to a definition
after freezing makes a new version.

## 4. Arms and protocols

Arms: the base candidates (MDF-paper-int, MDF-paper-float, KNN8-int, KNN8-float), ET-B,
**ET-BF** (B + F, the primary "ours" arm) and ET-BFC (B + F + 66 context + indicator). All forests
are `ExtraTreesClassifier(n_estimators=100)` with defaults, threshold 0.5 and no balancing. The
population is spaCy + DRF, 1,616 rows.

- **P1, test-grouped CV:** the same 30 repeated StratifiedGroupKFold(10) splits as v0.6.
- **P2, leave-one-project-out:** 2 folds. Forests are refit with 30 seeds; KNN and the rule are
  deterministic.
- **Comparator per protocol:** the base candidate with the highest mean MCC in that protocol,
  computed from baseline arms before any F feature is used.

## 5. Success rule (to be frozen)

**Headline, "failure-evidence features improve on MDFlaker", requires all of:**
1. P1: ET-BF − comparator ΔMCC ≥ +0.05, and the 30-repeat 95% interval excludes 0;
2. P1: ET-BF − ET-B ΔMCC ≥ +0.02, interval excludes 0. This shows the new features matter, not just
   the classifier swap;
3. P2: ET-BF beats the P2 comparator in **both** held-out projects, with mean ΔMCC ≥ +0.05 over the
   two. Seed spread is reported.
4. Wording keeps the v0.6 qualifiers: "against our reimplementation of the described method", and
   "two of three projects".

**Context claim (secondary), "FlakeXplain context adds value given failure evidence":** P1
ET-BFC − ET-BF ≥ +0.02 with the interval excluding 0, **and** in P2 ET-BFC is no worse than ET-BF
in either project by more than 0.02.

**Rerun-cost endpoint (secondary):** policy "rerun a failure 30 times only if its flakiness score is
at or above t". t is set per model inside each training fold so that 95% of flaky failures are
rerun. Measured as the fraction of held-out failures rerun. Met if ET-BF needs at least 10% fewer
reruns than the P1 comparator at that recall. MDFlaker's score is the rule output (0/1) for
previous-passed rows and the KNN probability otherwise.

Partial outcomes are reported with their own wording: only 1, only 1-2, or only 3.

## 6. Secondary analyses (reported)

F-only (without B), row-level CV (memorization check), per-project tables, feature importance by
permutation on held-out folds, and Random Forest variants.

## 7. Confirmation on untouched data (proposed, requires resources)

GitHub Actions re-runs are too rare for labels: 0 re-runs among 100 sampled spaCy runs and 2 among
100 DRF runs, and logs are deleted after 90 days. Confirmation would instead:
- collect failed test cases from DRF and spaCy CI runs in the last 90 days;
- re-run each failing test 30 times at its commit, as MDFlaker labelled;
- compute F, train the frozen models on all 1,616 rows, and evaluate once.

This needs a GitHub token (log download requires authentication) and CI compute, through our
existing workflow setup. Expected size: tens of failures. It is reported with bootstrap intervals,
and the result is descriptive unless at least 30 flaky and 30 non-flaky cases are obtained.

## 8. Limits fixed in advance

Exploratory follow-up on inspected data; 2 projects; MDFlaker labels from 2020 Travis reruns;
gate G2a failed in v0.6. If P2 fails, no cross-project claim is made.
