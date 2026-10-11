"""Run the complete pinned Prefect suite with its historical expiry fixture.

The 2021 checkout uses literal 2025 API-key expiration dates. Restore only
Pendulum's clock during those cases; wall time and scheduler clocks stay real.
No upstream source, assertions, collection, or outcomes are changed.
"""
import sys

import pendulum
import pytest
from zmq.utils import jsonapi


def verify_notebook_serializer():
    """Initialize the real JSON backend before docs' optional-import mocks.

    docs/test_generate_docs.py loads Prefect's integrations under an import
    hook that returns MagicMock for missing optional packages. PyZMQ 22.1.0
    otherwise caches a mocked simplejson as its backend during collection.
    Normal import here lets PyZMQ select its authentic installed JSON backend.
    """
    sample = {"flakexplain_serializer_probe": [1, True, None]}
    packed = jsonapi.dumps(sample)
    if not isinstance(packed, bytes) or jsonapi.loads(packed) != sample:
        raise RuntimeError("Jupyter requires a real JSON serializer returning bytes")
    print("Verified notebook JSON backend:", jsonapi.jsonmod.__name__, flush=True)


class HistoricalExpiryClock:
    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_runtest_makereport(self, item, call):
        # Identify the case before pytest formats an exception. Historical
        # daemon heartbeat threads can spin through a test's mocked sleep
        # until its fixtures tear down; source introspection can exhaust RAM.
        if call.excinfo is not None:
            print("\nPrefect exception before report:", item.nodeid,
                  "phase=" + call.when, call.excinfo.typename, flush=True)
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        path = item.nodeid.split("::", 1)[0].replace("\\", "/")
        if path == "tests/cli/test_auth.py" and item.originalname == "test_create_key":
            with pendulum.test(pendulum.datetime(2021, 7, 1, tz="UTC")):
                yield
        else:
            yield


if __name__ == "__main__":
    verify_notebook_serializer()
    print("Prefect expiry fixture: Pendulum 2021-07-01 UTC for test_create_key only", flush=True)
    raise SystemExit(pytest.main(sys.argv[1:], plugins=[HistoricalExpiryClock()]))
