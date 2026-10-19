"""CANNIER-protocol context experiment (v0.5).

Re-runs the authors' released classifier protocol (cannier_framework/model.py) with the
18 released features versus the same 18 plus 66 static context features and one
context-availability indicator, paired by repeat, and re-implements the authors'
Rerun/iDFlakies/Pairwise cost simulation. See reports/cannier-protocol-v0.5/PROTOCOL.md.

Downloaded upstream Python and pickle files are never executed or deserialized.
"""
import argparse,gc,json,sqlite3,subprocess,time
from datetime import datetime,timezone
import numpy as np
from scipy import stats
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import ExtraTreesClassifier,RandomForestClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold,StratifiedGroupKFold
import sklearn,imblearn
from train_pilot import ROOT,sha,reader,write_csv,load_feature_table

AUTHORS=ROOT/'local-evidence/cannier-matched-v0.4'
MATCHED=ROOT/'dataset/cannier-matched-v0.4'
OUT=ROOT/'reports/cannier-protocol-v0.5'
LOCAL=ROOT/'local-evidence/cannier-protocol-v0.5'
SEED=20261019
N_MEASUREMENTS=30
N_RERUNS=2500
# Authors' BEST_MODELS and PROBLEMS: (domain column, label column, classifier, trees).
TASKS={'NOD-vs-Rest':(None,3,ExtraTreesClassifier,100),'NOD-vs-Victim':(5,3,RandomForestClassifier,75),
       'Victim-vs-Rest':(None,4,ExtraTreesClassifier,75),'Polluter-vs-Rest':(None,6,RandomForestClassifier,100)}
AUTHOR_PREDS={'NOD-vs-Rest':'NOD-vs-Rest_18_ExtraTrees_100_SMOTE','NOD-vs-Victim':'NOD-vs-Victim_18_RandomForest_75_SMOTE',
              'Victim-vs-Rest':'Victim-vs-Rest_18_ExtraTrees_75_SMOTE','Polluter-vs-Rest':'Polluter-vs-Rest_18_RandomForest_100_SMOTE'}
ANALYSES={'primary':30,'mapped_only':10,'family_grouped':10}
ARMS=('baseline','context')
RULE=dict(min_gain=0.05,degrade=-0.02,reproduction_tolerance=0.03,cost_saving=0.20,bootstrap=2000,
          reference_abs_mcc={'NOD-vs-Rest':0.532094,'NOD-vs-Victim':0.692611,'Victim-vs-Rest':0.519517,'Polluter-vs-Rest':0.945824})

# ---------------------------------------------------------------- data

def load_data():
    items=np.load(AUTHORS/'output/items.npy',allow_pickle=False)
    features=np.load(AUTHORS/'output/features.npy',mmap_mode='r',allow_pickle=False)
    schema=json.loads((MATCHED/'schema.json').read_text());columns=schema['context_columns']
    manifest=json.loads((MATCHED/'manifest.json').read_text())
    for name in ('features_context.csv.gz','metadata.csv.gz'):
        if sha(MATCHED/name)!=manifest['files'][name]:raise ValueError('Frozen matched table changed: '+name)
    meta=list(reader(MATCHED/'metadata.csv.gz'));ids=np.array([r['example_id'] for r in meta])
    rows=np.array([int(r['original_row']) for r in meta])
    if len(set(rows))!=len(rows):raise ValueError('Duplicate original rows')
    table=load_feature_table(MATCHED/'features_context.csv.gz',columns,ids)
    context=np.zeros((len(items),len(columns)+1));context[rows,:-1]=table;context[rows,-1]=1
    family=np.array(['unmapped-'+str(i) for i in range(len(items))],dtype=object)
    family[rows]=[r['source_family_id'] for r in meta]
    return items,features,context,family,columns+['context_available']

def item_times(features):
    return np.asarray(features[:,:,2]).mean(axis=1)

def dependencies(items):
    """Per-project (victim_index, polluter_index) pairs rebuilt from read-only SQLite."""
    subjects=json.loads((ROOT/'cannier-replication/subjects.json').read_text());out=[];offset=0
    for pid,repo in enumerate(subjects):
        slug=repo.split('/')[-1]
        con=sqlite3.connect((AUTHORS/'output/volume'/(slug+'.sqlite3')).resolve().as_uri()+'?mode=ro',uri=True)
        ids=[r[0] for r in con.execute('select id from item where n_runs_features=30 and n_runs_baseline=2500 and n_runs_shuffle=2500')]
        index={k:i for i,k in enumerate(ids)}
        pairs=np.array([(index[v],index[p]) for v,p in con.execute('select victim_id,polluter_id from dependency')],dtype=int).reshape(-1,2)
        con.close()
        if not (items[offset:offset+len(ids),0]==pid).all():raise ValueError('Project rows misaligned: '+slug)
        if len(pairs) and not items[offset+pairs[:,1],6].all():raise ValueError('Polluter labels disagree with dependency table')
        out.append(pairs);offset+=len(ids)
    if offset!=len(items):raise ValueError('Dependency rows misaligned')
    return out

# ---------------------------------------------------------------- training

def task_view(items,task):
    domain,label,_,_=TASKS[task]
    mask=np.ones(len(items),bool) if domain is None else items[:,domain].astype(bool)
    return mask,items[mask,label].astype(bool)

def repeat_seed(task,repeat):
    return SEED+1000*list(TASKS).index(task)+repeat

def run(analysis,task,first,last):
    """Fit both arms for repeats [first,last), sharing draw, split and seeds per repeat."""
    if not (OUT/'protocol.json').exists():raise ValueError('Freeze the protocol first')
    items,features,context,family,_=load_data();mask,y=task_view(items,task)
    if analysis=='mapped_only':
        keep=context[:,-1]==1;sub=keep[mask];ctx=context[:,:-1]
    else:
        sub=np.ones(mask.sum(),bool);ctx=context
    y=y[sub];rows=np.flatnonzero(mask)[sub];_,_,cls,trees=TASKS[task]
    root=LOCAL/'preds'/analysis;root.mkdir(parents=True,exist_ok=True)
    for repeat in range(first,last):
        target={arm:root/f'{task}_{arm}_r{repeat:02d}.npy' for arm in ARMS}
        if all(p.exists() for p in target.values()):continue
        seed=repeat_seed(task,repeat);rng=np.random.default_rng(seed)
        choice=int(rng.choice(N_MEASUREMENTS,1,replace=False)[0])
        base=np.asarray(features[rows,choice,:],dtype=float)
        xs={'baseline':base,'context':np.hstack((base,ctx[rows]))}
        if analysis=='family_grouped':
            splits=list(StratifiedGroupKFold(n_splits=10,shuffle=True,random_state=seed).split(base,y,family[rows]))
        else:
            splits=list(StratifiedKFold(n_splits=10,shuffle=True,random_state=seed).split(base,y))
        fold=np.full(len(y),-1)
        for k,(_,test) in enumerate(splits):fold[test]=k
        np.savez_compressed(root/f'{task}_r{repeat:02d}_split.npz',fold=fold,choice=choice,rows=rows)
        start=time.perf_counter()
        for arm in ARMS:
            pred=np.full(len(y),np.nan)
            for k,(train,test) in enumerate(splits):
                xt,yt=SMOTE(random_state=seed+k).fit_resample(xs[arm][train],y[train])
                model=cls(n_estimators=trees,random_state=seed+k,n_jobs=-1).fit(xt,yt)
                pred[test]=model.predict_proba(xs[arm][test])[:,list(model.classes_).index(True)]
                del model,xt,yt;gc.collect()  # fully grown forests are large; free before the next fit
            if not np.isfinite(pred).all():raise ValueError('Missing out-of-fold predictions')
            np.save(target[arm],pred)
        print(f'{analysis} {task} repeat {repeat} done in {time.perf_counter()-start:.0f}s',flush=True)

# ---------------------------------------------------------------- metrics

def abs_mcc(tn,fn,fp,tp):
    """Authors' get_mcc (absolute value; NaN when undefined)."""
    tn,fn,fp,tp=[np.asarray(v,dtype=float) for v in (tn,fn,fp,tp)]
    with np.errstate(all='ignore'):
        return np.abs((tp*tn-fp*fn)/np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)))

def signed_mcc(tn,fn,fp,tp):
    tn,fn,fp,tp=[np.asarray(v,dtype=float) for v in (tn,fn,fp,tp)]
    d=np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    with np.errstate(all='ignore'):
        return np.where(d>0,(tp*tn-fp*fn)/np.where(d>0,d,1),0.0)

def confusion(y,pred,threshold=.5):
    p=pred>=threshold
    return np.array([(~p&~y).sum(),(~p&y).sum(),(p&~y).sum(),(p&y).sum()],dtype=float)

def load_preds(analysis,task,arm,repeats):
    root=LOCAL/'preds'/analysis
    return np.stack([np.load(root/f'{task}_{arm}_r{r:02d}.npy') for r in range(repeats)])

# ---------------------------------------------------------------- cost simulation

THRESH=.01*np.arange(102)

def bins(pred):
    """Number of grid thresholds t_k (k=0..101) with t_k <= pred: pred >= .01*k  <=>  k < bins."""
    return np.searchsorted(THRESH,pred,side='right')

def simple_front_points(labels,preds,item_costs,fixed_cost):
    """Authors' SingleModelTechnique over thresh_l<=thresh_u grid at one n_F, every repeat averaged."""
    kl,ku=np.triu_indices(102)
    keep=(kl<=100)&~((kl==0)&(ku==101));kl,ku=kl[keep],ku[keep]  # (0,1.01) is only the no-model point
    perf=np.zeros(len(kl));cost=np.zeros(len(kl))
    for pred in preds:
        b=bins(pred)
        pos=np.bincount(b[labels],minlength=103).astype(float);neg=np.bincount(b[~labels],minlength=103).astype(float)
        cst=np.bincount(b,weights=item_costs,minlength=103)
        cpos,cneg,ccst=np.cumsum(pos),np.cumsum(neg),np.cumsum(cst)  # counts with bins<=k
        tn=cneg[ku];fp=neg.sum()-cneg[ku];fn=cpos[kl];tp=pos.sum()-cpos[kl]
        perf+=abs_mcc(tn,fn,fp,tp);cost+=ccst[ku]-ccst[kl]
    perf/=len(preds);cost=cost/len(preds)+fixed_cost
    pts=np.c_[perf,cost,.01*kl,.01*ku,np.ones(len(kl))]
    pts=np.r_[pts,[[1,item_costs.sum(),0,1.01,0]]]
    return pts[np.isfinite(pts[:,0])]

def pairwise_front_points(proj,times,deps,preds_v,preds_p,fixed_cost,n_proj):
    """Authors' Pairwise technique over the 101x101 grid at one n_F (repeat pairs from default_rng(0))."""
    total=sum(len(d) for d in deps);counts=np.zeros((101,101));cost=np.zeros((101,101))
    offsets=np.r_[0,np.cumsum(np.bincount(proj,minlength=n_proj))]
    pairs=rng_pairs()
    for i,j in pairs:
        bv,bp=bins(preds_v[i]),bins(preds_p[j])
        for pid,d in enumerate(deps):
            if len(d):
                h=np.zeros((103,103));np.add.at(h,(bv[offsets[pid]+d[:,0]],bp[offsets[pid]+d[:,1]]),1)
                counts+=h[::-1,::-1].cumsum(0).cumsum(1)[::-1,::-1][1:102,1:102]
        nv=np.zeros((n_proj,103));np.add.at(nv,(proj,bv),1);np_=np.zeros((n_proj,103));np.add.at(np_,(proj,bp),1)
        tv=np.zeros((n_proj,103));np.add.at(tv,(proj,bv),times);tp=np.zeros((n_proj,103));np.add.at(tp,(proj,bp),times)
        ge=lambda a:a[:,::-1].cumsum(1)[:,::-1][:,1:102]  # mass with bins>k, i.e. pred >= .01*k
        cost+=ge(np_).T@ge(tv)+ge(tp).T@ge(nv)  # indexed [k_p,k_v]; transposed below
    counts/=len(pairs);cost=cost.T/len(pairs)+fixed_cost
    kv,kp=np.meshgrid(np.arange(101),np.arange(101),indexing='ij')
    pts=np.c_[(counts/total).ravel(),cost.ravel(),.01*kv.ravel(),.01*kp.ravel(),np.ones(kv.size)]
    keep=~((kv.ravel()==0)&(kp.ravel()==0))
    return pts[keep]

def rng_pairs():
    return np.random.default_rng(seed=0).choice(N_MEASUREMENTS,(N_MEASUREMENTS,2))

def pareto(points):
    """Nondominated points maximizing perf and minimizing cost (authors' make_points)."""
    _,unique=np.unique(points[:,:2],axis=0,return_index=True);points=points[np.sort(unique)]
    order=np.lexsort((-points[:,0],points[:,1]));points=points[order]
    best=-np.inf;keep=[]
    for i,(perf,_) in enumerate(points[:,:2]):
        if perf>best:keep.append(i);best=perf
    front=points[keep];return front[front[:,0].argsort()]

def knee(points):
    """Authors' get_knee_point."""
    s=points[:,:2].copy();s-=s.min(axis=0);s/=s.max(axis=0);s-=np.array([1,0])
    return points[np.linalg.norm(s,axis=1).argmin()]

def cost_inputs(items,features):
    times=item_times(features);proj=items[:,0];n_proj=int(proj.max())+1
    project_times=np.bincount(proj,weights=times,minlength=n_proj)
    nod=items[:,3].astype(bool);p_fail=items[nod,1]/N_RERUNS
    a=p_fail**(N_RERUNS+1)-(p_fail-1)*(1-p_fail)**N_RERUNS-p_fail**2+p_fail-1;b=(p_fail-1)*p_fail
    rerun=times.copy();rerun[nod]*=a/b;rerun[~nod]*=N_RERUNS
    dom=items[:,5].astype(bool);idf=project_times[proj[dom]]*(1+.2*(items[dom,2]-1))
    return dict(times=times,proj=proj,n_proj=n_proj,project_times=project_times,rerun=rerun,idflakies=idf,domain=dom)

def technique_fronts(items,c,deps,preds):
    """preds: dict task -> (repeats, domain) array at n_F=1."""
    fixed=c['project_times'].sum();out={}
    out['Rerun']=pareto(simple_front_points(items[:,3].astype(bool),preds['NOD-vs-Rest'],c['rerun'],fixed))
    out['iDFlakies']=pareto(simple_front_points(items[c['domain'],3].astype(bool),preds['NOD-vs-Victim'],c['idflakies'],fixed))
    pw=pairwise_front_points(c['proj'],c['times'],deps,preds['Victim-vs-Rest'],preds['Polluter-vs-Rest'],fixed,c['n_proj'])
    full=np.array([[1,(2*np.bincount(c['proj'],minlength=c['n_proj'])*c['project_times']).sum(),0,0,0]])
    out['Pairwise']=pareto(np.r_[pw,full])
    return out

def check_cost():
    """Our simulator on the authors' n_F=1 predictions must reproduce their released n_F=1 front points."""
    import zipfile,io
    items=np.load(AUTHORS/'output/items.npy');features=np.load(AUTHORS/'output/features.npy',mmap_mode='r')
    c=cost_inputs(items,features);deps=dependencies(items)
    if sum(len(d) for d in deps)!=194457:raise ValueError('Dependency pair total differs from authors table (194457)')
    preds={t:np.load(AUTHORS/'output/preds'/(AUTHOR_PREDS[t]+'_1.npy')) for t in TASKS}
    fronts=technique_fronts(items,c,deps,preds);z=zipfile.ZipFile(AUTHORS/'authors-output.zip');report={}
    for name,front in fronts.items():
        released=np.load(io.BytesIO(z.read(f'output/points/{name}.npy')))
        wanted=released[released[:,4]<=1]
        matched=[bool(np.any(np.all(np.isclose(front[:,:2],w[:2],rtol=1e-6,atol=0),axis=1))) for w in wanted]
        report[name]=dict(released_points_nF_le_1=len(wanted),reproduced=int(sum(matched)),front_points=len(front))
        print(name,report[name],flush=True)
    ok=all(v['reproduced']==v['released_points_nF_le_1'] for v in report.values())
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'cost_simulator_check.json').write_text(json.dumps(dict(passed=ok,techniques=report,dependency_pairs=194457),indent=2)+'\n')
    if not ok:raise SystemExit('Cost simulator does not reproduce released points')

# ---------------------------------------------------------------- freeze and evaluate

def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'protocol.json').exists():raise ValueError('Do not overwrite the frozen protocol')
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    protocol=dict(created_utc=datetime.now(timezone.utc).isoformat(),git_head=head,protocol_markdown_sha256=sha(OUT/'PROTOCOL.md'),
        base_paper='doi:10.1007/s10664-023-10307-w',authors_archive_sha256='07d714a7e0f57863070d1ba6631191aa6e856fac1ad3ffc92765d6c1fc56f9f1',
        context_table_sha256=sha(MATCHED/'features_context.csv.gz'),metadata_sha256=sha(MATCHED/'metadata.csv.gz'),
        tasks={k:dict(domain_column=v[0],label_column=v[1],classifier=v[2].__name__,n_estimators=v[3],sampling='SMOTE') for k,v in TASKS.items()},
        analyses=ANALYSES,arms=list(ARMS),seed=SEED,n_feature_samples=1,folds=10,rule=RULE,
        software=dict(sklearn=sklearn.__version__,imbalanced_learn=imblearn.__version__,numpy=np.__version__))
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n');print('Protocol frozen:',sha(OUT/'protocol.json'))

def paired_interval(d):
    m=d.mean();h=stats.t.ppf(.975,len(d)-1)*d.std(ddof=1)/np.sqrt(len(d));return m,m-h,m+h

def evaluate():
    protocol=json.loads((OUT/'protocol.json').read_text())
    if sha(OUT/'PROTOCOL.md')!=protocol['protocol_markdown_sha256']:raise ValueError('PROTOCOL.md changed after freezing')
    items,features,context,_,_=load_data();proj=items[:,0];n_proj=int(proj.max())+1
    summary=[];by_repeat=[];by_project=[];verdict={}
    for analysis,repeats in ANALYSES.items():
        for task in TASKS:
            mask,y=task_view(items,task);p=proj[mask]
            if analysis=='mapped_only':keep=context[mask,-1]==1;y,p=y[keep],p[keep]
            try:preds={arm:load_preds(analysis,task,arm,repeats) for arm in ARMS}
            except FileNotFoundError:continue
            cm={arm:np.stack([confusion(y,r) for r in preds[arm]]) for arm in ARMS}
            pc={arm:np.stack([[confusion(y[p==j],r[p==j]) for j in range(n_proj)] for r in preds[arm]]) for arm in ARMS}
            row=dict(analysis=analysis,task=task,cases=len(y),positives=int(y.sum()),repeats=repeats)
            for arm in ARMS:
                a=abs_mcc(*cm[arm].T);s=signed_mcc(*cm[arm].T);tn,fn,fp,tp=cm[arm].T
                ap=np.array([average_precision_score(y,r) for r in preds[arm]])
                with np.errstate(all='ignore'):prec=tp/(tp+fp);rec=tp/(tp+fn);f1=2*tp/(2*tp+fp+fn)
                row.update({f'{arm}_abs_mcc':a.mean(),f'{arm}_signed_mcc':s.mean(),f'{arm}_ap':ap.mean(),f'{arm}_precision':np.nanmean(prec),f'{arm}_recall':rec.mean(),f'{arm}_f1':f1.mean()})
                for r in range(repeats):by_repeat.append(dict(analysis=analysis,task=task,arm=arm,repeat=r,abs_mcc=a[r],signed_mcc=s[r],ap=ap[r],tn=tn[r],fn=fn[r],fp=fp[r],tp=tp[r]))
                if analysis=='primary':
                    mean_counts=pc[arm].mean(axis=0)
                    for j in range(n_proj):
                        by_project.append(dict(task=task,arm=arm,project_id=j,tn=mean_counts[j,0],fn=mean_counts[j,1],fp=mean_counts[j,2],tp=mean_counts[j,3],abs_mcc=np.nanmean(abs_mcc(*pc[arm][:,j].T))))
            d=abs_mcc(*cm['context'].T)-abs_mcc(*cm['baseline'].T);m,lo,hi=paired_interval(d)
            rng=np.random.default_rng(SEED);w=rng.multinomial(n_proj,np.full(n_proj,1/n_proj),size=RULE['bootstrap']).astype(float)
            boot=np.nanmean(abs_mcc(*np.einsum('bp,rpk->brk',w,pc['context']).transpose(2,0,1)),axis=1)-np.nanmean(abs_mcc(*np.einsum('bp,rpk->brk',w,pc['baseline']).transpose(2,0,1)),axis=1)
            blo,bhi=np.nanpercentile(boot,[2.5,97.5])
            row.update(delta_abs_mcc=m,delta_t_lo=lo,delta_t_hi=hi,delta_project_boot_lo=blo,delta_project_boot_hi=bhi,
                       reproduction_gap=row['baseline_abs_mcc']-RULE['reference_abs_mcc'][task])
            summary.append(row)
            if analysis=='primary':
                reproduced=abs(row['reproduction_gap'])<=RULE['reproduction_tolerance']
                improved=reproduced and m>=RULE['min_gain'] and lo>0
                degraded=m<=RULE['degrade'] and hi<0
                verdict[task]=dict(reproduced=bool(reproduced),improved=bool(improved),degraded=bool(degraded),strong=bool(improved and blo>0))
    write_csv(OUT/'metrics_summary.csv',summary,list(summary[0]))
    write_csv(OUT/'metrics_by_repeat.csv',by_repeat,list(by_repeat[0]))
    write_csv(OUT/'metrics_by_project_primary.csv',by_project,list(by_project[0]))
    claim=None
    if len(verdict)==4:
        improved=[t for t,v in verdict.items() if v['improved']]
        met=len(improved)>=2 and any(t in improved for t in ('NOD-vs-Rest','Victim-vs-Rest')) and not any(v['degraded'] for v in verdict.values())
        claim=dict(rule_met=bool(met),improved_tasks=improved,strength='strong' if met and all(verdict[t]['strong'] for t in improved) else ('supported within CANNIER protocol only' if met else 'not met'))
    cost=evaluate_cost(items,features) if len(verdict)==4 else None
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(OUT/'protocol.json'),implementation_sha256=sha(ROOT/'scripts/cannier_protocol.py'),
                per_task=verdict,classification_claim=claim,cost=cost)
    (OUT/'results.json').write_text(json.dumps(result,indent=2,default=float)+'\n');print(json.dumps(result,indent=2,default=float))

def evaluate_cost(items,features):
    c=cost_inputs(items,features);deps=dependencies(items);fronts={}
    for arm in ARMS:
        fronts[arm]=technique_fronts(items,c,deps,{t:load_preds('primary',t,arm,ANALYSES['primary']) for t in TASKS})
    out={}
    for name in fronts['baseline']:
        base,ctx=fronts['baseline'][name],fronts['context'][name];kb,kc=knee(base),knee(ctx)
        for arm,f in (('baseline',base),('context',ctx)):
            write_csv(OUT/f'front_{name}_{arm}.csv',[dict(perf=a,cost=b,thresh_1=t1,thresh_2=t2,n_f=n) for a,b,t1,t2,n in f],['perf','cost','thresh_1','thresh_2','n_f'])
        reach=ctx[ctx[:,0]>=kb[0]];matched=float(reach[:,1].min()) if len(reach) else None
        out[name]=dict(baseline_knee=dict(perf=kb[0],cost=kb[1],params=kb[2:].tolist()),context_knee=dict(perf=kc[0],cost=kc[1],params=kc[2:].tolist()),
                       context_cost_at_baseline_knee_perf=matched,relative_saving=None if matched is None else 1-matched/kb[1])
    savings=[v['relative_saving'] for v in out.values()]
    out['rule_met']=bool(any(s is not None and s>=RULE['cost_saving'] for s in savings) and not any(s is None or s<=-RULE['cost_saving'] for s in savings))
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','check-cost','run','evaluate'])
    p.add_argument('--analysis',choices=list(ANALYSES),default='primary');p.add_argument('--task',choices=list(TASKS))
    p.add_argument('--first',type=int,default=0);p.add_argument('--last',type=int)
    a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='check-cost':check_cost()
    elif a.action=='evaluate':evaluate()
    else:run(a.analysis,a.task,a.first,a.last if a.last is not None else ANALYSES[a.analysis])
