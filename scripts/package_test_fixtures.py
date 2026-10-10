"""Supply authentic pinned eggs for historical easy_install integration tests."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

from runtime import atomic_json, checked_output


def package_fixture_dir(repo):
    return Path(repo) / ".venv/flakexplain-package-fixtures"


def prepare_package_test_fixtures(python, repo, config):
    fixtures = config.get("package_test_fixtures", [])
    root = package_fixture_dir(repo)
    for fixture in fixtures:
        downloads = root / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        wheel = downloads / fixture["filename"]
        if not wheel.exists():
            with urlopen(fixture["url"], timeout=120) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != fixture["sha256"]:
                raise RuntimeError("Package fixture checksum mismatch: " + fixture["filename"])
            wheel.write_bytes(payload)
        if hashlib.sha256(wheel.read_bytes()).hexdigest() != fixture["sha256"]:
            raise RuntimeError("Package fixture checksum mismatch: " + fixture["filename"])
        egg = root / fixture["egg_name"]
        if not egg.exists():
            checked_output([str(python), "-c",
                            "from setuptools.wheel import Wheel; import sys; "
                            "Wheel(sys.argv[1]).install_as_egg(sys.argv[2])",
                            str(wheel), str(egg)], repo)
    if fixtures:
        atomic_json(Path(repo) / "logs/package_test_fixture_provenance.json", fixtures)
