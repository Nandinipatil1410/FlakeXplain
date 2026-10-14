# CANNIER matched baseline-versus-context experiment

Status: completed retrospective controlled ablation on the authors released feature/label corpus. This is not untouched independent confirmation or a reproduction of the complete hybrid detector.

## What is now comparable

The original release contains 89,668 cases across 30 projects. The matched cohort contains 86,781 source-mapped cases, including 157 author-labelled NOD and 1001 author-labelled victims. Both representations use exactly the same cases, author labels, project-grouped folds, model settings and sampling procedure.
Baseline: actual released 18 static/dynamic measurements, using the first stored instrumentation measurement independently of outcomes. Extension: those identical 18 columns plus 66 bounded context features. No original feature is replaced with an AST proxy.
The primary comparison preserves natural imbalance without synthetic cases or class weighting. The author-SMOTE setting is a separately declared sensitivity variable, fitted inside training partitions only. Classifiers match the published best families/tree counts: 100-tree Extra Trees for NOD-vs-rest and 75-tree Extra Trees for victim-vs-rest.

## Paired project-held-out results

| Task / training balance | Baseline AP | Context AP | AP difference | Baseline MCC | Context MCC | MCC difference |
|---|---:|---:|---:|---:|---:|---:|
| NOD-vs-Rest / natural | 0.004641 | 0.006960 | +0.002318 | 0.000000 | 0.000000 | +0.000000 |
| NOD-vs-Rest / author_smote_sensitivity | 0.005674 | 0.005984 | +0.000310 | -0.000630 | -0.000646 | -0.000016 |
| Victim-vs-Rest / natural | 0.017761 | 0.017277 | -0.000484 | -0.002433 | 0.000000 | +0.002433 |
| Victim-vs-Rest / author_smote_sensitivity | 0.026556 | 0.029918 | +0.003362 | 0.028134 | 0.089941 | +0.061807 |

MCC above uses a fixed 0.5 threshold and signed MCC. AP summarizes score ranking. Additional inner-project-OOF MCC-selected thresholds are reported in metrics_pooled.csv; they were not selected from outer-test outcomes.

## Project-resampling uncertainty

| Task / balance | 95% AP-difference interval | 95% MCC-difference interval |
|---|---|---|
| NOD-vs-Rest / natural | [-0.003877, 0.021345] | undefined |
| NOD-vs-Rest / author_smote_sensitivity | [-0.002849, 0.012295] | [-0.000683, 0.000431] |
| Victim-vs-Rest / natural | [-0.004795, 0.007752] | undefined |
| Victim-vs-Rest / author_smote_sensitivity | [-0.031934, 0.049655] | [-0.053558, 0.168858] |

Intervals use 500 paired project-bootstrap samples of fixed OOF predictions. They do not include model-refitting or prior feature-development uncertainty; two tasks and two metrics are reported without selecting a favourable winner. Project counts are small and prevalence varies.

## Original CANNIER scores recovered from its release

| Original task | Derived mean AP | Mean signed MCC | Repeats |
|---|---:|---:|---:|
| NOD-vs-Rest | 0.490934 | 0.532094 | 30 |
| NOD-vs-Victim | 0.744827 | 0.692611 | 30 |
| Victim-vs-Rest | 0.529366 | 0.519517 | 30 |
| Polluter-vs-Rest | 0.987053 | 0.945824 | 30 |

These AP values were newly computed from the authors released predictions; the paper itself reports MCC. They use the authors full task domains, original stratified case-level cross-validation, SMOTE and random single-measurement selection. They are reference verification, not matched comparison scores for our changed cohort/project-fold protocol. Released prediction MCC values reproduce the rounded paper figures.

## Scope and limitations

- The source/context design and these projects influenced earlier development. Project-held-out fitting is enforced, but the study is retrospective; it cannot substitute for untouched positive-project confirmation.
- Original author NOD/victim labels come from their 2,500 baseline/shuffle protocol. They are retained separately from our own 25/27-round instability labels. No labels were silently merged or reinterpreted.
- Source exclusions are retained per case and project. Whole-cohort baseline and matched-cohort performance cannot be interchanged. Dynamic/generated tests that cannot be mapped uniquely remain excluded from both matched models.
- The new environment uses scikit-learn 1.7.2 rather than the authors 1.0.2. Five project-grouped folds replace their stratified case-level ten folds. Fixed first-measurement selection replaces random feature sample selection. These are explicit protocol adaptations.
- Author code computes absolute MCC; this experiment retains signed MCC. No negative correlation is turned into positive performance.
- The authors framework feature-name tuple reverses the names of External Modules and Assertions relative to the SQLite/plugin numeric order. We preserve numeric measurements and use their actual SQLite column names; no values are exchanged.
- Near-clone/fork assessment, human fixture/context review and independent positive confirmation remain incomplete. Original hybrid rerunning costs were not measured again; no efficiency claim follows from offline ranking.
- No new broad workflow campaign was needed: all 30 historical source revisions and original instrumentation data were recovered. The prior independent three-project confirmation remains unchanged and zero-positive.

## Interpretation

The primary matched results are mixed or uncertain. Report the task-specific increases and regressions and their project-level intervals. They do not establish a general improvement over CANNIER; the earlier static-baseline gain is a different experiment.

Verification: 1774 checks passed, including replay of all 40 outer models, author-array/SQLite alignment, original label preservation, no project overlap, feature allowlists and training-only sampling/threshold selection.
Sources: https://doi.org/10.1007/s10664-023-10307-w ; https://github.com/flake-it/cannier-experiment/tree/b96d6ed02e98d514eb6a92ca264a082234cb9728 ; https://github.com/flake-it/cannier-framework/tree/89c74c27847474248b581b428aed2b417141296e .
