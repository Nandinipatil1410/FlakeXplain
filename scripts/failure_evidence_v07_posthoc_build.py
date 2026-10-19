"""v0.7 POST-HOC diagnostic (not part of the frozen rule): P1 arms with folds grouped by build ID,
so that no other failure from the same build is in training (build-identity leakage check)."""
import csv,gzip,json
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold
from mdflaker_stage2 import SEED,REPEATS,load,sha
from mdflaker_stage3 import table,ci
from failure_evidence_v07_run import OUT,V7,ET,BASE,run,summ,delta,POPULATION

def main():
    rows,X,y,meta=load();projects=np.array([m['project'] for m in meta]);builds=np.array([m['project']+'|'+m['build_id'] for m in meta])
    _,C=table('features_context.csv.gz')
    with gzip.open(V7/'features_failure.csv.gz','rt',encoding='utf-8') as f:fr=list(csv.DictReader(f))
    idx=np.array([int(r['row']) for r in fr]);F=np.array([[float(r[c]) for c in fr[0] if c!='row'] for r in fr])
    X,y,C,b,proj=X[idx],y[idx],C[idx],builds[idx],projects[idx];XF=np.hstack([X,F]);XFC=np.hstack([X,F,C])
    folds=[list(StratifiedGroupKFold(10,shuffle=True,random_state=SEED+r).split(X,y,b)) for r in range(REPEATS)]
    res=run({'KNN8-float':(BASE['KNN8-float'],X),'MDF-paper-int':(BASE['MDF-paper-int'],X),'ET-B':(ET,X),'ET-BF':(ET,XF),'ET-BFC':(ET,XFC)},y,folds)
    S=summ(res,y,proj)
    out=dict(post_hoc=True,script_sha256=sha(__file__),builds=len(set(b)),arms=S,
        d_ETBF_vs_KNN8=delta(res,'ET-BF','KNN8-float'),d_ETBF_vs_ETB=delta(res,'ET-BF','ET-B'),d_ETBFC_vs_ETBF=delta(res,'ET-BFC','ET-BF'))
    (OUT/'posthoc_build_grouped.json').write_text(json.dumps(out,indent=1,default=float)+'\n')
    for n,s in S.items():print(n,round(s['mcc']['mean'],3),{k:round(v,3) for k,v in s['per_project_mcc'].items()})
    for k in ('d_ETBF_vs_KNN8','d_ETBF_vs_ETB','d_ETBFC_vs_ETBF'):print(k,round(out[k]['mean'],3),[round(v,3) for v in out[k]['ci95']])

if __name__=='__main__':main()
