"""Export a reproducible, static-only dataset from the frozen audited evidence.

Run after fetch_dataset_sources.py. Never imports subjects or executes pytest.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
from dataset_static import SourceIndex, FEATURES, features, body_tree, digest

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'
SOURCE_ROOT = ROOT / 'local-evidence/recovery-2026-10-12/pinned-sources'

def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def csv_write(path, rows, fields):
    # Fixed gzip mtime makes exports byte-reproducible.
    if path.suffix == '.gz':
        import io
        with path.open('wb') as out, gzip.GzipFile(filename='', fileobj=out, mode='wb',mtime=0) as gz:
            with io.TextIOWrapper(gz,encoding='utf-8',newline='') as f:
                writer = csv.DictWriter(f,fieldnames=fields,extrasaction='raise')
                writer.writeheader(); writer.writerows(rows)
    else:
        with path.open('w',encoding='utf-8',newline='') as f:
            writer = csv.DictWriter(f,fieldnames=fields,extrasaction='raise')
            writer.writeheader(); writer.writerows(rows)

def verify_sources(root, record):
    archive = ROOT / record['archive']
    if file_sha(archive) != record['sha256']:
        raise ValueError('Archive hash mismatch: ' + record['project'])
    expected = {}
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            relative = '/'.join(member.name.split('/')[1:])
            if member.isfile() and relative.endswith('.py'):
                with tar.extractfile(member) as f:
                    expected[relative] = hashlib.sha256(f.read()).hexdigest()
    actual = {p.relative_to(root).as_posix():file_sha(p) for p in root.rglob('*.py')}
    if actual != expected:
        raise ValueError('Extracted Python files differ from pinned archive: ' + record['project'])
    return digest(json.dumps(expected,sort_keys=True)), len(expected)

def make_groups(metadata):
    """Join project groups sharing substantive exact AST test bodies."""
    projects = sorted({r['project'] for r in metadata})
    parents = {p:p for p in projects}
    def find(p):
        while parents[p] != p:
            parents[p] = parents[parents[p]]; p = parents[p]
        return p
    families = defaultdict(set)
    for r in metadata:
        if r['body_statements'] >= 3 and r['body_ast_nodes'] >= 20:
            families[r['body_ast_sha256']].add(r['project'])
    shared = []
    for key, ps in sorted(families.items()):
        if len(ps) > 1:
            ps = sorted(ps)
            shared.append(dict(body_ast_sha256=key,projects='|'.join(ps)))
            for p in ps[1:]:
                parents[find(p)] = find(ps[0])
    groups = defaultdict(list)
    for p in projects:
        groups[find(p)].append(p)
    names = {p:'+'.join(ps) for ps in groups.values() for p in ps}
    return names, shared

def allocate(groups, counts, n):
    members = defaultdict(list)
    for p,g in groups.items():
        members[g].append(p)
    if len(members) < n:
        raise ValueError(f'Only {len(members)} independent groups for {n} folds')
    totals = {g:(sum(counts[p][1] for p in ps),sum(sum(counts[p].values()) for p in ps)) for g,ps in members.items()}
    ranked = sorted(members,key=lambda g:(-totals[g][0],-totals[g][1],g))
    fold_totals = [[0,0,0] for _ in range(n)]
    target_positive = max(1,sum(v[0] for v in totals.values())/n)
    target_cases = max(1,sum(v[1] for v in totals.values())/n)
    target_groups = max(1,len(members)/n)
    assignment = {}
    for order,g in enumerate(ranked):
        def cost(f):
            pos,cases,num=fold_totals[f]
            add_pos,add_cases=totals[g]
            return (((pos+add_pos)**2-pos**2)/target_positive**2
                    + ((cases+add_cases)**2-cases**2)/target_cases**2
                    + .25*((num+1)**2-num**2)/target_groups**2, f)
        fold = order if order<n else min(range(n),key=cost)
        assignment[g] = fold
        fold_totals[fold][0] += totals[g][0]; fold_totals[fold][1] += totals[g][1]; fold_totals[fold][2] += 1
    return {p:assignment[g] for p,g in groups.items()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT / 'dataset/v0.1')
    args = parser.parse_args()
    out = args.output; out.mkdir(parents=True,exist_ok=True)
    audit_path = ROOT / 'reports/workflow-audit/audit.json'
    cases_path = ROOT / 'reports/workflow-audit/test_details.csv.gz'
    audit = json.loads(audit_path.read_text())
    freeze_path = ROOT/'reports/evidence-recovery/dataset_freeze_verification.json'
    freeze = json.loads(freeze_path.read_text())
    if freeze['status']!='passed' or freeze['evidence_hashes_sha256']!=file_sha(ROOT/'reports/workflow-audit/evidence_hashes.csv'):
        raise ValueError('Reverify the frozen evidence before export')
    projects = {p['project']:p for p in audit['projects'] if p['status'].startswith('protocol_complete')}
    candidates = defaultdict(list)
    with gzip.open(cases_path,'rt',encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            if r['primary_eligible'] == 'True':
                candidates[r['project']].append(r)
    labels, metadata, body_rows, context_rows, excluded, contexts, source_manifest, summaries, parse_errors = [],[],[],[],[],[],[],[],[]
    fixture_features = ['fixture_autouse_count'] + ['fixture_scope_'+s for s in ('function','class','module','package','session','other')] + ['fixture_dependency_edges']
    context_features = ['fixture_count','helper_count','lifecycle_count'] + fixture_features + ['context_'+s for s in FEATURES]
    for project in sorted(candidates):
        p = projects[project]
        root = SOURCE_ROOT / project
        record = json.loads((root / 'FLAKEXPLAIN_SOURCE_PROVENANCE.json').read_text())
        if record['commit'] != p['commit']:
            raise ValueError('Source/evidence revision differs: '+project)
        pyhash, pycount = verify_sources(root,record)
        source_manifest.append(dict(record,python_tree_sha256=pyhash,python_files=pycount))
        index = SourceIndex(root)
        parse_errors.extend(dict(project=project,**error) for error in index.errors)
        cache = {}
        totals = Counter()
        for r in candidates[project]:
            raw_identity = json.dumps([project,p['commit'],p['environment_id'],r['file'],r['classname'],r['name']],ensure_ascii=False,separators=(',',':'))
            example = digest(raw_identity)
            mapped, status = index.map_test(r)
            if mapped is None:
                excluded.append(dict(example_id=example,project=project,commit=p['commit'],file=r['file'],classname=r['classname'],name=r['name'],label=r['label'],reason=status))
                totals['excluded'] += 1
                totals['excluded_positive'] += r['label'] == 'observed_flaky'
                continue
            fn, cls, collection_path = mapped
            context_id = digest(json.dumps([project,p['commit'],fn.key,cls,collection_path],separators=(',',':')))
            if context_id not in cache:
                context = index.context(fn,cls,collection_path)
                bf = features(fn)
                cf = {k:context[k] for k in ('fixture_count','helper_count','lifecycle_count')}
                fixture_infos = [f.fixture_info() for f,kind in context['nodes'].values() if kind=='fixture']
                cf['fixture_autouse_count'] = sum(info['autouse'] is True for info in fixture_infos)
                for scope in ('function','class','module','package','session'):
                    cf['fixture_scope_'+scope] = sum(info['scope']==scope for info in fixture_infos)
                cf['fixture_scope_other'] = sum(info['scope'] not in ('function','class','module','package','session') for info in fixture_infos)
                cf['fixture_dependency_edges'] = sum(kind=='fixture' and parent!=fn.key for parent,child,kind in context['edges'])
                cf.update({'context_'+k:context['features'].get(k,0) for k in FEATURES})
                body_ast = ast.dump(body_tree(fn),include_attributes=False)
                # Mapping metadata and unresolved references never enter feature columns.
                cm = dict(context_id=context_id,project=project,commit=p['commit'],test_source=fn.key,
                          collection_path=collection_path,collection_class=cls,
                          unresolved_fixture_references=context['unresolved'],bounded=context['bounded'],
                          helper_resolution='named repository functions only; unresolved calls not exhaustively classified',
                          nodes=[dict(source=f.key,kind=kind,start_line=f.node.lineno,end_line=f.node.end_lineno,
                                      file_sha256=f.file_hash,function_sha256=digest(f.text),
                                      fixture_info=f.fixture_info() if kind=='fixture' else None)
                                 for f,kind in sorted(context['nodes'].values(),key=lambda x:x[0].key)],
                          edges=context['edges'])
                contexts.append(cm)
                cache[context_id] = bf,cf,context,body_ast
            bf,cf,context,body_ast = cache[context_id]
            label = int(r['label']=='observed_flaky')
            if not (int(r['pass_count']) > 0 and (int(r['fail_count'])+int(r['error_count'])>0)) == bool(label):
                raise ValueError('Label invariant differs')
            if int(r['skip_count']) or int(r['missing_count']) or int(r['duplicate_rounds']):
                raise ValueError('Incomplete case entered binary cohort')
            label_row = dict(example_id=example,label=label,label_name=r['label'],effective_n=r['effective_n'],
                             pass_count=r['pass_count'],fail_count=r['fail_count'],error_count=r['error_count'],outcomes=r['outcomes'])
            for config in ('original','random','reverse'):
                values = [v for v,filename in zip(r['outcomes'],p['round_order']) if filename.startswith(config+'_')]
                for outcome,code in [('pass','P'),('fail','F'),('error','E')]:
                    label_row[config+'_'+outcome+'_count'] = values.count(code)
            labels.append(label_row)
            metadata.append(dict(example_id=example,project=project,commit=p['commit'],environment_id=p['environment_id'],
                                 membership=p['membership'],junit_file=r['file'],junit_classname=r['classname'],
                                 junit_name=r['name'],parameter_suffix=r['name'][r['name'].find('['):] if '[' in r['name'] else '',
                                 source_path=fn.path,source_qualname=fn.qualname,source_start=fn.node.lineno,source_end=fn.node.end_lineno,
                                 collection_path=collection_path,collection_class=cls,source_file_sha256=fn.file_hash,
                                 source_nodeid=collection_path+'::'+(cls.replace('.','::')+'::' if cls else '')+r['name'],
                                 nodeid_status='derived_from_unique_static_match_not_recorded_collection_log',
                                 source_function_sha256=digest(fn.text),source_family_id=digest(project+'|'+p['commit']+'|'+fn.key),
                                 body_ast_sha256=digest(body_ast),body_statements=bf['statements'],body_ast_nodes=len(list(ast.walk(body_tree(fn)))),
                                 context_id=context_id,unresolved_fixture_count=len(context['unresolved']),context_bounded=int(context['bounded']),
                                 mapping_status=status,evidence_rounds='|'.join(p['round_order'])))
            body_rows.append(dict(example_id=example,**{'body_'+k:v for k,v in bf.items()}))
            context_rows.append(dict(example_id=example,**cf))
            totals['included'] += 1; totals['positive'] += label
            totals['unresolved_fixture_cases'] += bool(context['unresolved'])
            totals['bounded_cases'] += context['bounded']
            totals['with_context'] += bool(context['nodes'])
        summaries.append(dict(project=project,commit=p['commit'],membership=p['membership'],python=p['python'],platform=p['platform'],
                              rounds_original=p['rounds']['original'],rounds_random=p['rounds']['random'],rounds_reverse=p['rounds']['reverse'],candidate_cases=len(candidates[project]),
                              model_cases=totals['included'],observed_flaky=totals['positive'],not_observed_flaky=totals['included']-totals['positive'],
                              source_excluded=totals['excluded'],source_excluded_positive=totals['excluded_positive'],
                              with_context=totals['with_context'],unresolved_fixture_cases=totals['unresolved_fixture_cases'],
                              bounded_cases=totals['bounded_cases'],source_parse_errors=len(index.errors)))
        print(f'{project}: {totals["included"]}/{len(candidates[project])} source-mapped; {totals["positive"]} positives',flush=True)
    if not metadata:
        raise ValueError('No resolved examples')
    all_ids = [set(r['example_id'] for r in table) for table in (labels,metadata,body_rows,context_rows)]
    if not all(s==all_ids[0] and len(s)==len(labels) for s in all_ids):
        raise ValueError('Dataset joins are not one-to-one')
    groups, shared = make_groups(metadata)
    counts = defaultdict(Counter)
    label_by_id = {r['example_id']:r['label'] for r in labels}
    for r in metadata:
        counts[r['project']][label_by_id[r['example_id']]] += 1
    assignment = allocate(groups,counts,5)
    splits = [dict(project=p,project_group=groups[p],outer_test_fold=assignment[p],
                   cases=sum(counts[p].values()),positives=counts[p][1]) for p in sorted(groups)]
    inner = []
    for outer in range(5):
        train_groups = {p:g for p,g in groups.items() if assignment[p]!=outer}
        inner_assignment = allocate(train_groups,counts,4)
        for p in sorted(inner_assignment):
            inner.append(dict(outer_test_fold=outer,project=p,inner_validation_fold=inner_assignment[p],project_group=groups[p]))
    fold_stats = []
    for fold in range(5):
        ps = [p for p in assignment if assignment[p]==fold]
        positives = sum(counts[p][1] for p in ps)
        if positives==0 or sum(r['label'] for r in labels)==positives:
            raise ValueError('Outer split cannot support positive-class evaluation')
        fold_stats.append(dict(fold=fold,projects=ps,cases=sum(sum(counts[p].values()) for p in ps),positives=positives))
    # Declared stratified source-review queue; completion must be recorded separately.
    review = []
    for p in sorted(groups):
        for label in (1,0):
            options = [r for r in metadata if r['project']==p and label_by_id[r['example_id']]==label]
            if options:
                r = min(options,key=lambda r:r['example_id'])
                review.append(dict(example_id=r['example_id'],project=p,label=label,source_path=r['source_path'],
                                   source_qualname=r['source_qualname'],source_start=r['source_start'],context_id=r['context_id'],review_status='pending'))
    tables = [('labels.csv.gz',labels),('metadata.csv.gz',metadata),('features_body.csv.gz',body_rows),
              ('features_context.csv.gz',context_rows),('source_exclusions.csv.gz',excluded),
              ('project_summary.csv',summaries),('splits_outer.csv',splits),('splits_inner.csv',inner),
              ('cross_project_exact_duplicates.csv',shared),('manual_review_queue.csv',review),('source_parse_errors.csv',parse_errors)]
    for name,rows in tables:
        fields = list(rows[0]) if rows else (['body_ast_sha256','projects'] if name.startswith('cross_') else ['project','path','reason'] if name.startswith('source_parse') else ['example_id','reason'])
        csv_write(out/name,rows,fields)
    with (out/'contexts.jsonl.gz').open('wb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz:
        for c in contexts:
            gz.write((json.dumps(c,sort_keys=True,separators=(',',':'))+'\n').encode())
    schema = dict(version=VERSION,join_key='example_id',predictor_tables={
        'features_body.csv.gz':['body_'+k for k in FEATURES],
        'features_context.csv.gz':context_features},
        excluded_from_predictors=['labels.csv.gz','metadata.csv.gz','contexts.jsonl.gz','source_exclusions.csv.gz'],
        bounds=dict(fixture_depth=4,helper_depth=2,context_nodes=32),
        task='Predict observed instability under the recorded multi-order and seed-varying protocol',
        context_completeness='Partial static context; third-party/plugin fixtures and dynamic dispatch can be unresolved',
        label_origin='New execution evidence, not CANNIER released labels',
        duplicate_grouping='Exact AST test bodies with >=3 statements and >=20 AST nodes; shorter common idioms are not grouped. Near-duplicates remain unaudited.',
        source_resolution='Unique named module/class functions and uniquely resolvable inherited methods. Generated functions and doctests without a direct function match are excluded. Derived source node IDs are not original execution-order records.',
        fixture_resolution='Nearest conftest/module/class fixtures, imported repository fixtures, explicit arguments, literal parametrize/usefixtures, autouse and dependencies; pytest_plugins registries, third-party fixture bodies, dynamic collection and dynamic fixture names are not expanded.',
        split_policy='Deterministic greedy project-group allocation minimizing incremental normalized squared imbalance of positive counts, case counts and group counts (weights 1,1,0.25); five outer and four inner folds. No fitted predictors used.')
    (out/'schema.json').write_text(json.dumps(schema,indent=2)+'\n')
    (out/'source_manifest.json').write_text(json.dumps(source_manifest,indent=2)+'\n')
    manifest = dict(version=VERSION,candidate_cases=sum(map(len,candidates.values())),model_cases=len(labels),
                    observed_flaky=sum(r['label'] for r in labels),projects=len(groups),source_families=len({r['source_family_id'] for r in metadata}),
                    contexts=len(contexts),source_exclusions=len(excluded),cross_project_duplicate_bodies=len(shared),folds=fold_stats,
                    inputs={str(p.relative_to(ROOT)):file_sha(p) for p in [audit_path,cases_path,
                        ROOT/'reports/workflow-audit/evidence_hashes.csv',ROOT/'reports/evidence-recovery/identity_resolution_rules.json',
                        freeze_path,ROOT/'scripts/verify_frozen_evidence.py',ROOT/'scripts/dataset_static.py',ROOT/'scripts/prepare_dataset.py',ROOT/'scripts/fetch_dataset_sources.py',ROOT/'scripts/validate_dataset.py']})
    manifest['files'] = {name:file_sha(out/name) for name in sorted([name for name,_ in tables]+['contexts.jsonl.gz','schema.json','source_manifest.json'])}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('model_cases','observed_flaky','projects','source_exclusions','source_families')},indent=2))

if __name__ == '__main__':
    main()
