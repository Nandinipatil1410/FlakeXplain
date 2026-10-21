"""Command-line interface: `flakexplain detect` and `flakexplain triage`."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

from . import __version__

CAVEAT = ("Scores come from ET-BF trained on 1,292 rerun-labelled CI failures from 8 open-source projects (FlakeXplain v0.8). "
          "They are advice, not proof: a 'likely flaky' failure can still be a real bug. "
          "Accuracy is much higher for tests with recorded failure history, so keep the history file between runs.")


def cmd_detect(args):
    from .detect import detect
    out = args.out or Path(args.path) / ".flakexplain" / "detect"
    summary = detect(args.path, out, args.original, args.random, args.reverse, args.seed, args.pytest_args)
    if summary is None:
        return 2
    print(f"\n{summary['observed_flaky']} observed flaky ({summary['od']} OD, {summary['nod']} NOD, "
          f"{summary['unclassified']} unclassified); {summary['not_observed_flaky']} not observed flaky "
          f"after {summary['total_rounds']} rounds; {summary['unlabelled']} unlabelled.")
    for test_id, d in sorted(summary["flaky"].items()):
        print(f"  {d['classification']:<12} {d['failures']}/{d['runs']} failed  {test_id}")
    print(f"Report: {Path(out).resolve() / 'report.md'}")
    return 1 if args.fail_on_flaky and summary["observed_flaky"] else 0


def text_report(result):
    lines = [f"FlakeXplain triage: {len(result['failures'])} failed test(s)"]
    for n in result["notes"]:
        lines.append(f"note: {n}")
    for r in result["failures"]:
        lines.append(f"\n{r['verdict'].upper():<20} P(flaky)={r['p_flaky']:.2f}  {r['nodeid']}")
        for z in r["reasons"]:
            arrow = "towards flaky" if z["contribution"] > 0 else "towards real"
            lines.append(f"    {z['contribution']:+.3f} {arrow:<13} {z['label']} = {z['value']:g}")
    lines.append(f"\nExplanations: {result['explanation_method']}. {CAVEAT}")
    return "\n".join(lines)


def markdown_report(result):
    flaky = [r for r in result["failures"] if r["verdict"] == "likely flaky"]
    lines = [f"### FlakeXplain triage: {len(flaky)} of {len(result['failures'])} failure(s) look flaky", "",
             "| Verdict | P(flaky) | Test | Main reasons |", "|---|---:|---|---|"]
    for r in sorted(result["failures"], key=lambda r: -r["p_flaky"]):
        why = "; ".join(f"{z['label']} = {z['value']:g} ({'+' if z['contribution'] > 0 else '-'})" for z in r["reasons"][:3])
        lines.append(f"| {'🔁 likely flaky' if r['verdict'] == 'likely flaky' else '🐞 likely real'} | {r['p_flaky']:.2f} | `{r['nodeid']}` | {why} |")
    lines += [""] + [f"> Note: {n}" for n in result["notes"]]
    lines += ["", f"<sub>(+) pushes towards flaky, (-) towards real; {result['explanation_method']}. {CAVEAT}</sub>"]
    return "\n".join(lines)


def cmd_triage(args):
    from . import history as hist
    from .features import extract, from_junit, from_log, git
    from .model import load, predict

    rc, top = git(args.repo, "rev-parse", "--show-toplevel")
    if rc:
        print(f"error: {args.repo} is not inside a git repository", file=sys.stderr)
        return 2
    root = Path(top.strip())
    head = args.head
    base = args.base
    if base is None:
        rc, parent = git(root, "rev-parse", head + "^")
        base = parent.strip() if rc == 0 else None  # Actions checks out PRs as a merge commit: HEAD^ is the base
    notes = []
    if base is None:
        notes.append("No base commit (fetch at least 2 commits, e.g. actions/checkout with fetch-depth: 2); diff features are unavailable.")
    if args.log:
        failures, duration = from_log(Path(args.log).read_text(encoding="utf-8", errors="replace"))
    else:
        py_files = set(git(root, "ls-files", "*.py")[1].splitlines())
        failures, duration = from_junit(args.junit, py_files)
    if args.job_duration is not None:
        duration = args.job_duration
    elif duration is not None:
        notes.append("Job duration was not given, so the test session time from the report is used; pass --job-duration for best results.")
    if not failures:
        result = dict(failures=[], notes=["No failed tests found in the report."], explanation_method="none")
        print(json.dumps(result, indent=1) if args.format == "json" else "FlakeXplain triage: no failed tests found.")
        return 0
    if len(failures) > 5:
        notes.append(f"{len(failures)} tests failed in this job. Mass failures usually have one shared cause; check the first failure first.")
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID") or datetime.datetime.now(datetime.timezone.utc).strftime("local-%Y%m%dT%H%M%S")
    pr = args.pr if args.pr is not None else os.environ.get("GITHUB_EVENT_NAME", "").startswith("pull_request")
    history_path = Path(args.history) if args.history else root / ".flakexplain" / "history.jsonl"
    history = hist.load(history_path)
    if not history:
        notes.append(f"No failure history at {history_path}; every failure is treated as new. Keep this file between CI runs.")
    when = datetime.datetime.now(datetime.timezone.utc)
    from .features import PREVIOUS_STATE
    rows = extract(failures, repo=root, base=base, tree=head, source_root=root, repo_name=root.name,
                   roots=[root.as_posix()] + list(args.rootdir), history=history, run_id=run_id, when=when,
                   previous_state=PREVIOUS_STATE[args.previous_state], job_duration_s=duration or 0.0, pr_build=pr)
    model, card = load()
    method, rows = predict(model, rows)
    result = dict(version=__version__, model=card["name"], run_id=run_id, head=head, base=base, notes=notes,
                  explanation_method=method, failures=rows)
    if not args.no_record:
        hist.record(history_path, [n for n, _ in failures], run_id, when)
    out = {"json": lambda: json.dumps(result, indent=1), "markdown": lambda: markdown_report(result), "text": lambda: text_report(result)}[args.format]()
    if args.output:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
    else:
        print(out)
    return 1 if args.fail_on_real and any(r["verdict"] == "likely real failure" for r in rows) else 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="flakexplain", description=__doc__)
    p.add_argument("--version", action="version", version=f"flakexplain {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("detect", help="Find flaky tests by rerunning the suite in original, random and reverse order.",
                       description="Find flaky tests by rerunning the suite in original, random and reverse order. "
                                   "Extra arguments after -- go to pytest, e.g. `flakexplain detect -- tests/unit`.")
    d.add_argument("path", nargs="?", default=".", help="Project directory (default: current directory).")
    d.add_argument("--original", type=int, default=12, help="Original-order rounds (default 12).")
    d.add_argument("--random", type=int, default=12, help="Random-order rounds (default 12).")
    d.add_argument("--reverse", type=int, default=1, help="Reverse-order rounds (default 1).")
    d.add_argument("--seed", type=int, default=42, help="Seed for the random-order seeds (default 42).")
    d.add_argument("--out", type=Path, help="Output directory (default: <path>/.flakexplain/detect).")
    d.add_argument("--fail-on-flaky", action="store_true", help="Exit 1 if any flaky test is observed.")
    d.add_argument("pytest_args", nargs="*", help=argparse.SUPPRESS)
    d.set_defaults(func=cmd_detect)

    t = sub.add_parser("triage", help="Score each failed test of a CI run as likely flaky or likely real.")
    src = t.add_mutually_exclusive_group(required=True)
    src.add_argument("--log", help="pytest console output saved from the run (best: matches the training data).")
    src.add_argument("--junit", help="JUnit XML report from pytest --junitxml.")
    t.add_argument("--repo", default=".", help="Path inside the git checkout that was tested (default: .).")
    t.add_argument("--head", default="HEAD", help="Commit that was tested (default: HEAD).")
    t.add_argument("--base", help="Commit to diff against (default: HEAD^).")
    t.add_argument("--history", help="Failure history file (default: <repo>/.flakexplain/history.jsonl).")
    t.add_argument("--no-record", action="store_true", help="Do not add this run's failures to the history.")
    t.add_argument("--run-id", help="Identifier of this CI run (default: $GITHUB_RUN_ID or a timestamp).")
    t.add_argument("--previous-state", choices=["passed", "failed", "none", "other"], default="none",
                   help="Result of the previous run of this workflow on this branch (default: none).")
    t.add_argument("--job-duration", type=float, help="Whole CI job duration in seconds.")
    pr = t.add_mutually_exclusive_group()
    pr.add_argument("--pr", dest="pr", action="store_true", default=None, help="This was a pull-request build.")
    pr.add_argument("--push", dest="pr", action="store_false", help="This was a push build.")
    t.add_argument("--rootdir", action="append", default=[], help="Extra absolute checkout path that appears in tracebacks.")
    t.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    t.add_argument("--output", help="Write the report to this file instead of stdout.")
    t.add_argument("--fail-on-real", action="store_true", help="Exit 1 if any failure looks real.")
    t.set_defaults(func=cmd_triage)

    args, extra = p.parse_known_args(argv)
    if args.command == "detect":
        args.pytest_args = list(args.pytest_args) + [a for a in extra if a != "--"]
    elif extra:
        p.error("unrecognized arguments: " + " ".join(extra))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
