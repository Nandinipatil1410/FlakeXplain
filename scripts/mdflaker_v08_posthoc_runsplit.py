"""v0.8 post-hoc check: does the E1 time split put failures from the same CI run (or commit) on both
sides? (Outside the frozen rule; results.json and the other JSON files are not touched.)

S1 measure: per project, workflow runs (run_id) and commits (head_sha) with failures in both the E1
   training and test parts, and the test failures that share a run or commit with training.
S2 drop: the same fitted models as E1, scored without the test failures whose run (or commit) also
   appears in training.
S3 regroup: a group-respecting time split. Per project, whole runs (or commits), ordered by their first
   failure time, go to training until it holds at least 60% of the project's failures; the rest go to
   test. Models are refitted on that split and scored on all of test and on unseen tests.
All for original and strict history. Each interval uses its own generator seeded with SEED.
"""
import csv,gzip,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_analyze import B,F,V8,OUT,SEED,et,knn8,mdf_paper,mcc,metrics,boot
from mdflaker_v08_features import CAND
from mdflaker_v08_robustness import strict_frequency,e1_split

def ci(y,a,b,p):return boot(y,a,b,p,np.random.default_rng(SEED))

def grouped_split(proj,t,g):
    tr=[];te=[]
    for p in np.unique(proj):
        ix=np.flatnonzero(proj==p);first={}
        for i in ix:first[g[i]]=min(first.get(g[i],t[i]),t[i])
        order=sorted(first,key=lambda k:(first[k],k));need=int(round(0.6*len(ix)));n=0
        trg=set()
        for k in order:
            if n>=need:break
            trg.add(k);n+=int((g[ix]==k).sum())
        tr+=[i for i in ix if g[i] in trg];te+=[i for i in ix if g[i] not in trg]
    return np.array(sorted(tr)),np.array(sorted(te))

def score(Xb,XFb,y,proj,node,tr,te,mask=None):
    p={'MDF-paper-int':mdf_paper(np.trunc(Xb[tr]),y[tr],np.trunc(Xb[te])),'KNN8-float':knn8(Xb[tr],y[tr],Xb[te]),'ET-BF':et(XFb[tr],y[tr],XFb[te])}
    p['project prior']=np.array([int(y[tr][proj[tr]==proj[i]].mean()>=0.5) for i in te])
    seen=set(node[tr]);u=np.array([n not in seen for n in node[te]])
    m=np.ones(len(te),bool) if mask is None else mask
    out={}
    for sub,mm in (('E1',m),('unseen_E1',m&u)):
        ys,ps=y[te][mm],proj[te][mm]
        out[sub]=dict(n=int(mm.sum()),flaky=int(ys.sum()),projects=int(len(set(ps))),arms={a:metrics(ys,q[mm]) for a,q in p.items()},
            **{f'd_ETBF_vs_{k}':dict(mcc=mcc(ys,p['ET-BF'][mm])-mcc(ys,p[a][mm]),ci95=ci(ys,p['ET-BF'][mm],p[a][mm],ps))
               for k,a in (('MDF','MDF-paper-int'),('KNN8','KNN8-float'),('prior','project prior'))})
    return out

def main():
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')))
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']):int(r['label']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);rows=[feat[i] for i in ids]
    _,strict=strict_frequency(cands);fs=np.array([strict[i] for i in ids])
    X=np.array([[float(r[k]) for k in B] for r in rows]);XF=np.hstack([X,np.array([[float(r[k]) for k in F] for r in rows])])
    j=B.index('flaky_frequency');Xs=X.copy();Xs[:,j]=fs;XFs=XF.copy();XFs[:,j]=fs
    y=np.array([lab[i] for i in ids]);proj=np.array([r['repo'] for r in rows]);t=np.array([r['created_at'] for r in rows])
    run=np.array([cands[i]['repo']+'|'+cands[i]['run_id'] for i in ids]);sha=np.array([cands[i]['repo']+'|'+cands[i]['head_sha'] for i in ids])
    node=np.array([r['repo']+'|'+r['nodeid'].split('[')[0] for r in rows])
    tr,te=e1_split(proj,t)
    rep=dict(note='post hoc; outside the frozen rule; other JSON files unchanged',seed=SEED)
    s1={}
    for gname,g in (('run',run),('commit',sha)):
        trs=set(g[tr]);shared=np.array([x in trs for x in g[te]])
        per={}
        for p in np.unique(proj):
            mtr=proj[tr]==p;mte=proj[te]==p
            both=set(g[tr][mtr])&set(g[te][mte])
            per[p]=dict(groups_both_sides=len(both),test_failures_sharing=int(shared[mte].sum()),test_failures=int(mte.sum()))
        s1[gname]=dict(groups_both_sides=int(sum(v['groups_both_sides'] for v in per.values())),
            test_failures_sharing=int(shared.sum()),test_failures=int(len(te)),flaky_among_sharing=int(y[te][shared].sum()),per_project=per)
    rep['S1_measure']=s1
    for v,(Xb,XFb) in dict(original=(X,XF),strict=(Xs,XFs)).items():
        r={'E1_as_frozen':score(Xb,XFb,y,proj,node,tr,te)}
        for gname,g in (('run',run),('commit',sha)):
            trs=set(g[tr]);keep=np.array([x not in trs for x in g[te]])
            r[f'drop_shared_{gname}']=score(Xb,XFb,y,proj,node,tr,te,keep)
            gtr,gte=grouped_split(proj,t,g)
            assert not (set(g[gtr])&set(g[gte]))
            r[f'regroup_{gname}']=dict(train=int(len(gtr)),**score(Xb,XFb,y,proj,node,gtr,gte))
        rep[v]=r
    (OUT/'posthoc_runsplit.json').write_text(json.dumps(rep,indent=1,default=float)+'\n')
    for g in ('run','commit'):
        s=s1[g];print('S1',g,'groups on both sides',s['groups_both_sides'],'test failures sharing',s['test_failures_sharing'],'/',s['test_failures'],'flaky',s['flaky_among_sharing'])
    for v in ('original','strict'):
        for k,o in rep[v].items():
            for sub in ('E1','unseen_E1'):
                x=o[sub];print(v,k,sub,x['n'],x['flaky'],{a:round(m['mcc'],3) for a,m in x['arms'].items()},
                    {d:(round(x[d]['mcc'],3),[round(c,2) for c in x[d]['ci95']]) for d in ('d_ETBF_vs_MDF','d_ETBF_vs_KNN8','d_ETBF_vs_prior')})

if __name__=='__main__':main()
