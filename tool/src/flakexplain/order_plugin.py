"""Pytest plugin for reordered rounds, loaded with `-p flakexplain.order_plugin`.

Items are reordered in memory, so long test lists never reach the command line (WinError 206).
"""
import random


def pytest_addoption(parser):
    group = parser.getgroup("flakexplain")
    group.addoption("--fx-order", choices=("reverse", "random"), help="Reorder collected tests.")
    group.addoption("--fx-seed", type=int, default=0, help="Seed for --fx-order=random.")


def pytest_collection_modifyitems(config, items):
    order = config.getoption("--fx-order")
    if order == "reverse":
        items.reverse()
    elif order == "random":
        random.Random(config.getoption("--fx-seed")).shuffle(items)


def pytest_report_header(config):
    order = config.getoption("--fx-order")
    if order:
        return f"flakexplain order: {order}" + (f", seed {config.getoption('--fx-seed')}" if order == "random" else "")
