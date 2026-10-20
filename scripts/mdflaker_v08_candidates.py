"""v0.8: build the label-blind candidate list (PROTOCOL section 4) from downloaded CI job logs.

All isolated failures (job with <= 5 failed tests) plus one seeded draw per mass-failure job.
Environment (runner image, Python, pytest rootdir) and the job's run steps come from the log itself.
"""
import csv,json,random,re,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_probe import parse,STAMP,ANSI,read_log

ROOT=Path(__file__).resolve().parents[1];LOGS=ROOT/'local-evidence/mdflaker-fresh-v0.8/logs';OUT=ROOT/'reports/mdflaker-fresh-v0.8'
PROJECTS=json.loads((OUT/'projects_proposed.json').read_text())['projects']
SEED=20261020;ISOLATED_MAX=5

def env(log):
    lines=[ANSI.sub('',STAMP.sub('',l)) for l in log.splitlines()]
    image=next((l.split('Image:',1)[1].strip() for l in lines if l.startswith('Image: ')),'')
    plat=next((re.search(r'platform (\w+) -- Python ([\d.]+)',l) for l in lines if re.search(r'^platform \w+ -- Python',l)),None)
    root=next((l.split('rootdir:',1)[1].split(',')[0].strip() for l in lines if l.startswith('rootdir:')),'')
    steps=[l[len('##[group]Run '):].strip() for l in lines if l.startswith('##[group]Run ')]
    merge=next((re.search(r'Merge ([0-9a-f]{40}) into ([0-9a-f]{40})',l) for l in lines if re.search(r'HEAD is now at \S+ Merge [0-9a-f]{40} into [0-9a-f]{40}',l)),None)
    return dict(image=image,platform=plat.group(1) if plat else '',python=plat.group(2) if plat else '',rootdir=root,steps=steps,
        merge_head=merge.group(1) if merge else '',merge_base=merge.group(2) if merge else '')

def main():
    rng=random.Random(SEED);out=[];envs={}
    for p in PROJECTS:
        d=LOGS/p['repo'].replace('/','__')
        for t in sorted(d.glob('*.txt*'),key=lambda x:int(x.name.split('.')[0])):
            m=json.loads((d/(t.name.split('.')[0]+'.json')).read_text());log=read_log(t)
            failed=sorted(parse(log))
            if not failed:continue
            e=env(log);envs[m['job_id']]=e
            mass=len(failed)>ISOLATED_MAX;chosen=[rng.choice(failed)] if mass else failed
            for node in chosen:
                out.append(dict(repo=p['repo'],run_id=m['run_id'],job_id=m['job_id'],job_name=m['job_name'],workflow=m['workflow'],event=m['event'],
                    head_sha=m['head_sha'],created_at=m['created_at'],run_attempt=m['run_attempt'],nodeid=node,job_failed_tests=len(failed),
                    mass_job=int(mass),image=e['image'],platform=e['platform'],python=e['python'],rootdir=e['rootdir'],
                    checkout=('push' if m['event']!='pull_request' else 'pr_merge' if e['merge_head']==m['head_sha'] else 'pr_merge_unknown'),
                    merge_base=e['merge_base'] if m['event']=='pull_request' else ''))
    out.sort(key=lambda r:(r['repo'],r['created_at'],r['job_id'],r['nodeid']))
    dest=OUT/'candidates.csv'
    with open(dest,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,list(out[0]));w.writeheader();w.writerows(out)
    (ROOT/'local-evidence/mdflaker-fresh-v0.8/job_envs.json').write_text(json.dumps(envs,indent=1))
    by={}
    for r in out:
        b=by.setdefault(r['repo'],dict(candidates=0,mass=0,commits=set(),envs=set(),missing_python=0))
        b['candidates']+=1;b['mass']+=r['mass_job'];b['commits'].add(r['head_sha']);b['envs'].add((r['head_sha'],r['image'],r['python']));b['missing_python']+=not r['python']
    for r in out:by[r['repo']].setdefault('checkout',{}).setdefault(r['checkout'],0);by[r['repo']]['checkout'][r['checkout']]+=1
    summary={k:dict(checkout=v['checkout'],candidates=v['candidates'],mass=v['mass'],commits=len(v['commits']),environments=len(v['envs']),missing_python=v['missing_python']) for k,v in by.items()}
    print(json.dumps(summary,indent=1));print('total',len(out),'sha256',hashlib.sha256(dest.read_bytes()).hexdigest())

if __name__=='__main__':main()
