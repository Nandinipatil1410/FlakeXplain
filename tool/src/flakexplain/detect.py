"""`flakexplain detect`: the iDFlakies-style protocol of the FlakeXplain study, for any pytest project.

1. Baseline gate: the suite must pass cleanly in original order (up to 3 attempts), or detection stops.
2. Rounds: original order, random order (seeded), reverse order, each writing JUnit XML.
3. Classification: a test with at least one pass and one failure/error is observed flaky:
   OD if it fails only under reordering, NOD if it also fails in original order.
   Consistently passing tests are "not observed flaky after N runs", never proven non-flaky.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_ARGS = ["-p", "no:randomly", "-p", "no:cov", "--tb=short", "-q"]


def pytest_env(project):
    env = os.environ.copy()
    paths = [str(project / p) for p in ("tasks", "tests", "src", ".") if (project / p).is_dir()]
    env["PYTHONPATH"] = os.pathsep.join(paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PYTHONUNBUFFERED"] = "1"
    return env


def parse_junit(path):
    """{test_id: PASS|FAIL|ERROR|SKIP}, or None when the file is missing, broken or has no test cases."""
    try:
        cases = ET.parse(path).getroot().findall(".//testcase")
    except (OSError, ET.ParseError):
        return None
    if not cases or any(c.find("error[@message='collection failure']") is not None for c in cases):
        return None
    out = {}
    for c in cases:
        name, classname, file = c.get("name", ""), c.get("classname", ""), c.get("file", "")
        test_id = f"{file}::{name}" if file else f"{classname}::{name}" if classname else name
        if c.find("failure") is not None:
            out[test_id] = "FAIL"
        elif c.find("error") is not None:
            out[test_id] = "ERROR"
        elif c.find("skipped") is not None:
            out[test_id] = "SKIP"
        else:
            out[test_id] = "PASS"
    return out


def run_pytest(project, out_dir, name, extra, pytest_args, log):
    xml = out_dir / f"{name}.xml"
    cmd = [sys.executable, "-m", "pytest", *BASE_ARGS, f"--junitxml={xml}", *extra, *pytest_args]
    start = time.monotonic()
    with open(out_dir / f"{name}.log", "w", encoding="utf-8") as f:
        code = subprocess.run(cmd, cwd=project, env=pytest_env(project), stdout=f, stderr=subprocess.STDOUT).returncode
    elapsed = time.monotonic() - start
    log(f"  {name}: exit {code}, {elapsed:.1f}s")
    return code, xml, elapsed


def baseline(project, out_dir, pytest_args, log, attempts=3):
    """Return the passing baseline's test count, or None when the gate stays closed."""
    for attempt in range(1, attempts + 1):
        code, xml, _ = run_pytest(project, out_dir, f"baseline_{attempt}", [], pytest_args, log)
        outcomes = parse_junit(xml)
        if code == 0 and outcomes and "FAIL" not in outcomes.values() and "ERROR" not in outcomes.values():
            # An entirely skipped suite does not open the gate.
            if any(s == "PASS" for s in outcomes.values()):
                return len(outcomes)
        if code not in (0, 1):
            log(f"  pytest exit {code} (collection, interruption or usage error); not retrying.")
            break
    return None


def plan(original, randomised, reverse, seed):
    rng = random.Random(seed)
    rounds = [("original-order", f"original_run_{i}", []) for i in range(1, original + 1)]
    for i in range(1, randomised + 1):
        s = rng.randint(100000, 999999)
        rounds.append(("random-order", f"random_run_{i}", ["-p", "flakexplain.order_plugin", "--fx-order=random", f"--fx-seed={s}"]))
    rounds += [("reverse-order", f"reverse_run_{i}", ["-p", "flakexplain.order_plugin", "--fx-order=reverse"]) for i in range(1, reverse + 1)]
    return rounds


def classify(round_outcomes):
    """round_outcomes: [(config, round_name, {test_id: status})]. Mirrors scripts/parse_results.py."""
    records = defaultdict(list)
    for config, name, outcomes in round_outcomes:
        for test_id, status in outcomes.items():
            records[test_id].append(dict(config=config, round=name, status=status))
    flaky, not_observed, unlabelled = {}, [], []
    for test_id, recs in records.items():
        active = {r["status"] for r in recs if r["status"] != "SKIP"}
        if "PASS" in active and active & {"FAIL", "ERROR"}:
            by = {c: {r["status"] for r in recs if r["config"] == c and r["status"] != "SKIP"}
                  for c in ("original-order", "random-order", "reverse-order")}
            failed = lambda c: bool(by[c] & {"FAIL", "ERROR"})
            if failed("original-order"):
                kind, reason = "NOD", "Fails in original order too, so not explained by test order"
            elif (failed("random-order") or failed("reverse-order")) and by["original-order"] == {"PASS"}:
                kind, reason = "OD", "Fails only when the test order changes"
            else:
                kind, reason = "Unclassified", "Mixed behaviour; more reruns are needed"
            fails = [r["round"] for r in recs if r["status"] in ("FAIL", "ERROR")]
            flaky[test_id] = dict(classification=kind, reason=reason, runs=len(recs),
                                  failures=len(fails), failed_rounds=fails)
        elif active == {"PASS"}:
            not_observed.append(test_id)
        else:
            unlabelled.append(test_id)  # skip-only or failure-only: no label
    return flaky, not_observed, unlabelled


def report_markdown(summary):
    s = summary
    lines = [
        "# FlakeXplain detection report", "",
        f"- Project: `{s['project']}`", f"- Commit: `{s['commit']}`", f"- Finished: {s['finished_utc']}",
        f"- Rounds: {s['rounds']['original']} original, {s['rounds']['random']} random (seed {s['seed']}), "
        f"{s['rounds']['reverse']} reverse",
        f"- Tests seen: {s['tests']}", "",
        "| Observed flaky | OD | NOD | Unclassified | Not observed flaky | Unlabelled |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {s['observed_flaky']} | {s['od']} | {s['nod']} | {s['unclassified']} | {s['not_observed_flaky']} | {s['unlabelled']} |",
        "",
    ]
    if s["flaky"]:
        lines += ["## Observed flaky tests", "", "| Test | Type | Failed runs | Why |", "|---|---|---:|---|"]
        for test_id, d in sorted(s["flaky"].items()):
            lines.append(f"| `{test_id}` | {d['classification']} | {d['failures']}/{d['runs']} | {d['reason']} |")
        lines.append("")
    lines += [
        "## How to read this", "",
        f"- **Not observed flaky** means the test passed in all {s['total_rounds']} rounds; it is not proof that it can never flake.",
        "- **OD** (order-dependent) tests usually share state with other tests: global variables, files, caches or fixtures.",
        "- **NOD** tests usually depend on time, concurrency, randomness or the network.",
        "- **Unlabelled** tests were skipped in every round, or failed in every round.", "",
    ]
    return "\n".join(lines)


def git_commit(project):
    r = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def detect(project, out_dir, original=12, randomised=12, reverse=1, seed=42, pytest_args=(), log=print):
    project, out_dir = Path(project).resolve(), Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"Baseline gate (up to 3 clean original-order runs) in {project}")
    count = baseline(project, out_dir, list(pytest_args), log)
    if count is None:
        log("Baseline failed: the suite does not pass cleanly, so flaky tests cannot be told apart from broken ones.\n"
            f"Fix or deselect the failing tests (logs in {out_dir}), then run detect again.")
        return None
    log(f"Baseline passed with {count} tests. Running {original + randomised + reverse} rounds.")
    results = []
    for i, (config, name, extra) in enumerate(plan(original, randomised, reverse, seed), 1):
        log(f"[{i}/{original + randomised + reverse}] {config}")
        code, xml, _ = run_pytest(project, out_dir, name, extra, list(pytest_args), log)
        outcomes = parse_junit(xml)
        if code not in (0, 1) or outcomes is None:
            log(f"  round {name} did not complete (exit {code}); it is left out of the evidence.")
            continue
        results.append((config, name, outcomes))
    flaky, not_observed, unlabelled = classify(results)
    rounds = {c: sum(1 for r in results if r[0] == f"{c}-order") for c in ("original", "random", "reverse")}
    summary = dict(project=str(project), commit=git_commit(project), finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   seed=seed, rounds=rounds, total_rounds=len(results), tests=len({t for r in results for t in r[2]}),
                   observed_flaky=len(flaky), od=sum(d["classification"] == "OD" for d in flaky.values()),
                   nod=sum(d["classification"] == "NOD" for d in flaky.values()),
                   unclassified=sum(d["classification"] == "Unclassified" for d in flaky.values()),
                   not_observed_flaky=len(not_observed), unlabelled=len(unlabelled), flaky=flaky)
    (out_dir / "results.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(report_markdown(summary), encoding="utf-8")
    return summary
