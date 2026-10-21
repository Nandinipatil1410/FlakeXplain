# FlakeXplain: bounded development-cycle results

The highest observed development AP is 0.05516 (Tuned ET: context v2), versus 0.00840 for the original body-only pilot. The predeclared revised-context comparison changes pooled AP by +0.04804, with a conditional project-bootstrap interval [-0.00651, +0.08545]. These are development findings on already-inspected folds, not proof of improvement over a published base paper.

Prepared 13 October 2026 for the guide discussion on 14 October 2026.

## Scope and method

Original dataset v0.1, labels and splits are frozen. All 96,118 cases and 35 projects remain; no artificial balancing, subject reruns or label changes were performed. Ten model variants were assessed using five outer development folds and four inner project folds. Four Extra Trees configurations vary depth/leaf size/class weighting; two Logistic Regression C values are compared. Candidates maximize inner OOF average precision; thresholds maximize inner OOF F1. Numeric LR uses training-only log1p/scaling. Text LR uses masked AST tokens and stateless hashing with training-only IDF. Every selected inner OOF score is retained.

V2 core* includes six new body-operation counts and two scoped-read indicators in addition to the original 22 body counts. Thus v2 is an incremental-context comparison, not a pure body/context ablation. The v1 comparisons retain the strict 22-versus-55 distinction.

## Results

| Model | AP (0-1) | Precision | Recall | F1 | MCC | FP / 1k |
|---|---:|---:|---:|---:|---:|---:|
| Original ET: body | 0.00840 | 1.24% | 29.44% | 2.37% | 0.0278 | 170.7 |
| Original ET: context | 0.00686 | 0.84% | 60.32% | 1.66% | 0.0149 | 515.3 |
| Tuned ET: body v1 | 0.00615 | 0.53% | 4.62% | 0.95% | -0.0058 | 62.7 |
| Tuned ET: context v1 | 0.03155 | 1.55% | 47.62% | 3.00% | 0.0521 | 220.1 |
| Tuned ET: core v2* | 0.00711 | 1.51% | 10.68% | 2.64% | 0.0215 | 50.7 |
| Tuned ET: context v2 | 0.05516 | 1.33% | 7.22% | 2.25% | 0.0146 | 38.8 |
| LR: body v1 | 0.00987 | 0.41% | 8.95% | 0.79% | -0.0157 | 156.9 |
| LR: context v1 | 0.02654 | 0.49% | 14.29% | 0.94% | -0.0143 | 212.1 |
| LR: core v2* | 0.01262 | 0.97% | 8.66% | 1.75% | 0.0078 | 64.1 |
| LR: context v2 | 0.01328 | 0.79% | 22.37% | 1.53% | 0.0041 | 204.1 |
| Text LR: body | 0.00953 | 0.90% | 22.94% | 1.73% | 0.0099 | 183.9 |
| Text LR: context | 0.00863 | 1.02% | 21.79% | 1.96% | 0.0152 | 152.9 |

AP is average precision, not accuracy or trapezoidal PR area. Precision/recall/F1 use thresholds chosen inside the training partitions. Best model is identified after development-result inspection and is descriptive, not a confirmed deployment selection. Pooled scores from different models/folds need not be calibrated; retain fold/project/macro results.

### Later Random Forest reference results

Random Forest was added as a reference after the bounded development cycle. These results come from a separate five-project-fold development selection run on the same 96,118 cases, using 100 trees (`max_features="sqrt"`, `bootstrap=True`, no class weighting). The fixed development-selected thresholds below were used for threshold-based metrics.

| Model | AP (0-1) | Threshold | Precision | Recall | F1 | MCC | FP / 1k |
|---|---:|---:|---:|---:|---:|---:|---:|
| Random Forest: core reference | 0.00904 | 0.1400 | 2.00% | 3.90% | 2.64% | 0.0180 | 13.9 |
| Random Forest: context reference | 0.01459 | 0.0875 | 2.49% | 23.95% | 4.52% | 0.0572 | 68.0 |

These are development-selection results, not independent confirmation. Their fitting and selection procedure differs from the nested bounded-cycle results above, so compare them as a separate reference rather than treating them as a controlled head-to-head replacement. The Random Forest implementation is an adaptation, not a reproduction of the published study.

## Primary paired comparison by fold

| Fold | Revised core AP | Revised context AP |
|---|---:|---:|
| 0 | 0.05792 | 0.11149 |
| 1 | 0.00927 | 0.00691 |
| 2 | 0.00435 | 0.01235 |
| 3 | 0.00421 | 0.07427 |
| 4 | 0.00654 | 0.00732 |

Among 29 positive projects, revised context AP improved in 16 and regressed in 13. See metrics_project_macro.csv and primary_project_deltas.csv. The bootstrap resamples projects without refitting; it excludes feature-development/model-selection uncertainty and is not definitive significance.

## Per-project ranking budget

Taking the top 10% separately inside each project selects 9,628 cases in total (rounding up within projects). The original body pilot captures 63/693 positives (9.09%), the revised ET core captures 103/693 (14.86%), and revised ET context captures 121/693 (17.46%). This matched within-project ranking diagnostic is more relevant to a new project than pooling scores from differently calibrated fold models.

The revised context model's pooled top-10% recall is 44.16%, which is substantially higher than its per-project-budget recall. Do not present the pooled figure as the expected recall at a 10% budget inside a new project, or as measured rerun time savings. This is a retrospective label-capture analysis, not a new rerunning experiment.

## Error and representation audit

The declared sample contains 50 context-model false positives and 50 false negatives across 35 projects, with distinct source families per error type. Twelve source excerpts across 12 projects were inspected by Codex; no human causal validation or label changes are claimed. All 100 sample rows remain a declared review queue, with completed excerpt reviews stored separately.

| Representation | Features | Positive cases sharing vectors with negatives |
|---|---:|---:|
| v1_body | 22 | 379 / 693 (54.69%) |
| v1_context | 55 | 132 / 693 (19.05%) |
| v2_body | 30 | 277 / 693 (39.97%) |
| v2_context | 96 | 123 / 693 (17.75%) |

Collision counts are full-corpus descriptive diagnostics; labels were used only to measure collisions, never to construct predictors or fit an oracle. Lower collision counts mean more distinguishable source representations, not proven predictive or causal improvement.

Concrete findings: assertion-like unittest/fixture calls were missed by ast.Assert counts; decorator-generated arguments can be mistaken for candidate fixtures; time-related API names can describe deterministic operations; shared module state, parameter-specific behavior and stringified subprocess programs remain partial. The revision separates fixture/helper/lifecycle means and adds operation counts and potential class state. Plugin/override graph expansion was not implemented in this bounded cycle.

## Verification

466 checks passed; 50 saved models reproduced outer scores. Independent sklearn metrics, inner-AP selection, thresholds from saved inner predictions, training-only scalers/IDF and project membership were verified. Candidate-fit convergence warnings: 0. The repository unit suite passed 84 tests with one Linux-only test skipped (85 discovered). Exact models and inner score arrays are retained in ignored local-evidence/development-models.

## Research positioning and next decisions

Recommended framing: cross-project static prediction of observed Python test instability. Use the 2024 cross-project study for the research question and the 2022 static study as a methodological baseline family. Keep CANNIER as a Python/hybrid reference and source of subject overlap. These are adaptations to investigate, not reproduced methods or beaten published scores.

The 2024 study evaluates transfer/filtering approaches with source/target adaptation conditions. Audit its released code and target-data assumptions before attempting a zero-target-label comparison. The 2022 study uses Java metrics, requiring an explicit Python mapping. CANNIER has runtime features, different targets, budgets and a hybrid objective. None of their reported scores is directly comparable with our development scores.

Proposed next steps: agree the static cross-project scope with the guide; complete a compatible released-baseline adaptation and bounded fixture/parameter audit; predeclare the final model/evaluation protocol; obtain independent evidence if an untouched confirmation claim is required. Current outer folds have influenced development. All-pass-after-N labels remain uncertain; random-round order/seed effects are confounded; current source/near-duplicate/fixture limitations remain disclosed.

## Sources

- [Cross-project study, IEEE Access 2024](https://doi.org/10.1109/ACCESS.2024.3458184) and [authors' artifact](https://github.com/alfcan/crossproject-flaky-test-prediction).
- [Static Test Flakiness Prediction, EMSE 2022](https://doi.org/10.1007/s10664-022-10227-1).
- [CANNIER, EMSE 2023](https://doi.org/10.1007/s10664-023-10307-w).
