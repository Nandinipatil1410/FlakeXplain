"""One predeclared development cycle after the inspected v0.1 pilot.

Fixed candidate grids; project-disjoint inner selection. No untouched-test claim.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import time
import warnings
import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import HashingVectorizer,TfidfTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer,StandardScaler
from train_pilot import ROOT,SEED,load_dataset,load_feature_table,reader,sha,write_csv,metrics,best_threshold,weighted_ap

ET_GRID=[dict(max_depth=12,min_samples_leaf=20,class_weight='balanced'),
         dict(max_depth=20,min_samples_leaf=5,class_weight='balanced'),
         dict(max_depth=12,min_samples_leaf=20,class_weight=None),
         dict(max_depth=20,min_samples_leaf=5,class_weight=None)]
LR_GRID=[dict(C=.1),dict(C=1.)]
MODEL_SPECS=[(kind,source) for kind in ('extra_trees','logistic') for source in ('v1_body','v1_context','v2_body','v2_context')]+[('text_logistic','text_body'),('text_logistic','text_context')]
HASH_PARAMS=dict(n_features=65536,alternate_sign=False,norm=None,lowercase=False,tokenizer=str.split,token_pattern=None,dtype=np.float32)

def build_model(kind,parameters):
    if kind=='extra_trees':
        return ExtraTreesClassifier(n_estimators=128,max_features='sqrt',random_state=SEED,n_jobs=4,bootstrap=False,**parameters)
    classifier=LogisticRegression(class_weight='balanced',solver='liblinear',max_iter=2000,tol=1e-3,random_state=SEED,**parameters)
    if kind=='logistic':
        return Pipeline([('log1p',FunctionTransformer(np.log1p)),('scale',StandardScaler()),('classifier',classifier)])
    return Pipeline([('tfidf',TfidfTransformer(sublinear_tf=True)),('classifier',classifier)])

def load_inputs():
    ids,y,meta,projects,folds,inner,old,body_cols,context_cols=load_dataset(ROOT/'dataset/v0.1')
    source=ROOT/'dataset/development-v0.2'; manifest=json.loads((source/'manifest.json').read_text())
    if manifest['dataset_manifest_sha256']!=sha(ROOT/'dataset/v0.1/manifest.json'):
        raise ValueError('Development cases reference a different dataset')
    for filename,digest in manifest['files'].items():
        if sha(source/filename)!=digest:
            raise ValueError('Development artifact changed: '+filename)
    if sha(ROOT/'scripts/prepare_development_features.py')!=manifest['extractor_sha256']:
        raise ValueError('Development extractor changed')
    schema=json.loads((source/'schema.json').read_text())
    body=load_feature_table(source/'features_body.csv.gz',schema['body_columns'],ids)
    context=load_feature_table(source/'features_context.csv.gz',schema['context_columns'],ids)
    xs=dict(v1_body=old['extra_trees_body'],v1_context=old['extra_trees_context'],v2_body=body,v2_context=np.hstack((body,context)))
    columns=dict(v1_body=body_cols,v1_context=body_cols+context_cols,v2_body=schema['body_columns'],v2_context=schema['body_columns']+schema['context_columns'])
    return ids,y,meta,projects,folds,inner,xs,columns,manifest

def add_text_inputs(xs,meta,manifest):
    path=ROOT/manifest['source_documents']
    if sha(path)!=manifest['source_documents_sha256']:
        raise ValueError('Source document checksum differs')
    documents={}
    with gzip.open(path,'rt',encoding='utf-8') as f:
        for line in f:
            r=json.loads(line)
            body=' '.join(r['body'].split()[:512]); ctx=' '.join(r['context'].split()[:1024])
            documents[r['context_id']]=(body,body+' '+ctx)
    hasher=HashingVectorizer(**HASH_PARAMS)
    for index,name in enumerate(('text_body','text_context')):
        # Stateless transform only: no full-data vocabulary, IDF or normalization fit.
        xs[name]=hasher.transform([documents[r['context_id']][index] for r in meta]).tocsr()
        print(f'{name}: stateless hashes prepared; nnz={xs[name].nnz}',flush=True)
    return hasher

def bootstrap_difference(y,a,b,projects,repeats=500):
    _,inverse=np.unique(projects,return_inverse=True); n=int(inverse.max()+1); rng=np.random.default_rng(SEED)
    differences=[]
    for _ in range(repeats):
        w=rng.multinomial(n,np.repeat(1/n,n))[inverse].astype(float)
        aa=weighted_ap(y,a,w); bb=weighted_ap(y,b,w)
        if aa is not None and bb is not None:
            differences.append(bb-aa)
    return dict(valid_repeats=len(differences),percentile_95_interval=list(map(float,np.quantile(differences,[.025,.975]))),
                limitation='Project resampling of fixed development OOF scores; no model refits, selection/development uncertainty or untouched confirmation.')

def train(args):
    start=time.perf_counter(); out=args.output; out.mkdir(parents=True,exist_ok=True)
    if (out/'protocol.json').exists():
        raise ValueError('Use a new run directory; existing protocol is immutable')
    ids,y,meta,projects,folds,inner,xs,columns,feature_manifest=load_inputs()
    protocol=dict(stage='development after inspected pilot; outer results are not untouched confirmation',
                  primary_comparison='v2 Extra Trees body+context versus v2 body using the same candidate grid and inner-AP selection',
                  secondary='v1/v2 numeric Logistic Regression, tuned v1 Extra Trees, AST-token hashed TF-IDF Logistic Regression',
                  models=[kind+'_'+source for kind,source in MODEL_SPECS],extra_trees_grid=ET_GRID,logistic_C_grid=LR_GRID,
                  common_extra_trees=dict(n_estimators=128,max_features='sqrt',bootstrap=False,random_state=SEED,n_jobs=4),
                  common_logistic=dict(solver='liblinear',class_weight='balanced',max_iter=2000,tol=1e-3,random_state=SEED),
                  numeric_preprocessing='ET raw numeric; LR log1p then StandardScaler fitted only inside each training partition',
                  text='512 body / 1024 context AST tokens; stateless unsigned hashing to 65536 columns; sublinear TF-IDF fitted on training partitions only. No learned full-data vocabulary.',
                  selection='Maximum pooled four-inner-fold OOF average precision; ties choose first listed candidate',
                  thresholds='Report fixed 0.5 and maximum inner-OOF-F1 threshold for the selected candidate; ties choose higher threshold',
                  balance='All original 96118 cases; no SMOTE, downsampling, duplication or project exclusion',
                  seed=SEED,feature_columns=columns,
                  inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'dataset/v0.1/manifest.json',ROOT/'dataset/development-v0.2/manifest.json',
                      ROOT/'scripts/train_development.py',ROOT/'scripts/train_pilot.py',ROOT/'requirements-pilot.txt']})
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    hasher=add_text_inputs(xs,meta,feature_manifest)
    model_root=ROOT/'local-evidence/development-models'/out.name; model_root.mkdir(parents=True,exist_ok=True)
    model_names=protocol['models']; scores={name:np.full(len(y),np.nan) for name in model_names}; thresholds={name:np.full(len(y),np.nan) for name in model_names}
    inner_store={}; search=[]; selection=[]; fold_metrics=[]; saved=[]; warnings_count=0
    for fold in range(5):
        train=folds!=fold; test=~train
        inner_assignment={r['project']:int(r['inner_validation_fold']) for r in inner if int(r['outer_test_fold'])==fold}
        inner_ids=np.array([inner_assignment.get(p,-1) for p in projects])
        for kind,source in MODEL_SPECS:
            name=kind+'_'+source; x=xs[source]; grid=ET_GRID if kind=='extra_trees' else LR_GRID
            best=None
            for candidate,parameters in enumerate(grid):
                probability=np.full(len(y),np.nan)
                for inner_fold in range(4):
                    fit=train&(inner_ids!=inner_fold); valid=train&(inner_ids==inner_fold)
                    if set(projects[fit])&set(projects[valid]) or set(projects[fit])&set(projects[test]):
                        raise ValueError('Project leakage')
                    model=build_model(kind,parameters)
                    with warnings.catch_warnings(record=True) as notices:
                        warnings.simplefilter('always',ConvergenceWarning); model.fit(x[fit],y[fit])
                        warnings_count+=sum(issubclass(w.category,ConvergenceWarning) for w in notices)
                    probability[valid]=model.predict_proba(x[valid])[:,1]
                    del model
                if not np.isfinite(probability[train]).all() or np.isfinite(probability[test]).any():
                    raise ValueError('Inner OOF partition differs')
                ap=weighted_ap(y[train],probability[train],np.ones(train.sum()))
                search.append(dict(outer_fold=fold,model=name,candidate=candidate,parameters=json.dumps(parameters,sort_keys=True),inner_oof_ap=ap))
                if best is None or ap>best[0]+1e-12:
                    best=(ap,candidate,parameters,probability)
            ap,candidate,parameters,inner_probability=best
            threshold,inner_f1=best_threshold(y[train],inner_probability[train])
            inner_store[f'{name}__outer_{fold}']=inner_probability
            model=build_model(kind,parameters); fit_start=time.perf_counter(); model.fit(x[train],y[train]); fit_seconds=time.perf_counter()-fit_start
            probability=model.predict_proba(x[test])[:,1]
            scores[name][test]=probability; thresholds[name][test]=threshold
            selection.append(dict(model=name,outer_fold=fold,selected_candidate=candidate,parameters=json.dumps(parameters,sort_keys=True),
                                  inner_oof_ap=ap,inner_oof_f1=inner_f1,threshold=threshold,outer_training_cases=int(train.sum()),
                                  train_projects='|'.join(sorted(set(projects[train]))),test_projects='|'.join(sorted(set(projects[test])))))
            for mode,t in [('fixed_0.5',.5),('inner_f1',threshold)]:
                fold_metrics.append(dict(model=name,outer_fold=fold,threshold_mode=mode,threshold=t,**metrics(y[test],probability,probability>=t,ids[test])))
            path=model_root/f'{name}-outer-{fold}.joblib'
            payload=dict(estimator=model,input_source=source,feature_columns=columns.get(source),hasher=hasher if source.startswith('text_') else None,
                         threshold=threshold,train_projects=sorted(set(projects[train])),test_projects=sorted(set(projects[test])),
                         dataset_manifest_sha256=sha(ROOT/'dataset/v0.1/manifest.json'),development_manifest_sha256=sha(ROOT/'dataset/development-v0.2/manifest.json'))
            joblib.dump(payload,path,compress=3); saved.append(dict(model=name,outer_fold=fold,path=str(path.relative_to(ROOT)),sha256=sha(path),fit_seconds=fit_seconds))
            print(f'outer={fold} {name}: selected={candidate}, inner AP={ap:.5f}, held-out AP={fold_metrics[-1]["average_precision"]:.5f}',flush=True)
            del model,payload
    pooled=[]; by_project=[]; family_weighted=[]
    family_counts=Counter(r['source_family_id'] for r in meta); family_weights=np.array([1/family_counts[r['source_family_id']] for r in meta])
    for name in model_names:
        if not np.isfinite(scores[name]).all():
            raise ValueError('Outer OOF incomplete')
        for mode in ('fixed_0.5','inner_f1'):
            prediction=scores[name]>=(.5 if mode=='fixed_0.5' else thresholds[name])
            pooled.append(dict(model=name,threshold_mode=mode,**metrics(y,scores[name],prediction,ids)))
            weighted=metrics(y,scores[name],prediction,ids,weights=family_weights)
            weighted.pop('recall_at_top_10_percent'); weighted.pop('top_10_percent_cases')
            family_weighted.append(dict(model=name,threshold_mode=mode,**weighted))
            for project in sorted(set(projects)):
                mask=projects==project
                by_project.append(dict(model=name,threshold_mode=mode,project=project,outer_fold=int(folds[mask][0]),**metrics(y[mask],scores[name][mask],prediction[mask],ids[mask])))
    bootstrap=bootstrap_difference(y,scores['extra_trees_v2_body'],scores['extra_trees_v2_context'],projects)
    rows=(dict(example_id=str(ids[i]),project=str(projects[i]),outer_fold=int(folds[i]),label=int(y[i]),
               **{name+'_score':float(scores[name][i]) for name in model_names},
               **{name+'_threshold':float(thresholds[name][i]) for name in model_names}) for i in range(len(y)))
    fields=['example_id','project','outer_fold','label']+[name+'_score' for name in model_names]+[name+'_threshold' for name in model_names]
    write_csv(out/'oof_predictions.csv.gz',rows,fields)
    for filename,table in [('metrics_pooled.csv',pooled),('metrics_by_project.csv',by_project),('metrics_by_fold.csv',fold_metrics),
                           ('inner_candidate_search.csv',search),('selected_configurations.csv',selection),('metrics_family_weighted.csv',family_weighted)]:
        write_csv(out/filename,table,list(table[0]))
    inner_file=model_root/'selected_inner_oof.npz'; np.savez_compressed(inner_file,**inner_store)
    result=dict(status='completed',stage='development, not untouched confirmation',cases=len(y),positives=int(y.sum()),projects=len(set(projects)),
                elapsed_seconds=time.perf_counter()-start,convergence_warnings=warnings_count,pooled=pooled,primary_context_minus_body_ap=
                next(r['average_precision'] for r in pooled if r['model']=='extra_trees_v2_context')-next(r['average_precision'] for r in pooled if r['model']=='extra_trees_v2_body'),
                primary_paired_project_bootstrap=bootstrap,models=saved,inner_oof=dict(path=str(inner_file.relative_to(ROOT)),sha256=sha(inner_file)))
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    manifest=dict(status='completed',files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                  implementation_sha256=sha(Path(__file__)),protocol_sha256=sha(out/'protocol.json'))
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(status='completed',elapsed_seconds=result['elapsed_seconds'],convergence_warnings=warnings_count,primary_delta=result['primary_context_minus_body_ap']),indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,default=ROOT/'reports/development-v0.2')
    train(parser.parse_args())
