# FlakeXplain base-paper decision without a Q3 restriction

Prepared 5 October 2026. Submission by November is sufficient according to the user. A base from the intended journal remains a college requirement. No classifier experiments were executed during this assessment.

## Recommendation and limits

Preferred technical candidate: **CANNIER**, the approach in Parry et al. (2023), [Empirically evaluating flaky test detection techniques combining test case rerunning and machine learning models](https://link.springer.com/article/10.1007/s10664-023-10307-w), Empirical Software Engineering 28, article 72, DOI 10.1007/s10664-023-10307-w.

Focus the proposed extension on the **Victim-vs-Rest classifier component**. The paper already uses SHAP, so adding explanations alone is not a new contribution. Extending that component does not establish improvement over the complete hybrid detector.

The journal is listed as SJR Software Q1 for 2025 by [Selcuk University's journal database](https://avid.selcuk.edu.tr/dergiler/18650). Confirm current Scopus coverage through the college library. This is a demanding publication target: selecting a paper from it is not evidence that the eventual submission will be accepted.

The [publisher](https://link.springer.com/journal/10664/how-to-publish-with-us) offers subscription publication with no APC, alongside optional paid open access. Its [journal page](https://link.springer.com/journal/10664) reports a median 24 days to first decision. That is not a guarantee of acceptance or completion of review in 24 days. Submission by November is the planning target.

## Why this is more reproducible than the Q3 leads

The authors publish an [experiment repository](https://github.com/flake-it/cannier-experiment), including an output archive, and a [framework](https://github.com/flake-it/cannier-framework). Their documentation provides separate feature arrays and label/evidence metadata. The original environment was Ubuntu 20.04/Python 3.8; compatibility with the current Windows/Python environment has not been tested.

Use the released benchmark rather than recreate its full rerun campaign. Availability of a repository is not the same as a successful reproduction: archive contents, dependencies, and row-to-source mapping still require local verification.

## Proposed contribution

Investigate whether bounded static fixture/helper context improves order-dependent flaky-test risk prediction on projects absent from training. Compare the same model family and evaluation protocol with and without that context. The benefit and novelty remain hypotheses.

Suggested architecture:

Pinned source -> test/fixture/helper resolver -> numeric features -> CPU classifier -> risk ranking and source-linked explanations.

Keep a separate evidence path:

Pinned environment -> controlled execution orders -> observed outcomes -> labels and confirmation replay.

Candidate added inputs are fixture scope/autouse, teardown structure, shared-state operations, filesystem/time/randomness dependencies, and fixture dependency structure. Report unresolved context and extraction coverage. Do not claim these features prove a root cause.

## Fair comparison

1. Validate released row-to-node-ID/source mapping and exact commit retrieval before building fixture augmentation.
2. Establish one shared task and eligibility cohort. The project's passing baseline gate may exclude cases admitted by the authors' labels; document exclusions and apply identical eligibility to every compared model.
3. Reproduce a bounded classifier experiment, clearly separating the original protocol from the proposed project-disjoint protocol.
4. Under the new protocol, compare a controlled baseline adaptation and its fixture-augmented counterpart on exactly the same held-out examples. If sampling, features, or splits change, call it an adaptation rather than an exact reproduction.
5. Preserve naturally observed evaluation prevalence. The published pipeline uses SMOTE; the primary FlakeXplain protocol should use no synthetic or duplicated examples. Any investigation of sampling would need to be an explicitly identified experiment variable, consistent with AGENTS.md.
6. Use static inputs and at most one permitted baseline feature measurement for the primary prediction experiment. Never feed rerun counts, outcome flips, labels, seeds, or subtype annotations into the feature matrix. Choose measurements independently of outcomes.
7. Fit preprocessing, tuning, and thresholds only on training/validation projects. Keep related projects, parameterized variants, and near-duplicates appropriately grouped.
8. Report average precision, MCC, precision/recall/F1, false positives per 1,000 negative-labelled cases, and recall among the highest-ranked 10%, with per-project results and uncertainty. Do not claim improvement by comparing a new dataset's score against a published score from another protocol.

**Verified overlap requiring attention:** the current FlakeXplain report lists IPython at 95d2b79a2bd889da7a29e7c3cf5f49c1d25ff43d and Loguru at f31e97142adc1156693a26ecaf47208d3765a6e3. Both exact commits also appear in the authors' [subjects.json](https://github.com/flake-it/cannier-experiment/blob/main/subjects.json). Re-executing them does not make them an independent source-code benchmark. Hold each whole project out of training when evaluating it and explicitly report overlapping evidence.

## Required project changes

- Add dataset export and canonical source identity/provenance mapping.
- Separate order shuffling from runtime RNG reseeding and replay suspected OD failures before confirming the subtype.
- Implement bounded static fixture extraction and validate its resolution on a declared sample.
- Implement CPU baselines and shared project-disjoint evaluation with a fixture-context ablation.
- Export reproducible predictions, uncertainty, extraction coverage, and error analysis.
- Add limited SHAP/source-linked explanations after the comparison works.

Maintain the passing baseline gate, prescribed PYTHONPATH, -p no:cov, and in-memory reversal. Preserve raw evidence and its version history. LLM evaluation and neural-model training are optional; they should not consume the core month.

## Feasibility gate and schedule

**First 2-3 working days:** load the archive, check provenance and source joins, run a small classifier comparison, measure runtime/memory, and test fixture resolution. Reject this extension if the source joins cannot be established reliably within that time. A GPU is unnecessary for the proposed classical-model experiment.

**Remainder of week 1:** establish a baseline and a bounded fixture-context pilot. Decide whether the effect and extraction coverage justify the remaining work. No gain has been observed yet.

**Week 2:** complete the extractor and freeze the shared evaluation protocol.

**Week 3:** complete comparative evaluation, confirmation sample, and error analysis; report negative results as well as improvements.

**Week 4:** prepare the manuscript and reproducible artifact, obtain guide review, and submit if the evidence supports the claims. Writing methods and related work can proceed alongside implementation.

The current corpus is small and cause-correlated; one reported NOD example is insufficient for a separate NOD classifier. Do not substitute high overall accuracy for positive-class evidence. A focused contribution with rigorous validation is the aim, not an unverified promise of a new architecture or large performance gain.

**Decision:** select CANNIER for the feasibility pilot, not as a guarantee of publication. Definitive journal commitment should follow the pilot and assessment of the resulting contribution.
