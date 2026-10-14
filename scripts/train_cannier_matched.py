"""Matched CANNIER-feature ablation, retaining natural imbalance as primary.

Author-SMOTE sensitivity is explicitly separate. Original predictions are never fit.
"""
import gc,json,time
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
import sklearn,imblearn
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import average_precision_score,matthews_corrcoef,roc_curve
from prepare_cannier_matched import LOCAL,OUT,DATA,TASKS
from train_pilot import ROOT,reader,sha,write_csv,load_feature_table,metrics

SEED=20261014
VARIANTS=[(balance,representation) for balance in ('natural','author_smote_sensitivity') for representation in ('baseline','context')]

def mcc_threshold(y,score):
    fpr,tpr,thresholds=roc_curve(y,score,drop_intermediate=False)
    tp=tpr*y.sum();fp=fpr*(len(y)-y.sum());fn=y.sum()-tp;tn=len(y)-y.sum()-fp
    denom=np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn));mcc=np.divide(tp*tn-fp*fn,denom,out=np.zeros_like(denom),where=denom>0)
    finite=np.isfinite(thresholds);best=mcc[finite].max();indices=np.flatnonzero(finite&np.isclose(mcc,best,rtol=0,atol=1e-12))
    return float(thresholds[indices[0]])

def load_inputs():
    manifest=json.loads((DATA/'manifest.json').read_text())
    for name,value in manifest['files'].items():
        if sha(DATA/name)!=value:raise ValueError('Matched dataset changed: '+name)
    schema=json.loads((DATA/'schema.json').read_text());labelrows=list(reader(DATA/'labels.csv.gz'));ids=np.array([r['example_id'] for r in labelrows])
    index={r['example_id']:r for r in reader(DATA/'metadata.csv.gz')};meta=[index[k] for k in ids];projects=np.array([r['project'] for r in meta])
    outer={r['project']:int(r['outer_fold']) for r in reader(DATA/'splits_outer.csv')};folds=np.asarray([outer[p] for p in projects])
    b=load_feature_table(DATA/'features_baseline.csv.gz',schema['baseline_columns'],ids)
    c=load_feature_table(DATA/'features_context.csv.gz',schema['context_columns'],ids)
    return ids,labelrows,meta,projects,folds,dict(baseline=b,context=np.hstack((b,c))),dict(baseline=schema['baseline_columns'],context=schema['baseline_columns']+schema['context_columns'])

def fit(x,y,task,balance,seed):
    n=100 if task=='NOD-vs-Rest' else 75
    before=len(y)
    if balance=='author_smote_sensitivity':
        if min(np.bincount(y,minlength=2))<6:raise ValueError('Default author SMOTE infeasible; do not reduce neighbors silently')
        x,y=SMOTE(random_state=seed).fit_resample(x,y)
    model=ExtraTreesClassifier(n_estimators=n,max_depth=None,min_samples_leaf=1,max_features='sqrt',bootstrap=False,class_weight=None,random_state=seed,n_jobs=4)
    model.fit(x,y);return model,dict(original_fit_cases=before,actual_fit_cases=len(y),actual_fit_positives=int(y.sum()))

def original_reference():
    items=np.load(LOCAL/'output/items.npy',allow_pickle=False);allrows=[]
    specs=[('NOD-vs-Rest',3,None,'ExtraTrees',100),('NOD-vs-Victim',3,5,'RandomForest',75),('Victim-vs-Rest',4,None,'ExtraTrees',75),('Polluter-vs-Rest',6,None,'RandomForest',100)]
    for task,column,domain,family,trees in specs:
        y=items[:,column].astype(int)
        if domain is not None:y=y[items[:,domain].astype(bool)]
        name=f'{task}_18_{family}_{trees}_SMOTE_1.npy';path=LOCAL/'output/preds'/name;scores=np.load(path,allow_pickle=False)
        if scores.shape!=(30,len(y)):raise ValueError('Original predictions shape differs')
        for repeat,score in enumerate(scores):
            mcc=float(matthews_corrcoef(y,score>=.5));allrows.append(dict(task=task,repeat=repeat,cases=len(y),positives=int(y.sum()),average_precision=float(average_precision_score(y,score)),signed_mcc=mcc,authors_absolute_mcc=abs(mcc),predictions_sha256=sha(path)))
    write_csv(OUT/'authors_released_predictions_metrics.csv',allrows,list(allrows[0]))
    summary=[]
    for task,*_ in specs:
        rows=[r for r in allrows if r['task']==task]
        summary.append(dict(task=task,cases=rows[0]['cases'],positives=rows[0]['positives'],repeats=30,derived_ap_mean=float(np.mean([r['average_precision'] for r in rows])),derived_ap_std=float(np.std([r['average_precision'] for r in rows])),signed_mcc_mean=float(np.mean([r['signed_mcc'] for r in rows])),authors_absolute_mcc_mean=float(np.mean([r['authors_absolute_mcc'] for r in rows]))))
    write_csv(OUT/'authors_released_predictions_summary.csv',summary,list(summary[0]));print('Original released-score metrics:',json.dumps(summary),flush=True)

def train():
    if (OUT/'run_manifest.json').exists():raise ValueError('Matched run already complete')
    protocol=json.loads((OUT/'protocol.json').read_text());modelroot=LOCAL/'models';modelroot.mkdir(exist_ok=True)
    if (OUT/'training_protocol.json').exists():raise ValueError('Training protocol already exists; preserve incomplete run instead of overwriting')
    runprotocol=dict(created_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(OUT/'protocol.json'),dataset_manifest_sha256=sha(DATA/'manifest.json'),implementation_sha256=sha(ROOT/'scripts/train_cannier_matched.py'),requirements_sha256=sha(ROOT/'requirements-cannier-matched.txt'),sklearn=sklearn.__version__,imbalanced_learn=imblearn.__version__,variants=VARIANTS,seed=SEED)
    (OUT/'training_protocol.json').write_text(json.dumps(runprotocol,indent=2)+'\n')
    ids,labels,meta,projects,folds,xs,columns=load_inputs();inner=list(reader(DATA/'splits_inner.csv'));start=time.perf_counter()
    original_reference();allmetrics=[];projectmetrics=[];training=[];models=[];budget=[]
    for task,labelkey in [('NOD-vs-Rest','nod'),('Victim-vs-Rest','victim')]:
        y=np.asarray([int(r[labelkey]) for r in labels]);taskroot=OUT/task;taskroot.mkdir(exist_ok=True)
        scores={};thresholds={}
        for balance,representation in VARIANTS:
            name=balance+'_'+representation;x=xs[representation];score=np.full(len(y),np.nan);threshold=np.full(len(y),np.nan)
            for fold in range(5):
                train=folds!=fold;test=~train;assignment={r['project']:int(r['inner_fold']) for r in inner if int(r['outer_fold'])==fold};innerids=np.asarray([assignment.get(p,-1) for p in projects]);inscore=np.full(len(y),np.nan)
                for innerfold in range(4):
                    fitmask=train&(innerids!=innerfold);valid=train&(innerids==innerfold)
                    if set(projects[fitmask])&set(projects[valid]) or set(projects[fitmask])&set(projects[test]):raise ValueError('Project leakage')
                    if len(np.unique(y[fitmask]))!=2:raise ValueError('Task cannot support project-held-out inner fit')
                    model,details=fit(x[fitmask],y[fitmask],task,balance,SEED+fold*10+innerfold)
                    inscore[valid]=model.predict_proba(x[valid])[:,1];del model;gc.collect()
                if not np.isfinite(inscore[train]).all() or np.isfinite(inscore[test]).any():raise ValueError('Incomplete or leaked inner OOF')
                cut=mcc_threshold(y[train],inscore[train]);model,details=fit(x[train],y[train],task,balance,SEED+fold*10+9)
                score[test]=model.predict_proba(x[test])[:,1];threshold[test]=cut
                modelpath=modelroot/(task+'_'+name+'_'+str(fold)+'.joblib')
                innerpath=modelroot/(task+'_'+name+'_'+str(fold)+'_inner.npz');np.savez_compressed(innerpath,scores=inscore)
                joblib.dump(dict(model=model,columns=columns[representation],threshold=cut,outer_fold=fold,training_projects=sorted(set(projects[train])),test_projects=sorted(set(projects[test])),task=task,balance=balance,representation=representation),modelpath,compress=3)
                models.append(dict(task=task,variant=name,outer_fold=fold,path=str(modelpath.relative_to(ROOT)),sha256=sha(modelpath),inner_path=str(innerpath.relative_to(ROOT)),inner_sha256=sha(innerpath)))
                training.append(dict(task=task,variant=name,outer_fold=fold,threshold=cut,train_positives=int(y[train].sum()),test_positives=int(y[test].sum()),**details))
                print(f'{task} {name} fold {fold} complete; threshold={cut:.6g}',flush=True);del model;gc.collect()
            scores[name]=score;thresholds[name]=threshold
            for mode in ('fixed_0.5','inner_mcc'):
                prediction=score>=(.5 if mode=='fixed_0.5' else threshold)
                allmetrics.append(dict(task=task,variant=name,threshold_mode=mode,**metrics(y,score,prediction,ids)))
                for p in sorted(set(projects)):
                    take=projects==p;projectmetrics.append(dict(task=task,variant=name,threshold_mode=mode,project=p,**metrics(y[take],score[take],prediction[take],ids[take])))
            selected=0;found=0
            for p in sorted(set(projects)):
                take=np.flatnonzero(projects==p);k=int(np.ceil(.1*len(take)));top=take[np.lexsort((ids[take],-score[take]))[:k]];selected+=k;found+=int(y[top].sum())
            budget.append(dict(task=task,variant=name,selected_cases=selected,positives_recovered=found,positives=int(y.sum()),recall=found/y.sum()))
        rows=[]
        for i,key in enumerate(ids):
            r=dict(example_id=key,project=projects[i],outer_fold=int(folds[i]),label=int(y[i]),source_family_id=meta[i]['source_family_id'])
            for name in scores:r[name+'_score']=float(scores[name][i]);r[name+'_threshold']=float(thresholds[name][i])
            rows.append(r)
        write_csv(taskroot/'oof_predictions.csv.gz',rows,list(rows[0]))
    write_csv(OUT/'metrics_pooled.csv',allmetrics,list(allmetrics[0]));write_csv(OUT/'metrics_by_project.csv',projectmetrics,list(projectmetrics[0]));write_csv(OUT/'training_partitions.csv',training,list(training[0]));write_csv(OUT/'per_project_top10_budget.csv',budget,list(budget[0]))
    result=dict(status='trained',elapsed_seconds=time.perf_counter()-start,models=models,fit_count=200,protocol_sha256=sha(OUT/'protocol.json'),training_protocol_sha256=sha(OUT/'training_protocol.json'),dataset_manifest_sha256=sha(DATA/'manifest.json'),files={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='run_manifest.json'})
    (OUT/'run_manifest.json').write_text(json.dumps(result,indent=2)+'\n');print('Matched fits complete:',result['elapsed_seconds'],flush=True)

if __name__=='__main__':train()
