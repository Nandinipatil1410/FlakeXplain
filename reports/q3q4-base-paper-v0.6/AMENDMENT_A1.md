# Amendment A1 to the v0.6 protocol

Dated 19 October 2026. Committed **before stage 1**: no source join, no context extraction, no model
fit, and no comparison of any prediction with a label had been done. `PROTOCOL.md` and
`protocol.json` stay byte-identical; where they conflict, this amendment takes precedence.

## What triggered it (facts found after the freeze)

1. **The base paper reports no precision, recall, F1 or accuracy.** The Software Impacts article
   (4 pages, read in full) gives only Fig. 2(a), unlabelled detection counts: TC_flaky 234,
   TC_non-flaky 374, MF_flaky 447, MF_non-flaky 867, Missing 44. It cites the APSEC paper as
   "ICSE 2022" in reference [13]. The published-F1 version of gate G2 is therefore impossible.
   This is recorded in `published_reference.json`.
2. **The paper links a different repository:** `SoftwareImpacts/SIMPAC-2025-241` at
   `5b63f3a96b999b13c709a367d161708a4bcea9b9`, the same commit as `azeem599/SIMPAC_FT`. All four
   dataset CSVs, all three build histories and the shared code files are byte-identical to the
   pinned `azeem59/MDFlakerForPaperUpdated@618dc047`. The paper repository has no `evaluate.py`.
3. **The paper's classifier is not the KNN(k=8) that was frozen.** Section 2.3 of the paper and
   `mysql_handler.py` (`update_detection_result`, `KNN_predict`) implement a conditional strategy:
   - *Scenario 1* (previous build state = passed): flaky if and only if the traceback does **not**
     cover the recent changes.
   - *Scenario 2* (otherwise): `KNeighborsClassifier(10, p=1)` trained on `dataset.csv` with
     int-cast features, flaky if and only if P(flaky) > 0.7.
4. **The paper repository releases the tool's recorded decisions.**
   `output/csv/results/Results_2020-11-28_01-39-46.csv` holds 1,966 executions (Build ID, Test Method,
   decision, detection method, factors, Path): 1,082 Flaky, 849 Non-Flaky and 35 "Missing factors".
   These recorded counts differ from Fig. 2(a); both are reported.

## Changes

**A1.1: comparator candidates.** B\* is chosen from four candidates, all re-fitted inside each
training fold:
- `MDF-paper-int`: the conditional strategy above, with int-cast features, k=10, p=1 and threshold
  P > 0.7. This is the paper's method.
- `MDF-paper-float`: the same, with float features.
- `KNN8-int` and `KNN8-float`: the originally frozen `evaluate.py` variants (k=8, p=1, majority vote).

B\* is the candidate with the highest mean primary-protocol MCC. It is fixed from baseline results
only, before any context arm is evaluated. C1 compares ET-BC against B\*. The rest of the success rule
is unchanged.

**A1.2: gate G2 (replaces the original G2).**
- *G2a, implementation check.* Fit `MDF-paper-int` exactly as released: `read_data` with
  `header=1` and `[1:]`, which drops the first two data rows, trained on all of `dataset.csv`. Apply
  it to every `Results` row that has a decision of Flaky or Non-Flaky and joins uniquely to
  `dataset.csv` on (Build ID, Test Method), using that row's dataset factors. G2a passes if our
  decisions agree with the recorded decisions on at least 90% of joined rows. If it fails, every
  claim says "against our reimplementation of the described method", and the disagreement is
  reported.
- *G2b, released-prediction reference R (reported, not part of the rule).* The recorded `Results`
  decisions are joined to the authors' labels. Missing-factor rows are counted as non-flaky
  predictions, and the coverage rate is reported. The output is MCC, F1, precision, recall and
  accuracy. These are **in-sample** for MDFlaker, because its KNN was trained on the same
  `dataset.csv`, so R is an optimistic upper reference for the base, not a paired comparison. ET-BC's
  primary-protocol MCC is reported beside it.

**A1.3: stage 1 mapping.** The `Path` column of the `Results` CSV is an extra label-blind source for
locating test files. It is used when the build history's `failed_info` does not identify a unique
file. The G1 thresholds are unchanged.

**A1.4: provenance.** Data are taken from the paper repository (`SIMPAC-2025-241@5b63f3a`). Its
hashes equal those already frozen in `protocol.json`.

Nothing else changes: not the features, the Extra Trees configuration, the grouping, the seeds, the
thresholds or the C1/C2 rule values.
