"""Independent synthetic checks for identity, context and split isolation."""
import ast
from collections import Counter
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from dataset_static import SourceIndex, features
from prepare_dataset import allocate, make_groups

class StaticExtractionTests(unittest.TestCase):
    def index(self, files):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name,text in files.items():
            path=root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)
        return SourceIndex(root)

    def test_parameter_id_is_preserved_but_does_not_change_source(self):
        index=self.index({'tests/test_a.py':'def test_a(value):\n    assert value\n'})
        first,status=index.map_test(dict(classname='tests.test_a',name='test_a[first]'))
        second,_=index.map_test(dict(classname='tests.test_a',name='test_a[second]'))
        self.assertEqual(first[0].key,second[0].key)
        self.assertEqual(status,'unique_static_function')
        self.assertIsNone(index.map_test(dict(classname='tests.test_a',name='generated_1'))[0])

    def test_ambiguous_module_suffix_is_not_first_match(self):
        index=self.index({'one/test_a.py':'def test_a():\n    pass\n','two/test_a.py':'def test_a():\n    pass\n'})
        self.assertEqual(index.map_test(dict(classname='test_a',name='test_a'))[1],'ambiguous_source')

    def test_inherited_method_is_resolved_without_importing_subject(self):
        index=self.index({'tests/base.py':'class Base:\n    def test_a(self):\n        assert True\n',
                          'tests/test_child.py':'from tests.base import Base\nclass Child(Base):\n    pass\n'})
        result,_=index.map_test(dict(classname='tests.test_child.Child',name='test_a'))
        self.assertEqual(result[0].key,'tests/base.py::Base.test_a')
        self.assertEqual(result[2],'tests/test_child.py')

    def test_nearest_fixture_wins_and_autouse_and_dependencies_are_included(self):
        index=self.index({'conftest.py':'''import pytest
@pytest.fixture(autouse=True)
def environment():
    yield
@pytest.fixture
def value():
    return 'wrong'
''','tests/conftest.py':'''import pytest
@pytest.fixture
def dependency():
    return 3
@pytest.fixture(scope='session')
def value(dependency):
    return dependency
''','tests/test_a.py':'''import pytest
@pytest.mark.parametrize('parameter', [1,2])
def test_a(value, parameter, default=1):
    assert value == parameter + default
'''})
        mapped,_=index.map_test(dict(classname='tests.test_a',name='test_a[1]'))
        ctx=index.context(*mapped)
        self.assertEqual(set(ctx['nodes']),{'conftest.py::environment','tests/conftest.py::value','tests/conftest.py::dependency'})
        self.assertEqual(ctx['unresolved'],[])

    def test_class_fixture_overrides_module_and_usefixtures_and_lifecycle(self):
        index=self.index({'tests/test_a.py':'''import pytest
@pytest.fixture
def value():
    return 1
class Test:
    @pytest.fixture
    def value(self):
        return 2
    def setup_method(self):
        self.state = []
    @pytest.mark.usefixtures('value')
    def test_a(self):
        assert True
'''})
        mapped,_=index.map_test(dict(classname='tests.test_a.Test',name='test_a'))
        ctx=index.context(*mapped)
        self.assertIn('tests/test_a.py::Test.value',ctx['nodes'])
        self.assertNotIn('tests/test_a.py::value',ctx['nodes'])
        self.assertEqual(ctx['lifecycle_count'],1)

    def test_dynamic_fixture_and_bounded_helper_graph_are_explicit(self):
        index=self.index({'test_a.py':'''def helper3():
    return 1
def helper2():
    return helper3()
def helper1():
    return helper2()
def test_a(request):
    request.getfixturevalue('some_fixture')
    assert helper1()
'''})
        mapped,_=index.map_test(dict(classname='test_a',name='test_a'))
        ctx=index.context(*mapped)
        self.assertTrue(ctx['bounded'])
        self.assertEqual(ctx['helper_count'],2)
        self.assertIn('dynamic_getfixturevalue',ctx['unresolved'])

    def test_body_features_do_not_inspect_decorators_or_outcomes(self):
        index=self.index({'test_a.py':'''@random.seed(42)
def test_a():
    assert True
'''})
        fn=index.functions[('test_a.py','test_a')]
        values=features(fn)
        self.assertEqual(values['random_calls'],0)
        self.assertEqual(values['asserts'],1)
        self.assertTrue(all(isinstance(v,int) and v>=0 for v in values.values()))

    def test_imported_fixture_decorator_alias_is_recognized(self):
        index=self.index({'test_a.py':'''from pytest import fixture as fx
@fx
def dependency():
    return 1
def test_a(dependency):
    assert dependency
'''})
        mapped,_=index.map_test(dict(classname='test_a',name='test_a'))
        context=index.context(*mapped)
        self.assertEqual(context['fixture_count'],1)
        self.assertEqual(context['unresolved'],[])

    def test_locally_shadowed_global_helper_is_not_selected(self):
        index=self.index({'test_a.py':'''def operation():
    return 1
def test_a(operation):
    assert operation()
'''})
        mapped,_=index.map_test(dict(classname='test_a',name='test_a'))
        self.assertEqual(index.context(*mapped)['helper_count'],0)

    def test_duplicate_projects_share_one_split_group(self):
        rows=[dict(project=p,body_statements=3,body_ast_nodes=20,body_ast_sha256=h)
              for p,h in [('a','shared'),('b','shared'),('c','different')]]
        groups,shared=make_groups(rows)
        self.assertEqual(groups['a'],groups['b'])
        self.assertEqual(len(shared),1)
        split=allocate(groups,{p:Counter({0:10,1:1}) for p in groups},2)
        self.assertEqual(split['a'],split['b'])
        self.assertNotEqual(split['a'],split['c'])

if __name__=='__main__':
    unittest.main()
