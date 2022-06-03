import os
from sys import path

os.environ['DEBUGFILE_NO_PATCH_PRINT'] = '1'
from rich.traceback import install
import click
import bdb

if home := os.path.expanduser('~') not in path:
    path.append(home)
install(width=os.getenv('COLUMNS', 130), show_locals=True, suppress=(click, bdb))

from termwiki.page_tree import page_tree