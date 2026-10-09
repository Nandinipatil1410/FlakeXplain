"""Checks for pinned setup failures and evidence packaging; no subject experiments."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import setup_repos
import runtime
import parse_results
from cannier_subjects import NEW_CANNIER_REPOS
from package_cannier_evidence import package


class RemainingSubjectTests(unittest.TestCase):
    def test_remaining_coverage_matches_the_published_inventory(self):
        root = Path(__file__).resolve().parents[1]
        inventory = json.loads((root / "cannier-replication/inventory.json").read_text(encoding="utf-8-sig"))
        expected = {item["repository"]: item["commit"] for item in inventory["subjects"] if item["status"] == "new-workflow"}
        actual = {config["url"][len("https://github.com/"):-4]: config["commit"]
                  for config in NEW_CANNIER_REPOS.values()}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 20)
        for subject in NEW_CANNIER_REPOS:
            self.assertIn(subject, runtime.REPOS)
            self.assertIn(subject, parse_results.REPOS)

    def test_snapshot_failure_does_not_install_source_or_continue(self):
        config = NEW_CANNIER_REPOS["requests"]
        with patch.object(setup_repos, "run_command", return_value=("", "", 9)) as run:
            code = setup_repos.install_cannier_snapshot(Path("python"), Path("repo"), config)
        self.assertEqual(code, 9)
        self.assertEqual(run.call_count, 1)
        self.assertIn("--no-deps", run.call_args.args[0])

    def test_packaging_preserves_evidence_but_excludes_source_and_binaries(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder) / "work"
            repo = work / "repos/requests"
            (repo / "results").mkdir(parents=True)
            (repo / "logs").mkdir()
            (repo / "results/original_run_1.xml").write_text("<testsuites/>")
            (repo / "logs/run.log").write_text("example log")
            (repo / "logs/unwanted.py").write_text("print(1)")
            (repo / "logs/unwanted.exe").write_bytes(b"binary")
            out = Path(folder) / "evidence"
            with patch("package_cannier_evidence.subprocess.check_output", return_value="system packages"):
                hashes = package("requests", work, out)
            self.assertTrue((out / "repos/requests/results/original_run_1.xml").exists())
            self.assertFalse(list(out.rglob("*.py")))
            self.assertFalse(list(out.rglob("*.exe")))
            for name, digest in hashes.items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
