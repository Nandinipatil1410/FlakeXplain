#!/usr/bin/env python3
"""Prepare pinned checkouts; reuse verified environments; install test dependencies only."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.8 historical-subject workflows.
    import tomli as tomllib
from datetime import datetime, timezone

from runtime import (
    BASE_DIR,
    REPOS_DIR,
    REPOS as REPO_NAMES,
    atomic_json,
    checked_output,
    fingerprint,
    python_for,
    read_json,
    run_command,
)

REPOS = {
    "click": {
        "url": "https://github.com/pallets/click",
        "commit": "6aabf099",
        "extra_pkgs": ["pytest", "pytest-randomly"],
    },
    "flask": {
        "url": "https://github.com/pallets/flask",
        "commit": "d318b683",
        "extra_pkgs": [
            "pytest", "pytest-randomly", "blinker", "asgiref", "python-dotenv",
            "pytest-asyncio", "watchdog",
        ],
    },
    "filelock": {
        "url": "https://github.com/tox-dev/filelock",
        "commit": "82f66d7b0aaa83755f8d71d0b0da88408b58ec4a",
        "extra_pkgs": [
            "pytest", "pytest-randomly", "pytest-asyncio", "pytest-mock",
            "pytest-cov", "pytest-timeout", "virtualenv",
        ],
    },
    "fsspec": {
        "url": "https://github.com/fsspec/filesystem_spec",
        "commit": "13b0bce8",
        "extra_pkgs": [
            "pytest", "pytest-randomly", "pytest-asyncio", "pytest-mock",
            "requests", "numpy",
        ],
    },
    "httpx": {
        "url": "https://github.com/encode/httpx",
        "commit": "b5addb64f0161ff6bfe94c124ef76f6a1fba5254",
        "extra_pkgs": [
            "pytest", "pytest-randomly", "pytest-asyncio", "pytest-trio", "trio",
            "anyio", "httpcore", "cryptography", "trustme", "uvicorn", "brotli",
            "zstandard", "chardet", "h2", "socksio", "rich", "pygments",
        ],
    },
    "urllib3": {
        "url": "https://github.com/urllib3/urllib3",
        "commit": "a5d70ebfd6a30ceba0e9cc322089a6497dcd643e",
        "supported_platforms": ["linux"],
        "installer": "uv",
        "uv_version": "0.11.7",
        "uv_sync_args": [
            "--frozen", "--inexact", "--group", "dev",
            "--extra", "socks", "--extra", "brotli", "--extra", "zstd",
            "--extra", "h2",
        ],
        "extra_pkgs": ["pytest-randomly==5.0.0"],
        "verify_pkgs": [
            "urllib3", "anyio", "h2", "httpx", "hypercorn", "PySocks",
            "pytest", "pytest-randomly", "pytest-socket", "pytest-timeout",
            "quart", "quart-trio", "trio", "cryptography", "idna",
            "pyOpenSSL", "trustme",
        ],
    },
    "werkzeug": {
        "url": "https://github.com/pallets/werkzeug",
        "commit": "f97c305673ba121a1dae6764c37e8be48907a1d1",
        "supported_platforms": ["linux"],
        "installer": "uv",
        "uv_version": "0.11.7",
        "uv_sync_args": [
            "--frozen", "--inexact", "--no-default-groups", "--group", "tests",
        ],
        "extra_pkgs": ["pytest-randomly==5.0.0"],
        "verify_pkgs": [
            "Werkzeug", "cffi", "cryptography", "ephemeral-port-reserve",
            "pytest", "pytest-randomly", "pytest-timeout", "watchdog",
        ],
    },
    "rich": {
        "url": "https://github.com/Textualize/rich",
        "commit": "9d8f9a372cc5916fd4781fec207ced7ddac2f08f",
        "supported_platforms": ["linux"],
        "constraint_lock": "poetry.lock",
        "extra_pkgs": [
            "pytest", "pytest-cov", "attrs", "typing-extensions",
            "pytest-randomly==3.15.0",
        ],
        "verify_pkgs": [
            "rich", "pytest", "pytest-randomly", "pytest-cov", "attrs",
            "typing-extensions", "pygments", "markdown-it-py",
        ],
    },
    "pytest": {
        "url": "https://github.com/pytest-dev/pytest",
        "commit": "a315b97ce61f158bef9957152c8415fe743aa553",
        "supported_platforms": ["linux"],
        "installer": "uv",
        "uv_version": "0.11.7",
        "uv_sync_args": [
            "--frozen", "--inexact", "--no-default-groups", "--group", "dev",
        ],
        "extra_pkgs": ["pytest-randomly==5.0.0"],
        "verify_pkgs": [
            "pytest", "pytest-randomly", "attrs", "coverage", "hypothesis",
            "mock", "numpy", "pexpect", "pytest-xdist", "PyYAML", "requests",
            "setuptools", "xmlschema",
        ],
    },
    "ipython": {
        "url": "https://github.com/ipython/ipython.git",
        "commit": "95d2b79a2bd889da7a29e7c3cf5f49c1d25ff43d",
        "supported_platforms": ["linux"],
        "python_version": "3.8.18",
        "install_target": ".[test]",
        "extra_pkgs": [
            "pytest==6.2.4", "pytest-randomly==3.15.0", "matplotlib==3.4.2",
            "jedi==0.17.0", "parso==0.8.2",
        ],
        "verify_pkgs": [
            "ipython", "pytest", "pytest-randomly", "nose", "numpy",
            "ipykernel", "nbformat", "requests", "testpath", "matplotlib",
            "jedi", "parso",
        ],
    },
    "reframe": {
        "url": "https://github.com/eth-cscs/reframe.git",
        "commit": "576eb3f1dcc015d1e6d7a10602c748d4f810da68",
        "supported_platforms": ["linux"],
        "python_version": "3.8.18",
        # setup.py imports reframe, whose import chain requires jsonschema
        # before pip can generate editable-install metadata.
        "bootstrap_pkgs": ["jsonschema==3.2.0"],
        "extra_pkgs": [
            "pytest==6.2.4", "pytest-randomly==3.15.0",
            "jsonschema==3.2.0", "coverage==5.5",
        ],
        "verify_pkgs": [
            "ReFrame-HPC", "pytest", "pytest-randomly", "jsonschema", "coverage",
        ],
    },
    "loguru": {
        "url": "https://github.com/Delgan/loguru.git",
        "commit": "f31e97142adc1156693a26ecaf47208d3765a6e3",
        "supported_platforms": ["linux"],
        "python_version": "3.8.18",
        "extra_pkgs": [
            "pytest==6.2.4", "pytest-randomly==3.15.0", "colorama==0.4.4",
        ],
        "verify_pkgs": ["loguru", "pytest", "pytest-randomly", "colorama"],
    },
    "freezegun": {
        "url": "https://github.com/spulec/freezegun.git",
        "commit": "b46da782a7a051081fd51577749cfc0074db0cc6",
        "supported_platforms": ["linux"],
        "python_version": "3.8.18",
        "extra_pkgs": [
            "pytest==6.2.4", "pytest-randomly==3.15.0",
            "python-dateutil==2.8.2", "maya==0.6.1",
        ],
        "verify_pkgs": [
            "freezegun", "pytest", "pytest-randomly", "python-dateutil", "maya",
        ],
    },
}


def dependency_specs(repo_name, repo, config):
    specs = list(config["extra_pkgs"])
    # Preserve upstream test pins without installing documentation/lint/release tools.
    if repo_name == "httpx":
        pins = {}
        for line in (repo / "requirements.txt").read_text(encoding="utf-8").splitlines():
            match = re.match(r"([A-Za-z0-9_-]+)(==[^ ;#]+)", line.strip())
            if match:
                pins[match[1].lower().replace("_", "-")] = match.group(0)
        specs = [pins.get(name.lower().replace("_", "-"), name) for name in specs]
    return specs


def lockfile_constraints(repo, lock_name):
    """Convert a committed Poetry lock into pip constraints without changing upstream."""
    lock_path = repo / lock_name
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    pins = {}
    for package in data.get("package", []):
        name = package["name"]
        normalized = name.lower().replace("_", "-")
        version = package["version"]
        previous = pins.get(normalized)
        if previous and previous != version:
            raise RuntimeError(
                f"{lock_path} contains multiple versions for {name}: "
                f"{previous} and {version}."
            )
        pins[normalized] = version
    if not pins:
        raise RuntimeError(f"No package versions found in {lock_path}.")
    constraints = repo / "poetry_lock_constraints.txt"
    constraints.write_text(
        "".join(f"{name}=={pins[name]}\n" for name in sorted(pins)),
        encoding="utf-8",
    )
    return constraints


def setup_repo(repo_name, config, refresh=False):
    supported = config.get("supported_platforms")
    if supported and sys.platform not in supported:
        raise RuntimeError(
            f"{repo_name} is configured for {', '.join(supported)}. Use the prepared "
            "Ubuntu GitHub Actions workflow; no upstream tests will be patched or skipped."
        )
    expected_python = config.get("python_version")
    actual_python = ".".join(str(part) for part in sys.version_info[:3])
    if expected_python and actual_python != expected_python:
        raise RuntimeError(
            f"{repo_name} requires Python {expected_python}; current interpreter is "
            f"Python {actual_python}."
        )
    repo = REPOS_DIR / repo_name
    source = BASE_DIR / "repos" / repo_name
    print(f"\nSetting up {repo_name} at {repo}", flush=True)
    if not repo.exists():
        REPOS_DIR.mkdir(parents=True, exist_ok=True)
        if source.exists() and source.resolve() != repo.resolve():
            dirty = checked_output(["git", "diff", "HEAD", "--"], source)
            if dirty:
                raise RuntimeError(
                    f"{source} has tracked edits; preserve/review them before local migration."
                )
            pinned = checked_output(["git", "rev-parse", "HEAD"], source)
            checked_output(
                ["git", "clone", "--no-hardlinks", "--no-checkout", str(source), str(repo)]
            )
            checked_output(["git", "checkout", "--detach", pinned], repo)
        else:
            checked_output(["git", "clone", config["url"], str(repo)])
            checked_output(["git", "checkout", "--detach", config["commit"]], repo)
    commit = checked_output(["git", "rev-parse", "HEAD"], repo)
    if not commit.startswith(config["commit"]):
        raise RuntimeError(
            f"{repo_name}: expected commit {config['commit']}, found {commit}."
        )
    python = python_for(repo)
    state_path = repo / "setup_state.json"
    state = read_json(state_path)
    if python.exists() and not refresh:
        current = fingerprint(repo)
        if state.get("environment_id") == current["id"]:
            print("Reusing verified environment; no package downloads or upgrades.", flush=True)
            return current

    # Do not mutate an environment that already has detection evidence.
    if any((repo / "results").glob("*_run_*.xml")):
        raise RuntimeError(
            "Environment is unverified/changed with existing results. "
            "Use a fresh --work-dir; old evidence is preserved."
        )

    if not python.exists():
        checked_output([sys.executable, "-m", "venv", str(repo / ".venv")])

    bootstrap = config.get("bootstrap_pkgs", [])
    if bootstrap:
        _, _, code = run_command(
            [
                str(python), "-m", "pip", "install",
                "--disable-pip-version-check",
            ] + bootstrap,
            cwd=repo,
            log_path=repo / "logs" / "setup-bootstrap.log",
        )
        if code:
            raise RuntimeError(
                f"Bootstrap dependency installation failed. See {repo / 'logs'}"
            )

    specs = dependency_specs(repo_name, repo, config)
    install_target = config.get(
        "install_target",
        ".[brotli,cli,http2,socks,zstd]" if repo_name == "httpx" else ".",
    )
    cmd = [
        str(python), "-m", "pip", "install", "--disable-pip-version-check",
        "-e", install_target,
    ] + specs
    if config.get("constraint_lock"):
        cmd += ["-c", str(lockfile_constraints(repo, config["constraint_lock"]))]
    # Reuse pinned versions from an existing completed environment when available.
    # HTTPX's requirements supply explicit test pins; constraints do not replace them.
    lock = BASE_DIR / "environment-locks" / f"{repo_name}.txt"
    snapshot = lock if lock.exists() else source / "env_snapshot.txt"
    if snapshot.exists() and (lock.exists() or source.resolve() != repo.resolve()):
        pins = [
            line
            for line in snapshot.read_text(encoding="utf-8").splitlines()
            if re.match(r"^[A-Za-z0-9_.-]+==[^ ]+$", line)
            and not line.lower().startswith(("pip==", "setuptools==", "wheel=="))
        ]
        constraints = repo / "migration_constraints.txt"
        constraints.write_text("\n".join(pins) + "\n", encoding="utf-8")
        cmd += ["-c", str(constraints)]
    install_log = repo / "logs" / "setup-install.log"
    if config.get("installer") == "uv":
        # Use each upstream project's committed uv.lock and test dependency group.
        uv_version = config.get("uv_version", "0.11.7")
        _, _, code = run_command(
            [
                str(python), "-m", "pip", "install", "--disable-pip-version-check",
                f"uv=={uv_version}",
            ],
            cwd=repo,
            log_path=install_log,
        )
        if code == 0:
            uv = python.parent / ("uv.exe" if os.name == "nt" else "uv")
            uv_env = os.environ.copy()
            uv_env["UV_PROJECT_ENVIRONMENT"] = str(repo / ".venv")
            sync_args = config.get("uv_sync_args", [])
            _, _, code = run_command(
                [str(uv), "sync"] + sync_args,
                cwd=repo,
                env=uv_env,
                log_path=repo / "logs" / "setup-uv-sync.log",
            )
        if code == 0:
            _, _, code = run_command(
                [
                    str(python), "-m", "pip", "install",
                    "--disable-pip-version-check",
                ] + specs,
                cwd=repo,
                log_path=repo / "logs" / "setup-randomly.log",
            )

    else:
        _, _, code = run_command(cmd, cwd=repo, log_path=install_log)
    if code:
        raise RuntimeError(f"Dependency installation failed. See {repo / 'logs'}")
    checked_output([python, "-m", "pip", "check"], repo)
    # Require the package itself plus the repository's test distributions.
    packages = config.get("verify_pkgs", [repo_name] + config["extra_pkgs"])
    packages = [re.split(r"[<>=!~;\[]", name, maxsplit=1)[0] for name in packages]
    checked_output(
        [
            python,
            "-c",
            "from importlib.metadata import version; "
            + "print({name: version(name) for name in "
            + repr(packages)
            + "})",
        ],
        repo,
    )
    current = fingerprint(repo)
    (repo / "env_snapshot.txt").write_text(
        "\n".join(current["packages"]) + "\n", encoding="utf-8"
    )
    (repo / "environment.json").write_text(
        __import__("json").dumps(current, indent=2), encoding="utf-8"
    )
    setup_log = repo / "setup_log.md"
    if setup_log.exists():
        archive = (
            repo
            / "logs"
            / ("setup-before-" + datetime.now().strftime("%Y%m%dT%H%M%S") + ".md")
        )
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(setup_log.read_bytes())
    setup_log.write_text(
        f"# Setup Log: {repo_name}\n\n"
        f"- **Repository**: {config['url']}\n"
        f"- **Pinned Commit Hash**: {commit}\n"
        f"- **Python Version**: {current['python']}\n"
        f"- **Execution Directory**: {repo}\n"
        f"- **OS**: {current['platform']}\n"
        f"- **Environment ID**: {current['id']}\n"
        f"- **Setup Date**: {datetime.now(timezone.utc).isoformat()}\n"
        "- **Source modifications**: No compatibility patches applied by setup.\n"
        "- **Installation log**: logs/setup-install.log\n"
        "- **Environment Snapshot**: env_snapshot.txt and environment.json\n",
        encoding="utf-8",
    )
    atomic_json(
        repo / "baseline_state.json",
        {"status": "NEEDS_BASELINE", "environment_id": current["id"]},
    )
    atomic_json(state_path, {"environment_id": current["id"], "commit": commit})
    print("Environment verified and saved.", flush=True)
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", choices=REPO_NAMES)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Reinstall test dependencies (only before detection).",
    )
    args = parser.parse_args()
    for name in [args.repo] if args.repo else REPO_NAMES:
        setup_repo(name, REPOS[name], refresh=args.refresh)


if __name__ == "__main__":
    main()
