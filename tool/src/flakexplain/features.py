"""Features of a failed CI test execution, as defined for ET-BF in the v0.8 study.

Each function mirrors scripts/mdflaker_v08_features.py (and the strict history of
scripts/mdflaker_v08_robustness.py); scripts/check_tool_parity.py checks the match on the v0.8 data.
Only evidence available when the failure happens is used: the log, the diff, the test source and
failures recorded in earlier runs. Rerun outcomes are never features.
"""
from __future__ import annotations

import datetime
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from .smells import test_size, test_smells
from .source_index import SourceIndex

B_COLS = ["flaky_frequency", "traceback_coverage", "test_smells", "previous_state", "test_size"]
F_COLS = ["build_failed_tests", "same_file_cofailures", "job_duration_s", "pr_build", "changed_files", "changed_py_files",
          "changed_test_py_files", "nonpy_only_change", "changed_lines", "own_test_file_changed", "path_overlap_depth",
          "traceback_frames", "frames_in_changed_files", "last_frame_in_test_file", "frames_outside_repo",
          "min_line_distance_to_change", "diff_available"]
COLUMNS = B_COLS + F_COLS
PREVIOUS_STATE = {"passed": 0, "failed": 1, "none": 2, "other": 3}
CAP = 1000
ISOLATED_MAX = 5  # in v0.8 only one failure per job with more failures was kept, so co-failures were 0 there

ANSI = re.compile(r"\x1b\[[0-9;]*m|\[[0-9;]*m(?=\S)")
STAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ")
FAILED = [re.compile(r"^(?:FAILED|ERROR) (\S+?\.py::\S+)"), re.compile(r"^(\S+?\.py::\S+) (?:FAILED|ERROR)\b")]
FRAME_PYTEST = re.compile(r"^(\S+\.py):(\d+): in (\S+)")
FRAME_NATIVE = re.compile(r'File "([^"]+\.py)", line (\d+), in (\S+)')
DURATION = re.compile(r"=+ .*\bin ([\d.]+)s\b")


def clean_lines(text):
    return [ANSI.sub("", STAMP.sub("", line)) for line in text.splitlines()]


def norm_node(nodeid):
    file, sep, rest = nodeid.partition("::")
    return file.replace("\\", "/") + sep + rest


def failed_tests(lines):
    """Failed node IDs from pytest's short test summary (`FAILED path::test - msg`)."""
    tests = set()
    for line in lines:
        line = line.strip()
        for rx in FAILED:
            m = rx.match(line)
            if m:
                tests.add(m.group(1).split(" - ")[0])
    return sorted(tests)


def report_sections(lines):
    """[(title, frames)] for each `____ title ____` report section, in log order, in one pass."""
    sections, current = [], None
    for line in lines:
        s = line.strip()
        if re.match(r"^_{3,} .+ _{3,}$", s):
            current = (s.strip("_ "), [])
            sections.append(current)
            continue
        if re.match(r"^={3,}", s):
            current = None
        if current is not None:
            m = FRAME_PYTEST.match(s) or FRAME_NATIVE.search(s)
            if m:
                current[1].append((m.group(1).replace("\\", "/"), int(m.group(2))))
    return sections


def traceback_frames(sections, nodeid):
    """Frames of the failing test's report sections, as (path, line)."""
    name = nodeid.split("::")[-1]
    return [f for title, frames in sections
            if title == name or title.endswith("." + name) or title.endswith("::" + name) for f in frames]


def frames_from_text(text):
    frames = []
    for s in clean_lines(text):
        s = s.strip()
        m = FRAME_PYTEST.match(s) or FRAME_NATIVE.search(s)
        if m:
            frames.append((m.group(1).replace("\\", "/"), int(m.group(2))))
    return frames


def from_log(text):
    """[(nodeid, frames)] and the session duration in seconds (None if absent) from a pytest console log."""
    lines = clean_lines(text)
    nodes = [norm_node(n) for n in failed_tests(lines)]
    durations = [float(m.group(1)) for m in map(DURATION.search, lines) if m]
    sections = report_sections(lines)
    return [(n, traceback_frames(sections, n)) for n in nodes], (durations[-1] if durations else None)


def from_junit(path, py_files):
    """[(nodeid, frames)] and the total test time from a JUnit XML report.

    pytest's default report has no file attribute, so the module path is recovered from `classname`
    by matching repository .py files.
    """
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    total = sum(float(s.get("time", 0) or 0) for s in suites) or None
    out = []
    for case in root.iter("testcase"):
        bad = case.find("failure")
        if bad is None:
            bad = case.find("error")
        if bad is None:
            continue
        name, classname, file = case.get("name", ""), case.get("classname", ""), case.get("file", "")
        node = None
        parts = classname.split(".")
        for i in range(len(parts), 0, -1):
            path = "/".join(parts[:i]) + ".py"
            if (file and file.replace("\\", "/").endswith(path)) or path in py_files or any(p.endswith("/" + path) for p in py_files):
                node = "::".join([path, *parts[i:], name])
                break
        if node is None:
            node = f"{file or classname.replace('.', '/') + '.py'}::{name}"
        out.append((norm_node(node), frames_from_text((bad.get("message") or "") + "\n" + (bad.text or ""))))
    return out, total


# --- git -----------------------------------------------------------------------------------------

def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def diff(repo, base, tree):
    if not base or not tree:
        return None
    rc, names = git(repo, "diff", "--name-only", base, tree)
    if rc:
        return None
    files = [f for f in names.splitlines() if f]
    lines = 0
    for line in git(repo, "diff", "--numstat", base, tree, "--", "*.py")[1].splitlines():
        a, d, _ = line.split("\t", 2)
        lines += (int(a) if a.isdigit() else 0) + (int(d) if d.isdigit() else 0)
    hunks, cur = defaultdict(list), None
    for line in git(repo, "diff", "-U0", base, tree, "--", "*.py")[1].splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            s, n = int(m.group(1)), int(m.group(2) or 1)
            hunks[cur].append((s, s + max(n, 1) - 1))
    return dict(files=files, lines=lines, hunks=hunks)


# --- per-failure helpers -------------------------------------------------------------------------

def norm_frame(path, repo_name, roots=()):
    """(repo-relative path, in_repo) for a traceback path; roots are absolute checkout paths."""
    if f"/{repo_name}/{repo_name}/" in path:  # GitHub runner checkout: /home/runner/work/<name>/<name>/
        return path.split(f"/{repo_name}/{repo_name}/", 1)[1], True
    for root in roots:
        root = root.rstrip("/") + "/"
        if path.lower().startswith(root.lower()):
            return path[len(root):], True
    if "site-packages" in path or "/lib/python" in path or "hostedtoolcache" in path or path.startswith(("/usr", "/opt")):
        return path, False
    # As in v0.8, other Windows drive paths count as in-repo; library paths were caught by the rule above.
    return path.lstrip("./"), not path.startswith("/")


def depth(a, b):
    a, b = a.split("/")[:-1], b.split("/")[:-1]
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def resolve(index, nodeid):
    """Test function for a rootdir-relative node ID: file by path suffix, then Class.method or function."""
    file, _, rest = nodeid.split("[")[0].partition("::")
    parts = [p for p in rest.split("::") if p]
    cands = [p for p in index.modules if p == file or p.endswith("/" + file)]
    if len(cands) != 1 or not parts:
        return None
    path, cls, name = cands[0], ".".join(parts[:-1]), parts[-1]
    found = index.method(path, cls, name) if cls else ([index.functions[(path, name)]] if (path, name) in index.functions else [])
    return found[0] if len(found) == 1 else None


def flaky_frequency(history, when):
    """MDFlaker's factor over failures of this test in earlier runs; a gap > 8 h starts a new transition."""
    past = sorted(t for t in history if t <= when)
    if not past:
        return 0.0
    transitions = 1
    for a, b in zip(past, past[1:]):
        if a + datetime.timedelta(hours=8) < b:
            transitions += 1
    return round(transitions / (len(past) + 2), 2)


def history_key(nodeid):
    return norm_node(nodeid).split("[")[0]


def extract(failures, *, repo, base, tree, source_root, repo_name, roots=(), history=None, run_id="", when=None,
            previous_state=2, job_duration_s=0.0, pr_build=0, index=None):
    """One feature dict per failure. `failures` is [(nodeid, frames)] for every failed test of the job.

    history: {history_key: [(datetime, run_id)]} of failures recorded before this run (strict history:
    entries from this run_id, or not earlier than `when`, are ignored).
    """
    when = when or datetime.datetime.now(datetime.timezone.utc)
    d = diff(repo, base, tree)
    files = d["files"] if d else []
    py = [f for f in files if f.endswith(".py")]
    if index is None and source_root is not None:
        index = SourceIndex(source_root)
    rows = []
    for nodeid, raw in failures:
        node = norm_node(nodeid)
        fn = resolve(index, node) if index is not None else None
        frames = [(norm_frame(p, repo_name, roots), ln) for p, ln in raw]
        test_path = fn.path if fn else ""
        dist, cov = CAP, 0
        for (p, inrepo), ln in frames:
            if not inrepo:
                continue
            for f, hs in (d["hunks"].items() if d else []):
                if f in p or p in f:
                    for s, e in hs:
                        if s <= ln <= e:
                            cov = 1
                        dist = min(dist, 0 if s <= ln <= e else min(abs(ln - s), abs(ln - e)))
        smells = size = 0
        if fn:
            text = (Path(index.root) / fn.path).read_text(encoding="utf-8", errors="replace")
            smells = test_smells(fn.node)
            size = test_size(fn.qualname.split(".")[-1], text.splitlines(keepends=True))
        past = [w for w, r in (history or {}).get(history_key(node), []) if str(r) != str(run_id) and w < when]
        same_file = 0
        if len(failures) <= ISOLATED_MAX:
            same_file = sum(1 for other, _ in failures if other != nodeid and other.split("::")[0] == nodeid.split("::")[0])
        last = frames[-1][0][0] if frames else ""
        row = dict(
            flaky_frequency=flaky_frequency(past, when), traceback_coverage=cov, test_smells=smells,
            previous_state=previous_state, test_size=size,
            build_failed_tests=len(failures), same_file_cofailures=same_file, job_duration_s=job_duration_s, pr_build=int(pr_build),
            changed_files=len(files), changed_py_files=len(py), changed_test_py_files=sum("test" in f.lower() for f in py),
            nonpy_only_change=int(d is not None and not py), changed_lines=d["lines"] if d else 0,
            own_test_file_changed=int(bool(test_path) and test_path in files),
            path_overlap_depth=max((depth(test_path, f) for f in py), default=0) if test_path else 0,
            traceback_frames=len(frames),
            frames_in_changed_files=sum(1 for (p, inrepo), _ in frames if inrepo and any(f in p or p in f for f in files)),
            last_frame_in_test_file=int(bool(frames) and bool(test_path) and (test_path.endswith(last) or last.endswith(test_path))),
            frames_outside_repo=sum(1 for (p, inrepo), _ in frames if not inrepo),
            min_line_distance_to_change=min(dist, CAP), diff_available=int(d is not None))
        rows.append(dict(nodeid=node, source_mapped=int(bool(fn)), test_path=test_path, features=row))
    return rows
