"""v0.6 stage 3: frozen comparison (PROTOCOL.md + amendments A1, A2) and secondary analyses.

Arms, splits, seeds and thresholds are the frozen ones; nothing here is tuned.
"""
import csv,gzip,json
from pathlib import Path
import numpy as np
from scipy import stats
from sklearn.ensemble import ExtraTreesClassifier,RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import matthews_corrcoef,f1_score
from mdflaker_stage2 import ROOT,LOCAL,OUT,SEED,REPEATS,POPULATION,load,knn8,mdf_paper,as_int,splits,metrics,sha

def table(name):
    with gzip.open(LOCAL/'stage1'/name,'rt',encoding='utf-8') as f:r=list(csv.DictReader(f))
    cols=[c for c in r[0] if c!='row'];return cols,np.array([[float(x[c]) for c in cols] for x in r])

def forest(cls):
    def fit(Xtr,ytr,Xte,seed):
        m=cls(n_estimators=100,random_state=seed,n_jobs=-1).fit(Xtr,ytr);p=m.predict_proba(Xte)[:,list(m.classes_).index(1)]
        return (p>=0.5).astype(int),p
    return fit
ET=forest(ExtraTreesClassifier);RF=forest(RandomForestClassifier)
def bstar(Xtr,ytr,Xte,seed):return knn8(Xtr,ytr,Xte)  # B* = KNN8-float (stage 2)

def run(arms,y,folds_by_repeat):
    out={n:[] for n in arms}
    for r,folds in enumerate(folds_by_repeat):
        for n,(fit,X) in arms.items():
            pred=np.zeros(len(y),int);score=np.zeros(len(y))
            for tr,te in folds:pred[te],score[te]=fit(X[tr],y[tr],X[te],SEED+r)
            out[n].append(dict(metrics(y,pred,score),pred=pred))
    return out

def ci(v):
    v=np.asarray(v,float);h=stats.t.ppf(.975,len(v)-1)*v.std(ddof=1)/np.sqrt(len(v)) if len(v)>1 else float('nan')
    return dict(mean=float(v.mean()),ci95=[float(v.mean()-h),float(v.mean()+h)])

def summarize(res,y,proj):
    s={}
    for n,reps in res.items():
        s[n]={k:ci([r[k] for r in reps]) for k in ('mcc','f1','precision','recall','accuracy','ap')}
        allp=np.concatenate([r['pred'] for r in reps]);ally=np.tile(y,len(reps));allg=np.tile(proj,len(reps))
        s[n]['pooled_project_mcc']={p:float(matthews_corrcoef(ally[allg==p],allp[allg==p])) for p in POPULATION}
    return s

def delta(res,a,b,k='mcc'):return ci([x[k]-z[k] for x,z in zip(res[a],res[b])])

def prior_scores(Xbody_ctx_new):
    """S5: ET trained on the development corpus (v0.2 body+context, v0.1 labels), DRF cases removed."""
    D=ROOT/'dataset'
    def read(p):
        with gzip.open(p,'rt',encoding='utf-8') as f:return {r['example_id']:r for r in csv.DictReader(f)}
    meta,lab,body,ctx=(read(D/'v0.1/metadata.csv.gz'),read(D/'v0.1/labels.csv.gz'),read(D/'development-v0.2/features_body.csv.gz'),read(D/'development-v0.2/features_context.csv.gz'))
    schema=json.loads((D/'development-v0.2/schema.json').read_text());cols=schema['body_columns']+schema['context_columns']
    ids=[e for e in body if meta[e]['project']!='djangorestframework']
    X=np.array([[float({**body[e],**ctx[e]}[c]) for c in cols] for e in ids]);y=np.array([int(lab[e]['label']) for e in ids])
    m=ExtraTreesClassifier(n_estimators=100,random_state=SEED,n_jobs=-1).fit(X,y)
    return m.predict_proba(Xbody_ctx_new)[:,list(m.classes_).index(1)],dict(training_cases=len(ids),positives=int(y.sum()),excluded_project='djangorestframework')

def main():
    rows,X,y,meta=load();groups=np.array([m['group_id'] for m in meta]);projects=np.array([m['project'] for m in meta])
    ccols,C=table('features_context.csv.gz');bcols,B=table('features_body.csv.gz')
    idx=np.flatnonzero(np.isin(projects,POPULATION));X,y,C,B,groups,proj=X[idx],y[idx],C[idx],B[idx],groups[idx],projects[idx]
    XC=np.hstack([X,C]);report=dict(stage=3,script_sha256=sha(__file__),stage1_files={n:sha(LOCAL/'stage1'/n) for n in ('metadata.csv.gz','features_context.csv.gz','features_body.csv.gz')},
        rows=len(y),context_columns=len(ccols),B_star='KNN8-float')
    # Primary: test-grouped 10-fold CV, 30 repeats, same splits as stage 2.
    folds=[splits(y,groups,r) for r in range(REPEATS)]
    prim=run({'KNN-B*':(bstar,X),'ET-B':(ET,X),'ET-BC':(ET,XC)},y,folds)
    P=summarize(prim,y,proj);report['primary']=P
    C1=dict(d_mcc=delta(prim,'ET-BC','KNN-B*'),d_f1=delta(prim,'ET-BC','KNN-B*','f1'))
    C1['met']=C1['d_mcc']['mean']>=0.05 and C1['d_mcc']['ci95'][0]>0 and C1['d_f1']['mean']>=0
    C2=dict(d_mcc=delta(prim,'ET-BC','ET-B'));C2['met']=C2['d_mcc']['mean']>=0.02 and C2['d_mcc']['ci95'][0]>0
    gap={p:P['ET-BC']['pooled_project_mcc'][p]-P['KNN-B*']['pooled_project_mcc'][p] for p in POPULATION}
    nodeg=all(g>-0.05 for g in gap.values());robust=all(g>0 for g in gap.values())
    g2=json.loads((OUT/'stage2_summary.json').read_text());g1ok=g2['G1']['passed'];g2ok=g2['G2a']['passed']
    report['rule']=dict(G1_passed=g1ok,G2a_passed=g2ok,C1=C1,C2=C2,project_gap_vs_Bstar=gap,no_degradation=nodeg,robust_both_projects=robust,
        headline_met=bool(g1ok and C1['met'] and C2['met'] and nodeg),
        qualifier=('against our reimplementation of the described method' if not g2ok else 'against the released implementation'),
        strength=('robust across projects' if robust else 'supported on pooled data only'))
    # S1: authors' row-level protocol.
    s1folds=[list(StratifiedKFold(10,shuffle=True,random_state=SEED+r).split(X,y)) for r in range(REPEATS)]
    s1=run({'KNN-B*':(bstar,X),'ET-B':(ET,X),'ET-BC':(ET,XC)},y,s1folds)
    report['S1_row_level']=dict(arms=summarize(s1,y,proj),d_C1=delta(s1,'ET-BC','KNN-B*'),d_C2=delta(s1,'ET-BC','ET-B'),
        memorization_gap={n:report_gap for n,report_gap in ((n,summarize(s1,y,proj)[n]['mcc']['mean']-P[n]['mcc']['mean']) for n in s1)})
    # S2: leave-one-project-out (2 folds, deterministic).
    lopo=[[(np.flatnonzero(proj!=p),np.flatnonzero(proj==p)) for p in POPULATION]]
    s2=run({'KNN-B*':(bstar,X),'MDF-paper-int':(lambda a,b,c,s:mdf_paper(as_int(a),b,as_int(c)),X),'ET-B':(ET,X),'ET-BC':(ET,XC)},y,lopo)
    report['S2_leave_one_project_out']={n:dict(per_project={p:float(matthews_corrcoef(y[proj==p],r[0]['pred'][proj==p])) for p in POPULATION},
        per_project_f1={p:float(f1_score(y[proj==p],r[0]['pred'][proj==p])) for p in POPULATION}) for n,r in s2.items()}
    # S4: static-only (Test Smells, Test Size, context); S5: transfer prior; S6: Random Forest.
    XS=np.hstack([X[:,[2,4]],C]);score,info=prior_scores(np.hstack([B,C[:,:-1]]))
    XP=np.hstack([XC,score[:,None]])
    sec=run({'ET-static':(ET,XS),'ET-BC+prior':(ET,XP),'RF-B':(RF,X),'RF-BC':(RF,XC)},y,folds)
    S=summarize(sec,y,proj)
    report['S4_static_only']=dict(arm=S['ET-static'],d_vs_KNN_Bstar=ci([a['mcc']-b['mcc'] for a,b in zip(sec['ET-static'],prim['KNN-B*'])]))
    report['S5_transfer_prior']=dict(prior=info,arm=S['ET-BC+prior'],d_vs_ET_BC=ci([a['mcc']-b['mcc'] for a,b in zip(sec['ET-BC+prior'],prim['ET-BC'])]))
    report['S6_random_forest']=dict(arms={'RF-B':S['RF-B'],'RF-BC':S['RF-BC']},d_RF_BC_vs_RF_B=delta(sec,'RF-BC','RF-B'),
        d_RF_BC_vs_KNN_Bstar=ci([a['mcc']-b['mcc'] for a,b in zip(sec['RF-BC'],prim['KNN-B*'])]))
    (OUT/'stage3_results.json').write_text(json.dumps(report,indent=1,default=float)+'\n')
    print(json.dumps(report['rule'],indent=1,default=float))
    for n,s in P.items():print(n,round(s['mcc']['mean'],4),s['pooled_project_mcc'])

if __name__=='__main__':main()
