"""Export the derived, shareable v0.8 data into replication/data/ (data release pending guide approval).

Copies or derives, from local-evidence/mdflaker-fresh-v0.8/ and reports/mdflaker-fresh-v0.8/:
  candidates.csv            frozen candidate failures (copy of the committed report file)
  features.csv.gz           label-blind features (copy)
  labels.csv                frozen labels (copy; SHA-256 checked against RESULTS.md)
  previous_states.json      cached GitHub API metadata used by the feature step (copy)
  job_durations.json        cached GitHub API metadata used by the feature step (copy)
  rerun_outcomes.csv        per candidate: rerun environment, environment check and outcome counts over 30 rounds
  failure_history.csv.gz    failed node IDs parsed from every saved CI job log, with run/job metadata
  MANIFEST.json             SHA-256, size and source of every exported file

Never exported: raw CI job logs, rerun setup/check/round logs, git clones, or any token. The token-pattern
scan below aborts the export if a GitHub token shape appears in any output file.

Usage: python replication/export_derived_data.py [--dry-run]
Read-only on its sources; writes only replication/data/. Uses the standard library only.
"""
import csv,gzip,hashlib,io,json,os,re,shutil,sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
V8=ROOT/'local-evidence/mdflaker-fresh-v0.8';REP=ROOT/'reports/mdflaker-fresh-v0.8';DEST=ROOT/'replication/data'
LABELS_SHA=('3d856bde','b4c2')  # RESULTS.md: SHA-256 `3d856bde…b4c2`
RUNS=json.loads((REP/'labels_summary.json').read_text())['runs']  # the six full-mode rerun runs used for labels
MAX_BYTES=20_000_000
TOKEN=re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}')

sys.path.insert(0,str(ROOT/'scripts'))
os.environ.setdefault('GH_TOKEN','unused')  # mdflaker_v08_probe reads GH_TOKEN at import; no API call is made here
from mdflaker_v08_probe import parse,read_log

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def norm(n):return n.split('::',1)[0].replace(chr(92),'/')+('::'+n.split('::',1)[1] if '::' in n else '')

def rerun_rows(cands):
    """One row per (rerun run, environment, candidate), from the e*.json result records only (no logs)."""
    rows=[]
    for run in RUNS:
        for f in sorted((V8/'runs'/run).glob('rerun-*/e*.json')):
            if '_' in f.stem:continue
            r=json.loads(f.read_text(encoding='utf-8'));c=r.get('env_check') or {}
            for i in r['candidates']:
                node=norm(cands[i]['nodeid']);outs=[rd['outcomes'].get(node,'MISSING') for rd in r.get('rounds',[])];n=Counter(outs)
                rows.append(dict(candidate=i,repo=r['repo'],rerun_run_id=run,env_id=r['env_id'],runner=r['runner'],python=r['python'],variant=r['variant'],
                    status=r['status'],stage=r.get('stage',''),env_check_other_tests=c.get('other_tests',''),env_check_other_passed=c.get('other_passed',''),
                    env_check_other_failed=c.get('other_failed',''),nodeid_invalid=int(node in r.get('invalid_nodeids',[])),
                    nodeid_not_collectable=int(node in r.get('not_collectable',[])),rounds=len(outs),
                    **{o.lower():n.get(o,0) for o in ('PASSED','FAILED','ERROR','SKIPPED','XFAIL','XPASS','MISSING')}))
    return sorted(rows,key=lambda x:(x['candidate'],x['rerun_run_id']))

def history_rows():
    """Failed node IDs per saved CI job log (the history behind flaky_frequency and its strict variant)."""
    rows=[]
    for d in sorted((V8/'logs').iterdir()):
        for t in sorted(d.glob('*.txt*'),key=lambda x:int(x.name.split('.')[0])):
            m=json.loads((d/(t.name.split('.')[0]+'.json')).read_text())
            for n in sorted(parse(read_log(t))):
                rows.append(dict(repo=d.name.replace('__','/',1),run_id=m['run_id'],job_id=m['job_id'],workflow=m.get('workflow'),event=m.get('event'),
                    created_at=m['created_at'],nodeid=n))
    return rows

def csv_bytes(rows):
    s=io.StringIO();w=csv.DictWriter(s,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);return s.getvalue().encode('utf-8')

def main():
    dry='--dry-run' in sys.argv
    lab=V8/'labels.csv';h=sha(lab)
    if not (h.startswith(LABELS_SHA[0]) and h.endswith(LABELS_SHA[1])):sys.exit(f'labels.csv SHA-256 {h} does not match RESULTS.md ({LABELS_SHA[0]}…{LABELS_SHA[1]})')
    print('labels.csv SHA-256 matches RESULTS.md:',h)
    cands=list(csv.DictReader(open(REP/'candidates.csv',encoding='utf-8')))
    copies={'candidates.csv':REP/'candidates.csv','features.csv.gz':V8/'features.csv.gz','labels.csv':lab,
        'previous_states.json':V8/'previous_states.json','job_durations.json':V8/'job_durations.json'}
    derived={}
    rr=rerun_rows(cands)
    if rr:derived['rerun_outcomes.csv']=(csv_bytes(rr),'derived from local-evidence/mdflaker-fresh-v0.8/runs/<run>/rerun-*/e*.json for runs '+', '.join(RUNS))
    hist=history_rows()
    derived['failure_history.csv.gz']=(gzip.compress(csv_bytes(hist),mtime=0),'derived: node IDs parsed (mdflaker_v08_probe.parse) from local-evidence/mdflaker-fresh-v0.8/logs/*/*.txt.gz plus their *.json metadata')
    size=sum(p.stat().st_size for p in copies.values())+sum(len(b) for b,_ in derived.values())
    print(f'export size {size:,} bytes ({len(rr)} rerun rows, {len(hist)} history rows)')
    if size>MAX_BYTES:sys.exit(f'export larger than {MAX_BYTES:,} bytes; refusing')
    for name,(b,_) in derived.items():
        if TOKEN.search(gzip.decompress(b) if name.endswith('.gz') else b):sys.exit('token-like string in '+name)
    for name,p in copies.items():
        b=p.read_bytes()
        if TOKEN.search(gzip.decompress(b) if name.endswith('.gz') else b):sys.exit('token-like string in '+name)
    if dry:print('dry run: nothing written');return
    DEST.mkdir(parents=True,exist_ok=True);files={}
    for name,p in copies.items():
        shutil.copyfile(p,DEST/name);files[name]=dict(source=p.relative_to(ROOT).as_posix(),source_sha256=sha(p))
    for name,(b,src) in derived.items():(DEST/name).write_bytes(b);files[name]=dict(source=src)
    for name in files:
        files[name].update(sha256=sha(DEST/name),bytes=(DEST/name).stat().st_size)
        assert 'source_sha256' not in files[name] or files[name]['source_sha256']==files[name]['sha256']
    manifest=dict(study='FlakeXplain v0.8: MDFlaker on fresh GitHub Actions failures',labels_sha256_matches_results_md=True,rerun_runs=RUNS,
        excluded='raw CI job logs, rerun setup/environment-check/round logs, git clones, tokens',files=files)
    (DEST/'MANIFEST.json').write_text(json.dumps(manifest,indent=1)+'\n')
    for name,f in files.items():print(f"{name:24} {f['bytes']:>9,}  {f['sha256']}")

if __name__=='__main__':main()
