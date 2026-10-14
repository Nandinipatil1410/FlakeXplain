"""Produce an evidence-linked pilot report without fitting or selecting models."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import precision_recall_curve
from train_pilot import ROOT, VARIANTS, reader, sha, write_csv

def main():
    out=ROOT/'reports/pilot-v0.1'
    results=json.loads((out/'results.json').read_text())
    validation=json.loads((out/'validation.json').read_text())
    if validation['status']!='passed':
        raise ValueError('Validate pilot before reporting')
    pooled={(r['model'],r['threshold_mode']):r for r in results['pooled']}
    body=pooled[(VARIANTS[0],'inner_f1')]; context=pooled[(VARIANTS[1],'inner_f1')]
    fold=list(reader(out/'metrics_by_fold.csv')); projects=list(reader(out/'metrics_by_project.csv'))
    diagnostics=list(reader(out/'generalization_diagnostics.csv'))
    source_weighted=list(reader(out/'metrics_source_family_weighted.csv'))
    prediction=list(reader(out/'oof_predictions.csv.gz'))
    columns=('source_path','source_qualname','junit_name','context_bounded','unresolved_fixture_count')
    wanted={r['example_id'] for r in prediction}
    meta={r['example_id']:{k:r[k] for k in columns} for r in reader(ROOT/'dataset/v0.1/metadata.csv.gz') if r['example_id'] in wanted}
    error_samples=[]
    for name,prefix in zip(VARIANTS,('body','context')):
        for error_type,label,predicted,descending in [('false_positive',0,1,True),('false_negative',1,0,False)]:
            candidates=[r for r in prediction if int(r['label'])==label and int(r[prefix+'_inner_prediction'])==predicted]
            ranked=sorted(candidates,key=lambda r:((-1 if descending else 1)*float(r[prefix+'_score']),r['example_id']))[:10]
            for r in ranked:
                error_samples.append(dict(model=name,error_type=error_type,example_id=r['example_id'],project=r['project'],
                                          outer_fold=r['outer_fold'],label=r['label'],score=r[prefix+'_score'],
                                          selected_threshold=r[prefix+'_inner_threshold'],**meta[r['example_id']]))
    write_csv(out/'error_samples.csv',error_samples,list(error_samples[0]))
    y=np.array([int(r['label']) for r in prediction]); curves=[]
    for name,prefix in zip(VARIANTS,('body','context')):
        score=np.array([float(r[prefix+'_score']) for r in prediction])
        precision,recall,thresholds=precision_recall_curve(y,score)
        curves.extend(dict(model=name,threshold=float(t),precision=float(p),recall=float(r))
                      for p,r,t in zip(precision[:-1],recall[:-1],thresholds))
    write_csv(out/'precision_recall_curve.csv.gz',curves,list(curves[0]))
    macro=[]
    for name in VARIANTS:
        selected=[r for r in projects if r['model']==name and r['threshold_mode']=='inner_f1']
        positive=[r for r in selected if int(r['positives'])>0]
        macro.append(dict(model=name,projects=len(selected),positive_projects=len(positive),
                          macro_average_precision_positive_projects=float(np.mean([float(r['average_precision']) for r in positive])),
                          macro_recall_positive_projects=float(np.mean([float(r['recall']) for r in positive])),
                          macro_f1_all_projects=float(np.mean([float(r['f1']) for r in selected])),
                          macro_false_positives_per_1000_negative=float(np.mean([float(r['false_positives_per_1000_negative']) for r in selected]))))
    write_csv(out/'metrics_project_macro.csv',macro,list(macro[0]))
    ci=results['paired_project_bootstrap']['percentile_95_interval']
    delta=context['average_precision']-body['average_precision']
    lines=['# FlakeXplain pilot training results','',
        '**Empirically verified conclusion: this pilot does not support an improvement from the current bounded context feature set. Both classifiers generalize weakly to held-out projects.**','',
        '## Experiment actually run','',
        f"Evaluated {results['cases']:,} cases across {results['projects']} projects: {results['positives']} observed-flaky and {results['cases']-results['positives']:,} not-observed-flaky. Natural positive prevalence is {100*body['prevalence']:.4f}%. No synthetic cases, oversampling or test-project tuning were used.",
        '',
        'Extra Trees body-only (22 numeric features) versus the same model with bounded fixture/helper/lifecycle context (55 total features). Fixed parameters: 128 trees, max_depth=20, min_samples_leaf=5, max_features="sqrt", class_weight="balanced", bootstrap=False, random_state=20261013, four CPU threads. Class weights are computed within each fit. A shared configuration means the same hyperparameter settings/training procedure; the number of available features differs by design.',
        '',
        'Five frozen outer project-separated folds provide one held-out prediction per case. For each outer fold and each feature variant, four inner project-separated fits select the threshold maximizing inner out-of-fold F1; a fifth fit uses all outer-training projects to predict the outer-test projects. In total, 50 fits were run and 10 outer models retained. No hyperparameter search, full-dataset deployment fit, LLM run or CANNIER faithful reproduction was performed.',
        '',
        f"Training/evaluation/bootstrap run time: {results['elapsed_seconds']:.1f} seconds on this machine (excluding installation and later artifact verification). Reproducible package pins are in requirements-pilot.txt; exact environment and pre-result choices are in protocol.json.",
        '',
        '## Main ranking comparison','',
        '| Model/reference | Pooled average precision (0–1) | Recall at top-ranked 10% |','|---|---:|---:|']
    for name,description in [(VARIANTS[0],'Extra Trees: body'),(VARIANTS[1],'Extra Trees: body + context'),('body_size_heuristic','Fixed test-size ranking'),('training_prevalence','Per-fold training-prevalence score')]:
        mode='inner_f1' if name in VARIANTS else 'reference'; r=pooled[(name,mode)]
        lines.append(f"| {description} | {r['average_precision']:.6f} | {100*r['recall_at_top_10_percent']:.2f}% |")
    lines += ['',f"Constant-score AP is the corpus prevalence, {body['prevalence']:.6f}; it is a descriptive no-discrimination reference. Per-fold training prevalence is not globally constant, so its pooled AP differs. The size heuristic only ranks by body line span; its all-negative binary metrics in the CSV are placeholders for the all-negative reference, not a selected size threshold.",
        '',f"Context minus body pooled AP: **{delta:+.6f}**. Project-resampled paired 95% percentile interval (500 resamples): **[{ci[0]:+.6f}, {ci[1]:+.6f}]**. The interval includes zero; this is conditional uncertainty on fixed OOF predictions, with no refitting or feature-development uncertainty. It does not establish a statistically reliable improvement or deterioration.",
        '',
        'Average precision uses [scikit-learn average_precision_score](https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.average_precision_score.html), not trapezoidal PR area. Pooled scores come from different fold models and are uncalibrated; fold/project results are essential alongside the pooled figure. [Extra Trees documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesClassifier.html) describes the class-weight and model settings used.',
        '', '## Classification at training-only selected thresholds','',
        '| Model | Precision | Recall | F1 | MCC | TP | FP | FN | FP per 1,000 negatives |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name,description in [(VARIANTS[0],'Body'),(VARIANTS[1],'Body + context')]:
        r=pooled[(name,'inner_f1')]
        lines.append(f"| {description} | {100*r['precision']:.2f}% | {100*r['recall']:.2f}% | {100*r['f1']:.2f}% | {r['mcc']:.4f} | {r['tp']:.0f} | {r['fp']:.0f} | {r['fn']:.0f} | {r['false_positives_per_1000_negative']:.2f} |")
    lines += ['',
        'The context model’s higher recall comes with 49,173 false positives: more than half the negative cases are flagged. Its precision and F1 are lower than body-only. This is not evidence of a useful context improvement.',
        '', '## Fixed 0.5 threshold reference','',
        '| Model | Precision | Recall | F1 | TP | FP | FN |','|---|---:|---:|---:|---:|---:|---:|']
    for name,description in [(VARIANTS[0],'Body'),(VARIANTS[1],'Body + context')]:
        r=pooled[(name,'fixed_0.5')]
        lines.append(f"| {description} | {100*r['precision']:.2f}% | {100*r['recall']:.2f}% | {100*r['f1']:.2f}% | {r['tp']:.0f} | {r['fp']:.0f} | {r['fn']:.0f} |")
    lines += ['',
        'At 0.5, the context model detects none of the 693 observed positives. Class-weighted Extra Trees scores were not calibrated as natural-prevalence probabilities. Threshold adjustment cannot fix the poor ranking quality.',
        '', '## Results by held-out fold','',
        '| Fold | Cases | Positives | Body AP | Context AP |','|---|---:|---:|---:|---:|']
    for outer in range(5):
        a=next(r for r in fold if r['model']==VARIANTS[0] and r['threshold_mode']=='inner_f1' and int(r['outer_fold'])==outer)
        b=next(r for r in fold if r['model']==VARIANTS[1] and r['threshold_mode']=='inner_f1' and int(r['outer_fold'])==outer)
        lines.append(f"| {outer} | {int(a['cases']):,} | {a['positives']} | {float(a['average_precision']):.6f} | {float(b['average_precision']):.6f} |")
    lines += ['',
        'Context AP is lower in every outer fold. Airflow contributes 300 of 693 positives; fold 0 contains 310 positives. Project-level AP/recall are undefined for the six zero-positive projects and are left blank in metrics_by_project.csv. Precision with no predicted positives and degenerate MCC use zero with explicit definition flags.',
        '', '## Project-macro sensitivity','',
        '| Model | Mean AP over 29 positive projects | Mean F1 over all 35 projects | Mean FP per 1,000 negatives |',
        '|---|---:|---:|---:|']
    for name,description in [(VARIANTS[0],'Body'),(VARIANTS[1],'Body + context')]:
        r=next(r for r in macro if r['model']==name)
        lines.append(f"| {description} | {r['macro_average_precision_positive_projects']:.6f} | {100*r['macro_f1_all_projects']:.2f}% | {r['macro_false_positives_per_1000_negative']:.2f} |")
    lines += ['',
        'Equal-project macro F1 is slightly higher for context, while macro AP is lower and the false-alarm burden is much higher. This mixed secondary result is retained; it does not reverse the failed primary ranking comparison.',
        '', '## Generalization diagnostics','',
        '| Model | Training resubstitution AP range | Held-out AP range |','|---|---:|---:|']
    for name,description in [(VARIANTS[0],'Body'),(VARIANTS[1],'Body + context')]:
        rows=[r for r in diagnostics if r['model']==name]
        train=[float(r['training_resubstitution_average_precision']) for r in rows]
        test=[float(r['held_out_average_precision']) for r in rows]
        lines.append(f"| {description} | {min(train):.4f}–{max(train):.4f} | {min(test):.4f}–{max(test):.4f} |")
    lines += ['',
        'Training resubstitution is a fit diagnostic, not a valid estimate of unseen-project performance. The large training/held-out gap, especially for context, is consistent with overfitting or project distribution shift; it does not by itself prove a specific cause. Aggregate context counts can encode project-specific structure. Existing extraction gaps, class/module state, generated test bodies, plugin fixtures and parameter-specific behavior are candidates for a bounded development audit.',
        '', '## Sensitivity to shared source families','',
        '| Model | Family-weighted AP | Family-weighted F1 at inner-selected threshold |','|---|---:|---:|']
    for name,description in [(VARIANTS[0],'Body'),(VARIANTS[1],'Body + context')]:
        r=next(r for r in source_weighted if r['model']==name and r['threshold_mode']=='inner_f1')
        lines.append(f"| {description} | {float(r['average_precision']):.6f} | {100*float(r['f1']):.2f}% |")
    lines += ['',
        'Each defining source-function family has total weight one, distributed over its parameterized/inherited cases. Weighted outcome counts can therefore be fractional. Case-count/positive/prevalence fields in the sensitivity CSV describe the original unweighted corpus; weighted metrics describe the family weighting. This sensitivity also does not show a context benefit.',
        '', '## Verification and saved artifacts','',
        f"Pilot verification passed **{len(validation['checks'])} checks**, including dataset joins, independent sklearn metric recomputation, model feature allowlists, threshold project membership and replay of all 10 saved outer models. The repository suite passed 80 tests with one Linux-only check skipped on Windows (81 discovered).",
        '',
        '- protocol.json and run_manifest.json: frozen configuration, software/input hashes and original result checksums.',
        '- results.json, metrics_pooled.csv, metrics_by_fold.csv, metrics_by_project.csv: all measured performance, including unfavorable results.',
        '- oof_predictions.csv.gz: one held-out score/prediction per case for both variants and references.',
        '- threshold_selection.csv: per-fold inner-selected thresholds and eligible training projects; inner models can be recreated from code and are not serialized.',
        '- metrics_project_macro.csv and metrics_source_family_weighted.csv: project/family sensitivity.',
        '- generalization_diagnostics.csv: training-fit versus held-out diagnostics.',
        '- feature_importance.csv: fold-wise impurity importances; these can be biased and are neither SHAP explanations nor causal findings.',
        '- error_samples.csv: deterministic high-score false positives and low-score false negatives with source references, for inspection rather than causal annotation.',
        '- precision_recall_curve.csv.gz: pooled OOF PR points for later plotting.',
        '- Saved outer estimators are ignored local files under local-evidence/pilot-models/pilot-v0.1; their hashes are recorded in results.json.','',
        '## Decision before final training','',
        '**This pilot is not ready to be promoted as a successful final model.** Keep it as the fixed negative reference. Next, audit a bounded development sample of missed positives/false alarms, improve context representation and resolution where supported, add simple regularized/text baselines, and tune with project-separated inner validation. Preserve natural imbalance and feature–label isolation.',
        '',
        'All five outer folds have now been inspected. If their results influence further feature/model decisions, they are development evaluation; repeating them later is not an untouched final test. A defensible final study needs a predeclared evaluation design, with fresh independent projects/evidence if an untouched confirmation claim is desired, or explicitly development-conditioned repeated/nested evaluation with that limitation disclosed. Final deployment fitting on all cases would not itself produce an independent performance estimate.',
        '',
        'These results concern static observed-instability prediction on the FlakeXplain corpus. They neither reproduce CANNIER’s full feature/label task nor demonstrate an improvement over its hybrid detector. Publication improvement remains unestablished.',
        '', '## Reproduce','', '```powershell',
        'python -m venv .venv-pilot',
        r'.\.venv-pilot\Scripts\python.exe -m pip install -r requirements-pilot.txt',
        r'.\.venv-pilot\Scripts\python.exe scripts/train_pilot.py --output reports/pilot-reproduction',
        r'.\.venv-pilot\Scripts\python.exe scripts/validate_pilot.py --run reports/pilot-reproduction',
        '```','',
        'Use a new output directory. The runner refuses to overwrite an existing pilot. Exact wall-clock time and serialized-model bytes can differ; model score replay is checked with absolute tolerance 1e-12.','']
    (out/'PILOT_RESULTS_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    artifacts={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='review_manifest.json'}
    review=dict(status='verified',files=artifacts,report_script_sha256=sha(Path(__file__)),validator_sha256=sha(ROOT/'scripts/validate_pilot.py'))
    (out/'review_manifest.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(dict(report=str(out/'PILOT_RESULTS_REPORT.md'),context_minus_body_ap=delta,macro_metrics=macro),indent=2))

if __name__=='__main__':
    main()
