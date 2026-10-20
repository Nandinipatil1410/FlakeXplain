"""v0.8 post-hoc robustness (outside the frozen rule; results.json is not touched).

R1 strict history: `flaky_frequency_strict` counts only failures of the test in EARLIER workflow runs
   (other run_id and log created_at < the failure's created_at), so sibling jobs of the same run, which may
   not have finished at prediction time, are excluded. E1, E2 and the E1 unseen-tests check are rerun for
   MDF-paper-int, KNN8-float and ET-BF with the strict feature replacing the original.
R2 SHAP explanations: ET-BF trained on the E1 training part, shap.TreeExplainer on the E1 test part;
   global mean-|SHAP| ranking and three local explanations (flaky TP, not-flaky TN, most confident error).

Sources: candidates.csv, the saved CI job logs and their metadata, features.csv.gz and labels.csv. Labels are
used only as targets and for scoring; rerun outcomes are never features.
"""
import csv,gzip,json,sys,datetime
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_analyze import B,F,V8,OUT,SEED,BASE,et,knn8,mdf_paper,mcc,metrics,boot,evaluate
from mdflaker_v08_features import LOGS,CAND,flaky_frequency
from mdflaker_v08_probe import parse,read_log
from sklearn.ensemble import ExtraTreesClassifier

def ts(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))

def strict_frequency(cands):
    """flaky_frequency per candidate, original (<= created_at, any run) and strict (earlier runs only)."""
    hist=defaultdict(list)
    for d in LOGS.iterdir():
        for t in d.glob('*.txt*'):
            m=json.loads((d/(t.name.split('.')[0]+'.json')).read_text());when=ts(m['created_at'])
            for n in parse(read_log(t)):hist[(d.name,n.split('[')[0].replace(chr(92),'/'))].append((when,str(m['run_id'])))
    orig={};strict={}
    for i,c in enumerate(cands):
        node=c['nodeid'].split('::',1)[0].replace(chr(92),'/')+('::'+c['nodeid'].split('::',1)[1] if '::' in c['nodeid'] else '')
        h=hist[(c['repo'].replace('/','__'),node.split('[')[0])];when=ts(c['created_at'])
        orig[i]=flaky_frequency([w for w,_ in h],when)
        strict[i]=flaky_frequency([w for w,r in h if r!=str(c['run_id']) and w<when],when)
    return orig,strict

def e1_split(proj,t):
    tr=[];te=[]
    for p in np.unique(proj):
        ix=np.flatnonzero(proj==p);ix=ix[np.argsort(t[ix],kind='stable')];k=int(round(0.6*len(ix)));tr+=list(ix[:k]);te+=list(ix[k:])
    return np.array(tr),np.array(te)

def main():
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')))
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']):int(r['label']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);rows=[feat[i] for i in ids]
    orig,strict=strict_frequency(cands)
    stored=np.array([float(r['flaky_frequency']) for r in rows]);recomputed=np.array([orig[i] for i in ids]);fs=np.array([strict[i] for i in ids])
    X=np.array([[float(r[k]) for k in B] for r in rows]);XF=np.hstack([X,np.array([[float(r[k]) for k in F] for r in rows])])
    j=B.index('flaky_frequency');Xs=X.copy();Xs[:,j]=fs;XFs=XF.copy();XFs[:,j]=fs
    y=np.array([lab[i] for i in ids]);proj=np.array([r['repo'] for r in rows]);t=np.array([r['created_at'] for r in rows])
    rep=dict(note='post hoc; outside the frozen rule; results.json unchanged',labelled=int(len(y)),flaky=int(y.sum()))
    rep['R1_feature']=dict(recomputed_matches_stored=int((np.abs(recomputed-stored)<1e-9).sum()),
        changed_by_strict=int((np.abs(fs-stored)>1e-9).sum()),strict_zero=int((fs==0).sum()),original_zero=int((stored==0).sum()),
        mean_original=float(stored.mean()),mean_strict=float(fs.mean()),
        mean_by_label=dict(original=dict(flaky=float(stored[y==1].mean()),not_flaky=float(stored[y==0].mean())),
                           strict=dict(flaky=float(fs[y==1].mean()),not_flaky=float(fs[y==0].mean()))))
    tr,te=e1_split(proj,t);E1=[(tr,te)];E2=[(np.flatnonzero(proj!=p),np.flatnonzero(proj==p)) for p in np.unique(proj)]
    variants=dict(original=(X,XF),strict=(Xs,XFs));r1={};rng=np.random.default_rng(SEED)
    for v,(Xb,XFb) in variants.items():
        arms={'MDF-paper-int':(mdf_paper,np.trunc(Xb)),'KNN8-float':(knn8,Xb),'ET-BF':(et,XFb)};r1[v]={}
        for name,spl in (('E1',E1),('E2',E2)):
            yt,pt,preds,res=evaluate(name,spl,Xb,y,proj,arms)
            for a in res:res[a].pop('per_project_mcc')
            r1[v][name]=dict(arms=res,d_ETBF_vs_KNN8=dict(mcc=res['ET-BF']['mcc']-res['KNN8-float']['mcc'],ci95=boot(yt,preds['ET-BF'],preds['KNN8-float'],pt,rng)),
                d_ETBF_vs_MDF=dict(mcc=res['ET-BF']['mcc']-res['MDF-paper-int']['mcc'],ci95=boot(yt,preds['ET-BF'],preds['MDF-paper-int'],pt,rng)))
        # unseen tests: E1 test failures whose test (params stripped) never occurs in training (as diagnostics D5)
        node=np.array([r['repo']+'|'+r['nodeid'].split('[')[0] for r in rows]);seen=set(node[tr]);u=np.array([n not in seen for n in node[te]])
        p={a:fit(Xm[tr],y[tr],Xm[te]) for a,(fit,Xm) in arms.items()};yu=y[te][u]
        r1[v]['unseen_E1']=dict(n=int(u.sum()),flaky=int(yu.sum()),arms={a:metrics(yu,q[u]) for a,q in p.items()},
            d_ETBF_vs_KNN8=dict(mcc=mcc(yu,p['ET-BF'][u])-mcc(yu,p['KNN8-float'][u]),ci95=boot(yu,p['ET-BF'][u],p['KNN8-float'][u],proj[te][u],rng)))
    rep['R1_strict_history']=r1
    # R2 SHAP on ET-BF (same estimator settings as analyze.et)
    import shap
    names=B+F;r2={'shap_version':shap.__version__}
    for v,XFb in (('original',XF),('strict',XFs)):
        m=ExtraTreesClassifier(n_estimators=100,random_state=SEED,n_jobs=-1).fit(XFb[tr],y[tr]);c1=list(m.classes_).index(1)
        ex=shap.TreeExplainer(m);sv=np.asarray(ex.shap_values(XFb[te]))
        sv=sv[c1] if sv.ndim==3 and sv.shape[0]==len(m.classes_) else sv[...,c1] if sv.ndim==3 else sv
        base=float(np.ravel(ex.expected_value)[c1]) if np.ndim(ex.expected_value) else float(ex.expected_value)
        prob=m.predict_proba(XFb[te])[:,c1];pred=(prob>=0.5).astype(int);yt=y[te]
        additivity=float(np.max(np.abs(base+sv.sum(1)-prob)))
        g=np.abs(sv).mean(0);order=np.argsort(-g)
        out=dict(model='ET-BF',train=int(len(tr)),test=int(len(te)),base_value=base,max_additivity_error=additivity,
            global_mean_abs_shap=[dict(feature=names[k],mean_abs_shap=round(float(g[k]),4),mean_shap_flaky=round(float(sv[yt==1,k].mean()),4),
                mean_shap_not_flaky=round(float(sv[yt==0,k].mean()),4)) for k in order])
        if v=='original':
            def local(i,kind):
                k=te[i];top=np.argsort(-np.abs(sv[i]))[:6]
                return dict(kind=kind,candidate=int(ids[k]),repo=rows[k]['repo'],nodeid=rows[k]['nodeid'],label=int(y[k]),predicted=int(pred[i]),
                    p_flaky=round(float(prob[i]),3),base_value=round(base,3),
                    top_contributions=[dict(feature=names[q],value=float(XFb[k,q]),shap=round(float(sv[i,q]),4)) for q in top],
                    other_features_shap=round(float(sv[i].sum()-sv[i,top].sum()),4))
            conf=np.abs(prob-0.5)
            def pick(mask):  # most confident case of the kind; ties -> lowest candidate id
                c=np.flatnonzero(mask);return c[np.lexsort((np.array(ids)[te[c]],-conf[c]))[0]]
            out['local_examples']=[local(pick((yt==1)&(pred==1)),'flaky true positive'),local(pick((yt==0)&(pred==0)),'not-flaky true negative'),
                local(pick(yt!=pred),'error ('+('false positive' if pred[pick(yt!=pred)]==1 else 'false negative')+')')]
            out['confusion']=dict(tp=int(((yt==1)&(pred==1)).sum()),tn=int(((yt==0)&(pred==0)).sum()),fp=int(((yt==0)&(pred==1)).sum()),fn=int(((yt==1)&(pred==0)).sum()))
        r2[v]=out
    rep['R2_shap_E1']=r2
    (OUT/'robustness.json').write_text(json.dumps(rep,indent=1,default=float)+'\n')
    print(json.dumps(rep['R1_feature'],indent=1))
    for v in r1:
        for e in ('E1','E2','unseen_E1'):print(v,e,{a:round(x['mcc'],3) for a,x in r1[v][e]['arms'].items()},'dETBF-KNN8',round(r1[v][e]['d_ETBF_vs_KNN8']['mcc'],3),r1[v][e]['d_ETBF_vs_KNN8']['ci95'])
    for v in ('original','strict'):print(v,'SHAP top',[(d['feature'],d['mean_abs_shap']) for d in r2[v]['global_mean_abs_shap'][:6]],'additivity',r2[v]['max_additivity_error'])
    for e in r2['original']['local_examples']:print(e['kind'],e['repo'],e['nodeid'],e['p_flaky'],[(d['feature'],d['value'],d['shap']) for d in e['top_contributions'][:3]])

if __name__=='__main__':main()
