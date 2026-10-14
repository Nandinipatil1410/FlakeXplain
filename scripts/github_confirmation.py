"""Read status and preserve artifacts for the prospectively selected campaign.

Credentials are obtained in memory from Git's credential helper, never printed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import urllib.request
import urllib.error
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/final-confirmation-v0.3'
API='https://api.github.com/repos/Nandinipatil1410/FlakeXplain'

@lru_cache(maxsize=1)
def headers():
    env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
    result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\nusername=Nandinipatil1410\n\n',capture_output=True,text=True,check=True,cwd=ROOT,env=env,timeout=30)
    credential=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    return {'Authorization':'Bearer '+credential['password'],'Accept':'application/vnd.github+json','User-Agent':'FlakeXplain-confirmation'}

def get(path):
    with urllib.request.urlopen(urllib.request.Request(API+path,headers=headers()),timeout=60) as response:
        return json.load(response)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['status','download']);args=parser.parse_args()
    run=json.loads((OUT/'campaign_runs.json').read_text())[0];rid=run['id']
    data=get('/actions/runs/'+str(rid))
    jobs=get('/actions/runs/'+str(rid)+'/jobs?per_page=100')
    summary=dict(checked_utc=datetime.now(timezone.utc).isoformat(),id=rid,url=data['html_url'],status=data['status'],conclusion=data['conclusion'],head_sha=data['head_sha'],
        jobs=[dict(name=j['name'],status=j['status'],conclusion=j['conclusion'],started_at=j['started_at'],completed_at=j['completed_at']) for j in jobs['jobs']])
    (OUT/'campaign_status.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
    if args.action=='status':return
    if not (OUT/'model_manifest.json').exists():raise ValueError('Do not access outcomes before all models are frozen')
    if data['status']!='completed':raise ValueError('Wait for campaign completion before extracting outcomes')
    artifacts=get('/actions/runs/'+str(rid)+'/artifacts?per_page=100')['artifacts']
    expected={'werkzeug','attrs','tenacity'};saved=[]
    for artifact in artifacts:
        project=next((p for p in expected if artifact['name'].startswith('confirmation-'+p+'-')),None)
        if not project: continue
        target=ROOT/'local-evidence/confirmation-artifacts';target.mkdir(parents=True,exist_ok=True)
        archive=target/(artifact['name']+'.zip')
        if not archive.exists():
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self,*args,**kwargs): return None
            request=urllib.request.Request(API+'/actions/artifacts/'+str(artifact['id'])+'/zip?cache_bust='+str(time.time_ns()),headers=headers())
            try:
                urllib.request.build_opener(NoRedirect()).open(request,timeout=60)
                raise ValueError('Expected a signed artifact download redirect')
            except urllib.error.HTTPError as redirect:
                if redirect.code!=302: raise
                signed_url=redirect.headers['Location']
            # Do not forward the GitHub credential to the artifact storage host.
            with urllib.request.urlopen(signed_url,timeout=60) as response,archive.with_suffix('.partial').open('wb') as f: shutil.copyfileobj(response,f)
            archive.with_suffix('.partial').replace(archive)
        checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
        if artifact.get('digest') and artifact['digest']!='sha256:'+checksum:raise ValueError('GitHub archive digest mismatch')
        evidence=ROOT/'local-evidence/confirmation-evidence'/project;evidence.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                path=(evidence/entry.filename).resolve()
                if evidence.resolve() not in path.parents:raise ValueError('Unsafe artifact path')
                if entry.is_dir():path.mkdir(parents=True,exist_ok=True)
                else:
                    path.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(entry) as inp,path.open('wb') as f:shutil.copyfileobj(inp,f)
        saved.append(dict(project=project,artifact_id=artifact['id'],artifact_name=artifact['name'],archive_sha256=checksum,github_digest=artifact.get('digest'),run_id=rid,run_url=data['html_url'],archive=str(archive.relative_to(ROOT)),evidence=str(evidence.relative_to(ROOT))))
    (OUT/'artifact_provenance.json').write_text(json.dumps(saved,indent=2)+'\n')
    print('Preserved artifacts: '+str(len(saved)))

if __name__=='__main__':main()
