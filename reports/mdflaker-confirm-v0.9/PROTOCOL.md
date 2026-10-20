# v0.9 confirmation of the v0.8 MDFlaker improvement: protocol and success rule

Status: **DRAFT, 20 October 2026, awaiting team approval.** Nothing below is in force yet. It
becomes frozen only when the team approves it and its SHA-256 is recorded in `protocol.json`.
No v0.9 failure may be collected, rerun or labelled before that.

## 1. Purpose

v0.8 (`reports/mdflaker-fresh-v0.8/RESULTS.md`) met its frozen headline. Its strongest honest
finding came from **post-hoc** analyses (§3 and §6 of that report):
- with strict history, ET-BF beats MDFlaker's classifier on failures of tests not seen in training,
  within the same project: MCC 0.469 vs −0.160;
- the advantage on unseen projects (E2) does not survive strict history.

v0.9 tests the within-project finding **prospectively**:
- on CI failures that occur only after this protocol is frozen;
- with models trained only on v0.8 data;
- with every choice fixed in advance.

The cross-project claim is not retested as a claim (§7).

## 2. Task and labels (unchanged from v0.8)

The task is as in v0.8 `PROTOCOL.md` §2. A failed CI test execution is **flaky** if at least
1 of 30 reruns passes, and **not flaky** if all 30 fail.
- Reruns, environment matching, exclusions and labels follow v0.8 `PROTOCOL.md` §5 and amendments
  **B1** (rerun the tree CI tested), **B2** (mechanics, validity rule, labels) and **B3** (collection
  check).
- The harness is `scripts/mdflaker_v08_rerun_job.py`, at the commit recorded at freeze.

## 3. Projects

The same 8 projects as v0.8, with no additions or replacements: django-rest-framework, urllib3,
pytest, hypothesis, Cirq, conan, prefect and setuptools.

## 4. Collection (label-blind)

- **Window:** workflow runs **created after the freeze timestamp** (recorded in `protocol.json`)
  and up to the collection date **T1 = freeze + 35 days**. Collection happens once, at T1. Logs
  and failure counts are not looked at before then.
- **Extraction:** the same pipeline as v0.8 (`scripts/mdflaker_v08_candidates.py` and
  `mdflaker_v08_probe.py`), applied to the new window. The unit is a failed (test, commit, job)
  execution.
- **Sampling:** all isolated failures (≤ 5 failed tests in the job). From mass-failure jobs, 1 test
  per job is drawn with seed 20261020.
- **Per-project cap:** to bound rerun cost, at most **300** candidates per project are kept. If a
  project has more, they are drawn uniformly with seed 20261020 **before** any rerun.
- **One extension, decided on label-blind counts only:** if fewer than **300 primary-subset
  candidates** (§6) exist at T1, the window is extended **once** to T2 = T1 + 28 days and recollected.
  No other extension is allowed. A short sample is then reported as descriptive only (§7).
- Pilots and recipe fixes are allowed only as in B2/B3: check-only mode, setup and env-check logs
  only, each fix recorded with a date.

## 5. Features and models (frozen; no retraining or tuning on v0.9 data)

- **Features:** MDFlaker's 5 factors (B) and the 17 v0.7 failure-evidence features (F), as in v0.8.
  `flaky_frequency` is replaced by **`flaky_frequency_strict`** from
  `scripts/mdflaker_v08_robustness.py`: it counts only failures from **earlier workflow runs**
  (another `run_id`, with log `created_at` before the failure's own).
- **History for v0.9 failures:** all v0.8 window logs, plus v0.9 window logs from earlier runs.
- **Training set:** all 1,292 v0.8 labelled failures, with strict features. Every model is trained
  once on this set and then applied unchanged to v0.9.
- **Our model:** ET-BF, `ExtraTreesClassifier(n_estimators=100, random_state=20261020)` on B + F,
  flaky if P ≥ 0.5.
- **Comparators** (the same training set):
  - MDF-paper-int and MDF-paper-float (rule plus KNN k = 10, P > 0.7);
  - KNN8-int and KNN8-float;
  - **project prior**: each project's v0.8 majority class.
- **Also reported, not compared in the rule:** ET-B (B only) and ET-BFC (B + F + C).

## 6. Evaluation sets

- **Primary subset (P):** labelled v0.9 failures whose test (repo + node ID, parameters stripped)
  **does not occur** among the 1,292 v0.8 labelled failures.
- **All (A):** every labelled v0.9 failure.

Statistics:
- MCC, F1, precision and recall, pooled and per project;
- 95% intervals from a project bootstrap with 2,000 resamples, seed 20261020, predictions fixed.

## 7. Success rule

Let **C\*** be the comparator with the **highest** MCC on P. Choosing the best comparator after
seeing v0.9 is deliberately conservative.

- **Minimum sample:** P has at least 40 flaky and 40 not-flaky failures, and at least 4 projects
  have failures in P. Below that, all results are descriptive only.
- **Confirmation (headline):** MCC(ET-BF) − MCC(C\*) on P is **≥ +0.10**, **and** the lower bound
  of its 95% project-bootstrap interval is **> 0**.
- **Supporting result (reported, not required):** the same difference on A.
- **Not claimed:**
  - leave-one-project-out on v0.9 is reported descriptively only, and no cross-project claim is
    made whatever its value;
  - ET-BFC versus ET-BF is reported descriptively.

If the headline is not met, the paper reports v0.8's within-project result as **not confirmed**.

## 8. Commitments

- No feature, model, threshold or rule change after the freeze. Only label-blind amendments (for
  example a recipe fix) are allowed, each dated and committed before labels exist.
- Rerun outcomes are labels only, never features.
- Every unlabelled candidate is reported with its reason.
- All results are published whether or not the rule is met.

## 9. Effort

- About 5–9 weeks of wall time, mostly waiting for failures to accumulate.
- About one day of work to collect, plan and run reruns, using the existing scripts.
- About 30 reruns per candidate, so up to roughly 2,400 candidates × 30 runs of only the failing
  tests on GitHub Actions.

## Approval

To freeze, a team member approves this text unchanged. The approver, the freeze timestamp (UTC),
this file's SHA-256 and the harness commit are then recorded in `protocol.json`, and committed
before any v0.9 log is downloaded.
