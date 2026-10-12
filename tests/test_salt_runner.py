import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import runtime
import run_salt_tests


class SaltRunnerTests(unittest.TestCase):
    def test_only_salt_uses_the_launcher(self):
        repo = Path("salt")
        self.assertEqual(runtime.pytest_command("salt", repo), [
            runtime.python_for(repo), "-u", ROOT / "scripts/run_salt_tests.py"])
        self.assertEqual(runtime.pytest_command("flask", Path("flask"))[-2:], ["-m", "pytest"])

    def test_cleanup_terminates_then_kills_only_surviving_children(self):
        first, survivor = Mock(), Mock()
        api = types.SimpleNamespace(
            Process=Mock(return_value=Mock(children=Mock(return_value=[first, survivor]))),
            wait_procs=Mock(side_effect=[([first], [survivor]), ([survivor], [])]),
            NoSuchProcess=ProcessLookupError,
        )
        self.assertEqual(run_salt_tests.finish_children(api), 2)
        first.terminate.assert_called_once()
        survivor.terminate.assert_called_once()
        first.kill.assert_not_called()
        survivor.kill.assert_called_once()

    @unittest.skipUnless(os.name == "posix", "Salt uses Linux process groups")
    def test_leftover_output_pipe_cannot_hang_or_hide_pytest_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "pytest.py").write_text(
                "import os, subprocess, sys\n"
                "def main(args):\n"
                "    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "    print('FULL_ARGS', repr(args), flush=True)\n"
                "    return int(os.environ['SALT_TEST_CODE'])\n")
            # Deliberately leave cleanup to the outer process group, reproducing
            # an orphan that retains stdout after the pytest process exits.
            (root / "psutil.py").write_text(
                "class Process:\n"
                "    def children(self, recursive): return []\n"
                "class NoSuchProcess(Exception): pass\n"
                "def wait_procs(children, timeout): return (children, [])\n")
            for code in (0, 1):
                with self.subTest(code=code):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "scripts/run_salt_tests.py"),
                         "tests/pytests/unit", "-p", "no:cov", "--randomly-seed=640768"],
                        env=dict(os.environ, PYTHONPATH=folder, SALT_TEST_CODE=str(code)),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, code, result.stdout)
                    self.assertIn("tests/pytests/unit", result.stdout)
                    self.assertIn("--randomly-seed=640768", result.stdout)
                    self.assertIn("Salt pytest returned exit {}".format(code), result.stdout)


if __name__ == "__main__":
    unittest.main()
