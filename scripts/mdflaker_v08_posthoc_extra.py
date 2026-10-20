"""v0.8 extra post-hoc statistics for the paper draft (outside the frozen rule; results.json,
diagnostics.json and robustness.json are not touched).

X1 intervals missing from robustness.json, for original and strict history:
   - unseen tests (E1): ET-BF - MDF-paper-int;
   - E1 and unseen tests: ET-BF - project prior (each project's E1 training-majority class).
X2 per-project MCC on the unseen-tests subset (strict history).
X3 sensitivity without hypothesis: the same fitted models, scored on E1 / unseen-test failures from the
   other 7 projects only (training is unchanged).

Every bootstrap uses its own generator seeded with SEED, so each interval is reproducible on its own and
does not depend on how many intervals were computed before it.
"""
import csv,gzip,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_analyze import B,F,V8,OUT,SEED,et,knn8,mdf_paper,mcc,metrics,boot
from mdflaker_v08_features import CAND
from mdflaker_v08_robustness import strict_frequency,e1_split

def ci(y,a,b,p):return boot(y,a,b,p,np.random.default_rng(SEED))

def main():
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')))
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']):int(r['label']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);rows=[feat[i] for i in ids]
    _,strict=strict_frequency(cands);fs=np.array([strict[i] for i in ids])
    X=np.array([[float(r[k]) for k in B] for r in rows]);XF=np.hstack([X,np.array([[float(r[k]) for k in F] for r in rows])])
    j=B.index('flaky_frequency');Xs=X.copy();Xs[:,j]=fs;XFs=XF.copy();XFs[:,j]=fs
    y=np.array([lab[i] for i in ids]);proj=np.array([r['repo'] for r in rows]);t=np.array([r['created_at'] for r in rows])
    tr,te=e1_split(proj,t)
    node=np.array([r['repo']+'|'+r['nodeid'].split('[')[0] for r in rows]);seen=set(node[tr]);u=np.array([n not in seen for n in node[te]])
    prior=np.array([int(y[tr][proj[tr]==proj[i]].mean()>=0.5) for i in te])
    yt,pt=y[te],proj[te];nohyp=pt!='HypothesisWorks/hypothesis'
    rep=dict(note='post hoc; outside the frozen rule; other JSON files unchanged',seed=SEED,bootstrap='project bootstrap, 2,000 resamples, fresh generator per interval')
    for v,(Xb,XFb) in dict(original=(X,XF),strict=(Xs,XFs)).items():
        p={'MDF-paper-int':mdf_paper(np.trunc(Xb[tr]),y[tr],np.trunc(Xb[te])),'KNN8-float':knn8(Xb[tr],y[tr],Xb[te]),'ET-BF':et(XFb[tr],y[tr],XFb[te]),'project prior':prior}
        out={}
        for sub,m in (('E1',np.ones(len(te),bool)),('unseen_E1',u),('E1_without_hypothesis',nohyp),('unseen_E1_without_hypothesis',u&nohyp)):
            ys,ps=yt[m],pt[m]
            out[sub]=dict(n=int(m.sum()),flaky=int(ys.sum()),projects=int(len(set(ps))),arms={a:metrics(ys,q[m]) for a,q in p.items()},
                d_ETBF_vs_MDF=dict(mcc=mcc(ys,p['ET-BF'][m])-mcc(ys,p['MDF-paper-int'][m]),ci95=ci(ys,p['ET-BF'][m],p['MDF-paper-int'][m],ps)),
                d_ETBF_vs_KNN8=dict(mcc=mcc(ys,p['ET-BF'][m])-mcc(ys,p['KNN8-float'][m]),ci95=ci(ys,p['ET-BF'][m],p['KNN8-float'][m],ps)),
                d_ETBF_vs_prior=dict(mcc=mcc(ys,p['ET-BF'][m])-mcc(ys,prior[m]),ci95=ci(ys,p['ET-BF'][m],prior[m],ps)))
        out['unseen_E1_per_project']={q:dict(n=int((u&(pt==q)).sum()),flaky=int(yt[u&(pt==q)].sum()),
            **{a:mcc(yt[u&(pt==q)],p[a][u&(pt==q)]) for a in ('MDF-paper-int','KNN8-float','ET-BF')}) for q in np.unique(pt[u])}
        rep[v]=out
    (OUT/'posthoc_extra.json').write_text(json.dumps(rep,indent=1,default=float)+'\n')
    for v in ('original','strict'):
        for sub in ('E1','unseen_E1','E1_without_hypothesis','unseen_E1_without_hypothesis'):
            o=rep[v][sub];print(v,sub,o['n'],o['flaky'],{a:round(x['mcc'],3) for a,x in o['arms'].items()},
                {k:(round(o[k]['mcc'],3),[round(c,3) for c in o[k]['ci95']]) for k in ('d_ETBF_vs_MDF','d_ETBF_vs_KNN8','d_ETBF_vs_prior')})
        print(v,'per project',{q:{k:(round(x,3) if isinstance(x,float) else x) for k,x in d.items()} for q,d in rep[v]['unseen_E1_per_project'].items()})

if __name__=='__main__':main()
