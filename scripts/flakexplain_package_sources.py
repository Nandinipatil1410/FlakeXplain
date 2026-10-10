"""Configure pinned sources for upstream easy_install integration tests.

Only the source option changes. Tests still install the wheels themselves and
retain all assertions. No fixture package is installed at collection.
"""
from pathlib import Path

import pytest


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
