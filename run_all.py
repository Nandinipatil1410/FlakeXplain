#!/usr/bin/env python3
"""Run FlakeXplain with local execution storage and resumable stages."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "scripts"))
from runtime import REPOS, default_work_dir, pipeline_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", choices=REPOS)
    parser.add_argument("--work-dir", type=Path, default=default_work_dir(),
                        help="Execution root containing repos/. Defaults to local AppData on Windows.")
    parser.add_argument("--refresh-setup", action="store_true")
    parser.add_argument("--force-baseline", action="store_true")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Prepare and verify the baseline without starting the 25 rounds.")
    parser.add_argument("--reverse-rounds", type=int, default=1,
                        help="Reverse-order rounds for detection (default: 1).")
    args = parser.parse_args()
    if args.reverse_rounds < 1:
        parser.error("--reverse-rounds must be at least 1")
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["FLAKEXPLAIN_REPOS_DIR"] = str(work / "repos")
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    print(f"Execution storage: {work}\nReport: {BASE_DIR / 'FlakeXplain_Flaky_Report.md'}", flush=True)
    failures = []
    for repo in [args.repo] if args.repo else REPOS:
        with pipeline_lock(work, repo):
            stages = [("setup_repos.py", ["--refresh"] if args.refresh_setup else []),
                      ("baseline_gate.py", ["--force"] if args.force_baseline else [])]
            if not args.baseline_only:
                stages.append(
                    ("idflakies_runner.py", ["--reverse-rounds", str(args.reverse_rounds)])
                )
            for script, extra in stages:
                print(f"\nRUNNING {script} [{repo}]", flush=True)
                cmd = [sys.executable, "-u", str(BASE_DIR / "scripts" / script), repo] + extra
                result = subprocess.run(cmd, cwd=BASE_DIR, env=env)
                if result.returncode:
                    failures.append(repo)
                    print(f"{repo}: stopped at {script}; see the live output and logs.", flush=True)
                    break
    if not args.baseline_only:
        # One report writer after repository execution; no races between stages.
        result = subprocess.run([sys.executable, "-u", str(BASE_DIR / "scripts/parse_results.py")],
                                cwd=BASE_DIR, env=env)
        if result.returncode:
            raise SystemExit(result.returncode)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
