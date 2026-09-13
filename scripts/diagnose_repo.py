#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPOS_DIR = BASE_DIR / "repos"

def diagnose(repo_name):
    repo_dir = REPOS_DIR / repo_name
    venv_python = repo_dir / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    
    print(f"==================================================")
    print(f"DIAGNOSING PYTEST FOR: {repo_name}")
    print(f"==================================================")
    
    cmd = [str(venv_python), "-m", "pytest", "-p", "no:randomly", "--tb=short", "-q"]
    res = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
    
    print(f"Exit Code: {res.returncode}")
    print(f"--- STDOUT ---")
    print(res.stdout[:2000] if res.stdout else "<empty>")
    print(f"--- STDERR ---")
    print(res.stderr[:2000] if res.stderr else "<empty>")

if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "filelock"
    diagnose(repo)
