"""Independently reconcile pilot predictions and replay saved outer models."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, matthews_corrcoef, precision_score, recall_score, f1_score
from train_pilot import ROOT, VARIANTS, load_dataset, reader, sha, write_csv

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run',type=Path,default=ROOT/'reports/pilot-v0.1')
    args=parser.parse_args(); out=args.run
    manifest=json.loads((out/'run_manifest.json').read_text())
    results=json.loads((out/'results.json').read_text()); protocol=json.loads((out/'protocol.json').read_text())
    checks=[]
    def check(condition,message):
        if not condition:
            raise ValueError(message)
        checks.append(message)
    check(manifest['status']=='completed','Pilot finished all outer folds')
    check(all(sha(out/name)==value for name,value in manifest['files'].items()),'All original run artifacts match frozen checksums')
    check(sha(ROOT/'scripts/train_pilot.py')==manifest['implementation_sha256'],'Frozen training implementation hash matches')
    dataset=ROOT/'dataset/v0.1'
    ids,y,meta,projects,folds,inner,xs,body_columns,context_columns=load_dataset(dataset)
    check(sha(dataset/'manifest.json')==manifest['dataset_manifest_sha256'],'Dataset v0.1 checksum matches pilot input')
    rows=list(reader(out/'oof_predictions.csv.gz')); by_id={r['example_id']:r for r in rows}
    check(len(rows)==len(by_id)==len(ids) and set(by_id)==set(ids),'Exactly one held-out prediction row per dataset case')
    rows=[by_id[key] for key in ids]
    check(all(int(r['label'])==int(y[i]) and r['project']==projects[i] and int(r['outer_fold'])==int(folds[i]) for i,r in enumerate(rows)),
          'Labels, projects and held-out folds reconcile to frozen dataset')
    metrics_checks=True; diagnostics=[]
    for variant,prefix in zip(VARIANTS,('body','context')):
        scores=np.array([float(r[prefix+'_score']) for r in rows])
        check(np.isfinite(scores).all() and (scores>=0).all() and (scores<=1).all(),variant+': finite scores within [0,1]')
        for mode,column in [('fixed_0.5',prefix+'_fixed_prediction'),('inner_f1',prefix+'_inner_prediction')]:
            predictions=np.array([int(r[column]) for r in rows])
            thresholds=.5 if mode=='fixed_0.5' else np.array([float(r[prefix+'_inner_threshold']) for r in rows])
            check(np.array_equal(predictions,(scores>=thresholds).astype(int)),variant+' '+mode+': predictions match their declared thresholds')
            r=next(v for v in results['pooled'] if v['model']==variant and v['threshold_mode']==mode)
            tn,fp,fn,tp=confusion_matrix(y,predictions,labels=[0,1]).ravel()
            expected=dict(average_precision=average_precision_score(y,scores),precision=precision_score(y,predictions,zero_division=0),
                          recall=recall_score(y,predictions),f1=f1_score(y,predictions),mcc=matthews_corrcoef(y,predictions),
                          tp=tp,fp=fp,tn=tn,fn=fn,false_positives_per_1000_negative=1000*fp/(fp+tn))
            metrics_checks &= all(np.isclose(r[k],value,rtol=0,atol=1e-12) for k,value in expected.items())
        for fold in range(5):
            artifact=next(r for r in results['model_artifacts'] if r['model']==variant and r['outer_fold']==fold)
            path=ROOT/artifact['path']
            check(sha(path)==artifact['sha256'],variant+f' outer {fold}: saved model checksum matches')
            payload=joblib.load(path)
            train=folds!=fold; test=~train
            check(set(payload['train_projects'])==set(projects[train]) and set(payload['test_projects'])==set(projects[test]) and
                  not(set(payload['train_projects'])&set(payload['test_projects'])),variant+f' outer {fold}: saved train/test projects are disjoint')
            check(payload['feature_columns']==protocol['feature_columns'][variant] and payload['estimator'].n_features_in_==xs[variant].shape[1],
                  variant+f' outer {fold}: model feature order is the numeric allowlist')
            score=payload['estimator'].predict_proba(xs[variant][test])[:,1]
            check(np.allclose(score,scores[test],rtol=0,atol=1e-12),variant+f' outer {fold}: saved model reproduces held-out scores')
            selected=next(r for r in reader(out/'threshold_selection.csv') if r['model']==variant and int(r['outer_fold'])==fold)
            check(set(selected['train_projects'].split('|'))==set(projects[train]) and set(selected['test_projects'].split('|'))==set(projects[test]) and
                  int(selected['threshold_cases'])==int(train.sum()) and int(selected['threshold_positive_cases'])==int(y[train].sum()),
                  variant+f' outer {fold}: threshold selection reports only outer-training projects')
            train_score=payload['estimator'].predict_proba(xs[variant][train])[:,1]
            diagnostics.append(dict(model=variant,outer_fold=fold,training_resubstitution_average_precision=float(average_precision_score(y[train],train_score)),
                                    held_out_average_precision=float(average_precision_score(y[test],score)),
                                    training_prevalence=float(y[train].mean()),test_prevalence=float(y[test].mean()),
                                    train_score_mean_positive=float(train_score[y[train]==1].mean()),
                                    train_score_mean_negative=float(train_score[y[train]==0].mean()),
                                    test_score_mean_positive=float(score[y[test]==1].mean()),
                                    test_score_mean_negative=float(score[y[test]==0].mean())))
            del payload
    check(metrics_checks,'Independent sklearn metrics exactly reconcile to reported pooled results')
    write_csv(out/'generalization_diagnostics.csv',diagnostics,list(diagnostics[0]))
    result=dict(status='passed',checks=checks,cases=len(ids),positives=int(y.sum()),saved_outer_models_replayed=10,
                note='Training resubstitution scores are diagnostics only; held-out scores determine pilot performance. Inner models can be reproduced from the frozen code but are not serialized.')
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],checks=len(checks),cases=result['cases'],saved_outer_models_replayed=10),indent=2))

if __name__=='__main__':
    main()
