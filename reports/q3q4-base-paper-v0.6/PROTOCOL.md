# MDFlaker-base context experiment (v0.6): frozen protocol and success rule

Frozen 19 October 2026, **before any data were joined to source, any context feature was extracted,
or any model was fitted under this protocol**. The only data inspected so far are the released CSV
headers, row, label and test-name counts, and one django-rest-framework build history (build IDs to
commits). No feature-label relationship has been examined.
The machine-readable copy is `protocol.json`, which records this file's SHA-256.
Status of everything below: **Proposed** until `run_manifest.json` exists.

## Question

On MDFlaker's own released data, do our static fixture/helper/lifecycle/class-state context
features plus a fixed Extra Trees pipeline classify flaky test failures better than (a) MDFlaker's
published KNN method and (b) the same Extra Trees pipeline without context?

Base paper: A. Ahmad, "MDFlaker: A tool for multi-factor detection and root cause analysis of flaky
tests", *Software Impacts*, 2025, doi:10.1016/j.simpa.2025.100794 (SCImago Q3, Software, 2022-2025).
Method origin: Ahmad, Gomes, Shi, Sandahl, Leifler, APSEC 2021, doi:10.1109/APSEC53868.2021.00041.

## Data (authors' release, unchanged)

- `F_Detector/dataset.csv` from `azeem59/MDFlakerForPaperUpdated` at commit
  `618dc04739f2f93512e341e1a9dcce3ad6afb37d`: 2,151 failed test executions (spaCy 1,080,
  django-rest-framework 536, Superset 535). Project membership comes from the per-project CSVs.
  SHA-256 values are in `protocol.json`.
- Label: the authors' `Flaky or Not` column (1 = the failure did not reproduce in all 30 reruns).
  It is never altered or merged with FlakeXplain labels.
- Authors' features (set **B**): Flaky Frequency, Traceback Coverage, Test Smells, Previous State,
  Test Size.
- Raw files go under ignored `local-evidence/mdflaker-v0.6/`. Upstream code is read as data and never
  imported or executed.

## Stages and gates (in this order; a failed gate stops the experiment and is reported)

**Stage 1: label-blind source join.** For each row, join `Build ID` to `commit_sha` using the
released `*_build_history.json`. Locate the test from that build's `failed_info`
(`test_dir` + `test_file` + `test_class` + `test_case`). Download the GitHub archive at that commit
and run `scripts/confirmation_features.py::extract` unchanged, producing the same 66 context columns
as `dataset/cannier-matched-v0.4/features_context.csv.gz` plus `context_available`. A row is
*mapped* only if exactly one function matches. Ambiguous, missing or unparsable rows get zeros and
`context_available = 0`; they stay in the data and are listed in `source_exclusions.csv`. Join rules
never read the label.

- **Gate G1 (coverage):** at least 85% of rows are mapped. In addition, the mapped rate among flaky
  rows and among non-flaky rows must differ by no more than 10 percentage points. This is the only
  point at which labels are touched in stage 1, and they are only counted.

**Stage 2: baseline reproduction.** Before stage 2, `published_reference.json` must be filled with
the precision, recall, F1 and accuracy that the Software Impacts and APSEC papers report for the
multi-factor KNN, quoted with page and table numbers, or with an explicit "not reported". This file
is the only permitted addition after freezing. It must be committed before any context feature is
extracted.

Two baseline variants, both KNN(k=8, p=1, unscaled), as in `evaluate.py`:
- **B-released:** features cast to `int`, as in the released `read_data`.
- **B-described:** features as floats, as described in the paper.

- **Gate G2 (reproduction):** under the authors' split (random permutation; train on all but the
  last 200 rows, test on the last 80), repeated over 1,000 seeded permutations, the mean F1 of at
  least one variant is within ±0.05 of the published F1. If the paper reports no comparable F1, G2
  requires only that our implementation reproduces `evaluate.py`'s predictions exactly on 20 fixed
  permutations. In that case all claims say "against the released implementation".

The comparator **B\*** is whichever of B-released and B-described has the higher mean MCC under the
primary protocol below. It is chosen from baseline results only, before any context arm is
evaluated.

**Stage 3: context arms.** These run only after G1 and G2 pass and B\* is fixed.

## Arms

| Arm | Features | Classifier |
|---|---|---|
| KNN-B\* | B\* | KNN(k=8, p=1), authors' method |
| ET-B | B (floats) | ExtraTreesClassifier(n_estimators=100), other parameters scikit-learn defaults |
| ET-BC | B + 66 context + `context_available` | same ExtraTrees configuration |

None of the arms uses hyperparameter search, scaling, feature selection, SMOTE or class weighting.
The labels are about 64% flaky, so they are used at their natural balance. The decision threshold is
the classifier's default: 0.5 for ET, majority vote for KNN.

## Primary protocol: test-grouped repeated cross-validation

`StratifiedGroupKFold(n_splits=10, shuffle=True)`. The group is project + test file + test class +
test name; if the test file is unresolved, project + test name is used. All executions of one test
stay on the same side of each split. The protocol uses 30 repeats; repeat r uses seed 20261020 + r
for the split, and the same seed for every arm's classifier. Arms are paired by repeat.

**Why grouped is primary.** Only 448 distinct test names cover 2,151 rows, and context features are
constant per test. Under row-level splits, any per-test constant can act as an identifier and let a
forest memorize labels across builds of the same test. Grouping removes that shortcut. The authors'
row-level protocol is still run as secondary analysis S1, for comparability.

**Metric:** signed MCC from pooled out-of-fold predictions in each repeat, averaged over the 30
repeats. F1 (the paper's metric), precision, recall, accuracy and AP are also reported.

## Success rule

For a comparison X vs Y, D = MCC(X) − MCC(Y), paired by repeat, with a 95% t-interval over the
30 repeats.

- **C1, vs the published method:** ET-BC vs KNN-B\*.
- **C2, context contribution:** ET-BC vs ET-B.

**Headline claim, "FlakeXplain context features improve on MDFlaker", requires all of:**
1. G1 and G2 passed;
2. C1: mean D ≥ +0.05, its interval excludes 0, and mean ΔF1 ≥ 0;
3. C2: mean D ≥ +0.02, and its interval excludes 0. This shows the gain is not only a classifier swap;
4. no degradation: in no project is ET-BC's MCC (pooled over all repeats) below KNN-B\*'s by 0.05 or
   more.

**Strength qualifier:** the claim is "robust across projects" only if ET-BC beats KNN-B\* in MCC in
at least 2 of the 3 projects. Otherwise it is "supported on pooled data only".

**Partial outcomes, worded in advance:**
- C1 met, C2 not met: "Extra Trees on MDFlaker's own features beats its KNN; added static context
  gives no established further gain."
- C2 met, C1 not met: "context improves Extra Trees, but does not establish improvement over the
  published method."
- Neither met, or a gate failed: report it as such, and keep CANNIER v0.5 as the base paper.

No change to features, models, seeds, groups, thresholds or this rule is allowed after any stage 3
result is seen. Any variant is a new version.

## Secondary analyses (all reported, none can rescue the headline)

- **S1, the authors' row-level protocol:** the same arms under `StratifiedKFold(10, shuffle=True)`
  over rows, 30 repeats. It also reports the gap between row-level and grouped scores as a measure
  of memorization.
- **S2, leave-one-project-out:** 3 folds, deterministic, all arms.
- **S3, both baseline variants** (B-released, B-described) under the primary protocol.
- **S4, static-only:** ET with Test Smells + Test Size + 66 context + indicator. It excludes the
  history features (Flaky Frequency, Previous State) and the change-dependent Traceback Coverage. It
  shows what our static view alone achieves.
- **S5, transfer prior from the 96,118-case corpus:** a frozen Extra Trees model trained on
  `dataset/development-v0.2` context-v2 features, with all django-rest-framework cases removed from
  training. Its score is added as one extra feature to ET-BC. Test-level FlakeXplain labels are used
  only to train that prior and are never copied into this dataset.
- **S6:** Random Forest(100) in place of Extra Trees for ET-B and ET-BC.
- Per-project tables, the mapping-coverage table and the exclusion list.

## Interpretation limits (fixed now)

- MDFlaker's task is *failure-level* (is this failed execution flaky?). It is not the test-level
  task of FlakeXplain v0.1-v0.5, and results are not comparable with those numbers.
- The data are small: 2,151 rows, 448 distinct test names and 3 projects. Project-level conclusions
  are weak.
- Flaky Frequency and Previous State are history features that belong to the base method. They are
  kept in B because they are the base paper's inputs, but they are not static features. S4 isolates
  the static view.
- Labels are the authors' 30-rerun labels from 2020 Travis CI builds; we did not re-execute anything.
- The Software Impacts article is a tool paper. Its empirical evaluation is in the APSEC 2021
  conference paper, and whether that counts as a Q3 base paper is the guide's decision.
- The CANNIER v0.5 protocol, results and files are not modified by this version.
