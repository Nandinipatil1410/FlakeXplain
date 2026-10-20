"""v0.8: label-blind features for every frozen candidate (PROTOCOL section 6).

- B  (MDFlaker factors, reimplemented): flaky_frequency, traceback_coverage, test_smells, previous_state, test_size
- F  (v0.7 failure evidence, without has_own_traceback): co-failures, job duration, diff and traceback relations
- C  (66 static context features + context_available) from scripts/confirmation_features.py::extract

Sources: candidates.csv, the original CI job logs, local git clones (tested tree = push head, or
`git merge-tree` of the PR head into its base) and run metadata from the GitHub API. Re-run outcomes
and labels are never read.
"""
import csv,gzip,json,os,re,subprocess,sys,hashlib,datetime,shutil
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_probe import STAMP,ANSI,api,parse,read_log
from mdflaker_v08_smells import test_smells,test_size
from dataset_static import SourceIndex
from confirmation_features import extract

ROOT=Path(__file__).resolve().parents[1];V8=ROOT/'local-evidence/mdflaker-fresh-v0.8'
LOGS=V8/'logs';CLONES=V8/'clones';SRC=V8/'sources';OUT=ROOT/'reports/mdflaker-fresh-v0.8'
CAND=OUT/'candidates.csv';SCHEMA=json.loads((ROOT/'dataset/development-v0.2/schema.json').read_text());CONTEXT=SCHEMA['context_columns']
CAP=1000;MAX_PY=1_000_000
B_COLS=['flaky_frequency','traceback_coverage','test_smells','previous_state','test_size']
F_COLS=['build_failed_tests','same_file_cofailures','job_duration_s','pr_build','changed_files','changed_py_files','changed_test_py_files',
    'nonpy_only_change','changed_lines','own_test_file_changed','path_overlap_depth','traceback_frames','frames_in_changed_files',
    'last_frame_in_test_file','frames_outside_repo','min_line_distance_to_change','diff_available']

def clone(repo):return CLONES/(repo.split('/')[1]+'.git')

def git(repo,*a,stdin=None,lazy=False):
    env=dict(os.environ) if lazy else dict(os.environ,GIT_NO_LAZY_FETCH='1')
    r=subprocess.run(['git','-C',str(clone(repo)),'-c','gc.auto=0','-c','maintenance.auto=false',*a],capture_output=True,text=True,
        encoding='utf-8',errors='replace',input=stdin,env=env)
    return r.returncode,r.stdout

def prefetch(repo,oids,chunk=150):
    """Fetch missing blobs by object id in small retried chunks (resilient to dropped connections)."""
    if not oids:return 0
    _,out=git(repo,'cat-file','--batch-check',stdin='\n'.join(oids)+'\n')
    miss=[l.split()[0] for l in out.splitlines() if l.endswith(' missing')]
    for i in range(0,len(miss),chunk):
        for attempt in range(5):
            if git(repo,'-c','fetch.negotiationAlgorithm=noop','fetch','-q','--no-tags','--no-write-fetch-head','--filter=blob:none','origin',*miss[i:i+chunk])[0]==0:break
    return len(miss)

def py_blobs(repo,tree,paths=None):
    _,out=git(repo,'ls-tree','-r',tree,*(['--']+paths if paths else []))
    return [l.split()[2] for l in out.splitlines() if len(l.split())>=4 and l.split()[1]=='blob' and l.endswith('.py')]

def ensure(repo,shas):
    """Fetch commits not yet in the clone (PR heads live only on refs/pull/*), one at a time with retries."""
    _,out=git(repo,'cat-file','--batch-check',stdin='\n'.join(s for s in shas if s)+'\n')
    missing=[l.split()[0] for l in out.splitlines() if l.endswith(' missing')]
    for s in missing:
        for attempt in range(4):
            if git(repo,'fetch','-q','--no-tags','--filter=blob:none','origin',s)[0]==0:break
    return len(missing)

def tested_tree(c):
    """(tree, diff_base) for the code CI tested: push -> head_sha vs its first parent; PR -> merge-tree(base, head) vs base."""
    repo=c['repo']
    if c['checkout']=='pr_merge':
        rc,out=git(repo,'merge-tree','--write-tree',c['merge_base'],c['head_sha'],lazy=True)  # may need a few conflicting blobs
        return (out.split()[0],c['merge_base']) if rc==0 and out.strip() else (None,None)
    rc,out=git(repo,'rev-parse',c['head_sha']+'^{tree}');rc2,par=git(repo,'rev-parse',c['head_sha']+'^')
    return (out.strip() if rc==0 else None,par.strip() if rc2==0 else None)

def export(repo,tree):
    """Write the tree's .py files: blobs prefetched in chunks, then checked out into a scratch work tree."""
    dest=SRC/repo.split('/')[1]/tree
    if (dest/'.complete').exists():return dest
    shutil.rmtree(dest,ignore_errors=True);prefetch(repo,py_blobs(repo,tree))
    dest.mkdir(parents=True,exist_ok=True);idx=dest.parent/(tree+'.index')
    env=dict(os.environ,GIT_INDEX_FILE=str(idx),GIT_NO_LAZY_FETCH='1')
    p=subprocess.run(['git','--git-dir',str(clone(repo)),'--work-tree',str(dest),'-c','core.bare=false','-c','gc.auto=0','checkout',tree,'--',':(glob)**/*.py'],capture_output=True,env=env)
    idx.unlink(missing_ok=True)
    if p.returncode:return None
    for q in dest.rglob('*.py'):
        if q.stat().st_size>MAX_PY:q.unlink()  # generated data tables, as in v0.6 stage 1
    (dest/'.complete').write_text(tree);return dest

def diff(repo,base,tree):
    if not base or not tree:return None
    rc,names=git(repo,'diff','--name-only',base,tree)
    if rc:return None
    files=[f for f in names.splitlines() if f];lines=0;changed_py=[f for f in files if f.endswith('.py')]
    if changed_py:prefetch(repo,py_blobs(repo,base,changed_py)+py_blobs(repo,tree,changed_py))
    for l in git(repo,'diff','--numstat',base,tree,'--','*.py')[1].splitlines():
        a,d,_=l.split('\t',2);lines+=(int(a) if a.isdigit() else 0)+(int(d) if d.isdigit() else 0)
    hunks=defaultdict(list);cur=None
    for l in git(repo,'diff','-U0',base,tree,'--','*.py')[1].splitlines():
        if l.startswith('+++ '):cur=l[6:] if l.startswith('+++ b/') else None
        elif l.startswith('@@') and cur:
            m=re.search(r'\+(\d+)(?:,(\d+))?',l);s,n=int(m.group(1)),int(m.group(2) or 1);hunks[cur].append((s,s+max(n,1)-1))
    return dict(files=files,lines=lines,hunks=hunks)

FRAME_PYTEST=re.compile(r'^(\S+\.py):(\d+): in (\S+)')
FRAME_NATIVE=re.compile(r'File "([^"]+\.py)", line (\d+), in (\S+)')

def log_lines(c):return [ANSI.sub('',STAMP.sub('',l)) for l in read_log(LOGS/c['repo'].replace('/','__')/f"{c['job_id']}.txt").splitlines()]

def traceback_frames(lines,nodeid):
    """Frames of the failing test's report section (`____ name ____`), as (path, line) like MDFlaker's trace_analyzer."""
    name=nodeid.split('::')[-1];frames=[];inside=False
    for l in lines:
        s=l.strip()
        if re.match(r'^_{3,} .+ _{3,}$',s):
            title=s.strip('_ ');inside=title==name or title.endswith('.'+name) or title.endswith('::'+name);continue
        if re.match(r'^={3,}',s):inside=False
        if inside:
            m=FRAME_PYTEST.match(s) or FRAME_NATIVE.search(s)
            if m:frames.append((m.group(1).replace(chr(92),'/'),int(m.group(2))))
    return frames

def norm_frame(path,repo):
    name=repo.split('/')[1]
    if f'/{name}/{name}/' in path:return path.split(f'/{name}/{name}/',1)[1],True
    if 'site-packages' in path or '/lib/python' in path or 'hostedtoolcache' in path or path.startswith(('/usr','/opt')):return path,False
    return path.lstrip('./'),not path.startswith('/')

def depth(a,b):
    a,b=a.split('/')[:-1],b.split('/')[:-1];n=0
    for x,y in zip(a,b):
        if x!=y:break
        n+=1
    return n

def resolve(index,nodeid):
    """Test function for a rootdir-relative node ID: file by path suffix, then Class.method or function (params stripped)."""
    file,_,rest=nodeid.split('[')[0].partition('::');parts=[p for p in rest.split('::') if p]
    cands=[p for p in index.modules if p==file or p.endswith('/'+file)]
    if len(cands)!=1 or not parts:return None,None,None
    path=cands[0];cls='.'.join(parts[:-1]);name=parts[-1]
    found=index.method(path,cls,name) if cls else ([index.functions[(path,name)]] if (path,name) in index.functions else [])
    return (found[0],cls,path) if len(found)==1 else (None,None,None)

def flaky_frequency(history,when):
    """MDFlaker update_flaky_frequency: failures of this test up to `when`; a gap > 8 h starts a new transition."""
    past=sorted(t for t in history if t<=when)
    if not past:return 0.0
    tr=1
    for a,b in zip(past,past[1:]):
        if a+datetime.timedelta(hours=8)<b:tr+=1
    return round(tr/(len(past)+2),2)

def previous_states(cands):
    """MDFlaker previous_state codes (0 passed, 1 failed, 2 none, 3 other): previous run of the same workflow on the same branch."""
    runs={};state={}
    for c in cands:runs.setdefault((c['repo'],c['run_id']),None)
    for (repo,run) in runs:
        r=api(f'https://api.github.com/repos/{repo}/actions/runs/{run}') or {}
        runs[(repo,run)]=(r.get('workflow_id'),r.get('head_branch'),r.get('created_at'))
    groups=defaultdict(list)
    for (repo,run),(wf,br,created) in runs.items():
        if wf and br:groups[(repo,wf,br)].append((created,run))
    for (repo,wf,br),items in groups.items():
        hist=[]
        for page in range(1,4):
            d=api(f'https://api.github.com/repos/{repo}/actions/workflows/{wf}/runs?branch={br}&per_page=100&page={page}') or {}
            hist+=[(x['created_at'],x['id'],x['conclusion']) for x in d.get('workflow_runs',[])]
            if len(d.get('workflow_runs',[]))<100:break
        hist.sort()
        for created,run in items:
            prev=[h for h in hist if h[0]<created and str(h[1])!=str(run)]
            con=prev[-1][2] if prev else None
            state[(repo,run)]=2 if not prev else 0 if con=='success' else 1 if con=='failure' else 3
    return state

def job_durations(cands):
    out={}
    for c in cands:
        if c['job_id'] in out:continue
        j=api(f"https://api.github.com/repos/{c['repo']}/actions/jobs/{c['job_id']}") or {}
        try:out[c['job_id']]=(datetime.datetime.fromisoformat(j['completed_at'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(j['started_at'].replace('Z','+00:00'))).total_seconds()
        except Exception:out[c['job_id']]=0
    return out

def cached(name,fn):
    p=V8/name
    if p.exists():return json.loads(p.read_text())
    v=fn();p.write_text(json.dumps(v));return v

def main():
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')))
    hist=defaultdict(list)
    for d in LOGS.iterdir():
        for t in d.glob('*.txt*'):
            m=json.loads((d/(t.name.split('.')[0]+'.json')).read_text());when=datetime.datetime.fromisoformat(m['created_at'].replace('Z','+00:00'))
            for n in parse(read_log(t)):hist[(d.name,n.split('[')[0].replace(chr(92),'/'))].append(when)
    prev={tuple(k.split('|',1)):v for k,v in cached('previous_states.json',lambda:{f'{a}|{b}':s for (a,b),s in previous_states(cands).items()}).items()}
    dur=cached('job_durations.json',lambda:job_durations(cands))
    for repo in sorted({c['repo'] for c in cands}):
        n=ensure(repo,sorted({c['head_sha'] for c in cands if c['repo']==repo}|{c['merge_base'] for c in cands if c['repo']==repo and c['merge_base']}))
        print('fetched',n,'commits for',repo,flush=True)
    rows=[];idx=(None,None);diff_cache={};ctx_cache={};jobs={}
    order=sorted(range(len(cands)),key=lambda i:(cands[i]['repo'],cands[i]['head_sha'],cands[i]['merge_base']))  # parse each tree once
    for k,i in enumerate(order):
        c=cands[i];repo=c['repo'];row=dict(candidate=i,repo=repo,created_at=c['created_at'],nodeid=c['nodeid'])
        tree,base=tested_tree(c);row['tree_ok']=int(bool(tree))
        lines=jobs.setdefault(c['job_id'],log_lines(c));node=c['nodeid'].split('::',1)[0].replace(chr(92),'/')+('::'+c['nodeid'].split('::',1)[1] if '::' in c['nodeid'] else '')
        fn=cls=path=None;root=None
        if tree:
            root=export(repo,tree)
            if root:
                if idx[0]!=root:
                    if idx[0] is not None:shutil.rmtree(idx[0],ignore_errors=True)  # keep one exported tree on disk at a time
                    idx=(root,SourceIndex(root));ctx_cache={}
                fn,cls,path=resolve(idx[1],node)
        key=(repo,base,tree)
        if key not in diff_cache:diff_cache[key]=diff(repo,base,tree)
        d=diff_cache[key];files=d['files'] if d else [];py=[f for f in files if f.endswith('.py')]
        frames=[(norm_frame(p,repo),ln) for p,ln in traceback_frames(lines,node)]
        test_path=fn.path if fn else '';dist=CAP;cov=0
        for (p,inrepo),ln in frames:
            if not inrepo:continue
            for f,hs in (d['hunks'].items() if d else []):
                if f in p or p in f:
                    for s,e in hs:
                        if s<=ln<=e:cov=1
                        dist=min(dist,0 if s<=ln<=e else min(abs(ln-s),abs(ln-e)))
        when=datetime.datetime.fromisoformat(c['created_at'].replace('Z','+00:00'));src=None;smells=size=0
        if fn:
            text=(root/fn.path).read_text(encoding='utf-8',errors='replace');name=fn.qualname.split('.')[-1]
            smells=test_smells(fn.node);size=test_size(name,text.splitlines(keepends=True))
            ck=(str(root),fn.key,cls,path)
            if ck not in ctx_cache:ctx_cache[ck]=extract(idx[1],fn,cls,path)[1]
            src=ctx_cache[ck]
        row.update(flaky_frequency=flaky_frequency(hist[(repo.replace('/','__'),node.split('[')[0])],when),traceback_coverage=cov,
            test_smells=smells,previous_state=prev.get((repo,c['run_id']),2),test_size=size,source_mapped=int(bool(fn)))
        row.update(build_failed_tests=int(c['job_failed_tests']),same_file_cofailures=0,job_duration_s=dur.get(c['job_id'],0),pr_build=int(c['event']=='pull_request'),
            changed_files=len(files),changed_py_files=len(py),changed_test_py_files=sum('test' in f.lower() for f in py),
            nonpy_only_change=int(d is not None and not py),changed_lines=d['lines'] if d else 0,own_test_file_changed=int(bool(test_path) and test_path in files),
            path_overlap_depth=max((depth(test_path,f) for f in py),default=0) if test_path else 0,traceback_frames=len(frames),
            frames_in_changed_files=sum(1 for (p,inrepo),_ in frames if inrepo and any(f in p or p in f for f in files)),
            last_frame_in_test_file=int(bool(frames) and bool(test_path) and (test_path.endswith(frames[-1][0][0]) or frames[-1][0][0].endswith(test_path))),
            frames_outside_repo=sum(1 for (p,inrepo),_ in frames if not inrepo),min_line_distance_to_change=min(dist,CAP),diff_available=int(d is not None))
        for col in CONTEXT:row[col]=src[col] if src else 0
        row['context_available']=int(bool(src));rows.append(row)
        if k%100==0:print(k,repo,flush=True)
    if idx[0] is not None:shutil.rmtree(idx[0],ignore_errors=True)
    rows.sort(key=lambda r:r['candidate']);byjob=defaultdict(list)
    for c,r in zip(cands,rows):byjob[c['job_id']].append((c,r))
    for job,items in byjob.items():
        for c,r in items:r['same_file_cofailures']=sum(1 for c2,_ in items if c2 is not c and c2['nodeid'].split('::')[0]==c['nodeid'].split('::')[0])
    dest=V8/'features.csv.gz'
    with gzip.open(dest,'wt',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
    summary=dict(rows=len(rows),tree_ok=sum(r['tree_ok'] for r in rows),source_mapped=sum(r['source_mapped'] for r in rows),
        context_available=sum(r['context_available'] for r in rows),diff_available=sum(r['diff_available'] for r in rows),
        with_traceback=sum(r['traceback_frames']>0 for r in rows),by_repo={},sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),b_columns=B_COLS,f_columns=F_COLS,context_columns=len(CONTEXT))
    for r in rows:
        b=summary['by_repo'].setdefault(r['repo'],dict(rows=0,tree_ok=0,source_mapped=0,with_traceback=0))
        b['rows']+=1;b['tree_ok']+=r['tree_ok'];b['source_mapped']+=r['source_mapped'];b['with_traceback']+=r['traceback_frames']>0
    (OUT/'features_summary.json').write_text(json.dumps(summary,indent=1)+'\n');print(json.dumps(summary,indent=1))

if __name__=='__main__':main()
