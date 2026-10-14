"""Evaluate once on the prospectively selected independent evidence.

Models and thresholds are loaded from the pre-outcome manifest. No fitting here.
"""
import ast
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import joblib
import numpy as np
from dataset_static import SourceIndex,digest,body_tree
from confirmation_features import extract
from prepare_dataset import verify_sources
from train_final_confirmation import OUT,PROJECTS
from train_development import bootstrap_difference
from train_pilot import ROOT,reader,sha,write_csv,metrics

def tree_path_attribution(model,x):
    """Exact forest probability decomposition along observed tree paths, not SHAP."""
    values=np.zeros(x.size);base=0.
    for estimator in model.estimators_:
        t=estimator.tree_; node=0
        def prob(n):
            v=t.value[n,0];return float(v[1]/v.sum())
        base+=prob(0)
        while t.children_left[node]!=t.children_right[node]:
            feature=t.feature[node]
            child=t.children_left[node] if x[feature]<=t.threshold[node] else t.children_right[node]
            values[feature]+=prob(child)-prob(node);node=child
    return base/len(model.estimators_),values/len(model.estimators_)

def main():
    if (OUT/'external_results.json').exists():raise ValueError('External evaluation already exported; validate existing results instead')
    manifest=json.loads((OUT/'model_manifest.json').read_text());protocol=json.loads((OUT/'protocol.json').read_text())
    if manifest['protocol_sha256']!=sha(OUT/'protocol.json'):raise ValueError('Protocol changed after model freeze')
    replay=json.loads((OUT/'feature_replay_validation.json').read_text())
    if replay['status']!='passed' or replay['extractor_sha256']!=sha(ROOT/'scripts/confirmation_features.py'):raise ValueError('Feature adapter has not passed exact replay')
    audit=json.loads((OUT/'evidence-audit/audit.json').read_text())
    project_audit={r['project']:r for r in audit['projects']}
    known={r['body_ast_sha256'] for r in reader(ROOT/'dataset/v0.1/metadata.csv.gz') if int(r['body_statements'])>=3 and int(r['body_ast_nodes'])>=20}
    indexes={};python_trees=[]
    for p,c in PROJECTS.items():
        root=ROOT/'local-evidence/confirmation-sources'/p
        record=json.loads((root/'FLAKEXPLAIN_SOURCE_PROVENANCE.json').read_text())
        if record['commit']!=c['commit']:raise ValueError('Unpinned source')
        tree_hash,count=verify_sources(root,record);python_trees.append(dict(project=p,python_tree_sha256=tree_hash,python_files=count))
        indexes[p]=SourceIndex(root)
        if p in project_audit and project_audit[p]['commit']!=c['commit']:raise ValueError('Evidence/source revision mismatch')
    rows=[];excluded=[];cache={};audits=[]
    for r in reader(OUT/'evidence-audit/test_details.csv.gz'):
        if r['project'] not in PROJECTS:raise ValueError('Unregistered confirmation project')
        if r['primary_eligible']!='True':continue
        p=r['project'];index=indexes[p]
        eid=digest(json.dumps([p,PROJECTS[p]['commit'],r['file'],r['classname'],r['name']],separators=(',',':')))
        mapped,status=index.map_test(r)
        if mapped is None:
            excluded.append(dict(project=p,example_id=eid,label=r['label'],reason=status));continue
        fn,cls,path=mapped;key=(p,fn.key,cls,path)
        if key not in cache:cache[key]=extract(index,fn,cls,path)
        b,c,m=cache[key]
        if m['body_statements']>=3 and m['body_ast_nodes']>=20 and m['body_ast_sha256'] in known:
            excluded.append(dict(project=p,example_id=eid,label=r['label'],reason='substantive_exact_body_overlap_with_development'));continue
        row=dict(example_id=eid,project=p,label=int(r['label']=='observed_flaky'),effective_n=int(r['effective_n']),junit_classname=r['classname'],junit_name=r['name'],features=c,source=m)
        rows.append(row)
    if not rows:raise ValueError('No eligible source-mapped confirmation cases; report campaign audit only')
    rows.sort(key=lambda r:r['example_id']);ids=np.array([r['example_id'] for r in rows]);y=np.array([r['label'] for r in rows]);projects=np.array([r['project'] for r in rows])
    if len(set(ids))!=len(ids):raise ValueError('Duplicate external identity')
    outputs=[];metrics_rows=[];scores={};explanations=[]
    for record in manifest['models']:
        path=ROOT/record['path']
        if sha(path)!=record['sha256']:raise ValueError('Frozen model checksum differs')
        payload=joblib.load(path);model=payload['model'];cols=payload['columns'];name=record['model']
        if set(payload['training_projects'])&set(PROJECTS):raise ValueError('External project used in training')
        if payload['protocol_sha256']!=manifest['protocol_sha256'] or cols!=record['feature_columns']:raise ValueError('Model provenance differs')
        x=np.asarray([[r['features'][k] for k in cols] for r in rows],dtype=np.float32)
        if not np.isfinite(x).all() or (x<0).any():raise ValueError('Invalid static features')
        score=model.predict_proba(x)[:,1];scores[name]=score
        for threshold_name,threshold in [('frozen_development',record['threshold']),('fixed_0.5',.5)]:
            for project in ['ALL']+sorted(set(projects)):
                take=np.ones(len(y),dtype=bool) if project=='ALL' else projects==project
                m=metrics(y[take],score[take],score[take]>=threshold,ids[take])
                metrics_rows.append(dict(model=name,threshold_name=threshold_name,threshold=threshold,project=project,**m))
        for r,s in zip(rows,score):outputs.append(dict(model=name,example_id=r['example_id'],project=r['project'],label=r['label'],score=float(s),threshold=record['threshold'],prediction=int(s>=record['threshold'])))
        if name=='extra_trees_context':
            for p in sorted(set(projects)):
                options=np.flatnonzero(projects==p);order=options[np.lexsort((ids[options],-score[options]))]
                for i in order[:3]:
                    base,contributions=tree_path_attribution(model,x[i]);reconstructed=base+contributions.sum()
                    if abs(reconstructed-score[i])>1e-10:raise ValueError('Attribution does not reconstruct probability')
                    explanations.append(dict(example_id=rows[i]['example_id'],project=p,junit_name=rows[i]['junit_name'],
                        score=float(score[i]),base=float(base),reconstruction_error=float(abs(reconstructed-score[i])),method='Exact mean tree-path probability decomposition, not SHAP; correlated features and allocation are not causal diagnosis.',
                        source=rows[i]['source'],contributions=[dict(feature=k,value=float(v),contribution=float(c)) for k,v,c in sorted(zip(cols,x[i],contributions),key=lambda z:(-abs(z[2]),z[0]))]))
    # Trivial training-prevalence reference, with no external fitting.
    prevalence=manifest['training_positives']/manifest['training_cases']
    for project in ['ALL']+sorted(set(projects)):
        take=np.ones(len(y),dtype=bool) if project=='ALL' else projects==project
        metrics_rows.append(dict(model='constant_training_prevalence',threshold_name='fixed_0.5',threshold=.5,project=project,**metrics(y[take],np.repeat(prevalence,take.sum()),np.zeros(take.sum(),bool),ids[take])))
    primary=[]
    for p in ['ALL']+sorted(set(projects)):
        a=next(r for r in metrics_rows if r['model']=='extra_trees_core' and r['project']==p and r['threshold_name']=='frozen_development')
        b=next(r for r in metrics_rows if r['model']=='extra_trees_context' and r['project']==p and r['threshold_name']=='frozen_development')
        primary.append(dict(project=p,cases=a['cases'],positives=a['positives'],core_ap=a['average_precision'],context_ap=b['average_precision'],ap_difference=None if a['average_precision'] is None else b['average_precision']-a['average_precision'],core_fp=a['fp'],context_fp=b['fp']))
    positive_projects=sum(bool(y[projects==p].sum()) for p in set(projects))
    uncertainty=bootstrap_difference(y,scores['extra_trees_core'],scores['extra_trees_context'],projects) if positive_projects>=2 else dict(status='not_estimated',reason='Fewer than two independent positive confirmation projects; no meaningful project-bootstrap positive metric interval.')
    if positive_projects>=2:uncertainty['limitation']='Project resampling of fixed external predictions; only three prospectively selected projects, very limited precision; no population-representative claim.'
    for p in PROJECTS:
        take=projects==p;pa=project_audit.get(p,{})
        audits.append(dict(project=p,status=pa.get('status','no_artifact'),candidate_binary_cases=pa.get('eligible_tests',0),model_cases=int(take.sum()),observed_flaky=int(y[take].sum()),not_observed_flaky=int(take.sum()-y[take].sum()),source_exclusions=sum(r['project']==p for r in excluded),parse_errors=len(indexes[p].errors),unresolved_fixture_cases=sum(bool(r['source']['unresolved_fixture_count']) for r in rows if r['project']==p)))
    write_csv(OUT/'external_predictions.csv.gz',outputs,list(outputs[0]));write_csv(OUT/'external_metrics.csv',metrics_rows,list(metrics_rows[0]));write_csv(OUT/'external_project_summary.csv',audits,list(audits[0]));write_csv(OUT/'external_primary_comparison.csv',primary,list(primary[0]))
    write_csv(OUT/'external_source_exclusions.csv',excluded,list(excluded[0]) if excluded else ['project','example_id','label','reason'])
    import gzip
    with gzip.open(OUT/'external_features.jsonl.gz','wt',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r)+'\n')
    (OUT/'source_linked_explanations.json').write_text(json.dumps(explanations,indent=2)+'\n')
    result=dict(evaluated_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(OUT/'protocol.json'),model_manifest_sha256=sha(OUT/'model_manifest.json'),cases=len(y),positives=int(y.sum()),positive_projects=positive_projects,project_summary=audits,primary=primary,uncertainty=uncertainty,source_trees=python_trees,
        interpretation='No positive confirmation cases: evaluate false alarms only; recall, average precision and improvement remain unestablished.' if not y.sum() else 'Observed instability prediction on three prospectively selected projects; assess the paired results, positive-project count and limitations before any improvement claim.',
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'scripts/evaluate_confirmation.py',ROOT/'scripts/confirmation_features.py',OUT/'evidence-audit/audit.json',OUT/'feature_replay_validation.json']})
    (OUT/'external_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
