"""Checks for pinned setup failures and evidence packaging; no subject experiments."""
import hashlib
import io
import json
import os
import runpy
import subprocess
import sysconfig
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import setup_repos
import runtime
import parse_results
from cannier_subjects import NEW_CANNIER_REPOS
from package_cannier_evidence import package
import prepare_skimage_data
from git_test_fixtures import prepare_git_test_fixtures, git_test_fixture_env
import package_test_fixtures


class RemainingSubjectTests(unittest.TestCase):
    def test_moving_pip_source_is_pinned_without_removing_tests(self):
        config = NEW_CANNIER_REPOS["setuptools"]
        source = config["test_parameter_sources"][0]
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            root = package_test_fixtures.package_fixture_dir(repo)
            root.mkdir(parents=True)
            (root / "parameter_sources.json").write_text(json.dumps([source]))
            plugin = repo / "flakexplain_package_sources.py"
            plugin.write_bytes((Path(package_test_fixtures.__file__).with_name(
                plugin.name)).read_bytes())
            fake_pytest = types.SimpleNamespace(fixture=lambda **kw: lambda f: f)
            with patch.dict(sys.modules, pytest=fake_pytest):
                hook = runpy.run_path(str(plugin))["pytest_collection_modifyitems"]
            def item(module):
                return types.SimpleNamespace(
                    module=types.SimpleNamespace(__name__=module),
                    callspec=types.SimpleNamespace(params={"pip_version": source["original"]}),
                    user_properties=[])
            target, other = item(source["module"]), item("another.test_module")
            items = [target, other]
            hook(items)
            self.assertEqual(len(items), 2)
            self.assertEqual(target.callspec.params["pip_version"], source["pinned"])
            self.assertEqual(other.callspec.params["pip_version"], source["original"])
            self.assertEqual(target.user_properties, [("pinned_pip_version", source["pinned"])])

    def test_setuptools_prepares_metadata_before_replacing_itself(self):
        config = NEW_CANNIER_REPOS["setuptools"]
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(setup_repos, "run_command", return_value=("", "", 0)) as run, \
                patch("git_test_fixtures.prepare_git_test_fixtures"), \
                patch("package_test_fixtures.prepare_package_test_fixtures"):
            setup_repos.install_cannier_snapshot(Path("python"), Path(folder), config)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[1], ["python", "setup.py", "egg_info"])
        self.assertEqual(commands[2][-2:], ["-e", "."])

    def test_easy_install_fixture_checksums_and_subject_import_path(self):
        payload = b"verified wheel bytes"
        fixture = dict(filename="example.whl",
                       url="https://example.invalid/example.whl",
                       sha256=hashlib.sha256(payload).hexdigest())
        config = dict(package_test_fixtures=[fixture])
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            with patch.object(package_test_fixtures, "urlopen", return_value=io.BytesIO(payload)):
                package_test_fixtures.prepare_package_test_fixtures(Path("python"), repo, config)
                self.assertTrue((repo / "flakexplain_package_sources.py").is_file())
            wheel = package_test_fixtures.package_fixture_dir(repo) / "downloads/example.whl"
            wheel.write_bytes(b"corrupt")
            with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                package_test_fixtures.prepare_package_test_fixtures(Path("python"), repo, config)
        repo = Path("/tmp/setuptools")
        env = runtime.pytest_env(repo)
        self.assertNotIn(str(package_test_fixtures.package_fixture_dir(repo)),
                      env["PYTHONPATH"].split(os.pathsep))
        self.assertIn("flakexplain_package_sources", runtime.pytest_args("setuptools"))

    def test_external_git_fixture_clones_pinned_revision_without_global_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "upstream"
            source.mkdir()
            def git(*args, cwd=source, env=None):
                return subprocess.check_output(["git", *args], cwd=cwd, env=env,
                                               text=True, stderr=subprocess.STDOUT).strip()
            git("init")
            (source / "setup.py").write_text("historical version")
            git("add", "setup.py")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-m", "Historical fixture")
            historical = git("rev-parse", "HEAD")
            (source / "setup.py").write_text("changed version")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-am", "Changed upstream")
            repo = root / "subject"
            repo.mkdir()
            fixture = dict(name="sampleproject", url=source.as_uri(), commit=historical)
            config = dict(git_test_fixtures=[fixture])
            prepare_git_test_fixtures(repo, config)
            prepare_git_test_fixtures(repo, config)
            env = git_test_fixture_env(repo, config, os.environ.copy())
            git("clone", source.as_uri(), str(root / "clone"), cwd=root, env=env)
            self.assertEqual(git("rev-parse", "HEAD", cwd=root / "clone"), historical)
            self.assertEqual((root / "clone/setup.py").read_text(), "historical version")
            self.assertNotEqual(git("rev-parse", "HEAD"), historical)
            self.assertEqual(json.loads((repo / "logs/git_test_fixture_provenance.json").read_text()),
                             [fixture])
        self.assertEqual(runtime.pytest_args("setuptools"),
                         ["-p", "no:xdist", "-p", "flakexplain_package_sources"])
        self.assertFalse(any("setuptools-scm" in pin for pin in
                             NEW_CANNIER_REPOS["setuptools"]["bootstrap_pkgs"]))

    def test_skimage_data_is_pinned_verified_and_reusable_offline(self):
        config = NEW_CANNIER_REPOS["scikit_image"]
        payload = b"authentic dataset bytes"
        expected = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            registry = repo / "skimage/data/_registry.py"
            registry.parent.mkdir(parents=True)
            registry.write_text("registry = " + repr({"data/eagle.png": expected})
                                + "\nregistry_urls = " + repr({"data/eagle.png":
                                "https://gitlab.com/scikit-image/data/-/raw/master/eagle.png"}))
            with patch.object(prepare_skimage_data, "urlopen", return_value=io.BytesIO(payload)) as fetch:
                prepare_skimage_data.prepare_skimage_data(repo, config)
                self.assertIn("/repository/files/eagle.png/raw?ref=" + config["dataset_revision"],
                              fetch.call_args.args[0])
            with patch.object(prepare_skimage_data, "urlopen", side_effect=AssertionError("network")):
                prepare_skimage_data.prepare_skimage_data(repo, config)
            target = repo / "skimage/data/eagle.png"
            self.assertEqual(target.read_bytes(), payload)
            evidence = json.loads((repo / "logs/dataset_provenance.json").read_text())
            self.assertEqual(evidence["files"][0]["sha256"], expected)
            target.unlink()
            with patch.object(prepare_skimage_data, "urlopen", side_effect=lambda *a, **kw: io.BytesIO(b"wrong")), \
                    patch.object(prepare_skimage_data.time, "sleep"):
                with self.assertRaisesRegex(RuntimeError, "Downloaded dataset checksum mismatch"):
                    prepare_skimage_data.prepare_skimage_data(repo, config)
            self.assertFalse(target.exists())
            self.assertEqual(list(target.parent.iterdir()), [registry])

    def test_skimage_setup_prepares_all_datasets_before_success(self):
        config = NEW_CANNIER_REPOS["scikit_image"]
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            with patch.object(setup_repos, "run_command", return_value=("", "", 0)), \
                    patch.object(prepare_skimage_data, "prepare_skimage_data") as prepare:
                self.assertEqual(setup_repos.install_cannier_snapshot(Path("python"), repo, config), 0)
                prepare.assert_called_once_with(repo, config)
            with patch.object(setup_repos, "run_command", return_value=("", "", 0)), \
                    patch.object(prepare_skimage_data, "prepare_skimage_data",
                                 side_effect=RuntimeError("dataset unavailable")):
                with self.assertRaisesRegex(RuntimeError, "dataset unavailable"):
                    setup_repos.install_cannier_snapshot(Path("python"), repo, config)

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

    def test_flexget_recording_is_verified_preserved_and_packaged(self):
        config = NEW_CANNIER_REPOS["flexget"]
        fixture = config["test_fixtures"][0]
        data = (setup_repos.BASE_DIR / fixture["source"]).read_bytes()
        self.assertIn(b"https://api.t-ru.org/v1/get_tor_topic_data?by=topic_id&val=2455223", data)
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "repos/flexget"
            with patch.object(setup_repos, "run_command", return_value=("", "", 0)):
                self.assertEqual(setup_repos.install_cannier_snapshot(Path("python"), repo, config), 0)
            target = repo / fixture["destination"]
            self.assertEqual(target.read_bytes(), data)
            setup_repos.prepare_test_fixtures(repo, config)  # Reinstallation is idempotent.
            with patch("package_cannier_evidence.subprocess.check_output", return_value="packages"):
                package("flexget", Path(folder), Path(folder) / "evidence")
            logs = Path(folder) / "evidence/repos/flexget/logs"
            self.assertEqual((logs / (target.name + ".txt")).read_bytes(), data)
            self.assertEqual(json.loads((logs / "test_fixture_provenance.json").read_text()), [fixture])
            bad_config = dict(config, test_fixtures=[dict(fixture, sha256="0" * 64)])
            with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                setup_repos.prepare_test_fixtures(repo, bad_config)
            self.assertEqual(target.read_bytes(), data)
            target.write_bytes(b"different recording")
            with self.assertRaisesRegex(RuntimeError, "Refusing to overwrite"):
                setup_repos.prepare_test_fixtures(repo, config)
            self.assertEqual(target.read_bytes(), b"different recording")

    def test_pillow_tiff_fixtures_are_verified_installed_and_packaged(self):
        config = NEW_CANNIER_REPOS["pillow"]
        self.assertEqual({item["destination"] for item in config["test_fixtures"]}, {
            "Tests/images/crash_1.tif", "Tests/images/crash_2.tif",
            "Tests/images/string_dimension.tiff",
        })
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "repos/pillow"
            with patch.object(setup_repos, "run_command", return_value=("", "", 0)):
                self.assertEqual(setup_repos.install_cannier_snapshot(Path("python"), repo, config), 0)
            setup_repos.prepare_test_fixtures(repo, config)
            with patch("package_cannier_evidence.subprocess.check_output", return_value="packages"):
                package("pillow", Path(folder), Path(folder) / "evidence")
            logs = Path(folder) / "evidence/repos/pillow/logs"
            for fixture in config["test_fixtures"]:
                data = (setup_repos.BASE_DIR / fixture["source"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), fixture["sha256"])
                self.assertTrue(data.startswith((b"II", b"MM")))
                target = repo / fixture["destination"]
                self.assertEqual(target.read_bytes(), data)
                self.assertEqual((logs / (target.name + ".txt")).read_bytes(), data)
            self.assertEqual(json.loads((logs / "test_fixture_provenance.json").read_text()),
                             config["test_fixtures"])

    def test_hypothesis_entrypoint_install_is_required_and_preserves_pins(self):
        config = NEW_CANNIER_REPOS["hypothesis"]
        target = "hypothesis-python/examples/example_hypothesis_entrypoint"
        for exit_code in (0, 9):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as folder:
                repo = Path(folder)
                with patch.object(setup_repos, "run_command", side_effect=[
                    ("", "", 0), ("", "", 0), ("", "", 0), ("", "", exit_code)
                ]) as run:
                    code = setup_repos.install_cannier_snapshot(Path("python"), repo, config)
                self.assertEqual(code, exit_code)
                self.assertEqual(run.call_count, 4)
                command = run.call_args.args[0]
                self.assertEqual(command[-2:], ["-e", target])
                self.assertIn("--no-deps", command)
                self.assertIn("--no-build-isolation", command)
                self.assertEqual(run.call_args.kwargs["cwd"], repo)
                self.assertIn("example_hypothesis_entrypoint", str(run.call_args.kwargs["log_path"]))

    def test_explicit_snapshot_corrections_preserve_original_and_are_packaged(self):
        for subject, expected in [("celery", "argparse==1.4.0"), ("airflow", "argparse==1.4.0"), ("conan", "six==1.15.0"),
                                  ("cirq", "typing-extensions==3.10.0.2"),
                                  ("cirq", "typed-ast==1.4.3"), ("cirq", "filelock==3.4.1"),
                                  ("cirq", "matplotlib==3.5.2"),
                                  ("conan", "cmake==3.15.3"),
                                  ("electrum", "pycryptodomex==3.10.1"),
                                  ("flexget", "six==1.15.0")]:
            config = NEW_CANNIER_REPOS[subject]
            original = setup_repos.BASE_DIR / config["snapshot_path"]
            before = original.read_bytes()
            with tempfile.TemporaryDirectory() as folder:
                repo = Path(folder) / "repos" / subject
                effective = setup_repos.cannier_requirements(repo, config)
                text = effective.read_text()
                self.assertIn(expected, text.splitlines())
                if subject in ("conan", "flexget"):
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
            (sdk.parent / "argparse.py").write_text("raise RuntimeError('legacy argparse imported')")
            probe = [sys.executable, "-c", "import kubernetes.client; import argparse; argparse.ArgumentParser(allow_abbrev=False); print(kubernetes.client.MARKER)"]
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join([str(repo / "tests"), str(sdk.parent)])
            broken = subprocess.run(probe, cwd=repo, env=env, capture_output=True, text=True)
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn("No module named 'kubernetes.client'", broken.stderr)
            with patch.object(runtime, "checked_output", return_value=json.dumps([sysconfig.get_path("stdlib"), str(sdk.parent)])):
                env = runtime.pytest_env(repo)
            fixed = subprocess.run(probe, cwd=repo, env=env, capture_output=True, text=True)
            self.assertEqual(fixed.returncode, 0, fixed.stderr)
            self.assertEqual(fixed.stdout.strip(), "installed-sdk")
            for part in ("tasks", "tests", "src", "."):
                self.assertIn(str(repo / part), env["PYTHONPATH"].split(os.pathsep))

    def test_airflow_broker_fixture_is_passed_to_child_only_for_airflow(self):
        prefix = "AIRFLOW__CELERY_BROKER_TRANSPORT_OPTIONS__"
        expected = {"VISIBILITY_TIMEOUT": "21600", "_TEST_ONLY_BOOL": "True",
                    "_TEST_ONLY_FLOAT": "12.0", "_TEST_ONLY_STRING": "this is a test"}
        with patch.dict(os.environ, {}, clear=True), patch.object(runtime, "checked_output", return_value="[]"):
            env = runtime.pytest_env(Path("airflow"))
            probe = subprocess.run(
                [sys.executable, "-c", "import os,json; print(json.dumps(dict(os.environ)))"],
                env=env, capture_output=True, text=True, check=True)
            child = json.loads(probe.stdout)
            for name, value in expected.items():
                self.assertEqual(child[prefix + name], value)
                self.assertNotIn(prefix + name, os.environ)
                self.assertNotIn(prefix + name, runtime.pytest_env(Path("cirq")))

    def test_conan_does_not_inherit_runner_pkg_config_path(self):
        with patch.dict(os.environ, {"PKG_CONFIG_PATH": "/runner/python/lib/pkgconfig"}):
            env = runtime.pytest_env(Path("conan"))
            probe = subprocess.run(
                [sys.executable, "-c", "import os; print('PKG_CONFIG_PATH' in os.environ)"],
                env=env, capture_output=True, text=True, check=True)
            self.assertEqual(probe.stdout.strip(), "False")
            self.assertEqual(os.environ["PKG_CONFIG_PATH"], "/runner/python/lib/pkgconfig")
            self.assertEqual(runtime.pytest_env(Path("cirq"))["PKG_CONFIG_PATH"],
                             "/runner/python/lib/pkgconfig")

    def test_mitmproxy_large_integer_conversion_is_enabled_only_for_subject(self):
        if not hasattr(sys, "get_int_max_str_digits"):
            self.skipTest("Interpreter predates the integer-string conversion limit")
        probe = [sys.executable, "-c",
                 "import math; n = math.factorial(30000); s = str(n).encode(); "
                 "assert int(s) == n; print(len(s))"]
        with patch.dict(os.environ, {"PYTHONINTMAXSTRDIGITS": "4300"}):
            broken = subprocess.run(probe, env=os.environ.copy(), capture_output=True, text=True)
            self.assertNotEqual(broken.returncode, 0)
            self.assertIn("integer string conversion", broken.stderr)
            fixed = subprocess.run(probe, env=runtime.pytest_env(Path("mitmproxy")),
                                   capture_output=True, text=True)
            self.assertEqual(fixed.returncode, 0, fixed.stderr)
            self.assertGreater(int(fixed.stdout.strip()), 4300)
            self.assertEqual(os.environ["PYTHONINTMAXSTRDIGITS"], "4300")
            self.assertEqual(runtime.pytest_env(Path("cirq"))["PYTHONINTMAXSTRDIGITS"], "4300")

    def test_airflow_requests_upstream_database_reset_for_each_pytest_process(self):
        self.assertEqual(runtime.pytest_args("airflow"), ["tests", "--with-db-init"])

    def test_libcloud_excludes_only_uploader_and_preserves_snapshot_and_provenance(self):
        config = NEW_CANNIER_REPOS["libcloud"]
        original = setup_repos.BASE_DIR / config["snapshot_path"]
        before = original.read_bytes()
        self.assertEqual(set(config["snapshot_exclusions"]), {"codecov"})
        self.assertEqual(config["snapshot_additions"], ["toml==0.10.2"])
        self.assertIn("codecov==2.1.10", original.read_text().splitlines())
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "repos/libcloud"
            effective = setup_repos.cannier_requirements(repo, config)
            expected = [line for line in original.read_text().splitlines()
                        if line != "codecov==2.1.10"]
            expected.append("toml==0.10.2")
            self.assertEqual(effective.read_text().splitlines(), expected)
            self.assertEqual(original.read_bytes(), before)
            self.assertEqual(json.loads((repo / "cannier_setup_recipe.json").read_text()), config)
            with patch("package_cannier_evidence.subprocess.check_output", return_value="packages"):
                package("libcloud", Path(folder), Path(folder) / "evidence")
            archived = Path(folder) / "evidence/repos/libcloud"
            self.assertEqual((archived / "logs/effective-cannier-requirements.txt").read_bytes(),
                             effective.read_bytes())
            self.assertEqual(json.loads((archived / "cannier_setup_recipe.json").read_text()), config)

    def test_prefect_dependency_corrections_preserve_snapshot_and_evidence(self):
        config = NEW_CANNIER_REPOS["prefect"]
        original = setup_repos.BASE_DIR / config["snapshot_path"]
        before = original.read_bytes()
        overrides = config["snapshot_overrides"]
        self.assertEqual(set(overrides), {
            "boto3", "botocore", "s3transfer", "great-expectations", "ruamel.yaml",
            "requests", "chardet", "urllib3", "soda-sql"})
        self.assertEqual(overrides["soda-sql"], "soda-sql-core==2.1.0b1")
        self.assertFalse(config.get("snapshot_exclusions"))
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "repos/prefect"
            effective = setup_repos.cannier_requirements(repo, config)
            expected = [overrides.get(line.split("==", 1)[0].lower().replace("_", "-"), line)
                        for line in original.read_text().splitlines()]
            self.assertEqual(effective.read_text().splitlines(), expected)
            self.assertEqual(original.read_bytes(), before)
            with patch("package_cannier_evidence.subprocess.check_output", return_value="packages"):
                package("prefect", Path(folder), Path(folder) / "evidence")
            archived = Path(folder) / "evidence/repos/prefect"
            self.assertEqual((archived / "logs/effective-cannier-requirements.txt").read_bytes(),
                             effective.read_bytes())
            self.assertEqual(json.loads((archived / "cannier_setup_recipe.json").read_text()), config)

    def test_salt_login_preflight_preserves_pipeline_arguments_and_rejects_bad_sessions(self):
        fake_pwd = types.SimpleNamespace(getpwuid=lambda uid: types.SimpleNamespace(pw_name="cannier"))
        script = setup_repos.BASE_DIR / "scripts/run_salt_session.py"
        with patch.dict(sys.modules, {"pwd": fake_pwd}):
            main = runpy.run_path(str(script))["main"]
        self.assertEqual(runtime.pytest_args("salt"), ["tests/pytests/unit", "--capture=sys"])
        for tty, login in [(False, "cannier"), (True, "root"), (True, "cannier")]:
            with self.subTest(tty=tty, login=login), \
                    patch.object(os, "geteuid", return_value=1001, create=True), \
                    patch.object(os, "isatty", return_value=tty), \
                    patch.object(os, "getlogin", return_value=login), \
                    patch.object(os, "execv") as execute, \
                    patch.object(sys, "argv", [str(script), "salt", "--baseline-only", "--work-dir", "/tmp/work space"]):
                if tty and login == "cannier":
                    main()
                    self.assertEqual(execute.call_args.args, (sys.executable, [
                        sys.executable, str(setup_repos.BASE_DIR / "run_all.py"),
                        "salt", "--baseline-only", "--work-dir", "/tmp/work space"]))
                else:
                    with self.assertRaisesRegex(SystemExit, "terminal login"):
                        main()
                    execute.assert_not_called()

    def test_invalid_snapshot_exclusions_are_rejected(self):
        config = NEW_CANNIER_REPOS["libcloud"]
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "exclusion does not match"):
                setup_repos.cannier_requirements(Path(folder), dict(
                    config, snapshot_exclusions={"nonexistent-package": "unused"}))
            with self.assertRaisesRegex(RuntimeError, "both overridden and excluded"):
                setup_repos.cannier_requirements(Path(folder), dict(
                    config, snapshot_overrides={"codecov": "codecov==2.1.13"}))

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
