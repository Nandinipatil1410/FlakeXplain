# Reproducing the matched CANNIER experiment

This is a retrospective classifier ablation, with explicitly changed project-fold evaluation and software versions. It does not rerun the full hybrid detector or reproduce its execution-cost claims.

## Inspect retained results

Start with MATCHED_COMPARISON_REPORT.md and paired_comparisons.csv. Original released-score AP is in authors_released_predictions_summary.csv; it was computed from the authors' predictions, not printed in their paper. The matched dataset and exclusion tables are in dataset/cannier-matched-v0.4.

Model replay requires the local model files named in run_manifest.json. They are retained under ignored local-evidence/cannier-matched-v0.4/models and are excluded from the review ZIP. Existing exports must not be silently overwritten.

## Regenerate in an isolated experiment workspace

Use Python 3.11. Create an empty experiment directory and copy these inputs into the same relative locations: scripts/, requirements-pilot.txt, requirements-cannier-matched.txt, cannier-replication/subjects.json, cannier-replication/LICENSE, and dataset/development-v0.2/schema.json. Preserve file bytes. Do not copy the existing v0.4 output/data directories into this empty regeneration workspace.

From that workspace:

```powershell
python -m venv .venv-cannier
.\.venv-cannier\Scripts\python.exe -m pip install -r requirements-cannier-matched.txt
.\.venv-cannier\Scripts\python.exe scripts/fetch_cannier_release.py
.\.venv-cannier\Scripts\python.exe scripts/prepare_cannier_matched.py freeze
.\.venv-cannier\Scripts\python.exe scripts/prepare_cannier_matched.py prepare
$env:LOKY_MAX_CPU_COUNT='4'
.\.venv-cannier\Scripts\python.exe scripts/train_cannier_matched.py
.\.venv-cannier\Scripts\python.exe scripts/validate_cannier_matched.py
.\.venv-cannier\Scripts\python.exe scripts/report_cannier_matched.py
```

The fetch stage downloads the 354 MB original release, checks its published LFS size and SHA-256, safely extracts selected NumPy arrays and SQLite files, and obtains exact subject source commits. It never loads a pickle file or executes subject code. Reference Python files are downloaded for inspection only.

Preparation verifies all original item and feature array rows against SQLite, then maps test identities to unique pinned source functions. A unique exact path suffix handles collection from a subject subdirectory. Both representations use the same source-mapped cases. Unresolved/generated tests are retained in exclusions, including their original labels.

Five outer project folds evaluate both representations. Four inner project folds select only secondary MCC thresholds; published tree counts are fixed, with no new hyperparameter search. The main threshold is 0.5. Natural imbalance is primary. Author-SMOTE is a separate training-only sensitivity experiment, using default five neighbours; infeasible folds fail explicitly.

For a fresh preparation, copy the provided DATASET_CARD.md and THIRD_PARTY_LICENSE.txt into the new data component before freezing its manifest, if identical documentation hashes are required. Timestamps, absolute local provenance paths and extra documentation can change manifests without changing numeric arrays. Numerical equality, label/source joins, splits, models and metrics must still be verified; do not claim byte-identical run manifests across different hosts.

PDF generation is optional and uses ReportLab in a separate document runtime. scripts/build_cannier_comparison_pdf.py reads only verified result tables. Render and visually inspect it before packaging. PDF metadata timestamps need not be identical across regenerations.

## Interpretation controls

Original CANNIER NOD/victim targets remain distinct from FlakeXplain's 25/27-round generic instability labels. A negative in one subtype task is not necessarily non-flaky. No runtime measurement is replaced with a static proxy. The context extension adds only the frozen 66 context counts, not additional revised body features.

Original authors' case-level cross-validation and sampling yield different reference numbers from this project-held-out experiment. Earlier feature development used these projects; this is not untouched external confirmation. No result here establishes measured rerunning-cost savings.
