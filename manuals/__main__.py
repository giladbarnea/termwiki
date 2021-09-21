# try:
#     from rich.traceback import install
#
#     install(extra_lines=5, show_locals=True)
# except ModuleNotFoundError as e:
#     pass
if __name__ == '__main__':
    from . import main
    # import sys
    #
    # for arg in sys.argv:
    #     if arg.startswith('--new='):
    #         newtopic = arg[6:]
    #         main.create_new_manual(newtopic)
    #         break
    # else:
    #     main.get_topic()
    main.get_topic()
