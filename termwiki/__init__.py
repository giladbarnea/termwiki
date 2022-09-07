# ** termwiki/__init__.py
import os
from sys import path

from rich.traceback import install
from rich.console import Console
console = Console(color_system='truecolor')
print(f'{os.get_terminal_size() = }')
import click
import bdb

if home := os.path.expanduser('~') not in path:
    path.append(home)
install(width=os.getenv('COLUMNS', 130), show_locals=True, suppress=(click, bdb))

from termwiki.page import page_tree