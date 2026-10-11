"""Run the complete pinned Prefect suite with its historical expiry fixture.

The 2021 checkout uses literal 2025 API-key expiration dates. Restore only
Pendulum's clock during those cases; wall time and scheduler clocks stay real.
No upstream source, assertions, collection, or outcomes are changed.
"""
import sys

import pendulum
import pytest


class HistoricalExpiryClock:
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        path = item.nodeid.split("::", 1)[0].replace("\\", "/")
        if path == "tests/cli/test_auth.py" and item.originalname == "test_create_key":
            with pendulum.test(pendulum.datetime(2021, 7, 1, tz="UTC")):
                yield
        else:
            yield


if __name__ == "__main__":
    print("Prefect expiry fixture: Pendulum 2021-07-01 UTC for test_create_key only", flush=True)
    raise SystemExit(pytest.main(sys.argv[1:], plugins=[HistoricalExpiryClock()]))
