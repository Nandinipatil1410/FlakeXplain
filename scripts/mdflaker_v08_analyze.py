"""v0.8 analysis under the frozen rule (PROTOCOL.md section 7; amendments B1-B3).

E1 time-ordered (per project: earliest 60% train, latest 40% test; pooled), E2 leave-one-project-out,
E3 external transfer (train on MDFlaker's released spaCy+DRF rows, test on all fresh labelled rows).
Comparator per evaluation = best of the four base candidates by pooled MCC (baseline arms only).
Inference: project bootstrap (2,000 resamples of projects, predictions fixed) for MCC differences.
"""
import csv,gzip,json,sys
from pathlib import Path
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import matthews_corrcoef,f1_score,precision_score,recall_score

ROOT=Path(__file__).resolve().parents[1];V8=ROOT/'local-evidence/mdflaker-fresh-v0.8';OUT=ROOT/'reports/mdflaker-fresh-v0.8'
SEED=20261020;BOOT=2000
B=['flaky_frequency','traceback_coverage','test_smells','previous_state','test_size']
F=['build_failed_tests','same_file_cofailures','job_duration_s','pr_build','changed_files','changed_py_files','changed_test_py_files','nonpy_only_change',
   'changed_lines','own_test_file_changed','path_overlap_depth','traceback_frames','frames_in_changed_files','last_frame_in_test_file','frames_outside_repo',
   'min_line_distance_to_change','diff_available']

def mdf_paper(Xtr,ytr,Xte):
    knn=KNeighborsClassifier(10,p=1).fit(Xtr,ytr);p=knn.predict_proba(Xte)[:,list(knn.classes_).index(1)] if 1 in knn.classes_ else np.zeros(len(Xte))
    rule=Xte[:,3]==0
    return np.where(rule,Xte[:,1]==0,p>0.7).astype(int)
def knn8(Xtr,ytr,Xte):return KNeighborsClassifier(min(8,len(ytr)),p=1).fit(Xtr,ytr).predict(Xte)
def et(Xtr,ytr,Xte):
    m=ExtraTreesClassifier(n_estimators=100,random_state=SEED,n_jobs=-1).fit(Xtr,ytr)
    return (m.predict_proba(Xte)[:,list(m.classes_).index(1)]>=0.5).astype(int) if 1 in m.classes_ else np.zeros(len(Xte),int)
BASE={'MDF-paper-int':(mdf_paper,True),'MDF-paper-float':(mdf_paper,False),'KNN8-int':(knn8,True),'KNN8-float':(knn8,False)}

def mcc(y,p):return float(matthews_corrcoef(y,p)) if len(set(y))>1 else float('nan')
def metrics(y,p):return dict(mcc=mcc(y,p),f1=float(f1_score(y,p,zero_division=0)),precision=float(precision_score(y,p,zero_division=0)),recall=float(recall_score(y,p,zero_division=0)),n=int(len(y)),positives=int(y.sum()))

def boot(y,pa,pb,proj,rng):
    """Project bootstrap of MCC(a)-MCC(b) with predictions fixed."""
    ps=np.unique(proj);idx={p:np.flatnonzero(proj==p) for p in ps};d=[]
    for _ in range(BOOT):
        s=np.concatenate([idx[p] for p in rng.choice(ps,len(ps),replace=True)])
        if len(set(y[s]))>1:d.append(matthews_corrcoef(y[s],pa[s])-matthews_corrcoef(y[s],pb[s]))
    return [float(np.percentile(d,2.5)),float(np.percentile(d,97.5))] if d else [float('nan')]*2

def evaluate(name,splits,X,y,proj,mats):
    """splits: list of (train_idx,test_idx); predictions pooled over test parts."""
    test=np.concatenate([te for _,te in splits]);preds={}
    for arm,(fit,Xm) in mats.items():
        p=np.zeros(len(y),int)
        for tr,te in splits:p[te]=fit(Xm[tr],y[tr],Xm[te])
        preds[arm]=p[test]
    yt,pt=y[test],proj[test];res={a:metrics(yt,p) for a,p in preds.items()}
    for a in res:res[a]['per_project_mcc']={q:mcc(yt[pt==q],preds[a][pt==q]) for q in np.unique(pt)}
    return yt,pt,preds,res

def main():
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']):int(r['label']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);rows=[feat[i] for i in ids]
    ctx=[k for k in rows[0] if k not in B+F and k not in ('candidate','repo','created_at','nodeid','tree_ok','source_mapped')]
    X=np.array([[float(r[k]) for k in B] for r in rows]);XF=np.hstack([X,np.array([[float(r[k]) for k in F] for r in rows])])
    XFC=np.hstack([XF,np.array([[float(r[k]) for k in ctx] for r in rows])]);Xi=np.trunc(X)
    y=np.array([lab[i] for i in ids]);proj=np.array([r['repo'] for r in rows]);t=np.array([r['created_at'] for r in rows])
    rep=dict(labelled=len(y),flaky=int(y.sum()),not_flaky=int((1-y).sum()),projects={p:dict(n=int((proj==p).sum()),flaky=int(y[proj==p].sum())) for p in np.unique(proj)})
    both=[p for p in np.unique(proj) if 0<y[proj==p].sum()<(proj==p).sum()]
    rep['minimum_sample_met']=bool(y.sum()>=60 and (1-y).sum()>=60 and len(np.unique(proj))>=4)
    rng=np.random.default_rng(SEED);base={n:(fit,Xi if integer else X) for n,(fit,integer) in BASE.items()}
    ours={'ET-B':(et,X),'ET-BF':(et,XF),'ET-BFC':(et,XFC)}
    # E1 time-ordered within project
    tr=[];te=[]
    for p in np.unique(proj):
        ix=np.flatnonzero(proj==p);ix=ix[np.argsort(t[ix],kind='stable')];k=int(round(0.6*len(ix)))
        tr+=list(ix[:k]);te+=list(ix[k:])
    E1=[(np.array(tr),np.array(te))]
    # E2 leave-one-project-out
    E2=[(np.flatnonzero(proj!=p),np.flatnonzero(proj==p)) for p in np.unique(proj)]
    out={}
    for name,spl in (('E1',E1),('E2',E2)):
        yt,pt,pb,rb=evaluate(name,spl,X,y,proj,base);comp=max(rb,key=lambda a:(np.nan_to_num(rb[a]['mcc'],nan=-9)))
        yt,pt,po,ro=evaluate(name,spl,X,y,proj,ours);preds={**pb,**po};res={**rb,**ro}
        out[name]=dict(comparator=comp,arms=res,
            d_ETBF_vs_comp=dict(mcc=res['ET-BF']['mcc']-res[comp]['mcc'],ci95=boot(yt,preds['ET-BF'],preds[comp],pt,rng)),
            d_ETBF_vs_ETB=dict(mcc=res['ET-BF']['mcc']-res['ET-B']['mcc'],ci95=boot(yt,preds['ET-BF'],preds['ET-B'],pt,rng)),
            d_ETBFC_vs_ETBF=dict(mcc=res['ET-BFC']['mcc']-res['ET-BF']['mcc'],ci95=boot(yt,preds['ET-BFC'],preds['ET-BF'],pt,rng)))
    # E3 (secondary, outside the rule): train on MDFlaker's released spaCy+DRF rows, test on all fresh labelled rows.
    try:
        V6=ROOT/'local-evidence/mdflaker-v0.6';V7=ROOT/'local-evidence/failure-evidence-v0.7'
        rel=list(csv.DictReader(open(V6/'upstream/simpac/F_Detector/dataset.csv',encoding='utf-8')))
        with gzip.open(V7/'features_failure.csv.gz','rt',encoding='utf-8') as f:f7={int(r['row']):r for r in csv.DictReader(f)}
        with gzip.open(V6/'stage1/features_context.csv.gz','rt',encoding='utf-8') as f:c6={int(r['row']):r for r in csv.DictReader(f)}
        rid=sorted(i for i in f7 if i in c6)
        Xr=np.array([[float(rel[i][k]) for k in ('Flaky Frequency','Traceback Coverage','Test Smells','Previous State','Test Size')] for i in rid])
        Fr=np.array([[float(f7[i]['build_duration_s' if k=='job_duration_s' else k]) for k in F] for i in rid])
        Cr=np.array([[float(c6[i][k]) for k in ctx] for i in rid]);yr=np.array([int(rel[i]['Flaky or Not']) for i in rid])
        tr_mats={'MDF-paper-int':(mdf_paper,np.trunc(Xr),Xi),'KNN8-float':(knn8,Xr,X),'ET-B':(et,Xr,X),'ET-BF':(et,np.hstack([Xr,Fr]),XF),'ET-BFC':(et,np.hstack([Xr,Fr,Cr]),XFC)}
        e3={a:metrics(y,fit(A,yr,Bm)) for a,(fit,A,Bm) in tr_mats.items()}
        out['E3']=dict(train_rows=len(rid),arms=e3,note='secondary; MDFlaker labels are Travis 30-rerun labels from 2020; feature definitions match except job vs build duration')
    except Exception as ex:out['E3']=dict(error=str(ex))
    h1=out['E1']['d_ETBF_vs_comp'];h2=out['E2']['d_ETBF_vs_comp'];g=out['E1']['d_ETBF_vs_ETB']
    headline=rep['minimum_sample_met'] and h1['mcc']>=0.05 and h1['ci95'][0]>0 and h2['mcc']>=0.05 and h2['ci95'][0]>0 and g['mcc']>=0.02
    c1=out['E1']['d_ETBFC_vs_ETBF'];c2=out['E2']['d_ETBFC_vs_ETBF']
    rep.update(evaluations=out,rule=dict(headline_met=bool(headline),context_claim_met=bool(c1['mcc']>=0.02 and c2['mcc']>=0),
        descriptive_only=not rep['minimum_sample_met']))
    (OUT/'results.json').write_text(json.dumps(rep,indent=1,default=float)+'\n')
    print(json.dumps({k:rep[k] for k in ('labelled','flaky','not_flaky','projects','minimum_sample_met','rule')},indent=1,default=float))
    for e in ('E1','E2'):
        o=out[e];print(e,'comparator',o['comparator'],{a:round(v['mcc'],3) for a,v in o['arms'].items()})
        print('  ETBF-comp',round(o['d_ETBF_vs_comp']['mcc'],3),o['d_ETBF_vs_comp']['ci95'],' ETBF-ETB',round(o['d_ETBF_vs_ETB']['mcc'],3),' ETBFC-ETBF',round(o['d_ETBFC_vs_ETBF']['mcc'],3))

if __name__=='__main__':main()
