# ** termwiki/__init__.py

import bdb

import click
from rich.traceback import install as rich_traceback_install

from termwiki.log import console

# if home := os.path.expanduser('~') not in path:
#     path.append(home)
rich_traceback_install(console=console,
                       width=console.width,
                       show_locals=True,
                       suppress=(click, bdb))

from termwiki.page import page_tree
