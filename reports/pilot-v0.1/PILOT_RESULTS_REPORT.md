# FlakeXplain pilot training results

**Empirically verified conclusion: this pilot does not support an improvement from the current bounded context feature set. Both classifiers generalize weakly to held-out projects.**

## Experiment actually run

Evaluated 96,118 cases across 35 projects: 693 observed-flaky and 95,425 not-observed-flaky. Natural positive prevalence is 0.7210%. No synthetic cases, oversampling or test-project tuning were used.

Extra Trees body-only (22 numeric features) versus the same model with bounded fixture/helper/lifecycle context (55 total features). Fixed parameters: 128 trees, max_depth=20, min_samples_leaf=5, max_features="sqrt", class_weight="balanced", bootstrap=False, random_state=20261013, four CPU threads. Class weights are computed within each fit. A shared configuration means the same hyperparameter settings/training procedure; the number of available features differs by design.

Five frozen outer project-separated folds provide one held-out prediction per case. For each outer fold and each feature variant, four inner project-separated fits select the threshold maximizing inner out-of-fold F1; a fifth fit uses all outer-training projects to predict the outer-test projects. In total, 50 fits were run and 10 outer models retained. No hyperparameter search, full-dataset deployment fit, LLM run or CANNIER faithful reproduction was performed.

Training/evaluation/bootstrap run time: 74.5 seconds on this machine (excluding installation and later artifact verification). Reproducible package pins are in requirements-pilot.txt; exact environment and pre-result choices are in protocol.json.

## Main ranking comparison

| Model/reference | Pooled average precision (0–1) | Recall at top-ranked 10% |
|---|---:|---:|
| Extra Trees: body | 0.008395 | 11.98% |
| Extra Trees: body + context | 0.006856 | 3.90% |
| Fixed test-size ranking | 0.008502 | 14.43% |
| Per-fold training-prevalence score | 0.005736 | 5.48% |

Constant-score AP is the corpus prevalence, 0.007210; it is a descriptive no-discrimination reference. Per-fold training prevalence is not globally constant, so its pooled AP differs. The size heuristic only ranks by body line span; its all-negative binary metrics in the CSV are placeholders for the all-negative reference, not a selected size threshold.

Context minus body pooled AP: **-0.001540**. Project-resampled paired 95% percentile interval (500 resamples): **[-0.004275, +0.001473]**. The interval includes zero; this is conditional uncertainty on fixed OOF predictions, with no refitting or feature-development uncertainty. It does not establish a statistically reliable improvement or deterioration.

Average precision uses [scikit-learn average_precision_score](https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html), not trapezoidal PR area. Pooled scores come from different fold models and are uncalibrated; fold/project results are essential alongside the pooled figure. [Extra Trees documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesClassifier.html) describes the class-weight and model settings used.

## Classification at training-only selected thresholds

| Model | Precision | Recall | F1 | MCC | TP | FP | FN | FP per 1,000 negatives |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Body | 1.24% | 29.44% | 2.37% | 0.0278 | 204 | 16286 | 489 | 170.67 |
| Body + context | 0.84% | 60.32% | 1.66% | 0.0149 | 418 | 49173 | 275 | 515.31 |

The context model’s higher recall comes with 49,173 false positives: more than half the negative cases are flagged. Its precision and F1 are lower than body-only. This is not evidence of a useful context improvement.

## Fixed 0.5 threshold reference

| Model | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| Body | 0.91% | 38.53% | 1.77% | 267 | 29225 | 426 |
| Body + context | 0.00% | 0.00% | 0.00% | 0 | 286 | 693 |

At 0.5, the context model detects none of the 693 observed positives. Class-weighted Extra Trees scores were not calibrated as natural-prevalence probabilities. Threshold adjustment cannot fix the poor ranking quality.

## Results by held-out fold

| Fold | Cases | Positives | Body AP | Context AP |
|---|---:|---:|---:|---:|
| 0 | 21,584 | 310 | 0.027261 | 0.017098 |
| 1 | 19,609 | 146 | 0.009030 | 0.004781 |
| 2 | 19,583 | 78 | 0.003866 | 0.003816 |
| 3 | 17,807 | 80 | 0.003661 | 0.003276 |
| 4 | 17,535 | 79 | 0.009252 | 0.004850 |

Context AP is lower in every outer fold. Airflow contributes 300 of 693 positives; fold 0 contains 310 positives. Project-level AP/recall are undefined for the six zero-positive projects and are left blank in metrics_by_project.csv. Precision with no predicted positives and degenerate MCC use zero with explicit definition flags.

## Project-macro sensitivity

| Model | Mean AP over 29 positive projects | Mean F1 over all 35 projects | Mean FP per 1,000 negatives |
|---|---:|---:|---:|
| Body | 0.029920 | 1.50% | 152.95 |
| Body + context | 0.014753 | 1.58% | 552.67 |

Equal-project macro F1 is slightly higher for context, while macro AP is lower and the false-alarm burden is much higher. This mixed secondary result is retained; it does not reverse the failed primary ranking comparison.

## Generalization diagnostics

| Model | Training resubstitution AP range | Held-out AP range |
|---|---:|---:|
| Body | 0.1741–0.2714 | 0.0037–0.0273 |
| Body + context | 0.4770–0.7326 | 0.0033–0.0171 |

Training resubstitution is a fit diagnostic, not a valid estimate of unseen-project performance. The large training/held-out gap, especially for context, is consistent with overfitting or project distribution shift; it does not by itself prove a specific cause. Aggregate context counts can encode project-specific structure. Existing extraction gaps, class/module state, generated test bodies, plugin fixtures and parameter-specific behavior are candidates for a bounded development audit.

## Sensitivity to shared source families

| Model | Family-weighted AP | Family-weighted F1 at inner-selected threshold |
|---|---:|---:|
| Body | 0.012904 | 3.71% |
| Body + context | 0.010299 | 2.89% |

Each defining source-function family has total weight one, distributed over its parameterized/inherited cases. Weighted outcome counts can therefore be fractional. Case-count/positive/prevalence fields in the sensitivity CSV describe the original unweighted corpus; weighted metrics describe the family weighting. This sensitivity also does not show a context benefit.

## Verification and saved artifacts

Pilot verification passed **63 checks**, including dataset joins, independent sklearn metric recomputation, model feature allowlists, threshold project membership and replay of all 10 saved outer models. The repository suite passed 80 tests with one Linux-only check skipped on Windows (81 discovered).

- protocol.json and run_manifest.json: frozen configuration, software/input hashes and original result checksums.
- results.json, metrics_pooled.csv, metrics_by_fold.csv, metrics_by_project.csv: all measured performance, including unfavorable results.
- oof_predictions.csv.gz: one held-out score/prediction per case for both variants and references.
- threshold_selection.csv: per-fold inner-selected thresholds and eligible training projects; inner models can be recreated from code and are not serialized.
- metrics_project_macro.csv and metrics_source_family_weighted.csv: project/family sensitivity.
- generalization_diagnostics.csv: training-fit versus held-out diagnostics.
- feature_importance.csv: fold-wise impurity importances; these can be biased and are neither SHAP explanations nor causal findings.
- error_samples.csv: deterministic high-score false positives and low-score false negatives with source references, for inspection rather than causal annotation.
- precision_recall_curve.csv.gz: pooled OOF PR points for later plotting.
- Saved outer estimators are ignored local files under local-evidence/pilot-models/pilot-v0.1; their hashes are recorded in results.json.

## Decision before final training

**This pilot is not ready to be promoted as a successful final model.** Keep it as the fixed negative reference. Next, audit a bounded development sample of missed positives/false alarms, improve context representation and resolution where supported, add simple regularized/text baselines, and tune with project-separated inner validation. Preserve natural imbalance and feature–label isolation.

All five outer folds have now been inspected. If their results influence further feature/model decisions, they are development evaluation; repeating them later is not an untouched final test. A defensible final study needs a predeclared evaluation design, with fresh independent projects/evidence if an untouched confirmation claim is desired, or explicitly development-conditioned repeated/nested evaluation with that limitation disclosed. Final deployment fitting on all cases would not itself produce an independent performance estimate.

These results concern static observed-instability prediction on the FlakeXplain corpus. They neither reproduce CANNIER’s full feature/label task nor demonstrate an improvement over its hybrid detector. Publication improvement remains unestablished.

## Reproduce

```powershell
python -m venv .venv-pilot
.\.venv-pilot\Scripts\python.exe -m pip install -r requirements-pilot.txt
.\.venv-pilot\Scripts\python.exe scripts/train_pilot.py --output reports/pilot-reproduction
.\.venv-pilot\Scripts\python.exe scripts/validate_pilot.py --run reports/pilot-reproduction
```

Use a new output directory. The runner refuses to overwrite an existing pilot. Exact wall-clock time and serialized-model bytes can differ; model score replay is checked with absolute tolerance 1e-12.
