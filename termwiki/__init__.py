# ** termwiki/__init__.py

import bdb
import os
import click
from rich.traceback import install as rich_traceback_install

from termwiki import consts
from termwiki.log import console


rich_traceback_install(
    console=console,
    width=console.width,
    show_locals=True,
    extra_lines=5,
    suppress=(click, bdb),
)


def improve_debug_convenience():
    try:
        import pdbpp
        import sys
        import functools

        def prepend_homedir_to_path():
            if (home := os.path.expanduser("~")) not in sys.path:
                sys.path.insert(0, home)

        def import_debug_module_and_set_trace():
            import debug

            pdbpp.set_trace()

        prepend_homedir_to_path()
        sys.breakpointhook = import_debug_module_and_set_trace
    except ModuleNotFoundError:
        pass


if not consts.PYCHARM_HOSTED:
    improve_debug_convenience()

from termwiki.page import page_tree
