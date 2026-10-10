"""Supply authentic pinned wheels for historical easy_install integration tests."""
import hashlib
from pathlib import Path
import shutil
from urllib.request import urlopen

from runtime import atomic_json


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
    if fixtures:
        shutil.copyfile(Path(__file__).with_name("flakexplain_package_sources.py"),
                        Path(repo) / "flakexplain_package_sources.py")
        atomic_json(Path(repo) / "logs/package_test_fixture_provenance.json", fixtures)
        sources = config.get("test_parameter_sources", [])
        atomic_json(root / "parameter_sources.json", sources)
        atomic_json(Path(repo) / "logs/test_parameter_source_provenance.json", sources)
