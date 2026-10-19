"""v0.7: label-blind failure-evidence features (PROTOCOL.md section 3) for the spaCy and DRF rows.

Reads the released build histories and the local git clones; labels are never read.
"""
import csv,gzip,json,os,re,subprocess,hashlib
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
V6=ROOT/'local-evidence/mdflaker-v0.6';UP=V6/'upstream/simpac';OUT=ROOT/'reports/failure-evidence-v0.7'
PROJECTS={'spaCy':('spacy.git','explosion/spaCy','spaCy/',['master','develop']),
    'django-rest-framework':('drf.git','encode/django-rest-framework','django-rest-framework/',['main','master'])}
COLUMNS=['build_failed_tests','same_file_cofailures','build_duration_s','pr_build','changed_files','changed_py_files','changed_test_py_files',
    'nonpy_only_change','changed_lines','own_test_file_changed','path_overlap_depth','has_own_traceback','traceback_frames',
    'frames_in_changed_files','last_frame_in_test_file','frames_outside_repo','min_line_distance_to_change','diff_available']
CAP=1000

def git(clone,*args):
    r=subprocess.run(['git','-C',str(V6/'clones'/clone),*args],capture_output=True,text=True,encoding='utf-8',errors='replace')
    return r.returncode,r.stdout

def base_commit(clone,branches,build):
    sha=build['commit_sha'];m=re.search(r'compare/([0-9a-f]+)\.\.\.([0-9a-f]+)',build['failed_info']['compare_url'])
    if m and git(clone,'rev-parse','--verify','-q',m.group(1)+'^{commit}')[0]==0:return git(clone,'rev-parse',m.group(1)+'^{commit}')[1].strip()
    if not m:
        for br in [build.get('branch_name')]+branches:
            rc,mb=git(clone,'merge-base',br,sha);mb=mb.strip()
            if rc==0 and mb and mb!=sha:return mb
    rc,parent=git(clone,'rev-parse',sha+'^');return parent.strip() if rc==0 else None

def diff(clone,base,sha):
    rc,names=git(clone,'diff','--name-only',base,sha)
    if rc!=0:return None
    files=[f for f in names.splitlines() if f]
    rc,num=git(clone,'diff','--numstat',base,sha,'--','*.py');lines=0
    for l in num.splitlines():
        a,d,_=l.split('\t',2);lines+=(int(a) if a.isdigit() else 0)+(int(d) if d.isdigit() else 0)
    rc,u=git(clone,'diff','-U0',base,sha,'--','*.py');hunks=defaultdict(list);cur=None
    for l in u.splitlines():
        if l.startswith('+++ '):cur=l[6:] if l.startswith('+++ b/') else None
        elif l.startswith('@@') and cur:
            m=re.search(r'\+(\d+)(?:,(\d+))?',l);s,n=int(m.group(1)),int(m.group(2) or 1);hunks[cur].append((s,s+max(n,1)-1))
    return dict(files=files,lines=lines,hunks=hunks)

def norm(path,slug,prefix):
    path=path.replace('\\','/')
    marker='/build/'+slug+'/'
    if marker in path:return path.split(marker,1)[1],True
    if path.startswith(prefix):return path[len(prefix):],True
    if path.startswith('/') or 'site-packages' in path or path.startswith('<'):return path,False
    return path,True

def depth(a,b):
    a,b=a.split('/')[:-1],b.split('/')[:-1];n=0
    for x,y in zip(a,b):
        if x!=y:break
        n+=1
    return n

def main():
    meta={}
    with gzip.open(V6/'stage1/metadata.csv.gz','rt',encoding='utf-8') as f:
        for m in csv.DictReader(f):meta[int(m['row'])]=m
    rows=list(csv.DictReader(open(UP/'F_Detector/dataset.csv',encoding='utf-8')))
    hist={p:json.load(open(UP/f'F_Detector/{p}_build_history.json',encoding='utf-8')) for p in PROJECTS}
    diffs={};out=[];notes=defaultdict(int)
    for i,r in enumerate(rows):
        p=meta[i]['project']
        if p not in PROJECTS:continue
        clone,slug,prefix,branches=PROJECTS[p];b=hist[p][r['Build ID']];fi=b['failed_info'];name=r['Test Case Name']
        key=(p,r['Build ID'])
        if key not in diffs:
            base=base_commit(clone,branches,b);diffs[key]=diff(clone,base,b['commit_sha']) if base else None
            notes['diff_ok' if diffs[key] else 'diff_unavailable']+=1
        d=diffs[key]
        own=[t for t in fi['failed_tests'] if t['test_case']==name]
        test_path=meta[i]['source_path'] or (norm(own[0]['test_dir'].rstrip('/')+'/'+own[0]['test_file'],slug,prefix)[0] if len(own)==1 else '')
        test_file=test_path.split('/')[-1] if test_path else (own[0]['test_file'] if len(own)==1 else '')
        same=sum(1 for t in fi['failed_tests'] if t['test_file']==test_file and t['test_case']!=name) if test_file else 0
        v=dict(row=i,build_failed_tests=len(fi['failed_tests']),same_file_cofailures=same,build_duration_s=b.get('duration') or 0,
            pr_build=int('/pull/' in fi['compare_url']),diff_available=int(d is not None))
        files=d['files'] if d else [];py=[f for f in files if f.endswith('.py')]
        v.update(changed_files=len(files),changed_py_files=len(py),changed_test_py_files=sum('test' in f.lower() for f in py),
            nonpy_only_change=int(d is not None and not py),changed_lines=d['lines'] if d else 0,
            own_test_file_changed=int(bool(test_path) and test_path in files),
            path_overlap_depth=max((depth(test_path,f) for f in py),default=0) if test_path else 0)
        tb=(fi.get('traceback') or {}).get(name) or []
        frames=[(norm(fr[0],slug,prefix),int(fr[1]) if str(fr[1]).isdigit() else None) for fr in tb]
        dist=CAP
        for (path,inrepo),line in frames:
            if d and inrepo and line is not None:
                for s,e in d['hunks'].get(path,[]):dist=min(dist,0 if s<=line<=e else min(abs(line-s),abs(line-e)))
        v.update(has_own_traceback=int(bool(tb)),traceback_frames=len(tb),
            frames_in_changed_files=sum(1 for (path,inrepo),_ in frames if inrepo and path in files),
            last_frame_in_test_file=int(bool(frames) and bool(test_path) and frames[-1][0][0]==test_path),
            frames_outside_repo=sum(1 for (path,inrepo),_ in frames if not inrepo),min_line_distance_to_change=min(dist,CAP))
        out.append({k:v[k] for k in ['row']+COLUMNS})
    dest=V6.parent/'failure-evidence-v0.7';dest.mkdir(parents=True,exist_ok=True)
    with gzip.open(dest/'features_failure.csv.gz','wt',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,['row']+COLUMNS);w.writeheader();w.writerows(out)
    summary=dict(rows=len(out),builds=len(diffs),notes=dict(notes),
        coverage={c:sum(1 for o in out if o[c]) for c in COLUMNS},
        sha256=hashlib.sha256((dest/'features_failure.csv.gz').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'features_summary.json').write_text(json.dumps(summary,indent=1)+'\n');print(json.dumps(summary,indent=1))

if __name__=='__main__':main()
