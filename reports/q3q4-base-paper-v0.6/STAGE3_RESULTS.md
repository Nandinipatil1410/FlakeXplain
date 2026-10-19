# v0.6 stage 3: MDFlaker-base comparison, verdict under the frozen rule

Run on 19 October 2026 with `scripts/mdflaker_stage3.py` and `.venv-pilot` (scikit-learn 1.7.2).
Status: **Empirically Verified**. Machine-readable output: `stage3_results.json`. The rule is in
`PROTOCOL.md`, as amended by A1 and A2. Nothing was tuned or changed after these results were seen.

Population: MDFlaker's released failed executions for spaCy and django-rest-framework (1,616 rows,
1,033 flaky). Superset was excluded under A2. The primary protocol is test-grouped stratified
10-fold CV, 30 repeats, with the same splits as the stage 2 baseline selection.

## Verdict

**The headline claim, "FlakeXplain context features improve on MDFlaker", is NOT met.**

| Rule element | Result | Met? |
|---|---|---|
| G1 (source coverage) | 95.0% mapped, 1.4 pp label gap | yes |
| G2a (implementation check) | 74.6% agreement | no: claims are "against our reimplementation of the described method" |
| C1: ET-BC vs B\* (KNN8-float) | ΔMCC **+0.072** [+0.059, +0.085], ΔF1 +0.019 [+0.013, +0.026] | **yes** |
| C2: ET-BC vs ET-B (context contribution) | ΔMCC **−0.036** [−0.053, −0.019] | **no** (context makes the model worse) |
| No degradation per project | spaCy +0.103, DRF +0.051 vs B\* | yes |
| Robust (beats B\* in both projects) | yes | yes |

Under the partial-outcome wording frozen in `PROTOCOL.md`, the allowed statement is:

> On MDFlaker's released data for spaCy and django-rest-framework (1,616 failed executions; Superset
> source unretrievable), Extra Trees on MDFlaker's own features outperforms our reimplementation of
> its KNN (MCC 0.534 → 0.642). Adding FlakeXplain's static context features gives **no** further
> gain; under test-grouped evaluation it significantly **reduces** MCC (0.642 → 0.606).

The C1 gain comes entirely from replacing KNN with Extra Trees, not from FlakeXplain's features.

## Primary results (mean over 30 repeats, 95% repeat interval)

| Arm | MCC | F1 | AP | Precision | Recall | MCC spaCy | MCC DRF |
|---|---|---:|---:|---:|---:|---:|---:|
| KNN-B\* (KNN8-float) | 0.534 [0.523, 0.545] | 0.825 | 0.865 | 0.843 | 0.809 | 0.399 | 0.724 |
| ET-B (authors' 5 features) | **0.642** [0.630, 0.654] | 0.864 | 0.925 | 0.887 | 0.842 | 0.526 | 0.815 |
| ET-BC (+ 66 context + indicator) | 0.606 [0.596, 0.616] | 0.844 | 0.879 | 0.885 | 0.807 | 0.502 | 0.775 |

## Secondary analyses (reported, cannot rescue the headline)

- **S1, the authors' row-level split:** KNN-B\* 0.752, ET-B 0.838, ET-BC **0.905**. Here context
  appears to help (+0.067 [+0.065, +0.069]). ET-BC has the largest gap between row-level and grouped
  scores (+0.299, against +0.196 for ET-B). This is the memorization shortcut the protocol
  anticipated: context features are constant per test, so the forest learns test identity across
  builds. **A row-level evaluation would have produced a spurious "context helps" result.**
- **S2, leave-one-project-out** (MCC, test spaCy / test DRF): the paper's own method MDF-paper-int
  scores 0.442 / 0.824, KNN-B\* 0.348 / 0.625, ET-B 0.353 / 0.250 and ET-BC 0.349 / 0.326.
  **Across projects, the base paper's conditional rule beats all our forests**, so the C1 advantage
  does not transfer to an unseen project.
- **S3, baseline variants:** see `STAGE1_2_RESULTS.md`. The paper's method (0.526) and B\* (0.534)
  are close.
- **S4, static-only** (smells, size, context; no history or traceback): MCC 0.205, which is 0.329
  below B\*. Static test code alone predicts this task poorly.
- **S5, transfer prior from the 96,118-case corpus** (94,716 training cases with DRF removed, 692
  positives): adding the prior score to ET-BC changes MCC by −0.037 [−0.046, −0.028].
- **S6, Random Forest:** RF-B 0.638 and RF-BC 0.605. Context changes MCC by −0.033 [−0.045, −0.021].
  The pattern is the same as with Extra Trees.

## Interpretation

- MDFlaker's task is deciding whether a given **failed execution** is flaky. Its strongest signals
  are per-execution history and change data: flaky frequency, previous state and traceback coverage.
  Static fixture and helper context describes the *test*, not the *failure*, so it adds noise on
  this task once memorization is blocked.
- This is consistent with v0.4 and v0.5: FlakeXplain context helps within-project and test-level
  prediction (v0.5 CANNIER protocol), but it does not establish cross-project or failure-level gains.
- Limits: 2 projects, 481 test groups, labels from 2020 Travis reruns, a failed G2a, and a
  retrospective analysis on released data.

## Consequence for the paper

MDFlaker does **not** provide a base paper over which FlakeXplain's contribution, the context
features, improves. The only defensible improvement, Extra Trees over KNN, is a classifier swap, and
it disappears across projects. CANNIER v0.5 remains the stronger story: all four tasks improved, one
cleared the frozen threshold, and the cost rule was met. Its base paper, however, is in a Q1 journal.

## Reproduction note

Stage 1 was rerun to add `features_body.csv.gz`, which S5 needs. The decompressed content of
`metadata.csv.gz` and `features_context.csv.gz` is byte-identical to the stage 2 inputs. Only the
gzip container bytes differ, so `stage2_summary.json` records the earlier container hash.
`stage3_results.json` records the current hashes.
