"""Pin external repositories cloned by unmodified historical subject tests."""
from pathlib import Path
import shlex

from runtime import atomic_json, checked_output


def fixture_path(repo, fixture):
    return Path(repo) / ".venv/flakexplain-git-fixtures" / fixture["name"]


def prepare_git_test_fixtures(repo, config):
    fixtures = config.get("git_test_fixtures", [])
    for fixture in fixtures:
        target = fixture_path(repo, fixture)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            checked_output(["git", "clone", "--no-checkout", fixture["url"], str(target)], repo)
            checked_output(["git", "checkout", "--detach", fixture["commit"]], target)
        actual = checked_output(["git", "rev-parse", "HEAD"], target)
        if actual != fixture["commit"]:
            raise RuntimeError("External test repository revision mismatch: " + fixture["name"])
        if checked_output(["git", "status", "--porcelain"], target):
            raise RuntimeError("External test repository has local changes: " + fixture["name"])
    if fixtures:
        atomic_json(Path(repo) / "logs/git_test_fixture_provenance.json", fixtures)


def git_test_fixture_env(repo, config, env):
    """Redirect only configured clone URLs, without changing global Git config."""
    parameters = env.get("GIT_CONFIG_PARAMETERS", "")
    for fixture in config.get("git_test_fixtures", []):
        target = fixture_path(repo, fixture).resolve()
        # Git 2.25 in Ubuntu 20.04 predates GIT_CONFIG_COUNT. This is the
        # inherited configuration format used by `git -c` in that version.
        parameter = "url." + target.as_uri() + ".insteadOf=" + fixture["url"]
        parameters += " " + shlex.quote(parameter)
    if config.get("git_test_fixtures"):
        env["GIT_CONFIG_PARAMETERS"] = parameters.strip()
    return env
