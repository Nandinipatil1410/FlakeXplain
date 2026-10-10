"""Configure pinned package sources for upstream easy_install integration tests.

Only the source option changes. Tests still install the wheels themselves and
retain their upstream assertions. No fixture package is installed at collection.
"""
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def pinned_easy_install_sources(request, monkeypatch):
    if getattr(getattr(request.node, "module", None), "__name__", "") != "setuptools.tests.test_integration":
        return
    from setuptools.command.easy_install import easy_install

    initialize = easy_install.initialize_options
    downloads = Path(__file__).parent / ".venv/flakexplain-package-fixtures/downloads"
    links = [path.resolve().as_uri() for path in sorted(downloads.glob("*.whl"))]

    def initialize_with_sources(command):
        initialize(command)
        existing = command.find_links or []
        if isinstance(existing, str):
            existing = existing.split()
        command.find_links = list(existing) + links

    monkeypatch.setattr(easy_install, "initialize_options", initialize_with_sources)
