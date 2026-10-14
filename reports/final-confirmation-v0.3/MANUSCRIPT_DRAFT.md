# Bounded Static Context for Python Flaky-Test Risk Prediction: An Empirical Study

*Manuscript draft, 14 October 2026. Not submission-ready: human validation, related-work completeness, licences and independent positive confirmation remain outstanding.*

## Abstract

We investigate whether bounded pytest fixture, helper and lifecycle context improves static prediction of observed test instability across projects. We construct an evidence-backed corpus of 96,118 source-mapped Python test cases from 35 projects, including 693 cases observed to flip outcomes. We preserve natural imbalance and separate repeated-run label evidence from static predictors. A bounded development comparison shows context Extra Trees average precision of 0.0552 versus 0.0071 for a scope-aware core representation; the project-resampling interval for the difference includes zero. Prospective confirmation on three additional projects yields 2,610 eligible cases with no observed flips in 25 rounds. At frozen development-selected thresholds, core/context models flag 111/3 cases, respectively. These findings support studying context and false-alarm behavior, but cannot establish independent recall or superiority over published hybrid detectors.

## Research questions

RQ1: Does incremental bounded context improve project-separated development ranking under the same model family and candidate-selection procedure? RQ2: How do frozen models behave on prospectively selected unseen projects? RQ3: What extraction gaps and source-feature collisions limit static prediction?

## Method and results

Use FINAL_STUDY_REPORT.md, protocol.json, the immutable dataset card, nested development protocol, per-project metrics, and independent confirmation tables as the authoritative method/results material. The 30-feature core already contains two scope-aware reads; the context extension contains 96 total counts. Original detection randomization changes order and runtime seeds, so observed instability is the target and OD/NOD categories remain provisional.

## Threats to validity

Development folds influenced feature choices; the external confirmation has zero observed positives and only three selected projects. Negative labels mean not observed flaky after a finite budget. Parametrized cases share source families. Near-clone/fork checks and plugin-aware fixture resolution are incomplete. Upstream source commits are pinned; some confirmation dependencies resolve at setup and are snapshotted. Source/identity exclusions and skip-only observations remain visible. Attribution is not causal diagnosis. Different thresholds and selected class weights prevent interpreting confirmation false-alarm differences as a pure feature effect.

## Relationship to prior work

CANNIER (2023, doi:10.1007/s10664-023-10307-w) supplies the original Python hybrid-detector reference. The 2024 IEEE Access cross-project study (doi:10.1109/ACCESS.2024.3458184) motivates project-level generalization; its labelled-target transfer setting differs from our zero-target-label task. Static Test Flakiness Prediction (2022, doi:10.1007/s10664-022-10227-1) motivates static metrics but requires a language/task adaptation. Our Random Forest references are explicitly family adaptations, not reproductions of those systems. Bibliography metadata and broader related work require verification before submission.

## Conclusion

The completed study provides an audited corpus, bounded extractor, reproducible project-separated experiments and a transparent independent negative result. It offers development evidence of context-related ranking gains and descriptive external false-alarm differences. Independent recall gains, causal explanations and hybrid detection-efficiency improvements remain unestablished.
