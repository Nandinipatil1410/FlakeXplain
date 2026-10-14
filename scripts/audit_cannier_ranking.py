"""Audit the predeclared within-project budget metric; do not change models."""
import json,math
import numpy as np
from prepare_cannier_matched import OUT
from train_pilot import reader,write_csv,sha,ROOT

def main():
    rows=[];details=[];budgets=list(reader(OUT/'per_project_top10_budget.csv'))
    for task in ('NOD-vs-Rest','Victim-vs-Rest'):
        pred=list(reader(OUT/task/'oof_predictions.csv.gz'));projects=np.asarray([r['project'] for r in pred]);ids=np.asarray([r['example_id'] for r in pred]);y=np.asarray([int(r['label']) for r in pred]);names=sorted(set(projects))
        for balance in ('natural','author_smote_sensitivity'):
            scores=[np.asarray([float(r[balance+'_'+rep+'_score']) for r in pred]) for rep in ('baseline','context')];counts=[]
            for p in names:
                take=np.flatnonzero(projects==p);k=math.ceil(.1*len(take));found=[]
                for score in scores:found.append(int(y[take[np.lexsort((ids[take],-score[take]))[:k]]].sum()))
                counts.append([int(y[take].sum()),*found]);details.append(dict(task=task,balance=balance,project=p,selected_cases=k,positives=int(y[take].sum()),baseline_found=found[0],context_found=found[1]))
            counts=np.asarray(counts);rng=np.random.default_rng(20261014);diff=[]
            for _ in range(500):
                w=rng.multinomial(len(names),np.repeat(1/len(names),len(names)));positive=w@counts[:,0]
                if positive:diff.append(float(w@(counts[:,2]-counts[:,1])/positive))
            a=int(counts[:,1].sum());b=int(counts[:,2].sum());positive=int(y.sum())
            for rep,found in [('baseline',a),('context',b)]:
                expected=next(r for r in budgets if r['task']==task and r['variant']==balance+'_'+rep)
                if int(expected['positives_recovered'])!=found:raise ValueError('Independent budget recomputation differs')
            rows.append(dict(task=task,balance=balance,positives=positive,baseline_found=a,context_found=b,baseline_recall=a/positive,context_recall=b/positive,recall_difference=(b-a)/positive,ci_lower=float(np.quantile(diff,.025)),ci_upper=float(np.quantile(diff,.975)),valid_repeats=len(diff)))
    write_csv(OUT/'ranking_budget_uncertainty.csv',rows,list(rows[0]));write_csv(OUT/'ranking_budget_by_project.csv',details,list(details[0]))
    lines=['# Secondary within-project ranking diagnostic','',
        'The protocol declared top ceil(10%) ranked separately inside each project. This audit independently recomputes that metric and adds paired project-resampling uncertainty after inspecting the primary comparison. No model, threshold, feature or split is changed. It is a secondary diagnostic, not a replacement primary endpoint.','',
        '| Task / balance | Baseline recovered | Context recovered | Recall difference | 95% project interval |','|---|---:|---:|---:|---|']
    for r in rows:lines.append(f"| {r['task']} / {r['balance']} | {r['baseline_found']}/{r['positives']} | {r['context_found']}/{r['positives']} | {100*r['recall_difference']:+.2f} percentage points | [{100*r['ci_lower']:+.2f}, {100*r['ci_upper']:+.2f}] pp |")
    lines+=['','All variants select the same 8,691 original cases in aggregate (ceil(10%) within each project). These are source-case counts, not independent cause counts or measured rerun savings. The intervals resample fixed predictions over 30 projects and omit refitting/prior development uncertainty. They do not establish full-detector superiority or untouched confirmation.','']
    (OUT/'RANKING_DIAGNOSTIC.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
