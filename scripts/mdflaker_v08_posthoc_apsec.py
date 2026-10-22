"""v0.8 post hoc: MDFlaker as described in the APSEC 2021 paper (outside the frozen rule; other JSON
files are not touched).

A1 KNN5 baseline: KNN with k = number of factors + 1 = 5, Manhattan distance, majority vote, on the four
   APSEC factors (trace-back coverage, flaky frequency, test smells, test size; no previous state and no
   conditional rule). Float factors as described, and integer-cast as in the authors' released code.
A2 Factor ablation: the APSEC Table III full factorial design, i.e. KNN5 on all 15 non-empty factor
   combinations plus a random classifier (fair coin, the "all factors disabled" row).

Evaluated on E1 (time-ordered, original history, as frozen), E2 (leave-one-project-out, original history,
as frozen) and the unseen-tests subset of E1 with strict history (the main post-hoc set). ET-BF,
MDF-paper-int and KNN8-float are recomputed on the same splits as reference rows, so they must equal
results.json / robustness.json. Labels are used only as targets and for scoring.
"""
import csv,gzip,itertools,json,sys
from pathlib import Path
import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.neighbors import KNeighborsClassifier
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_analyze import B,F,V8,OUT,SEED,et,knn8,mdf_paper,mcc,metrics,boot
from mdflaker_v08_features import CAND
from mdflaker_v08_robustness import strict_frequency,e1_split

# APSEC Table III factor names and order -> our feature columns
FACTORS={'trace-back':'traceback_coverage','frequency':'flaky_frequency','smells':'test_smells','size':'test_size'}
TABLE3_ORDER=[('frequency',),('size',),('smells',),('trace-back',),('size','frequency'),('smells','size'),('smells','frequency'),
    ('trace-back','size'),('trace-back','smells'),('trace-back','frequency'),('size','smells','frequency'),('trace-back','size','frequency'),
    ('trace-back','size','smells'),('trace-back','smells','frequency'),('trace-back','smells','frequency','size')]


def knn5(Xtr,ytr,Xte):
    return KNeighborsClassifier(min(5,len(ytr)),p=1).fit(Xtr,ytr).predict(Xte)


def coin(n,seed):
    return np.random.default_rng(seed).integers(0,2,n)


def ci(y,a,b,p):
    return boot(y,a,b,p,np.random.default_rng(SEED))


def scored(y,p):
    m=metrics(y,p);m['accuracy']=float(accuracy_score(y,p));return m


def main():
    assert {frozenset(c) for c in TABLE3_ORDER}=={frozenset(c) for r in range(1,5) for c in itertools.combinations(FACTORS,r)}
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')))
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']):int(r['label']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);rows=[feat[i] for i in ids]
    _,strict=strict_frequency(cands);fs=np.array([strict[i] for i in ids])
    X=np.array([[float(r[k]) for k in B] for r in rows]);XF=np.hstack([X,np.array([[float(r[k]) for k in F] for r in rows])])
    j=B.index('flaky_frequency');Xs=X.copy();Xs[:,j]=fs;XFs=XF.copy();XFs[:,j]=fs
    y=np.array([lab[i] for i in ids]);proj=np.array([r['repo'] for r in rows]);t=np.array([r['created_at'] for r in rows])
    tr,te=e1_split(proj,t)
    node=np.array([r['repo']+'|'+r['nodeid'].split('[')[0] for r in rows]);seen=set(node[tr]);unseen=np.array([n not in seen for n in node[te]])
    col={name:B.index(c) for name,c in FACTORS.items()}

    def splits(kind):
        if kind=='E2':return [(np.flatnonzero(proj!=p),np.flatnonzero(proj==p)) for p in np.unique(proj)]
        return [(tr,te)]

    def pooled(fit,Xm,spl):
        test=np.concatenate([b for _,b in spl]);p=np.zeros(len(y),int)
        for a,b in spl:p[b]=fit(Xm[a],y[a],Xm[b])
        return test,p[test]

    sets={'E1':('E1',X,XF,None),'E2':('E2',X,XF,None),'unseen_E1_strict':('E1',Xs,XFs,unseen)}
    rep=dict(note='post hoc; outside the frozen rule; results.json, robustness.json and posthoc_extra.json unchanged',
        seed=SEED,knn='k=5, Manhattan (p=1), majority vote, unscaled; APSEC 2021 Sec. IV-C and V-A',
        random='fair coin per failure, seeded with SEED + 16 (APSEC Table III row 16)',
        bootstrap='project bootstrap, 2,000 resamples, fresh generator per interval')
    for name,(kind,Xb,XFb,mask) in sets.items():
        spl=splits(kind)
        test,_=pooled(knn5,Xb[:,[col['trace-back']]],spl)
        keep=np.ones(len(test),bool) if mask is None else mask
        yt,pt=y[test][keep],proj[test][keep]
        preds={}
        for integer in (False,True):
            Xk=np.trunc(Xb) if integer else Xb;tag='int' if integer else 'float'
            for combo in TABLE3_ORDER:
                _,p=pooled(knn5,Xk[:,[col[c] for c in combo]],spl);preds[f'KNN5-{tag}: '+', '.join(combo)]=p[keep]
        preds['random (coin)']=coin(len(test),SEED+16)[keep]
        _,p=pooled(mdf_paper,np.trunc(Xb),spl);preds['ref MDF-paper-int']=p[keep]
        _,p=pooled(knn8,Xb,spl);preds['ref KNN8-float']=p[keep]
        _,p=pooled(et,XFb,spl);preds['ref ET-BF']=p[keep]
        allf='KNN5-float: trace-back, smells, frequency, size';alli='KNN5-int: trace-back, smells, frequency, size'
        best5=max((a for a in preds if a.startswith('KNN5')),key=lambda a:np.nan_to_num(mcc(yt,preds[a]),nan=-9))
        rep[name]=dict(n=int(len(yt)),flaky=int(yt.sum()),projects=int(len(set(pt))),
            arms={a:scored(yt,p) for a,p in preds.items()},best_knn5_combination=best5,
            d_ETBF_vs_KNN5_all_float=dict(mcc=mcc(yt,preds['ref ET-BF'])-mcc(yt,preds[allf]),ci95=ci(yt,preds['ref ET-BF'],preds[allf],pt)),
            d_ETBF_vs_KNN5_all_int=dict(mcc=mcc(yt,preds['ref ET-BF'])-mcc(yt,preds[alli]),ci95=ci(yt,preds['ref ET-BF'],preds[alli],pt)),
            d_ETBF_vs_best_KNN5=dict(mcc=mcc(yt,preds['ref ET-BF'])-mcc(yt,preds[best5]),ci95=ci(yt,preds['ref ET-BF'],preds[best5],pt)))
    (OUT/'posthoc_apsec.json').write_text(json.dumps(rep,indent=1,default=float)+'\n')
    for name in sets:
        o=rep[name];print(f"\n{name}: n={o['n']} flaky={o['flaky']} projects={o['projects']} best KNN5 = {o['best_knn5_combination']}")
        for a,m in o['arms'].items():print(f"  {a:55s} MCC {m['mcc']:+.3f}  F1 {m['f1']:.3f}  acc {m['accuracy']:.3f}  P {m['precision']:.3f}  R {m['recall']:.3f}")
        for k in ('d_ETBF_vs_KNN5_all_float','d_ETBF_vs_KNN5_all_int','d_ETBF_vs_best_KNN5'):
            print(f"  {k}: {o[k]['mcc']:+.3f} {[round(c,3) for c in o[k]['ci95']]}")


if __name__=='__main__':main()
