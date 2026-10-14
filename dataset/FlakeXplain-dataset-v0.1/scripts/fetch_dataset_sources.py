"""Fetch commit-pinned source archives without importing or executing subjects."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def fetch(project, repository, commit, destination):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Expected a full commit: ' + project)
    source = destination / project
    archive = destination / f'{project}-{commit}.tar.gz'
    manifest = source / 'FLAKEXPLAIN_SOURCE_PROVENANCE.json'
    if manifest.exists():
        record = json.loads(manifest.read_text())
        if record['commit'] != commit or not archive.exists() or sha(archive) != record['sha256']:
            raise ValueError('Existing source provenance differs: ' + project)
        return record
    url = f'https://codeload.github.com/{repository}/tar.gz/{commit}'
    if not archive.exists():
        temp = archive.with_suffix('.partial')
        request = urllib.request.Request(url, headers={'User-Agent': 'FlakeXplain-source-audit'})
        with urllib.request.urlopen(request, timeout=180) as response, temp.open('wb') as out:
            shutil.copyfileobj(response, out)
        temp.replace(archive)
    source.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            parts = PurePosixPath(member.name).parts
            if not parts or '..' in parts or PurePosixPath(member.name).is_absolute():
                raise ValueError('Unsafe archive member')
            target = source.joinpath(*parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as inp, target.open('wb') as out:
                    shutil.copyfileobj(inp, out)
            # Links/devices are intentionally not materialized or followed.
    record = dict(project=project, repository=repository, commit=commit, url=url,
                  archive=str(archive.relative_to(ROOT)), sha256=sha(archive),
                  source=str(source.relative_to(ROOT)))
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    return record

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, default=ROOT / 'local-evidence/recovery-2026-10-12/pinned-sources')
    args = parser.parse_args()
    audit = json.loads((ROOT / 'reports/workflow-audit/audit.json').read_text())
    # Read our trusted configuration as AST, never execute subject code.
    import ast
    tree = ast.parse((ROOT / 'scripts/setup_repos.py').read_text(encoding='utf-8-sig'))
    configs = next(ast.literal_eval(n.value) for n in tree.body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'REPOS' for t in n.targets))
    configs.update(json.loads((ROOT / 'cannier-replication/remaining-configs.json').read_text(encoding='utf-8-sig')))
    args.destination.mkdir(parents=True, exist_ok=True)
    records, failures = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {}
        for p in audit['projects']:
            if not p['status'].startswith('protocol_complete'):
                continue
            repository = configs[p['project']]['url'].removeprefix('https://github.com/').removesuffix('.git').rstrip('/')
            job = pool.submit(fetch, p['project'], repository, p['commit'], args.destination)
            jobs[job] = p['project']
        for job in as_completed(jobs):
            try:
                record = job.result()
                records.append(record)
                print(record['project'] + ': pinned source verified', flush=True)
            except Exception as exc:
                failures.append((jobs[job], str(exc)))
                print(f'{jobs[job]}: FAILED {exc}', flush=True)
    (args.destination / 'source_inventory.json').write_text(json.dumps(sorted(records, key=lambda x:x['project']), indent=2)+'\n')
    if failures:
        raise SystemExit(str(failures))

if __name__ == '__main__':
    main()
