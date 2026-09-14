"""Regression checks for resume safety and the baseline gate; no real repo test runs."""
from __future__ import annotations
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import runtime
import baseline_gate
import idflakies_runner as runner
import setup_repos
import parse_results


def write_xml(path, failure=False, count=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    cases = "".join(f'<testcase name="test_{i}">' +
                    ('<failure message="failure"/>' if failure and i == 0 else '') +
                    '</testcase>' for i in range(count))
    path.write_text('<testsuites><testsuite>' + cases + '</testsuite></testsuites>', encoding="utf-8")


class PipelineTests(unittest.TestCase):
    def test_live_output_is_saved_without_truncation(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "command.log"
            with contextlib.redirect_stdout(io.StringIO()):
                stdout, _, code = runtime.run_command(
                    [sys.executable, "-u", "-c", "print('x' * 4000); print('finished')"], log_path=log)
            self.assertEqual(code, 0)
            self.assertIn("x" * 4000, stdout)
            self.assertIn("finished", log.read_text(encoding="utf-8"))

    def test_xml_requires_complete_document_and_expected_count(self):
        with tempfile.TemporaryDirectory() as folder:
            xml = Path(folder) / "round.xml"
            xml.write_text("<testsuites>" + " " * 200)
            self.assertFalse(runtime.complete_xml(xml))
            write_xml(xml)
            self.assertTrue(runtime.complete_xml(xml, 2))
            self.assertFalse(runtime.complete_xml(xml, 3))

    def test_baseline_cache_rejects_changed_environment_and_missing_xml(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            write_xml(repo / "logs/baseline.xml")
            runtime.atomic_json(repo / "baseline_state.json",
                                dict(status="PASSED", environment_id="old", collected_count=2,
                                     xml_file="logs/baseline.xml"))
            self.assertFalse(runtime.baseline_state(repo, {"id": "new"}))
            self.assertTrue(runtime.baseline_state(repo, {"id": "old"}))
            (repo / "logs/baseline.xml").unlink()
            self.assertFalse(runtime.baseline_state(repo, {"id": "old"}))

    def test_failed_baseline_retries_without_opening_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "filelock"
            repo.mkdir()
            calls = []
            def fake(cmd, **kwargs):
                calls.append(cmd)
                xml = Path(next(str(x).split("=", 1)[1] for x in cmd if str(x).startswith("--junitxml=")))
                write_xml(xml, failure=True, count=1)
                self.assertIn("-x", cmd)
                self.assertIn("no:cov", cmd)
                self.assertIn("no:randomly", cmd)
                return "", "", 1
            with patch.object(baseline_gate, "REPOS_DIR", root), \
                 patch.object(baseline_gate, "fingerprint", return_value={"id": "same"}), \
                 patch.object(baseline_gate, "run_command", side_effect=fake), \
                 contextlib.redirect_stdout(io.StringIO()):
                passed, *_ = baseline_gate.verify_baseline("filelock")
            self.assertFalse(passed)
            self.assertEqual(len(calls), 3)
            self.assertEqual(runtime.read_json(repo / "baseline_state.json")["status"], "FAILED")

    def test_baseline_records_only_complete_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "filelock"
            repo.mkdir()
            codes = iter([1, 0])
            def fake(cmd, **kwargs):
                code = next(codes)
                xml = Path(next(str(x).split("=", 1)[1] for x in cmd if str(x).startswith("--junitxml=")))
                write_xml(xml, failure=bool(code), count=1 if code else 2)
                return "", "", code
            with patch.object(baseline_gate, "REPOS_DIR", root), \
                 patch.object(baseline_gate, "fingerprint", return_value={"id": "same"}), \
                 patch.object(baseline_gate, "run_command", side_effect=fake), \
                 contextlib.redirect_stdout(io.StringIO()):
                passed, count, attempt, _ = baseline_gate.verify_baseline("filelock")
            self.assertTrue(passed)
            self.assertEqual((count, attempt), (2, 2))
            self.assertFalse((repo / "results").exists())

    def test_round_seed_or_exit_mismatch_is_not_resumed(self):
        with tempfile.TemporaryDirectory() as folder:
            xml = Path(folder) / "random_run_1.xml"
            write_xml(xml)
            record = dict(exit_code=0, config="random-order", round=1, seed=42, xml_file=xml.name)
            self.assertTrue(runner.reusable(record, xml, "random-order", 1, 42, 2))
            self.assertFalse(runner.reusable(record, xml, "random-order", 1, 43, 2))
            record["exit_code"] = 2
            self.assertFalse(runner.reusable(record, xml, "random-order", 1, 42, 2))

    def test_checkpoint_survives_interrupted_next_round(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "filelock"
            repo.mkdir()
            calls = []
            def fake(cmd, **kwargs):
                self.assertNotIn("-x", cmd)
                calls.append(cmd)
                xml = Path(next(str(x).split("=", 1)[1] for x in cmd if str(x).startswith("--junitxml=")))
                write_xml(xml)
                return "", "", 0 if len(calls) == 1 else 2
            state = dict(collected_count=2, xml_file="logs/baseline.xml")
            with patch.object(runner, "REPOS_DIR", root), \
                 patch.object(runner, "fingerprint", return_value={"id": "same"}), \
                 patch.object(runner, "baseline_state", return_value=state), \
                 patch.object(runner, "run_command", side_effect=fake), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "Incomplete"):
                    runner.run_idflakies_suite("filelock", orig_rounds=1, rand_rounds=0)
                saved = runtime.read_json(repo / "results/execution_manifest.json")
                self.assertEqual(len(saved["original_rounds"]), 1)
                self.assertIsNone(saved["reverse_round"])
                calls.clear()
                runner.run_idflakies_suite("filelock", orig_rounds=1, rand_rounds=0)
            self.assertEqual(len(calls), 1)  # Only reverse rerun; original reused.

    def test_default_plan_keeps_all_25_rounds_and_reproducible_seeds(self):
        plan = list(runner.round_plan("filelock"))
        self.assertEqual(len(plan), 25)
        self.assertEqual(sum(row[0] == "original-order" for row in plan), 12)
        self.assertEqual(sum(row[0] == "random-order" for row in plan), 12)
        self.assertEqual(sum(row[0] == "reverse-order" for row in plan), 1)
        self.assertEqual(plan, list(runner.round_plan("filelock")))

    def test_candidate_plan_supports_three_reverse_rounds(self):
        plan = list(runner.round_plan("ipython", reverse_rounds=3))
        self.assertEqual(len(plan), 27)
        self.assertEqual(
            [row[3] for row in plan if row[0] == "reverse-order"],
            ["reverse_run_1.xml", "reverse_run_2.xml", "reverse_run_3.xml"],
        )

    def test_reverse_manifest_reader_is_backward_compatible(self):
        old = {"reverse_round": {"xml_file": "reverse_run_1.xml"}}
        new = {
            "reverse_round": old["reverse_round"],
            "reverse_rounds": [old["reverse_round"], {"xml_file": "reverse_run_2.xml"}],
        }
        self.assertEqual(runner.manifest_reverse_rounds(old), [old["reverse_round"]])
        self.assertEqual(len(runner.manifest_reverse_rounds(new)), 2)

    def test_httpx_setup_keeps_test_pins_and_excludes_documentation_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / "requirements.txt").write_text("pytest==8.4.1\nmkdocs==1.6.1\nruff==0.12.11\n")
            specs = setup_repos.dependency_specs("httpx", repo, setup_repos.REPOS["httpx"])
            self.assertIn("pytest==8.4.1", specs)
            self.assertFalse(any(x.startswith(("mkdocs", "ruff", "twine")) for x in specs))

    def test_poetry_lock_versions_become_pip_constraints(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / "poetry.lock").write_text(
                """[[package]]
name = "Pygments"
version = "2.19.2"

[[package]]
name = "markdown-it-py"
version = "3.0.0"
""",
                encoding="utf-8",
            )
            constraints = setup_repos.lockfile_constraints(repo, "poetry.lock")
            self.assertEqual(
                constraints.read_text(encoding="utf-8").splitlines(),
                ["markdown-it-py==3.0.0", "pygments==2.19.2"],
            )

    def test_urllib3_is_pinned_and_uses_upstream_test_controls(self):
        config = setup_repos.REPOS["urllib3"]
        self.assertEqual(
            config["commit"],
            "a5d70ebfd6a30ceba0e9cc322089a6497dcd643e",
        )
        self.assertEqual(config["supported_platforms"], ["linux"])
        self.assertEqual(config["installer"], "uv")
        args = runtime.pytest_args("urllib3")
        self.assertIn("--disable-socket", args)
        self.assertIn("--allow-unix-socket", args)
        self.assertIn("test/", args)
        self.assertEqual(len(list(runner.round_plan("urllib3"))), 25)

    def test_additional_repositories_are_pinned_and_use_upstream_test_paths(self):
        expected = {
            "werkzeug": "f97c305673ba121a1dae6764c37e8be48907a1d1",
            "rich": "9d8f9a372cc5916fd4781fec207ced7ddac2f08f",
            "pytest": "a315b97ce61f158bef9957152c8415fe743aa553",
        }
        for name, commit in expected.items():
            with self.subTest(repo=name):
                config = setup_repos.REPOS[name]
                self.assertEqual(config["commit"], commit)
                self.assertEqual(config["supported_platforms"], ["linux"])
                self.assertEqual(len(list(runner.round_plan(name))), 25)
                self.assertIn(name, runtime.REPOS)
                self.assertIn(name, parse_results.REPOS)
        self.assertEqual(runtime.pytest_args("werkzeug"), ["tests/"])
        self.assertEqual(runtime.pytest_args("rich"), ["tests/"])
        self.assertEqual(runtime.pytest_args("pytest"), ["testing/"])
        self.assertEqual(
            setup_repos.REPOS["rich"]["constraint_lock"],
            "poetry.lock",
        )
        self.assertNotIn("installer", setup_repos.REPOS["rich"])
        self.assertIn(
            "pytest-randomly==3.15.0",
            setup_repos.REPOS["rich"]["extra_pkgs"],
        )
        self.assertEqual(set(runtime.REPOS), set(parse_results.REPOS))
        self.assertIn("--group", setup_repos.REPOS["werkzeug"]["uv_sync_args"])
        self.assertIn("--group", setup_repos.REPOS["pytest"]["uv_sync_args"])

    def test_each_additional_repository_has_an_isolated_ubuntu_workflow(self):
        workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
        for name in ("werkzeug", "rich", "pytest"):
            with self.subTest(repo=name):
                workflow = (workflows / f"flakexplain-{name}.yml").read_text(
                    encoding="utf-8"
                )
                self.assertIn("workflow_dispatch:", workflow)
                self.assertIn("runs-on: ubuntu-24.04", workflow)
                self.assertIn(f"python run_all.py {name}", workflow)
                self.assertIn(f"repos/{name}/results/", workflow)
                self.assertIn("FlakeXplain_Flaky_Report.md", workflow)

    def test_selected_candidates_are_pinned_and_have_baseline_first_workflows(self):
        expected = {
            "ipython": "95d2b79a2bd889da7a29e7c3cf5f49c1d25ff43d",
            "reframe": "576eb3f1dcc015d1e6d7a10602c748d4f810da68",
            "loguru": "f31e97142adc1156693a26ecaf47208d3765a6e3",
            "freezegun": "b46da782a7a051081fd51577749cfc0074db0cc6",
        }
        workflows = Path(__file__).resolve().parents[1] / ".github" / "workflows"
        for name, commit in expected.items():
            with self.subTest(repo=name):
                config = setup_repos.REPOS[name]
                self.assertEqual(config["commit"], commit)
                self.assertEqual(config["supported_platforms"], ["linux"])
                self.assertEqual(config["python_version"], "3.8.18")
                self.assertIn(name, runtime.REPOS)
                self.assertIn(name, parse_results.REPOS)
                workflow = (workflows / f"flakexplain-{name}.yml").read_text(
                    encoding="utf-8"
                )
                self.assertIn("default: baseline-only", workflow)
                self.assertIn(f"python run_all.py {name} --baseline-only", workflow)
                self.assertIn(f"python run_all.py {name} --reverse-rounds 3", workflow)
                self.assertIn('python-version: "3.8.18"', workflow)
                self.assertIn(f"repos/{name}/results/", workflow)
        self.assertEqual(runtime.pytest_args("reframe"), ["unittests/"])
        self.assertEqual(runtime.pytest_args("loguru"), ["tests/"])
        self.assertEqual(runtime.pytest_args("freezegun"), ["tests/"])
        self.assertEqual(runtime.pytest_args("ipython"), [])
        self.assertEqual(set(runtime.REPOS), set(parse_results.REPOS))
    def test_workflow_targets_only_urllib3_on_ubuntu(self):
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "flakexplain.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertIn("python run_all.py urllib3", workflow)
        self.assertNotIn("matrix.repo", workflow)
        self.assertIn("FlakeXplain_Flaky_Report.md", workflow)
        self.assertIn("urllib3", parse_results.REPOS)
    def test_urllib3_future_warning_environment_matches_upstream(self):
        env = runtime.pytest_env(Path("urllib3"))
        self.assertEqual(env["PYTHONWARNINGS"], "always::FutureWarning")
    def test_report_excludes_uncheckpointed_and_unlabelled_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "filelock"
            results = repo / "results"
            results.mkdir(parents=True)
            cases = ('<testcase classname="tests" name="pass"/>'
                     '<testcase classname="tests" name="skip"><skipped/></testcase>'
                     '<testcase classname="tests" name="fail"><failure/></testcase>')
            (results / "original_run_1.xml").write_text(
                '<testsuites><testsuite>' + cases + '</testsuite></testsuites>')
            write_xml(results / "random_run_1.xml")  # Never committed to manifest.
            runtime.atomic_json(repo / "baseline_state.json", dict(status="PASSED", environment_id="same"))
            runtime.atomic_json(results / "execution_manifest.json",
                                dict(environment_id="same", collected_count=3,
                                     original_rounds=[dict(xml_file="original_run_1.xml", exit_code=1)],
                                     random_rounds=[], reverse_round=None))
            with patch.object(parse_results, "REPOS_DIR", root):
                summary = parse_results.analyze_repo_results("filelock")
            self.assertEqual(summary["total_rounds"], 1)
            self.assertEqual(summary["not_observed_flaky_count"], 1)
            self.assertEqual(summary["unlabelled_count"], 2)
            self.assertEqual(summary["observed_flaky_count"], 0)

    def test_report_reads_all_plural_reverse_round_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "ipython"
            results = repo / "results"
            for number in range(1, 4):
                write_xml(results / f"reverse_run_{number}.xml", count=2)
            runtime.atomic_json(
                repo / "baseline_state.json",
                dict(status="PASSED", environment_id="same", collected_count=2),
            )
            runtime.atomic_json(
                results / "execution_manifest.json",
                dict(
                    environment_id="same",
                    collected_count=2,
                    original_rounds=[],
                    random_rounds=[],
                    reverse_rounds=[
                        dict(xml_file=f"reverse_run_{number}.xml", exit_code=0)
                        for number in range(1, 4)
                    ],
                    reverse_round=None,
                ),
            )
            with patch.object(parse_results, "REPOS_DIR", root):
                summary = parse_results.analyze_repo_results("ipython")
            self.assertEqual(summary["rev_rounds"], 3)
            self.assertEqual(summary["total_rounds"], 3)
            self.assertEqual(summary["not_observed_flaky_count"], 2)

    def test_pipeline_lock_rejects_duplicate_and_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with runtime.pipeline_lock(root, "filelock"):
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    with runtime.pipeline_lock(root, "filelock"):
                        pass
            with runtime.pipeline_lock(root, "filelock"):
                pass

    def test_pytest_environment_has_required_paths(self):
        env = runtime.pytest_env(Path("example"))
        for part in ("tasks", "tests", "src"):
            self.assertIn(str(Path("example") / part), env["PYTHONPATH"])


if __name__ == "__main__":
    unittest.main()
