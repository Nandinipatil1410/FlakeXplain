"""Run Salt's full pytest suite, then contain leftover test processes.

Salt's historical suite can leave multiprocessing children alive after pytest
prints its final summary. They can block interpreter shutdown or retain the
pipeline's output pipe. Cleanup happens only after pytest.main has returned,
including all normal pytest teardown hooks; its exit code is preserved.
"""
import os
import signal
import subprocess
import sys


def finish_children(process_api):
    children = process_api.Process().children(recursive=True)
    for child in children:
        try:
            child.terminate()
        except process_api.NoSuchProcess:
            pass
    _, alive = process_api.wait_procs(children, timeout=5)
    for child in alive:
        try:
            child.kill()
        except process_api.NoSuchProcess:
            pass
    process_api.wait_procs(alive, timeout=5)
    return len(children)


def child_main(arguments):
    import psutil
    import pytest

    code = int(pytest.main(arguments))
    count = finish_children(psutil)
    print("Salt pytest returned exit {}; cleaned up {} child processes".format(code, count), flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    # pytest has completed all hooks. Avoid a second unbounded join of stale
    # multiprocessing/thread state during Python's interpreter finalization.
    os._exit(code)


def run(arguments):
    process = subprocess.Popen(
        [sys.executable, "-u", __file__, "--salt-child", *arguments],
        start_new_session=True,
    )
    try:
        return process.wait()
    finally:
        # Contain inherited output descriptors even if the child aborts.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


if __name__ == "__main__":
    if sys.argv[1:2] == ["--salt-child"]:
        child_main(sys.argv[2:])
    else:
        raise SystemExit(run(sys.argv[1:]))
