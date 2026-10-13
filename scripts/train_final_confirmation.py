"""Freeze the external protocol, select on development projects, fit all-data models.

Fresh confirmation outcomes must not be opened until model_manifest.json exists.
The Random Forest reference is an adaptation, not a published-paper reproduction.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import time
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from train_development import load_inputs, build_model, ET_GRID
from train_pilot import ROOT, SEED, sha, write_csv, metrics, best_threshold, weighted_ap

OUT = ROOT/'reports/final-confirmation-v0.3'
MODEL_ROOT = ROOT/'local-evidence/final-models/final-confirmation-v0.3'
PROJECTS = {
    'werkzeug': {'repository':'pallets/werkzeug','commit':'f97c305673ba121a1dae6764c37e8be48907a1d1'},
    'attrs': {'repository':'python-attrs/attrs','commit':'ee66e7274852438cc23d4240a1a9cd632fda8b52'},
    'tenacity': {'repository':'jd/tenacity','commit':'32ac68f0941319c0d2f4fb927f96e4ee29bb46c6'},
}

def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'protocol.json'
    if path.exists():
        raise ValueError('Protocol already frozen; do not overwrite')
    p=dict(created_utc=datetime.now(timezone.utc).isoformat(),stage='prospective external confirmation',
        confirmation_projects=PROJECTS,budget_hours=4,
        selection_reason='Three Python pytest projects outside the 35-project development corpus, with available source and practical full-suite CPU execution. Werkzeug was an earlier optional execution candidate but has no imported evidence. No outcome-based replacement.',
        dependency_risk='attrs and tenacity dependencies resolve at setup time and are snapshotted; this is a pinned-source experiment, not a claim of historic dependency equivalence.',
        detection='Passing full baseline required; 12 original + 12 pytest-randomly + 1 reverse; Ubuntu 24.04, Python 3.11.9. Baseline failures, incomplete runs, source exclusions and zero-positive projects retained in audit.',
        label='At least one pass and one failure/error; negatives all-pass after 25 complete observations. Skips, missing, colliding and failure-only identities excluded from binary analysis.',
        causal_limit='Random execution changes order and runtime seeds. Subtypes are provisional; no causal or pure-order assertion.',
        models=['extra_trees_core','extra_trees_context','random_forest_core_reference','random_forest_context_reference'],
        feature_definition='Frozen v0.2 revised core (30 counts, including two scope-aware reads) versus core + bounded fixture/helper/lifecycle/class state context (96 counts). This is incremental context beyond the scope-aware core.',
        extra_trees_grid=ET_GRID,selection='Five fixed development project folds; select largest pooled OOF average precision, first listed tie. No external outcomes used.',
        random_forest=dict(n_estimators=100,class_weight=None,max_depth=None,min_samples_leaf=1,max_features='sqrt',bootstrap=True,random_state=SEED,n_jobs=4),
        baseline_caveat='Random Forest family reference inspired by the audited 2024 artifact; Python features, no target labels, no PCA, no sampling, no transfer preprocessing. Not a faithful reproduction or a CANNIER comparison.',
        threshold='Maximum F1 on development OOF scores for selected configuration; highest threshold tie. Also fixed 0.5. Freeze before opening external outcomes.',
        primary='Paired external average precision difference: Extra Trees context minus core. Report pooled and each project; undefined positive metrics stay null.',
        secondary='MCC, precision, recall, F1, false positives per 1000 negatives, and recall at top ceil(10% of each project), stable example_id tie break. Random Forest and trivial references are secondary.',
        uncertainty='Project bootstrap only if at least two eligible positive projects; otherwise descriptive results with insufficient-project warning. Selection and dependency drift limitations disclosed.',
        duplication='Exclude external substantive exact body AST matches to development (>=3 statements and >=20 AST nodes) from primary; retain in audit. Near-clones remain a limitation.',
        release='Original development dataset immutable. All-data final models include development only until confirmation is evaluated. Any later confirmation-inclusive deployment fit has no new evaluation claim.',
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'dataset/v0.1/manifest.json',ROOT/'dataset/development-v0.2/manifest.json',ROOT/'scripts/train_final_confirmation.py',ROOT/'requirements-pilot.txt']})
    path.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
    print('Frozen protocol: '+sha(path),flush=True)

def train():
    protocol=json.loads((OUT/'protocol.json').read_text())
    for name,digest in protocol['inputs'].items():
        if sha(ROOT/name)!=digest: raise ValueError('Frozen input changed: '+name)
    MODEL_ROOT.mkdir(parents=True,exist_ok=True)
    if (OUT/'model_manifest.json').exists(): raise ValueError('Final models already frozen')
    ids,y,meta,projects,folds,inner,xs,columns,manifest=load_inputs()
    if set(projects)&set(PROJECTS): raise ValueError('Confirmation project in training')
    start=time.perf_counter(); searches=[]; selected=[]; predictions=[]; summaries=[]; models=[]
    for family in ('extra_trees','random_forest'):
        for source in ('v2_body','v2_context'):
            name=family+('_core' if source=='v2_body' else '_context')+('_reference' if family=='random_forest' else '')
            x=xs[source]; grid=ET_GRID if family=='extra_trees' else [protocol['random_forest']]
            best=None
            for candidate,params in enumerate(grid):
                scores=np.full(len(y),np.nan)
                for fold in range(5):
                    fit=folds!=fold; test=~fit
                    if set(projects[fit])&set(projects[test]): raise ValueError('Project leakage')
                    model=build_model('extra_trees',params) if family=='extra_trees' else RandomForestClassifier(**params)
                    model.fit(x[fit],y[fit]);scores[test]=model.predict_proba(x[test])[:,1]
                ap=weighted_ap(y,scores,np.ones(len(y)))
                searches.append(dict(model=name,candidate=candidate,parameters=json.dumps(params,sort_keys=True),development_oof_ap=ap))
                print(f'{name} candidate {candidate}: development AP={ap:.6f}',flush=True)
                if best is None or ap>best[0]+1e-12: best=(ap,candidate,params,scores.copy())
            ap,candidate,params,scores=best
            threshold,_=best_threshold(y,scores)
            selected.append(dict(model=name,candidate=candidate,parameters=params,threshold=threshold,development_oof_ap=ap))
            summaries.append(dict(model=name,stage='development selection; not independent confirmation',**metrics(y,scores,scores>=threshold,ids)))
            for key,p,fold,label,score in zip(ids,projects,folds,y,scores):
                predictions.append(dict(model=name,example_id=key,project=p,fold=int(fold),label=int(label),score=float(score),threshold=threshold))
            model=build_model('extra_trees',params) if family=='extra_trees' else RandomForestClassifier(**params)
            model.fit(x,y)
            path=MODEL_ROOT/(name+'.joblib')
            joblib.dump(dict(model=model,columns=columns[source],threshold=threshold,training_projects=sorted(set(projects)),protocol_sha256=sha(OUT/'protocol.json')),path,compress=3)
            importance=sorted(zip(columns[source],model.feature_importances_),key=lambda z:(-z[1],z[0]))
            write_csv(OUT/(name+'_importance.csv'),[dict(feature=k,impurity_importance=float(v)) for k,v in importance],['feature','impurity_importance'])
            models.append(dict(model=name,path=str(path.relative_to(ROOT)),sha256=sha(path),feature_columns=columns[source],threshold=threshold))
    write_csv(OUT/'candidate_search.csv',searches,list(searches[0]))
    write_csv(OUT/'development_selection_predictions.csv.gz',predictions,list(predictions[0]))
    write_csv(OUT/'development_selection_metrics.csv',summaries,list(summaries[0]))
    (OUT/'selected_models.json').write_text(json.dumps(selected,indent=2)+'\n')
    result=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(OUT/'protocol.json'),
                training_cases=len(y),training_positives=int(y.sum()),training_projects=sorted(set(projects)),models=models,elapsed_seconds=time.perf_counter()-start,
                external_outcomes_accessed=False,explanations='Impurity importance is model attribution, biased toward flexible features; not cause confirmation.')
    (OUT/'model_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('frozen_utc','training_cases','elapsed_seconds')}),flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','train'])
    globals()[parser.parse_args().action]()
