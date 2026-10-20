# Is This CI Failure Flaky? Revisiting MDFlaker on Fresh, Rerun-Labelled Failures

**Draft v1, 20 October 2026. Not for submission.**
Authors: Nandini Patil, Bhumika Mane, Trusha Kulkarni, Pranavi Baad (author order and affiliations TBD).

Status conventions used in this draft (from `AGENTS.md`): every result is tagged as **frozen rule**
(decided before the data were labelled), **post hoc** (computed after the frozen results were
known) or **planned** (v0.9, not yet collected). Every number is taken from a report or JSON file in
this repository; the source is given in brackets, for example [v0.8 RESULTS §6.1]. Paths are relative
to the repository root. Citations whose details are not in the repository are marked
**[CITE NEEDED]**.

Source abbreviations:
- **v0.6** = `reports/q3q4-base-paper-v0.6/` (PROTOCOL, AMENDMENT_A1/A2, STAGE1_2_RESULTS, STAGE3_RESULTS, BASE_PAPER_SEARCH*, `published_reference.json`)
- **v0.7** = `reports/failure-evidence-v0.7/` (PROTOCOL, RESULTS)
- **v0.8** = `reports/mdflaker-fresh-v0.8/` (PROTOCOL, AMENDMENT_B1–B3, RESULTS, `results.json`, `diagnostics.json`, `robustness.json`, `labels_summary.json`, `features_summary.json`)
- **v0.9** = `reports/mdflaker-confirm-v0.9/` (PROTOCOL, `protocol.json`)

---

## 1. Abstract

When a test fails in continuous integration (CI), developers must decide whether the failure is a
real regression or a flaky failure that would pass on a rerun. MDFlaker (Software Impacts, 2025)
addresses this failure-level task with five factors (traceback coverage of the change, flakiness
frequency, test smells, previous state and test size) and a rule plus k-nearest-neighbour (KNN)
classifier. We first re-examine MDFlaker's released dataset and show that it cannot support a fair
improvement claim: only two of its three projects have retrievable source, whether a traceback was
stored is close to a label proxy in spaCy (6.4% vs 81.9% flaky), and failures from the same tests
and builds make within-project evaluations optimistic. We therefore collect a new dataset: 1,659
failed pytest executions from the GitHub Actions logs of 8 Python projects, each rerun 30 times on the
code the CI job actually tested. 1,292 failures receive labels (409 flaky, 883 not flaky); the 367
unlabelled ones are reported with reasons. We add 17 failure-evidence features (co-failures, change
content and traceback-to-change relations) to MDFlaker's factors and train an Extra Trees model
(ET-BF). Under a success rule frozen before labelling, ET-BF beats the best MDFlaker-style baseline in
both a time-ordered within-project evaluation (MCC 0.755 vs 0.239) and leave-one-project-out
(0.357 vs −0.014). Post-hoc checks show that these headline numbers are inflated by project base rates,
by repeated tests, and by a history feature that counts concurrent sibling jobs. With a strict,
prediction-time-safe history feature and only on failures of tests never seen in training, ET-BF
reaches MCC 0.469 against −0.160 for our reimplementation of MDFlaker; the cross-project advantage
does not survive (MCC 0.100, interval includes 0). Static test-code context features do not help in
any experiment. A prospective confirmation on failures occurring after 20 October 2026 is frozen and
will be reported after collection on 24 November 2026.

---

## 2. Introduction

A flaky test passes or fails without any change to the code under test. In CI, each failed test
raises a triage question: should the developer investigate a regression, or rerun the job? Rerunning
every failure many times is expensive, and ignoring failures hides real bugs. A classifier that
predicts, for one failed execution, whether it is flaky can rank failures for rerunning or
investigation.

MDFlaker [Ahmad 2025; Ahmad et al. 2021] is, to our knowledge, the only flaky-test *classifier* with
public data published in a Q3/Q4 journal. Our search covered 743 Q3/Q4 computer-science journals in
SCImago's 2025 rankings [v0.6 BASE_PAPER_SEARCH_ROUND2]. MDFlaker's task is failure-level: given one
failed execution, predict whether it would pass in at least one of 30 reruns. Its released data cover
2,151 failed executions from spaCy, django-rest-framework (DRF) and Superset [v0.6 PROTOCOL].

This paper started as an attempt to improve on MDFlaker using its own released data. That attempt
failed in an informative way (Section 4). The data contain shortcuts that let a model look much
better than it is, and once they are removed MDFlaker's simple rule generalizes across projects better
than any learned model we tried [v0.7 RESULTS]. We then collected new failures and evaluated in a
way designed to avoid those shortcuts.

**Contributions.**
1. **A re-examination of MDFlaker's released data** (Section 4): a traceback-availability label proxy,
   build fingerprints and test memorization, and the consequences for evaluation design.
2. **A new failure-level dataset** (Section 5): 1,659 fresh GitHub Actions failures from 8 Python
   projects, labelled by 30 reruns on the tree CI tested, with every exclusion reported.
3. **A preregistered-style comparison** (Sections 6–8): MDFlaker's factors plus failure-evidence
   features under a success rule frozen before labelling, followed by clearly labelled post-hoc
   checks that narrow the claim to what survives: a within-project gain on unseen tests, under
   strict history.
4. **Two negative results**: the cross-project gain disappears under strict history, and static
   test-code context features never help on this task.
5. **A frozen prospective confirmation plan** (Section 11) whose results are not yet known.

We deliberately report the smaller, defensible numbers as the main result and the larger frozen-rule
numbers as context.

---

## 3. Background and related work

### 3.1 Flaky tests and rerun-based detection

Flaky tests have been studied extensively [CITE NEEDED: survey of flaky-test research, e.g. a
general survey or empirical study]. The standard way to observe flakiness is rerunning. iDFlakies
[Lam et al., ICST 2019; CITE NEEDED: full reference] reruns test suites in the original order and in
modified orders and separates order-dependent (OD) from non-order-dependent (NOD) flaky tests. Our
earlier FlakeXplain work ported this methodology to pytest (`AGENTS.md`). The present paper uses the
simpler rerun label that MDFlaker uses (Section 5.3), not iDFlakies reordering.

### 3.2 Combining reruns and machine learning: CANNIER

CANNIER [Parry, Kapfhammer, Hilton and McMinn, *Empirical Software Engineering* 28, 2023,
doi:10.1007/s10664-023-10307-w] combines rerun-based detection with machine-learning models, using
model predictions to decide which tests to rerun and so reduce detection cost. In our earlier v0.5
experiment (`reports/cannier-protocol-v0.5/RESULTS.md`), adding 66 static context features to
CANNIER's 18 features under CANNIER's own protocol gave consistent but mostly small gains (absolute
MCC +0.029 to +0.096 across four tasks; only victim detection cleared the pre-set +0.05 threshold).
CANNIER is test-level and is published in a Q1 journal, so it is related work here rather than the
base paper.

### 3.3 MDFlaker

MDFlaker [A. Ahmad, "MDFlaker: A tool for multi-factor detection and root cause analysis of flaky
tests", *Software Impacts* 26 (2025) 100794, doi:10.1016/j.simpa.2025.100794] is a tool paper. The
method and its evaluation originate in Ahmad, Gomes, Shi, Sandahl and Leifler, APSEC 2021,
doi:10.1109/APSEC53868.2021.00041 [v0.6 PROTOCOL]. The tool uses five factors per failed execution:

- **Traceback coverage:** whether the failure's traceback covers the recent code changes;
- **Flaky frequency:** the test's past flakiness from build history;
- **Test smells:** counted with rules from the released `get_test_smells.py`;
- **Previous state:** the test's outcome in the previous build;
- **Test size.**

As described in Section 2.3 of the paper and implemented in the released code
(`mysql_handler.py`), the classifier is conditional [v0.6 AMENDMENT_A1]:
- *Scenario 1* (previous build state passed): the failure is flaky if and only if the traceback does
  **not** cover the recent changes;
- *Scenario 2* (otherwise): `KNeighborsClassifier(10, p=1)` on integer-cast factors, flaky if
  P(flaky) > 0.7.

The released `evaluate.py` instead uses KNN with k = 8 on a single 80-row hold-out [v0.6
BASE_PAPER_SEARCH]. The Software Impacts article reports no precision, recall, F1 or accuracy; its
only quantitative result is a figure of unlabelled detection counts [v0.6 `published_reference.json`].
We could not obtain the APSEC 2021 paper. We therefore compare against **our reimplementation of the
described method**, never against MDFlaker's reported numbers.

### 3.4 Other flaky-test prediction work

- **Static and vocabulary-based prediction:** FLAST [Verdecchia et al., 2021], cross-project flaky
  test prediction [Afeltra et al., 2024], linguistic diversity [Ahmad et al., 2025], LLMs for
  cross-language detection [Ahmad and Sun, 2025], all in *IEEE Access*; and Pontillo et al. [2022,
  *Empirical Software Engineering*] [v0.6 BASE_PAPER_SEARCH; CITE NEEDED: full references]. These
  predict test-level flakiness from test code, which is closest to our static context features (C).
  Other well-known static predictors such as FlakeFlagger and Flakify [CITE NEEDED] belong here too.
- **CI-artifact models:** HgtFlaky [Dai et al., *Computers* (MDPI), 2026, doi:10.3390/computers15060372]
  uses a graph transformer on CI runtime artifacts for Java benchmarks.
- **Other Q3/Q4-journal flaky-test papers**, none a classifier with public data [v0.6
  BASE_PAPER_SEARCH, BASE_PAPER_SEARCH_ROUND2]: adaptive latest-position execution for Android
  [Zhang, Wang and Zhao, IJSEKE 2024, doi:10.1142/s0218194024500232]; JS-TOD for Jest order dependency
  [Hashemi et al., *Science of Computer Programming* 2026, doi:10.1016/j.scico.2026.103462]; FlakyLoc
  [*Journal of Web Engineering* 2020, doi:10.13052/jwe1540-9589.1927]; and an industrial ML detector
  without public data [Elgazzar et al., LNNS 2026; CITE NEEDED: full reference].
- **Explanations:** we use SHAP [CITE NEEDED: Lundberg and Lee] with TreeExplainer [CITE NEEDED].

**Positioning.** Most prediction work is test-level: is this test flaky? MDFlaker and this paper are
failure-level: is *this failure* flaky? The distinction matters because failure-level evidence
(co-failures in the same job, the change being tested, the traceback) is available, whereas a
static view of the test is constant across all of its failures.

---

## 4. Problems in MDFlaker's released data

All findings in this section come from v0.6 and v0.7, which used MDFlaker's release (authors'
repository at commit `618dc047`, byte-identical to the paper's linked repository
`SIMPAC-2025-241@5b63f3a`) [v0.6 AMENDMENT_A1].

### 4.1 Coverage and reproduction

- **Superset is unusable.** 81 of its 84 build commits cannot be retrieved from GitHub; they were
  probably Travis pull-request merge commits. The study population therefore has 2 projects: spaCy
  (1,080 rows) and DRF (536), 1,616 rows with 1,033 flaky (63.9%) [v0.6 AMENDMENT_A2,
  STAGE1_2_RESULTS].
- **Implementation check failed.** Only 142 released tool decisions join uniquely to the dataset. On
  those, our reimplementation agrees with the recorded decision 74.6% of the time, below our 90% gate
  [v0.6 STAGE1_2_RESULTS].
- **Data facts.** 83 (build, test) keys occur more than once; 4 of them have conflicting labels
  [v0.6 STAGE1_2_RESULTS].

### 4.2 The label is MDFlaker's rerun label, but a parser artifact acts as a proxy

MDFlaker labels a failure flaky when it did not fail in all 30 reruns (`failed_times != 30`) [v0.6
BASE_PAPER_SEARCH]. We keep that definition. In the released spaCy data, however, rows whose test has
a stored traceback are 6.4% flaky (173 rows), and rows without one are 81.9% flaky (907 rows) [v0.7
RESULTS]. Whether the authors' log parser stored a traceback is therefore close to a label proxy. In
v0.7, the indicator `has_own_traceback` was the second most important feature (permutation importance
0.20), after MDFlaker's own traceback coverage (0.52). A deployed tool would not see the same
availability pattern.

### 4.3 Test memorization

Only 448 distinct test names cover the 2,151 rows [v0.6 PROTOCOL]. Any feature that is constant per
test can act as a test identifier. Under the authors' row-level split, adding our static context
features appears to help (ET-BC 0.905 vs ET-B 0.838 MCC), but under test-grouped cross-validation
the same features *reduce* MCC (0.642 → 0.606, Δ −0.036 [−0.053, −0.019]) [v0.6 STAGE3_RESULTS]. A
row-level evaluation would have produced a spurious "context helps" result.

### 4.4 Build fingerprints

Test-grouped folds still put other failures from the same build into training. With folds grouped
by build instead, our failure-evidence features reduce MCC (ET-BF vs ET-B: −0.034 [−0.039, −0.029])
[v0.7 RESULTS]. Linking tests and builds puts all of spaCy and 95% of DRF into one connected
component, so no within-project split is free of both shortcuts.

### 4.5 What survives

The only evaluation free of both shortcuts is leave-one-project-out. There, MDFlaker's conditional
rule (MDF-paper-int) beats every learned model we tried:
- v0.6: 0.442 (test spaCy) / 0.824 (test DRF), against ET-B 0.353 / 0.250 [v0.6 STAGE3_RESULTS];
- v0.7: against ET-BF, spaCy 0.442 vs 0.275 and DRF 0.824 vs 0.093 [v0.7 RESULTS].

The v0.7 frozen headline was therefore not met. We conclude that MDFlaker's release, with two
projects and heavily linked tests and builds, cannot support an honest improvement claim. Both v0.6
and v0.7 were run on data we had already inspected, so they are exploratory.

**Lessons carried into the new study:**
1. evaluate on newly collected failures;
2. cap mass-failure jobs so one build cannot contribute many near-identical rows;
3. exclude traceback *availability* as a feature in advance;
4. report results on tests not seen in training.

---

## 5. The new dataset

### 5.1 Projects

Projects were selected by a rule frozen before collection, while labels were unknown [v0.8
PROTOCOL §3]. Candidates were Python projects with public GitHub Actions CI that runs pytest and
prints failed node IDs. The preference order put MDFlaker's own projects (spaCy, DRF) first, then
projects from the FlakeXplain corpus still on GitHub Actions. A project needed at least 20 parseable
failed executions in the window; at most 8 were taken.

The frozen list is **django-rest-framework, urllib3, pytest, hypothesis, Cirq, conan, prefect and
setuptools**:
- spaCy was excluded with 1 candidate, and sunpy (16) and dask (18) fell below the threshold;
- PyGithub, xonsh and fonttools qualified but fell outside the cap of 8.

### 5.2 Collection (label-blind)

Using the GitHub REST API, we took workflow runs from the last 90 days (the log retention limit),
their failed jobs and job logs. Logs were downloaded on 19 and 20 October 2026 [v0.8 PROTOCOL §4].
Each log was parsed into failed pytest node IDs, short tracebacks (file, line), the commit, the base
commit, timestamps and the run attempt.

- **Unit:** one failed (test, commit, job) execution.
- **Isolated failures** (the job has ≤ 5 failed tests): all included.
- **Mass-failure jobs** (> 5 failed tests): 1 test per job, drawn with seed 20261020. In a 40-log
  probe, these jobs held about 11,400 of 11,657 failures, typically sharing one cause; uncapped, they
  would recreate the build-fingerprint shortcut of Section 4.4.

The frozen candidate list `candidates.csv` has **1,659** failed executions. 1,459 (88%) map to their
test function's source, and 761 have a parsed traceback [v0.8 RESULTS §1, `features_summary.json`].

### 5.3 Labels from 30 reruns

The label is MDFlaker's own [v0.8 PROTOCOL §2]:
- **flaky:** at least 1 pass in 30 reruns;
- **not flaky:** 30 of 30 reruns fail.

Each candidate is rerun 30 times on GitHub Actions in a matching environment: the same OS family
and runner generation and the same Python minor version (PyPy and free-threaded builds where the job
used them), with each project's own CI tooling (tox, nox, `uv sync` or requirements files) and
`-p no:randomly` [v0.8 PROTOCOL §5, AMENDMENT_B2].

Three label-blind amendments were committed before any label existed:
- **B1, rerun what CI tested.** For `pull_request` events, GitHub Actions tests a merge of the head
  into the base branch, not the head commit. We check out the merge base and merge the head on top.
  1,544 candidates are PR runs with a parsed merge line and 115 are push runs [v0.8 AMENDMENT_B1].
- **B2, mechanics and environment validity.** Candidates are grouped into 1,026 rerun environments
  covering 1,641 candidates. Before the rounds, the candidates' files are run once with every
  candidate deselected; the environment is valid if at least 80% of the other tests pass, skip or
  xfail. Recipes were fixed in four check-only pilots, using only setup and environment-check logs
  [v0.8 AMENDMENT_B2].
- **B3, collection check.** A first full attempt was discarded unseen after two harness bugs were
  found: one garbled node ID could abort a whole round, and node-ID formats did not match. A
  `--collect-only` check now excludes uncollectable candidates before any round [v0.8 AMENDMENT_B3].

Labels come from the 6 restarted batches (GitHub Actions runs 39391984769, 39392001716, 39400858694,
39416723189, 39432208752 and 39432222851) [v0.8 RESULTS §1].

### 5.4 Counts and exclusions

**1,292 labelled: 409 flaky and 883 not flaky. 367 unlabelled** [v0.8 RESULTS §1,
`labels_summary.json`].

| Reason unlabelled | Count |
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
| **Total** | **1,292** | **409** | **31.7** |

All 8 projects have both classes, and the frozen minimum sample (≥ 60 per class across ≥ 4
projects) is met. Base rates differ widely: hypothesis is 91% flaky, conan 9.4%. Section 8.2 shows
why this matters.

---

## 6. Method

### 6.1 Features

**B: MDFlaker's five factors, reimplemented** [v0.8 PROTOCOL §6, `features_summary.json`]:
`flaky_frequency`, `traceback_coverage`, `test_smells` (rules reimplemented from `get_test_smells.py`),
`previous_state` and `test_size`. History comes from the same 90-day window, using runs whose logs
list test outcomes.

**F: 17 failure-evidence features**, defined in v0.7 and frozen before extraction [v0.7 PROTOCOL §3;
`features_summary.json`]. All are available when the failed job finishes:

| Group | Features |
|---|---|
| Co-failures | `build_failed_tests` (failed tests in the job), `same_file_cofailures` (other failed tests in the same file) |
| Job | `job_duration_s`, `pr_build` |
| Change content | `changed_files`, `changed_py_files`, `changed_test_py_files`, `nonpy_only_change`, `changed_lines`, `own_test_file_changed`, `path_overlap_depth`, `diff_available` |
| Traceback to change | `traceback_frames`, `frames_in_changed_files`, `last_frame_in_test_file`, `frames_outside_repo`, `min_line_distance_to_change` |

`has_own_traceback`, the artifact of Section 4.2, was excluded in advance.

**C: 66 static context features** (fixtures, helpers, lifecycle and class state), extracted from the
test's source by the extractor used in FlakeXplain v0.4/v0.5. They describe the test, not the
failure.

### 6.2 Models

All configurations were frozen in v0.7 and reused unchanged [v0.8 PROTOCOL §6]. Each forest is
`ExtraTreesClassifier(n_estimators=100)` with scikit-learn defaults, threshold 0.5 and no class
balancing [v0.7 PROTOCOL §4; CITE NEEDED: Extra Trees].

| Arm | Features | Classifier |
|---|---|---|
| MDF-paper-int | B, integer-cast | MDFlaker's rule plus KNN (k = 10, p = 1, P > 0.7) — our reimplementation of the published method |
| MDF-paper-float | B, floats | same |
| KNN8-int / KNN8-float | B | KNN (k = 8, p = 1, majority vote), as in the released `evaluate.py` |
| ET-B | B | Extra Trees |
| **ET-BF** (ours) | B + F | Extra Trees |
| ET-BFC | B + F + C | Extra Trees |

Integer casting, as in the released code, truncates fractional flaky frequencies to 0 [v0.6
BASE_PAPER_SEARCH]. We include both casts so that the comparator is the stronger variant, not a straw
man. We use the natural class balance; no oversampling is applied.

In the tables below, **"MDFlaker"** means MDF-paper-int and **"KNN8"** means KNN8-float [v0.8
RESULTS §4].

---

## 7. Evaluation design

### 7.1 Evaluations

- **E1, time-ordered within project (primary):** in each project, train on the earliest 60% of
  failures by timestamp and test on the latest 40%; pool predictions across projects. Test part:
  n = 516 (171 flaky); training part: 776.
- **E2, leave-one-project-out (primary):** train on 7 projects, test on the 8th; pool over all
  1,292.
- **E3, external transfer (secondary):** train on MDFlaker's released 1,616 spaCy + DRF rows and test
  on all 1,292 fresh failures. MDFlaker's labels are 2020 Travis 30-rerun labels, and job duration
  replaces build duration.

[v0.8 PROTOCOL §7, `results.json`]

### 7.2 The unseen-tests subset (post hoc)

The E1 test part restricted to failures whose test does not occur in the E1 training part: **n = 321
(91 flaky, 8 projects)**. The other 195 E1 test failures belong to tests seen in training [v0.8
RESULTS §3.2, `diagnostics.json` D5]. This subset was defined after the frozen results were known.
It is the most conservative within-project check we have, and the v0.9 confirmation adopts it as its
primary set in advance (Section 11).

### 7.3 Metric and inference

The main metric is Matthews correlation coefficient (MCC), which stays informative under class
imbalance and is 0 for a constant or random predictor. F1, precision and recall are also reported.
Differences in MCC are given with 95% **project-bootstrap** intervals: 2,000 resamples of projects,
with predictions fixed (`scripts/mdflaker_v08_analyze.py`). With 8 projects these intervals are wide.

### 7.4 The frozen success rule

Frozen on 20 October 2026, before any failure was rerun or labelled [v0.8 PROTOCOL §7]:
- The **comparator** in each evaluation is the best baseline arm (MDF-paper-* or KNN8-*), chosen
  on baseline arms only.
- **Headline:** ET-BF beats the comparator by MCC ≥ +0.05 in **both** E1 and E2, with
  project-bootstrap intervals excluding 0, **and** ET-BF beats ET-B by ≥ +0.02 in E1.
- **Context claim:** ET-BFC − ET-BF ≥ +0.02 in E1, and ≥ 0 in E2.

### 7.5 Strict history (post hoc)

`flaky_frequency` as frozen counts the test's failures up to the failure's timestamp. That includes
sibling jobs of the *same* workflow run that started at the same time. Their results only exist once
those jobs finish, so the feature partly measures "failed in one job vs in many jobs" [v0.8
RESULTS §3.4]. We therefore define `flaky_frequency_strict`, which counts only failures of the test
in **earlier workflow runs**: a different `run_id`, with the log's `created_at` before the failure's
own [v0.8 RESULTS §6.1]. It is 0 for 646 of the 1,292 rows and differs from the original on 1,193
rows; its mean is 0.23 for flaky and 0.06 for not-flaky rows (originally 0.33 and 0.12). The
robustness script reproduces the frozen numbers exactly before swapping the feature.

---

## 8. Results

### 8.1 Main result: strict history, within project (post hoc)

We take the strict-history numbers as the main result, because they use only information available
at prediction time. Same splits, labels and models as the frozen analysis [v0.8 RESULTS §6.1,
`robustness.json`].

| Evaluation | Model | MCC | F1 | Precision | Recall |
|---|---|---:|---:|---:|---:|
| **Unseen tests, E1** (n = 321, 91 flaky) | MDFlaker | −0.160 | 0.134 | 0.151 | 0.121 |
| | KNN8 | −0.128 | 0.101 | 0.146 | 0.077 |
| | **ET-BF** | **0.469** | **0.602** | **0.667** | **0.549** |
| **E1 time-ordered** (n = 516, 171 flaky) | MDFlaker | 0.033 | 0.325 | 0.357 | 0.298 |
| | KNN8 | 0.225 | 0.409 | 0.544 | 0.327 |
| | **ET-BF** | **0.679** | **0.779** | **0.819** | **0.743** |

MCC differences (95% project-bootstrap interval) [v0.8 RESULTS §6.1]:
- unseen tests, ET-BF − KNN8: **+0.60 [0.14, 0.86]**;
- E1, ET-BF − KNN8: +0.45 [0.21, 0.78];
- E1, ET-BF − MDFlaker: +0.65 [0.39, 0.93].

MDFlaker's numbers do not change under strict history, because it casts features to integers and
`trunc(flaky_frequency)` is 0 for both variants.

On failures of tests the model has never seen, in projects it has seen, ET-BF has a clearly positive
MCC, while both MDFlaker-style classifiers are below 0. This is our main claim. Its limits:
- it is post hoc on v0.8, which is why v0.9 exists;
- per-project results vary (Section 8.3);
- the interval is wide.

### 8.2 Frozen-rule results

Frozen-rule MCC, pooled over test parts [v0.8 RESULTS §2]:

| Arm | E1 time-ordered | E2 leave-one-project-out | E3 transfer (secondary) |
|---|---:|---:|---:|
| MDF-paper-int | 0.033 | −0.054 | 0.156 |
| MDF-paper-float | 0.091 | −0.014 | — |
| KNN8-int | 0.180 | −0.095 | — |
| KNN8-float | 0.239 | −0.044 | 0.283 |
| ET-B | 0.569 | 0.346 | 0.264 |
| **ET-BF** | **0.755** | **0.357** | 0.173 |
| ET-BFC | 0.716 | 0.390 | 0.128 |

Comparators: KNN8-float in E1, MDF-paper-float in E2.

| Rule term | Required | Observed | 95% CI | Met |
|---|---|---:|---|---|
| ET-BF − comparator, E1 | ≥ +0.05, CI > 0 | +0.516 | [0.216, 0.919] | yes |
| ET-BF − comparator, E2 | ≥ +0.05, CI > 0 | +0.370 | [0.031, 0.698] | yes |
| ET-BF − ET-B, E1 | ≥ +0.02 | +0.186 | [−0.028, 0.543] | yes |
| ET-BFC − ET-BF, E1 (context) | ≥ +0.02 | −0.039 | [−0.134, 0.088] | no |
| ET-BFC − ET-BF, E2 (context) | ≥ 0 | +0.033 | [−0.052, 0.108] | yes |

**The frozen headline is met; the context claim is not.** ET-BF had E1 F1 0.82 (precision 0.91,
recall 0.75) and E2 F1 0.55. Two qualifications that follow from the table itself:
- the ET-BF − ET-B rule term required only a point estimate, and its interval includes 0;
- in E2, ET-BF and ET-B are nearly equal (Δ +0.011 [−0.104, 0.167], `results.json`), so the E2 margin
  comes from the classifier, not from the F features.

### 8.3 Why the frozen numbers overstate the result (post hoc)

From `diagnostics.json` [v0.8 RESULTS §3]:

1. **Project base rates.** Predicting each project's training-majority class gives E1 MCC 0.52.
   ET-BF exceeds it by +0.24 [−0.01, 0.87]. Pooled E1 rewards learning that hypothesis failures are
   mostly flaky.
2. **Per-project results vary.** Within projects, ET-BF averages 0.56 MCC against 0.31 for ET-B. It
   is −0.07 on hypothesis (91% flaky) and between 0.37 and 0.96 on the others; several projects have
   very few flaky test failures in E1 (conan 3, DRF 2).
3. **Test memorization.** ET-BF scores 0.98 on the 195 E1 test failures whose test also occurs in
   training, and 0.57 on the 321 unseen ones (ET-B 0.38, KNN8-float −0.08, project prior 0.15).
4. **Traceback availability is not a proxy here.** Its relation to the label changes sign by project
   (pytest: 71% flaky with a traceback, 3% without; Cirq: 6% with, 22% without). Dropping
   `traceback_frames` leaves E1 unchanged (0.755) and raises E2 from 0.357 to 0.496.
5. **Same-run history.** `flaky_frequency` is the top permutation-importance feature (0.24), and it
   includes concurrent sibling jobs (Section 7.5).

### 8.4 Original vs strict history, all evaluations (post hoc)

[v0.8 RESULTS §6.1]

| Evaluation | Model | MCC original | MCC strict |
|---|---|---:|---:|
| E1 (n = 516) | MDFlaker | 0.033 | 0.033 |
| | KNN8 | 0.239 | 0.225 |
| | ET-BF | 0.755 | 0.679 |
| E2 (n = 1,292) | MDFlaker | −0.054 | −0.054 |
| | KNN8 | −0.044 | −0.126 |
| | ET-BF | 0.357 | **0.100** |
| Unseen tests (n = 321) | MDFlaker | −0.160 | −0.160 |
| | KNN8 | −0.084 | −0.128 |
| | ET-BF | 0.568 | 0.469 |

| ET-BF − KNN8 (95% CI) | Original | Strict |
|---|---|---|
| E1 | +0.52 [0.22, 0.92] | +0.45 [0.21, 0.78] |
| E2 | +0.40 [0.16, 0.64] | +0.23 [−0.03, 0.48] |
| Unseen tests | +0.65 [0.25, 1.04] | +0.60 [0.14, 0.86] |

Under strict history, ET-BF − MDFlaker is +0.65 [0.39, 0.93] in E1 and +0.15 [−0.11, 0.45] in E2.

### 8.5 Cross-project (E2): the gain does not survive strict history

Under the frozen rule, ET-BF beat the comparator in E2 (+0.370). With strict history, ET-BF falls to
MCC 0.100 (F1 0.416), and both its differences, against KNN8 and against MDFlaker, have intervals
that include 0. Much of the cross-project signal came from same-run sibling failures, which a tool
would not have at prediction time. **We make no claim about unseen projects.** All baselines are at
or below 0 in E2, so even the frozen E2 margin mostly reflects the baselines collapsing.

### 8.6 External transfer (E3)

Models trained on MDFlaker's released 2020 Travis data transfer poorly to the fresh failures: the
best is KNN8-float (MCC 0.283, F1 0.541), and ET-BF reaches 0.173 [v0.8 RESULTS §4]. Our features do
not help when trained on the old data, which is consistent with Section 4's finding that those data
reward dataset-specific shortcuts.

### 8.7 Static context features (C): a negative result

Static test-code context never helped on the failure-level task:

| Study | Comparison | ΔMCC (95% interval) |
|---|---|---|
| v0.6, released data, test-grouped CV | ET-BC − ET-B | −0.036 [−0.053, −0.019] |
| v0.7, released data, test-grouped CV | ET-BFC − ET-BF | −0.057 [−0.067, −0.047] |
| v0.8, fresh data, E1 | ET-BFC − ET-BF | −0.039 [−0.134, 0.088] |
| v0.8, fresh data, E2 | ET-BFC − ET-BF | +0.033 [−0.052, 0.108] |

[v0.6 STAGE3_RESULTS; v0.7 RESULTS; v0.8 RESULTS §2.] The only apparent gain, on MDFlaker's
row-level split, was memorization (Section 4.3). In v0.6, a static-only model (smells, size and
context, without history or traceback) reached MCC 0.205, 0.329 below the KNN baseline [v0.6
STAGE3_RESULTS S4]. Static features describe the test, which is constant across its failures, and
not the failure. This contrasts with the test-level CANNIER setting, where the same features gave
small gains (Section 3.2).

---

## 9. Explanations (post hoc)

ET-BF was trained on the E1 training part (776 failures) and explained with `shap.TreeExplainer`
(shap 0.51.0) on the E1 test part (516) [v0.8 RESULTS §6.2, `robustness.json` R2]. On that part the
model has 129 true positives, 332 true negatives, 13 false positives and 42 false negatives. The base
value is P(flaky) = 0.307, and SHAP values sum to the predicted probability (maximum error < 1e-13).

**Global ranking** (mean |SHAP|, change in P(flaky)):

| Rank | Original history | | Strict history | |
|---:|---|---:|---|---:|
| 1 | `flaky_frequency` | 0.090 | `own_test_file_changed` | 0.076 |
| 2 | `last_frame_in_test_file` | 0.068 | `last_frame_in_test_file` | 0.074 |
| 3 | `own_test_file_changed` | 0.060 | `traceback_frames` | 0.036 |
| 4 | `traceback_frames` | 0.036 | `flaky_frequency` (strict) | 0.031 |
| 5 | `job_duration_s` | 0.031 | `frames_outside_repo` | 0.030 |
| 6 | `frames_outside_repo` | 0.031 | `same_file_cofailures` | 0.030 |

[`robustness.json` R2_shap_E1.] Of MDFlaker's own factors other than flaky frequency, none is in the
top 6; `traceback_coverage` is 21st of 22 under both variants (0.0035 and 0.0033).

**Local examples** (original history; the most confident case of each kind) [v0.8 RESULTS §6.2]:

| Case | Test | P(flaky) | Largest contributions |
|---|---|---:|---|
| True positive | hypothesis `test_observability.py::test_assume_has_status_reason` | 1.00 | `last_frame_in_test_file` = 1: +0.25; `flaky_frequency` = 0.51: +0.19; `job_duration_s` = 3618: +0.11 |
| True negative | prefect `test_schedules.py::…::test_rrule_schedule_preserves_and_localizes_rdates` | 0.00 | `own_test_file_changed` = 1: −0.08; `same_file_cofailures` = 4: −0.07; `last_frame_in_test_file` = 0: −0.05 |
| False positive | hypothesis `test_exceptiongroup.py::test_discard_multiple_frozen` | 0.86 | `last_frame_in_test_file` = 1: +0.27; `flaky_frequency` = 0.50: +0.17; `same_file_cofailures` = 1: −0.07 |

**Reading.** The model's view of a real regression is intuitive: the test's own file changed and
several tests in the same file failed together. A failure whose innermost frame is in the test file
pushes towards flaky; the false positive has the same profile as the hypothesis true positive, which
suggests the model partly learns hypothesis-specific failure shapes. SHAP explains what the model
uses, not what causes flakiness, and the explanations were not validated with developers.

---

## 10. Threats to validity

**Construct validity.**
- *Label noise.* Reruns ran on GitHub-hosted runners matched by OS family and Python minor version,
  not on the original machines. Some environment-dependent failures may be mislabelled, in either
  direction. MDFlaker's labels share this limitation.
- *Label definition.* "Not flaky" means 30 of 30 reruns failed; a rarely passing failure can be
  labelled not flaky. "Flaky" includes failures that pass on a rerun for environmental reasons.
- *Unlabelled candidates.* 367 of 1,659 (22%) are unlabelled. Exclusions are objective and recorded,
  but they are unevenly spread (for example 79 conan environment-check failures, 38 Cirq setup
  failures), so the labelled set may not represent each project's failures.
- *Our reimplementation of MDFlaker.* Our implementation check on the released data failed (74.6%
  agreement, Section 4.1), and the paper reports no comparable metrics. All comparisons are against
  our reimplementation of the described method.

**Internal validity.**
- *Post-hoc analyses.* The unseen-tests subset, the strict-history feature and the SHAP analysis were
  all defined after the frozen results were known. Our main claim therefore rests on a post-hoc
  analysis; v0.9 tests it prospectively.
- *History window.* Test history comes from a 90-day window, and only from runs whose logs list
  outcomes; failures early in the window have less history.
- *Same-run leakage.* Section 7.5 removes the sibling-job leak we found in `flaky_frequency`; we
  have not audited every F feature for similar timing issues [see open questions].

**External validity.**
- 8 Python projects on GitHub Actions in one 90-day window; hypothesis dominates the flaky class
  (161 of 409).
- Results with 8 projects have wide project-bootstrap intervals; some projects have very few test
  failures in E1.
- Only pytest projects; the feature extractors assume pytest log formats.

**Conclusion validity.**
- MCC values near 0 are unstable on small subsets; several per-project MCCs rest on fewer than 10
  flaky failures.
- Two bootstrap computations for the unseen-tests difference give slightly different intervals
  (diagnostics [0.22, 1.07]; robustness [0.25, 1.04]); we report the robustness numbers in the strict
  comparison.

---

## 11. Confirmation study (v0.9) — planned, results TBD

**Status: frozen 20 October 2026 at 14:48:22 UTC** (approved by Nandini Patil for the team; commit
`e02e3a7`; protocol SHA-256 `80004e48…a5b2`; harness commit `f28849b`) [v0.9 PROTOCOL,
`protocol.json`]. No v0.9 data have been collected or looked at.

**Purpose.** Test the within-project finding of Section 8.1 prospectively, on CI failures that
occur only after the freeze, with models trained only on v0.8 data and every choice fixed in
advance.

**Design.**
- **Projects:** the same 8 projects; no additions or replacements.
- **Window:** workflow runs created after the freeze and up to **T1 = 24 November 2026**,
  collected once at T1. If fewer than 300 primary-set candidates exist (a label-blind count), the
  window is extended once to **T2 = 22 December 2026**.
- **Sampling:** as in v0.8 (isolated failures in full, 1 per mass-failure job, seed 20261020), with
  at most 300 candidates per project.
- **Labels:** 30 reruns with the v0.8 harness and amendments B1–B3.
- **Features and models:** B + F with `flaky_frequency_strict`. Every model is trained once on all
  1,292 v0.8 labelled failures and applied unchanged. ET-BF is
  `ExtraTreesClassifier(n_estimators=100, random_state=20261020)`, flaky if P ≥ 0.5.
- **Comparators:** MDF-paper-int, MDF-paper-float, KNN8-int, KNN8-float and a per-project prior
  (each project's v0.8 majority class). ET-B and ET-BFC are reported but not compared in the rule.
- **Primary set (P):** labelled v0.9 failures whose test does **not** occur among the v0.8 labelled
  failures. **All (A):** every labelled v0.9 failure.

**Success rule.** Let C\* be the comparator with the highest MCC on P (chosen after seeing v0.9,
which is deliberately conservative).
- **Minimum sample:** P has at least 40 flaky and 40 not-flaky failures from at least 4 projects;
  otherwise results are descriptive only.
- **Confirmation:** MCC(ET-BF) − MCC(C\*) on P is **≥ +0.10**, with the lower bound of its 95%
  project-bootstrap interval (2,000 resamples) **> 0**.
- **Not claimed:** leave-one-project-out and ET-BFC vs ET-BF are descriptive only.
- If the rule is not met, this paper will report the v0.8 within-project result as **not
  confirmed**. Results are published whether or not the rule is met.

**Results: TBD after collection on 24 November 2026.**

| | n | Flaky | ET-BF MCC | C\* | C\* MCC | Δ [95% CI] | Met |
|---|---:|---:|---:|---|---:|---|---|
| Primary set P | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| All A (supporting) | TBD | TBD | TBD | TBD | TBD | TBD | — |

---

## 12. Conclusion

MDFlaker's released data cannot support an improvement claim: they contain a traceback-availability
label proxy, build fingerprints and heavy test repetition, and across its two usable projects
MDFlaker's simple rule beats every learned model we tried. On 1,292 newly collected, rerun-labelled
GitHub Actions failures from 8 Python projects, adding failure-evidence features to MDFlaker's
factors met a success rule frozen before labelling. Post-hoc checks narrow what can be claimed. The
gain that survives a prediction-time-safe history feature is within-project: on failures of tests
never seen in training, ET-BF reaches MCC 0.469 against −0.160 for our reimplementation of MDFlaker.
The cross-project gain does not survive. Static test-code context does not help on this
failure-level task in any of our experiments. The most useful signals are about the failure itself:
whether the test's own file changed, where the traceback ends, and what else failed alongside it.
Whether the within-project result holds on future failures is the question of the frozen v0.9 study,
to be reported after 24 November 2026.

**Data and artifacts.** Protocols, amendments, results and scripts are in the repository. The label
file (`local-evidence/mdflaker-fresh-v0.8/labels.csv`, SHA-256 `3d856bde…b4c2`) is not yet
committed [see open questions].

---

## Open questions for the team

1. **Venue and framing.** Is a Software Impacts tool paper acceptable to the guide as the Q3 base
   paper (v0.6 BASE_PAPER_SEARCH risk 1)? Which target journal, and what length and template?
2. **Main result is post hoc.** Are we comfortable submitting before v0.9 results exist
   (after 24 November 2026, possibly 22 December), or should submission wait? If v0.9 fails, the
   paper becomes mainly a dataset-and-negative-results paper; do we want a framing that works either
   way?
3. **APSEC 2021 paper.** We have not read it. Can someone with library access get it, check whether
   it reports precision/recall/F1, and confirm the factor definitions? `RESULTS.md` §4 says "the F1
   values in the MDFlaker paper", while `published_reference.json` says the Software Impacts article
   reports none; this sentence needs fixing.
4. **Missing statistics.** No bootstrap interval exists for ET-BF − MDFlaker on unseen tests under
   strict history, or for strict ET-BF against the project prior (0.52) in E1. Should we compute
   these (post hoc) before submission?
5. **Two intervals for one difference.** The unseen-tests ET-BF − KNN8 (original) interval is
   [0.22, 1.07] in `diagnostics.json` and [0.25, 1.04] in `robustness.json`. Which do we report, and
   should both scripts share a bootstrap seed?
6. **Timing audit of F.** Strict history fixed `flaky_frequency`. Do any F features (for example
   `build_failed_tests` or `same_file_cofailures`) also depend on information that is only complete
   after sibling jobs finish? This should be checked before v0.9 results, without changing v0.9.
7. **Hypothesis dominance.** ET-BF is −0.07 on hypothesis. Should we report a results table without
   hypothesis (post hoc), or per-project tables only?
8. **Data release.** May we commit or archive `labels.csv` and the candidate list (licensing of CI
   logs, project consent)? This affects the reproducibility statement.
9. **Citations.** Full references are needed for iDFlakies, FLAST, Afeltra et al., Pontillo et al.,
   the Ahmad et al. IEEE Access papers, Elgazzar et al., SHAP, Extra Trees, and a flaky-test survey;
   FlakeFlagger and Flakify are not in the repository at all.
10. **v0.9 PROTOCOL.md header.** The file still reads "DRAFT … awaiting team approval", although
    `protocol.json` records it as frozen and approved. Editing it would change its SHA-256. Should we
    add a separate note instead?
11. **Title and contribution order.** Lead with the dataset and evaluation lessons, or with the
    within-project improvement?
