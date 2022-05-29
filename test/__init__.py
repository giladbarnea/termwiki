print()
from sys import path
import os
if os.path.expanduser('~') not in path:
    path.append(os.path.expanduser('~'))