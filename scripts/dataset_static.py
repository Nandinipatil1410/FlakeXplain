"""Conservative AST-only test and bounded fixture/helper resolution.

No upstream code is imported. Unresolved dynamic/plugin references stay explicit.
"""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
import tokenize

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        root = dotted(node.value)
        return root + '.' + node.attr if root else node.attr
    return ''

def strings(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [x.strip() for x in node.value.split(',') if x.strip()]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [s for n in node.elts for s in strings(n)]
    return []

@dataclass
class Function:
    path: str
    qualname: str
    node: object
    text: str
    file_hash: str
    fixture_decorator_names: tuple = ('fixture','yield_fixture')

    @property
    def key(self):
        return self.path + '::' + self.qualname

    @property
    def fixture(self):
        for d in self.node.decorator_list:
            base = d.func if isinstance(d, ast.Call) else d
            if dotted(base).split('.')[-1] in self.fixture_decorator_names:
                return d
        return None

    def fixture_info(self):
        d = self.fixture
        info = dict(name=self.node.name, scope='function', autouse=False)
        if isinstance(d, ast.Call):
            for kw in d.keywords:
                if kw.arg in ('name', 'scope', 'autouse'):
                    try:
                        info[kw.arg] = ast.literal_eval(kw.value)
                    except (ValueError, TypeError):
                        info[kw.arg] = 'dynamic'
        return info

def body_tree(fn):
    return ast.Module(body=fn.node.body, type_ignores=[])

FEATURES = ('lines', 'statements', 'calls', 'asserts', 'branches', 'loops',
            'try_blocks', 'raises', 'with_blocks', 'awaits', 'yields', 'imports',
            'globals', 'mutable_literals', 'comprehensions', 'time_calls',
            'random_calls', 'filesystem_calls', 'network_calls', 'mock_calls',
            'process_calls', 'finalizer_calls')

def features(fn):
    tree = body_tree(fn)
    nodes = list(ast.walk(tree))
    calls = [dotted(n.func).lower() for n in nodes if isinstance(n, ast.Call)]
    def count(types):
        return sum(isinstance(n, types) for n in nodes)
    def tokens(parts):
        return sum(any(p in c.split('.') for p in parts) for c in calls)
    vals = [fn.node.end_lineno - fn.node.lineno + 1, count(ast.stmt), len(calls),
            count(ast.Assert), count((ast.If, ast.IfExp)), count((ast.For, ast.AsyncFor, ast.While)),
            count(ast.Try), count(ast.Raise), count((ast.With, ast.AsyncWith)),
            count(ast.Await), count((ast.Yield, ast.YieldFrom)), count((ast.Import, ast.ImportFrom)),
            count((ast.Global, ast.Nonlocal)), count((ast.List, ast.Dict, ast.Set)),
            count((ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)),
            tokens(('time', 'sleep', 'datetime', 'monotonic', 'perf_counter', 'now', 'utcnow')),
            tokens(('random', 'randint', 'choice', 'shuffle', 'seed', 'uuid4')),
            tokens(('open', 'mkdir', 'unlink', 'remove', 'write_text', 'read_text', 'chdir', 'mkstemp')),
            tokens(('socket', 'requests', 'urlopen', 'connect', 'httpx', 'getaddrinfo')),
            tokens(('patch', 'monkeypatch', 'mock', 'magicmock', 'setattr', 'setenv')),
            tokens(('subprocess', 'popen', 'multiprocessing', 'thread', 'start', 'system')),
            tokens(('addfinalizer',))]
    return dict(zip(FEATURES, vals))

class SourceIndex:
    def __init__(self, root):
        self.root = Path(root)
        self.modules, self.functions, self.classes, self.errors = {}, {}, {}, []
        self.fixtures_by_scope = defaultdict(list)
        self.suffixes = defaultdict(set)
        for path in sorted(self.root.rglob('*.py')):
            relative = path.relative_to(self.root).as_posix()
            try:
                with tokenize.open(path) as f:
                    text = f.read()
                tree = ast.parse(text, filename=relative)
            except (SyntaxError, UnicodeError, LookupError, RecursionError) as exc:
                self.errors.append(dict(path=relative, reason=type(exc).__name__))
                continue
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            self.modules[relative] = dict(tree=tree, text=text, imports={})
            tokens = relative[:-3].split('/')
            for start in range(len(tokens)):
                self.suffixes['.'.join(tokens[start:])].add(relative)
            if tokens[-1] == '__init__':
                for start in range(len(tokens)-1):
                    self.suffixes['.'.join(tokens[start:-1])].add(relative)
            for n in tree.body:
                if isinstance(n, ast.Import):
                    for a in n.names:
                        self.modules[relative]['imports'][a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
                elif isinstance(n, ast.ImportFrom):
                    module = n.module or ''
                    if n.level:
                        parent = relative[:-3].split('/')[:-1]
                        if n.level > 1:
                            parent = parent[:-(n.level-1)]
                        module = '.'.join(parent + ([module] if module else []))
                    for a in n.names:
                        self.modules[relative]['imports'][a.asname or a.name] = module + '.' + a.name
            self._scan(relative, tree.body, '', text.splitlines(keepends=True), file_hash)

    def _scan(self, path, body, prefix, lines, file_hash):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = min([n.lineno] + [d.lineno for d in n.decorator_list])
                aliases = tuple(alias for alias,full in self.modules[path]['imports'].items()
                                if full.rpartition('.')[2] in ('fixture','yield_fixture'))
                fn = Function(path, prefix + n.name, n, ''.join(lines[start-1:n.end_lineno]), file_hash,
                              ('fixture','yield_fixture')+aliases)
                self.functions[(path, fn.qualname)] = fn
                if fn.fixture is not None:
                    self.fixtures_by_scope[(path,prefix.rstrip('.'))].append(fn)
            elif isinstance(n, ast.ClassDef):
                self.classes[(path, prefix+n.name)] = n
                self._scan(path, n.body, prefix+n.name+'.', lines, file_hash)

    def symbol(self, path, symbol):
        """Resolve a named symbol only when a unique repository definition exists."""
        if (path, symbol) in self.functions or (path, symbol) in self.classes:
            return path, symbol
        first, *rest = symbol.split('.')
        imp = self.modules[path]['imports'].get(first)
        if imp:
            full = '.'.join([imp] + rest)
            for i in range(len(full.split('.'))-1, 0, -1):
                parts = full.split('.')
                paths = self.suffixes.get('.'.join(parts[:i]), set())
                qual = '.'.join(parts[i:])
                matches = [(p, qual) for p in paths if (p,qual) in self.functions or (p,qual) in self.classes]
                if len(matches) == 1:
                    return matches[0]
        return None

    def method(self, path, cls, name, seen=None):
        seen = set() if seen is None else seen
        if (path,cls) in seen:
            return []
        seen.add((path,cls))
        fn = self.functions.get((path, cls+'.'+name))
        if fn:
            return [fn]
        node = self.classes.get((path,cls))
        found = []
        for b in node.bases if node else []:
            target = self.symbol(path, dotted(b))
            if target:
                found.extend(self.method(*target, name, seen.copy()))
        # Multiple inheritance with competing implementations is ambiguous here.
        return list({x.key:x for x in found}.values())

    def map_test(self, row):
        classname = row['classname']
        name = row['name'].split('[', 1)[0]
        parts = classname.split('.')
        matches = []
        for i in range(len(parts), 0, -1):
            paths = self.suffixes.get('.'.join(parts[:i]), set())
            cls = '.'.join(parts[i:])
            for path in paths:
                if cls:
                    matches.extend((fn, cls, path) for fn in self.method(path, cls, name))
                elif (path,name) in self.functions:
                    matches.append((self.functions[(path,name)], '', path))
            if matches:
                break
        unique = {(fn.key,cls,p):(fn,cls,p) for fn,cls,p in matches}
        if len(unique) == 1:
            return next(iter(unique.values())), 'unique_static_function'
        return None, 'ambiguous_source' if unique else 'unresolved_or_generated_or_doctest'

    def context(self, fn, collection_class, collection_path, max_nodes=32):
        """Fixtures depth<=4; direct named helpers depth<=2, at most32 unique nodes."""
        applicable = []
        path = Path(collection_path)
        ancestors = list(reversed(path.parent.parents)) + [path.parent]
        for parent in ancestors:
            p = (parent / 'conftest.py').as_posix()
            if p in self.modules:
                applicable.append((p, ''))
        applicable.append((collection_path, ''))
        if collection_class:
            # Base fixtures are considered only for uniquely resolved base classes.
            def bases(p, cls, seen):
                if (p,cls) in seen:
                    return
                seen.add((p,cls))
                node = self.classes.get((p,cls))
                for base in node.bases if node else []:
                    target = self.symbol(p, dotted(base))
                    if target:
                        bases(*target, seen)
                applicable.append((p,cls+'.'))
            bases(collection_path, collection_class, set())
        fixtures = {}
        autouse_names = set()
        marks = []
        for p, prefix in applicable:
            for f in self.fixtures_by_scope[(p,prefix.rstrip('.'))]:
                fixtures[f.fixture_info()['name']] = f
                if f.fixture_info()['autouse'] is True:
                    autouse_names.add(f.fixture_info()['name'])
            if not prefix:
                for alias in self.modules[p]['imports']:
                    target = self.symbol(p,alias)
                    if target and target in self.functions:
                        f = self.functions[target]
                        if f.fixture is not None:
                            fixtures[alias] = f
                            if f.fixture_info()['autouse'] is True:
                                autouse_names.add(alias)
            tree = self.modules[p]['tree'] if not prefix else self.classes.get((p,prefix[:-1]))
            if tree:
                marks.extend(getattr(tree, 'decorator_list', []))
                for n in tree.body:
                    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'pytestmark' for t in n.targets):
                        marks.extend(n.value.elts if isinstance(n.value,(ast.List,ast.Tuple)) else [n.value])
        marks.extend(fn.node.decorator_list)
        params, usefixtures = set(), []
        for d in marks:
            if isinstance(d, ast.Call):
                kind = dotted(d.func).split('.')[-1]
                if kind == 'parametrize' and d.args:
                    indirect = next((k.value for k in d.keywords if k.arg == 'indirect'), None)
                    direct = set(strings(d.args[0]))
                    if isinstance(indirect, ast.Constant) and indirect.value is True:
                        direct = set()
                    elif indirect is not None:
                        direct -= set(strings(indirect))
                    params.update(direct)
                elif kind == 'usefixtures':
                    usefixtures += [s for a in d.args for s in strings(a)]
        defaults = {a.arg for a in fn.node.args.args[-len(fn.node.args.defaults):]} if fn.node.args.defaults else set()
        defaults.update(a.arg for a,d in zip(fn.node.args.kwonlyargs,fn.node.args.kw_defaults) if d is not None)
        required = [a.arg for a in fn.node.args.args + fn.node.args.kwonlyargs if a.arg not in {'self','cls'} | params | defaults]
        required += usefixtures + sorted(autouse_names)
        selected, unresolved, edges, bounded = {}, set(), [], False
        def add_fixture(name, parent, depth, stack):
            nonlocal bounded
            if name == 'request':
                return
            f = fixtures.get(name)
            if not f:
                unresolved.add('fixture:'+name)
                return
            edges.append((parent, f.key, 'fixture'))
            if f.key in stack:
                unresolved.add('fixture_cycle_or_override:'+name)
                return
            if f.key in selected:
                return
            if depth > 4 or len(selected) >= max_nodes:
                bounded = True
                return
            selected[f.key] = (f,'fixture')
            for a in f.node.args.args + f.node.args.kwonlyargs:
                if a.arg not in ('self','cls'):
                    add_fixture(a.arg, f.key, depth+1, stack | {f.key})
        for name in sorted(set(required)):
            add_fixture(name, fn.key, 1, set())
        # Pytest xunit and unittest lifecycle methods execute outside the test body.
        lifecycle = []
        for name in ('setup_module','teardown_module','setup_function','teardown_function'):
            if (collection_path,name) in self.functions:
                lifecycle.append(self.functions[(collection_path,name)])
        if collection_class:
            for name in ('setup_method','teardown_method','setup_class','teardown_class',
                         'setUp','tearDown','setUpClass','tearDownClass'):
                opts = self.method(collection_path,collection_class,name)
                if len(opts) == 1:
                    lifecycle.extend(opts)
        for f in lifecycle:
            if len(selected) >= max_nodes:
                bounded = True
                break
            selected.setdefault(f.key,(f,'lifecycle'))
            edges.append((fn.key,f.key,'lifecycle'))
        def helpers(f, depth):
            nonlocal bounded
            # A local binding can shadow a module helper. Do not resolve it globally.
            locals_ = {a.arg for a in f.node.args.args+f.node.args.kwonlyargs+f.node.args.posonlyargs}
            for item in ast.walk(body_tree(f)):
                if isinstance(item,ast.Name) and isinstance(item.ctx,ast.Store):
                    locals_.add(item.id)
            for n in ast.walk(body_tree(f)):
                if not isinstance(n, ast.Call):
                    continue
                sym = dotted(n.func)
                target = None
                if sym.startswith(('self.','cls.')):
                    cls = f.qualname.rpartition('.')[0]
                    opts = self.method(f.path, cls, sym.split('.',1)[1])
                    if len(opts) == 1:
                        target = (opts[0].path, opts[0].qualname)
                elif sym and sym.split('.')[0] not in locals_:
                    target = self.symbol(f.path, sym)
                if not target or target not in self.functions:
                    continue
                h = self.functions[target]
                if h.key == fn.key or h.fixture is not None:
                    continue
                edges.append((f.key,h.key,'helper'))
                if h.key in selected:
                    continue
                if depth > 2 or len(selected) >= max_nodes:
                    bounded = True
                    continue
                selected[h.key] = (h,'helper')
                helpers(h, depth+1)
        helpers(fn, 1)
        for f,kind in list(selected.values()):
            if kind in ('fixture','lifecycle'):
                helpers(f,1)
        # Detect request.getfixturevalue: string-literal and dynamic alike remain explicit.
        for f in [fn] + [v[0] for v in selected.values()]:
            if any(isinstance(n,ast.Call) and dotted(n.func).endswith('.getfixturevalue') for n in ast.walk(body_tree(f))):
                unresolved.add('dynamic_getfixturevalue')
        aggregate = Counter()
        for f,kind in selected.values():
            aggregate.update(features(f))
        return dict(nodes=selected, edges=sorted(set(edges)), unresolved=sorted(unresolved), bounded=bounded,
                    features=dict(aggregate), fixture_count=sum(k=='fixture' for _,k in selected.values()),
                    helper_count=sum(k=='helper' for _,k in selected.values()),
                    lifecycle_count=sum(k=='lifecycle' for _,k in selected.values()))
