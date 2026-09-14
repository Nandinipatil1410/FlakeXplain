#!/usr/bin/env python3
"""Clean original-order baseline gate, with fail-fast retries and validated reuse."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import time
import xml.etree.ElementTree as ET

from runtime import (REPOS, REPOS_DIR, atomic_json, baseline_state, complete_xml, fingerprint,
                     pytest_args, pytest_command, pytest_env, run_command)


def verify_baseline(repo_name, force=False):
    repo = REPOS_DIR / repo_name
    current = fingerprint(repo)
    state = baseline_state(repo, current)
    if state and not force:
        print(f"{repo_name}: reusing PASSED baseline for unchanged environment.", flush=True)
        return True, state["collected_count"], state["passing_attempt"], state["duration"]
    # Invalidate any old pass before attempting a fresh baseline.
    atomic_json(repo / "baseline_state.json", {"status": "RUNNING", "environment_id": current["id"]})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = repo / "logs" / ("baseline-" + stamp)
    log_dir.mkdir(parents=True, exist_ok=True)
    passing_attempt = None
    count = 0
    elapsed = 0.0
    attempts = []
    for attempt in range(1, 4):
        print(f"\n--- Baseline Attempt {attempt}/3 for {repo_name} ---", flush=True)
        xml = log_dir / f"attempt_{attempt}.xml"
        # A failed suite cannot pass the gate; stop at its first failure.
        # Every successful attempt must still execute the complete collected suite.
        cmd = pytest_command(repo_name, repo) + [
            "-p", "no:randomly", "-p", "no:cov", "--tb=short", "-q", "-x",
            "--durations=15", f"--junitxml={xml}",
        ]
        cmd += pytest_args(repo_name)
        start = time.monotonic()
        _, _, code = run_command(cmd, cwd=repo, env=pytest_env(repo),
                                 log_path=log_dir / f"attempt_{attempt}.log")
        elapsed = time.monotonic() - start
        attempts.append({"attempt": attempt, "exit_code": code, "duration": elapsed,
                         "xml_file": str(xml.relative_to(repo))})
        print(f"Attempt {attempt}: {elapsed:.2f}s, exit code {code}", flush=True)
        if code == 0 and complete_xml(xml):
            cases = ET.parse(xml).getroot().findall(".//testcase")
            if not any(case.find("failure") is not None or case.find("error") is not None for case in cases):
                count = len(cases)
                # Do not open the gate for an entirely skipped suite.
                if any(case.find("skipped") is None for case in cases):
                    passing_attempt = attempt
                    break
        if code not in (0, 1):
            print("Collection/interruption/infrastructure error; stopping baseline retries.", flush=True)
            break
    passed = passing_attempt is not None
    state = dict(status="PASSED" if passed else "FAILED", environment_id=current["id"],
                 collected_count=count, passing_attempt=passing_attempt, duration=elapsed,
                 attempts=attempts, xml_file=attempts[-1]["xml_file"])
    atomic_json(repo / "baseline_state.json", state)
    status = f"PASSED (Attempt {passing_attempt}, {elapsed:.2f}s)" if passed else "FAILED (Discarded)"
    with (repo / "setup_log.md").open("a", encoding="utf-8") as log:
        log.write(f"\n## Step 2 Baseline Gate Results\n"
                  f"- **Total Collected Tests**: {count if passed else 'Unknown (attempt stopped early)'}\n"
                  f"- **Baseline Gate Status**: {status}\n"
                  f"- **Passing Attempt**: {passing_attempt}\n"
                  f"- **Baseline Wall-Clock Duration**: {elapsed:.2f} seconds\n"
                  f"- **Baseline Evidence**: {log_dir.relative_to(repo)}\n")
    print(f"{repo_name}: {status}", flush=True)
    return passed, count, passing_attempt, elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", choices=REPOS)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    success = True
    for name in [args.repo] if args.repo else REPOS:
        passed, *_ = verify_baseline(name, force=args.force)
        success = passed and success
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
