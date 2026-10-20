# v0.8 MDFlaker on fresh CI failures: DRAFT protocol (not frozen)

Status: **Proposed, draft.** Nothing has been collected. The project list (section 3) and the rule
(section 7) are frozen before any failure is labelled.

## 1. Purpose

MDFlaker (Software Impacts 2025, SCImago Q3) is the only Q3/Q4-journal flaky-test classifier with
public data (`reports/q3q4-base-paper-v0.6/BASE_PAPER_SEARCH_ROUND2.md`). Its released data have
three problems found in v0.6/v0.7:
- tests memorized across builds;
- build fingerprints;
- in spaCy, traceback availability acting as a label proxy (6.4% vs 81.9% flaky).

There are also only 2 usable projects. v0.8 tests MDFlaker's task on **newly collected, untouched**
failures, with evaluations that remove those shortcuts.

## 2. Task (identical to MDFlaker)

Given one failed test execution in CI, predict whether it is **flaky**: the test passes at least once
in 30 reruns at the same commit. Otherwise it is **not flaky**: it fails all 30 times. This is
MDFlaker's own label definition (`failed_times != 30`).

## 3. Projects (selection rule frozen before collection; labels unknown when selecting)

Candidates are Python projects with public GitHub Actions CI that runs pytest and prints failed
node IDs (`FAILED path::name`). Preference order:
1. spaCy and django-rest-framework, MDFlaker's own projects (DRF uses its own runner; parsed if its
   log format allows);
2. FlakeXplain corpus projects still active on GitHub Actions, e.g. urllib3, rich, pytest, filelock,
   attrs, hypothesis, celery, kombu, loguru, pyramid, tornado, requests, sunpy and others.

Inclusion rule: in the collection window, at least 20 failed test executions parseable from logs.
At most 8 projects, taken in preference order. The list is frozen in `projects.json` before
labelling.

## 4. Collection (label-blind)

Using the GitHub REST API:
- workflow runs from the last 90 days (log retention limit);
- failed jobs;
- job logs, parsed into failed pytest node IDs, short tracebacks (file, line), the run's commit,
  the base commit (push `before` sha, or the PR merge-base), timestamps and the run attempt.

**Unit and sampling (from the label-blind probe, 20 Oct 2026):** the unit is a failed
(test, commit, job) execution.
- **Isolated failures** (the job has ≤ 5 failed tests): all are included.
- **Mass-failure jobs** (> 5 failed tests): only 1 test per job is included, drawn with seed
  20261020. In the 40-log probe these jobs held about 11,400 of 11,657 failures, and one cause is
  shared by every failure in the job; uncapped, they would recreate the build-fingerprint shortcut
  found in v0.7.
- `mass_job` is reported as a stratum. It is not a predictor.

From the same window we build each test's history: pass/fail per run, for runs whose logs list test
outcomes. If no complete pass list exists, history comes only from runs where the test failed, and
this limitation is reported.

## 5. Labelling (30 reruns)

Each failed execution (test, commit) is rerun 30 times at that commit. We use our existing GitHub
Actions workflow setup on a fork, with the project's own test command, the Python version from the
original job, and `-p no:randomly -p no:cov`. Labels:
- **flaky:** at least 1 pass in 30;
- **not flaky:** 30/30 fail;
- **excluded and reported:** environment or setup failures (cannot install, collection error), or
  skip-only results.

Re-runs happen on a different runner from the original CI. This is a known source of label noise,
as it was for MDFlaker.

## 6. Features and arms

- **MDFlaker factors, reimplemented:** traceback coverage of the diff, flakiness frequency from
  history before the failure, test smells (rules reimplemented from `get_test_smells.py`), previous
  state and test size.
- **FlakeXplain:**
  - F: the v0.7 failure-evidence features, *without* `has_own_traceback`, which is excluded in
    advance as a known artifact;
  - C: the 66 static context features.
- **Arms:** MDF-paper (rule plus KNN, k=10, P > 0.7), KNN8, ET-B, ET-BF, ET-BFC, all frozen
  configurations from v0.7.

## 7. Evaluation and success rule (draft values)

- **E1, time-ordered (primary):** within each project, train on the earliest 60% of failures by
  timestamp and test on the latest 40%; pooled across projects. This prevents future-to-past leakage.
- **E2, leave-one-project-out (primary):** train on all other projects.
- **E3, external transfer (secondary):** train on MDFlaker's released 1,616 rows and test on all
  fresh failures, for MDF-paper and for our arms.
- The comparator is the best base candidate per evaluation, chosen on baseline arms only.

**Headline** (fresh data): ET-BF beats the comparator by MCC ≥ +0.05 in **both** E1 and E2, with
project-bootstrap 95% intervals excluding 0 (at least 4 projects needed for E2), **and** ET-BF beats
ET-B by ≥ +0.02 in E1. **Context claim:** ET-BFC − ET-BF ≥ +0.02 in E1, and no worse in E2.

**Minimum sample:** at least 60 flaky and 60 not-flaky labelled failures across at least 4 projects.
Below that, results are descriptive only.

## 8. Effort and requirements

- A GitHub token with public-repository read access, for logs; it stays in an environment variable
  and is never written into files.
- A fork to run reruns on GitHub Actions. About 30 reruns × N failures; each job reruns only the
  failing tests.
- Roughly 1–2 weeks of wall time, depending on how many failures exist in the 90-day window.
