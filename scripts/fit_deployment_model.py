"""Fit a separate deployment model after external evaluation; no new test claim."""
import gzip,json
from datetime import datetime,timezone
import joblib
import numpy as np
from train_development import load_inputs,build_model
from train_final_confirmation import OUT
from train_pilot import ROOT,sha

def main():
    validation=json.loads((OUT/'validation.json').read_text())
    if validation['status']!='passed':raise ValueError('Verify external evaluation first')
    out=ROOT/'local-evidence/deployment-v0.3';out.mkdir(parents=True,exist_ok=True)
    if (out/'extra_trees_context.joblib').exists():raise ValueError('Deployment model already exists')
    ids,y,meta,projects,folds,inner,xs,cols,feature_manifest=load_inputs()
    with gzip.open(OUT/'external_features.jsonl.gz','rt',encoding='utf-8') as f:external=[json.loads(line) for line in f]
    columns=cols['v2_context'];extra=np.asarray([[r['features'][c] for c in columns] for r in external],np.float32)
    x=np.vstack((xs['v2_context'],extra));labels=np.r_[y,[r['label'] for r in external]]
    names=sorted(set(projects)|{r['project'] for r in external})
    selected=next(r for r in json.loads((OUT/'selected_models.json').read_text()) if r['model']=='extra_trees_context')
    model=build_model('extra_trees',selected['parameters']);model.fit(x,labels)
    path=out/'extra_trees_context.joblib'
    payload=dict(model=model,columns=columns,threshold=selected['threshold'],training_projects=names,stage='Deployment fit on development plus already evaluated confirmation; no untouched test performance',protocol_sha256=sha(OUT/'protocol.json'))
    joblib.dump(payload,path,compress=3)
    check=joblib.load(path)
    indices=np.linspace(0,len(labels)-1,100,dtype=int)
    if not np.allclose(check['model'].predict_proba(x[indices]),model.predict_proba(x[indices]),rtol=0,atol=1e-12):raise ValueError('Serialized model replay differs')
    card=dict(fitted_utc=datetime.now(timezone.utc).isoformat(),path=str(path.relative_to(ROOT)),sha256=sha(path),training_cases=len(labels),training_positives=int(labels.sum()),training_projects=names,feature_columns=columns,threshold=selected['threshold'],parameters=selected['parameters'],serialization_replay_cases=100,
        interpretation='Deployment model uses all available eligible source-mapped cases. External results belong to the earlier frozen development-only models, not this retrained model. Scores are uncalibrated instability risk estimates; negative labels mean not observed flaky in 25/27 runs.',
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'external_results.json',OUT/'external_features.jsonl.gz',ROOT/'dataset/development-v0.2/manifest.json',ROOT/'scripts/fit_deployment_model.py']})
    (OUT/'deployment_model_card.json').write_text(json.dumps(card,indent=2)+'\n')
    print({k:card[k] for k in ('training_cases','training_positives','threshold','serialization_replay_cases')})

if __name__=='__main__':main()
