"""Fixed-configuration, nested project-disjoint Extra Trees pilot.

Predictors are loaded exclusively from schema allowlisted numeric feature tables.
No test outcome evidence or identity/provenance column is passed to an estimator.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import sys
import time

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve

ROOT=Path(__file__).resolve().parents[1]
SEED=20261013
PARAMETERS=dict(n_estimators=128,criterion='gini',max_depth=20,min_samples_split=2,
                min_samples_leaf=5,max_features='sqrt',bootstrap=False,class_weight='balanced',
                random_state=SEED,n_jobs=4)
VARIANTS=('extra_trees_body','extra_trees_context')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()

def reader(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8',newline='') as f:
        yield from csv.DictReader(f)

def write_csv(path,rows,fields):
    def write(f):
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    if path.suffix=='.gz':
        with path.open('wb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz:
            with io.TextIOWrapper(gz,encoding='utf-8',newline='') as f:
                write(f)
    else:
        with path.open('w',encoding='utf-8',newline='') as f:
            write(f)

def load_feature_table(path,columns,ids):
    positions={k:i for i,k in enumerate(ids)}
    seen=set(); data=np.empty((len(ids),len(columns)),dtype=np.float32)
    for r in reader(path):
        if set(r)!=set(columns)|{'example_id'}:
            raise ValueError('Unexpected predictor schema: '+str(path))
        key=r['example_id']
        if key in seen or key not in positions:
            raise ValueError('Duplicate/unmatched feature ID')
        seen.add(key); data[positions[key]]=[float(r[k]) for k in columns]
    if seen!=set(ids) or not np.isfinite(data).all() or (data<0).any():
        raise ValueError('Incomplete/invalid features')
    return data

def load_dataset(dataset):
    manifest=json.loads((dataset/'manifest.json').read_text())
    for name,value in manifest['files'].items():
        if sha(dataset/name)!=value:
            raise ValueError('Frozen dataset checksum differs: '+name)
    schema=json.loads((dataset/'schema.json').read_text())
    labels=list(reader(dataset/'labels.csv.gz'))
    ids=np.array([r['example_id'] for r in labels])
    if len(set(ids))!=len(ids):
        raise ValueError('Duplicate labels')
    y=np.array([int(r['label']) for r in labels],dtype=np.int8)
    if set(y)!={0,1}:
        raise ValueError('Expected both binary classes')
    del labels
    positions={key:i for i,key in enumerate(ids)}
    meta=[None]*len(ids)
    wanted=('project','source_family_id','membership','context_id','context_bounded','unresolved_fixture_count','source_path','source_qualname','junit_name')
    for r in reader(dataset/'metadata.csv.gz'):
        i=positions.get(r['example_id'])
        if i is None or meta[i] is not None:
            raise ValueError('Metadata join differs')
        meta[i]={k:r[k] for k in wanted}
    if any(r is None for r in meta):
        raise ValueError('Missing metadata')
    body_columns=schema['predictor_tables']['features_body.csv.gz']
    context_columns=schema['predictor_tables']['features_context.csv.gz']
    body=load_feature_table(dataset/'features_body.csv.gz',body_columns,ids)
    context=load_feature_table(dataset/'features_context.csv.gz',context_columns,ids)
    xs={VARIANTS[0]:body,VARIANTS[1]:np.hstack((body,context))}
    projects=np.array([r['project'] for r in meta])
    outer=list(reader(dataset/'splits_outer.csv')); inner=list(reader(dataset/'splits_inner.csv'))
    assignment={r['project']:int(r['outer_test_fold']) for r in outer}
    if set(assignment)!=set(projects) or len(assignment)!=len(outer):
        raise ValueError('Outer project assignment differs')
    folds=np.array([assignment[p] for p in projects],dtype=np.int8)
    for outer_fold in range(5):
        selected=[r for r in inner if int(r['outer_test_fold'])==outer_fold]
        if {r['project'] for r in selected}!={p for p in assignment if assignment[p]!=outer_fold}:
            raise ValueError('Inner folds include held-out projects or omit training projects')
        if len({r['project'] for r in selected})!=len(selected):
            raise ValueError('Duplicate inner project assignment')
    return ids,y,meta,projects,folds,inner,xs,body_columns,context_columns

def best_threshold(y,score):
    if len(np.unique(y))!=2 or not np.isfinite(score).all():
        raise ValueError('Threshold requires complete inner OOF scores with both classes')
    precision,recall,thresholds=precision_recall_curve(y,score)
    denom=precision[:-1]+recall[:-1]
    f1=np.divide(2*precision[:-1]*recall[:-1],denom,out=np.zeros_like(denom),where=denom>0)
    # Conservative deterministic tie-breaking: highest threshold at maximal F1.
    candidates=np.flatnonzero(np.isclose(f1,f1.max(),rtol=0,atol=1e-12))
    index=candidates[-1]
    return float(thresholds[index]),float(f1[index])

def metrics(y,score,prediction,ids,weights=None):
    y=np.asarray(y); prediction=np.asarray(prediction,dtype=bool)
    w=np.ones(len(y)) if weights is None else np.asarray(weights,dtype=float)
    tp=float(w[(y==1)&prediction].sum()); fp=float(w[(y==0)&prediction].sum())
    tn=float(w[(y==0)&~prediction].sum()); fn=float(w[(y==1)&~prediction].sum())
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else None
    f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0
    denominator=(tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
    mcc=(tp*tn-fp*fn)/math.sqrt(denominator) if denominator else 0.0
    # IDs break tied scores independently of labels; budget applies to cases, not families.
    budget=math.ceil(.1*len(y))
    order=np.lexsort((np.asarray(ids),-np.asarray(score)))
    top=order[:budget]
    top_recall=float((y[top]==1).sum()/(y==1).sum()) if (y==1).any() else None
    return dict(cases=len(y),positives=int((y==1).sum()),prevalence=float((y==1).mean()),
                average_precision=float(average_precision_score(y,score,sample_weight=w)) if (y==1).any() else None,
                precision=precision,recall=recall,f1=f1,mcc=mcc,
                false_positives_per_1000_negative=1000*fp/(fp+tn) if fp+tn else None,
                recall_at_top_10_percent=top_recall,top_10_percent_cases=budget,
                tp=tp,fp=fp,tn=tn,fn=fn,predicted_positive=int(prediction.sum()),
                precision_defined=bool(tp+fp),recall_defined=bool(tp+fn),mcc_denominator_nonzero=bool(denominator))

def weighted_ap(y,score,weights):
    """Average precision with grouped score ties, also used for cluster resampling."""
    order=np.argsort(-score,kind='stable'); yy=y[order]; ww=weights[order]
    ends=np.r_[np.flatnonzero(np.diff(score[order])!=0),len(y)-1]
    pos=np.cumsum(yy*ww)[ends]; total=np.cumsum(ww)[ends]
    if not pos[-1]:
        return None
    precision=np.divide(pos,total,out=np.zeros_like(pos,dtype=float),where=total>0)
    return float(np.sum(precision*np.diff(np.r_[0,pos]))/pos[-1])

def paired_project_bootstrap(y,scores,projects,repeats=500):
    names,inverse=np.unique(projects,return_inverse=True)
    rng=np.random.default_rng(SEED)
    differences=[]
    for _ in range(repeats):
        counts=rng.multinomial(len(names),np.repeat(1/len(names),len(names)))
        weights=counts[inverse].astype(float)
        a=weighted_ap(y,scores[VARIANTS[0]],weights); b=weighted_ap(y,scores[VARIANTS[1]],weights)
        if a is not None and b is not None:
            differences.append(b-a)
    return dict(metric='context minus body average precision',resampling_unit='project',repeats=repeats,
                valid_repeats=len(differences),seed=SEED,
                percentile_95_interval=[float(v) for v in np.quantile(differences,[.025,.975])],
                limitation='Conditional on fixed out-of-fold predictions; no model refitting or feature-development uncertainty. Pilot diagnostic, not definitive significance.')

def train(args):
    output=args.output; output.mkdir(parents=True,exist_ok=True)
    if (output/'run_manifest.json').exists() or (output/'protocol.json').exists():
        raise ValueError('Use a new output directory; do not overwrite an existing pilot')
    start=time.perf_counter()
    ids,y,meta,projects,folds,inner,xs,body_columns,context_columns=load_dataset(args.dataset)
    model_root=ROOT/'local-evidence/pilot-models'/output.name
    model_root.mkdir(parents=True,exist_ok=True)
    protocol=dict(stage='pilot; all frozen outer folds are development evaluation after inspection',
                  primary_comparison='Paired pooled outer-OOF average precision: body versus body+context Extra Trees',
                  secondary_metrics=['precision','recall','F1','MCC','false positives per 1000 negatives','recall at top-ranked 10%'],
                  hyperparameter_tuning='None; one fixed configuration shared by both variants',
                  parameters=PARAMETERS,feature_columns={VARIANTS[0]:body_columns,VARIANTS[1]:body_columns+context_columns},
                  thresholds=dict(primary=0.5,secondary='Per-outer-fold maximum F1 on four inner project-separated OOF folds; highest threshold wins ties'),
                  class_balance='All cases retained; balanced class weights computed from each fit training subset only',
                  model_selection='No post-result selection or refitting on the full dataset in this pilot',
                  splits='Dataset v0.1 frozen five outer and four inner project folds',
                  ranking_ties='Lexicographic example_id tie-break, independent of labels',
                  undefined_metrics='Zero-positive project AP/recall are null; precision with no predicted positives and degenerate MCC use zero with flags',
                  bootstrap_repeats=500,
                  package_versions=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__,joblib=joblib.__version__,platform=platform.platform()),
                  inputs={str(p.relative_to(ROOT)):sha(p) for p in [args.dataset/'manifest.json',ROOT/'scripts/train_pilot.py',ROOT/'requirements-pilot.txt']})
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    scores={v:np.full(len(y),np.nan) for v in VARIANTS}
    predictions={v:np.zeros(len(y),dtype=np.int8) for v in VARIANTS}
    thresholds={v:np.full(len(y),np.nan) for v in VARIANTS}
    prior=np.full(len(y),np.nan); fold_metrics=[]; threshold_log=[]; models=[]; importance=[]
    for fold in range(5):
        train_mask=folds!=fold; test_mask=~train_mask
        inner_assignment={r['project']:int(r['inner_validation_fold']) for r in inner if int(r['outer_test_fold'])==fold}
        inner_ids=np.array([inner_assignment.get(p,-1) for p in projects])
        if (inner_ids[test_mask]!=-1).any():
            raise ValueError('Held-out project entered inner training')
        prior[test_mask]=float(y[train_mask].mean())
        for variant in VARIANTS:
            x=xs[variant]; inner_scores=np.full(len(y),np.nan)
            fit_seconds=0.0
            for inner_fold in range(4):
                fit=train_mask&(inner_ids!=inner_fold); valid=train_mask&(inner_ids==inner_fold)
                if set(projects[fit])&set(projects[valid]) or set(projects[fit])&set(projects[test_mask]):
                    raise ValueError('Project leakage in fit partition')
                if set(y[fit])!={0,1} or set(y[valid])!={0,1}:
                    raise ValueError('Inner partition lacks a label class')
                model=ExtraTreesClassifier(**PARAMETERS)
                fit_start=time.perf_counter(); model.fit(x[fit],y[fit]); fit_seconds+=time.perf_counter()-fit_start
                inner_scores[valid]=model.predict_proba(x[valid])[:,1]
                print(f'outer={fold} {variant} inner={inner_fold}: fit complete',flush=True)
                del model
            if not np.isfinite(inner_scores[train_mask]).all() or np.isfinite(inner_scores[test_mask]).any():
                raise ValueError('Inner OOF coverage differs')
            threshold,inner_f1=best_threshold(y[train_mask],inner_scores[train_mask])
            threshold_log.append(dict(model=variant,outer_fold=fold,threshold=threshold,inner_oof_f1=inner_f1,
                                      threshold_cases=int(train_mask.sum()),threshold_positive_cases=int(y[train_mask].sum()),
                                      train_projects='|'.join(sorted(set(projects[train_mask]))),test_projects='|'.join(sorted(set(projects[test_mask])))))
            model=ExtraTreesClassifier(**PARAMETERS)
            fit_start=time.perf_counter(); model.fit(x[train_mask],y[train_mask]); outer_fit_seconds=time.perf_counter()-fit_start
            probability=model.predict_proba(x[test_mask])[:,1]
            scores[variant][test_mask]=probability; thresholds[variant][test_mask]=threshold
            predictions[variant][test_mask]=(probability>=threshold).astype(np.int8)
            for mode,pred in [('fixed_0.5',probability>=.5),('inner_f1',probability>=threshold)]:
                fold_metrics.append(dict(model=variant,outer_fold=fold,threshold_mode=mode,threshold=.5 if mode=='fixed_0.5' else threshold,
                                         **metrics(y[test_mask],probability,pred,ids[test_mask])))
            filename=model_root/f'{variant}-outer-{fold}.joblib'
            joblib.dump(dict(estimator=model,feature_columns=protocol['feature_columns'][variant],threshold=threshold,
                             train_projects=sorted(set(projects[train_mask])),test_projects=sorted(set(projects[test_mask])),
                             dataset_manifest_sha256=sha(args.dataset/'manifest.json')),filename,compress=3)
            models.append(dict(model=variant,outer_fold=fold,path=str(filename.relative_to(ROOT)),sha256=sha(filename),
                               inner_fit_seconds=fit_seconds,outer_fit_seconds=outer_fit_seconds))
            for column,value in zip(protocol['feature_columns'][variant],model.feature_importances_):
                importance.append(dict(model=variant,outer_fold=fold,feature=column,impurity_importance=float(value)))
            ap=fold_metrics[-1]['average_precision']
            print(f'outer={fold} {variant}: held-out AP={ap:.6f}, inner-selected threshold={threshold:.6f}',flush=True)
            del model
    if not all(np.isfinite(scores[v]).all() and np.isfinite(thresholds[v]).all() for v in VARIANTS):
        raise ValueError('Outer OOF scores missing')
    scores['training_prevalence']=prior
    scores['body_size_heuristic']=xs[VARIANTS[0]][:,body_columns.index('body_lines')].astype(float)
    aggregate=[]; per_project=[]; sensitivity=[]
    family_counts=Counter(r['source_family_id'] for r in meta)
    family_weights=np.array([1/family_counts[r['source_family_id']] for r in meta])
    for name,score in scores.items():
        modes=['fixed_0.5','inner_f1'] if name in VARIANTS else ['reference']
        for mode in modes:
            prediction=predictions[name] if mode=='inner_f1' else score>=.5 if name in VARIANTS else np.zeros(len(y),dtype=bool)
            aggregate.append(dict(model=name,threshold_mode=mode,**metrics(y,score,prediction,ids)))
            for project in sorted(set(projects)):
                mask=projects==project
                per_project.append(dict(model=name,threshold_mode=mode,project=project,outer_fold=int(folds[mask][0]),
                                        membership=meta[np.flatnonzero(mask)[0]]['membership'],**metrics(y[mask],score[mask],prediction[mask],ids[mask])))
            if name in VARIANTS:
                values=metrics(y,score,prediction,ids,weights=family_weights)
                values.pop('recall_at_top_10_percent'); values.pop('top_10_percent_cases')
                sensitivity.append(dict(model=name,threshold_mode=mode,analysis='Each defining source family has total weight 1; parameters/inherited cases share weight',**values))
    bootstrap=paired_project_bootstrap(y,scores,projects)
    rows=(dict(example_id=str(ids[i]),project=str(projects[i]),source_family_id=meta[i]['source_family_id'],outer_fold=int(folds[i]),label=int(y[i]),
               body_score=float(scores[VARIANTS[0]][i]),context_score=float(scores[VARIANTS[1]][i]),
               body_fixed_prediction=int(scores[VARIANTS[0]][i]>=.5),context_fixed_prediction=int(scores[VARIANTS[1]][i]>=.5),
               body_inner_threshold=float(thresholds[VARIANTS[0]][i]),context_inner_threshold=float(thresholds[VARIANTS[1]][i]),
               body_inner_prediction=int(predictions[VARIANTS[0]][i]),context_inner_prediction=int(predictions[VARIANTS[1]][i]),
               training_prevalence_score=float(prior[i]),body_size_score=float(scores['body_size_heuristic'][i])) for i in range(len(y)))
    fields=['example_id','project','source_family_id','outer_fold','label','body_score','context_score','body_fixed_prediction','context_fixed_prediction',
            'body_inner_threshold','context_inner_threshold','body_inner_prediction','context_inner_prediction','training_prevalence_score','body_size_score']
    write_csv(output/'oof_predictions.csv.gz',rows,fields)
    for filename,table in [('metrics_pooled.csv',aggregate),('metrics_by_fold.csv',fold_metrics),('metrics_by_project.csv',per_project),
                           ('threshold_selection.csv',threshold_log),('feature_importance.csv',importance),('metrics_source_family_weighted.csv',sensitivity)]:
        write_csv(output/filename,table,list(table[0]))
    result=dict(stage='pilot',cases=len(y),positives=int(y.sum()),projects=len(set(projects)),dataset_manifest_sha256=sha(args.dataset/'manifest.json'),
                pooled=aggregate,paired_project_bootstrap=bootstrap,elapsed_seconds=time.perf_counter()-start,
                model_artifacts=models,metric_definition='Average precision is sklearn average_precision_score, not trapezoidal PR area.',
                reference_note='Both references predict all-negative. Size heuristic only provides ranking scores; its binary metrics are the all-negative reference, not a fitted threshold.')
    (output/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    manifest=dict(status='completed',protocol_sha256=sha(output/'protocol.json'),
                  files={p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()},
                  implementation_sha256=sha(Path(__file__)),dataset_manifest_sha256=sha(args.dataset/'manifest.json'))
    (output/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(status='completed',elapsed_seconds=result['elapsed_seconds'],pooled=aggregate,bootstrap=bootstrap),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',type=Path,default=ROOT/'dataset/v0.1')
    parser.add_argument('--output',type=Path,default=ROOT/'reports/pilot-v0.1')
    train(parser.parse_args())
