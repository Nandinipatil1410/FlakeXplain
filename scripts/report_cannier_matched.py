"""Summarize the controlled CANNIER-feature comparison, including regressions."""
import json
from collections import defaultdict
import numpy as np
from prepare_cannier_matched import OUT,DATA
from train_pilot import ROOT,reader,sha,write_csv,weighted_ap

def paired_interval(y,a,b,projects,repeats=500):
    names,inverse=np.unique(projects,return_inverse=True);rng=np.random.default_rng(20261014)
    differences={'ap':[],'mcc_fixed_0.5':[]}
    def mcc(score,w):
        pred=score>=.5;tp=w[(y==1)&pred].sum();fp=w[(y==0)&pred].sum();tn=w[(y==0)&~pred].sum();fn=w[(y==1)&~pred].sum();denom=(tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
        return float((tp*tn-fp*fn)/np.sqrt(denom)) if denom else None
    for _ in range(repeats):
        w=rng.multinomial(len(names),np.repeat(1/len(names),len(names)))[inverse].astype(float)
        aa=weighted_ap(y,a,w);bb=weighted_ap(y,b,w)
        if aa is not None and bb is not None:differences['ap'].append(bb-aa)
        aa=mcc(a,w);bb=mcc(b,w)
        if aa is not None and bb is not None:differences['mcc_fixed_0.5'].append(bb-aa)
    return {k:dict(valid_repeats=len(v),lower=float(np.quantile(v,.025)),upper=float(np.quantile(v,.975))) if v else dict(valid_repeats=0,lower=None,upper=None) for k,v in differences.items()}

def main():
    validation=json.loads((OUT/'validation.json').read_text())
    if validation['status']!='passed':raise ValueError('Validate comparison first')
    pooled=list(reader(OUT/'metrics_pooled.csv'));perproject=list(reader(OUT/'metrics_by_project.csv'));budgets=list(reader(OUT/'per_project_top10_budget.csv'));summaries=list(reader(DATA/'project_summary.csv'))
    original=list(reader(OUT/'authors_released_predictions_summary.csv'));dataset=json.loads((DATA/'manifest.json').read_text());comparisons=[];family_rows=[];macro=[]
    for task in ('NOD-vs-Rest','Victim-vs-Rest'):
        predictions=list(reader(OUT/task/'oof_predictions.csv.gz'));y=np.asarray([int(r['label']) for r in predictions]);projects=np.asarray([r['project'] for r in predictions])
        counts=defaultdict(int)
        for r in predictions:counts[r['source_family_id']]+=1
        weights=np.asarray([1/counts[r['source_family_id']] for r in predictions])
        for balance in ('natural','author_smote_sensitivity'):
            a=next(r for r in pooled if r['task']==task and r['variant']==balance+'_baseline' and r['threshold_mode']=='fixed_0.5')
            b=next(r for r in pooled if r['task']==task and r['variant']==balance+'_context' and r['threshold_mode']=='fixed_0.5')
            scorea=np.asarray([float(r[balance+'_baseline_score']) for r in predictions]);scoreb=np.asarray([float(r[balance+'_context_score']) for r in predictions])
            interval=paired_interval(y,scorea,scoreb,projects)
            r=dict(task=task,balance=balance,cases=len(y),positives=int(y.sum()),baseline_ap=float(a['average_precision']),context_ap=float(b['average_precision']),ap_difference=float(b['average_precision'])-float(a['average_precision']),ap_ci_lower=interval['ap']['lower'],ap_ci_upper=interval['ap']['upper'],baseline_mcc=float(a['mcc']),context_mcc=float(b['mcc']),mcc_difference=float(b['mcc'])-float(a['mcc']),mcc_ci_lower=interval['mcc_fixed_0.5']['lower'],mcc_ci_upper=interval['mcc_fixed_0.5']['upper'],bootstrap_valid_ap=interval['ap']['valid_repeats'],bootstrap_valid_mcc=interval['mcc_fixed_0.5']['valid_repeats'])
            comparisons.append(r);print('Paired comparison:',json.dumps(r),flush=True)
            for representation,score in [('baseline',scorea),('context',scoreb)]:
                family_rows.append(dict(task=task,variant=balance+'_'+representation,source_families=len(counts),family_weighted_ap=weighted_ap(y,score,weights)))
                pr=[r for r in perproject if r['task']==task and r['variant']==balance+'_'+representation and r['threshold_mode']=='fixed_0.5']
                defined_mcc=[float(r['mcc']) for r in pr if r['mcc_denominator_nonzero']=='True']
                macro.append(dict(task=task,variant=balance+'_'+representation,positive_projects=sum(int(r['positives'])>0 for r in pr),macro_positive_project_ap=float(np.mean([float(r['average_precision']) for r in pr if r['average_precision']!=''])),macro_defined_project_mcc=float(np.mean(defined_mcc)) if defined_mcc else None))
    write_csv(OUT/'paired_comparisons.csv',comparisons,list(comparisons[0]));write_csv(OUT/'family_weighted_metrics.csv',family_rows,list(family_rows[0]));write_csv(OUT/'project_macro_metrics.csv',macro,list(macro[0]))
    lines=['# CANNIER matched baseline-versus-context experiment','',
        'Status: completed retrospective controlled ablation on the authors released feature/label corpus. This is not untouched independent confirmation or a reproduction of the complete hybrid detector.','',
        '## What is now comparable','',
        f"The original release contains {dataset['released_cases']:,} cases across 30 projects. The matched cohort contains {dataset['cases']:,} source-mapped cases, including {dataset['nod']} author-labelled NOD and {dataset['victim']} author-labelled victims. Both representations use exactly the same cases, author labels, project-grouped folds, model settings and sampling procedure.",
        'Baseline: actual released 18 static/dynamic measurements, using the first stored instrumentation measurement independently of outcomes. Extension: those identical 18 columns plus 66 bounded context features. No original feature is replaced with an AST proxy.',
        'The primary comparison preserves natural imbalance without synthetic cases or class weighting. The author-SMOTE setting is a separately declared sensitivity variable, fitted inside training partitions only. Classifiers match the published best families/tree counts: 100-tree Extra Trees for NOD-vs-rest and 75-tree Extra Trees for victim-vs-rest.','',
        '## Paired project-held-out results','',
        '| Task / training balance | Baseline AP | Context AP | AP difference | Baseline MCC | Context MCC | MCC difference |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in comparisons:lines.append(f"| {r['task']} / {r['balance']} | {r['baseline_ap']:.6f} | {r['context_ap']:.6f} | {r['ap_difference']:+.6f} | {r['baseline_mcc']:.6f} | {r['context_mcc']:.6f} | {r['mcc_difference']:+.6f} |")
    lines+=['','MCC above uses a fixed 0.5 threshold and signed MCC. AP summarizes score ranking. Additional inner-project-OOF MCC-selected thresholds are reported in metrics_pooled.csv; they were not selected from outer-test outcomes.','',
        '## Project-resampling uncertainty','',
        '| Task / balance | 95% AP-difference interval | 95% MCC-difference interval |', '|---|---|---|']
    def interval_text(low,high):return 'undefined' if low is None or high is None else f'[{low:.6f}, {high:.6f}]'
    for r in comparisons:lines.append(f"| {r['task']} / {r['balance']} | {interval_text(r['ap_ci_lower'],r['ap_ci_upper'])} | {interval_text(r['mcc_ci_lower'],r['mcc_ci_upper'])} |")
    lines+=['','Intervals use 500 paired project-bootstrap samples of fixed OOF predictions. They do not include model-refitting or prior feature-development uncertainty; two tasks and two metrics are reported without selecting a favourable winner. Project counts are small and prevalence varies.','',
        '## Original CANNIER scores recovered from its release','',
        '| Original task | Derived mean AP | Mean signed MCC | Repeats |', '|---|---:|---:|---:|']
    for r in original:lines.append(f"| {r['task']} | {float(r['derived_ap_mean']):.6f} | {float(r['signed_mcc_mean']):.6f} | {r['repeats']} |")
    lines+=['','These AP values were newly computed from the authors released predictions; the paper itself reports MCC. They use the authors full task domains, original stratified case-level cross-validation, SMOTE and random single-measurement selection. They are reference verification, not matched comparison scores for our changed cohort/project-fold protocol. Released prediction MCC values reproduce the rounded paper figures.','',
        '## Scope and limitations','',
        '- The source/context design and these projects influenced earlier development. Project-held-out fitting is enforced, but the study is retrospective; it cannot substitute for untouched positive-project confirmation.',
        '- Original author NOD/victim labels come from their 2,500 baseline/shuffle protocol. They are retained separately from our own 25/27-round instability labels. No labels were silently merged or reinterpreted.',
        '- Source exclusions are retained per case and project. Whole-cohort baseline and matched-cohort performance cannot be interchanged. Dynamic/generated tests that cannot be mapped uniquely remain excluded from both matched models.',
        '- The new environment uses scikit-learn 1.7.2 rather than the authors 1.0.2. Five project-grouped folds replace their stratified case-level ten folds. Fixed first-measurement selection replaces random feature sample selection. These are explicit protocol adaptations.',
        '- Author code computes absolute MCC; this experiment retains signed MCC. No negative correlation is turned into positive performance.',
        '- The authors framework feature-name tuple reverses the names of External Modules and Assertions relative to the SQLite/plugin numeric order. We preserve numeric measurements and use their actual SQLite column names; no values are exchanged.',
        '- Near-clone/fork assessment, human fixture/context review and independent positive confirmation remain incomplete. Original hybrid rerunning costs were not measured again; no efficiency claim follows from offline ranking.',
        '- No new broad workflow campaign was needed: all 30 historical source revisions and original instrumentation data were recovered. The prior independent three-project confirmation remains unchanged and zero-positive.','',
        '## Interpretation','']
    natural=[r for r in comparisons if r['balance']=='natural'];supported=all(r['ap_ci_lower'] is not None and r['mcc_ci_lower'] is not None and r['ap_ci_lower']>0 and r['mcc_ci_lower']>0 for r in natural)
    if supported:conclusion='Both prespecified tasks show positive AP and fixed-threshold MCC differences with positive conditional project-bootstrap intervals in the primary natural-imbalance experiment. This supports a retrospective classifier-extension finding, subject to source exclusions, prior development and the need for independent positive confirmation. It does not establish superiority over the full CANNIER hybrid detector.'
    elif all(r['ap_difference']<=0 and r['mcc_difference']<=0 for r in natural):conclusion='The primary matched experiment does not show improvement: added context failed to improve either pooled AP or fixed-threshold MCC on either task. Report the negative result rather than presenting the earlier internal static-baseline gain as CANNIER improvement.'
    else:conclusion='The primary matched results are mixed or uncertain. Report the task-specific increases and regressions and their project-level intervals. They do not establish a general improvement over CANNIER; the earlier static-baseline gain is a different experiment.'
    lines +=[conclusion,'',
        f"Verification: {validation['checks']} checks passed, including replay of all 40 outer models, author-array/SQLite alignment, original label preservation, no project overlap, feature allowlists and training-only sampling/threshold selection.",
        'Sources: https://doi.org/10.1007/s10664-023-10307-w ; https://github.com/flake-it/cannier-experiment/tree/b96d6ed02e98d514eb6a92ca264a082234cb9728 ; https://github.com/flake-it/cannier-framework/tree/89c74c27847474248b581b428aed2b417141296e .','']
    (OUT/'MATCHED_COMPARISON_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'conclusion.json').write_text(json.dumps(dict(conclusion=conclusion,comparisons=comparisons,validation_checks=validation['checks'],source_manifest_sha256=sha(DATA/'manifest.json'),report_sha256=sha(OUT/'MATCHED_COMPARISON_REPORT.md')),indent=2)+'\n')
    print(conclusion,flush=True)

if __name__=='__main__':main()
