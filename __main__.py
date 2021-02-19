# from mytool.util.debug import ExcHandler

# import os
# import sys
# from IPython.core import ultratb
#
# sys.excepthook = ultratb.VerboseTB(include_vars=False)

if __name__ == '__main__':
    from . import myman
    import sys

    for arg in sys.argv:
        if arg.startswith('--new='):
            newtopic = arg[6:]
            myman.create_new_manual(newtopic)
            break
    else:
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
