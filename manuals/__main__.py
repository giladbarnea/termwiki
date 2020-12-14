# from mytool.util.debug import ExcHandler
from . import myman
# import os
# import sys
# from IPython.core import ultratb
#
# sys.excepthook = ultratb.VerboseTB(include_vars=False)

if __name__ == '__main__':
    myman.main()
    # try:
    # except Exception as e:
    #
    #     from mytool import term
    #     from pprint import pformat as pf
    #
    #     print(f"{term.color('Exception was thrown in myman.main()', 'sat red')}\n",
    #           ExcHandler(e).full())
    #     if (PYTHONPATH := os.environ.get('PYTHONPATH')) and 'JetBrains/Toolbox/apps/PyCharm-P' in PYTHONPATH:
    #         raise e
