"""Extract each dataset test's source lines from the pinned archives for the v0.10 LLM baseline.

Reads archives only (no project code is imported or executed). Every source file is checked
against the SHA-256 recorded in dataset/v0.1/metadata.csv.gz; any mismatch stops the run.
The output holds example_id, project, outer_fold, label and code: no rerun evidence.
"""
import csv
import gzip
import hashlib
import json
import statistics
import tarfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'dataset/v0.1'
OUT_DIR = ROOT / 'local-evidence/llm-codebert-v0.10'
OUT = OUT_DIR / 'test_sources.jsonl.gz'
SUMMARY = ROOT / 'reports/llm-codebert-v0.10/extraction_summary.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_csv_gz(path):
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def main():
    folds = {r['project']: int(r['outer_test_fold']) for r in csv.DictReader(open(DATA / 'splits_outer.csv'))}
    labels = {r['example_id']: int(r['label']) for r in read_csv_gz(DATA / 'labels.csv.gz')}
    meta = read_csv_gz(DATA / 'metadata.csv.gz')
    archives = {m['project']: ROOT / Path(m['archive'].replace('\\', '/'))
                for m in json.load(open(DATA / 'source_manifest.json'))}
    by_project = defaultdict(list)
    for row in meta:
        by_project[row['project']].append(row)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lengths, written, positives = [], 0, 0
    with gzip.open(OUT, 'wt', encoding='utf-8', newline='\n') as out:
        for project in sorted(by_project):
            rows = by_project[project]
            wanted = {r['source_path']: r['source_file_sha256'] for r in rows}
            files = {}
            with tarfile.open(archives[project], 'r:gz') as tar:
                for member in tar:
                    if not member.isfile():
                        continue
                    path = member.name.split('/', 1)[1] if '/' in member.name else ''
                    if path in wanted:
                        data = tar.extractfile(member).read()
                        if sha(data) != wanted[path]:
                            raise ValueError(f'{project}: SHA-256 mismatch for {path}')
                        files[path] = data.decode('utf-8').splitlines()
            missing = set(wanted) - set(files)
            if missing:
                raise ValueError(f'{project}: {len(missing)} source files not in archive, e.g. {sorted(missing)[0]}')
            for r in rows:
                lines = files[r['source_path']][int(r['source_start']) - 1:int(r['source_end'])]
                code = '\n'.join(lines)
                if not code.strip():
                    raise ValueError(f'{project}: empty source for {r["example_id"]}')
                label = labels[r['example_id']]
                out.write(json.dumps({'example_id': r['example_id'], 'project': project,
                                      'outer_fold': folds[project], 'label': label, 'code': code}) + '\n')
                lengths.append(len(code))
                written += 1
                positives += label
            print(f'{project}: {len(rows)} tests')
    if written != len(labels):
        raise ValueError(f'wrote {written} rows but labels has {len(labels)}')
    summary = {
        'output': OUT.relative_to(ROOT).as_posix(),
        'output_sha256': sha(OUT.read_bytes()),
        'tests': written,
        'positives': positives,
        'projects': len(by_project),
        'code_characters': {'median': statistics.median(lengths), 'p90': sorted(lengths)[int(0.9 * len(lengths))],
                            'max': max(lengths)},
        'fields': ['example_id', 'project', 'outer_fold', 'label', 'code'],
    }
    SUMMARY.write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
