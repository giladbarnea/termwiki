from sys import path
import os
os.environ['DEBUGFILE_NO_PATCH_PRINT'] = '1'
from rich.traceback import install
import click
if home:=os.path.expanduser('~') not in path:
    path.append(home)
install(width=os.getenv('COLUMNS', 130),show_locals=True,suppress=(click,))