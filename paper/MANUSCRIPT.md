# Is This CI Failure Flaky? Revisiting MDFlaker on Fresh, Rerun-Labelled Failures

Nandini Patil, Bhumika Mane, Trusha Kulkarni, Pranavi Baad

[TEAM: affiliations, corresponding author and e-mail; author order]

---

## Highlights

- MDFlaker's released data contain a label proxy and test and build shortcuts
- New dataset: 1,659 CI failures from 8 Python projects, labelled by 30 reruns
- Post hoc, on unseen tests: MCC 0.469 vs −0.160 for our MDFlaker reimplementation
- Margin over a per-project base-rate predictor is not significant
- Cross-project gain fails strict history; static test-code features never help

[PENDING v0.9: replace the fourth highlight with the matching variant prepared before collection.]

## Abstract

MDFlaker predicts whether a failed continuous integration (CI) test execution is flaky, that is, whether it would pass on a rerun. It uses five factors and a rule combined with a k-nearest-neighbour classifier. We first show that MDFlaker's released data cannot support a fair improvement claim. Whether a traceback was stored is close to a label proxy, and repeated tests and builds make within-project evaluations optimistic. We therefore collect 1,659 failed pytest executions from the GitHub Actions logs of 8 Python projects and rerun each 30 times on the code that CI tested. 1,292 receive labels: 409 flaky and 883 not flaky. We add 17 failure-evidence features to MDFlaker's factors and train an Extra Trees model (ET-BF). Under a success rule frozen before labelling, ET-BF beats the best MDFlaker-style baseline within projects (MCC 0.755 vs 0.239) and across projects (0.357 vs −0.014). Post-hoc checks show that these numbers are inflated by project base rates, repeated tests and a history feature that counts concurrent jobs. With a strict history feature and only on tests unseen in training, ET-BF reaches MCC 0.469 against −0.160 for our MDFlaker reimplementation (difference +0.63, 95% interval [0.14, 0.94]). Its margin over a per-project base-rate predictor, however, is not significant (+0.32 [−0.29, 0.61]). The cross-project gain does not survive strict history, and static test-code features never help. [PENDING v0.9: one sentence reporting the frozen prospective confirmation.]

**Keywords:** Flaky tests; Continuous integration; Failure triage; Test reruns; Machine learning; Empirical evaluation

---

## 1. Introduction

A flaky test passes or fails without any change to the code under test [1]. In continuous integration (CI), every failed test raises a triage question: is this a regression to investigate, or a flaky failure that would pass if the job were rerun? Rerunning every failure is costly. Developers restart at least 1.72% of builds on Travis CI, and restarts triple the median pull-request merge time [2]. Investigating a failure by hand costs far more than rerunning it [3]. Ignoring failures, on the other hand, hides real bugs: tests that are flaky at some point reveal more than a third of all regression faults in Chromium [4]. A classifier that predicts, for one failed execution, whether it is flaky can rank failures for rerunning or for investigation.

Most flaky-test predictors work at the level of tests: they ask whether a test is flaky, usually from its source code [5, 6, 7, 8, 9]. Haben et al. argue that this is the wrong unit, because the same test can fail flakily in one release and for real in another; prediction should target executions instead [4]. MDFlaker [10, 11] is one of the few published classifiers that does this. Given one failed execution, it predicts whether the execution would pass in at least one of 30 reruns. It uses five factors (traceback coverage of the change, flakiness frequency, test smells, previous state and test size) and a conditional rule with a k-nearest-neighbour (KNN) classifier. Its authors released 2,151 labelled failures from three Python projects.

This paper began as an attempt to improve on MDFlaker using its own released data. The attempt failed in an informative way. The data contain shortcuts that let a model look much better than it is, and once those shortcuts are removed, MDFlaker's simple rule generalizes across projects better than any learned model we tried. We therefore collected new failures and designed an evaluation that avoids those shortcuts. We fixed the success rule before any failure was labelled, and we report the frozen-rule results first. We then report post-hoc checks that narrow the claim to what survives.

We address the following research questions:

- **RQ1.** Can MDFlaker's released data support a fair improvement claim?
- **RQ2.** On freshly collected, rerun-labelled CI failures, do failure-evidence features improve on MDFlaker's classifiers under a success rule frozen in advance?
- **RQ3.** How much of that improvement survives controls for project base rates, test memorization, prediction-time history and same-run leakage?
- **RQ4.** Does adding static test-code context help?
- **RQ5.** What does the model rely on?

**Contributions.**

1. A re-examination of MDFlaker's released data. It reveals a traceback-availability label proxy, build fingerprints and heavy test repetition, and it shows how each one inflates evaluation (Section 3).
2. A new failure-level dataset: 1,659 GitHub Actions failures from 8 Python projects, labelled by 30 reruns on the code that CI tested, with every exclusion reported (Section 4).
3. A comparison under a success rule frozen before labelling, followed by clearly separated post-hoc checks (Sections 6 and 7). The improvement that survives is a within-project one, on tests not seen in training.
4. Two negative results: the cross-project gain disappears when history is restricted to information available at prediction time, and static test-code context never helps on this task (Section 7).
5. A prospective confirmation, frozen before its data exist, on failures that occur after the freeze (Section 8).

Section 2 reviews related work. Sections 3 to 8 answer the research questions. Section 9 discusses implications, Section 10 threats to validity, and Section 11 concludes.

---

## 2. Background and related work

### 2.1 Observing flakiness by rerunning

The standard way to observe flakiness is to rerun tests. iDFlakies [12] reruns test suites in the original order and in modified orders, and it separates order-dependent from non-order-dependent flaky tests. Rerun-based labels have known limits. Lam et al. reran Java test suites 4,000 times and found flaky tests whose failure rates differ greatly between test orders [13]. For Python, Gruber et al. estimate that 170 reruns are needed on average for 95% confidence that a passing test is not flaky [14]. Like MDFlaker, we label a failure flaky if at least one of 30 reruns passes. A failure that fails all 30 reruns is therefore "not observed flaky after 30 reruns", not proven non-flaky.

### 2.2 Combining reruns and prediction

CANNIER [15] combines rerunning with machine-learning models: predictions decide which tests to rerun, which reduces the cost of detection. Rerun costs vary by setting. In one industrial case study, an automatic rerun cost about $0.0002 and a manual investigation about $5 [3]. There, a classifier's value lies mainly in triage and explanation rather than in saving machine time.

### 2.3 MDFlaker

MDFlaker [10] is described in a short tool paper; its method and evaluation come from an earlier conference paper [11]. For each failed execution it computes five factors:
- **traceback coverage:** whether the failure's traceback covers the recent code changes;
- **flaky frequency:** the test's past flakiness in build history;
- **test smells:** counted with rules from its released code;
- **previous state:** the outcome of the previous build;
- **test size.**

The classifier is conditional. If the previous build passed, the failure is flaky exactly when the traceback does *not* cover the recent changes. Otherwise a KNN classifier (k = 10, Manhattan distance) on integer-cast factors predicts flaky when P(flaky) > 0.7. The released evaluation script instead uses KNN with k = 8 on a single 80-row hold-out. The tool paper reports no precision, recall, F1 or accuracy; its only quantitative result is a set of detection counts without ground truth. We therefore compare against our reimplementation of the described method and never against reported numbers.

### 2.4 Test-level prediction

Most flaky-test prediction is test-level. FLAST [5] predicts flakiness from test-code similarity. Pontillo et al. [7] and Afeltra et al. [6] study static and cross-project prediction. FlakeFlagger [8] uses features of each test's behaviour, such as execution time and coverage. Flakify [9] fine-tunes a code language model on test source. Ahmad et al. compare languages and language models for this task [16, 17], and Dai et al. use a heterogeneous graph transformer on CI artifacts [18]. These methods describe the *test*, which stays the same across all of its failures; our static context features (Section 5) are of this kind.

### 2.5 Failure-level classification and triage

Several studies classify failures rather than tests. DeFlaker [19] marks a newly failing test as flaky when it executed none of the changed code, which needs coverage of each change. At Mozilla, classifiers on job telemetry, such as runtime, CPU load and platform, separate intermittent CI job failures from real ones [20]. Other methods use the failure text:
- brown-build detection compares a build log with logs of earlier false-positive builds [21];
- failure de-duplication, evaluated on 230,439 failure messages from 22 Java projects, works very well for some projects and not at all for others [22];
- An et al. match abstracted error messages and stack traces against past flaky symptoms at SAP HANA, with precision of at least 96% [23].

At Google, a model predicts whether a failed execution was a flake, so that the failure can be ignored [24]. History-based triage is the industrial counterpart of MDFlaker's flaky-frequency factor: Ericsson flags tests whose no-fault-found failure rate is unstable compared with the previous release [25], and Apple ranks tests by entropy- and flip-rate-based flakiness scores [26].

Flaky failures are also not independent of each other. Flaky failures often occur in clusters that share a root cause [27], and fixing a consistently failing test can remove failures in other tests [28]. This supports co-failure features. It also means that failures from the same CI run should be kept together when data are split; we check this in Section 7.3.

Other Q3/Q4-journal work on flaky tests addresses different problems: adaptive execution for Android [29], order-dependency detection in Jest [30], flakiness localization in web applications [31], and an industrial ML detector without public data [32].

**Gap.** To our knowledge, none of these studies evaluates failure-level classification on open data with both a strict, time-ordered history and project-separated transfer. [TEAM: this claim rests on the papers' abstracts; confirm it against the full texts of [20], [21], [22] and Leinen et al. (IEEE TSE, 2026, doi:10.1109/TSE.2026.3729363) before submission.]

---

## 3. Problems in MDFlaker's released data (RQ1)

We used the authors' release of 2,151 failed executions from spaCy (1,080), django-rest-framework (DRF; 536) and Superset (535). The label is the authors' 30-rerun label. We joined each row to its build commit and test source, and we reimplemented the classifier.

**Coverage and reproduction.** Superset could not be used: 81 of its 84 build commits are no longer retrievable from GitHub, probably because they were temporary pull-request merge commits. The study population therefore has two projects, spaCy and DRF: 1,616 rows, 1,033 of them flaky (63.9%). Only 142 of the tool's released decisions join uniquely to the dataset. On those, our reimplementation agrees with the recorded decision 74.6% of the time. The released decisions were produced at a different time from the released data, so the two cannot be reconciled exactly. All our comparisons are therefore against our reimplementation of the described method.

**A label proxy.** In spaCy, rows whose test has a stored traceback are 6.4% flaky (173 rows), while rows without one are 81.9% flaky (907 rows). Whether the authors' log parser stored a traceback is therefore close to a label proxy. A model given this indicator ranked it second in permutation importance (0.20), after MDFlaker's own traceback coverage (0.52). A deployed tool would not see the same availability pattern.

**Test memorization.** Only 448 distinct test names cover the 2,151 rows, so any per-test feature can act as a test identifier. Under the authors' row-level split, adding 66 static context features appears to help (Extra Trees MCC 0.905 vs 0.838). Under test-grouped cross-validation, the same features *reduce* MCC from 0.642 to 0.606 (Δ −0.036, 95% interval [−0.053, −0.019]).

**Build fingerprints.** Test-grouped folds still put other failures from the same build into training. With folds grouped by build instead, our failure-evidence features reduce MCC (Δ −0.034 [−0.039, −0.029]). Linking tests and builds places all of spaCy and 95% of DRF in one connected component, so no within-project split is free of both shortcuts.

**What survives.** Leave-one-project-out is the only evaluation free of both shortcuts. There, MDFlaker's conditional rule (MCC 0.442 when tested on spaCy, 0.824 on DRF) beats every learned model we tried. For example, Extra Trees on MDFlaker's factors scores 0.353 and 0.250, and with failure evidence added 0.275 and 0.093.

**Answer to RQ1.** No. With two usable projects, a near-proxy for the label and heavily linked tests and builds, the released data cannot support an honest improvement claim. These analyses were exploratory, on data we had already inspected. The lessons we carried forward were:
1. evaluate on newly collected failures;
2. cap failures from mass-failure jobs;
3. exclude traceback *availability* as a feature in advance;
4. report results on tests not seen in training.

---

## 4. A new dataset of rerun-labelled CI failures

### 4.1 Projects

Projects were selected by a rule fixed before collection, while no labels were known. Candidates were Python projects with public GitHub Actions CI that runs pytest and prints failed node IDs. MDFlaker's own projects came first in the preference order, followed by projects from our earlier pytest corpus. Each project needed at least 20 parseable failed executions in the collection window, and at most 8 projects were taken. The resulting projects are django-rest-framework, urllib3, pytest, hypothesis, Cirq, conan, prefect and setuptools. spaCy had only one candidate. Two further projects fell below the threshold, and three qualified but fell outside the cap.

### 4.2 Collection

Through the GitHub REST API we collected workflow runs from the last 90 days (the log retention limit), their failed jobs and job logs. Logs were downloaded on 19 and 20 October 2026. We parsed each log into failed pytest node IDs, short tracebacks (file and line), the commit, the base commit, timestamps and the run attempt. The unit of analysis is one failed (test, commit, job) execution. All failures from jobs with at most 5 failed tests are included. From mass-failure jobs (more than 5 failed tests), one test per job is sampled with a fixed seed. In a 40-log probe, mass-failure jobs held about 11,400 of 11,657 failures, typically with one shared cause; uncapped, they would recreate the build-fingerprint shortcut of Section 3.

The frozen candidate list has 1,659 failed executions. Of these, 1,459 (88%) map to their test function's source and 761 have a parsed traceback.

### 4.3 Labels from 30 reruns

A failure is **flaky** if at least 1 of 30 reruns passes and **not flaky** if all 30 fail. Each candidate is rerun on GitHub Actions in a matching environment, with:
- the same OS family and runner generation;
- the same Python minor version, including PyPy and free-threaded builds where the original job used them;
- the project's own CI tooling (tox, nox, `uv sync` or requirements files);
- random test ordering disabled.

Three rules were fixed before any label existed:
1. **Rerun what CI tested.** For pull-request events, GitHub Actions tests a merge of the head into the base branch, not the head commit. We therefore rebuild that merge; 1,544 candidates are pull-request runs and 115 are push runs.
2. **Environment validity.** Before the rounds, each environment runs the candidates' test files once with every candidate deselected. It is valid only if at least 80% of the other tests pass, skip or xfail. Recipes were fixed in four check-only pilots, using setup and environment-check logs only.
3. **Collection check.** Candidates that pytest cannot collect are excluded before any round. A first full attempt was discarded unseen after two harness bugs were found.

### 4.4 Counts and exclusions

1,292 failures are labelled: 409 flaky and 883 not flaky. The 367 unlabelled failures are reported with their reasons (Table 1). Table 2 and Fig. 2 give the per-project counts. All 8 projects have both classes. Base rates differ widely, from 9.4% flaky in conan to 91.0% in hypothesis, which matters for evaluation (Section 7.2).

**Table 1.** Reasons for unlabelled candidates.

| Reason | Count |
|---|---:|
| Invalid node ID(s) in the rerun environment | 175 |
| Failed environment check | 86 |
| Setup failed | 38 |
| Mixed, skipped or missing outcomes | 35 |
| Cygwin environment (cannot be reproduced) | 18 |
| Incomplete rounds | 11 |
| No artifact | 4 |
| **Total** | **367** |

**Table 2.** Labelled failures per project.

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

[FIGURE 1 — fig1_pipeline]
**Fig. 1.** Study pipeline. Failed test executions from GitHub Actions logs give 1,659 candidates in 8 projects. Each is rerun 30 times on the code CI tested: 409 are flaky, 883 not flaky and 367 unlabelled with reported reasons. Feature sets B (MDFlaker's factors), F (failure evidence) and C (static test context) feed the compared models. Models are evaluated time-ordered within projects (E1), leave-one-project-out (E2) and on tests unseen in training. The unseen-test subset and the strict-history variant are post hoc.

[FIGURE 2 — fig2_projects]
**Fig. 2.** Labelled failures per project (light) and the flaky failures among them (dark), with counts and flaky rate.

---

## 5. Approach

### 5.1 Features

**B, MDFlaker's five factors**, reimplemented: flaky frequency, traceback coverage, test smells, previous state and test size. Test history comes from the same 90-day window, using runs whose logs list test outcomes.

**F, 17 failure-evidence features**, defined and frozen before extraction (Table 3). All are available when the failed job finishes. The traceback-availability indicator of Section 3 was excluded in advance.

**C, 66 static context features** describing the test's fixtures, helpers, lifecycle methods and class state, extracted from its source. They describe the test, not the failure.

**Table 3.** Failure-evidence features (F).

| Group | Features |
|---|---|
| Co-failures | failed tests in the job; other failed tests in the same file |
| Job | job duration; pull-request build |
| Change content | changed files; changed Python files; changed test files; non-Python-only change; changed lines; own test file changed; directory overlap between the test and the change; diff available |
| Traceback to change | traceback frames; frames in changed files; innermost frame in the test file; frames outside the repository; smallest line distance between a frame and a changed hunk |

### 5.2 Models

All configurations were fixed in advance (Table 4). Each forest is an Extra Trees classifier [33] with 100 trees, scikit-learn defaults, a 0.5 threshold and no class balancing. Class imbalance is left as observed, without oversampling. We include both integer and float versions of MDFlaker's factors because integer casting, as in the released code, truncates fractional flaky frequencies to 0. The comparator in each evaluation is therefore the stronger baseline variant, not a weakened one. Below, "MDFlaker" denotes MDF-paper-int and "KNN8" denotes KNN8-float.

**Table 4.** Compared models.

| Model | Features | Classifier |
|---|---|---|
| MDF-paper-int | B, integer-cast | MDFlaker's rule plus KNN (k = 10, Manhattan, P > 0.7), our reimplementation |
| MDF-paper-float | B, float | same |
| KNN8-int / KNN8-float | B | KNN (k = 8, Manhattan, majority vote), as in the released evaluation script |
| ET-B | B | Extra Trees |
| **ET-BF** (ours) | B + F | Extra Trees |
| ET-BFC | B + F + C | Extra Trees |

---

## 6. Evaluation design

### 6.1 Evaluations

- **E1, time-ordered within project (primary).** In each project, models train on the earliest 60% of failures by time and are tested on the latest 40%; predictions are pooled across projects. Training has 776 failures; test has 516, of which 171 are flaky.
- **E2, leave-one-project-out (primary).** Models train on 7 projects and are tested on the 8th; predictions are pooled over all 1,292 failures.
- **E3, external transfer (secondary).** Models train on MDFlaker's released 1,616 spaCy and DRF rows and are tested on all 1,292 fresh failures.

### 6.2 Metric and inference

The main metric is the Matthews correlation coefficient (MCC). It stays informative under class imbalance and is 0 for a constant or random predictor. We also report F1, precision and recall. Differences in MCC come with 95% project-bootstrap intervals: 2,000 resamples of projects, with predictions held fixed. With 8 projects these intervals are wide, and their bounds vary by a few hundredths between bootstrap draws.

### 6.3 The frozen success rule

Before any failure was rerun or labelled, we fixed the following rule:
- **Comparator:** in each evaluation, the best of the four MDFlaker-style baselines, chosen on baseline results only.
- **Headline:** ET-BF must beat the comparator by MCC ≥ +0.05 in **both** E1 and E2, with project-bootstrap intervals excluding 0. In addition, ET-BF must beat ET-B by at least +0.02 in E1.
- **Context claim:** ET-BFC − ET-BF ≥ +0.02 in E1, and ≥ 0 in E2.

### 6.4 Post-hoc checks

The following checks were defined after the frozen results were known, and we label them post hoc throughout:
- **Base-rate baseline:** a project prior that predicts each project's majority class in training.
- **Unseen-tests subset:** the E1 test failures whose test does not occur in training. It has 321 failures (91 flaky) in all 8 projects.
- **Strict history:** a history feature restricted to information available at prediction time (Section 7.2).
- **Same-run check:** whether the E1 split separates failures from the same CI run (Section 7.3).
- **SHAP explanations** (Section 7.5).

The prospective study in Section 8 adopts the unseen-tests subset and strict history *in advance*.

---

## 7. Results

### 7.1 Frozen-rule results (RQ2)

Table 5 gives MCC for every model and evaluation. The comparator was KNN8-float in E1 and MDF-paper-float in E2.

**Table 5.** MCC under the frozen rule, pooled over test parts.

| Model | E1 time-ordered | E2 leave-one-project-out | E3 transfer |
|---|---:|---:|---:|
| MDF-paper-int | 0.033 | −0.054 | 0.156 |
| MDF-paper-float | 0.091 | −0.014 | — |
| KNN8-int | 0.180 | −0.095 | — |
| KNN8-float | 0.239 | −0.044 | 0.283 |
| ET-B | 0.569 | 0.346 | 0.264 |
| **ET-BF** | **0.755** | **0.357** | 0.173 |
| ET-BFC | 0.716 | 0.390 | 0.128 |

**Table 6.** Terms of the frozen success rule.

| Rule term | Required | Observed | 95% interval | Met |
|---|---|---:|---|---|
| ET-BF − comparator, E1 | ≥ +0.05, interval > 0 | +0.516 | [0.216, 0.919] | yes |
| ET-BF − comparator, E2 | ≥ +0.05, interval > 0 | +0.370 | [0.031, 0.698] | yes |
| ET-BF − ET-B, E1 | ≥ +0.02 | +0.186 | [−0.028, 0.543] | yes |
| ET-BFC − ET-BF, E1 | ≥ +0.02 | −0.039 | [−0.134, 0.088] | no |
| ET-BFC − ET-BF, E2 | ≥ 0 | +0.033 | [−0.052, 0.108] | yes |

The headline was met and the context claim was not. In E1, ET-BF reached F1 0.82 (precision 0.91, recall 0.75); in E2 it reached F1 0.55. Two qualifications follow from the tables themselves:
- the ET-BF − ET-B term required only a point estimate, and its interval includes 0;
- in E2, ET-BF and ET-B are nearly equal (Δ +0.011 [−0.104, 0.167]), so the E2 margin comes from the classifier, not from the failure-evidence features.

All MDFlaker-style baselines score at or below 0 in E2, so the frozen E2 margin mostly reflects the baselines collapsing on unseen projects.

### 7.2 What survives the post-hoc checks (RQ3)

**Project base rates.** Predicting each project's training-majority class gives E1 MCC 0.52. ET-BF exceeds this by +0.24 [−0.01, 0.87]. Pooled E1 therefore rewards learning, for example, that hypothesis failures are mostly flaky. Within projects, ET-BF averages 0.56 MCC against 0.31 for ET-B. It scores −0.07 on hypothesis and between 0.37 and 0.96 on the other projects, several of which have very few flaky test failures in E1.

**Test memorization.** ET-BF scores 0.98 on the 195 E1 test failures whose test also occurs in training, and 0.57 on the 321 unseen ones.

**Same-run history.** As frozen, flaky frequency counts the test's failures up to the failure's timestamp. That includes sibling jobs of the same workflow run, which started at the same time but whose results exist only once those jobs finish. It is the top feature by permutation importance (0.24). We therefore define a strict variant that counts only failures in **earlier workflow runs**. It is 0 for 646 of the 1,292 rows. Its mean is 0.23 for flaky rows and 0.06 for not-flaky rows, compared with 0.33 and 0.12 for the original. MDFlaker's results do not change, because integer casting truncates both variants to 0.

**Traceback availability is not a proxy in the new data.** Its relation to the label changes sign between projects. In pytest, 71% of failures with a traceback are flaky against 3% without one; in Cirq, the figures are 6% and 22%. Dropping the traceback-frame count leaves E1 unchanged (0.755).

Table 7 gives the main result: strict history, within project.

**Table 7.** Strict history, within project (post hoc).

| Evaluation | Model | MCC | F1 | Precision | Recall |
|---|---|---:|---:|---:|---:|
| **Unseen tests** (n = 321, 91 flaky) | MDFlaker | −0.160 | 0.134 | 0.151 | 0.121 |
| | KNN8 | −0.128 | 0.101 | 0.146 | 0.077 |
| | **ET-BF** | **0.469** | **0.602** | **0.667** | **0.549** |
| **E1** (n = 516, 171 flaky) | MDFlaker | 0.033 | 0.325 | 0.357 | 0.298 |
| | KNN8 | 0.225 | 0.409 | 0.544 | 0.327 |
| | **ET-BF** | **0.679** | **0.779** | **0.819** | **0.743** |

**Table 8.** MCC differences under strict history, with 95% project-bootstrap intervals (post hoc).

| Subset | ET-BF − MDFlaker | ET-BF − KNN8 | ET-BF − project prior |
|---|---|---|---|
| Unseen tests | **+0.63 [0.14, 0.94]** | +0.60 [0.10, 0.85] | +0.32 [−0.29, 0.61] |
| E1 | +0.65 [0.38, 0.97] | +0.45 [0.17, 0.79] | +0.16 [−0.09, 0.71] |

The project prior scores 0.52 in E1 and 0.15 on unseen tests. Fig. 3 compares original and strict history across all evaluations.

[FIGURE 3 — fig3_mcc_original_vs_strict]
**Fig. 3.** MCC with the original history feature (open markers) and with strict history, which counts only earlier workflow runs (filled markers, post hoc), for MDFlaker, KNN8 and ET-BF on E1, E2 and unseen tests.

**Per project.** On unseen tests under strict history (Fig. 4), ET-BF beats MDFlaker in 5 projects, ties in 2 and loses in 1 (hypothesis: −0.828 vs −0.418, on 11 failures). Its per-project median is 0.25. Pooled MCC (0.469) is higher than most per-project values because it also rewards separating projects with different flaky rates; for example, 55 of prefect's 59 unseen failures are flaky. Scored without hypothesis, ET-BF reaches 0.521 on unseen tests (n = 310, 84 flaky) against −0.146 for MDFlaker, a difference of +0.67 [0.19, 0.99].

[FIGURE 4 — fig4_unseen_per_project]
**Fig. 4.** Per-project MCC on unseen tests under strict history (post hoc). Subsets are small (n and flaky counts shown), so single-project values are unstable; an MCC of 0 can mean that a model predicted only one class.

### 7.3 Same-run failures across the split (RQ3, post hoc)

Flaky failures from one CI run often share a cause [27], and a time-ordered split can place one run on both sides. In E1, six runs at the time boundary have failures in both training and test. The 50 test failures they share with training are all not flaky. We corrected for this in two ways: by dropping those failures, and by re-splitting with whole runs (or whole commits) kept on one side and refitting. Table 9 shows the result. ET-BF stays at 0.40–0.54 on unseen tests and ahead of MDFlaker in every variant, with intervals excluding 0. Its margin over the project prior stays non-significant. MDFlaker's E1 score rises from 0.03 to 0.13–0.16, because it had misclassified many of the shared failures.

**Table 9.** E1 with same-run failures removed or regrouped (strict history; post hoc).

| Variant | ET-BF, E1 | MDFlaker, E1 | ET-BF, unseen | MDFlaker, unseen | ET-BF − MDFlaker, unseen |
|---|---:|---:|---:|---:|---|
| As in Table 7 | 0.679 | 0.033 | 0.469 | −0.160 | +0.63 [0.14, 0.94] |
| Drop shared run | 0.663 | 0.133 | 0.464 | −0.134 | +0.60 [0.14, 0.86] |
| Regroup by run | 0.687 | 0.164 | 0.537 | −0.103 | +0.64 [0.17, 0.89] |
| Drop shared commit | 0.661 | 0.135 | 0.459 | −0.132 | +0.59 [0.14, 0.86] |
| Regroup by commit | 0.628 | 0.135 | 0.399 | −0.155 | +0.55 [0.15, 0.80] |

### 7.4 Cross-project and external transfer (RQ3)

**Cross-project.** With strict history, ET-BF's E2 MCC falls from 0.357 to 0.100 (F1 0.416). Its differences from KNN8 (+0.23 [−0.03, 0.48]) and from MDFlaker (+0.15 [−0.11, 0.45]) both have intervals that include 0. Much of the frozen cross-project signal came from same-run sibling failures, which a deployed tool would not have at prediction time. We therefore make no claim about unseen projects.

**External transfer.** Models trained on MDFlaker's 2020 Travis data transfer poorly to the fresh failures. The best is KNN8-float (MCC 0.283, F1 0.541); ET-BF reaches 0.173. This is consistent with Section 3: the old data reward dataset-specific shortcuts.

**Answer to RQ2 and RQ3.** The frozen rule was met. What survives the post-hoc checks is narrower:
- **What survives:** a within-project gain on tests unseen in training. ET-BF reaches MCC 0.469 there, against −0.160 for MDFlaker, and the gap holds after correcting for same-run leakage.
- **What does not survive:** a clear advantage over a per-project base-rate predictor, and the cross-project gain.

### 7.5 Static context features (RQ4)

Static test-code context never helped on this failure-level task (Table 10). The only apparent gain, under MDFlaker's row-level split, was memorization (Section 3). A static-only model on MDFlaker's data (test smells, test size and context, without history or traceback) reached MCC 0.205, 0.329 below the KNN baseline. Static features describe the test, which stays the same across its failures; they do not describe the failure.

**Table 10.** Effect of adding static context features (C).

| Data and evaluation | Comparison | ΔMCC [95% interval] |
|---|---|---|
| MDFlaker's data, test-grouped CV | ET-BC − ET-B | −0.036 [−0.053, −0.019] |
| MDFlaker's data, test-grouped CV | ET-BFC − ET-BF | −0.057 [−0.067, −0.047] |
| New data, E1 | ET-BFC − ET-BF | −0.039 [−0.134, 0.088] |
| New data, E2 | ET-BFC − ET-BF | +0.033 [−0.052, 0.108] |

**Answer to RQ4.** No.

### 7.6 What the model relies on (RQ5, post hoc)

We trained ET-BF on the E1 training part and explained it on the E1 test part with SHAP [34] using TreeExplainer [35]. On that part the model has 129 true positives, 332 true negatives, 13 false positives and 42 false negatives. The base value is P(flaky) = 0.307, and SHAP values sum to the predicted probability (maximum error < 1e-13).

With the original history feature, the top features by mean |SHAP| are flaky frequency (0.090), innermost frame in the test file (0.068), own test file changed (0.060), traceback frames (0.036), job duration (0.031) and frames outside the repository (0.031). With strict history, own test file changed (0.076) and innermost frame in the test file (0.074) lead, and flaky frequency falls to fourth (0.031) (Fig. 5). MDFlaker's traceback coverage ranks 21st of 22 in both cases.

[FIGURE 5 — fig5_shap_ranking]
**Fig. 5.** Global SHAP ranking (mean |SHAP|) of the 22 ET-BF features on the E1 test part, with original history and with strict history (post hoc).

**Table 11.** Local explanations: the most confident case of each kind (original history). Contributions are changes in P(flaky).

| Case | Test | P(flaky) | Largest contributions |
|---|---|---:|---|
| True positive | hypothesis `test_observability.py::test_assume_has_status_reason` | 1.00 | innermost frame in test file = 1: +0.25; flaky frequency = 0.51: +0.19; job duration = 3,618 s: +0.11 |
| True negative | prefect `test_schedules.py::…::test_rrule_schedule_preserves_and_localizes_rdates` | 0.00 | own test file changed = 1: −0.08; same-file co-failures = 4: −0.07; innermost frame in test file = 0: −0.05 |
| False positive | hypothesis `test_exceptiongroup.py::test_discard_multiple_frozen` | 0.86 | innermost frame in test file = 1: +0.27; flaky frequency = 0.50: +0.17; same-file co-failures = 1: −0.07 |

**Answer to RQ5.** The model relies mainly on evidence about the failure itself:
- whether the test's own file changed;
- where the traceback ends;
- what else failed alongside the test.

A real regression looks as expected: the test's own file changed and several tests in the same file failed together. The false positive has the same profile as the hypothesis true positive, which suggests that the model partly learns project-specific failure shapes. SHAP explains what the model uses, not what causes flakiness, and we have not validated these explanations with developers.

---

## 8. Prospective confirmation

The main result in Section 7 is post hoc. We therefore froze a confirmation study on 20 October 2026, before any of its data existed.

**Design.**
- **Projects:** the same 8 projects.
- **Window:** workflow runs created after the freeze, up to 24 November 2026, collected once. If fewer than 300 candidates for the primary set (defined below) exist, the window is extended once, to 22 December 2026; this decision uses label-blind counts only.
- **Sampling and labels:** as in Section 4, with at most 300 candidates per project.
- **Models:** strict-history features. Every model is trained once on all 1,292 labelled failures of Section 4 and applied unchanged. ET-BF uses a fixed random seed and a 0.5 threshold.
- **Comparators:** the four MDFlaker-style baselines and the per-project prior.
- **Primary set P:** labelled new failures whose test does not occur in the training data.

**Success rule.**
- **Comparator:** C\*, the comparator with the highest MCC on P, chosen after seeing the results (a deliberately conservative choice).
- **Minimum sample:** P must contain at least 40 flaky and 40 not-flaky failures from at least 4 projects; otherwise the results are descriptive only.
- **Confirmation:** MCC(ET-BF) − MCC(C\*) on P is at least +0.10, and the lower bound of its 95% project-bootstrap interval is above 0.
- **Descriptive only:** leave-one-project-out and the context comparison are reported without a claim.

The results are reported whatever the outcome. If the rule is not met, the within-project result of Section 7 is reported as not confirmed.

**Table 12.** Prospective confirmation results.

| Set | n | Flaky | ET-BF MCC | C\* | C\* MCC | Δ [95% interval] | Met |
|---|---:|---:|---:|---|---:|---|---|
| Primary set P | [PENDING] | [PENDING] | [PENDING] | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| All new failures | [PENDING] | [PENDING] | [PENDING] | [PENDING] | [PENDING] | [PENDING] | — |

[PENDING v0.9: results paragraph, using the variant for the observed outcome prepared before collection, plus per-project results.]

---

## 9. Discussion

**Implications for practitioners.** A failure-level classifier is most useful as a ranking and explanation aid inside one project, not as a model carried to a new project. The most informative signals are cheap to compute from the CI job itself:
- whether the failing test's own file changed;
- where the traceback ends;
- how many other tests failed in the same file.

History features help only if they count information that exists when the prediction is made. A rate that includes concurrent jobs of the same run looks predictive offline but is not available in practice. Because a per-project base rate already explains much of the pooled accuracy, a team adopting such a tool should check that it beats "always predict this project's usual outcome" on its own data.

**Implications for researchers.** Our results show how easily failure-level evaluations overstate performance:
- **Row-level splits:** these let per-test features act as identifiers (Section 3).
- **Test- and build-linked splits:** failures that share a test or a build leak information between training and test (Section 3).
- **Pooled MCC:** pooling across projects with different base rates rewards separating projects as well as discriminating within them (Section 7.2).
- **History features:** a feature computed "up to the failure's timestamp" can leak results from concurrent jobs (Section 7.2).

We recommend that failure-level studies:
1. collect fresh data;
2. compare against a per-project base-rate predictor;
3. report results on tests unseen in training and per project;
4. compute history from earlier runs only;
5. keep failures from one CI run together when splitting;
6. fix the success rule before labelling.

**Why within-project but not cross-project?** Flaky-failure patterns appear to be project-specific. Hypothesis failures are 91% flaky and conan failures 9%, and the false positive in Table 11 mirrors a project-specific true positive. Models trained on 7 projects carry over little of this once the same-run signal is removed. Larger and more varied training data, or per-project calibration, may change this; our data cannot tell.

---

## 10. Threats to validity

**Construct validity.**
- **Label noise.** Reruns ran on GitHub-hosted runners matched by OS family and Python minor version, not on the original machines. Some environment-dependent failures may be mislabelled, in either direction; MDFlaker's labels share this limitation.
- **Label definition.** "Not flaky" means that all 30 reruns failed, and rarely passing failures may be missed [14].
- **Exclusions.** 367 of 1,659 candidates (22%) are unlabelled. The exclusions are objective and recorded but unevenly spread, so the labelled set may not represent each project's failures equally.
- **Reimplementation.** Our check of the reimplementation against MDFlaker's released decisions reached 74.6% agreement, and the tool paper reports no comparable metrics. All comparisons are against our reimplementation.

**Internal validity.**
- **Post-hoc analyses.** The unseen-tests subset, strict history, the same-run check and SHAP were all defined after the frozen results were known. The prospective study tests the main finding without this freedom.
- **History window.** Test history comes from a 90-day window, so early failures have less history.
- **Timing gaps.** A review of the feature extraction found no timing leak in the failure-evidence features: job-log, traceback and change features are available when the job finishes. Two small gaps remain unmeasured:
  - previous state uses the final conclusion of the latest earlier run, which may still have been running;
  - strict history may count earlier runs that had not finished yet.
- **Sampling artifact.** The same-file co-failure count uses sampled candidates, so it is 0 for mass-failure jobs.

**External validity.** We studied 8 Python projects on GitHub Actions in one 90-day window, and hypothesis contributes 161 of the 409 flaky failures. All projects use pytest, and our parsers assume pytest log formats.

**Conclusion validity.** With 8 projects, project-bootstrap intervals are wide, and their bounds vary by a few hundredths between draws. Several per-project MCC values rest on fewer than 10 flaky failures, so we word every conclusion that depends on a bound near 0 cautiously.

---

## 11. Conclusion

MDFlaker's released data cannot support an improvement claim. They contain a traceback-availability label proxy, build fingerprints and heavy test repetition, and across the two usable projects MDFlaker's simple rule beats every learned model we tried. On 1,292 newly collected, rerun-labelled GitHub Actions failures from 8 Python projects, adding failure-evidence features to MDFlaker's factors met a success rule frozen before labelling. Post-hoc checks narrow what can be claimed. The gain that survives a strict history feature and same-run corrections is within-project: on failures of tests never seen in training, ET-BF reaches MCC 0.469 against −0.160 for our reimplementation of MDFlaker. Its margin over a per-project base-rate predictor is not significant, and the cross-project gain does not survive. Static test-code context does not help on this task. The most useful signals describe the failure itself: whether the test's own file changed, where the traceback ends, and what else failed alongside it. [PENDING v0.9: final sentence on the prospective confirmation.]

---

## CRediT authorship contribution statement

**Nandini Patil:** Data curation, Investigation, Methodology, Software, Validation, Visualization, Writing – original draft, Writing – review & editing. **Bhumika Mane:** Conceptualization, Investigation, Project administration, Software, Validation, Visualization, Writing – original draft, Writing – review & editing. **Trusha Kulkarni:** Data curation, Formal analysis, Investigation, Software, Validation, Visualization, Writing – original draft, Writing – review & editing. **Pranavi Baad:** Data curation, Formal analysis, Investigation, Methodology, Software, Visualization, Writing – original draft, Writing – review & editing.

## Declaration of competing interest

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper. [TEAM: every author to confirm.]

## Funding

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors. [TEAM: confirm.]

## Data availability

The derived data for the new dataset (candidate list, features, labels and rerun summaries), together with the protocols, analysis scripts and result files, will be archived at [Zenodo DOI]. The code is released under the MIT licence and the data under CC-BY-4.0. Raw CI logs are not redistributed; the archived run and job identifiers allow them to be retrieved while GitHub retains them. MDFlaker's released dataset is available from its authors' repository [10]. [TEAM: pending the guide's approval of the Zenodo release.]

## Declaration of generative AI and AI-assisted technologies in the writing process

During the preparation of this work the authors used Claude (Anthropic) in order to draft and edit the manuscript text. After using this tool, the authors reviewed and edited the content as needed and take full responsibility for the content of the published article. [TEAM: confirm after your own rewrite, and decide whether the methods should mention AI-assisted code.]

## Acknowledgements

[TEAM: project guide and institution.]

## References

[1] O. Parry, G. M. Kapfhammer, M. Hilton, P. McMinn, "A survey of flaky tests," *ACM Transactions on Software Engineering and Methodology*, vol. 31, no. 1, Art. 17, 2022. doi:10.1145/3476105.

[2] T. Durieux, C. Le Goues, M. Hilton, R. Abreu, "Empirical study of restarted and flaky builds on Travis CI," in *Proc. 17th Int. Conf. on Mining Software Repositories (MSR)*, 2020, pp. 254–264. doi:10.1145/3379597.3387460.

[3] F. Leinen, D. Elsner, A. Pretschner, A. Stahlbauer, M. Sailer, E. Jürgens, "Cost of flaky tests in continuous integration: An industrial case study," in *Proc. IEEE Conf. on Software Testing, Verification and Validation (ICST)*, 2024, pp. 329–340. doi:10.1109/ICST60714.2024.00037.

[4] G. Haben, S. Habchi, J. Micco, M. Harman, M. Papadakis, M. Cordy, Y. Le Traon, "The importance of accounting for execution failures when predicting test flakiness," in *Proc. 39th IEEE/ACM Int. Conf. on Automated Software Engineering (ASE)*, 2024, pp. 1979–1989. doi:10.1145/3691620.3695261.

[5] R. Verdecchia, E. Cruciani, B. Miranda, A. Bertolino, "Know you neighbor: Fast static prediction of test flakiness," *IEEE Access*, vol. 9, pp. 76119–76134, 2021. doi:10.1109/ACCESS.2021.3082424.

[6] A. Afeltra, A. Cannavale, F. Pecorelli, V. Pontillo, F. Palomba, "A large-scale empirical investigation into cross-project flaky test prediction," *IEEE Access*, vol. 12, pp. 131255–131265, 2024. doi:10.1109/ACCESS.2024.3458184.

[7] V. Pontillo, F. Palomba, F. Ferrucci, "Static test flakiness prediction: How far can we go?," *Empirical Software Engineering*, 2022. doi:10.1007/s10664-022-10227-1.

[8] A. Alshammari, C. Morris, M. Hilton, J. Bell, "FlakeFlagger: Predicting flakiness without rerunning tests," in *Proc. 43rd IEEE/ACM Int. Conf. on Software Engineering (ICSE)*, 2021, pp. 1572–1584. doi:10.1109/ICSE43902.2021.00140.

[9] S. Fatima, T. A. Ghaleb, L. Briand, "Flakify: A black-box, language model-based predictor for flaky tests," *IEEE Transactions on Software Engineering*, vol. 49, no. 4, pp. 1912–1927, 2023. doi:10.1109/TSE.2022.3201209.

[10] A. Ahmad, "MDFlaker: A tool for multi-factor detection and root cause analysis of flaky tests," *Software Impacts*, vol. 26, 100794, 2025. doi:10.1016/j.simpa.2025.100794.

[11] A. Ahmad, F. Gomes de Oliveira Neto, Z. Shi, K. Sandahl, O. Leifler, "A multi-factor approach for flaky test detection and automated root cause analysis," in *Proc. 28th Asia-Pacific Software Engineering Conference (APSEC)*, 2021, pp. 338–348. doi:10.1109/APSEC53868.2021.00041.

[12] W. Lam, R. Oei, A. Shi, D. Marinov, T. Xie, "iDFlakies: A framework for detecting and partially classifying flaky tests," in *Proc. 12th IEEE Conf. on Software Testing, Validation and Verification (ICST)*, 2019, pp. 312–322. doi:10.1109/ICST.2019.00038.

[13] W. Lam, S. Winter, A. Astorga, V. Stodden, D. Marinov, "Understanding reproducibility and characteristics of flaky tests through test reruns in Java projects," in *Proc. IEEE 31st Int. Symp. on Software Reliability Engineering (ISSRE)*, 2020, pp. 403–413. doi:10.1109/ISSRE5003.2020.00045.

[14] M. Gruber, S. Lukasczyk, F. Krois, G. Fraser, "An empirical study of flaky tests in Python," in *Proc. 14th IEEE Conf. on Software Testing, Verification and Validation (ICST)*, 2021, pp. 148–158. doi:10.1109/ICST49551.2021.00026.

[15] O. Parry, G. M. Kapfhammer, M. Hilton, P. McMinn, "Empirically evaluating flaky test detection techniques combining test case rerunning and machine learning models," *Empirical Software Engineering*, vol. 28, 2023. doi:10.1007/s10664-023-10307-w.

[16] A. Ahmad, X. Sun, M. R. Naeem, Y. Javed, M. Akour, K. Sandahl, "Understanding flaky tests through linguistic diversity: A cross-language and comparative machine learning study," *IEEE Access*, vol. 13, pp. 54561–54584, 2025. doi:10.1109/ACCESS.2025.3553626.

[17] A. Ahmad, X. Sun, "Base, instruct, and fine-tune: Evaluating LLMs for cross-language flaky test detection," *IEEE Access*, vol. 13, pp. 205254–205277, 2025. doi:10.1109/ACCESS.2025.3639645.

[18] P. Dai, X. Ma, Y. Zhao, Y. Gong, "Heterogeneous graph transformer with multi-view representation learning for flaky test detection," *Computers*, vol. 15, no. 6, Art. 372, 2026. doi:10.3390/computers15060372.

[19] J. Bell, O. Legunsen, M. Hilton, L. Eloussi, T. Yung, D. Marinov, "DeFlaker: Automatically detecting flaky tests," in *Proc. 40th Int. Conf. on Software Engineering (ICSE)*, 2018, pp. 433–444. doi:10.1145/3180155.3180164.

[20] J. Lampel, S. Just, S. Apel, A. Zeller, "When life gives you oranges: Detecting and diagnosing intermittent job failures at Mozilla," in *Proc. 29th ACM Joint European Software Engineering Conf. and Symp. on the Foundations of Software Engineering (ESEC/FSE)*, 2021, pp. 1381–1392. doi:10.1145/3468264.3473931.

[21] D. Olewicki, M. Nayrolles, B. Adams, "Towards language-independent brown build detection," in *Proc. 44th Int. Conf. on Software Engineering (ICSE)*, 2022, pp. 2177–2188. doi:10.1145/3510003.3510122.

[22] A. Alshammari, P. Ammann, M. Hilton, J. Bell, "230,439 test failures later: An empirical evaluation of flaky failure classifiers," in *Proc. IEEE Conf. on Software Testing, Verification and Validation (ICST)*, 2024, pp. 257–268. doi:10.1109/ICST60714.2024.00031.

[23] G. An, J. Yoon, T. Bach, J. Hong, S. Yoo, "Just-in-time flaky test detection via abstracted failure symptom matching," in *Proc. IEEE Int. Conf. on Software Maintenance and Evolution (ICSME)*, 2024, pp. 741–752. doi:10.1109/ICSME58944.2024.00078.

[24] M. Hoang, A. Berding, "Presubmit Rescue: Automatically ignoring flaky test executions," in *Proc. 1st Int. Workshop on Flaky Tests (FTW)*, 2024, pp. 1–2. doi:10.1145/3643656.3643896.

[25] M. H. U. Rehman, P. C. Rigby, "Quantifying no-fault-found test failures to prioritize inspection of flaky tests at Ericsson," in *Proc. 29th ACM Joint European Software Engineering Conf. and Symp. on the Foundations of Software Engineering (ESEC/FSE)*, 2021, pp. 1371–1380. doi:10.1145/3468264.3473930.

[26] E. Kowalczyk, K. Nair, Z. Gao, L. Silberstein, T. Long, A. Memon, "Modeling and ranking flaky tests at Apple," in *Proc. ACM/IEEE 42nd Int. Conf. on Software Engineering: Software Engineering in Practice (ICSE-SEIP)*, 2020, pp. 110–119. doi:10.1145/3377813.3381370.

[27] O. Parry, G. M. Kapfhammer, M. Hilton, P. McMinn, "Systemic flakiness: An empirical analysis of co-occurring flaky test failures," in *Proc. 29th Int. Conf. on Evaluation and Assessment in Software Engineering (EASE)*, 2025, pp. 476–487. doi:10.1145/3756681.3756945.

[28] P. E. Strandberg, T. J. Ostrand, E. J. Weyuker, W. Afzal, D. Sundmark, "Intermittently failing tests in the embedded systems domain," in *Proc. 29th ACM SIGSOFT Int. Symp. on Software Testing and Analysis (ISSTA)*, 2020, pp. 337–348. doi:10.1145/3395363.3397359.

[29] W. Zhang, W. Wang, R. Zhao, "Flaky test detection based on adaptive latest position execution for concurrent Android applications," *Int. J. Software Engineering and Knowledge Engineering*, vol. 34, no. 8, pp. 1313–1338, 2024. doi:10.1142/S0218194024500232.

[30] N. Hashemi, A. Tahir, S. Rasheed, A. Shi, R. Blagojevic, "JS-TOD: Detecting order-dependent flaky tests in Jest," *Science of Computer Programming*, vol. 252, Art. 103462, 2026. doi:10.1016/j.scico.2026.103462.

[31] J. Morán, C. Augusto, A. Bertolino, C. De La Riva, J. Tuya, "FlakyLoc: Flakiness localization for reliable test suites in web applications," *Journal of Web Engineering*, vol. 19, no. 2, pp. 267–296, 2020. doi:10.13052/jwe1540-9589.1927.

[32] M. ElGazzar, E. Hossny, F. A. Omara, "A machine learning-based detection of test automation flakiness," in *Intelligent Systems, Blockchain, and Communication Technologies*, Lecture Notes in Networks and Systems, vol. 1801, Springer, Cham, 2026, pp. 91–102. doi:10.1007/978-3-032-15784-3_8. [CITE NEEDED: book editors and conference name.]

[33] P. Geurts, D. Ernst, L. Wehenkel, "Extremely randomized trees," *Machine Learning*, vol. 63, pp. 3–42, 2006. doi:10.1007/s10994-006-6226-1.

[34] S. M. Lundberg, S.-I. Lee, "A unified approach to interpreting model predictions," in *Advances in Neural Information Processing Systems 30 (NIPS)*, 2017, pp. 4765–4774.

[35] S. M. Lundberg, G. Erion, H. Chen, et al., "From local explanations to global understanding with explainable AI for trees," *Nature Machine Intelligence*, vol. 2, pp. 56–67, 2020. doi:10.1038/s42256-019-0138-9.
