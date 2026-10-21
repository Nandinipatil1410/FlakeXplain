"""Check that the flakexplain CLI computes the same ET-BF features as the v0.8 study.

For every labelled v0.8 failure, the CLI's extractor (tool/src/flakexplain/features.py) is run on the
saved CI log, the local clone and the v0.8 run metadata, and each feature is compared with
features.csv.gz (flaky_frequency with the strict value). Source-dependent features need exported trees,
so they are compared on the failures of --source-trees randomly drawn tested trees only.
Usage: GH_TOKEN=unused python scripts/check_tool_parity.py [--source-trees N]
"""
import argparse,csv,functools,gzip,json,os,random,sys,datetime
from collections import defaultdict,Counter
from pathlib import Path
os.environ['GIT_NO_LAZY_FETCH']='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tool/src'))
from mdflaker_v08_features import CAND,LOGS,V8,clone,tested_tree,export,rmtree,read_log
from mdflaker_v08_robustness import strict_frequency
from flakexplain import features as fx
from flakexplain.source_index import SourceIndex
fx.diff=functools.lru_cache(maxsize=None)(fx.diff)  # many failures share a tested tree

SOURCE=['test_smells','test_size','own_test_file_changed','path_overlap_depth','last_frame_in_test_file']
def ts(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-trees',type=int,default=12);a=ap.parse_args()
    cands=list(csv.DictReader(open(CAND,encoding='utf-8')))
    with gzip.open(V8/'features.csv.gz','rt',encoding='utf-8') as f:feat={int(r['candidate']):r for r in csv.DictReader(f)}
    lab={int(r['candidate']) for r in csv.DictReader(open(V8/'labels.csv',encoding='utf-8')) if r['label']!=''}
    ids=sorted(i for i in lab if i in feat);_,strict=strict_frequency(cands);print('strict history done',flush=True)
    prev={tuple(k.split('|',1)):v for k,v in json.loads((V8/'previous_states.json').read_text()).items()}
    dur=json.loads((V8/'job_durations.json').read_text())
    # History in the CLI's format, built from the same saved logs with the CLI's own log parser.
    hist=defaultdict(list);parsed={}
    for d in LOGS.iterdir():
        for t in d.glob('*.txt*'):
            m=json.loads((d/(t.name.split('.')[0]+'.json')).read_text());text=read_log(t)
            failures,_=fx.from_log(text);parsed[(d.name,str(m['job_id']))]=failures
            for n,_ in failures:hist[(d.name,fx.history_key(n))].append((ts(m['created_at']),str(m['run_id'])))
    byrepo=defaultdict(dict)
    for (k,n),v in hist.items():byrepo[k][n]=v
    print('logs parsed',len(parsed),flush=True)
    trees={}
    for i in ids:trees.setdefault(tested_tree(cands[i]),[]).append(i)
    rng=random.Random(20261021);pick=set(rng.sample(sorted(k for k in trees if k[0]),min(a.source_trees,sum(1 for k in trees if k[0]))))
    mism=Counter();checked=Counter();examples=defaultdict(list);src_rows=0
    for n,((tree,base),members) in enumerate(sorted(trees.items(),key=lambda kv:str(kv[0]))):
        if n%25==0:print('tree',n,'of',len(trees),flush=True)
        repo=cands[members[0]]['repo'];root=export(repo,tree) if (tree,base) in pick else None;index=SourceIndex(root) if root else None
        for i in members:
            c=cands[i];key=repo.replace('/','__');failures=parsed[(key,c['job_id'])]
            node=fx.norm_node(c['nodeid'])
            h=byrepo[key]
            rows=fx.extract(failures,repo=clone(repo),base=base,tree=tree,source_root=None,index=index,repo_name=repo.split('/')[1],
                roots=[c['rootdir']] if c['rootdir'] else [],history=h,run_id=c['run_id'],when=ts(c['created_at']),
                previous_state=prev.get((repo,c['run_id']),2),job_duration_s=dur.get(c['job_id'],0),pr_build=c['event']=='pull_request')
            mine=next((r for r in rows if r['nodeid']==node),None)
            if mine is None:mism['candidate_not_parsed']+=1;examples['candidate_not_parsed'].append(c['nodeid']);continue
            src_rows+=index is not None
            for col in fx.COLUMNS:
                if col in SOURCE and index is None:continue
                want=strict[i] if col=='flaky_frequency' else float(feat[i][col]);got=float(mine['features'][col]);checked[col]+=1
                if abs(want-got)>1e-6:
                    mism[col]+=1
                    if len(examples[col])<3:examples[col].append(dict(candidate=i,want=want,got=got))
        if root:rmtree(root)
    out=dict(failures=len(ids),rows_with_source=src_rows,checked=dict(checked),mismatches=dict(mism),examples=dict(examples))
    print(json.dumps(out,indent=1))
    (ROOT/'reports/mdflaker-fresh-v0.8/tool_parity.json').write_text(json.dumps(out,indent=1)+'\n')

if __name__=='__main__':main()
