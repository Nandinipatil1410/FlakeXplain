"""Rehash the audited raw evidence before declaring a dataset freeze."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repos-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/evidence-recovery/dataset_freeze_verification.json')
    args=parser.parse_args()
    audit=json.loads((ROOT/'reports/workflow-audit/audit.json').read_text())
    projects={p['project'] for p in audit['projects'] if p['status'].startswith('protocol_complete')}
    failures=[]; count=0; total=0
    with (ROOT/'reports/workflow-audit/evidence_hashes.csv').open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['project'] not in projects:
                continue
            path=args.repos_dir/r['project']/r['evidence_path']
            h=hashlib.sha256()
            try:
                with path.open('rb') as inp:
                    for block in iter(lambda:inp.read(1048576),b''):
                        h.update(block)
                if path.stat().st_size!=int(r['bytes']) or h.hexdigest()!=r['sha256']:
                    failures.append(str(path))
                total+=path.stat().st_size; count+=1
            except OSError as exc:
                failures.append(str(path)+': '+str(exc))
    result=dict(status='passed' if not failures else 'failed',projects=len(projects),files=count,bytes=total,failures=failures,
                evidence_hashes_sha256=hashlib.sha256((ROOT/'reports/workflow-audit/evidence_hashes.csv').read_bytes()).hexdigest())
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if failures:
        raise SystemExit(1)
if __name__=='__main__':
    main()
