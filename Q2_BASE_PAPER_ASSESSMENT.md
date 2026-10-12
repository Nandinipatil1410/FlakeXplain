# Q2 base-paper assessment for FlakeXplain

Prepared 5 October 2026. Submission by early November is the target. No model experiments, artifact reproduction, or project changes were performed during this search. This assessment supplements the earlier Q3 assessment and unrestricted base-paper decision; it does not turn those conditional recommendations into verified experiments.

## Decision

No fully qualified SJR-Q2 Python classifier paper with a verified reproducible experiment and demonstrated improvement opportunity was identified. This is a search result, not proof that no such paper exists.

The closest SJR-Q2 route is **Software Testing, Verification and Reliability (STVR)**, using a factors study as the same-journal foundation for a proposed new architecture. It is conditional on the college accepting a foundational empirical study rather than an existing classifier as the base paper. It cannot support a claim of beating the original paper's F1: the study supplies no such classifier baseline.

If a numerical Python classifier baseline is compulsory, CANNIER remains the technically stronger candidate, but its journal is **SJR-Q1**, not SJR-Q2. Public directories list it as JCR-Q2; that is a different ranking and does not make it an easier publication target.

## Closest SJR-Q2 pair

**Journal:** Software Testing, Verification and Reliability, Wiley. Public [SJR directory](https://www.akaturk.com/journals/20432?lang=tr) reports 2025 Q2 in Software, Media Technology, and Safety/Risk/Reliability/Quality, SJR 0.482. [JournalsBase](https://www.journalsbase.com/journals/software-testing-verification-and-reliability) agrees. These are secondary listings; current coverage, category, year, and quartile should be checked in the college's Scopus/SCImago access before formal selection. JCR is separately listed as Q3.

**Paper:** Azeem Ahmad, Ola Leifler, Kristian Sandahl (2021), [Empirical analysis of practitioners' perceptions of test flakiness factors](https://onlinelibrary.wiley.com/doi/full/10.1002/stvr.1791), volume 31, issue 8, e1791, DOI 10.1002/stvr.1791. The full publisher article was accessible.

The paper identifies 19 perceived factors across five companies and examines limited industrial test artifacts. It investigates size and assertion count as measurable properties. It does not provide a predictive ML architecture or classification benchmark. Its data-availability statement requires Software Center permission; a public replication dataset was not verified. The languages of its supplied test artifacts were not established from the article, so do not call it a Python baseline.

## Proposed extension and evaluation

Proposed working title: *Fixture-Aware and Explainable Flaky-Test Risk Prediction for Python Projects*.

Develop a static predictor that resolves each test's pytest fixtures and bounded helper context, then predicts observed-flaky risk with CPU models. Use test length, assertions, and test-body features as controls; investigate fixture scope, autouse, teardown structure, and shared-state operations as added context. These are hypotheses, not demonstrated novel features or improvements.

Evaluate on identical held-out projects:

1. Simple baselines: always-negative and training-prevalence risk.
2. Proposed size/assertion-only model motivated by the factors study. Clearly label this as your operationalization, not the authors' model.
3. Test-body token/AST classifier.
4. The same classifier with fixture/helper context.
5. A compatible published Python baseline such as a controlled CANNIER adaptation, if its artifact can be reproduced and the task aligned. This may be additional related work even when the same-journal foundation is STVR.

Report average precision/PR curves, MCC, precision/recall/F1, false positives per 1,000 negative-labelled tests, per-project results, and uncertainty. Fit all preprocessing, tuning, and thresholds on training/validation projects. Preserve natural evaluation imbalance. Never use rerun outcomes, failure frequency, seeds, or subtype labels as predictor inputs. Retain the finite-rerun caveat for negative labels.

Before experiments, audit node-ID/source mapping, parameterized duplicates and shared causes, and the confounding between reordered execution and program random-seed changes. Replay suspicious failures under controlled conditions. Static fixture context is explanatory evidence, not proof of a causal root.

CPU is sufficient for the proposed AST/scikit-learn architecture. GPUs are unnecessary for this design. LLM comparison is optional and should follow a sound core experiment rather than delay it. One month is a planning target, not a guarantee of a submission-ready research contribution.

## Journal fit and cost

The [STVR author guidelines](https://onlinelibrary.wiley.com/page/journal/10991689/homepage/forauthors.html) accept practical and theoretical research, experience papers, and software notes. That supports topical fit, not acceptance probability. They offer a standard publication licence and optional hybrid open access. The [open-access page](https://onlinelibrary.wiley.com/page/journal/10991689/homepage/fundedaccess.html) currently lists USD 2,860 before taxes for optional OA. Do not treat OA payment as compulsory. Reconfirm charges at submission.

## Alternatives screened

- **CANNIER / Empirical Software Engineering (2023):** Python, public experiment/framework repositories, CPU classifier component; strongest technical match. [Paper](https://link.springer.com/article/10.1007/s10664-023-10307-w), [artifact](https://github.com/flake-it/cannier-experiment), [ranking listing](https://avid.selcuk.edu.tr/dergiler/18650): SJR 2025 Q1, separately JCR Q2. Artifact/source joins remain unverified locally. See BASE_PAPER_DECISION.md for the proposed controlled comparison and overlap precautions.
- **SleepReplacer / Software Quality Journal (2022):** Selenium thread-sleep refactoring, not this Python risk-classification task. [Paper](https://link.springer.com/article/10.1007/s11219-022-09596-z). Category-specific rankings must not be collapsed into an unqualified Q2 claim.
- **HgtFlaky / Computers (2026):** graph-transformer/runtime evidence architecture on FlakeFlagger and IDoFT, rather than a verified Python arm. [Paper](https://www.mdpi.com/2073-431X/15/6/372). [Publisher statistics](https://www.mdpi.com/journal/computers/stats) distinguish JCR Q2 from CiteScore Q1 in main computing categories. This was not selected as a feasible matching baseline.

## Four-week scope, conditional on guide acceptance

- Week 1: validate evidence and source mapping; run project-disjoint CPU baselines; freeze evaluation protocol.
- Week 2: implement bounded fixture/helper extraction and controlled ablation.
- Week 3: complete held-out evaluation, confirmation checks, uncertainty, and failure analysis.
- Week 4: prepare manuscript and reproducibility materials, guide review, and submission.

If the pilot offers no defensible benefit or insufficient independent positive examples, narrow or revise the research question. Do not manufacture a large gain, compare scores from different datasets as improvement, or equate a new architecture with guaranteed acceptance.
