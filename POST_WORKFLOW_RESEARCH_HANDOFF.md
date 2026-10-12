# FlakeXplain: research handoff after workflow completion

Prepared 11 October 2026 from the user's agreed research direction.

## Activation and objective

When the user says the workflow runs are complete and asks to begin this plan, use this file as the implementation handoff. Creating this file does not authorize starting experiments now. Follow AGENTS.md and preserve unrelated local changes and original evidence.

Objective: develop and evaluate a defensible extension to the classifier component of CANNIER, investigating whether bounded static pytest fixture/helper context improves flaky-test risk prediction on unseen projects. Prepare a reproducible artifact and submission-ready manuscript if the evidence supports the contribution.

This is a proposed research plan, not a demonstrated improvement or guarantee of publication. Clearly distinguish Proposed, Implemented, and Empirically Verified throughout reports. CANNIER already uses ML-assisted rerunning and SHAP; neither adding SHAP nor executing more repositories alone establishes novelty. Improving a classifier does not establish improvement over the complete hybrid detector.

## User priorities

- Reuse completed workflow evidence. Do not restart the full campaign by default.
- The user has limited time and requests full workflow runs rather than baseline-only diagnostic workflow dispatches when a workflow execution is necessary.
- Use eligible repositories both inside and outside CANNIER's dataset.
- Prioritize evidence quality, static feature extraction, fair comparisons, and writing. LLM experiments are optional after the core comparison works.
- Do not promise that existing runs satisfy every possible research claim. Establish sufficiency through an artifact audit.

## Phase 1: preserve and audit completed evidence

1. Inventory workflow runs and downloadable artifacts, recording repository, run URL/ID/attempt, workflow commit, execution mode, status, and artifact identifier. Download artifacts before their actual retention expiry; do not assume they remain indefinitely available.
2. Preserve original downloads unchanged, record archive checksums, and extract into separate evidence directories. Keep failed/incomplete attempts distinguishable from accepted evidence. Avoid accidentally combining rounds from different environments or attempts.
3. Audit each subject for a passing baseline, the intended 12 original + 12 random + 1 reverse rounds, valid nontruncated JUnit XML, execution manifest, environment identity, pinned subject commit, dependency/setup recipe, logs, and provenance. Verify actual per-test observations and identities, not just aggregate counts or a green workflow badge.
4. Inspect the actual packaging implementation and archives. The inspected packager copies allowlisted results/logs, environment and setup/baseline states, dependency snapshot, recipe, provenance, system packages, and checksums. It does not package the full upstream source tree. Retrieve source at the exact recorded commit for feature extraction; do not substitute current upstream HEAD.
5. Produce an audit table with accepted, incomplete, baseline-failed, ambiguous, and unavailable evidence, plus reasons and any recoverable gaps. Do not silently exclude projects or invent missing observations.
6. Resolve conflicting historical report counts from audited raw evidence. Do not treat figures in AGENTS.md or older planning documents as current verified totals.

Deliverables: evidence inventory, immutable archive/checksum manifest, audit report, accepted cohort definition, and explicit remaining gaps.

## Phase 2: freeze the dataset and task

Export a machine-readable dataset containing project, exact commit, environment identity, canonical test identity, parameterized identity, source-function identity/location/hash, observation counts by outcome/configuration, label, evidence references, and verification status. Keep label/evidence fields separate from predictor feature tables.

- Observed flaky: at least one PASS and one FAIL/ERROR under the audited protocol.
- Negative target: not observed flaky after the recorded effective N observations; never describe it as proven non-flaky.
- Exclude skip-only, failure-only, missing/ambiguous identities, and incomplete observations from the primary binary target according to a declared rule. Retain them in the audit and document exclusions.
- Preserve parameterized cases without synthetic duplication. Account for shared source functions, near-duplicates, and cause families when assessing independence.
- Labels from released CANNIER data and freshly observed labels may have different semantics and execution budgets. Record their origin and align tasks explicitly; do not merge them as interchangeable ground truth.

Primary feasible task: predict observed outcome instability from static source context. A victim-vs-rest task is appropriate only if victim labels are sufficiently verified and aligned with the baseline. A generic observed-flaky classifier must not be presented as an exact reproduction of CANNIER's victim classifier.

## Critical limitation: ordering and random seeding

The inspected runner uses pytest-randomly for random rounds and disables it for original/reverse rounds. pytest-randomly can change both test order and runtime random seeds. A failure only in random rounds therefore does not establish an order dependency.

Keep existing observed-flaky evidence. Treat inferred OD/NOD subtypes as provisional unless confirmation supports them. Confirm that a seed and XML alone allow reconstruction before claiming exact replay: inspect whether canonical collection and actual execution order were recorded, including relevant plugins and parallel execution.

Choose claims proportionate to the evidence:

- Existing complete evidence can support prediction of instability observed under the specified protocol, with its limitations disclosed.
- Confirmed OD or causal claims may require controlled executions preserving relevant predecessors, order, environment, and runtime seeding. A single test passing in isolation does not disprove order dependence.
- If confirmation is needed, define a bounded sample and protocol, and report unresolved cases honestly. Do not automatically repeat all projects.
- A separate pure-order experiment must control runtime seeding independently of shuffling and record execution order. Do not retroactively describe old rounds as pure-order experiments.

## Phase 3: use both repository groups fairly

Verify membership against the authors' actual released subject inventory and exact revisions. Do not infer membership from a project name alone.

1. Shared CANNIER projects: compare a compatible baseline and the extension on identical eligible examples, documenting overlap, protocol changes, and exclusions.
2. Additional projects: assess generalization beyond CANNIER's subject set. Run both models on the same additional examples.

For a clean external evaluation, train/tune on eligible CANNIER projects, freeze feature definitions, hyperparameters, thresholds, and any prompts, then evaluate on the additional projects. If those projects influenced development, report that and use project-disjoint/nested evaluation rather than calling them untouched external validation.

Keep whole projects out of training when evaluating them. Group forks, closely related projects, duplicated source, and parameterized variants appropriately. Declare project inclusion criteria based on evidence quality, not model performance or presence of positives. Keep eligible projects with zero observed positives to assess false alarms; recall for their positive class is undefined.

Additional projects are valuable evaluation data, but their presence alone does not prove dataset novelty or independence from other published benchmarks. Describe the execution protocol, selection process, overlap, and coverage accurately. Do not generalize corpus prevalence to all Python software.

## Phase 4: implement static features and controlled baselines

Retrieve pinned sources without executing test suites for static analysis. Implement and validate bounded resolution of test bodies, explicit fixtures, applicable autouse fixtures, conftest.py, fixture dependencies, and selected helpers. Record unresolved references, extraction coverage, bounds, and limitations.

Candidate context features: fixture scope/autouse, teardown/finalizer structure, fixture dependency structure, shared mutable-state operations, monkeypatch/mock usage, and filesystem/network/time/randomness operations. These indicate risk; they do not prove a failure cause. Validate resolution and extracted feature evidence on a declared manual sample.

Implement CPU baselines and a controlled ablation:

- Trivial/prevalence reference and simple size/assertion heuristic.
- Test-body text baseline such as TF-IDF plus logistic regression.
- Test-body static classifier.
- The same model family and training procedure with fixture/helper context added.
- Compatible CANNIER baseline using the released artifact where feasible; otherwise explicitly name and document an adaptation.

Inspect the paper, framework, released features, labels, and source mapping before claiming faithful reproduction. Static-only input may differ from CANNIER's dynamic feature set. Do not claim to reproduce unavailable dynamic measurements with AST substitutes. Use released compatible measurements where appropriate; otherwise report the limitation or define an adapted baseline.

Never use repeated-run outcomes, flip/failure counts, seeds, order-specific failures, subtype annotations, or label-derived cause annotations as predictor inputs. Start static-only. Any permitted single-run dynamic measurement must be selected independently of outcomes and kept distinct from detection evidence. Existing JUnit durations are not automatically equivalent to all original CANNIER features.

Preserve natural class imbalance. No SMOTE or duplicated examples in the primary experiment. Class weights are permissible. CANNIER's sampling choices must be disclosed; any sampling comparison is a separately declared experimental variable, not a hidden baseline change.

## Phase 5: freeze evaluation and test the contribution

Use identical eligible examples and splits for compared models. Prefer project-disjoint outer evaluation with project-grouped inner tuning where feasible; document folds that cannot support tuning because of insufficient positive projects. Fit vocabulary, imputers, scalers, feature selection, hyperparameters, and thresholds only using training/validation data. Freeze random seeds and export fold membership and out-of-fold predictions.

Report average precision (define the PR summary), MCC, precision, recall, F1, false positives per 1,000 negative-labelled tests, and recall at a declared top-ranked budget such as 10%. Include pooled and project-level results, numbers of independent positive projects/source families, uncertainty respecting project/cause clustering, and error analysis. Do not hide undefined metrics or treat accuracy alone as evidence of success.

The principal ablation asks whether context adds value when model family, cohort, split, and training procedure are held constant. Report regressions and negative results. Do not compare a score on this corpus with CANNIER's published score on another corpus as proof of improvement.

Claiming improved hybrid detection efficiency requires a separate matched-budget experiment with retained execution context, detection yield, timing, and valid confirmation. Offline risk ranking alone does not demonstrate faster detection or real CPU savings. Do not make that expansion the default under the user's time constraint.

## Phase 6: explanations, artifact, and manuscript

After the core comparison works, add source-linked feature evidence and bounded SHAP/rule explanations. Separate model attribution from replay-backed diagnosis. An optional LLM comparison must use the same held-out examples, fixed context budgets/prompts/model version, structured outputs, caching, and cost reporting, without access to outcome evidence.

Prepare reproducible dataset export, extractor/evaluation scripts, environment specification, split files, predictions, figures/tables generated from actual results, limitations, and reproduction instructions. Verify licences before redistributing upstream source or third-party datasets. Preserve evidence references and version history.

Write research questions around context value, unseen-project generalization, and extraction/explanation coverage. Conduct a focused related-work review before asserting novelty. If gains or independent positives are insufficient, narrow or revise the claim instead of manufacturing a positive conclusion. Submission readiness and journal acceptance are separate outcomes.

Suggested implementation files (adapt to the existing repository): scripts/export_dataset.py, scripts/extract_features.py, scripts/train_evaluate.py, scripts/explain_predictions.py, an evidence-audit utility, and documentation of cohorts/splits. Add meaningful checks for identity joins, leakage prevention, fixture resolution, and split isolation.

## Execution decision rules

- Artifact download, audit, source retrieval, dataset export, static extraction, model training, explanation generation, and writing normally require no upstream workflow reruns.
- Missing/incomplete rounds, inaccessible required evidence, incompatible measurements needed for a faithful baseline, or stronger causal claims may require additional execution. State the specific gap and choose the smallest scientifically valid remedy.
- For any necessary workflow dispatch, follow the user's full-run preference. Distinguish model experiments and bounded confirmation studies from full workflow campaigns. If a confirmation study would conflict with that preference, clarify that specific choice before execution.
- Do not alter upstream tests, ignore real baseline failures, or weaken gates to manufacture eligible evidence. Follow AGENTS.md requirements for PYTHONPATH, -p no:cov, and in-memory reversal.
- Do not declare success merely because workflows finish. Success is an audited corpus plus a reproducible, fairly evaluated research contribution, with claims limited to observed results.

## First agent update after activation

Report: which artifacts are available; which projects meet the declared evidence criteria; shared versus additional membership; missing source/identity/label information; which work can proceed without rerunning; and the proposed primary task given label validity. Continue independent audit and implementation work without unnecessary permission questions. Do not dispatch a broad rerun campaign merely because stronger optional claims would benefit from one.

## References and prior context

- CANNIER paper: https://link.springer.com/article/10.1007/s10664-023-10307-w
- Authors' experiment artifact: https://github.com/flake-it/cannier-experiment
- Authors' framework: https://github.com/flake-it/cannier-framework
- pytest-randomly behavior: https://github.com/pytest-dev/pytest-randomly
- Local context: AGENTS.md and BASE_PAPER_DECISION.md. PUBLICATION_RESEARCH_PLAN.md contains superseded journal/base-paper recommendations; do not revive those decisions without checking the latest user direction.

Review external sources and the actual run revisions when implementing. This handoff records the plan and inspected code behavior, not an audit of all finished workflow artifacts.
