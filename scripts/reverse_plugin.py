"""
Pytest Plugin for iDFlakies Reverse-Order Execution
Inverts the collected test items sequence in memory before test execution.
Avoids Windows command-line length limits (WinError 206).
"""


def pytest_collection_modifyitems(config, items):
    items.reverse()
