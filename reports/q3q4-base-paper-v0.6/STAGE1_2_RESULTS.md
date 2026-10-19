# v0.6 stages 1 and 2: gate results (baseline arms only)

Run on 19 October 2026 with `.venv-pilot` (scikit-learn 1.7.2), using `scripts/mdflaker_stage1.py`
and `scripts/mdflaker_stage2.py`. Status: **Empirically Verified** for everything below. **No context
feature has been used in any model, and stage 3 has not been run.** Machine-readable outputs:
`stage1_summary.json` and `stage2_summary.json`. Raw exports and tables are under ignored
`local-evidence/mdflaker-v0.6/`.

## Stage 1: source join (label-blind)

| Project | Rows | Mapped to one source function | Note |
|---|---:|---:|---|
| spaCy | 1,080 | 1,035 | all 65 commits retrieved |
| django-rest-framework | 536 | 500 | all 62 commits retrieved |
| incubator-superset | 535 | 8 | 81/84 commits unretrievable; excluded by Amendment A2 |

How rows were resolved: 646 by the recorded failing-test path, 897 by unique-name search inside the
build commit, 81 ambiguous or unresolved, and 527 with the commit unavailable. The rows form 481
distinct test groups.

Two label-blind implementation changes were made during stage 1:
- `.py` files over 1 MB are skipped when exporting source. These are spaCy's generated lemmatizer
  lookup tables; the 18 in the first spaCy export made the AST parser run out of memory. Each
  commit's skipped list is in `sources/<project>/<commit>/.skipped.json`.
- Large blobs are fetched lazily for spaCy, because 51 spaCy commits first failed to export without
  them.

**Disclosure.** An early stage 1 trial ran with broken spaCy exports (0 spaCy rows mapped). Before it
was stopped, it wrote a summary at 21:29, 13 minutes before Amendment A2 was committed at 21:42. At
that time the script computed G1 automatically, so the file contained label-wise coverage counts
for all 2,151 rows. Nobody read it until after A2 was committed. A2 was decided only on commit
availability. The file is kept, unchanged, as
`local-evidence/mdflaker-v0.6/trial_stage1_summary_written_2129.json`. Since then, the script
computes G1 only on request, in stage 2.

## Gate G1 (A2 population: spaCy + DRF, 1,616 rows): **PASSED**

95.0% of rows are mapped (threshold 85%). The mapped rate is 94.5% for flaky rows and 95.9% for
non-flaky rows, a gap of 1.4 percentage points (threshold 10).

## Gate G2a (implementation check): **FAILED**

Only 142 of the released recorded decisions join uniquely to `dataset.csv`. On those, our
reimplementation of the paper's method agrees with the recorded decision 74.6% of the time
(threshold 90%): 82.2% for traceback-rule rows and 66.7% for multi-factor rows. The released
decisions were produced from the authors' database at a different time from the CSV, so the
released code and data cannot reproduce them exactly.

**Consequence (fixed in A1.2):** the experiment continues, but every claim must say "against our
reimplementation of the described method", not "against MDFlaker's results".

## G2b: released-prediction reference R (reported, not part of the rule)

The recorded decisions cover only 173 dataset rows (10.7% of the primary population). On those rows,
in-sample for MDFlaker: MCC 0.166, F1 0.203, precision 0.121, recall 0.636, accuracy 0.682. Coverage
is too low for R to be a useful reference.

## Comparator selection (primary protocol: test-grouped 10-fold CV, 30 repeats, 1,616 rows)

| Candidate | MCC (95% CI) | F1 | AP | MCC spaCy | MCC DRF |
|---|---|---:|---:|---:|---:|
| MDF-paper-int (paper's method, as released) | 0.526 [0.515, 0.537] | 0.779 | 0.899 | 0.389 | 0.826 |
| MDF-paper-float | 0.523 [0.512, 0.535] | 0.807 | 0.878 | 0.351 | 0.830 |
| KNN8-int | 0.427 [0.418, 0.437] | 0.756 | 0.883 | 0.271 | 0.710 |
| **KNN8-float → B\*** | **0.534 [0.523, 0.545]** | 0.825 | 0.865 | 0.400 | 0.724 |

B\* = **KNN8-float**, chosen by mean MCC under the frozen rule. It is only 0.008 MCC above the
paper's own method, so either is a fair comparator.

## Data facts

- 83 (build, test) keys occur more than once, giving 84 extra rows. In 4 of those keys the
  duplicates have conflicting labels, and in 66 the factor values differ. All rows are kept, as the
  authors released them.
- Labels in the primary population: 1,033 of 1,616 rows are flaky (63.9%).
- S7, baseline-only on all 2,151 rows: MDF-paper-int 0.563, MDF-paper-float 0.601, KNN8-int 0.502,
  KNN8-float 0.551 and ET-B 0.682 MCC. ET-B uses only the authors' features. This already suggests
  that the classifier swap alone is worth a lot. C2 is the test that separates that from the context
  contribution.

## Next: stage 3 (not run)

Stage 3 compares ET-BC with KNN8-float (C1) and with ET-B (C2), under the frozen C1/C2 rule and the
A2 project criteria.
