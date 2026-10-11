"""Fail early unless Salt's unmodified login-dependent tests can run."""
import os
from pathlib import Path
import pwd
import sys


def main():
    if sys.version_info[:3] != (3, 8, 18):
        raise SystemExit("Salt requires Python 3.8.18 in the terminal login: " + sys.version)
    user = pwd.getpwuid(os.geteuid()).pw_name
    if user != "cannier" or not os.isatty(0) or os.getlogin() != user:
        raise SystemExit("Salt requires an unprivileged cannier terminal login")
    # pam_umask applies user-group mode 0002 to SSH logins. Salt's TLS tests
    # require the standard 0022 creation mask for public certificates.
    os.umask(0o022)
    print("Verified Salt terminal login: " + user, flush=True)
    print("Verified Salt pipeline interpreter: " + sys.executable, flush=True)
    pipeline = Path(__file__).resolve().parents[1] / "run_all.py"
    os.execv(sys.executable, [sys.executable, str(pipeline), *sys.argv[1:]])


if __name__ == "__main__":
    main()
