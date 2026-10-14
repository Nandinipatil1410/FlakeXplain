"""Retrieve verified public CANNIER artifacts and exact source revisions.

Downloaded upstream Python and pickle files are never executed or deserialized.
"""
import argparse,concurrent.futures,hashlib,json,shutil,time,urllib.request,zipfile
from pathlib import Path
from fetch_dataset_sources import fetch
from train_pilot import ROOT,sha
from prepare_cannier_matched import LOCAL

REVISION='b96d6ed02e98d514eb6a92ca264a082234cb9728'
DIGEST='07d714a7e0f57863070d1ba6631191aa6e856fac1ad3ffc92765d6c1fc56f9f1'
SIZE=354333950
BEST=['NOD-vs-Rest_18_ExtraTrees_100_SMOTE_1.npy','Victim-vs-Rest_18_ExtraTrees_75_SMOTE_1.npy','NOD-vs-Victim_18_RandomForest_75_SMOTE_1.npy','Polluter-vs-Rest_18_RandomForest_100_SMOTE_1.npy']

def download(url,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(url,headers={'User-Agent':'FlakeXplain-matched-replication'})
    with urllib.request.urlopen(req,timeout=60) as response,target.with_suffix(target.suffix+'.partial').open('wb') as f:
        total=0;last=time.monotonic()
        while True:
            block=response.read(1024*1024)
            if not block:break
            f.write(block);total+=len(block)
            if time.monotonic()-last>20:print('Downloaded bytes:',total,flush=True);last=time.monotonic()
    target.with_suffix(target.suffix+'.partial').replace(target)

def main():
    LOCAL.mkdir(parents=True,exist_ok=True);archive=LOCAL/'authors-output.zip'
    if not archive.exists():download('https://media.githubusercontent.com/media/flake-it/cannier-experiment/'+REVISION+'/output.zip',archive)
    if archive.stat().st_size!=SIZE or sha(archive)!=DIGEST:raise ValueError('CANNIER archive does not match published LFS digest')
    subjects=json.loads((ROOT/'cannier-replication/subjects.json').read_text());slugs={repo.split('/')[-1] for repo in subjects}
    wanted={'output/items.npy','output/features.npy'}|{'output/preds/'+p for p in BEST}|{'output/volume/'+p+'.sqlite3' for p in slugs}
    with zipfile.ZipFile(archive) as z:
        if not wanted<=set(z.namelist()):raise ValueError('Required release members missing')
        for name in sorted(wanted):
            target=(LOCAL/name).resolve()
            if LOCAL.resolve() not in target.parents:raise ValueError('Unsafe archive member')
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(name) as inp,target.open('wb') as f:shutil.copyfileobj(inp,f)
    sources={}
    for candidate in [LOCAL/'source_records.json',ROOT/'dataset/v0.1/source_manifest.json']:
        if candidate.exists():
            for r in json.loads(candidate.read_text()):
                if (ROOT/r['source']).exists() and (ROOT/r['archive']).exists():sources[(r['repository'],r['commit'])]=r
    destination=LOCAL/'sources';destination.mkdir(exist_ok=True)
    def source(item):
        repo,data=item;commit=data[0];cached=sources.get((repo,commit))
        if cached:
            if sha(ROOT/cached['archive'])!=cached['sha256']:raise ValueError('Cached source archive changed')
            return cached
        return fetch(repo.split('/')[-1].lower().replace('-','_'),repo,commit,destination.resolve())
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(source,subjects.items()))
    (LOCAL/'source_records.json').write_text(json.dumps(records,indent=2)+'\n')
    references=[('framework','cannier-framework','89c74c27847474248b581b428aed2b417141296e',['cannier_framework/model.py','cannier_framework/collate.py','cannier_framework/globals.py','requirements.txt']),('plugin','pytest-cannier','2d58145c2786477a721c754e3a05639017c080d4',['pytest_cannier/features.py','requirements.txt'])]
    for directory,repo,revision,files in references:
        for name in files:
            target=LOCAL/directory/name
            if not target.exists():download('https://raw.githubusercontent.com/flake-it/'+repo+'/'+revision+'/'+name,target)
    print('Verified release and source archives ready:',len(records),'projects; no upstream code executed',flush=True)

if __name__=='__main__':main()
