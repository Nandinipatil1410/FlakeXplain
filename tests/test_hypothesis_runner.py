import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


spec = importlib.util.spec_from_file_location(
    "hypothesis_runner", Path(__file__).resolve().parents[1] / "scripts/run_hypothesis_tests.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class HypothesisRunnerTests(unittest.TestCase):
    def test_both_suites_run_and_failures_are_preserved_in_combined_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "round.xml"
            calls = []

            def execute(cmd):
                calls.append(cmd)
                xml = Path(next(arg.split("=", 1)[1] for arg in cmd if arg.startswith("--junitxml=")))
                failure = "<failure message='real failure'/>" if len(calls) == 1 else ""
                xml.write_text("<testsuites><testsuite><testcase name='case%d'>%s</testcase></testsuite></testsuites>" % (len(calls), failure))
                return 1 if len(calls) == 1 else 0

            args = ["-p", "no:cov", "-p", "randomly", "--randomly-seed=123",
                    "hypothesis-python", "--junitxml=" + str(output)]
            with patch.object(runner.subprocess, "call", side_effect=execute):
                self.assertEqual(runner.run(args), 1)
            self.assertEqual(len(calls), 2)
            self.assertIn("--ignore=" + runner.EXAMPLE, calls[0])
            self.assertIn(runner.EXAMPLE, calls[1])
            self.assertIn("--randomly-seed=123", calls[1])
            tree = ET.parse(output)
            self.assertEqual(len(tree.findall(".//testcase")), 2)
            self.assertEqual(len(tree.findall(".//failure")), 1)

    def test_collection_error_never_publishes_combined_round(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "round.xml"
            with patch.object(runner.subprocess, "call", side_effect=[2, 0]) as call:
                self.assertEqual(runner.run(["hypothesis-python", "--junitxml=" + str(output)]), 2)
            self.assertEqual(call.call_count, 2)
            self.assertFalse(output.exists())
