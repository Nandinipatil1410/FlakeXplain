"""v0.8: group the frozen candidates into re-run environments and attach each one's recipe.

Label-blind: uses candidates.csv and the original job logs only. Writes rerun/v0.8/plan.json and
rerun/v0.8/batch_NN.json (at most 200 environments each, the GitHub matrix limit is 256).
"""
import csv,json,re,sys
from collections import OrderedDict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_probe import STAMP,ANSI

ROOT=Path(__file__).resolve().parents[1];LOGS=ROOT/'local-evidence/mdflaker-fresh-v0.8/logs'
CAND=ROOT/'reports/mdflaker-fresh-v0.8/candidates.csv';DEST=ROOT/'rerun/v0.8';BATCH=200
PYTEST_ARGS='-rA -p no:randomly -p no:cacheprovider'

def log_lines(repo,job):
    t=LOGS/repo.replace('/','__')/f'{job}.txt'
    return [ANSI.sub('',STAMP.sub('',l)) for l in t.read_text(encoding='utf-8',errors='replace').splitlines()]

def runner(image):
    if image.startswith('ubuntu-22.04'):return 'ubuntu-22.04'
    if image.startswith('ubuntu'):return 'ubuntu-24.04'
    if image.startswith('windows'):return 'windows-2025' if '2025' in image else 'windows-2022'
    if image.startswith('macos'):return 'macos-15' if 'macos-15' in image else 'macos-latest'
    return ''

def python_spec(c,variant):
    minor='.'.join(c['python'].split('.')[:2]);name=(c['job_name']+' '+variant).lower()
    if 'pypy' in name:return 'pypy'+minor
    if re.search(r'3\.\d+t\b',name) or 'freethread' in name:return minor+'t'
    return minor

def recipe(c,lines):
    """(variant, setup command, test command template). {args} is replaced by node IDs plus PYTEST_ARGS."""
    repo=c['repo']
    if repo=='encode/django-rest-framework':
        fail=next((m.group(1) for l in lines for m in [re.match(r'^(py\d+-[\w.-]+): (?:FAIL|exit [1-9])',l)] if m),None)
        env=fail or 'py'+c['python'].replace('.','')[:3]
        return env,'python -m pip install tox',f'tox run -e {env} -- {{args}}'
    if repo=='urllib3/urllib3':
        s=next((l.split('NOX_SESSION:',1)[1].strip() for l in lines if 'NOX_SESSION:' in l),'test-'+'.'.join(c['python'].split('.')[:2]))
        return s,'python -m pip install nox',f'nox -s {s} --reuse-existing-virtualenvs -- {{args}}'
    if repo=='pytest-dev/pytest':
        env=next((m.group(1) for l in lines for m in [re.search(r'tox run -e (\S+)',l)] if m),'py')
        return env,'python -m pip install tox',f'tox run -e {env} -- {{args}}'
    if repo=='pypa/setuptools':
        return 'py','python -m pip install tox','tox -e py -- {args}'
    if repo=='HypothesisWorks/hypothesis':
        return 'pytest','python -m pip install -r requirements/test.txt -e .','python -m pytest {args}'
    if repo=='quantumlib/Cirq':
        return 'pytest','python -m pip install -r dev_tools/requirements/dev.env.txt','python -m pytest {args}'
    if repo=='conan-io/conan':
        return 'pytest','python -m pip install -r conans/requirements.txt -r conans/requirements_server.txt -r conans/requirements_dev.txt','python -m pytest {args}'
    if repo=='PrefectHQ/prefect':
        return 'uv','python -m pip install uv && uv sync','uv run pytest {args}'
    raise ValueError(repo)

def unsupported(c):
    if c['rootdir'].startswith('/cygdrive'):return 'cygwin environment'
    if not runner(c['image']):return 'unknown runner image'
    return ''

def main():
    rows=list(csv.DictReader(open(CAND,encoding='utf-8')));envs=OrderedDict();excluded=[]
    for i,c in enumerate(rows):
        why=unsupported(c)
        if why:excluded.append(dict(candidate=i,repo=c['repo'],nodeid=c['nodeid'],reason=why));continue
        variant,setup,test=recipe(c,log_lines(c['repo'],c['job_id']))
        sha=c['head_sha'];base=c['merge_base'] if c['checkout']=='pr_merge' else ''
        key=(c['repo'],sha,base,runner(c['image']),python_spec(c,variant),variant)
        e=envs.setdefault(key,dict(repo=c['repo'],head_sha=sha,merge_base=base,runner=key[3],python=key[4],variant=variant,
            setup=setup,test=test,pytest_args=PYTEST_ARGS,setup_cwd='workdir' if c['repo']=='PrefectHQ/prefect' else 'root',candidates=[],nodeids=[]))
        e['candidates'].append(i)
        if c['nodeid'] not in e['nodeids']:e['nodeids'].append(c['nodeid'])
    items=list(envs.values())
    for n,e in enumerate(items):e['env_id']=f'e{n:04d}'
    DEST.mkdir(parents=True,exist_ok=True)
    batches=[items[i:i+BATCH] for i in range(0,len(items),BATCH)]
    for b,chunk in enumerate(batches):(DEST/f'batch_{b:02d}.json').write_text(json.dumps(chunk,indent=1)+'\n')
    by={}
    for e in items:by.setdefault(e['repo'],[0,0]);by[e['repo']][0]+=1;by[e['repo']][1]+=len(e['candidates'])
    plan=dict(environments=len(items),candidates_planned=sum(len(e['candidates']) for e in items),excluded=excluded,batches=len(batches),
        by_repo={k:dict(environments=v[0],candidates=v[1]) for k,v in by.items()},runners={r:sum(e['runner']==r for e in items) for r in sorted({e['runner'] for e in items})})
    (DEST/'plan.json').write_text(json.dumps(plan,indent=1)+'\n')
    print(json.dumps({k:v for k,v in plan.items() if k!='excluded'},indent=1));print('excluded',len(excluded))

if __name__=='__main__':main()
