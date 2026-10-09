"""Pin external repositories cloned by unmodified historical subject tests."""
from pathlib import Path

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
    index = int(env.get("GIT_CONFIG_COUNT", "0"))
    for fixture in config.get("git_test_fixtures", []):
        target = fixture_path(repo, fixture).resolve()
        env["GIT_CONFIG_KEY_" + str(index)] = "url." + target.as_uri() + ".insteadOf"
        env["GIT_CONFIG_VALUE_" + str(index)] = fixture["url"]
        index += 1
    if config.get("git_test_fixtures"):
        env["GIT_CONFIG_COUNT"] = str(index)
    return env
