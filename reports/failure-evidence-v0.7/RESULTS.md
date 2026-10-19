# v0.7 failure-evidence experiment: results

Run on 19 October 2026 (`scripts/failure_evidence_v07_features.py`, `scripts/failure_evidence_v07_run.py`).
Status: **Empirically Verified**. The rule was frozen in `PROTOCOL.md` (commit `279ef1b`) before
feature extraction. Machine-readable outputs: `results.json`, `comparators.json` and
`features_summary.json`, plus the post-hoc `posthoc_build_grouped.json`.

## Verdict under the frozen rule: headline NOT met

Comparators were selected from baseline arms only: KNN8-float for P1 and MDF-paper-int (the paper's
method) for P2.

| Rule element | Result | Met? |
|---|---|---|
| R1, P1: ET-BF vs KNN8-float | ΔMCC +0.231 [+0.220, +0.242] (0.534 → 0.766) | yes |
| R2, P1: ET-BF vs ET-B | ΔMCC +0.124 [+0.111, +0.136] | yes |
| R3, P2: ET-BF vs MDF-paper-int, both projects | spaCy 0.275 vs 0.442 (−0.167); DRF 0.093 vs 0.824 (−0.731) | **no** |
| **Headline** | | **no** |
| Context claim: ET-BFC vs ET-BF | P1 −0.057 [−0.067, −0.047] | no |
| Rerun cost: ≥ 10% saving at 95% flaky recall | ET-BF reruns 74.9% of failures vs 91.0% for KNN8-float (17.6% saving) | met, but see below |

## Post-hoc diagnostics (after the verdict; they do not change it)

They show that the within-project R1/R2 gains **should not be claimed as real improvements**:

1. **Traceback-availability artifact.** In spaCy, rows whose test has a stored traceback are 6.4%
   flaky (173 rows), and rows without one are 81.9% flaky (907 rows). Whether the authors' log parser
   stored a traceback is close to a label proxy. `has_own_traceback` is the second most important
   ET-BF feature (permutation importance 0.20, after MDFlaker's own Traceback Coverage at 0.52). A
   deployed tool would not see this availability pattern the same way.
2. **Build fingerprints.** Test-grouped folds still put other failures from the same build into
   training. With folds grouped by build instead, the failure features *reduce* MCC (ET-BF vs ET-B:
   −0.034 [−0.039, −0.029]). Build-grouped folds in turn reintroduce test memorization, so every arm
   rises (KNN8-float 0.745).
3. **No clean within-project split exists.** Linking tests and builds puts all of spaCy and 95% of
   DRF into one connected component. The only evaluation free of both shortcuts is
   leave-one-project-out, and there ET-BF loses to the paper's method in both projects.
4. **The rerun-cost saving is not at matched recall** (ET-BF 0.950 vs KNN8-float 0.971), and it
   inherits points 1 and 2.

## What this means

- On MDFlaker's released data, MDFlaker's own conditional rule generalizes across projects better
  than any learned model we tried (v0.6 and v0.7).
- The large within-project numbers are driven by artifacts of how the dataset was collected: per-test
  memorization (v0.6), per-build fingerprints and traceback availability (v0.7). With 2 projects and
  heavily linked tests and builds, this dataset cannot support an honest "we beat MDFlaker" claim.
- FlakeXplain context did not help on this failure-level task in either version.
- **MDFlaker should be reported as a negative replication result, not used as the improvement base.**
  The dataset-artifact findings themselves (the traceback-availability proxy, and the test and build
  shortcuts that make row-level and test-grouped evaluations optimistic) are a legitimate
  methodological contribution.
