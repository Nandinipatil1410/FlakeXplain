"""Independent metric checks and frozen-model replay; no training or tuning."""
import gzip,json,math
import joblib
import numpy as np
from sklearn.metrics import average_precision_score,confusion_matrix,matthews_corrcoef
from train_final_confirmation import OUT,PROJECTS
from train_pilot import ROOT,reader,sha

def main():
    result=json.loads((OUT/'external_results.json').read_text());manifest=json.loads((OUT/'model_manifest.json').read_text());checks=[]
    def check(condition,message):
        if not condition:raise ValueError(message)
        checks.append(message)
    check(sha(OUT/'protocol.json')==manifest['protocol_sha256']==result['protocol_sha256'],'Unchanged prospectively frozen protocol')
    check(sha(OUT/'model_manifest.json')==result['model_manifest_sha256'],'Unchanged pre-outcome model manifest')
    for name,digest in result['inputs'].items():check(sha(ROOT/name)==digest,'Verified evaluation input '+name)
    with gzip.open(OUT/'external_features.jsonl.gz','rt',encoding='utf-8') as f:rows=[json.loads(line) for line in f]
    ids=np.array([r['example_id'] for r in rows]);y=np.array([r['label'] for r in rows]);projects=np.array([r['project'] for r in rows])
    check(len(ids)==len(set(ids))==result['cases'],'One external feature row per case')
    check(set(projects)<=set(PROJECTS),'Only prospectively registered external projects')
    preds=list(reader(OUT/'external_predictions.csv.gz'));metrics=list(reader(OUT/'external_metrics.csv'))
    for record in manifest['models']:
        name=record['model'];check(sha(ROOT/record['path'])==record['sha256'],name+': frozen model checksum')
        payload=joblib.load(ROOT/record['path']);check(not set(payload['training_projects'])&set(PROJECTS),name+': no external projects in training')
        x=np.asarray([[r['features'][k] for k in payload['columns']] for r in rows],np.float32)
        score=payload['model'].predict_proba(x)[:,1]
        pr={r['example_id']:r for r in preds if r['model']==name};check(len(pr)==len(rows),name+': predictions cover all cases')
        check(np.allclose(score,[float(pr[k]['score']) for k in ids],rtol=0,atol=1e-12),name+': all probabilities replayed')
        check(all(int(pr[k]['label'])==int(label) and pr[k]['project']==p for k,label,p in zip(ids,y,projects)),name+': label and project joins')
        for m in (r for r in metrics if r['model']==name):
            take=np.ones(len(y),bool) if m['project']=='ALL' else projects==m['project'];yy=y[take];ss=score[take];threshold=float(m['threshold']);pred=ss>=threshold
            tn,fp,fn,tp=confusion_matrix(yy,pred,labels=[0,1]).ravel()
            check(all(int(float(m[k]))==v for k,v in [('tn',tn),('fp',fp),('fn',fn),('tp',tp)]),name+' '+m['project']+' '+m['threshold_name']+': independent confusion matrix')
            if yy.any():check(abs(float(m['average_precision'])-average_precision_score(yy,ss))<1e-12,name+' '+m['project']+': independent AP')
            else:check(m['average_precision']=='' and m['recall']=='',name+' '+m['project']+': undefined positive metrics retained')
            if np.unique(yy).size==2:check(abs(float(m['mcc'])-matthews_corrcoef(yy,pred))<1e-12,name+' '+m['project']+': independent MCC')
            if m['threshold_name']=='frozen_development':check(threshold==record['threshold'],name+' '+m['project']+': no external threshold tuning')
            if yy.any():
                top=np.lexsort((ids[take],-ss))[:math.ceil(.1*len(yy))]
                check(abs(float(m['recall_at_top_10_percent'])-yy[top].sum()/yy.sum())<1e-12,name+' '+m['project']+': independently ranked budget')
    ex=json.loads((OUT/'source_linked_explanations.json').read_text());check(all(r['reconstruction_error']<1e-10 for r in ex),'Source-linked probability decompositions reconstruct model scores')
    artifact_hashes={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='validation.json'}
    data=dict(status='passed',checks=len(checks),details=checks,files=artifact_hashes,validator_sha256=sha(ROOT/'scripts/validate_confirmation.py'))
    (OUT/'validation.json').write_text(json.dumps(data,indent=2)+'\n');print('Confirmation verification passed:',len(checks),'checks')

if __name__=='__main__':main()
