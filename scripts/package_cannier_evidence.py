"""Package allowlisted evidence files, preserving repo import layout and checksums."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from cannier_subjects import NEW_CANNIER_REPOS


def package(subject, work, output):
    config = NEW_CANNIER_REPOS[subject]
    repo = work / "repos" / subject
    destination = output / "repos" / subject
    destination.mkdir(parents=True, exist_ok=True)
    allowed = {".xml", ".json", ".md", ".txt", ".log"}
    for directory in ("results", "logs"):
        for source in sorted((repo / directory).rglob("*")):
            if source.is_file() and not source.is_symlink() and source.suffix.lower() in allowed:
                target = destination / source.relative_to(repo)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    for filename in ("env_snapshot.txt", "environment.json", "setup_state.json",
                     "baseline_state.json", "setup_log.md", "cannier_setup_recipe.json"):
        source = repo / filename
        if source.is_file() and not source.is_symlink():
            shutil.copyfile(source, destination / filename)
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / config["snapshot_path"], destination / "cannier_dependency_snapshot.txt")
    keys = ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "MODE")
    provenance = {key: os.environ.get(key) for key in keys}
    provenance.update(subject=subject, recipe=config,
                      note="Workflow completion alone does not establish complete detection evidence.")
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    try:
        system_packages = subprocess.check_output(["dpkg-query", "-W"], text=True)
    except (OSError, subprocess.CalledProcessError):
        system_packages = "Unavailable on this platform"
    (output / "system_packages.txt").write_text(system_packages, encoding="utf-8")
    report = root / "FlakeXplain_Flaky_Report.md"
    if subject == "airflow" and os.environ.get("MODE") == "full" and report.is_file():
        shutil.copyfile(report, output / report.name)
    hashes = {str(path.relative_to(output)).replace(chr(92), "/"):
              hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(output.rglob("*"))
              if path.is_file() and path.name != "checksums.json"}
    (output / "checksums.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True, choices=NEW_CANNIER_REPOS)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    package(args.subject, args.work_dir, args.output)


if __name__ == "__main__":
    main()
