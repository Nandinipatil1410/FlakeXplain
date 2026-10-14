"""Join released CANNIER measurements to pinned, statically resolved context.

Never execute upstream code or load pickle files. Verify SQLite/NumPy alignment.
"""
import ast,gc,json,sqlite3
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from dataset_static import SourceIndex,body_tree,digest
from confirmation_features import extract
from prepare_dataset import make_groups,allocate,verify_sources
from train_pilot import ROOT,sha,reader,write_csv

LOCAL=ROOT/'local-evidence/cannier-matched-v0.4'
OUT=ROOT/'reports/cannier-matched-v0.4'
DATA=ROOT/'dataset/cannier-matched-v0.4'
TASKS={'NOD-vs-Rest':3,'Victim-vs-Rest':4}

def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'protocol.json').exists():raise ValueError('Do not overwrite frozen protocol')
    protocol=dict(created_utc=datetime.now(timezone.utc).isoformat(),stage='Retrospective matched baseline ablation on authors released corpus; same projects influenced earlier development, not untouched external confirmation',
        authors_archive_sha256='07d714a7e0f57863070d1ba6631191aa6e856fac1ad3ffc92765d6c1fc56f9f1',authors_archive_bytes=354333950,
        authors_revision='b96d6ed02e98d514eb6a92ca264a082234cb9728',framework_revision='89c74c27847474248b581b428aed2b417141296e',plugin_revision='2d58145c2786477a721c754e3a05639017c080d4',
        tasks=list(TASKS),task_status='Both tasks prespecified; report both, no choosing a winner after results',
        baseline='Actual released 18 static/dynamic features, first stored feature measurement per case chosen independently of outcomes. Original author NOD and victim targets preserved.',
        extension='Same 18 measurements plus frozen v0.2 66 additional context counts. No revised core/body features added. Existing source-only extractor unchanged.',
        matching='Read-only SQLite item IDs and nodeids; verify every original item array row and all 30 feature measurements against SQLite. Only unique exact source/class method matches; audit all exclusions and original labels.',
        cohort='Identical source-mapped finite-feature examples for baseline and context. Retain zero-positive projects. Do not merge author labels with our 25-round labels.',
        primary_balance='Natural observed imbalance; no synthetic cases, undersampling or class weighting.',
        sensitivity_balance='Separately labelled author-SMOTE replication sensitivity, training partitions only, default k_neighbors=5, natural held-out cases. This is an explicitly analysed experimental variable, not primary rebalance.',
        classifiers={'NOD-vs-Rest':{'family':'ExtraTrees','n_estimators':100},'Victim-vs-Rest':{'family':'ExtraTrees','n_estimators':75}},
        common_parameters=dict(max_depth=None,min_samples_leaf=1,max_features='sqrt',bootstrap=False,class_weight=None,n_jobs=4),
        random_seed=20261014,outer_folds=5,inner_folds=4,
        splits='Project-disjoint five folds; join projects sharing substantive exact body ASTs (>=3 statements and >=20 AST nodes); allocate on union NOD/victim counts. Four inner project folds for thresholds only; no hyperparameter search.',
        primary_metrics='Signed MCC at fixed 0.5 and average precision; paired context-minus-baseline differences for both tasks. Project-level uncertainty, no selective winner or paper-superiority claim.',
        secondary_metrics='Inner-OOF maximum signed-MCC thresholds (highest threshold tie), precision/recall/F1/false positives per 1000 negatives, separately ranked per-project top-10% budget, family weighting.',
        software='New isolated pinned scikit-learn 1.7.2 environment; authors used 1.0.2. Protocol and software adaptations disclosed; original released predictions evaluated separately without refitting.',
        original_reference='Recompute signed MCC and AP from the authors 30 released predictions at feature sample size 1 on their full original task domains. Derived AP is not a score printed in the paper.',
        metric_correction='Authors get_mcc returns absolute MCC. New analyses use signed sklearn MCC; export both for released-score verification, do not hide negative correlation.',
        feature_name_correction='SQLite/plugin put External Modules at index12 and Assertions at index13; framework FEATURE_NAMES reverses these labels. Preserve numeric order and use SQLite column names; neither column is exchanged.',
        incomplete_claims='No new independent positive projects, faithful full hybrid detector rerun, causal confirmation or measured rerun savings supplied by this retrospective comparison.',
        source_inputs={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'scripts/prepare_cannier_matched.py',ROOT/'scripts/confirmation_features.py',ROOT/'scripts/dataset_static.py',ROOT/'scripts/prepare_development_features.py',ROOT/'cannier-replication/subjects.json']})
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    print('Matched comparison protocol frozen:',sha(OUT/'protocol.json'),flush=True)

def prepare():
    DATA.mkdir(parents=True,exist_ok=True)
    if (DATA/'manifest.json').exists():raise ValueError('Matched dataset already frozen')
    protocol=json.loads((OUT/'protocol.json').read_text())
    for name,value in protocol['source_inputs'].items():
        if sha(ROOT/name)!=value:raise ValueError('Frozen source input changed: '+name)
    if sha(LOCAL/'authors-output.zip')!=protocol['authors_archive_sha256']:raise ValueError('Author archive checksum mismatch')
    items=np.load(LOCAL/'output/items.npy',allow_pickle=False);features=np.load(LOCAL/'output/features.npy',mmap_mode='r',allow_pickle=False)
    subjects=json.loads((ROOT/'cannier-replication/subjects.json').read_text());records={r['repository']:r for r in json.loads((LOCAL/'source_records.json').read_text())}
    context_columns=json.loads((ROOT/'dataset/development-v0.2/schema.json').read_text())['context_columns']
    metadata=[];labels=[];baseline=[];contexts=[];excluded=[];summaries=[];source_checks=[];offset=0;feature_columns=None
    for pid,(repo,(commit,*_)) in enumerate(subjects.items()):
        slug=repo.split('/')[-1];project=slug.lower().replace('-','_');record=records[repo]
        if record['commit']!=commit:raise ValueError('Wrong source revision')
        root=ROOT/record['source'];tree_hash,pyfiles=verify_sources(root,record)
        source_checks.append(dict(project=project,commit=commit,tree_sha256=tree_hash,files=pyfiles))
        con=sqlite3.connect((LOCAL/'output/volume'/(slug+'.sqlite3')).resolve().as_uri()+'?mode=ro',uri=True)
        selected=con.execute('select id,nodeid,n_fail_baseline,n_fail_shuffle from item where n_runs_features=30 and n_runs_baseline=2500 and n_runs_shuffle=2500').fetchall()
        indexes={r[0]:i for i,r in enumerate(selected)};polluters={r[0] for r in con.execute('select distinct polluter_id from dependency')}
        expected=np.asarray([[pid,a,b,int(0<a<2500),int(not 0<a<2500 and a!=b),int(a<2500 and b>0),int(i in polluters)] for i,node,a,b in selected])
        actual=items[offset:offset+len(selected)]
        if not np.array_equal(expected,actual):raise ValueError('Released item rows do not align with SQLite: '+slug)
        names=[r[1] for r in con.execute('pragma table_info(features)')][1:]
        if feature_columns is None:feature_columns=names
        if names!=feature_columns:raise ValueError('Feature schema differs by subject')
        count=Counter();feature_rows_verified=0
        for r in con.execute('select * from features'):
            if r[0] not in indexes:continue
            i=indexes[r[0]];j=count[i];count[i]+=1
            if j>=30 or not np.array_equal(np.asarray(r[1:]),features[offset+i,j],equal_nan=True):raise ValueError('Released feature row mismatch: '+slug)
            feature_rows_verified+=1
        if any(count[i]!=30 for i in range(len(selected))):raise ValueError('Feature measurements incomplete')
        con.close();index=SourceIndex(root);cache={};included=Counter();reasons=Counter()
        for i,(item,nodeid,a,b) in enumerate(selected):
            rowindex=offset+i;eid=digest('cannier-release|'+repo+'|'+commit+'|'+str(item)+'|'+nodeid)
            parts=nodeid.split('[',1)[0].split('::');path=parts[0];method=parts[-1];cls='.'.join(parts[1:-1]);mapped=[]
            resolution='exact_repository_path'
            if path not in index.modules:
                suffixes=[p for p in index.modules if p.endswith('/'+path)]
                if len(suffixes)==1:path=suffixes[0];resolution='unique_subdirectory_relative_path'
            if cls:mapped=index.method(path,cls,method)
            elif (path,method) in index.functions:mapped=[index.functions[(path,method)]]
            reason=''
            if len(mapped)!=1:reason='source_ambiguous' if mapped else 'source_unresolved_or_generated'
            elif not np.isfinite(features[rowindex,0]).all():reason='nonfinite_first_feature_measurement'
            if reason:
                excluded.append(dict(example_id=eid,project=project,nodeid=nodeid,original_row=rowindex,nod=int(actual[i,3]),victim=int(actual[i,4]),reason=reason));reasons[reason]+=1;continue
            fn=mapped[0];key=(fn.key,cls,path)
            if key not in cache:cache[key]=extract(index,fn,cls,path)
            core,extended,source=cache[key]
            metadata.append(dict(example_id=eid,project=project,repository=repo,commit=commit,item_id=item,nodeid=nodeid,original_row=rowindex,
                source_path=fn.path,source_qualname=fn.qualname,collection_class=cls,collection_path=path,path_resolution=resolution,source_file_sha256=fn.file_hash,
                source_family_id=digest(repo+'|'+commit+'|'+fn.key),body_ast_sha256=source['body_ast_sha256'],body_statements=source['body_statements'],body_ast_nodes=source['body_ast_nodes'],
                unresolved_fixture_count=source['unresolved_fixture_count'],context_bounded=source['context_bounded']))
            labels.append(dict(example_id=eid,nod=int(actual[i,3]),victim=int(actual[i,4]),nod_victim_domain=int(actual[i,5]),polluter=int(actual[i,6])))
            baseline.append(dict(example_id=eid,**dict(zip(names,features[rowindex,0]))))
            contexts.append(dict(example_id=eid,**{k:extended[k] for k in context_columns}))
            included['cases']+=1;included['nod']+=int(actual[i,3]);included['victim']+=int(actual[i,4]);included['polluter']+=int(actual[i,6])
        summaries.append(dict(project=project,commit=commit,released_cases=len(selected),mapped_cases=included['cases'],nod=included['nod'],victim=included['victim'],polluter=included['polluter'],exclusions=sum(reasons.values()),feature_rows_verified=feature_rows_verified,source_parse_errors=len(index.errors)))
        offset+=len(selected);print(slug+': '+str(dict(summaries[-1])),flush=True);del index;gc.collect()
    if offset!=len(items):raise ValueError('Not all released rows were joined')
    groups,duplicates=make_groups(metadata);counts=defaultdict(Counter);lab={r['example_id']:r for r in labels}
    for r in metadata:counts[r['project']][int(bool(lab[r['example_id']]['nod'] or lab[r['example_id']]['victim']))]+=1
    outer=allocate(groups,counts,5);splits=[dict(project=p,project_group=groups[p],outer_fold=outer[p]) for p in sorted(groups)];inner=[]
    for fold in range(5):
        assignment=allocate({p:g for p,g in groups.items() if outer[p]!=fold},counts,4)
        inner.extend(dict(outer_fold=fold,project=p,inner_fold=f) for p,f in sorted(assignment.items()))
    for name,rows in [('metadata.csv.gz',metadata),('labels.csv.gz',labels),('features_baseline.csv.gz',baseline),('features_context.csv.gz',contexts),('source_exclusions.csv.gz',excluded),('project_summary.csv',summaries),('splits_outer.csv',splits),('splits_inner.csv',inner),('cross_project_exact_duplicates.csv',duplicates)]:
        write_csv(DATA/name,rows,list(rows[0]) if rows else ['body_ast_sha256','projects'])
    (DATA/'schema.json').write_text(json.dumps(dict(baseline_columns=feature_columns,context_columns=context_columns,excluded_predictors=['nodeid','project','labels','run counts','failure counts','source IDs']),indent=2)+'\n')
    manifest=dict(status='prepared',cases=len(labels),released_cases=len(items),nod=sum(r['nod'] for r in labels),victim=sum(r['victim'] for r in labels),projects=len(summaries),protocol_sha256=sha(OUT/'protocol.json'),source_checks=source_checks,author_archive_sha256=protocol['authors_archive_sha256'],extractor_sha256=sha(ROOT/'scripts/prepare_cannier_matched.py'),files={p.name:sha(p) for p in DATA.iterdir() if p.is_file()})
    (DATA/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:manifest[k] for k in ('cases','released_cases','nod','victim','projects')}),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','prepare']);globals()[p.parse_args().action]()
