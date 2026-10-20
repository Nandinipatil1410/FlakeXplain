"""v0.8 re-run harness, executed inside one GitHub Actions job (standard library only).

1. Rebuild the tree CI tested: head_sha for pushes; merge_base + `git merge head_sha` for PRs (B1).
2. Run the project's setup command.
3. Environment check (B2): run the candidate tests' files once; record how the *other* tests in
   those files behave. Candidate outcomes are not recorded in this step.
4. Run the candidate node IDs 30 times, recording each node's outcome per round from pytest -rA.
"""
import argparse,json,os,re,shlex,subprocess,sys,time
from pathlib import Path

ROUNDS=30;ROUND_TIMEOUT=900;SETUP_TIMEOUT=2400
OUTCOME=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+?\.py::\S+)')

def sh(cmd,cwd,timeout):
    t=time.time()
    try:
        p=subprocess.run(cmd,cwd=cwd,shell=True,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
            env=dict(os.environ,PY_COLORS='0',NO_COLOR='1',FORCE_COLOR='0',TERM='dumb'))
        return p.returncode,p.stdout+p.stderr,time.time()-t
    except subprocess.TimeoutExpired as e:
        out=(e.stdout or b'').decode('utf-8','replace') if isinstance(e.stdout,bytes) else (e.stdout or '')
        return 'timeout',out,time.time()-t

SUMMARY=re.compile(r'^=+ short test summary info =+$')
END=re.compile(r'^=+ .*(passed|failed|error|skipped|deselected|no tests ran).* in [\d.]+s.* =+$')

def outcomes(text):
    """Outcomes from pytest's final short-summary section only (captured output of inner runs is ignored)."""
    res={};lines=[re.sub(r'\[[0-9;]*m','',l).strip() for l in text.splitlines()];start=None
    for i,l in enumerate(lines):
        if SUMMARY.match(l):start=i
    if start is None:return res
    for l in lines[start+1:]:
        if END.match(l):break
        m=OUTCOME.match(l)
        if m:res[m.group(2).split(' - ')[0]]=m.group(1)
    return res

def quote(nodeids):
    return ' '.join(shlex.quote(n) if os.name!='nt' else '"'+n.replace('"','\\"')+'"' for n in nodeids)

def checkout(env,target):
    url=f"https://github.com/{env['repo']}.git";target.mkdir(parents=True,exist_ok=True)
    steps=['git init -q .',f'git remote add origin {url}',
        f"git fetch -q --filter=blob:none --no-tags origin {env['head_sha']} {env['merge_base']}".strip(),
        'git fetch -q --filter=blob:none --tags origin']  # tag-based versions (setuptools_scm, hatch-vcs) need tags
    if env['merge_base']:
        steps+=[f"git checkout -q {env['merge_base']}",f"git -c user.name=rerun -c user.email=rerun@example.invalid merge -q --no-edit {env['head_sha']}"]
    else:steps+=[f"git checkout -q {env['head_sha']}"]
    for s in steps:
        rc,out,_=sh(s,target,900)
        if rc!=0:return f'{s.split()[1]} failed: {out[-400:]}'
    return ''

def workdir(target,nodeids):
    """Shallowest directory under the repo where the node IDs' files exist (rootdir-relative IDs)."""
    files=[n.split('::')[0] for n in nodeids];cands=[target]+sorted({p.parent for f in files for p in target.rglob(Path(f).name)},key=lambda p:len(p.parts))
    for d in cands:
        if all((d/f).exists() for f in files):return d
    return target

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--batch',required=True);ap.add_argument('--env',required=True);ap.add_argument('--out',required=True);ap.add_argument('--check-only',action='store_true',help='local validation: stop after the environment check')
    a=ap.parse_args();env=next(e for e in json.loads(Path(a.batch).read_text()) if e['env_id']==a.env)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);target=Path('target').resolve()
    rec=dict(env_id=env['env_id'],repo=env['repo'],head_sha=env['head_sha'],merge_base=env['merge_base'],runner=env['runner'],python=env['python'],
        variant=env['variant'],candidates=env['candidates'],nodeids=env['nodeids'],python_actual=sys.version,status='started')
    save=lambda:(out/f"{env['env_id']}.json").write_text(json.dumps(rec,indent=1))
    err=checkout(env,target)
    if err:rec.update(status='setup_failed',stage='checkout',detail=err);save();return
    # Node IDs whose file is absent from the tested tree are log-parsing artifacts (e.g. nested pytester
    # output); they are excluded objectively, before any outcome is seen.
    present=[n for n in env['nodeids'] if any(p.as_posix().endswith(n.split('::')[0]) for p in target.rglob(Path(n.split('::')[0]).name))]
    rec['invalid_nodeids']=[n for n in env['nodeids'] if n not in present];env['nodeids']=present;rec['nodeids']=present
    if not present:rec.update(status='excluded',stage='nodeids',detail='no candidate file in tree');save();return
    cwd=workdir(target,env['nodeids']);rec['workdir']=str(cwd.relative_to(target))
    rc,log,dt=sh(env['setup'],cwd,SETUP_TIMEOUT);rec['setup_seconds']=round(dt)
    (out/f"{env['env_id']}_setup.log").write_text(log[-20000:],encoding='utf-8')
    if rc!=0:rec.update(status='setup_failed',stage='install',detail=str(rc));save();return
    files=sorted({n.split('::')[0] for n in env['nodeids']})
    deselect=' '.join('--deselect '+quote([n]) for n in env['nodeids'])  # candidates never run in the check
    rc,log,dt=sh(env['test'].replace('{args}',quote(files)+' '+deselect+' '+env['pytest_args']),cwd,ROUND_TIMEOUT*2)
    res=outcomes(log);others={k:v for k,v in res.items() if k.split('[')[0] not in {n.split('[')[0] for n in env['nodeids']} and k not in env['nodeids']}
    rec['env_check']=dict(returncode=str(rc),seconds=round(dt),other_tests=len(others),other_passed=sum(v in ('PASSED','XFAIL','SKIPPED') for v in others.values()),
        other_failed=sum(v in ('FAILED','ERROR') for v in others.values()))
    (out/f"{env['env_id']}_envcheck.log").write_text(log[-20000:],encoding='utf-8')
    if a.check_only:rec['status']='check_only';save();return
    rounds=[]
    for i in range(ROUNDS):
        rc,log,dt=sh(env['test'].replace('{args}',quote(env['nodeids'])+' '+env['pytest_args']),cwd,ROUND_TIMEOUT)
        res=outcomes(log);rounds.append(dict(returncode=str(rc),seconds=round(dt,1),outcomes={n:res.get(n,'MISSING') for n in env['nodeids']}))
        if i==0:(out/f"{env['env_id']}_round0.log").write_text(log[-20000:],encoding='utf-8')
        rec['rounds']=rounds;save()
    rec['status']='done';save()

if __name__=='__main__':main()
