"""Fail early unless Salt's unmodified login-dependent tests can run."""
import os
from pathlib import Path
import pwd
import sys


def main():
    user = pwd.getpwuid(os.geteuid()).pw_name
    if user != "cannier" or not os.isatty(0) or os.getlogin() != user:
        raise SystemExit("Salt requires an unprivileged cannier terminal login")
    print("Verified Salt terminal login: " + user, flush=True)
    pipeline = Path(__file__).resolve().parents[1] / "run_all.py"
    os.execv(sys.executable, [sys.executable, str(pipeline), *sys.argv[1:]])


if __name__ == "__main__":
    main()
