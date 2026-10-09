"""Checks for pinned setup failures and evidence packaging; no subject experiments."""
import hashlib
import json
import os
import subprocess
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

    def test_explicit_snapshot_corrections_preserve_original_and_are_packaged(self):
        for subject, expected in [("celery", "argparse==1.4.0"), ("airflow", "argparse==1.4.0"), ("conan", "six==1.15.0")]:
            config = NEW_CANNIER_REPOS[subject]
            original = setup_repos.BASE_DIR / config["snapshot_path"]
            before = original.read_bytes()
            with tempfile.TemporaryDirectory() as folder:
                repo = Path(folder) / "repos" / subject
                effective = setup_repos.cannier_requirements(repo, config)
                text = effective.read_text()
                self.assertIn(expected, text.splitlines())
                if subject == "conan":
                    self.assertNotIn("six==1.16.0", text.splitlines())
                self.assertEqual(original.read_bytes(), before)
                self.assertEqual(json.loads((repo / "cannier_setup_recipe.json").read_text()), config)
                with patch("package_cannier_evidence.subprocess.check_output", return_value="packages"):
                    package(subject, Path(folder), Path(folder) / "output")
                self.assertTrue((Path(folder) / "output" / "repos" / subject / "logs" /
                                 "effective-cannier-requirements.txt").exists())

    def test_airflow_imports_installed_sdk_instead_of_test_package(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "airflow"
            test_package = repo / "tests/kubernetes"
            sdk = repo / "installed/kubernetes"
            test_package.mkdir(parents=True)
            sdk.mkdir(parents=True)
            (test_package / "__init__.py").write_text("")
            (sdk / "__init__.py").write_text("")
            (sdk / "client.py").write_text("MARKER = 'installed-sdk'")
            probe = [sys.executable, "-c", "import kubernetes.client; print(kubernetes.client.MARKER)"]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join([str(repo / "tests"), str(sdk.parent)])
            broken = subprocess.run(probe, cwd=repo, env=env, capture_output=True, text=True)
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn("No module named 'kubernetes.client'", broken.stderr)
            with patch.object(runtime, "checked_output", return_value=json.dumps([str(sdk.parent)])):
                env = runtime.pytest_env(repo)
            fixed = subprocess.run(probe, cwd=repo, env=env, capture_output=True, text=True)
            self.assertEqual(fixed.returncode, 0, fixed.stderr)
            self.assertEqual(fixed.stdout.strip(), "installed-sdk")
            for part in ("tasks", "tests", "src", "."):
                self.assertIn(str(repo / part), env["PYTHONPATH"].split(os.pathsep))

    def test_missing_snapshot_override_is_rejected(self):
        config = dict(NEW_CANNIER_REPOS["conan"], snapshot_overrides={"nonexistent-package": "nonexistent-package==1"})
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                setup_repos.cannier_requirements(Path(folder), config)

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
