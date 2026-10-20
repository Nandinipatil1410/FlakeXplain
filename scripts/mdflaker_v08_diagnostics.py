"""v0.8 post-hoc diagnostics (outside the frozen rule; reported separately from results.json).

D1 project-prior baseline: predict each project's training majority class (E1) -> how much pooled MCC is base rate.
D2 within-project MCC of each arm in E1 (and mean over projects with both classes in the test part).
D3 traceback availability as a label proxy: flaky rate with vs without a parsed traceback, per project,
   and ET-BF with traceback_frames removed (E1, E2).
D4 ET-BF permutation importance (E1 test part).
"""
import csv,gzip,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_analyze import B,F,V8,OUT,SEED,et,mcc,boot
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.inspection import permutation_importance

def main():
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']):int(r['label']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);rows=[feat[i] for i in ids]
    X=np.array([[float(r[k]) for k in B] for r in rows]);XF=np.hstack([X,np.array([[float(r[k]) for k in F] for r in rows])])
    y=np.array([lab[i] for i in ids]);proj=np.array([r['repo'] for r in rows]);t=np.array([r['created_at'] for r in rows])
    tr=[];te=[]
    for p in np.unique(proj):
        ix=np.flatnonzero(proj==p);ix=ix[np.argsort(t[ix],kind='stable')];k=int(round(0.6*len(ix)));tr+=list(ix[:k]);te+=list(ix[k:])
    tr,te=np.array(tr),np.array(te);out={};rng=np.random.default_rng(SEED)
    # D1 project prior
    prior=np.array([int(y[tr][proj[tr]==proj[i]].mean()>=0.5) for i in te])
    pBF=et(XF[tr],y[tr],XF[te]);pB=et(X[tr],y[tr],X[te])
    out['D1_project_prior_E1']=dict(mcc=mcc(y[te],prior),ETBF_minus_prior=mcc(y[te],pBF)-mcc(y[te],prior),ci95=boot(y[te],pBF,prior,proj[te],rng))
    # D2 within-project MCC
    w={}
    for p in np.unique(proj[te]):
        m=proj[te]==p;w[p]=dict(n=int(m.sum()),flaky=int(y[te][m].sum()),ETBF=mcc(y[te][m],pBF[m]),ETB=mcc(y[te][m],pB[m]),prior=mcc(y[te][m],prior[m]))
    ok=[p for p in w if not np.isnan(w[p]['ETBF'])]
    out['D2_within_project_E1']=dict(per_project=w,mean_ETBF=float(np.nanmean([w[p]['ETBF'] for p in ok])),mean_ETB=float(np.nanmean([w[p]['ETB'] for p in ok])),projects=len(ok))
    # D3 traceback proxy
    tb=XF[:,B.__len__()+F.index('traceback_frames')]>0;d3={}
    for p in np.unique(proj):
        m=proj==p;d3[p]=dict(with_tb=int((m&tb).sum()),flaky_rate_with_tb=float(y[m&tb].mean()) if (m&tb).any() else None,
            without_tb=int((m&~tb).sum()),flaky_rate_without_tb=float(y[m&~tb].mean()) if (m&~tb).any() else None)
    keep=[j for j in range(XF.shape[1]) if j!=len(B)+F.index('traceback_frames')]
    e2=[(np.flatnonzero(proj!=p),np.flatnonzero(proj==p)) for p in np.unique(proj)]
    def pooled(Xm,spl):
        p=np.zeros(len(y),int);test=np.concatenate([b for _,b in spl])
        for a,b in spl:p[b]=et(Xm[a],y[a],Xm[b])
        return mcc(y[test],p[test])
    out['D3_traceback']=dict(per_project=d3,ETBF_E1=mcc(y[te],pBF),ETBF_no_tbframes_E1=mcc(y[te],et(XF[tr][:,keep],y[tr],XF[te][:,keep])),
        ETBF_E2=pooled(XF,e2),ETBF_no_tbframes_E2=pooled(XF[:,keep],e2))
    # D5 memorization: E1 restricted to test failures whose test (node ID, params stripped) never occurs in training
    from mdflaker_v08_analyze import knn8
    node=np.array([r['repo']+'|'+r['nodeid'].split('[')[0] for r in rows]);seen=set(node[tr]);u=np.array([n not in seen for n in node[te]])
    pK=knn8(X[tr],y[tr],X[te]);pC=et(XF[tr][:,keep],y[tr],XF[te][:,keep])
    out['D5_unseen_tests_E1']=dict(n=int(u.sum()),flaky=int(y[te][u].sum()),projects=int(len(set(proj[te][u]))),
        ETBF=mcc(y[te][u],pBF[u]),ETB=mcc(y[te][u],pB[u]),KNN8_float=mcc(y[te][u],pK[u]),prior=mcc(y[te][u],prior[u]),
        ETBF_minus_KNN8=dict(mcc=mcc(y[te][u],pBF[u])-mcc(y[te][u],pK[u]),ci95=boot(y[te][u],pBF[u],pK[u],proj[te][u],rng)),
        seen_n=int((~u).sum()),ETBF_seen=mcc(y[te][~u],pBF[~u]),KNN8_seen=mcc(y[te][~u],pK[~u]))
    # D4 importance
    m=ExtraTreesClassifier(n_estimators=100,random_state=SEED,n_jobs=-1).fit(XF[tr],y[tr])
    imp=permutation_importance(m,XF[te],y[te],scoring='matthews_corrcoef',n_repeats=20,random_state=SEED)
    names=B+F;out['D4_importance_E1']=sorted(((names[j],round(float(imp.importances_mean[j]),4)) for j in range(len(names))),key=lambda x:-x[1])[:10]
    (OUT/'diagnostics.json').write_text(json.dumps(out,indent=1,default=float)+'\n');print(json.dumps(out,indent=1,default=float))

if __name__=='__main__':main()
