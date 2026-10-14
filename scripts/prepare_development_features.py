"""Label-blind bounded representation revision, preserving dataset v0.1 cases.

Read pinned source ASTs and frozen context references only. No subject imports,
outcome labels, JUnit evidence, source strings or project IDs become predictors.
"""
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import tokenize
from types import SimpleNamespace
from dataset_static import FEATURES, dotted, features
from train_pilot import ROOT, reader, sha, write_csv

OUT=ROOT/'dataset/development-v0.2'
EXTRA=('unittest_asserts','attribute_writes','subscript_writes','mutable_ops','cleanup_calls','blocking_calls','module_shared_reads','class_shared_reads')
KIND_STATS=('lines','calls','asserts','yields','time_calls','random_calls','filesystem_calls','network_calls','mock_calls','process_calls','finalizer_calls')+EXTRA[:6]

def assignments(node):
    return [n for n in ast.walk(node) if isinstance(n,(ast.Assign,ast.AnnAssign,ast.AugAssign))]

def source_nodes(path):
    with tokenize.open(path) as f:
        tree=ast.parse(f.read())
    functions={}; classes={}
    def visit(body,prefix=''):
        for n in body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                functions[prefix+n.name]=n
            elif isinstance(n,ast.ClassDef):
                classes[prefix+n.name]=n
                visit(n.body,prefix+n.name+'.')
    visit(tree.body)
    return tree,functions,classes

def extra_features(node,module,class_nodes):
    body=ast.Module(body=node.body,type_ignores=[])
    nodes=list(ast.walk(body)); calls=[dotted(n.func).split('.')[-1].lower() for n in nodes if isinstance(n,ast.Call)]
    targets=[]
    for n in assignments(body):
        targets.extend(n.targets if isinstance(n,ast.Assign) else [n.target])
    global_names={t.id for n in module.body if isinstance(n,(ast.Assign,ast.AnnAssign))
                  for target in (n.targets if isinstance(n,ast.Assign) else [n.target]) for t in ast.walk(target) if isinstance(t,ast.Name)}
    class_names={t.id for c in class_nodes for n in c.body if isinstance(n,(ast.Assign,ast.AnnAssign))
                 for target in (n.targets if isinstance(n,ast.Assign) else [n.target]) for t in ast.walk(target) if isinstance(t,ast.Name)}
    values=[sum(c.startswith('assert') for c in calls),
            sum(isinstance(t,ast.Attribute) for target in targets for t in ast.walk(target)),
            sum(isinstance(t,ast.Subscript) for target in targets for t in ast.walk(target)),
            sum(c in ('append','extend','update','clear','pop','discard','setdefault','remove') for c in calls),
            sum(c in ('close','unlink','rmdir','remove','reset','restore','stop','join','terminate','cleanup') for c in calls),
            sum(c in ('sleep','wait','join','acquire','communicate') for c in calls),
            sum(isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) and n.id in global_names for n in nodes),
            sum(isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Load) and n.attr in class_names for n in nodes)]
    return dict(zip(EXTRA,values))

def code_tokens(node,limit):
    """AST vocabulary excludes comments/docstrings, literal values, signatures/names."""
    tokens=[]
    def add(value):
        value=re.sub(r'([a-z])([A-Z])',r'\1_\2',value).lower()
        for word in re.findall(r'[a-z][a-z0-9]*',value):
            if word not in ('flaky','flakiness','xfail','xpass'):
                tokens.append('id_'+word)
    def visit(n):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            for item in n.body:
                visit(item)
            return
        if isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):
            return
        tokens.append('ast_'+type(n).__name__.lower())
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            return
        if isinstance(n,ast.Constant):
            tokens.append('literal_'+type(n.value).__name__.lower())
            return
        if isinstance(n,ast.Name):
            add(n.id)
        elif isinstance(n,ast.Attribute):
            add(n.attr)
        for child in ast.iter_child_nodes(n):
            visit(child)
    visit(node)
    return ' '.join(tokens[:limit])

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'manifest.json').exists():
        raise ValueError('Do not overwrite a frozen development feature export')
    dataset=ROOT/'dataset/v0.1'
    original=json.loads((dataset/'manifest.json').read_text())
    for name in ('metadata.csv.gz','contexts.jsonl.gz','features_body.csv.gz','features_context.csv.gz','source_manifest.json'):
        if sha(dataset/name)!=original['files'][name]:
            raise ValueError('Frozen source input differs: '+name)
    records={r['project']:r for r in json.loads((dataset/'source_manifest.json').read_text())}
    metadata=list(reader(dataset/'metadata.csv.gz'))
    by_context={r['context_id']:r for r in metadata}
    cache={}; verified={}; function_cache={}
    def get(project,path):
        key=(project,path)
        if key not in cache:
            source=ROOT/records[project]['source']/path
            cache[key]=source_nodes(source); verified[key]=sha(source)
        return cache[key]
    def get_fn(project,path,qualname):
        key=(project,path,qualname)
        if key not in function_cache:
            tree,functions,classes=get(project,path)
            node=functions[qualname]
            cls=classes.get(qualname.rpartition('.')[0])
            ex=extra_features(node,tree,[cls] if cls else [])
            fs=features(SimpleNamespace(node=node)); fs.update(ex)
            function_cache[key]=(node,fs)
        return function_cache[key]
    body_extra={}; context_values={}; documents=[]; audits=[]
    with gzip.open(dataset/'contexts.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            context=json.loads(line); cid=context['context_id']; r=by_context[cid]; project=r['project']
            node,fs=get_fn(project,r['source_path'],r['source_qualname'])
            if verified[(project,r['source_path'])]!=r['source_file_sha256']:
                raise ValueError('Test source hash differs')
            tree,_,classes=get(project,context['collection_path'])
            cls=classes.get(context['collection_class']); class_body=[n for n in cls.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))] if cls else []
            class_ast=ast.Module(body=class_body,type_ignores=[])
            class_calls=[dotted(n.func).lower() for n in ast.walk(class_ast) if isinstance(n,ast.Call)]
            state=dict(class_state_assignments=len(assignments(class_ast)),class_state_calls=len(class_calls),
                       class_state_mutable_literals=sum(isinstance(n,(ast.List,ast.Dict,ast.Set)) for n in ast.walk(class_ast)),
                       class_state_random_calls=sum(any(t in c.split('.') for t in ('random','randn','randint','seed','randomstate')) for c in class_calls))
            kinds={k:[] for k in ('fixture','helper','lifecycle')}; texts=[]
            for entry in context['nodes']:
                path,qual=entry['source'].split('::',1); n,values=get_fn(project,path,qual)
                if verified[(project,path)]!=entry['file_sha256']:
                    raise ValueError('Context source hash differs')
                kinds[entry['kind']].append(values)
                texts.append('kind_'+entry['kind']+' '+code_tokens(n,1000))
            values={}
            for kind,functions in kinds.items():
                values[kind+'_count']=len(functions)
                for feature in KIND_STATS:
                    values[kind+'_mean_'+feature]=sum(fn[feature] for fn in functions)/max(1,len(functions))
            values.update(state)
            body_extra[cid]={'body_'+k:fs[k] for k in EXTRA}
            context_values[cid]=values
            documents.append(dict(context_id=cid,body=code_tokens(node,2000),context=' '.join(texts).split()))
            documents[-1]['context']=' '.join(documents[-1]['context'][:4000])
            audits.append(dict(context_id=cid,project=project,class_state_present=bool(class_body),
                               unresolved_candidates=len(context['unresolved_fixture_references']),bounded=context['bounded']))
            if len(documents)%10000==0:
                print(f'{len(documents)} contexts extracted without labels',flush=True)
    # Join by frozen ID; original fixture scope columns stay source-derived.
    body_original={r['example_id']:r for r in reader(dataset/'features_body.csv.gz')}
    context_original={r['example_id']:r for r in reader(dataset/'features_context.csv.gz')}
    scope_columns=['fixture_autouse_count']+['fixture_scope_'+s for s in ('function','class','module','package','session','other')]+['fixture_dependency_edges']
    body_rows=[]; context_rows=[]
    for r in metadata:
        cid=r['context_id']; key=r['example_id']
        body_rows.append(dict(body_original[key],**body_extra[cid]))
        context_rows.append(dict(example_id=key,**context_values[cid],**{k:context_original[key][k] for k in scope_columns}))
    write_csv(OUT/'features_body.csv.gz',body_rows,list(body_rows[0]))
    write_csv(OUT/'features_context.csv.gz',context_rows,list(context_rows[0]))
    local=ROOT/'local-evidence/development-v0.2'; local.mkdir(parents=True,exist_ok=True)
    with gzip.open(local/'source_documents.jsonl.gz','wt',encoding='utf-8') as f:
        for document in documents:
            f.write(json.dumps(document,separators=(',',':'))+'\n')
    write_csv(OUT/'extraction_audit.csv.gz',audits,list(audits[0]))
    schema=dict(body_columns=list(body_rows[0])[1:],context_columns=list(context_rows[0])[1:],
                changes='Framework-aware assertions/mutations, separate means by context kind and class-state initialization; original labels, cases, context graph and folds unchanged.',
                text='AST tokens only; no comments/docstrings, literal values, function/class signatures, file paths, test names or direct flaky/xfail words. 2000 body and 4000 context tokens maximum.',
                unresolved='No new plugin/override graph resolution in this bounded revision; existing gaps remain explicit.',
                predictors='Only numeric allowlists or transformed AST text; example_id/context_id used only for joining.')
    (OUT/'schema.json').write_text(json.dumps(schema,indent=2)+'\n')
    manifest=dict(status='completed',stage='development revision after inspected pilot; not untouched confirmation',cases=len(metadata),contexts=len(documents),
                  source_files_checked=len(verified),dataset_manifest_sha256=sha(dataset/'manifest.json'),
                  source_documents=str((local/'source_documents.jsonl.gz').relative_to(ROOT)),source_documents_sha256=sha(local/'source_documents.jsonl.gz'),
                  extractor_sha256=sha(Path(__file__)),files={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()},
                  class_state_contexts=sum(r['class_state_present'] for r in audits))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('cases','contexts','source_files_checked','class_state_contexts')},indent=2))

if __name__=='__main__':
    main()
