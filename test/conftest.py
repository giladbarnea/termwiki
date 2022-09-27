import os
import sys
from collections.abc import Mapping
from typing import Union

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.reports import TestReport, CollectReport

homedir = os.path.expanduser('~')
if homedir not in sys.path:
    sys.path.append(homedir)


# def pytest_addoption(parser: Parser):
#     parser.addoption("--skip-slow", action="store_true", default=False, help="Skip slow tests")
#
#
# def pytest_configure(config: Config):
#     config.addinivalue_line("markers", "slow: mark test as slow to run")
#
#
# def pytest_collection_modifyitems(config: Config, items):
#     if not config.getoption("--skip-slow"):
#         return
#     skip_slow = pytest.mark.skip(reason="Specified --skip-slow")
#     for item in items:
#         if "slow" in item.keywords:
#             item.add_marker(skip_slow)


def pytest_report_teststatus(report: CollectReport | TestReport, config: Config) -> tuple[str, str, str | Mapping[str, bool]]:
    if report.when == 'call':
        if report.failed:
            return report.outcome, 'x', ''
        if report.passed:
            return report.outcome, '√', ''
        breakpoint()
        return report.outcome, '', f'{report.outcome.title()} {report.head_line} at {report.location[0]}:{report.location[1]}'
    # breakpoint()
    # if report.skipped:
    #     return report.outcome, '🟡', 'Skipped'

    # def pytest_runtest_logreport(report: TestReport) -> None:
    #     if report.failed and hasattr(report.longrepr, 'getrepr'):
    #         report.longreprtext = report.longrepr.getrepr(truncate_locals=False)


    # def pytest_assertrepr_compare(config: Config, op: str, left, right) -> Optional[list[str]]:
    #     return None


def pytest_exception_interact(node, call, report) -> None:
    import importlib
    import os

    import _pytest
    import pluggy
    from rich.traceback import Traceback

    PYCHARM_HOSTED = os.environ.get("PYCHARM_HOSTED")
    width = max(int(os.getenv("COLUMNS", 130)), 130) if PYCHARM_HOSTED else None
    traceback = Traceback.from_exception(call.excinfo.type,
                                         call.excinfo.value,
                                         call.excinfo.tb,
                                         width=width,
                                         show_locals=True,
                                         suppress=(_pytest, importlib, pluggy), )
    height = max(int(os.getenv("LINES", 100)), 100) if PYCHARM_HOSTED else None

    from rich.console import Console

    console = Console(width=width, height=height)
    console.print(traceback)

# def pytest_enter_pdb(config: Config, pdb: pdb.Pdb) -> None:
#     print(f'\n{pdb = !r}, {type(pdb) = !r}')
