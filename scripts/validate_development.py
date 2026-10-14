"""Replay selected models, inner-OOF choices and transformations independently."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.metrics import average_precision_score,confusion_matrix,precision_score,recall_score,f1_score,matthews_corrcoef
from train_development import load_inputs,add_text_inputs
from train_pilot import ROOT,reader,sha,best_threshold,write_csv

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run',type=Path,default=ROOT/'reports/development-v0.2')
    out=parser.parse_args().run; manifest=json.loads((out/'run_manifest.json').read_text()); results=json.loads((out/'results.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text()); checks=[]
    def check(condition,message):
        if not condition:
            raise ValueError(message)
        checks.append(message)
    check(all(sha(out/name)==digest for name,digest in manifest['files'].items()),'Original development run output hashes match')
    check(sha(ROOT/'scripts/train_development.py')==manifest['implementation_sha256'],'Frozen development training code hash matches')
    ids,y,meta,projects,folds,inner,xs,columns,feature_manifest=load_inputs()
    add_text_inputs(xs,meta,feature_manifest)
    predictions=list(reader(out/'oof_predictions.csv.gz')); indexed={r['example_id']:r for r in predictions}
    check(len(indexed)==len(predictions)==len(ids) and set(indexed)==set(ids),'Exactly one development OOF row per frozen original case')
    predictions=[indexed[key] for key in ids]
    check(all(int(r['label'])==int(y[i]) and r['project']==projects[i] and int(r['outer_fold'])==int(folds[i]) for i,r in enumerate(predictions)),
          'All labels, identities and outer folds match the original dataset')
    path=ROOT/results['inner_oof']['path']; check(sha(path)==results['inner_oof']['sha256'],'Selected inner OOF archive hash matches')
    selected=list(reader(out/'selected_configurations.csv')); search=list(reader(out/'inner_candidate_search.csv'))
    scores={}; all_metrics=True; diagnostics=[]
    with np.load(path) as inner_scores:
        for name in protocol['models']:
            score=np.array([float(r[name+'_score']) for r in predictions]); scores[name]=score
            threshold=np.array([float(r[name+'_threshold']) for r in predictions])
            check(np.isfinite(score).all() and (score>=0).all() and (score<=1).all(),name+': scores valid')
            for mode in ('fixed_0.5','inner_f1'):
                pred=score>=(.5 if mode=='fixed_0.5' else threshold)
                actual=next(r for r in results['pooled'] if r['model']==name and r['threshold_mode']==mode)
                tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
                expected=dict(average_precision=average_precision_score(y,score),precision=precision_score(y,pred,zero_division=0),
                              recall=recall_score(y,pred),f1=f1_score(y,pred),mcc=matthews_corrcoef(y,pred),
                              tn=tn,fp=fp,fn=fn,tp=tp)
                all_metrics &= all(np.isclose(actual[k],v,atol=1e-12,rtol=0) for k,v in expected.items())
            for fold in range(5):
                train=folds!=fold; test=~train
                s=next(r for r in selected if r['model']==name and int(r['outer_fold'])==fold)
                candidate_rows=[r for r in search if r['model']==name and int(r['outer_fold'])==fold]
                maximum=max(float(r['inner_oof_ap']) for r in candidate_rows)
                chosen=min((r for r in candidate_rows if maximum-float(r['inner_oof_ap'])<=1e-12),key=lambda r:int(r['candidate']))
                check(int(chosen['candidate'])==int(s['selected_candidate']),name+f' fold {fold}: best inner-AP candidate chosen')
                prob=inner_scores[f'{name}__outer_{fold}']
                check(np.isfinite(prob[train]).all() and np.isnan(prob[test]).all(),name+f' fold {fold}: inner OOF excludes outer cases')
                t,f=best_threshold(y[train],prob[train])
                check(np.isclose(t,float(s['threshold']),atol=1e-12,rtol=0) and np.isclose(f,float(s['inner_oof_f1']),atol=1e-12,rtol=0)
                      and np.isclose(average_precision_score(y[train],prob[train]),float(s['inner_oof_ap']),atol=1e-12,rtol=0),
                      name+f' fold {fold}: threshold and inner AP reproduce from saved inner scores')
                check(set(s['train_projects'].split('|'))==set(projects[train]) and set(s['test_projects'].split('|'))==set(projects[test]),
                      name+f' fold {fold}: selected configuration reports disjoint projects')
                artifact=next(r for r in results['models'] if r['model']==name and r['outer_fold']==fold)
                path=ROOT/artifact['path']; check(sha(path)==artifact['sha256'],name+f' fold {fold}: model hash matches')
                payload=joblib.load(path); source=payload['input_source']; model=payload['estimator']; x=xs[source]
                params=json.loads(s['parameters'])
                estimator=model.named_steps['classifier'] if hasattr(model,'named_steps') else model
                check(all(estimator.get_params()[key]==value for key,value in params.items()),
                      name+f' fold {fold}: actual estimator uses the inner-selected parameters')
                check(set(payload['train_projects'])==set(projects[train]) and set(payload['test_projects'])==set(projects[test]),
                      name+f' fold {fold}: saved estimator membership matches')
                if source.startswith('text_'):
                    expected_idf=TfidfTransformer(sublinear_tf=True).fit(x[train]).idf_
                    check(np.allclose(expected_idf,model.named_steps['tfidf'].idf_,atol=1e-6,rtol=0),name+f' fold {fold}: IDF equals training-only fit')
                elif name.startswith('logistic_'):
                    expected_mean=np.log1p(x[train]).astype(np.float64).mean(axis=0)
                    check(np.allclose(expected_mean,model.named_steps['scale'].mean_,atol=1e-8,rtol=0),name+f' fold {fold}: scaler mean equals training-only fit')
                else:
                    check(payload['feature_columns']==columns[source] and model.n_features_in_==x.shape[1],name+f' fold {fold}: numeric allowlist holds')
                replay=model.predict_proba(x[test])[:,1]
                check(np.allclose(replay,score[test],atol=1e-12,rtol=0),name+f' fold {fold}: outer scores reproduce from saved model')
                train_score=model.predict_proba(x[train])[:,1]
                diagnostics.append(dict(model=name,outer_fold=fold,train_resubstitution_ap=float(average_precision_score(y[train],train_score)),
                                        outer_development_ap=float(average_precision_score(y[test],replay))))
                del model,payload
    check(all_metrics,'Independent sklearn pooled metrics match for all models and threshold modes')
    write_csv(out/'generalization_diagnostics.csv',diagnostics,list(diagnostics[0]))
    result=dict(status='passed',checks=checks,cases=len(ids),positives=int(y.sum()),models_replayed=len(results['models']),
                convergence_warnings=results['convergence_warnings'],stage='development, not untouched confirmation')
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='passed',checks=len(checks),models_replayed=len(results['models'])),indent=2))

if __name__=='__main__':
    main()
