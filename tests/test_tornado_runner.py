"""Regression checks for the historical Tornado namespace-package collector."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class TornadoRunnerTests(unittest.TestCase):
    def test_collector_imports_the_qualified_module_once(self):
        # The regression is module identity, independent of pytest's installed
        # version: config fixtures import tornado.test.options_test.Email.
        fake_pytest = types.ModuleType("pytest")
        fake_pytest.Module = type("Module", (), {})
        path = Path(__file__).resolve().parents[1] / "scripts/run_tornado_tests.py"
        spec = importlib.util.spec_from_file_location("tornado_runner", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"pytest": fake_pytest}):
            spec.loader.exec_module(module)
        collector = module.TornadoModule()
        collector.fspath = Path.cwd() / "tornado/test/options_test.py"
        expected = object()
        with patch.object(module.importlib, "import_module", return_value=expected) as load:
            self.assertIs(collector._getobj(), expected)
        load.assert_called_once_with("tornado.test.options_test")

    def test_only_tornado_suite_uses_the_launcher(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import runtime
        repo = Path("example")
        self.assertEqual(
            runtime.pytest_command("tornado", repo)[-1],
            runtime.BASE_DIR / "scripts/run_tornado_tests.py",
        )
        self.assertEqual(runtime.pytest_command("flask", repo)[-2:], ["-m", "pytest"])
