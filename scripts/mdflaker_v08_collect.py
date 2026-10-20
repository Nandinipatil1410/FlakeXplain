"""v0.8: download a rerun workflow's artifacts and summarize setup / environment-check status.

Usage: GH_TOKEN=... python scripts/mdflaker_v08_collect.py <run_id> [--outcomes]
Without --outcomes only setup and environment-check fields are printed (pilot / recipe fixing, B2).
"""
import io,json,os,sys,zipfile,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_probe import api,NOREDIRECT,TOKEN

def download(url):
    """Binary download; the API redirects to blob storage, fetched without the token."""
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json'})
    try:
        with NOREDIRECT.open(req,timeout=120) as r:return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (301,302,303,307,308):
            with urllib.request.urlopen(e.headers['Location'],timeout=300) as r:return r.read()
        raise

ROOT=Path(__file__).resolve().parents[1];REPO='Nandinipatil1410/FlakeXplain'
VALID=0.8

def main():
    run=sys.argv[1];dest=ROOT/'local-evidence/mdflaker-fresh-v0.8/runs'/run;dest.mkdir(parents=True,exist_ok=True)
    page=1;arts=[]
    while True:
        d=api(f'https://api.github.com/repos/{REPO}/actions/runs/{run}/artifacts?per_page=100&page={page}')
        if not d or not d.get('artifacts'):break
        arts+=d['artifacts'];page+=1
    for a in arts:
        out=dest/a['name']
        if out.exists():continue
        raw=download(a['archive_download_url'])
        try:zipfile.ZipFile(io.BytesIO(raw)).extractall(out)
        except zipfile.BadZipFile:print('bad zip',a['name'])
    rows=[]
    for f in sorted(dest.glob('rerun-*/e*.json')):
        if '_' in f.stem:continue
        r=json.loads(f.read_text(encoding='utf-8'));c=r.get('env_check') or {}
        ran=c.get('other_tests',0);ok=c.get('other_passed',0)
        verdict='setup_failed' if r['status']=='setup_failed' else 'excluded' if r['status']=='excluded' else ('unchecked' if not ran else 'valid' if ok/ran>=VALID else 'invalid')
        row=dict(env=r['env_id'],repo=r['repo'],runner=r['runner'],python=r['python'],variant=r['variant'],status=r['status'],stage=r.get('stage',''),
            detail=(r.get('detail') or '')[:120],setup_s=r.get('setup_seconds'),other=ran,other_ok=ok,env_verdict=verdict,invalid_ids=len(r.get('invalid_nodeids',[])))
        rows.append(row)
    for r in rows:print(json.dumps(r))
    print('artifacts',len(arts),'summarized',len(rows))

if __name__=='__main__':main()
