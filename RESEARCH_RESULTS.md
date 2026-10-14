# FlakeXplain research results

Current guide report: `output/pdf/FlakeXplain_Final_Study_Report.pdf`.
Start with `reports/final-confirmation-v0.3/GUIDE_FINAL_BRIEF.md`, then `FINAL_STUDY_REPORT.md` in the same directory.

## Verified status

- Frozen development corpus: 96,118 source-mapped cases, 693 observed positives, 35 projects.
- Independent confirmation: 2,610 all-pass cases across three prospectively selected projects, after 25 detection rounds. Eleven attrs skip-only identities are excluded.
- At frozen thresholds, Extra Trees core/context models flagged 111/3 confirmation cases. Recall and average precision are undefined because no positives were observed. A constant-negative reference flags zero cases.
- Separate all-data deployment fit: 98,728 cases across 38 projects, 693 observed positives. Its own unbiased performance is not measured.
- Dataset components: original labels/metadata in `dataset/v0.1`, revised development features in `dataset/development-v0.2`, and independent confirmation cases/features in `dataset/confirmation-v0.3`.
- Published Random Forest reference is an adaptation. No improvement over complete CANNIER or the 2024 labelled-target transfer system is established.

## Local use

Run from the project root with the pinned `requirements-pilot.txt` environment:

```powershell
.\.venv-pilot\Scripts\python.exe scripts/validate_confirmation.py
.\.venv-pilot\Scripts\python.exe scripts/predict_flakiness.py --source-root local-evidence/confirmation-sources/attrs --path tests/test_hooks.py --qualname TestAsDictHook.test_asdict
```

Prediction statically parses source and never imports or runs the subject project. Scores are uncalibrated risk estimates; a flagged test is not a confirmed flaky test. Explanations are exact mean tree-path probability decompositions, not SHAP or causal diagnoses.

## Reproduction boundaries

Frozen manifests bind exact file bytes; `.gitattributes` preserves them across checkouts. Do not edit frozen exports or implementation files bound by manifests. Make a new version instead.

Downloaded raw XML archives, pinned source archives, transformed text caches and serialized model binaries remain under ignored `local-evidence/`. Public source/workflow references and checksums are recorded in the report manifests. A clean clone needs those retained artifacts or deterministic regeneration before model replay; the guide ZIP is a review package, not a complete replication release.

The full existing-data training scripts and tests are included. Pinned sources can be retrieved using `scripts/fetch_dataset_sources.py`; the confirmation source commits are in `reports/final-confirmation-v0.3/protocol.json`. Keep failed, incomplete and zero-positive subjects visible. Do not retune on the already inspected external results and call them untouched again.

The manuscript remains a draft. Human annotations, near-clone review, compatible baseline reproduction and genuinely independent positive evidence remain necessary for stronger publication claims.
