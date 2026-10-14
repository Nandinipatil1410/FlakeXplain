"""Generate guide-facing tables, an honest study report, and a manuscript draft."""
import json
from pathlib import Path
from train_final_confirmation import OUT
from train_pilot import ROOT,reader,sha,write_csv

def main():
    result=json.loads((OUT/'external_results.json').read_text());validation=json.loads((OUT/'validation.json').read_text())
    if validation['status']!='passed':raise ValueError('Verify external results first')
    metrics=list(reader(OUT/'external_metrics.csv'));audit=json.loads((OUT/'evidence-audit/audit.json').read_text())
    rows=[]
    for r in audit['projects']:
        eligible=r['eligible_labels'];binary=eligible.get('observed_flaky',0)+eligible.get('not_observed_flaky',0)
        rows.append(dict(project=r['project'],total_identities=r['tests'],binary_cases=binary,observed_flaky=eligible.get('observed_flaky',0),not_observed_flaky=eligible.get('not_observed_flaky',0),skip_only=r['labels'].get('skip_only',0),rounds='12/12/1',detection_seconds=r['detection_seconds']))
    write_csv(OUT/'guide_project_table.csv',rows,list(rows[0]))
    # Preserve the evaluated artifact and explicitly correct its misleading metadata field name.
    erratum=dict(affected_files=['external_results.json','external_project_summary.csv'],field='candidate_binary_cases',
        correction='This field was populated from the audit eligible_tests count, which also contains skip-only identities. For attrs it reads 1412; the binary count is 1401 and the remaining 11 are skip-only. Model cohort, labels, features, scores, metrics and source exclusions are correct and unchanged.',
        authoritative_binary_counts={r['project']:r['binary_cases'] for r in rows},corrected_table='guide_project_table.csv')
    (OUT/'metadata_clarification.json').write_text(json.dumps(erratum,indent=2)+'\n')
    modelrows=[r for r in metrics if r['project']=='ALL' and (r['threshold_name']=='frozen_development' or r['model']=='constant_training_prevalence')]
    lines=['# FlakeXplain: completed study and independent confirmation','',
        'Prepared 14 October 2026. Status: empirically evaluated; publication-level detection improvement remains unestablished.','',
        '## What was completed','',
        '- Audited 35 development projects and froze 96,118 source-mapped cases: 693 observed flaky and 95,425 not observed flaky (0.721% observed prevalence).',
        '- Completed the original pilot and one bounded development cycle with project-separated training and tuning, static feature/label isolation, natural class imbalance, error inspection and collision audits.',
        '- Inspected the pinned 2024 authors artifact; implemented a Random Forest family reference on our features. This is explicitly an adaptation, not a faithful published reproduction.',
        '- Selected three new confirmation projects before inspecting outcomes, froze features, model selection rules and thresholds, and executed full baseline + 25-round workflows.',
        '- Fitted four development-only final models before opening confirmation evidence; replayed external predictions and independently verified metrics.',
        '- Produced source-linked mean tree-path probability decompositions; fitted a separate all-data deployment model after evaluation.','',
        '## Independent evidence','',
        '[Workflow run](https://github.com/Nandinipatil1410/FlakeXplain/actions/runs/38429430361). All three jobs passed local structural evidence checks, pinned source verification and complete 12 original + 12 random + 1 reverse rounds. The longest job took about 4.5 minutes, within the authorized four-hour cap. No projects were replaced after observing results.','',
        '| Project | Collected identities | Binary cases | Observed flaky | Skip-only | Detection seconds |',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['project']} | {r['total_identities']:,} | {r['binary_cases']:,} | {r['observed_flaky']} | {r['skip_only']} | {r['detection_seconds']:.2f} |")
    lines+=['','All 2,610 binary cases passed all 25 detection rounds. There were no source-mapping or substantive exact-body-overlap exclusions among these binary cases. Eleven attrs identities were skip-only and never entered model evaluation. Source mapping is static, and near-clone independence is not fully audited.','',
        '## Frozen-threshold confirmation results','',
        '| Model | Threshold | Observed false alarms | Per 1,000 negative-labelled cases |',
        '|---|---:|---:|---:|']
    for r in modelrows:lines.append(f"| {r['model']} | {float(r['threshold']):.6f} | {int(float(r['fp']))} | {float(r['false_positives_per_1000_negative']):.3f} |")
    lines+=['','Recall and average precision are undefined on this zero-positive confirmation set. F1/MCC conventions and their definedness flags remain in the machine-readable tables; they do not establish detection ability. The constant-negative reference makes zero false alarms here. High accuracy is therefore uninformative.','',
        'At separately development-selected thresholds, context ET produced 3 flags versus core ET\'s 111. This is a descriptive false-alarm difference on three selected projects. The two models selected different class weights as well as different thresholds; it does not isolate context causally or establish a matched-recall advantage. At threshold 0.5, core/context ET produced 221/0 flags.','',
        '## Development findings and their limits','',
        'The bounded nested development cycle yielded pooled average precision 0.055157 for revised-context ET versus 0.007112 for revised-core ET. Its project-resampling interval for the AP difference was [-0.006505, 0.085454], including zero. These folds influenced development and cannot be called untouched final confirmation.','',
        'At a separately ranked top-10% budget within each development project, revised-context ET found 121/693 observed positives (17.46%) versus 103/693 (14.86%) for revised-core ET. This is more relevant to an unseen-project inspection budget than pooled top-10% ranking. No rerun CPU savings were measured.','',
        'For the final all-development configuration selection, five project-fold OOF AP was 0.026762 for context ET and 0.010972 for core ET. These are selection results from a different fitting procedure, not replacement nested estimates or independent confirmation scores. All four final configurations are recorded in selected_models.json.','',
        'The 30-feature core includes two scope-aware read indicators. The 96-feature variant adds fixture/helper/lifecycle/class-state context; this comparison is incremental context beyond a scope-aware core, not a strict body-only comparison. The v0.1 22-feature body remains the strict body-only representation.','',
        '## Published baseline compatibility','',
        'The [2024 cross-project study](https://doi.org/10.1109/ACCESS.2024.3458184) is useful methodological framing. Its [authors\' artifact](https://github.com/alfcan/crossproject-flaky-test-prediction/tree/8fe244f03122706763484dea7b4d98b09fefb923) contains 26 Java metric columns. CPTrAda explicitly trains with labelled target-project fractions of 25%, 50% or 75%, testing on the remaining 25% target subset; it uses PCA, undersampling and transfer boosting. Our task uses no target-project training labels and Python AST features.','',
        'The implemented 100-tree Random Forest references use the same core/context feature tables and external cases, with no sampling, PCA or target-label transfer. They are model-family references only. No faithful [CANNIER](https://doi.org/10.1007/s10664-023-10307-w) hybrid/dynamic baseline or matched rerun-efficiency comparison was completed. Improvement over either complete published system is not established.','',
        '## Deployment and explanations','',
        'A separate Extra Trees context model was fitted on all 98,728 eligible cases across 38 projects, including the now-evaluated confirmation cases (693 observed positives). It keeps the development-selected configuration and threshold. The earlier frozen models own the confirmation results; this deployment refit has no new unbiased test score. Serialized deployment predictions were replayed on 100 cases.','',
        'Global impurity importances and nine source-linked explanations are provided. Explanations use exact mean tree-path probability decomposition with reconstruction checks; they are not SHAP and do not diagnose failure causes. Features associated with fixtures, processes and cleanup reflect model attribution, not empirical causal validation.','',
        '## Remaining work before a strong publication claim','',
        '1. Obtain genuinely independent positive projects under a prospectively declared follow-up protocol. Do not silently replace zero-positive subjects or retroactively alter this confirmation.',
        '2. Complete human source/context review and validate unresolved fixture/plugin/override behavior; the current error audit is AI-assisted and has no confirmed causal labels.',
        '3. Reproduce a compatible published baseline or narrow the contribution explicitly to an empirical Python context study. A labelled-target transfer task would require a separately declared experiment.',
        '4. Measure matched-budget rerun yield/time if claiming detection-efficiency improvement; add SHAP only as additional attribution with a fixed background.',
        '5. Complete licence review, near-clone/fork assessment, citation checking and manuscript peer review before submission. No acceptance guarantee is supported.','',
        '## Reproduction and verification','',
        f"- External validation: {validation['checks']} checks passed. Feature adapter: 80 contexts / 7,680 numeric values exactly replayed. Existing test suite: 85 tests, 84 passed and one Linux-specific skip.",
        '- Original data and pilot/development artifacts remain unchanged. Frozen models and downloaded archives remain under ignored local-evidence; their checksums and workflow references are exported.',
        '- Reproduction requires requirements-pilot.txt, pinned source archives, the frozen development tables, confirmation XML and local model binaries. The review ZIP is not a complete model/source redistribution package.',
        '- metadata_clarification.json explains the attrs candidate-count field naming error in the preserved evaluation output; guide_project_table.csv supplies corrected binary counts. Metrics are unaffected.','']
    (OUT/'FINAL_STUDY_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    brief=['# Guide meeting brief - 14 October 2026','',
        '**Completed:** audited dataset, pilot, bounded development study, adapted RF references, frozen final models, three independent full workflows, external evaluation, source-linked explanations, and all-data deployment fit.','',
        '**Measured result:** development context AP 0.0552 versus core 0.0071; uncertainty includes no gain. Independent confirmation: 2,610 eligible tests, zero observed positives; core/context ET flagged 111/3 at frozen thresholds.','',
        '**Honest conclusion:** context shows a development ranking signal and lower observed confirmation false alarms. Recall, overall generalization improvement and superiority to CANNIER remain unproven. A constant-negative model also flags zero cases in this confirmation.','',
        '**Useful guide decision:** position this as an evidence-backed empirical Python context study, or approve a prospectively designed positive-project follow-up and compatible baseline reproduction before making a stronger paper claim.','',
        '**Deployment:** Extra Trees context model, 98,728 cases / 38 projects / 693 positives, fitted after evaluation. Its own unbiased test performance is not measured.','']
    (OUT/'GUIDE_FINAL_BRIEF.md').write_text('\n'.join(brief),encoding='utf-8')
    manuscript=['# Bounded Static Context for Python Flaky-Test Risk Prediction: An Empirical Study','',
        '*Manuscript draft, 14 October 2026. Not submission-ready: human validation, related-work completeness, licences and independent positive confirmation remain outstanding.*','',
        '## Abstract','',
        'We investigate whether bounded pytest fixture, helper and lifecycle context improves static prediction of observed test instability across projects. We construct an evidence-backed corpus of 96,118 source-mapped Python test cases from 35 projects, including 693 cases observed to flip outcomes. We preserve natural imbalance and separate repeated-run label evidence from static predictors. A bounded development comparison shows context Extra Trees average precision of 0.0552 versus 0.0071 for a scope-aware core representation; the project-resampling interval for the difference includes zero. Prospective confirmation on three additional projects yields 2,610 eligible cases with no observed flips in 25 rounds. At frozen development-selected thresholds, core/context models flag 111/3 cases, respectively. These findings support studying context and false-alarm behavior, but cannot establish independent recall or superiority over published hybrid detectors.','',
        '## Research questions','',
        'RQ1: Does incremental bounded context improve project-separated development ranking under the same model family and candidate-selection procedure? RQ2: How do frozen models behave on prospectively selected unseen projects? RQ3: What extraction gaps and source-feature collisions limit static prediction?','',
        '## Method and results','',
        'Use FINAL_STUDY_REPORT.md, protocol.json, the immutable dataset card, nested development protocol, per-project metrics, and independent confirmation tables as the authoritative method/results material. The 30-feature core already contains two scope-aware reads; the context extension contains 96 total counts. Original detection randomization changes order and runtime seeds, so observed instability is the target and OD/NOD categories remain provisional.','',
        '## Threats to validity','',
        'Development folds influenced feature choices; the external confirmation has zero observed positives and only three selected projects. Negative labels mean not observed flaky after a finite budget. Parametrized cases share source families. Near-clone/fork checks and plugin-aware fixture resolution are incomplete. Upstream source commits are pinned; some confirmation dependencies resolve at setup and are snapshotted. Source/identity exclusions and skip-only observations remain visible. Attribution is not causal diagnosis. Different thresholds and selected class weights prevent interpreting confirmation false-alarm differences as a pure feature effect.','',
        '## Relationship to prior work','',
        'CANNIER (2023, doi:10.1007/s10664-023-10307-w) supplies the original Python hybrid-detector reference. The 2024 IEEE Access cross-project study (doi:10.1109/ACCESS.2024.3458184) motivates project-level generalization; its labelled-target transfer setting differs from our zero-target-label task. Static Test Flakiness Prediction (2022, doi:10.1007/s10664-022-10227-1) motivates static metrics but requires a language/task adaptation. Our Random Forest references are explicitly family adaptations, not reproductions of those systems. Bibliography metadata and broader related work require verification before submission.','',
        '## Conclusion','',
        'The completed study provides an audited corpus, bounded extractor, reproducible project-separated experiments and a transparent independent negative result. It offers development evidence of context-related ranking gains and descriptive external false-alarm differences. Independent recall gains, causal explanations and hybrid detection-efficiency improvements remain unestablished.','']
    (OUT/'MANUSCRIPT_DRAFT.md').write_text('\n'.join(manuscript),encoding='utf-8')
    print('Study report, guide brief, corrected project table and manuscript draft generated.')

if __name__=='__main__':main()
