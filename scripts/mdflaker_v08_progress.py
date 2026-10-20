"""Print one progress line for v0.8 rerun workflow runs: python scripts/mdflaker_v08_progress.py <run_id> ..."""
import collections,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from mdflaker_v08_probe import api

REPO='Nandinipatil1410/FlakeXplain'
parts=[];status=set()
for run in sys.argv[1:]:
    c=collections.Counter();total=0;page=1
    while True:
        d=api(f'https://api.github.com/repos/{REPO}/actions/runs/{run}/jobs?per_page=100&page={page}')
        if not d or not d.get('jobs'):break
        total=d['total_count']
        for j in d['jobs']:
            if j['name']=='plan':continue
            c[j['status']]+=1
            if j['status']=='completed' and j['conclusion']!='success':c['failed']+=1
        page+=1
    r=api(f'https://api.github.com/repos/{REPO}/actions/runs/{run}') or {};status.add(r.get('status'))
    parts.append(f"run {run}: {c['completed']}/{max(total-1,0)} done, {c['in_progress']} running, {c['queued']} queued, {c['failed']} failed")
print(' | '.join(parts)+(' | ALL COMPLETED' if status=={'completed'} else ''))
