# ** termwiki/__init__.py
import os
import sys
from sys import path

from rich.traceback import install
from rich.console import Console
console = Console(color_system='truecolor')
try:
    columns, rows = os.get_terminal_size()
    # print(f'{columns = }, {rows = }')
except OSError as e:
    print(repr(e),
          f'{hasattr(sys.stderr, "isatty") = }',
          f'{sys.stderr.isatty() = }',
          f'{sys.stdout.isatty() = }',
            sep='\n')
    columns = os.getenv('COLUMNS', 130)
    rows = os.getenv('LINES', 40)
import click
import bdb

if home := os.path.expanduser('~') not in path:
    path.append(home)
install(width=columns, show_locals=True, suppress=(click, bdb))

from termwiki.page import page_tree