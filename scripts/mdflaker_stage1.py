"""v0.6 stage 1: label-blind source join and context extraction for MDFlaker's released rows.

Reads the authors' dataset and build histories as data; never imports or runs upstream code.
Labels are read only after every mapping decision is fixed, to count gate G1 coverage.
"""
import csv,gzip,json,subprocess,tarfile,io,hashlib,sys,os
from collections import Counter,defaultdict
from pathlib import Path
from dataset_static import SourceIndex
from confirmation_features import extract

MAX_PY_BYTES=1_000_000  # larger .py files are generated data tables (spaCy lemmatizer lookups); skipped label-blind
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'local-evidence/mdflaker-v0.6';UP=LOCAL/'upstream/simpac';OUT=ROOT/'reports/q3q4-base-paper-v0.6'
PROJECTS={'spaCy':('dataset_spaCy.csv','spacy.git','spaCy/'),
    'django-rest-framework':('dataset_django_rest_framework.csv','drf.git','django-rest-framework/'),
    'incubator-superset':('dataset_incubator_superset.csv','superset.git','incubator-superset/')}
CONTEXT=json.loads((ROOT/'dataset/development-v0.2/schema.json').read_text())['context_columns']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def export(clone,commit):
    """Write the commit's .py files under sources/<clone>/<commit>; reuse an existing export."""
    dest=LOCAL/'sources'/clone.removesuffix('.git')/commit
    if (dest/'.complete').exists():return dest
    data=subprocess.run(['git','-C',str(LOCAL/'clones'/clone),'archive','--format=tar',commit,'--',':(glob)**/*.py'],capture_output=True,check=True,env=dict(os.environ,**({'GIT_NO_LAZY_FETCH':'1'} if clone=='superset.git' else {}))).stdout
    skipped=[]
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        for m in t.getmembers():
            if m.isfile() and not m.name.startswith(('/','..')) and '/../' not in m.name:
                if m.size>MAX_PY_BYTES:skipped.append(m.name);continue
                p=dest/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(m).read())
    (dest/'.skipped.json').write_text(json.dumps(skipped));(dest/'.complete').write_text(commit);return dest

def relative(path,prefix,index):
    path=path.replace('\\','/').lstrip('/')
    if path.startswith(prefix):path=path[len(prefix):]
    if path in index.modules:return path
    hits=[p for p in index.modules if p.endswith('/'+path)]
    return hits[0] if len(hits)==1 else None

def resolve(index,name,path,cls):
    """Return (function, collection_class, collection_path, how) only when exactly one function matches."""
    if path:
        if cls:found=[(f,cls) for f in index.method(path,cls,name)]
        else:found=[(index.functions[k],k[1].rpartition('.')[0]) for k in index.functions if k[0]==path and k[1].split('.')[-1]==name]
        found={f.key:(f,c) for f,c in found}
        if len(found)==1:
            f,c=next(iter(found.values()));return f,c,path,'path'
        if found:return None,None,None,'ambiguous_in_file'
    found={f.key:(f,k[1].rpartition('.')[0],k[0]) for k,f in index.functions.items() if k[1].split('.')[-1]==name and 'test' in k[0].lower()}
    if len(found)==1:
        f,c,p=next(iter(found.values()));return f,c,p,'unique_name_search'
    return None,None,None,'ambiguous_name' if found else 'unresolved'

def main():
    rows=list(csv.DictReader(open(UP/'F_Detector/dataset.csv',encoding='utf-8')))
    member={}
    for p,(f,_,_) in PROJECTS.items():
        for x in csv.DictReader(open(UP/'F_Detector'/f,encoding='utf-8')):member[(x['Build ID'],x['Test Case Name'])]=p
    hist={p:json.load(open(UP/f'F_Detector/{p}_build_history.json',encoding='utf-8')) for p in PROJECTS}
    paths=defaultdict(set)
    for x in csv.DictReader(open(UP/'output/csv/results/Results_2020-11-28_01-39-46.csv',encoding='utf-8')):paths[(x['Build ID'],x['Test Method'])].add(x['Path'])
    plan=defaultdict(list)
    for i,x in enumerate(rows):
        project=member[(x['Build ID'],x['Test Case Name'])];b=hist[project][x['Build ID']]
        plan[(project,b['commit_sha'])].append((i,x,b))
    meta=[None]*len(rows);ctx=[None]*len(rows);commits_missing=[]
    for (project,commit),items in sorted(plan.items()):
        _,clone,prefix=PROJECTS[project]
        try:root=export(clone,commit)
        except subprocess.CalledProcessError:
            commits_missing.append(dict(project=project,commit=commit));index=None
        else:index=SourceIndex(root)
        cache={}
        for i,x,b in items:
            name=x['Test Case Name'];path=cls=None;source='none'
            if index:
                ft=[t for t in (b.get('failed_info') or {}).get('failed_tests',[]) if t['test_case']==name]
                if len(ft)==1:
                    path=relative(ft[0]['test_dir'].rstrip('/')+'/'+ft[0]['test_file'],prefix,index);source='failed_info'
                    cls=None if ft[0].get('test_class') in (None,'NULL','') else ft[0]['test_class']
                elif len(paths.get((x['Build ID'],name),()))==1:
                    path=relative(next(iter(paths[(x['Build ID'],name)])),prefix,index);source='results_path'
                fn,c,p,how=resolve(index,name,path,cls)
            else:fn,how=None,'commit_unavailable'
            group=f'{project}|{p}|{c}|{name}' if fn else f'{project}|{name}'
            meta[i]=dict(row=i,project=project,build_id=x['Build ID'],commit=commit,test_name=name,location_source=source,
                resolution=how if not fn else how,mapped=int(bool(fn)),source_path=fn.path if fn else '',source_qualname=fn.qualname if fn else '',group_id=group)
            if fn:
                key=(fn.key,c,p)
                if key not in cache:cache[key]=extract(index,fn,c,p)[1]
                ctx[i]=dict(row=i,**{k:cache[key][k] for k in CONTEXT},context_available=1)
            else:ctx[i]=dict(row=i,**{k:0 for k in CONTEXT},context_available=0)
        del index;import gc;gc.collect()
        print(project,commit[:8],len(items),sum(meta[i]['mapped'] for i,_,_ in items),flush=True)
    data=LOCAL/'stage1';data.mkdir(parents=True,exist_ok=True)
    for name,table in [('metadata.csv.gz',meta),('features_context.csv.gz',ctx)]:
        with gzip.open(data/name,'wt',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,list(table[0]));w.writeheader();w.writerows(table)
    g1=None
    if '--gate' in sys.argv:
        # Gate G1: labels are read here for the first time, only to count coverage.
        label=[int(x['Flaky or Not']) for x in rows];mapped=[m['mapped'] for m in meta]
        rate=lambda v:sum(m for m,l in zip(mapped,label) if l==v)/max(1,label.count(v))
        g1=dict(rows=len(rows),mapped=sum(mapped),mapped_fraction=sum(mapped)/len(rows),mapped_rate_flaky=rate(1),mapped_rate_nonflaky=rate(0))
        g1['rate_gap_pp']=abs(g1['mapped_rate_flaky']-g1['mapped_rate_nonflaky'])*100
        g1['passed']=g1['mapped_fraction']>=0.85 and g1['rate_gap_pp']<=10
    summary=dict(gate_G1=g1,commits=len(plan),commits_unavailable=commits_missing,
        resolution=Counter(m['resolution'] for m in meta),location_source=Counter(m['location_source'] for m in meta),
        by_project={p:dict(rows=sum(m['project']==p for m in meta),mapped=sum(m['mapped'] for m in meta if m['project']==p)) for p in PROJECTS},
        distinct_groups=len({m['group_id'] for m in meta}),
        files={n:sha(data/n) for n in ('metadata.csv.gz','features_context.csv.gz')},extractor_sha256=sha(ROOT/'scripts/confirmation_features.py'),script_sha256=sha(__file__))
    (OUT/'stage1_summary.json').write_text(json.dumps(summary,indent=1)+'\n');print(json.dumps(dict(gate_G1=g1,by_project=summary["by_project"],resolution=summary["resolution"]),indent=1))

if __name__=='__main__':main()
