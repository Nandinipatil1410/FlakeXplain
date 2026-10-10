"""Run pytest with Tornado's native namespace-package import identities."""
import importlib
from pathlib import Path
import sys

import pytest


class TornadoModule(pytest.Module):
    def _getobj(self):
        relative = Path(str(self.fspath)).resolve().relative_to(Path.cwd())
        return importlib.import_module(".".join(relative.with_suffix("").parts))


class TornadoCollection:
    def pytest_pycollect_makemodule(self, path, parent):
        relative = Path(str(path)).resolve().relative_to(Path.cwd())
        if relative.parts[:2] == ("tornado", "test"):
            return TornadoModule.from_parent(parent, fspath=path)


if __name__ == "__main__":
    raise SystemExit(pytest.main(sys.argv[1:], plugins=[TornadoCollection()]))
