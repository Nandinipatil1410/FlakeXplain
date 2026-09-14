"""Shared live logging, environment identity and checkpoints for FlakeXplain."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import subprocess
import threading
import time
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent.parent
REPOS = [
    "click", "flask", "filelock", "fsspec", "httpx", "urllib3",
    "werkzeug", "rich", "pytest", "ipython", "reframe", "loguru", "freezegun",
]
def default_work_dir():
    if os.name == "nt":
        project_id = hashlib.sha256(str(BASE_DIR).encode()).hexdigest()[:8]
        return Path(os.environ["LOCALAPPDATA"]) / "FlakeXplain" / project_id
    return BASE_DIR


REPOS_DIR = Path(os.environ.get("FLAKEXPLAIN_REPOS_DIR", default_work_dir() / "repos")).resolve()


from contextlib import contextmanager


@contextmanager
def pipeline_lock(work, repo_name):
    """OS releases the lock even after an interrupted pipeline."""
    path = work / (repo_name + ".pipeline.lock")
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"Another pipeline is already running {repo_name} in {work}.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def python_for(repo):
    return repo / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def pytest_command(repo_name, repo):
    """Return the upstream-compatible test entry point for a repository."""
    if repo_name == "reframe":
        # ReFrame's wrapper initializes the generic runtime before pytest starts.
        return [python_for(repo), "-u", repo / "test_reframe.py"]
    return [python_for(repo), "-u", "-m", "pytest"]


def pytest_env(repo):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(repo / part) for part in ("tasks", "tests", "src", ".")]
        + [env.get("PYTHONPATH", "")]
    )
    if repo.name == "urllib3":
        env["PYTHONWARNINGS"] = "always::FutureWarning"
    return env


def pytest_args(repo_name):
    """Repository-owned pytest arguments required for a comparable full suite."""
    if repo_name == "urllib3":
        return [
            "--strict-config",
            "--strict-markers",
            "--disable-socket",
            "--allow-unix-socket",
            "--allow-hosts=localhost,127.0.0.1,::1,127.0.0.0,240.0.0.0",
            "test/",
        ]
    if repo_name == "pytest":
        return ["testing/"]
    if repo_name == "reframe":
        return ["unittests/"]
    if repo_name == "loguru":
        # This historical suite asserts Python's native thread traceback on stderr.
        # Pytest 6.2's hook redirects it into PytestUnhandledThreadExceptionWarning.
        return ["-p", "no:threadexception", "tests/"]
    if repo_name == "freezegun":
        return ["tests/"]
    if repo_name in {"werkzeug", "rich"}:
        return ["tests/"]
    return []


def run_command(cmd, cwd=None, *, env=None, log_path=None, quiet=False, heartbeat=30):
    """Stream complete output; heartbeat during quiet commands; preserve pytest capture."""
    cmd = [str(value) for value in cmd]
    if not quiet:
        print(f"Executing: {subprocess.list2cmdline(cmd)}", flush=True)
    child_env = (env or os.environ).copy()
    child_env["PYTHONUNBUFFERED"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    log = None
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = log_path.open("w", encoding="utf-8")
        log.write(f"cwd: {cwd}\ncommand: {subprocess.list2cmdline(cmd)}\n")
        log.flush()
    chunks = []
    events = queue.Queue()
    started = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=child_env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", bufsize=1)

        def read_output():
            try:
                for line in proc.stdout:
                    events.put(line)
            finally:
                events.put(None)

        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        try:
            while True:
                try:
                    line = events.get(timeout=heartbeat)
                except queue.Empty:
                    if not quiet:
                        print(f"[Still running: {time.monotonic() - started:.0f}s, PID {proc.pid}]", flush=True)
                    continue
                if line is None:
                    break
                chunks.append(line)
                if log:
                    log.write(line)
                    log.flush()
                if not quiet:
                    print(line, end="", flush=True)
            code = proc.wait()
        except BaseException:
            if proc.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
                else:
                    proc.terminate()
                proc.wait()
            raise
        finally:
            proc.stdout.close()
            thread.join(timeout=2)
    finally:
        if log:
            log.close()
    return "".join(chunks).strip(), "", code


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def checked_output(cmd, cwd=None):
    out, _, code = run_command(cmd, cwd=cwd, quiet=True)
    if code:
        raise RuntimeError(f"Command failed ({code}): {cmd}\n{out}")
    return out


def fingerprint(repo):
    """Bind checkpoints to tracked source, installed versions, host and location."""
    commit = checked_output(["git", "rev-parse", "HEAD"], repo)
    diff = checked_output(["git", "diff", "HEAD", "--"], repo)
    freeze = checked_output([python_for(repo), "-m", "pip", "freeze", "--all"], repo)
    version = checked_output([python_for(repo), "--version"], repo)
    # Include untracked source/config, but not virtualenvs or generated run artifacts.
    untracked = checked_output(["git", "ls-files", "--others", "--exclude-standard", "--", ".", ":!.venv", ":!results", ":!logs"], repo)
    source_files = {}
    for name in untracked.splitlines():
        if name.startswith((".venv/", "results/", "logs/")) or name == "conftest_reverse.py":
            continue
        path = repo / name
        if path.is_file() and path.suffix in (".py", ".toml", ".ini", ".cfg"):
            source_files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    value = dict(commit=commit, source_diff_sha256=hashlib.sha256(diff.encode()).hexdigest(),
                 untracked_source=source_files, packages=sorted(freeze.splitlines()), python=version,
                 platform=platform.platform(), machine=platform.machine(),
                 host=platform.node(), repo_path=str(repo))
    value["id"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return value


def complete_xml(path, expected_count=None):
    try:
        root = ET.parse(path).getroot()
        cases = root.findall(".//testcase")
        if any(case.find("error[@message='collection failure']") is not None for case in cases):
            return False
        return bool(cases) and (expected_count is None or len(cases) == expected_count)
    except (OSError, ET.ParseError):
        return False


def baseline_state(repo, current=None):
    state = read_json(repo / "baseline_state.json")
    current = current or fingerprint(repo)
    if state.get("environment_id") != current["id"] or state.get("status") != "PASSED":
        return {}
    if not complete_xml(repo / state["xml_file"], state["collected_count"]):
        return {}
    return state
