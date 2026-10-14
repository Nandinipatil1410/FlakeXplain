# FlakeXplain: completed study and independent confirmation

Prepared 14 October 2026. Status: empirically evaluated; publication-level detection improvement remains unestablished.

## What was completed

- Audited 35 development projects and froze 96,118 source-mapped cases: 693 observed flaky and 95,425 not observed flaky (0.721% observed prevalence).
- Completed the original pilot and one bounded development cycle with project-separated training and tuning, static feature/label isolation, natural class imbalance, error inspection and collision audits.
- Inspected the pinned 2024 authors artifact; implemented a Random Forest family reference on our features. This is explicitly an adaptation, not a faithful published reproduction.
- Selected three new confirmation projects before inspecting outcomes, froze features, model selection rules and thresholds, and executed full baseline + 25-round workflows.
- Fitted four development-only final models before opening confirmation evidence; replayed external predictions and independently verified metrics.
- Produced source-linked mean tree-path probability decompositions; fitted a separate all-data deployment model after evaluation.

## Independent evidence

[Workflow run](https://github.com/Nandinipatil1410/FlakeXplain/actions/runs/38429430361). All three jobs passed local structural evidence checks, pinned source verification and complete 12 original + 12 random + 1 reverse rounds. The longest job took about 4.5 minutes, within the authorized four-hour cap. No projects were replaced after observing results.

| Project | Collected identities | Binary cases | Observed flaky | Skip-only | Detection seconds |
|---|---:|---:|---:|---:|---:|
| attrs | 1,412 | 1,401 | 0 | 11 | 194.12 |
| tenacity | 185 | 185 | 0 | 0 | 62.27 |
| werkzeug | 1,024 | 1,024 | 0 | 0 | 232.16 |

All 2,610 binary cases passed all 25 detection rounds. There were no source-mapping or substantive exact-body-overlap exclusions among these binary cases. Eleven attrs identities were skip-only and never entered model evaluation. Source mapping is static, and near-clone independence is not fully audited.

## Frozen-threshold confirmation results

| Model | Threshold | Observed false alarms | Per 1,000 negative-labelled cases |
|---|---:|---:|---:|
| extra_trees_core | 0.519522 | 111 | 42.529 |
| extra_trees_context | 0.036106 | 3 | 1.149 |
| random_forest_core_reference | 0.140000 | 24 | 9.195 |
| random_forest_context_reference | 0.087500 | 2 | 0.766 |
| constant_training_prevalence | 0.500000 | 0 | 0.000 |

Recall and average precision are undefined on this zero-positive confirmation set. F1/MCC conventions and their definedness flags remain in the machine-readable tables; they do not establish detection ability. The constant-negative reference makes zero false alarms here. High accuracy is therefore uninformative.

At separately development-selected thresholds, context ET produced 3 flags versus core ET's 111. This is a descriptive false-alarm difference on three selected projects. The two models selected different class weights as well as different thresholds; it does not isolate context causally or establish a matched-recall advantage. At threshold 0.5, core/context ET produced 221/0 flags.

## Development findings and their limits

The bounded nested development cycle yielded pooled average precision 0.055157 for revised-context ET versus 0.007112 for revised-core ET. Its project-resampling interval for the AP difference was [-0.006505, 0.085454], including zero. These folds influenced development and cannot be called untouched final confirmation.

At a separately ranked top-10% budget within each development project, revised-context ET found 121/693 observed positives (17.46%) versus 103/693 (14.86%) for revised-core ET. This is more relevant to an unseen-project inspection budget than pooled top-10% ranking. No rerun CPU savings were measured.

For the final all-development configuration selection, five project-fold OOF AP was 0.026762 for context ET and 0.010972 for core ET. These are selection results from a different fitting procedure, not replacement nested estimates or independent confirmation scores. All four final configurations are recorded in selected_models.json.

The 30-feature core includes two scope-aware read indicators. The 96-feature variant adds fixture/helper/lifecycle/class-state context; this comparison is incremental context beyond a scope-aware core, not a strict body-only comparison. The v0.1 22-feature body remains the strict body-only representation.

## Published baseline compatibility

The [2024 cross-project study](https://doi.org/10.1109/ACCESS.2024.3458184) is useful methodological framing. Its [authors' artifact](https://github.com/alfcan/crossproject-flaky-test-prediction/tree/8fe244f03122706763484dea7b4d98b09fefb923) contains 26 Java metric columns. CPTrAda explicitly trains with labelled target-project fractions of 25%, 50% or 75%, testing on the remaining 25% target subset; it uses PCA, undersampling and transfer boosting. Our task uses no target-project training labels and Python AST features.

The implemented 100-tree Random Forest references use the same core/context feature tables and external cases, with no sampling, PCA or target-label transfer. They are model-family references only. No faithful [CANNIER](https://doi.org/10.1007/s10664-023-10307-w) hybrid/dynamic baseline or matched rerun-efficiency comparison was completed. Improvement over either complete published system is not established.

## Deployment and explanations

A separate Extra Trees context model was fitted on all 98,728 eligible cases across 38 projects, including the now-evaluated confirmation cases (693 observed positives). It keeps the development-selected configuration and threshold. The earlier frozen models own the confirmation results; this deployment refit has no new unbiased test score. Serialized deployment predictions were replayed on 100 cases.

Global impurity importances and nine source-linked explanations are provided. Explanations use exact mean tree-path probability decomposition with reconstruction checks; they are not SHAP and do not diagnose failure causes. Features associated with fixtures, processes and cleanup reflect model attribution, not empirical causal validation.

## Remaining work before a strong publication claim

1. Obtain genuinely independent positive projects under a prospectively declared follow-up protocol. Do not silently replace zero-positive subjects or retroactively alter this confirmation.
2. Complete human source/context review and validate unresolved fixture/plugin/override behavior; the current error audit is AI-assisted and has no confirmed causal labels.
3. Reproduce a compatible published baseline or narrow the contribution explicitly to an empirical Python context study. A labelled-target transfer task would require a separately declared experiment.
4. Measure matched-budget rerun yield/time if claiming detection-efficiency improvement; add SHAP only as additional attribution with a fixed background.
5. Complete licence review, near-clone/fork assessment, citation checking and manuscript peer review before submission. No acceptance guarantee is supported.

## Reproduction and verification

- External validation: 109 checks passed. Feature adapter: 80 contexts / 7,680 numeric values exactly replayed. Existing test suite: 85 tests, 84 passed and one Linux-specific skip.
- Original data and pilot/development artifacts remain unchanged. Frozen models and downloaded archives remain under ignored local-evidence; their checksums and workflow references are exported.
- Reproduction requires requirements-pilot.txt, pinned source archives, the frozen development tables, confirmation XML and local model binaries. The review ZIP is not a complete model/source redistribution package.
- metadata_clarification.json explains the attrs candidate-count field naming error in the preserved evaluation output; guide_project_table.csv supplies corrected binary counts. Metrics are unaffected.
