#!/usr/bin/env python3
"""Serial original, random and reverse rounds with validated checkpoints."""
from __future__ import annotations
import argparse
import random
import shutil
import time
from datetime import datetime, timezone

from runtime import (BASE_DIR, REPOS, REPOS_DIR, atomic_json, baseline_state, complete_xml,
                     fingerprint, python_for, pytest_args, pytest_env, read_json, run_command)

DEFAULT_ORIGINAL_ROUNDS = 12
DEFAULT_RANDOM_ROUNDS = 12
DEFAULT_REVERSE_ROUNDS = 1


def round_plan(repo_name, orig_rounds=12, rand_rounds=12, reverse_rounds=1):
    for number in range(1, orig_rounds + 1):
        yield "original-order", number, None, f"original_run_{number}.xml"
    rng = random.Random(42 + len(repo_name))
    for number in range(1, rand_rounds + 1):
        yield "random-order", number, rng.randint(100000, 999999), f"random_run_{number}.xml"
    for number in range(1, reverse_rounds + 1):
        yield "reverse-order", number, None, f"reverse_run_{number}.xml"


def manifest_reverse_rounds(manifest):
    """Read new plural records while remaining compatible with old manifests."""
    if "reverse_rounds" in manifest:
        return manifest["reverse_rounds"]
    return [manifest["reverse_round"]] if manifest.get("reverse_round") else []


def reusable(record, xml, config, number, seed, count):
    return bool(record and record.get("exit_code") in (0, 1)
                and record.get("config") == config and record.get("round") == number
                and record.get("seed") == seed and record.get("xml_file") == xml.name
                and complete_xml(xml, count))


def run_idflakies_suite(
    repo_name, orig_rounds=12, rand_rounds=12, reverse_rounds=1
):
    repo = REPOS_DIR / repo_name
    current = fingerprint(repo)
    baseline = baseline_state(repo, current)
    if not baseline:
        raise RuntimeError(f"{repo_name}: no complete passing baseline for this environment.")
    results = repo / "results"
    results.mkdir(parents=True, exist_ok=True)
    manifest_path = results / "execution_manifest.json"
    manifest = read_json(manifest_path)
    if manifest and manifest.get("environment_id") != current["id"]:
        raise RuntimeError("Existing detection evidence belongs to an unverified/different environment; use a fresh --work-dir.")
    if not manifest and any(results.glob("*_run_*.xml")):
        raise RuntimeError("Legacy XML has no verified environment manifest; use a fresh --work-dir.")
    if not manifest:
        manifest = dict(repo_name=repo_name, environment_id=current["id"], environment=current,
                        baseline_xml=baseline["xml_file"], collected_count=baseline["collected_count"],
                        original_rounds=[], random_rounds=[], reverse_rounds=[],
                        reverse_round=None,
                        total_wall_clock_seconds=0.0)
        atomic_json(manifest_path, manifest)
    shutil.copyfile(BASE_DIR / "scripts" / "reverse_plugin.py", repo / "conftest_reverse.py")
    records = {item["xml_file"]: item for item in
               manifest["original_rounds"] + manifest["random_rounds"]
               + manifest_reverse_rounds(manifest)}
    plan = list(round_plan(repo_name, orig_rounds, rand_rounds, reverse_rounds))
    for index, (config, number, seed, filename) in enumerate(plan, 1):
        xml = results / filename
        if reusable(records.get(filename), xml, config, number, seed, baseline["collected_count"]):
            print(f"[{index}/{len(plan)}] Reusing completed {filename}", flush=True)
            continue
        # Preserve incomplete evidence; it is never considered a completed round.
        if xml.exists():
            archive = results / "incomplete"
            archive.mkdir(exist_ok=True)
            xml.replace(archive / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ-") + filename))
        cmd = [python_for(repo), "-u", "-m", "pytest", "-p", "no:cov", "--tb=short", "-q",
               "--durations=15", f"--junitxml={xml}"]
        if config == "random-order":
            cmd += [f"--randomly-seed={seed}"]
        else:
            cmd += ["-p", "no:randomly"]
        if config == "reverse-order":
            cmd += ["-p", "conftest_reverse"]
        cmd += pytest_args(repo_name)
        print(f"\n[{index}/{len(plan)}] Starting {config} round {number}, seed={seed}", flush=True)
        start = time.monotonic()
        _, _, code = run_command(cmd, cwd=repo, env=pytest_env(repo),
                                 log_path=repo / "logs" / filename.replace(".xml", ".log"))
        elapsed = time.monotonic() - start
        if code not in (0, 1) or not complete_xml(xml, baseline["collected_count"]):
            raise RuntimeError(f"Incomplete/invalid round {filename} (exit {code}); checkpoint not committed.")
        record = dict(round=number, config=config, seed=seed, xml_file=filename,
                      exit_code=code, duration_seconds=round(elapsed, 2))
        records[filename] = record
        manifest["original_rounds"] = [r for r in records.values() if r["config"] == "original-order"]
        manifest["random_rounds"] = [r for r in records.values() if r["config"] == "random-order"]
        manifest["reverse_rounds"] = sorted(
            (r for r in records.values() if r["config"] == "reverse-order"),
            key=lambda r: r["round"],
        )
        # Retain the legacy field so older report readers still see round 1.
        manifest["reverse_round"] = (
            manifest["reverse_rounds"][0] if manifest["reverse_rounds"] else None
        )
        manifest["total_wall_clock_seconds"] = round(sum(r["duration_seconds"] for r in records.values()), 2)
        atomic_json(manifest_path, manifest)
        print(f"Completed in {elapsed:.2f}s; checkpoint saved.", flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", choices=REPOS)
    parser.add_argument(
        "--reverse-rounds",
        type=int,
        default=DEFAULT_REVERSE_ROUNDS,
        help="Number of reverse-order rounds (default: 1).",
    )
    args = parser.parse_args()
    if args.reverse_rounds < 1:
        parser.error("--reverse-rounds must be at least 1")
    for name in [args.repo] if args.repo else REPOS:
        run_idflakies_suite(name, reverse_rounds=args.reverse_rounds)


if __name__ == "__main__":
    main()
