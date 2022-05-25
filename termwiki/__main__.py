# try:
#     from rich.traceback import install
#
#     install(extra_lines=5, show_locals=True)
# except ModuleNotFoundError as e:
#     pass
if __name__ == '__main__':
    from . import main
    main.get_page()
