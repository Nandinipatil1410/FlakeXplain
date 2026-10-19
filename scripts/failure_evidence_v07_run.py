"""v0.7: comparator selection (baseline arms only), then P1/P2 arms, rerun-cost endpoint and secondaries."""
import csv,gzip,json
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier,RandomForestClassifier
from sklearn.model_selection import StratifiedKFold,StratifiedGroupKFold
from sklearn.inspection import permutation_importance
from sklearn.metrics import matthews_corrcoef
from mdflaker_stage2 import ROOT,LOCAL,SEED,REPEATS,POPULATION,load,knn8,mdf_paper,as_int,splits,metrics,sha
from mdflaker_stage3 import table,ci

OUT=ROOT/'reports/failure-evidence-v0.7';V7=ROOT/'local-evidence/failure-evidence-v0.7'
def forest(cls):
    def fit(Xtr,ytr,Xte,seed):
        m=cls(n_estimators=100,random_state=seed,n_jobs=-1).fit(Xtr,ytr);p=m.predict_proba(Xte)[:,list(m.classes_).index(1)]
        return (p>=0.5).astype(int),p
    return fit
ET=forest(ExtraTreesClassifier);RF=forest(RandomForestClassifier)
BASE={'MDF-paper-int':lambda a,b,c,s:mdf_paper(as_int(a),b,as_int(c)),'MDF-paper-float':lambda a,b,c,s:mdf_paper(a,b,c),
      'KNN8-int':lambda a,b,c,s:knn8(as_int(a),b,as_int(c)),'KNN8-float':lambda a,b,c,s:knn8(a,b,c)}

def run(arms,y,folds_by_repeat,seeds=None):
    out={n:[] for n in arms}
    for r,folds in enumerate(folds_by_repeat):
        for n,(fit,X) in arms.items():
            pred=np.zeros(len(y),int);score=np.zeros(len(y))
            for tr,te in folds:pred[te],score[te]=fit(X[tr],y[tr],X[te],SEED+(r if seeds is None else seeds[r]))
            out[n].append(dict(metrics(y,pred,score),pred=pred))
    return out

def per_project(reps,y,proj):return {p:float(np.mean([matthews_corrcoef(y[proj==p],r['pred'][proj==p]) for r in reps])) for p in POPULATION}
def summ(res,y,proj):return {n:dict({k:ci([r[k] for r in v]) for k in ('mcc','f1','precision','recall','ap')},per_project_mcc=per_project(v,y,proj)) for n,v in res.items()}
def delta(res,a,b,k='mcc'):return ci([x[k]-z[k] for x,z in zip(res[a],res[b])])

def rerun_fraction(fit,X,y,groups,folds,seed,recall=0.95):
    """Rerun if score >= t; t chosen from inner grouped 5-fold OOF scores of the training fold (95% of flaky reach t)."""
    rerun=np.zeros(len(y),bool)
    for tr,te in folds:
        oof=np.zeros(len(tr))
        for itr,ite in StratifiedGroupKFold(5,shuffle=True,random_state=seed).split(X[tr],y[tr],groups[tr]):
            oof[ite]=fit(X[tr][itr],y[tr][itr],X[tr][ite],seed)[1]
        t=np.quantile(oof[y[tr]==1],1-recall);rerun[te]=fit(X[tr],y[tr],X[te],seed)[1]>=t
    return float(rerun.mean()),float(rerun[y==1].mean())

def main():
    rows,X,y,meta=load();groups=np.array([m['group_id'] for m in meta]);projects=np.array([m['project'] for m in meta])
    _,C=table('features_context.csv.gz')
    with gzip.open(V7/'features_failure.csv.gz','rt',encoding='utf-8') as f:fr=list(csv.DictReader(f))
    fcols=[c for c in fr[0] if c!='row'];idx=np.array([int(r['row']) for r in fr]);F=np.array([[float(r[c]) for c in fcols] for r in fr])
    assert set(projects[idx])==set(POPULATION) and len(idx)==int(np.isin(projects,POPULATION).sum())
    X,y,C,groups,proj=X[idx],y[idx],C[idx],groups[idx],projects[idx]
    XF=np.hstack([X,F]);XFC=np.hstack([X,F,C])
    rep=dict(version='v0.7',script_sha256=sha(__file__),protocol_sha256=sha(OUT/'PROTOCOL.md'),features_sha256=sha(V7/'features_failure.csv.gz'),rows=len(y),failure_columns=fcols)
    P1f=[splits(y,groups,r) for r in range(REPEATS)];P2f=[(np.flatnonzero(proj!=p),np.flatnonzero(proj==p)) for p in POPULATION]
    # 1) Comparator selection from baseline arms only.
    b1=run({n:(f,X) for n,f in BASE.items()},y,P1f);b2=run({n:(f,X) for n,f in BASE.items()},y,[P2f])
    comp1=max(b1,key=lambda n:np.mean([r['mcc'] for r in b1[n]]));comp2=max(b2,key=lambda n:np.mean(list(per_project(b2[n],y,proj).values())))
    rep['comparators']=dict(P1=comp1,P2=comp2,P1_candidates={n:ci([r['mcc'] for r in v]) for n,v in b1.items()},P2_candidates={n:per_project(v,y,proj) for n,v in b2.items()})
    (OUT/'comparators.json').write_text(json.dumps(rep['comparators'],indent=1,default=float)+'\n')
    # 2) P1 arms.
    p1=run({'ET-B':(ET,X),'ET-BF':(ET,XF),'ET-BFC':(ET,XFC),'ET-F':(ET,F),'RF-BF':(RF,XF),'RF-BFC':(RF,XFC)},y,P1f);p1[comp1]=b1[comp1]
    S1=summ(p1,y,proj);rep['P1']=S1
    d1=delta(p1,'ET-BF',comp1);d1b=delta(p1,'ET-BF','ET-B');dctx=delta(p1,'ET-BFC','ET-BF')
    # 3) P2 arms (30 seeds for forests; base deterministic).
    p2=run({'ET-B':(ET,X),'ET-BF':(ET,XF),'ET-BFC':(ET,XFC)},y,[P2f]*REPEATS)
    pp2={n:per_project(v,y,proj) for n,v in p2.items()};pp2[comp2]=per_project(b2[comp2],y,proj)
    seed_sd={n:{p:float(np.std([matthews_corrcoef(y[proj==p],r['pred'][proj==p]) for r in v],ddof=1)) for p in POPULATION} for n,v in p2.items()}
    rep['P2']=dict(per_project_mcc=pp2,seed_sd=seed_sd)
    gap2={p:pp2['ET-BF'][p]-pp2[comp2][p] for p in POPULATION}
    ctx2={p:pp2['ET-BFC'][p]-pp2['ET-BF'][p] for p in POPULATION}
    # 4) Rerun-cost endpoint (P1 folds, 30 repeats).
    cost={n:[rerun_fraction(f,Xm,y,groups,P1f[r],SEED+r) for r in range(REPEATS)] for n,(f,Xm) in {'ET-BF':(ET,XF),comp1:(BASE[comp1],X)}.items()}
    frac={n:ci([c[0] for c in v]) for n,v in cost.items()};rec={n:ci([c[1] for c in v]) for n,v in cost.items()}
    saving=1-frac['ET-BF']['mean']/frac[comp1]['mean']
    # 5) Rule.
    r1=d1['mean']>=0.05 and d1['ci95'][0]>0;r2=d1b['mean']>=0.02 and d1b['ci95'][0]>0
    r3=all(g>0 for g in gap2.values()) and np.mean(list(gap2.values()))>=0.05
    rep['rule']=dict(R1_P1_vs_comparator=dict(d_mcc=d1,met=r1),R2_P1_vs_ET_B=dict(d_mcc=d1b,met=r2),
        R3_P2_vs_comparator=dict(per_project_gap=gap2,mean_gap=float(np.mean(list(gap2.values()))),met=bool(r3)),
        headline_met=bool(r1 and r2 and r3),
        context_claim=dict(P1_d_mcc=dctx,P2_per_project=ctx2,met=bool(dctx['mean']>=0.02 and dctx['ci95'][0]>0 and all(v>=-0.02 for v in ctx2.values()))),
        cost=dict(rerun_fraction=frac,flaky_recall=rec,saving=saving,met=bool(saving>=0.10)),
        qualifiers=['against our reimplementation of the described method','two of three projects (spaCy, django-rest-framework)','exploratory follow-up on data inspected in v0.6'])
    # 6) Secondaries: row-level memorization check, permutation importance.
    rl=[list(StratifiedKFold(10,shuffle=True,random_state=SEED+r).split(X,y)) for r in range(REPEATS)]
    s1=run({'ET-B':(ET,X),'ET-BF':(ET,XF),'ET-BFC':(ET,XFC),comp1:(BASE[comp1],X)},y,rl)
    rep['S_row_level']={n:ci([r['mcc'] for r in v]) for n,v in s1.items()}
    imp=np.zeros(XF.shape[1]);names=['FF','TracebackCov','Smells','PrevState','Size']+fcols
    for tr,te in P1f[0]:
        m=ExtraTreesClassifier(n_estimators=100,random_state=SEED,n_jobs=-1).fit(XF[tr],y[tr])
        imp+=permutation_importance(m,XF[te],y[te],scoring='matthews_corrcoef',n_repeats=5,random_state=SEED).importances_mean
    rep['S_permutation_importance_ET_BF']=dict(sorted(zip(names,(imp/10).tolist()),key=lambda x:-x[1]))
    (OUT/'results.json').write_text(json.dumps(rep,indent=1,default=float)+'\n')
    print(json.dumps(dict(comparators=dict(P1=comp1,P2=comp2),rule=rep['rule']),indent=1,default=float))
    for n,s in S1.items():print('P1',n,round(s['mcc']['mean'],4),{k:round(v,3) for k,v in s['per_project_mcc'].items()})
    print('P2',json.dumps(pp2,default=float))

if __name__=='__main__':main()
