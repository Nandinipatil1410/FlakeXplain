"""Load required pytest distributions without autoloading pytest-randomly.

Pytester's child fixtures deliberately delete PYTEST_ADDOPTS, so exclusions
there cannot isolate nested runs. PYTEST_PLUGINS survives those fixtures.
Loading named entry points also retains the version metadata required by the
upstream Hypothesis reporting tests.
"""


def pytest_addoption(parser, pluginmanager):
    for name in ("hypothesispytest", "xdist", "xdist.looponfail", "forked"):
        pluginmanager.load_setuptools_entrypoints("pytest11", name=name)
