# FlakeXplain publication decision and implementation plan

> **Latest assessment, 5 October 2026:** The user has reopened journal selection without a Q3 restriction and clarified that submission by November is sufficient. See [BASE_PAPER_DECISION.md](BASE_PAPER_DECISION.md). CANNIER is the preferred technical candidate, conditional on a reproduction/source-mapping pilot; no performance gain or acceptance is established. The previous JS-TOD recommendation remains withdrawn. The older decisions below are retained as research history, not the current recommendation.

> **Superseded recommendation, 5 October 2026:** The user has requested a Q3-only search. JS-TOD is withdrawn as the recommended base because its JavaScript detector does not provide a matching Python classifier experiment. CANNIER is also excluded from the current journal shortlist because its journal is Q1 by SJR. See [Q3_BASE_PAPER_ASSESSMENT.md](Q3_BASE_PAPER_ASSESSMENT.md) for the current assessment. The implementation ideas below remain proposals; the earlier journal decision and direct-base comparison discussion must not be treated as an approved publication plan.

Prepared 5 October 2026. This is a researched proposal, not a record of completed experiments or a promise of acceptance. No pipeline code or empirical evidence was changed during this review.

## Decision

Preferred pairing: **Science of Computer Programming**, Elsevier, and **JS-TOD: Detecting order-dependent flaky tests in Jest**, Hashemi et al., 2026, volume 252, article 103462, DOI [10.1016/j.scico.2026.103462](https://doi.org/10.1016/j.scico.2026.103462). The [published version is freely accessible](https://mro.massey.ac.nz/server/api/core/bitstreams/9d1605d6-737d-4379-afd7-eda1a272a405/content), and the [authors' implementation is public](https://github.com/Negar-Hashemi/JS-TOD).

This pairing fits the **new architecture** route. It does not establish that a Python classifier beats the paper's JavaScript detector. Porting reruns into Python alone is insufficient novelty; Python detectors already exist.

Two eligibility conditions remain: the college must accept Original Software Publications for project credits and accept SJR Q3 for a Scopus-indexed journal. The [RC SI quartile registry](https://journalrank.rcsi.science/ru/record-sources/quartiles/19366/?order=Desc&page=1&pagesize=50&sort=Year) lists SJR Software Q3 for 2025 and 2024, but CiteScore Software Q2 for 2024. This is a secondary registry, not direct authenticated Scopus verification. Confirm active indexing and the required quartile year/category through the college library using Scopus source ID 28416 and ISSNs 0167-6423 / 1872-7964. Do not call it unconditionally "CiteScore Q3."

The [publisher describes a software track](https://shop.elsevier.com/journals/science-of-computer-programming/0167-6423). Its [2025 editor-authored call](https://eapls.org/news/issues/open-call-for-software-submissions-science-of-computer-programming-software-track-xjw27/) describes review of the software, documentation, reproducibility, and a short accompanying manuscript. Check the current author guide before preparing the submission. Current author charges and article-type-specific subscription eligibility were not independently verified; do not assume either free publication or a particular APC.

Backup: **Software Impacts** with Ahmad's **MDFlaker: A tool for multi-factor detection and root cause analysis of flaky tests**, 2025, volume 26, 100794, [DOI 10.1016/j.simpa.2025.100794](https://www.sciencedirect.com/science/article/pii/S2665963825000545). The publisher abstract was accessible, but its full text and current artifact were not retrieved during this review. Do not lock a faithful reproduction plan or quote its performance without those materials. It also requires checking software article eligibility, current fees, and the ranking scheme. A simplified KNN comparator would be an adapted baseline, not a reproduction of MDFlaker.

## What the present project actually supports

Implemented: pinned-environment setup, passing baseline gate, original/random/reverse rerun orchestration, XML parsing, and reports. No classifier training, SHAP pipeline, fixture feature extractor, or LLM evaluation implementation was found in the inspected project files.

The current local report states 10 repositories with completed rounds, 15,679 collected tests, 127 observed flaky tests, 14,640 not-observed-flaky tests, and 912 unlabelled tests. The 0.86% figure is 127 / 14,767 labelled tests. It reports 126 OD and one NOD; these are provisional classifications, not separately verified causal conclusions. These counts are report-derived: raw XML and environment provenance were not independently revalidated in this review. Older project context and selection documents still refer to 50 positives and seven projects.

The positive corpus is small and concentrated in a few projects. Parameterized cases can share one underlying cause. Deliberate project selection enriches the corpus for known flakiness, so its percentage is not an estimate of flakiness across Python software generally. One NOD example cannot support a meaningful NOD classifier or reliable NOD performance estimates.

## Proposed contribution

Working title: **FlakeXplain: Fixture-Aware, Explainable Flaky-Test Risk Prediction with Reproducible Pytest Evidence**.

The contribution to investigate is the practical value of fixture context for predicting observed flakiness on unseen projects, combined with carefully separated rerun evidence and developer-facing explanations. Adding SHAP, an LLM, or a new language individually is not enough to establish research novelty. A focused related-work check must cover fixture-aware prediction specifically before making a novelty claim.

Two separate paths:

1. Pinned source + test + fixture/helper context -> static features -> risk score -> feature attribution.
2. Pinned environment + execution permutations -> actual outcomes -> observed labels -> confirmation replay -> diagnostic evidence.

Rerun outcomes, failure counts, flip counts, seeds, OD classifications, and label-derived annotations stay out of predictor inputs. Diagnostic outputs may show execution evidence, but that evidence cannot be silently fed back into a pre-execution predictor. SHAP explains a model score; it does not establish the cause of a failure.

## Priority changes and suggested files

| Priority | Files | Work and acceptance condition |
|---|---|---|
| Required | `scripts/idflakies_runner.py`, new `scripts/order_plugin.py` | Separate order randomization from program RNG reseeding. Use a private RNG for shuffling pytest items, record canonical collected IDs and full execution order, and keep runtime seeding identical across order conditions. Test a separate reseeding arm only when needed. |
| Required | `scripts/parse_results.py`, new `scripts/confirm_flakiness.py` | Preserve observed outcome flips separately from provisional subtype. Replay failing permutations under the same environment, compare original order, and investigate isolation/predecessors before confirming OD. Leave unresolved cases unresolved. |
| Required | New `scripts/export_dataset.py` | Export exact commit/environment, canonical node ID, source-function identity, source hash, per-test effective observations, label, evidence paths, and verification status. Exclude incomplete, ambiguous, skip-only, and failure-only records from binary supervised targets. Preserve raw artifacts. |
| Required | New `scripts/extract_features.py` | Extract test-body metrics plus bounded fixture/helper context; record unresolved fixtures. Inspect fixture scope/autouse, cleanup, shared mutable state, monkeypatch/mock usage, filesystem/network/time/randomness operations, and fixture dependency structure. Start with static-only inputs. |
| Required | New `scripts/train_evaluate.py` | Implement reproducible project-disjoint evaluation, simple models, train-only preprocessing and threshold selection, prediction export, and honest per-project results. |
| Required | New `scripts/explain_predictions.py` | Show source-linked feature evidence and limited SHAP/rule explanations. Keep model attribution separate from replay-backed diagnoses. |
| Required | Existing reports and documentation | Reconcile stale counts; audit implausible 0.03-second total execution times reported for click/flask; publish verified timing only. |
| Optional | New `scripts/llm_benchmark.py` | Fixed prompt/model/date, identical source-context budget, structured responses, caching, token/cost accounting, and project-disjoint evaluation. Pilot before running the full imbalanced corpus. |

Maintain passing-baseline integrity, the specified PYTHONPATH, `-p no:cov`, and in-memory reversal. Do not alter upstream tests merely to make baseline failures disappear. Distinguish new evidence from legacy artifacts without manifests. Preserve the original corpus as a version; corrections may change the final counts.

For confirmation and cause annotation, start with distinct source-test/cause families rather than all 127 parameterized instances. Record a bounded, declared sample, selection method, reviewer agreement, and actual verified cases. Do not promise a fixed number of confirmed positives before replay. If confirmations collapse into too few independent causes or projects, narrow the paper's claims instead of duplicating data.

## Evaluation that can support the paper

Freeze the evaluation protocol before model comparison. Use leave-one-project-out outer evaluation across eligible repositories, with inner project-grouped validation where feasible for thresholds and tuning. All parameterized variants and near-duplicates stay in the same group. Correlated upstream/downstream projects may need grouping together. Preserve naturally observed class ratios; class weights are allowed without synthetic examples or duplicated tests.

Compare a prevalence/random ranking reference, a simple code-size heuristic, TF-IDF + logistic regression on test bodies, static test-body logistic regression/random forest, and the same models with fixture context. Keep the model family fixed for the principal context ablation. Fit TF-IDF vocabulary, imputers, scalers, and thresholds only on training folds. LLM comparison is optional and must not replace classical baselines.

Report average precision (define whether this is the chosen PR-AUC summary), precision, recall, F1, false positives per 1,000 negative-labelled tests, and recall among the top 5%/10% ranked tests. Report pooled and project-level results, including false positives on projects with no observed positives. Positive-class recall is undefined on those projects; do not assign a misleading zero or omit their false positives. Report uncertainty at project/cause-family level and acknowledge the small number of clusters.

At this prevalence, always predicting the negative label yields about 99.14% accuracy. Accuracy alone is therefore not persuasive evidence.

The main hypotheses are that fixture context improves ranking on held-out projects and that bounded, source-linked explanations are useful. No improvement percentage, F1 value, or acceptance likelihood is established yet. Require gains against relevant baselines under the same protocol, and publish regressions and limitations as well as gains.

For a numerical comparison to the selected detector paper, distinguish three things: the published JavaScript results; an explicitly named Python adaptation of its reorder/rerun strategy; and FlakeXplain's predictor. The predictor and detector do different jobs. Do not compare their accuracies directly. A Python adaptation must be described as an adaptation, not the original executable. A direct original-tool comparison would require shared Jest workloads, which is a separate scope expansion.

Do not make adaptive ML-guided rerunning the core one-month requirement. Running only a high-risk test in isolation can remove the polluter and hide order-dependent failures. Any later rerun-efficiency experiment must retain relevant execution context, compare equal CPU/time budgets, use independent confirmation evidence, and measure detection yield or time to first confirmed failure. Otherwise, present ML as developer triage.

## Four-week execution plan

| Dates | Main deliverable |
|---|---|
| Oct 5-11 | Guide/library eligibility check; frozen source/evidence inventory; ordering-vs-seeding correction; canonical IDs; confirmation pilot and related-work matrix. |
| Oct 12-18 | Dataset export, fixture extraction, static baselines, first project-disjoint context ablation. Decide whether evidence supports the proposed contribution. |
| Oct 19-25 | Frozen evaluation, bounded confirmation/cause annotations, explanations, failure analysis, optional small LLM benchmark if the core work is complete. |
| Oct 26-Nov 1 | Manuscript, figures/tables from actual outputs, versioned public artifact, reproduction instructions, guide review, and submission if eligibility and evidence are satisfactory. |

Suggested division for four students: evidence/provenance; fixture extraction; evaluation/explanations; related work/artifact/manuscript. Cross-review labels and experimental scripts so the same person is not the only judge of their own evidence.

No GPU is necessary for this plan. AST parsing, logistic regression, random forests, and bounded SHAP explanations run on CPU. Hosted LLM inference does not require a local GPU but can incur fees. Repeated full test suites are likely the main computational cost; CPU capacity, compatible operating environments, storage, and reliable run time matter more than GPU availability. Do not fine-tune a large model for this deadline.

The achievable target is a completed, defensible experiment and submission-ready paper. Journal acceptance/publication by early November is outside the team's control. Establish whether credits require submission, acceptance, online publication, or actual Scopus indexing of the article.

## Additional sources and exclusions

- [CANNIER study, Empirical Software Engineering, 2023](https://link.springer.com/article/10.1007/s10664-023-10307-w): Python ML-assisted rerunning is prior work; do not claim to introduce that general idea.
- [pytest-randomly documentation](https://github.com/pytest-dev/pytest-randomly): its behavior includes both ordering and RNG reseeding; this supports the current protocol audit.
- [FlakyLoc, Journal of Web Engineering, 2020](https://journals.riverpublishers.com/index.php/JWE/article/view/3361): environmental failure localization would require a substantial web-testing scope change. The journal's [official charge page](https://journals.riverpublishers.com/index.php/JWE/charges) lists EUR 1,850. This is a poor practical choice for the present deadline and unknown budget.
- [Software Impacts template](https://legacyfileshare.elsevier.com/promis_misc/SIMPAC_Article_Template.pdf): a software publication format; the available template is older and should not substitute for checking the current guide.

Using a same-journal base paper meets the stated college constraint if the guide agrees. It does not guarantee novelty, acceptance, or credits. The defensible choice is driven by fit, accessible methods/artifacts, attainable validation, and transparent limits, rather than selecting a weak benchmark to promise large gains.
