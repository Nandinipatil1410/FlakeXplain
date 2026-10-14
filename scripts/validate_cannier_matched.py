"""Replay every outer model and verify metrics, partitions, labels and thresholds."""
import json
import joblib,numpy as np
from sklearn.metrics import average_precision_score,confusion_matrix,matthews_corrcoef,f1_score
from prepare_cannier_matched import OUT,DATA,LOCAL
from train_cannier_matched import load_inputs,mcc_threshold
from train_pilot import ROOT,reader,sha

def main():
    checks=[]
    def check(ok,message):
        if not ok:raise ValueError(message)
        checks.append(message)
    manifest=json.loads((OUT/'run_manifest.json').read_text());protocol=json.loads((OUT/'protocol.json').read_text())
    for name,value in manifest['files'].items():check(sha(OUT/name)==value,'Frozen run output '+name)
    check(sha(OUT/'protocol.json')==manifest['protocol_sha256'],'Protocol unchanged')
    for name,value in protocol['source_inputs'].items():check(sha(ROOT/name)==value,'Frozen source definition '+name)
    dataset_manifest=json.loads((DATA/'manifest.json').read_text())
    check(dataset_manifest['extractor_sha256']==sha(ROOT/'scripts/prepare_cannier_matched.py'),'Dataset preparation implementation unchanged')
    tp=json.loads((OUT/'training_protocol.json').read_text());check(tp['implementation_sha256']==sha(ROOT/'scripts/train_cannier_matched.py'),'Training implementation unchanged')
    check(sha(LOCAL/'authors-output.zip')==protocol['authors_archive_sha256'],'Original release archive hash verified')
    ids,labels,meta,projects,folds,xs,columns=load_inputs();items=np.load(LOCAL/'output/items.npy',allow_pickle=False);features=np.load(LOCAL/'output/features.npy',mmap_mode='r',allow_pickle=False)
    original_rows=np.asarray([int(r['original_row']) for r in meta]);check(len(set(original_rows))==len(ids),'Unique original released rows')
    check(np.array_equal(xs['baseline'],features[original_rows,0].astype(np.float32)),'All baseline values are genuine first stored author measurements')
    check(xs['baseline'].shape[1]==18 and xs['context'].shape[1]==84,'Exactly 18 baseline and 66 added context features')
    check(np.array_equal(xs['context'][:,:18],xs['baseline']),'Baseline measurement prefix identical in context variant')
    check(not set(columns['context'])&{'project','nodeid','nod','victim','polluter','n_fail_baseline','n_fail_shuffle'},'Evidence and identity predictors excluded')
    for key,column in [('nod',3),('victim',4),('nod_victim_domain',5),('polluter',6)]:check(np.array_equal([int(r[key]) for r in labels],items[original_rows,column]),'Original labels preserved: '+key)
    splits={r['project']:r for r in reader(DATA/'splits_outer.csv')}
    groups={}
    for p,r in splits.items():groups.setdefault(r['project_group'],set()).add(r['outer_fold'])
    check(all(len(v)==1 for v in groups.values()),'Exact duplicate project groups remain within one outer fold')
    pooled=list(reader(OUT/'metrics_pooled.csv'));perproject=list(reader(OUT/'metrics_by_project.csv'));partitions=list(reader(OUT/'training_partitions.csv'))
    for task,key in [('NOD-vs-Rest','nod'),('Victim-vs-Rest','victim')]:
        y=np.asarray([int(r[key]) for r in labels]);predrows={r['example_id']:r for r in reader(OUT/task/'oof_predictions.csv.gz')}
        check(set(predrows)==set(ids),task+': complete OOF coverage')
        rows=[predrows[k] for k in ids];check(all(int(r['label'])==v and r['project']==p and int(r['outer_fold'])==f for r,v,p,f in zip(rows,y,projects,folds)),task+': labels/projects/folds match')
        variants=sorted({r['variant'] for r in pooled if r['task']==task})
        for variant in variants:
            scores=np.asarray([float(r[variant+'_score']) for r in rows]);thresholds=np.asarray([float(r[variant+'_threshold']) for r in rows]);representation='context' if variant.endswith('_context') else 'baseline'
            for record in (r for r in manifest['models'] if r['task']==task and r['variant']==variant):
                check(sha(ROOT/record['path'])==record['sha256'],'Frozen model '+task+' '+variant+' '+str(record['outer_fold']))
                payload=joblib.load(ROOT/record['path']);fold=record['outer_fold'];test=folds==fold;train=~test
                check(set(payload['training_projects'])==set(projects[train]) and not set(payload['training_projects'])&set(projects[test]),task+' '+variant+': outer project separation')
                check(payload['columns']==columns[representation],task+' '+variant+': estimator feature allowlist')
                parameters=payload['model'].get_params()
                check(parameters['n_estimators']==(100 if task=='NOD-vs-Rest' else 75) and all(parameters[k]==v for k,v in protocol['common_parameters'].items()),task+' '+variant+': fixed published family/tree settings and common parameters')
                actual=payload['model'].predict_proba(xs[representation][test])[:,1]
                check(np.allclose(actual,scores[test],rtol=0,atol=1e-12),task+' '+variant+': all held-out probabilities replay')
                check(sha(ROOT/record['inner_path'])==record['inner_sha256'],task+' '+variant+': inner OOF hash')
                with np.load(ROOT/record['inner_path'],allow_pickle=False) as f:inner=f['scores']
                check(np.isfinite(inner[train]).all() and np.isnan(inner[test]).all(),task+' '+variant+': inner OOF excludes outer test')
                check(payload['threshold']==mcc_threshold(y[train],inner[train]) and np.all(thresholds[test]==payload['threshold']),task+' '+variant+': threshold selected on training OOF only')
                part=next(r for r in partitions if r['task']==task and r['variant']==variant and int(r['outer_fold'])==fold)
                if variant.startswith('natural_'):check(int(part['original_fit_cases'])==int(part['actual_fit_cases'])==int(train.sum()),task+' '+variant+': natural training population preserved')
                else:check(int(part['actual_fit_cases'])==2*max(np.bincount(y[train])),task+' '+variant+': separately declared SMOTE only in training')
            for m in [r for r in pooled+perproject if r['task']==task and r['variant']==variant]:
                take=np.ones(len(y),bool) if 'project' not in m else projects==m['project'];yy=y[take];ss=scores[take];cut=.5 if m['threshold_mode']=='fixed_0.5' else thresholds[take];pred=ss>=cut
                tn,fp,fn,tp=confusion_matrix(yy,pred,labels=[0,1]).ravel();check(all(int(float(m[k]))==v for k,v in [('tn',tn),('fp',fp),('fn',fn),('tp',tp)]),task+' '+variant+': independent confusion matrix')
                if yy.any():check(abs(float(m['average_precision'])-average_precision_score(yy,ss))<1e-12,task+' '+variant+': independent AP')
                else:check(m['average_precision']=='' and m['recall']=='',task+' '+variant+': undefined positive metrics retained')
                if len(np.unique(yy))==2:check(abs(float(m['mcc'])-matthews_corrcoef(yy,pred))<1e-12,task+' '+variant+': independent signed MCC')
    result=dict(status='passed',checks=len(checks),details=checks,implementation_sha256=sha(ROOT/'scripts/validate_cannier_matched.py'),run_manifest_sha256=sha(OUT/'run_manifest.json'))
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print('Matched experiment verification passed:',len(checks),'checks')

if __name__=='__main__':main()
