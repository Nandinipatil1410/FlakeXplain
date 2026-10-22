# FlakeXplain vs MDFlaker: element-by-element comparison

Prepared 22 October 2026 from a full reading of both MDFlaker papers:

- **[SI]** A. Ahmad, "MDFlaker: A tool for multi-factor detection and root cause analysis of flaky
  tests," *Software Impacts* 26 (2025) 100794. 4 pages. Our base paper (Q3).
- **[APSEC]** A. Ahmad, F. Gomes de Oliveira Neto, Z. Shi, K. Sandahl, O. Leifler, "A multi-factor
  approach for flaky test detection and automated root cause analysis," APSEC 2021, pp. 338–348.
  11 pages. The method and the only evaluation are here.

Our numbers come from `reports/mdflaker-fresh-v0.8/RESULTS.md`, `paper/MANUSCRIPT.md` and
`reports/llm-codebert-v0.10/RESULTS.md`. MCC and F1 for APSEC are computed by us from the confusion
counts in APSEC Table III; the paper itself reports accuracy, precision and recall only.

## 1. Corrections needed in our manuscript

| # | Manuscript now says | Both papers say | Fix |
|---|---|---|---|
| 1 | MDFlaker "uses five factors" (incl. previous state) | **Four factors**: trace-back coverage, flaky frequency, test smells, test size. [SI] §2.3 uses the previous build state only to **switch** between a trace-back rule (Scenario 1) and multi-factor KNN (Scenario 2). [APSEC] has no previous-state rule at all. | "Four factors, plus the previous build state, which [SI] uses to choose between a trace-back rule and KNN." Our B set keeps previous state as an input because the rule needs it; say so. |
| 2 | Conditional rule with KNN (k = 10, Manhattan) and P > 0.7, presented as "described" | [APSEC] §IV-C, §V-A: KNN, Manhattan distance, **k = factors + 1 = 5, majority vote**, no conditional rule. k = 10 and P > 0.7 are in the authors' released tool code (`mysql_handler.py`); k = 8 is in their released `evaluate.py`. | State the source of each setting: rule from [SI] §2.3; k = 10 / P > 0.7 from the released tool; k = 8 from the released evaluation script; k = 5 from [APSEC]. Add a k = 5 baseline (section 5). |
| 3 | Authors "released 2,151 labelled failures" | [APSEC] Table II: **2,166** failures (212 versions), 1,372 flaky and 794 not (63%). | Keep 2,151 for the release, add: "the paper reports 2,166; the release has 2,151." |
| 4 | — | [SI] cites [APSEC] as "ICSE 2022". The PDF's own header says APSEC 2021, DOI 10.1109/APSEC53868.2021.00041. | Keep our APSEC citation (already Crossref-verified). Optionally note the SI mis-citation. |
| 5 | Comparison "never against reported numbers" because none exist | True for [SI]. [APSEC] **does** report accuracy, precision and recall (Tables III–IV). | Add their reported numbers next to ours with the caveats in section 4, instead of saying none exist. |

Flaky frequency is **correct as implemented**: our `flaky_frequency` is [APSEC] equation 1,
transitions ÷ (failures + 2), with failures close in time counted as one transition (the released
code uses an 8-hour gap; the paper says "a short period").

## 2. Method side by side

| Aspect | MDFlaker [APSEC]/[SI] | FlakeXplain (ours) | What is new |
|---|---|---|---|
| Unit of prediction | Failed test execution | Failed test execution | Same unit, so the comparison is like for like |
| CI source | Travis CI logs + GitHub commits | GitHub Actions logs + GitHub API | Current CI system (Travis data is no longer collectable) |
| Projects | spaCy, DRF, Superset (3) | DRF, urllib3, pytest, hypothesis, Cirq, conan, prefect, setuptools (8) | More projects; selection rule fixed before labelling; MDFlaker's projects tried first (spaCy had 1 candidate, Superset's commits are gone) |
| Failures | 2,166 (63% flaky) | 1,659 candidates, 1,292 labelled (32% flaky) | Realistic flaky share; mass-failure jobs capped |
| Ground truth | Whole build rerun 30× locally, **tests in random orders** | Each failure rerun 30× on GitHub Actions, **original order** (random ordering disabled), on the merge commit CI tested, environment validated first | Labels isolate non-order flakiness; PR merge commits rebuilt; invalid environments excluded, not mislabelled |
| Features | 4 factors | MDFlaker's factors (B) + 17 failure-evidence features (F); 66 static context features tested separately (C) | F: co-failures, job duration, change content, where the traceback ends |
| Classifier | KNN (k = 5 paper; 10/8 in code) | Extra Trees (ET-BF), 100 trees, threshold 0.5 | Learns feature interactions; no integer casting |
| Split | Random 75/25 of rows | E1 time-ordered within project, E2 leave-one-project-out, unseen-test subset | Prevents test and build memorization (row split leaks, as we showed in v0.6) |
| Metrics | Accuracy, precision, recall; no statistics ([APSEC] §VII) | MCC (primary), F1, precision, recall, 95% project-bootstrap intervals | Imbalance-robust metric with uncertainty |
| Success criterion | None stated | Rule frozen before labelling | Pre-registered |
| Explanations | Smell counts/types, CSV of smells per test ([APSEC] Fig. 4–5) | SHAP per prediction and globally | Explains the model's actual decision, per failure |
| Tool | MDFlaker (MySQL, Travis) | `flakexplain detect` + `triage` CLI | Adds rerun-based detection; triage ships the frozen model |

## 3. Their figures and tables, and our counterparts

| Theirs | Shows | Our counterpart | Status |
|---|---|---|---|
| [SI] Fig. 1, [APSEC] Fig. 2 | Architecture | Fig. 1 pipeline | ✅ have |
| [APSEC] Fig. 3 | Data-collection workflow | Fig. 1 pipeline | ✅ have |
| [APSEC] Fig. 1 | Build history example for flaky frequency | — | ➕ optional: one sentence + equation 1 in §5.1 |
| [APSEC] Table I | 8 smell categories | — | ➕ add the smell list we reimplemented (`mdflaker_v08_smells.py`) as a short table or footnote |
| [APSEC] Table II | Data per project | Fig. 2 projects / §4.4 counts | ✅ have |
| [APSEC] Table III | All 16 factor combinations, pooled | Table 5 (models) | ➕ **add**: same 16-combination ablation on our data (section 5) |
| [APSEC] Table IV | Per-project results | Fig. 4 per-project MCC | ✅ have (unseen tests) |
| [APSEC] Fig. 4–5, [SI] Fig. 3–4 | Smell distributions and per-test smell CSV | Fig. 5 SHAP | ➕ add smell distribution, flaky vs not flaky, on our 1,292 failures |
| [APSEC] Table V | Qualitative tool comparison (DeFlaker, FLAST, Bayesian) | — | ➕ add same-style table with FlakeXplain as a row |
| [SI] Fig. 2(a) | Flagged flaky / non-flaky counts, two classifiers, no ground truth | — | ➕ add flagged counts for MDFlaker and ET-BF **next to the true counts** |
| [SI] Fig. 2(b) | Build success/failure history | — | optional: failures per project over the 90-day window |

## 4. Their reported numbers vs ours

**[APSEC] Table III, all projects pooled, 563 test failures, 58% flaky, random row split:**

| Factors | Accuracy | Precision | Recall | F1* | MCC* |
|---|---:|---:|---:|---:|---:|
| Trace-back only | 0.83 | 0.80 | 0.94 | 0.870 | 0.667 |
| Frequency only | 0.72 | 0.76 | 0.75 | 0.760 | 0.432 |
| Smells only | 0.55 | 0.57 | 0.91 | 0.704 | −0.062 |
| All four | 0.85 | 0.86 | 0.89 | 0.879 | **0.703** |
| Random | 0.48 | 0.56 | 0.49 | 0.528 | −0.033 |

\* computed by us from the paper's TP/TN/FP/FN.

**MDFlaker's method under stricter evaluation (ours):**

| Setting | MDFlaker-style | ET-BF |
|---|---:|---:|
| Their data, leave-one-project-out (v0.6): spaCy / DRF | 0.442 / 0.824 (rule) | 0.275 / 0.093 |
| Our data, E1 time-ordered (frozen) | 0.239 (best baseline) | 0.755 |
| Our data, E2 leave-one-project-out (frozen) | −0.014 | 0.357 |
| Our data, unseen tests, strict history (post hoc) | −0.160 | 0.469 |

**How to read this.** The 0.70 MCC in [APSEC] comes from a random row split on data with 63% flaky
failures, where a stored traceback nearly reveals the label (v0.6). On new failures, split by time
or project, the same method falls to about 0 MCC, and ET-BF stays well above it. On MDFlaker's own
data with a project split, MDFlaker's rule is better than our models; we report that openly.
Different data and splits mean these rows are context, not a single comparison; the controlled
comparison is the bottom three rows. **Note:** those rows use the released-code configuration of
MDFlaker. Against the paper's own configuration (k = 5) the picture is weaker; see section 6.

## 5. Recommended additions (in order of value)

1. **k = 5 majority-vote KNN baseline** (the [APSEC] setting) on the v0.8 data, as a post-hoc row.
   Our frozen baselines used k = 10 / P > 0.7 and k = 8, so a reviewer could ask about k = 5.
2. **Factor-combination ablation** like [APSEC] Table III: the 16 combinations of MDFlaker's four
   factors with their KNN on our E1 and unseen-test splits, next to ET-BF. It directly tests their
   RQ1 claims (trace-back best, smells near random) on new data.
3. **Flagged-vs-true counts figure**, our answer to [SI] Fig. 2(a).
4. **Smell distribution figure** on our failures, flaky vs not flaky, our answer to [SI] Fig. 3–4.
5. **Tool comparison table** in [APSEC] Table V style, adding FlakeXplain.
6. Manuscript text fixes from section 1.

Items 1, 2 and 4 are new post-hoc analyses and are labelled post hoc; they do not change the frozen
v0.8 decision. **Items 1 and 2 are done: see section 6.**

## 6. Post-hoc results: MDFlaker exactly as the APSEC paper configures it

Script `scripts/mdflaker_v08_posthoc_apsec.py`, output `reports/mdflaker-fresh-v0.8/posthoc_apsec.json`
(22 October 2026). **Post hoc, outside the frozen rule**; `results.json`, `robustness.json` and
`posthoc_extra.json` are unchanged. KNN5 = k = 5, Manhattan distance, majority vote, on the four APSEC
factors (no previous state, no conditional rule), as in [APSEC] §IV-C and §V-A. The reference rows
(MDF-paper-int, KNN8-float, ET-BF) were recomputed in the same run and equal the published values
exactly, which checks the pipeline. Intervals: 95% project bootstrap, 2,000 resamples.

### 6.1 The k = 5 baseline (all four factors)

| Evaluation | n (flaky) | KNN5 float | KNN5 int | MDF-paper-int (frozen) | Best frozen baseline | ET-BF |
|---|---|---:|---:|---:|---:|---:|
| E1 time-ordered | 516 (171) | **0.474** | 0.293 | 0.033 | 0.239 | **0.755** |
| E2 leave-one-project-out | 1,292 (409) | **0.148** | −0.031 | −0.054 | −0.014 | **0.357** |
| Unseen tests, strict history | 321 (91) | −0.013 | −0.065 | −0.160 | −0.128 | **0.469** |

| ET-BF minus KNN5 (float) | ΔMCC | 95% interval |
|---|---:|---|
| E1 | +0.282 | [0.007, 0.755] |
| E2 | +0.209 | [−0.219, 0.641] |
| Unseen tests, strict | +0.482 | [−0.346, 0.851] |

**What this means:**
- **The paper's own setting is the strongest MDFlaker baseline.** On E1 and E2, KNN5 with float
  factors beats every baseline in the frozen comparison (0.474 vs 0.239 in E1). Our frozen comparators
  came from the released code (k = 10 / P > 0.7, k = 8), not from the paper.
- **ET-BF still has the higher MCC in every evaluation,** but against KNN5 only the E1 difference has
  an interval above 0, and only just. On E2 and on unseen tests the intervals include 0.
- **Consequence for the paper:** the claim "+0.63 over MDFlaker on unseen tests" is against the
  released-tool configuration. Against the APSEC configuration the point estimate is +0.48, but it is
  not statistically clear. The manuscript must say which MDFlaker configuration each number refers to,
  and report this table.
- Integer casting (as in the released code) badly hurts KNN5 (E1 0.474 → 0.293), mostly because it
  truncates flaky frequency to 0.

### 6.2 Factor ablation, our counterpart to [APSEC] Table III (KNN5, float factors)

| Factors | [APSEC] MCC* (their data, row split) | Our E1 | Our E2 | Our unseen, strict |
|---|---:|---:|---:|---:|
| frequency | 0.432 | **0.540** | 0.169 | 0.018 |
| size | 0.237 | 0.274 | 0.021 | −0.060 |
| smells | −0.062 | 0.062 | −0.458 | 0.055 |
| trace-back | **0.667** | 0.000 | −0.508 | 0.000 |
| size, frequency | — | **0.566** | **0.438** | 0.090 |
| trace-back, frequency | 0.647 | 0.507 | 0.199 | 0.030 |
| trace-back, smells | — | 0.130 | −0.397 | **0.149** |
| all four | **0.703** | 0.474 | 0.148 | −0.013 |
| random (coin) | −0.033 | 0.051 | 0.017 | 0.021 |
| *ET-BF (reference)* | — | *0.755* | *0.357* | *0.469* |

\* computed from [APSEC] Table III confusion counts. All 15 combinations are in `posthoc_apsec.json`;
the table shows the rows [APSEC] discusses plus the best combination in each evaluation.

**What this means, compared with [APSEC] RQ1:**
- **Trace-back, their best factor, does not work on our data.** Alone it labels every failure flaky
  (recall 1.0, MCC 0). Trace-back coverage marks the change as covered for only 93 of 1,292 failures
  (7%), and those are *less* often flaky (22%) than the rest (32%). On their data a stored traceback
  nearly revealed the label (v0.6), which may explain the difference.
- **Flaky frequency is our best single factor** (E1 0.540), consistent with their finding that it is a
  useful history signal.
- **Test smells are near random**, as [APSEC] also found (their −0.06, our 0.06).
- **Size is weak** on both datasets, as [APSEC] concluded.
- **Combining all four factors does not help on our data** (0.474 in E1, below frequency alone),
  unlike their result.
- The best combination in each column (size + frequency in E1 and E2, 0.566 and 0.438) was picked
  *after* seeing test results, so it is optimistic. In E2 it is above ET-BF (0.438 vs 0.357;
  difference −0.081, interval [−0.299, 0.274]). Report it as an observation, not as a fair baseline.

### 6.3 Updated claim for the manuscript

> Under the frozen rule, ET-BF beats the MDFlaker-style baselines from the released code. Post hoc,
> against MDFlaker configured exactly as in the APSEC paper (KNN, k = 5), ET-BF has the higher MCC in
> every evaluation (+0.28 in E1, interval [0.01, 0.76]; +0.21 in E2 and +0.48 on unseen tests, both
> with intervals that include 0). MDFlaker's best factor in the original study, trace-back coverage,
> does not separate flaky from non-flaky failures in fresh GitHub Actions data.
