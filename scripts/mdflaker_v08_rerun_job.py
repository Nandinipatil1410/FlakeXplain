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

def match(key,nodeids):
    """pytest may print IDs relative to its rootdir (a parent of our workdir): match exact or '/'-suffix."""
    return next((n for n in nodeids if key==n or key.endswith('/'+n)),None)

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
    """Shallowest directory D under the repo such that D/<file> exists for every node ID (rootdir-relative IDs)."""
    files=[n.split('::')[0] for n in nodeids];bases=None
    for f in files:
        k=len(Path(f).parts)
        found={Path(*p.parts[:len(p.parts)-k]) for p in target.rglob(Path(f).name) if p.as_posix().endswith(f)}
        bases=found if bases is None else bases&found
    return min(bases,key=lambda d:len(d.parts)) if bases else target

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
    # Windows job logs can print node IDs with backslashes; normalize the file part (label-blind).
    env['nodeids']=[n.split('::',1)[0].replace(chr(92),'/')+('::'+n.split('::',1)[1] if '::' in n else '') for n in env['nodeids']]
    present=[n for n in env['nodeids'] if any(p.as_posix().endswith(n.split('::')[0]) for p in target.rglob(Path(n.split('::')[0]).name))]
    rec['invalid_nodeids']=[n for n in env['nodeids'] if n not in present];env['nodeids']=present;rec['nodeids']=present
    if not present:rec.update(status='excluded',stage='nodeids',detail='no candidate file in tree');save();return
    cwd=workdir(target,env['nodeids']);rec['workdir']=str(cwd.relative_to(target))
    setup_cwd=cwd if env.get('setup_cwd')=='workdir' else target  # most recipes install from the repository root
    # {first:a|b} -> the first of the listed paths that exists (renamed package directories).
    setup=re.sub(r'\{first:([^}]*)\}',lambda m:next((x for x in m.group(1).split('|') if (setup_cwd/x).exists()),m.group(1).split('|')[0]),env['setup'])
    rec['setup_command']=setup
    rc,log,dt=sh(setup,setup_cwd,SETUP_TIMEOUT);rec['setup_seconds']=round(dt)
    (out/f"{env['env_id']}_setup.log").write_text(log[-20000:],encoding='utf-8')
    if rc!=0:rec.update(status='setup_failed',stage='install',detail=str(rc));save();return
    files=sorted({n.split('::')[0] for n in env['nodeids']})
    deselect=' '.join('--deselect '+quote([n]) for n in env['nodeids'])  # candidates never run in the check
    rc,log,dt=sh(env['test'].replace('{args}',quote(files)+' '+deselect+' '+env['pytest_args']),cwd,ROUND_TIMEOUT*2)
    res=outcomes(log);base={n.split('[')[0] for n in env['nodeids']}
    others={k:v for k,v in res.items() if match(k.split('[')[0],list(base)) is None}
    rec['env_check']=dict(returncode=str(rc),seconds=round(dt),other_tests=len(others),other_passed=sum(v in ('PASSED','XFAIL','SKIPPED') for v in others.values()),
        other_failed=sum(v in ('FAILED','ERROR') for v in others.values()))
    (out/f"{env['env_id']}_envcheck.log").write_text(log[-20000:],encoding='utf-8')
    # Collection check (B3): pytest aborts a whole session if any argument cannot be collected, so
    # candidates are collected (never executed) first; uncollectable ones are excluded, label-blind.
    # Output formats differ (tox/nox wrappers may add -v), so the decision uses only pytest's exit code,
    # its "N collected" count and its not-found/collection errors, never the listing of IDs.
    def collectable(nodeids):
        rc,log,_=sh(env['test'].replace('{args}',quote(nodeids)+' --collect-only -q '+env['pytest_args']),cwd,ROUND_TIMEOUT)
        text=re.sub(r'\x1b\[[0-9;]*m','',log)
        counts=[int(x) for x in re.findall(r'collected (\d+) items?',text)+re.findall(r'(\d+) tests? collected',text)]
        bad=re.search(r'ERROR: (not found|found no collectors)|errors? during collection|\d+ errors? in ',text)
        return str(rc)=='0' and bool(counts) and max(counts)>=len(nodeids) and not bad,log
    good,log=collectable(env['nodeids'])
    ok=set(env['nodeids']) if good else {n for n in env['nodeids'] if collectable([n])[0]}
    rec['not_collectable']=[n for n in env['nodeids'] if n not in ok];env['nodeids']=[n for n in env['nodeids'] if n in ok];rec['nodeids']=env['nodeids']
    (out/f"{env['env_id']}_collect.log").write_text(log[-20000:],encoding='utf-8')
    if not env['nodeids']:rec.update(status='excluded',stage='collect',detail='no candidate collectable');save();return
    if a.check_only:rec['status']='check_only';save();return
    rounds=[]
    for i in range(ROUNDS):
        rc,log,dt=sh(env['test'].replace('{args}',quote(env['nodeids'])+' '+env['pytest_args']),cwd,ROUND_TIMEOUT)
        res={};[res.setdefault(match(k,env['nodeids']),v) for k,v in outcomes(log).items()]
        rounds.append(dict(returncode=str(rc),seconds=round(dt,1),outcomes={n:res.get(n,'MISSING') for n in env['nodeids']}))
        if i==0:(out/f"{env['env_id']}_round0.log").write_text(log[-20000:],encoding='utf-8')
        rec['rounds']=rounds;save()
    rec['status']='done';save()

if __name__=='__main__':main()
