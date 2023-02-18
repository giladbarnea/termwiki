# ** termwiki/__init__.py

import bdb

import click
from rich.traceback import install as rich_traceback_install

from termwiki.log import console


rich_traceback_install(console=console,
                       width=console.width,
                       show_locals=True,
                       extra_lines=5,
                       suppress=(click, bdb))
import os
if os.getenv('PYCHARM_HOSTED', '0') != '1':
    try:
        import pdbpp
        import sys
        if (home := os.path.expanduser('~')) not in sys.path:
            sys.path.insert(0, home)
        sys.breakpointhook = pdbpp.set_trace
    except ModuleNotFoundError:
        pass
from termwiki.page import page_tree
