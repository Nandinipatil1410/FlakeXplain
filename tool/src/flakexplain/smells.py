"""Vendored verbatim from scripts/mdflaker_v08_smells.py; keep the two in sync.

Clean-room reimplementation of MDFlaker's "Test Smells" and "Test Size" factors.

Mirrors F_Detector/get_test_smells.py (test_smell_runner, get_size) and dependency_analysis.get_call
of SoftwareImpacts/SIMPAC-2025-241@5b63f3a (Apache-2.0), including their quirks: get_call returns
None for nested attribute chains, smells are counted per test-method AST, and the factor is the sum
of all smell counts. Upstream code is read as a specification only; it is never imported or run.
"""
import ast

def get_call_name(node):
    if not isinstance(node,ast.Call):return None
    f=node.func
    if isinstance(f,ast.Name):return f.id
    if isinstance(f,ast.Attribute) and isinstance(f.value,ast.Name):return f.attr
    return None

def get_call(node):
    if not isinstance(node,ast.Call):return None
    f=node.func
    if isinstance(f,ast.Name):return f.id
    if isinstance(f,ast.Attribute) and isinstance(f.value,ast.Name):return f.value.id+'.'+f.attr
    return None

class _V(ast.NodeVisitor):
    def __init__(self):self.count=0
    def done(self,node):pass

class Sleep(_V):
    def visit_Call(self,n):
        c=get_call_name(n)
        if c and 'sleep' in c:self.count+=1
        self.generic_visit(n)

class Waiting(_V):
    def visit_Call(self,n):
        c=get_call_name(n)
        if c and 'wait' in c:self.count+=1
        self.generic_visit(n)

class Timeout(_V):
    def visit_Call(self,n):
        c=get_call_name(n)
        if c and 'timeout' in c:self.count+=1
        self.count+=sum(isinstance(a,ast.Name) and 'timeout' in a.id for a in n.args)
        self.count+=sum(isinstance(k.arg,str) and 'timeout' in k.arg for k in n.keywords)
        self.generic_visit(n)

class WithSeed(_V):
    def visit_FunctionDef(self,n):
        for d in n.decorator_list:
            if isinstance(d,ast.Call) and isinstance(d.func,ast.Name) and 'with_seed' in d.func.id and d.args:self.count+=1
        self.generic_visit(n)
    visit_AsyncFunctionDef=visit_FunctionDef

class RandomWithoutSeed(_V):
    def __init__(self):super().__init__();self.seed=False
    def visit_Call(self,n):
        c=get_call(n)
        if c and 'seed' in c:self.seed=True
        if c and 'random' in c and not self.seed:self.count+=1  # upstream keyword check never fires (isinstance(keyword,str))
        self.generic_visit(n)

class Url(_V):
    def visit_Assign(self,n):
        self.count+=sum(isinstance(t,ast.Name) and t.id=='url' for t in n.targets)
        self.generic_visit(n)
    def visit_Call(self,n):
        for m in ast.walk(n):
            if isinstance(m,ast.keyword) and m.arg=='url':self.count+=1
            elif isinstance(m,ast.Name) and m.id=='url':self.count+=1
            elif isinstance(m,ast.Constant) and isinstance(m.value,str) and any(s in m.value for s in ('http','https','www.','.org','.com')):self.count+=1
        self.generic_visit(n)

class Socket(_V):
    def visit_Call(self,n):
        if get_call(n) in ('socket.connect','socket.settimeout','socket.gethostbyname'):self.count+=1
        self.generic_visit(n)

class AssertCalledWith(_V):
    def visit_Call(self,n):
        c=get_call(n)
        if c and 'assert_called_with' in c:self.count+=1
        self.generic_visit(n)

OS_DIR=['os.chdir','os.chroot','os.makedirs','os.listdir','os.mkdir','os.mkfifo','os.open','os.pathconf','os.remove','os.removedirs','os.rmdir','os.unlink']

class NotCheckExistence(_V):
    def __init__(self):
        super().__init__();self.f=dict(open_found=False,open_with_try=False,with_open=False,temp_cwd=False,with_mkdir=False,
            bare_mkdir=False,os_dir_try=False,os_dir_no_try=False,exists=False)
    def visit_Try(self,n):
        for m in ast.walk(n):
            c=get_call(m) if isinstance(m,ast.Call) else None
            if c and 'open' in c:self.f['open_with_try']=True
            if c and c in OS_DIR:self.f['os_dir_try']=True
        self.generic_visit(n)
    def visit_With(self,n):
        for m in ast.walk(n):
            if isinstance(m,ast.Call):
                c=get_call(m)
                if c and 'mkdir' in c:self.f['with_mkdir']=True
            elif isinstance(m,ast.withitem):
                for k in ast.walk(m):
                    c=get_call(k) if isinstance(k,ast.Call) else None
                    if c and 'open' in c:self.f['with_open']=True
        self.generic_visit(n)  # upstream get_call(With) is always None, so temp_cwd never set
    def visit_Call(self,n):
        c=get_call(n)
        if c:
            if 'open' in c:self.f['open_found']=True
            if c=='mkdir':self.f['bare_mkdir']=True
            if c in OS_DIR:self.f['os_dir_no_try']=True
            if 'exists' in c:self.f['exists']=True
        self.generic_visit(n)
    def done(self,node):
        f=self.f
        if f['open_found'] and not f['open_with_try'] and not f['with_open']:self.count+=1
        if f['bare_mkdir'] and not f['with_mkdir'] and not f['temp_cwd'] and not f['exists']:self.count+=1
        if f['os_dir_no_try'] and not f['os_dir_try'] and not f['exists']:self.count+=1

class OpenWithoutClose(_V):
    def __init__(self):super().__init__();self.o=self.c=self.w=False
    def visit_With(self,n):
        for m in ast.walk(n):
            if isinstance(m,ast.withitem):
                for k in ast.walk(m):
                    c=get_call(k) if isinstance(k,ast.Call) else None
                    if c and 'open' in c:self.w=True
        self.generic_visit(n)
    def visit_Call(self,n):
        c=get_call(n)
        if c and 'open' in c:self.o=True
        if c and 'close' in c:self.c=True
        self.generic_visit(n)
    def done(self,node):
        if self.o and not self.c and not self.w:self.count+=1

class ForInRange(_V):
    def visit_For(self,n):
        if isinstance(n.iter,ast.Call) and isinstance(n.target,ast.Name):
            c=get_call(n.iter)
            if c and 'range' in c:self.count+=1
        self.generic_visit(n)

class DatetimeNow(_V):
    def visit_Call(self,n):
        c=get_call(n)
        if c and 'datetime.now' in c:self.count+=1
        self.generic_visit(n)

RUNNER=[Sleep,Waiting,Timeout,WithSeed,RandomWithoutSeed,Url,Socket,AssertCalledWith,NotCheckExistence,OpenWithoutClose,ForInRange,DatetimeNow]

def test_smells(method_node):
    """MDFlaker 'Test Smells' factor: total smell count over test_smell_runner's 12 detectors."""
    total=0
    for cls in RUNNER:
        v=cls();v.visit(method_node);v.done(method_node);total+=v.count
    return total

def _indent(line):
    if line.split(' ')[0]!='':return 0
    n=0
    for x in line.split(' '):
        if x=='':n+=1
        elif x in ('def','async','await'):break
    return n

def test_size(name,lines):
    """MDFlaker 'Test Size' factor (get_size): non-blank lines after the first `def name(` until a sibling def/class/decorator."""
    n=0;found=False;base=0
    for line in lines:
        s=line.strip()
        if s.startswith('def '+name+'('):base=_indent(line);found=True
        elif found and s:
            if s.startswith(('def','class','async def','await def','@')):
                if _indent(line)<=base:break
                n+=1
            else:n+=1
    return n
