# FlakeXplain: Q3-only base-paper assessment

Prepared 5 October 2026. Scope: a Scopus-indexed journal, Q3 preference now treated as a search restriction, and a base paper from that same journal. Approximately one month is available. CPU-based work is preferred. This document supersedes the journal recommendation in PUBLICATION_RESEARCH_PLAN.md.

## Decision and verification status

**No fully qualified pairing has been verified.** The closest candidate is **Software Impacts + MDFlaker**, but it is a lead requiring a reproduction and task-alignment check, not a confirmed one-month improvement plan. Do not commit the project to it solely because its journal is Q3.

Searches covered Python flaky-test prediction/detection, Q3 software journals, relevant publisher records, author repositories, and related-work surveys. A negative search result does not prove that no suitable paper exists. It means this review has not established one meeting all the requirements together.

Q3 here means **SJR, Software category** unless the college specifies another metric. The [RC SI journal registry](https://journalrank.rcsi.science/ru/record-sources/quartiles/19821/) lists Software Impacts as SJR Q3 for 2025 and 2024, and CiteScore Q3 for 2024. This is secondary ranking evidence. Before submission, verify active Scopus coverage and the required metric/year with the college library, using ISSN 2665-9638 and source ID 21101060167. Do not equate SJR, CiteScore, and JCR quartiles. The [direct SCImago entry](https://www.scimagojr.com/journalsearch.php?q=21101060167&tip=sid) could not be retrieved in this review.

## Closest candidate

**Azeem Ahmad, “MDFlaker: A tool for multi-factor detection and root cause analysis of flaky tests,” Software Impacts, volume 26, article 100794 (2025), DOI 10.1016/j.simpa.2025.100794.**

The [publisher record](https://www.sciencedirect.com/science/article/pii/S2665963825000545) describes conditional KNN classification using traceback coverage, test smells, flakiness frequency, and test size. The author's [earlier thesis](https://www.diva-portal.org/smash/get/diva2%3A1689526/FULLTEXT02.pdf) establishes a Python MDFlaker implementation and links its [GitLab artifact](https://gitlab.liu.se/azeah70/multifactorftdetector). That artifact was not retrievable through the available web tools. The full 2025 article and its current executable/data were not obtained. Earlier conference/thesis performance numbers must not be attributed to the 2025 journal article.

### Why this is not yet a safe baseline

FlakeXplain currently labels tests from repeated executions at a fixed commit. Its planned predictor uses static source context and permitted single-run measurements. A failed-execution diagnosis task instead requires examples of both flaky failures and genuine regression failures, with appropriate historical context. Consistently passing tests cannot substitute for genuine regression failures.

If MDFlaker's released experiment is this failure-level task, implementing it would require a separate historical-failure dataset and a separate evaluation. It cannot be compared directly with FlakeXplain's current binary corpus. The exact 2025 target and eligibility rules need to be checked in the full paper and artifact before finalizing this conclusion.

Using rerun-derived flaky frequency as a FlakeXplain predictor input would violate feature-label isolation. Removing such inputs and changing the target produces an **adapted baseline**, not a faithful reproduction. Merely implementing KNN and calling it MDFlaker is not acceptable.

## Candidate screening

| Candidate | Evidence and fit | Decision |
|---|---|---|
| Software Impacts / MDFlaker (2025) | Closest Python lead; ranking evidence above. Current executable, data, and full journal method unresolved; likely task mismatch needs confirmation. | Conditional lead only. |
| Science of Computer Programming / JS-TOD (2026) | [Published paper](https://mro.massey.ac.nz/server/api/core/bitstreams/9d1605d6-737d-4379-afd7-eda1a272a405/content) concerns Jest/JavaScript test ordering. | Withdrawn as the primary Python comparison. |
| Journal of Web Engineering / FlakyLoc (2020) | [Publisher paper](https://journals.riverpublishers.com/index.php/JWE/article/view/3361) addresses localization in web applications. | Does not match the current pytest risk-prediction experiment. |
| IJSEKE / adaptive latest-position detection (2024) | Concurrent Android event scheduling, rather than Python test-source prediction. | Requires a substantial ecosystem and task change; unsuitable for this month. |
| IJCESEN / Flaky Test Automation and Mitigating Test Crashes in Agile Releases (2025) | [Publisher record](https://www.ijcesen.com/index.php/ijcesen/article/view/3644) presents mitigation guidance and rerun heuristics. A reusable, matching empirical classifier baseline was not established. | Not selected; current Q3 eligibility also unverified. |

The table does not certify the current quartile of every rejected journal; methodological mismatch already rules those papers out. Empirical Software Engineering/CANNIER and IEEE Access classifier papers are excluded from the current Q3-only shortlist. Conference papers such as FLAKE16, FlaPy, and iPFlakies can support related work or additional comparisons but do not satisfy the same-journal base requirement.

## Feasible work to preserve while the base is unresolved

These are **proposed changes**, not implemented features or verified improvements:

1. Export a versioned dataset with canonical node IDs, source identities, pinned commits, environment manifests, per-test effective observation counts, and evidence references. Keep failure-only and skip-only cases unlabelled.
2. Separate execution-order shuffling from program RNG reseeding. Use a private RNG for shuffling; apply the same runtime seeding policy across compared conditions. Confirm suspected OD cases by replay before asserting causality.
3. Extract bounded static context from tests, fixtures, and helpers. Candidate features include fixture scope/autouse, teardown structure, shared state, filesystem operations, and time/randomness dependencies. Record unresolved context rather than guessing.
4. Train modest CPU models and compare test-only versus fixture-aware inputs on exactly the same project-disjoint folds. Preserve natural test-set prevalence. Fit preprocessing and choose thresholds using training/validation projects only.
5. Evaluate average precision, precision/recall/F1, MCC, false positives per 1,000 negative-labelled tests, and recall among the highest-ranked 10%. Report per-project results and uncertainty. Keep SHAP attribution distinct from confirmed failure causes.

These changes may support an original software architecture route if the guide accepts that route against a same-journal reference. They do not establish novelty or superiority by themselves. A related-work check and actual comparative experiments remain necessary.

The current local report states 127 observed-flaky cases and 14,640 not-observed-flaky cases across 10 completed projects; these are report-derived counts, not a new raw-evidence audit. Parameterized instances may share causes. The reported one NOD example cannot support a separate NOD classifier. Selected projects do not represent Python-wide prevalence.

## One-month feasibility gate

Before choosing MDFlaker, spend at most two working days on:

- Obtaining the full journal article and the associated released implementation/data through existing public or college-library access. No author contact has been made.
- Verifying the target, feature definitions, available input timing, split protocol, licensing, and mapping from released examples to source.
- Reproducing a small CPU experiment under documented dependencies and recording actual runtime and memory.
- Confirming that a fair comparison can use one shared dataset, task, and evaluation protocol without violating the project's feature-label rules.
- Checking that the guide accepts Software Impacts' original software article type for credits and that current publication charges are affordable. Current fees were not independently verified.

If those checks fail, MDFlaker is not a feasible direct-improvement base for the present deadline. Do not spend the remaining month reconstructing unavailable history/data, silently change the task, or promise better results. A GPU is not required for the proposed static extraction and classical models; dataset reconstruction and reproduction are the principal risks.

If the gate succeeds, allocate the remaining weeks to one focused extension and ablation, frozen evaluation and error analysis, then the manuscript and reproducible artifact. Treat one month as a research/submission window. Acceptance and publication within that month are not established.

**Recommended action:** retain Software Impacts/MDFlaker as the closest Q3 lead; keep the final base-paper selection open until the artifact and task checks pass. No improvement percentage or journal acceptance probability can be promised from this review.
