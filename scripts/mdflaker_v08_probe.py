"""v0.8 label-blind probe: count parseable failed pytest executions in recent GitHub Actions runs.

No rerun is performed and no label exists yet. Raw logs are kept under ignored local-evidence/
(GitHub deletes them after 90 days). Token is read from GH_TOKEN and never written anywhere.
"""
import json,os,re,sys,time,urllib.request,urllib.error
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];LOCAL=ROOT/'local-evidence/mdflaker-fresh-v0.8';OUT=ROOT/'reports/mdflaker-fresh-v0.8'
TOKEN=os.environ['GH_TOKEN']
# Preference order fixed in PROTOCOL_DRAFT.md section 3: MDFlaker's own projects, then FlakeXplain corpus projects.
REPOS=['explosion/spaCy','encode/django-rest-framework',
    'urllib3/urllib3','Textualize/rich','pytest-dev/pytest','tox-dev/filelock','python-attrs/attrs','HypothesisWorks/hypothesis',
    'celery/celery','celery/kombu','Delgan/loguru','Pylons/pyramid','tornadoweb/tornado','psf/requests','sunpy/sunpy',
    'quantumlib/Cirq','conan-io/conan','dask/dask','ipython/ipython','python-pillow/Pillow','PrefectHQ/prefect','mwaskom/seaborn',
    'pypa/setuptools','mitmproxy/mitmproxy','PyGithub/PyGithub','graphql-python/graphene','facebookresearch/hydra','Flexget/Flexget',
    'apache/libcloud','xonsh/xonsh','fonttools/fonttools','scikit-image/scikit-image','spulec/freezegun','reframe-hpc/reframe','spesmilo/electrum']
SINCE=(datetime.now(timezone.utc)-timedelta(days=89)).strftime('%Y-%m-%d')
MAX_RUNS,MAX_LOGS=int(os.environ.get('PROBE_MAX_RUNS',40)),int(os.environ.get('PROBE_MAX_LOGS',40))
if os.environ.get('PROBE_REPOS'):REPOS=os.environ['PROBE_REPOS'].split(',')
SKIP_JOB=re.compile(r'lint|\bdocs?\b|mypy|typing|pre-commit|changelog|release|publish|codeql|label|stale|\bcheck$|alls-green|dependabot',re.I)
SKIP_WORKFLOW=re.compile(r'lock|stale|label|issue|comment|bot|changelog|release|publish|docs|pages|codeql|welcome|triage|backport|dependabot',re.I)
SKIP_EVENT={'schedule','issue_comment','issues','pull_request_target','workflow_dispatch','dynamic','release'}
ANSI=re.compile(r'\x1b\[[0-9;]*m|\[[0-9;]*m(?=\S)')
STAMP=re.compile(r'^\d{4}-\d\d-\d\dT[\d:.]+Z ')
FAILED=[re.compile(r'^(?:FAILED|ERROR) (\S+?\.py::\S+)'),re.compile(r'^(\S+?\.py::\S+) (?:FAILED|ERROR)\b')]
calls=0

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**k):return None
NOREDIRECT=urllib.request.build_opener(NoRedirect)

def api(url,raw=False):
    """GitHub API call; log downloads redirect to blob storage, which must be fetched without the token."""
    global calls
    attempt=0
    while attempt<4:
        attempt+=1
        req=urllib.request.Request(url,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        try:
            try:
                with NOREDIRECT.open(req,timeout=60) as r:
                    calls+=1;data=r.read()
            except urllib.error.HTTPError as e:
                calls+=1
                if e.code in (301,302,303,307,308) and e.headers.get('Location'):
                    try:
                        with urllib.request.urlopen(e.headers['Location'],timeout=120) as r:data=r.read()
                    except urllib.error.HTTPError:return None  # expired or missing log blob
                elif e.code in (404,410):return None
                elif e.code in (403,429) and e.headers.get('X-RateLimit-Remaining')=='0':
                    wait=max(5,int(e.headers.get('X-RateLimit-Reset',time.time()+60))-time.time()+5)
                    print(f'rate limit reached; sleeping {int(wait)}s',flush=True);time.sleep(wait);attempt-=1;continue
                elif e.code in (403,429) or e.code>=500:time.sleep(30);continue
                else:return None
            return data.decode('utf-8','replace') if raw else json.loads(data)
        except Exception:time.sleep(5*(attempt+1))  # network resets, truncated reads, bad JSON
    return None

def read_log(path):
    """Read a saved job log; logs are stored gzip-compressed (<job>.txt.gz) after 20 Oct 2026."""
    import gzip
    path=Path(path);gz=path.with_name(path.name+'.gz') if path.suffix=='.txt' else path
    if path.suffix=='.txt' and path.exists():return path.read_text(encoding='utf-8',errors='replace')
    return gzip.open(gz,'rt',encoding='utf-8',errors='replace').read()

def parse(log):
    tests=set()
    for line in log.splitlines():
        line=ANSI.sub('',STAMP.sub('',line)).strip()
        for rx in FAILED:
            m=rx.match(line)
            if m:tests.add(m.group(1).split(' - ')[0])
    return tests

def main():
    part=LOCAL/os.environ.get('PROBE_PARTIAL','probe_partial.json');report=json.loads(part.read_text()) if part.exists() else {}
    for repo in REPOS:
        if repo in report:continue
        runs=[];page=1
        while len(runs)<MAX_RUNS and page<=int(os.environ.get('PROBE_MAX_PAGES',5)):
            d=api(f'https://api.github.com/repos/{repo}/actions/runs?status=failure&created=%3E%3D{SINCE}&per_page=100&page={page}')
            if not d or not d.get('workflow_runs'):break
            runs+=[r for r in d['workflow_runs'] if r.get('event') not in SKIP_EVENT and not SKIP_WORKFLOW.search(r.get('name') or '')];page+=1
        runs=runs[:MAX_RUNS];logs=0;execs=0;tests=set();commits=set();jobs_failed=0
        for run in runs:
            j=api(f"https://api.github.com/repos/{repo}/actions/runs/{run['id']}/jobs?filter=latest&per_page=100")
            for job in (j or {}).get('jobs',[]):
                if job.get('conclusion')!='failure' or SKIP_JOB.search(job.get('name','')):continue
                jobs_failed+=1
                if logs>=MAX_LOGS:continue
                path=LOCAL/'logs'/repo.replace('/','__')/f"{job['id']}.txt"
                if path.exists() or path.with_name(path.name+'.gz').exists():log=read_log(path)
                else:
                    log=api(f"https://api.github.com/repos/{repo}/actions/jobs/{job['id']}/logs",raw=True)
                    if log is None:continue
                    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(log,encoding='utf-8')
                    (path.with_suffix('.json')).write_text(json.dumps(dict(run_id=run['id'],job_id=job['id'],job_name=job['name'],head_sha=run['head_sha'],
                        event=run['event'],created_at=run['created_at'],run_attempt=run.get('run_attempt'),workflow=run.get('name'))),encoding='utf-8')
                logs+=1;t=parse(log)
                if t:execs+=len(t);tests|=t;commits.add(run['head_sha'])
        report[repo]=dict(failed_runs_seen=len(runs),failed_test_jobs=jobs_failed,logs_parsed=logs,failed_executions=execs,distinct_tests=len(tests),commits=len(commits))
        print(repo,report[repo],'api_calls',calls,flush=True);part.write_text(json.dumps(report,indent=1))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/os.environ.get('PROBE_SUMMARY','probe_summary.json')).write_text(json.dumps(dict(since=SINCE,max_runs=MAX_RUNS,max_logs=MAX_LOGS,api_calls=calls,repos=report),indent=1)+'\n')

if __name__=='__main__':main()
