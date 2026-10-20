"""v0.8: apply the frozen label rule (AMENDMENT_B2) to downloaded full-mode rerun artifacts.

Usage: python scripts/mdflaker_v08_label.py <run_id> [<run_id> ...]
Writes local-evidence/mdflaker-fresh-v0.8/labels.csv and reports/mdflaker-fresh-v0.8/labels_summary.json.
"""
import csv,json,sys,collections
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];RUNS=ROOT/'local-evidence/mdflaker-fresh-v0.8/runs'
CAND=ROOT/'reports/mdflaker-fresh-v0.8/candidates.csv';VALID=0.8;ROUNDS=30

def norm(n):return n.split('::',1)[0].replace(chr(92),'/')+('::'+n.split('::',1)[1] if '::' in n else '')

def main():
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')));label={};why={}
    for run in sys.argv[1:]:
        for f in sorted((RUNS/run).glob('rerun-*/e*.json')):
            if '_' in f.stem:continue
            r=json.loads(f.read_text(encoding='utf-8'))
            c=r.get('env_check') or {};ran=c.get('other_tests',0);ok=c.get('other_passed',0)
            if r['status']=='setup_failed':env='setup_failed'
            elif r['status']=='excluded':env='invalid_nodeids'
            elif r['status']!='done':env='incomplete'
            else:env='unchecked' if not ran else 'valid' if ok/ran>=VALID else 'invalid_env'
            for i in r['candidates']:
                node=norm(cands[i]['nodeid'])
                if env not in ('valid','unchecked'):label[i]=None;why[i]=env;continue
                if node in r.get('invalid_nodeids',[]) or node not in r['nodeids']:label[i]=None;why[i]='invalid_nodeid';continue
                outs=[rd['outcomes'].get(node,'MISSING') for rd in r.get('rounds',[])]
                if len(outs)<ROUNDS:label[i]=None;why[i]='incomplete_rounds'
                elif any(o in ('PASSED','XPASS') for o in outs):label[i]=1;why[i]=env
                elif all(o in ('FAILED','ERROR') for o in outs):label[i]=0;why[i]=env
                else:label[i]=None;why[i]='mixed_skip_or_missing'
    out=ROOT/'local-evidence/mdflaker-fresh-v0.8/labels.csv'
    with open(out,'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['candidate','repo','label','status'])
        for i in sorted(label):w.writerow([i,cands[i]['repo'],'' if label[i] is None else label[i],why[i]])
    by=collections.defaultdict(collections.Counter)
    for i in label:by[cands[i]['repo']]['flaky' if label[i]==1 else 'not_flaky' if label[i]==0 else 'unlabelled:'+why[i]]+=1
    tot=collections.Counter()
    for v in by.values():tot.update(v)
    summary=dict(runs=sys.argv[1:],candidates_with_results=len(label),total=dict(tot),by_repo={k:dict(v) for k,v in by.items()},
        projects_with_both_classes=sum(1 for v in by.values() if v['flaky'] and v['not_flaky']))
    (ROOT/'reports/mdflaker-fresh-v0.8/labels_summary.json').write_text(json.dumps(summary,indent=1)+'\n');print(json.dumps(summary,indent=1))

if __name__=='__main__':main()
