"""Configure pinned sources for upstream easy_install integration tests.

Only the source option changes. Tests still install the wheels themselves and
retain all assertions. No fixture package is installed at collection.
"""
from pathlib import Path
import json

import pytest


def pytest_collection_modifyitems(items):
    """Pin moving source inputs; preserve test IDs and assertions."""
    root = Path(__file__).parent / ".venv/flakexplain-package-fixtures"
    sources = json.loads((root / "parameter_sources.json").read_text())
    for item in items:
        module = getattr(getattr(item, "module", None), "__name__", "")
        params = getattr(getattr(item, "callspec", None), "params", {})
        for source in sources:
            key = source["parameter"]
            if (module == source["module"] and
                    params.get(key) == source["original"]):
                params[key] = source["pinned"]
                item.user_properties.append(("pinned_" + key,
                                             source["pinned"]))


@pytest.fixture(autouse=True)
def pinned_easy_install_sources(request, monkeypatch):
    module = getattr(request.node, "module", None)
    if getattr(module, "__name__", "") != "setuptools.tests.test_integration":
        return
    from setuptools.command.easy_install import easy_install

    initialize = easy_install.initialize_options
    root = Path(__file__).parent / ".venv/flakexplain-package-fixtures"
    wheels = sorted((root / "downloads").glob("*.whl"))
    links = [path.resolve().as_uri() for path in wheels]

    def initialize_with_sources(command):
        initialize(command)
        existing = command.find_links or []
        if isinstance(existing, str):
            existing = existing.split()
        command.find_links = list(existing) + links

    monkeypatch.setattr(easy_install, "initialize_options",
                        initialize_with_sources)
