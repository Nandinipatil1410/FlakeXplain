"""Restore registry-verified historical datasets before scikit-image experiments."""
import ast
import hashlib
from pathlib import Path
import tempfile
import time
from urllib.parse import quote
from urllib.request import urlopen

from runtime import atomic_json


def read_registry(path):
    """Read only literal dictionaries; never import the subject during setup."""
    values = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"registry", "registry_urls"}:
                    values[target.id] = ast.literal_eval(node.value)
    return values["registry"], values["registry_urls"]


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_skimage_data(repo, config):
    """Install exact registered bytes where unmodified _fetch finds local data."""
    repo = Path(repo)
    registry, urls = read_registry(repo / "skimage/data/_registry.py")
    provenance = []
    for name, expected in registry.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("Unsafe dataset registry path: " + name)
        destination = repo / "skimage" / relative
        url = urls.get(name)
        if url is not None:
            prefix = "https://gitlab.com/scikit-image/data/-/raw/master/"
            if not url.startswith(prefix):
                raise RuntimeError("Unrecognized dataset source: " + url)
            url = (
                "https://gitlab.com/api/v4/projects/scikit-image%2Fdata/repository/files/"
                + quote(url[len(prefix):], safe="") + "/raw?ref="
                + config["dataset_revision"]
            )
        else:
            url = ("https://raw.githubusercontent.com/scikit-image/scikit-image/"
                   + config["commit"] + "/skimage/" + quote(name, safe="/"))
        if destination.exists():
            if file_hash(destination) != expected:
                raise RuntimeError("Existing dataset checksum mismatch: " + name)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            print("Preparing checksum-pinned dataset: " + name, flush=True)
            # Write beside the destination and publish only after verification.
            for attempt in range(3):
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
                        temporary = Path(output.name)
                        with urlopen(url, timeout=120) as response:
                            while True:
                                block = response.read(1024 * 1024)
                                if not block:
                                    break
                                output.write(block)
                    if file_hash(temporary) != expected:
                        raise RuntimeError("Downloaded dataset checksum mismatch: " + name)
                    temporary.replace(destination)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        provenance.append({"path": name, "sha256": expected, "upstream_url": url})
    atomic_json(repo / "logs/dataset_provenance.json", {
        "subject_commit": config["commit"],
        "dataset_revision": config["dataset_revision"],
        "registry_sha256": file_hash(repo / "skimage/data/_registry.py"),
        "files": provenance,
        "note": "Exact upstream registry bytes supplied locally; source and tests unchanged.",
    })
