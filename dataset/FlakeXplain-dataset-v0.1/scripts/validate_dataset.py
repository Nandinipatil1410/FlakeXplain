"""Validate exported tables independently of the extraction loop."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()

def validate(out):
    manifest=json.loads((out/'manifest.json').read_text())
    schema=json.loads((out/'schema.json').read_text())
    checks=[]
    def check(condition,message):
        if not condition:
            raise ValueError(message)
        checks.append(message)
    check(all(sha(out/name)==h for name,h in manifest['files'].items()),'All exported file hashes match the manifest')
    check(all(sha(ROOT/name)==h for name,h in manifest['inputs'].items()),'Frozen input and extractor hashes match')
    labels=read(out/'labels.csv.gz'); metadata=read(out/'metadata.csv.gz')
    body=read(out/'features_body.csv.gz'); context=read(out/'features_context.csv.gz')
    sets=[{r['example_id'] for r in rows} for rows in (labels,metadata,body,context)]
    check(all(len(rows)==len(sets[0]) for rows in (labels,metadata,body,context)) and all(s==sets[0] for s in sets),
          'All four primary tables have unique, identical example IDs')
    check(len(labels)==manifest['model_cases'],'Model-ready case count reconciles')
    check(sum(int(r['label']) for r in labels)==manifest['observed_flaky'],'Positive count reconciles')
    check(len(labels)+len(read(out/'source_exclusions.csv.gz'))==manifest['candidate_cases'],'Included and source-excluded cases reconcile to evidence candidates')
    valid=True
    for r in labels:
        counts=Counter(r['outcomes'])
        y=int(r['label'])
        valid &= set(counts)<=set('PFE') and counts['P']>0 and bool(y)==bool(counts['F']+counts['E'])
        valid &= len(r['outcomes'])==int(r['effective_n'])
        for outcome,code in [('pass','P'),('fail','F'),('error','E')]:
            valid &= counts[code]==int(r[outcome+'_count'])
            valid &= sum(int(r[c+'_'+outcome+'_count']) for c in ('original','random','reverse'))==counts[code]
    check(valid,'Every label matches complete PASS/FAIL/ERROR observations and configuration counts')
    for name,rows in [('features_body.csv.gz',body),('features_context.csv.gz',context)]:
        allowed=set(schema['predictor_tables'][name])|{'example_id'}
        check(all(set(r)==allowed for r in rows),name+': exact predictor allowlist enforced')
        check(all(math.isfinite(float(v)) and float(v)>=0 and float(v).is_integer() for r in rows for k,v in r.items() if k!='example_id'),name+': finite nonnegative integer static features')
        check(not any(any(token in k for token in ('label','outcome','duration','seed','commit','project','fail_count','effective_n')) for k in allowed),name+': no detection or provenance fields among predictors')
    with gzip.open(out/'contexts.jsonl.gz','rt',encoding='utf-8') as f:
        contexts=[json.loads(line) for line in f]
    context_ids={c['context_id'] for c in contexts}
    check(len(context_ids)==len(contexts) and all(r['context_id'] in context_ids for r in metadata),'Context IDs are unique and every example joins to context provenance')
    check(all(len(c['nodes'])<=schema['bounds']['context_nodes'] for c in contexts),'Context size bound holds')
    sources={r['project']:r for r in json.loads((out/'source_manifest.json').read_text())}
    verified={}
    valid=True
    for r in metadata:
        path=ROOT/sources[r['project']]['source']/r['source_path']
        if path not in verified:
            verified[path]=sha(path)
        valid &= verified[path]==r['source_file_sha256'] and sources[r['project']]['commit']==r['commit']
        raw=json.dumps([r['project'],r['commit'],r['environment_id'],r['junit_file'],r['junit_classname'],r['junit_name']],ensure_ascii=False,separators=(',',':'))
        valid &= hashlib.sha256(raw.encode()).hexdigest()==r['example_id']
    check(valid,'Every identity and selected source-file hash matches pinned provenance')
    nodes_valid=True
    for c in contexts:
        for n in c['nodes']:
            path=ROOT/sources[c['project']]['source']/n['source'].split('::',1)[0]
            if path not in verified:
                verified[path]=sha(path)
            nodes_valid &= verified[path]==n['file_sha256']
    check(nodes_valid,'Every selected context source file matches its recorded hash')
    outer=read(out/'splits_outer.csv'); inner=read(out/'splits_inner.csv')
    split={r['project']:int(r['outer_test_fold']) for r in outer}
    check(len(split)==len(outer) and set(split)=={r['project'] for r in metadata},'Every eligible project has exactly one outer test fold')
    check(set(split.values())==set(range(5)),'All five outer folds are populated')
    groups=defaultdict(set)
    for r in outer:
        groups[r['project_group']].add(r['outer_test_fold'])
    check(all(len(v)==1 for v in groups.values()),'Exact-duplicate project groups never cross outer folds')
    check(all(len({split[p] for p in r['projects'].split('|')})==1 for r in read(out/'cross_project_exact_duplicates.csv')),
          'All substantive shared AST families stay in one outer fold')
    inner_valid=True
    for fold in range(5):
        records=[r for r in inner if int(r['outer_test_fold'])==fold]
        expected={p for p,f in split.items() if f!=fold}
        inner_valid &= {r['project'] for r in records}==expected and len(records)==len(expected)
        inner_valid &= {int(r['inner_validation_fold']) for r in records}==set(range(4))
        inner_groups=defaultdict(set)
        for r in records:
            inner_groups[r['project_group']].add(r['inner_validation_fold'])
        inner_valid &= all(len(v)==1 for v in inner_groups.values())
    check(inner_valid,'All four inner folds exclude the outer test projects and preserve duplicate groups')
    label_by_id={r['example_id']:int(r['label']) for r in labels}
    counts=defaultdict(Counter)
    for r in metadata:
        counts[split[r['project']]][label_by_id[r['example_id']]]+=1
    check(all(counts[f][0]>0 and counts[f][1]>0 and sum(counts[t][1] for t in counts if t!=f)>0 for f in range(5)),
          'Every outer test fold and its training complement contain both labels')
    result=dict(status='passed',checks=checks,cases=len(labels),positives=sum(label_by_id.values()),projects=len(split),source_files_verified=len(verified),
                manual_review='See manual_review_queue.csv and any completed static review record; not implied by automated validation')
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--dataset',type=Path,default=ROOT/'dataset/v0.1')
    print(json.dumps(validate(parser.parse_args().dataset),indent=2))
