"""Apply the frozen development representation to a new pinned source tree.

This module never receives labels, observation counts, or JUnit outcomes.
"""
import ast
from dataset_static import features, body_tree, digest, dotted
from prepare_development_features import EXTRA, KIND_STATS, assignments, extra_features

def extract(index, fn, collection_class, collection_path):
    def numeric(f):
        module=index.modules[f.path]['tree']
        cls=index.classes.get((f.path,f.qualname.rpartition('.')[0]))
        return dict(features(f),**extra_features(f.node,module,[cls] if cls else []))
    context=index.context(fn,collection_class,collection_path)
    bf=numeric(fn)
    core={'body_'+k:v for k,v in bf.items()}
    cls=index.classes.get((collection_path,collection_class))
    body=[n for n in cls.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))] if cls else []
    node=ast.Module(body=body,type_ignores=[])
    calls=[dotted(n.func).lower() for n in ast.walk(node) if isinstance(n,ast.Call)]
    state=dict(class_state_assignments=len(assignments(node)),class_state_calls=len(calls),
        class_state_mutable_literals=sum(isinstance(n,(ast.List,ast.Dict,ast.Set)) for n in ast.walk(node)),
        class_state_random_calls=sum(any(t in c.split('.') for t in ('random','randn','randint','seed','randomstate')) for c in calls))
    kinds={k:[] for k in ('fixture','helper','lifecycle')}
    for f,kind in sorted(context['nodes'].values(),key=lambda x:x[0].key): kinds[kind].append(numeric(f))
    values={}
    for kind,functions in kinds.items():
        values[kind+'_count']=len(functions)
        for feature in KIND_STATS:
            values[kind+'_mean_'+feature]=sum(f[feature] for f in functions)/max(1,len(functions))
    values.update(state)
    infos=[f.fixture_info() for f,kind in context['nodes'].values() if kind=='fixture']
    values['fixture_autouse_count']=sum(info['autouse'] is True for info in infos)
    for scope in ('function','class','module','package','session'):
        values['fixture_scope_'+scope]=sum(info['scope']==scope for info in infos)
    values['fixture_scope_other']=sum(info['scope'] not in ('function','class','module','package','session') for info in infos)
    values['fixture_dependency_edges']=sum(kind=='fixture' and parent!=fn.key for parent,child,kind in context['edges'])
    metadata=dict(source_path=fn.path,source_qualname=fn.qualname,source_file_sha256=fn.file_hash,
        body_ast_sha256=digest(ast.dump(body_tree(fn),include_attributes=False)),body_statements=features(fn)['statements'],
        body_ast_nodes=len(list(ast.walk(body_tree(fn)))),unresolved_fixture_count=len(context['unresolved']),
        context_bounded=bool(context['bounded']),context_sources=[dict(source=f.key,kind=kind,sha256=f.file_hash) for f,kind in sorted(context['nodes'].values(),key=lambda x:x[0].key)])
    return core,dict(core,**values),metadata
