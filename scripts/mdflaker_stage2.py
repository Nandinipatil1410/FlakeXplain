"""v0.6 stage 2: gate G2 (amendment A1) and comparator selection, using baseline arms only.

No context feature is read here. Upstream code is reimplemented, never imported or executed.
"""
import csv,gzip,json,hashlib
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import matthews_corrcoef,f1_score,precision_score,recall_score,accuracy_score,average_precision_score

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local-evidence/mdflaker-v0.6';UP=LOCAL/'upstream/simpac';OUT=ROOT/'reports/q3q4-base-paper-v0.6'
FACTORS=['Flaky Frequency','Traceback Coverage','Test Smells','Previous State','Test Size']
SEED=20261020;REPEATS=30
POPULATION=('spaCy','django-rest-framework')  # amendment A2

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load():
    rows=list(csv.DictReader(open(UP/'F_Detector/dataset.csv',encoding='utf-8')))
    X=np.array([[float(r[c]) for c in FACTORS] for r in rows]);y=np.array([int(r['Flaky or Not']) for r in rows])
    with gzip.open(LOCAL/'stage1/metadata.csv.gz','rt',encoding='utf-8') as f:meta=list(csv.DictReader(f))
    assert [int(m['row']) for m in meta]==list(range(len(rows)))
    return rows,X,y,meta

def as_int(X):return np.trunc(X).astype(int)  # released read_data casts with dtype=int

def mdf_paper(Xtr,ytr,Xte):
    """Section 2.3: previous state passed -> traceback rule; otherwise KNN(10, p=1), flaky if P > 0.7."""
    knn=KNeighborsClassifier(10,p=1).fit(Xtr,ytr);p=knn.predict_proba(Xte)[:,list(knn.classes_).index(1)]
    rule=Xte[:,3]==0;score=np.where(rule,(Xte[:,1]==0).astype(float),p)
    return np.where(rule,Xte[:,1]==0,p>0.7).astype(int),score

def knn8(Xtr,ytr,Xte):
    knn=KNeighborsClassifier(8,p=1).fit(Xtr,ytr)
    return knn.predict(Xte),knn.predict_proba(Xte)[:,list(knn.classes_).index(1)]

def et(Xtr,ytr,Xte,seed=0):
    m=ExtraTreesClassifier(n_estimators=100,random_state=seed,n_jobs=-1).fit(Xtr,ytr);p=m.predict_proba(Xte)[:,list(m.classes_).index(1)]
    return (p>=0.5).astype(int),p

CANDIDATES={'MDF-paper-int':(mdf_paper,True),'MDF-paper-float':(mdf_paper,False),'KNN8-int':(knn8,True),'KNN8-float':(knn8,False)}

def splits(y,groups,r):
    return list(StratifiedGroupKFold(10,shuffle=True,random_state=SEED+r).split(np.zeros(len(y)),y,groups))

def metrics(y,pred,score=None):
    m=dict(mcc=matthews_corrcoef(y,pred),f1=f1_score(y,pred,zero_division=0),precision=precision_score(y,pred,zero_division=0),
        recall=recall_score(y,pred,zero_division=0),accuracy=accuracy_score(y,pred))
    if score is not None:m['ap']=average_precision_score(y,score)
    return m

def run_arm(fit,X,y,groups,folds_by_repeat):
    out=[]
    for folds in folds_by_repeat:
        pred=np.zeros(len(y),int);score=np.zeros(len(y))
        for tr,te in folds:pred[te],score[te]=fit(X[tr],y[tr],X[te])
        out.append(dict(metrics(y,pred,score),pred=pred))
    return out

def summary(reps):
    s={}
    for k in ('mcc','f1','precision','recall','accuracy','ap'):
        v=np.array([r[k] for r in reps]);h=stats.t.ppf(.975,len(v)-1)*v.std(ddof=1)/np.sqrt(len(v))
        s[k]=dict(mean=v.mean(),ci95=[v.mean()-h,v.mean()+h])
    return s

def g2a(rows,keys,X,y,results,subset):
    Xi=as_int(X);decided=[r for r in results if r['Flaky or Not'] in ('Flaky','Non-Flaky')];joined=[]
    for r in decided:
        ix=[i for i in keys.get((r['Build ID'],r['Test Method']),[]) if subset[i]]
        if len(ix)==1 or (ix and len({tuple(X[i]) for i in ix})==1):joined.append((ix[0],int(r['Flaky or Not']=='Flaky'),r['Detection Method']))
    if not joined:return dict(joined_uniquely=0,passed=False)
    ours,_=mdf_paper(Xi[2:],y[2:],Xi[[j[0] for j in joined]])  # released read_data drops the first two data rows
    rec=np.array([j[1] for j in joined]);agree=float((ours==rec).mean())
    by={m:float(np.mean([ours[k]==rec[k] for k,j in enumerate(joined) if j[2]==m])) for m in sorted({j[2] for j in joined})}
    return dict(joined_uniquely=len(joined),agreement=agree,agreement_by_detection_method=by,threshold=0.90,passed=agree>=0.90)

def g2b(rows,y,results,subset):
    rec={}
    for r in results:rec.setdefault((r['Build ID'],r['Test Method']),set()).add(r['Flaky or Not'])
    cover=[i for i,r in enumerate(rows) if subset[i] and len(rec.get((r['Build ID'],r['Test Case Name']),()))==1]
    dec=[next(iter(rec[(rows[i]['Build ID'],rows[i]['Test Case Name'])])) for i in cover]
    pred=np.array([int(d=='Flaky') for d in dec])
    return dict(rows_with_single_recorded_decision=len(cover),coverage=len(cover)/max(1,int(subset.sum())),
        missing_factor_rows_counted_nonflaky=dec.count('Missing factors'),**metrics(y[cover],pred),note='in-sample for MDFlaker; reference only')

def select(fits,X,Xi,y,groups,mask):
    idx=np.flatnonzero(mask);folds=[splits(y[idx],groups[idx],r) for r in range(REPEATS)];arms={}
    for name,(fit,integer) in fits.items():arms[name]=run_arm(fit,(Xi if integer else X)[idx],y[idx],groups[idx],folds)
    return idx,arms

def main():
    rows,X,y,meta=load();groups=np.array([m['group_id'] for m in meta]);projects=np.array([m['project'] for m in meta])
    pop=np.isin(projects,POPULATION);everyone=np.ones(len(y),bool);mapped=np.array([int(m['mapped']) for m in meta])
    report=dict(stage=2,script_sha256=sha(__file__),stage1_metadata_sha256=sha(LOCAL/'stage1/metadata.csv.gz'),population=list(POPULATION))
    # Gate G1 (amendment A2.2): first point where labels meet the mapping.
    yp,mp=y[pop],mapped[pop]
    g1=dict(rows=int(pop.sum()),mapped=int(mp.sum()),mapped_fraction=float(mp.mean()),mapped_rate_flaky=float(mp[yp==1].mean()),mapped_rate_nonflaky=float(mp[yp==0].mean()),
        by_project={p:dict(rows=int((projects==p).sum()),mapped=int(mapped[projects==p].sum())) for p in sorted(set(projects))})
    g1['rate_gap_pp']=abs(g1['mapped_rate_flaky']-g1['mapped_rate_nonflaky'])*100;g1['passed']=g1['mapped_fraction']>=0.85 and g1['rate_gap_pp']<=10
    report['G1']=g1
    keys=defaultdict(list)
    for i,r in enumerate(rows):keys[(r['Build ID'],r['Test Case Name'])].append(i)
    dup=[v for v in keys.values() if len(v)>1]
    report['duplicates']=dict(keys_with_duplicates=len(dup),extra_rows=sum(len(v)-1 for v in dup),
        label_conflicts=sum(len({y[i] for i in v})>1 for v in dup),factor_conflicts=sum(len({tuple(X[i]) for i in v})>1 for v in dup))
    report['labels']={p:dict(rows=int((projects==p).sum()),flaky=int(y[projects==p].sum())) for p in sorted(set(projects))}
    results=list(csv.DictReader(open(UP/'output/csv/results/Results_2020-11-28_01-39-46.csv',encoding='utf-8')))
    report['G2a']=dict(all_rows=g2a(rows,keys,X,y,results,everyone),primary_population=g2a(rows,keys,X,y,results,pop))
    report['G2a']['passed']=report['G2a']['all_rows']['passed']
    report['G2b_reference_R']=dict(all_rows=g2b(rows,y,results,everyone),primary_population=g2b(rows,y,results,pop))
    Xi=as_int(X)
    idx,arms=select(CANDIDATES,X,Xi,y,groups,pop)
    report['candidates_primary']={n:summary(v) for n,v in arms.items()}
    best=max(arms,key=lambda n:np.mean([r['mcc'] for r in arms[n]]));report['B_star']=best
    pp=projects[idx]
    report['candidates_primary_per_project_mcc']={n:{p:float(np.mean([matthews_corrcoef(y[idx][pp==p],r['pred'][pp==p]) for r in v])) for p in POPULATION} for n,v in arms.items()}
    np.save(LOCAL/'stage2_bstar_predictions.npy',np.array([r['pred'] for r in arms[best]]))
    # S7 (A2.6): baseline-only arms on all 2,151 rows.
    _,s7=select(dict(CANDIDATES,**{'ET-B':(lambda a,b,c:et(a,b,c,SEED),False)}),X,Xi,y,groups,everyone)
    report['S7_all_rows_baseline_only']={n:summary(v) for n,v in s7.items()}
    (OUT/'stage2_summary.json').write_text(json.dumps(report,indent=1,default=float)+'\n')
    print(json.dumps({k:report[k] for k in ('G1','duplicates','G2a','G2b_reference_R','B_star')},indent=1,default=float))
    print({n:round(s['mcc']['mean'],4) for n,s in report['candidates_primary'].items()})

if __name__=='__main__':main()
