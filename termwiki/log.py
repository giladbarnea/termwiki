import functools
import inspect
import os
import sys

from rich.console import Console as RichConsole
from rich.theme import Theme
from rich.logging import RichHandler
import logging

DEBUG = os.getenv("TERMWIKI_DEBUG", "true").lower() in ("1", "true")
PYCHARM_HOSTED = os.getenv("PYCHARM_HOSTED")


def format_args(func):
    @functools.wraps(func)
    def log_method(*args, **kwargs):
        self, *args = args
        log_level_tag = f"[{func.__name__}]"
        formatted_args = log_level_tag + "\n· ".join(map(str, args))
        return func(self, formatted_args, **kwargs)

    return log_method

def log_in_out(func_or_nothing=None, watch=()):
    """A decorator that logs the entry and exit of a function."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # comma_sep_args = ", ".join(map(repr, args))
            # comma_sep_kwargs = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
            func_name = func.__name__
            if args and hasattr(args[0], func_name):
                self_arg, *rest = args
                prefix = f"{self_arg!r}.{func_name}"
                bound_func = func.__get__(self_arg, type(args[0]))
                signature = inspect.signature(bound_func)
                bound_args = signature.bind(*rest, **kwargs)
            else:
                prefix = func_name
                signature = inspect.signature(func)
                bound_args = signature.bind(*args, **kwargs)
            pretty_signature = f'{prefix}{str(bound_args)[16:-1]}'
            # self.debug(f"➡️️ [b white]Entered[/b white] {func_name}({comma_sep_args + (', ' if args and kwargs else '') + comma_sep_kwargs})")
            log.debug(f"➡️️ [b white]Entered[/b white] {pretty_signature}")
            ret = func(*args, **kwargs)
            log.debug(f"⬅️️️ Exiting {prefix}(...) -> {ret!r}")
            return ret

        return wrapper

    if func_or_nothing:
        # We're called e.g as @log_in_out
        return decorator(func_or_nothing)
    # We're called e.g as @log_in_out()
    return decorator


class Console(RichConsole):
    _theme = {
        "debug": "dim", "warn": "yellow", "warning": "yellow", "error": "red", "fatal": "bright_red", "success": "green", "prompt": "b bright_cyan", "title": "b bright_white",
        }

    def __init__(self, **kwargs):
        theme = kwargs.pop("theme", Theme({**self._theme, **{k.upper(): v for k, v in self._theme.items()}}), )
        super().__init__(  # force_terminal=True,
                # log_time_format='[%d.%m.%Y][%T]',
                # safe_box=False,
                # soft_wrap=True,
                log_time=kwargs.pop("log_time", False),
                color_system=kwargs.pop("color_system", "auto" if PYCHARM_HOSTED else "truecolor"),
                tab_size=kwargs.pop("tab_size", 2),
                log_path=kwargs.pop("log_path", True),
                file=kwargs.pop("file", sys.stdout if PYCHARM_HOSTED else sys.stderr),
                theme=theme,
                width=kwargs.pop("width", os.getenv('COLUMNS', 130)),
                **kwargs, )

    if DEBUG:
        @format_args
        def debug(self, *args, **kwargs):
            return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)
    else:
        def debug(self, *args, **kwargs):
            pass

        print(f" ! Console.debug() disabled\n")

    @format_args
    def info(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @format_args
    def warning(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @format_args
    def error(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @format_args
    def fatal(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @format_args
    def success(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @format_args
    def prompt(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @format_args
    def title(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)


console = Console()
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(funcName)s(...) │ %(message)s',
                    datefmt="[%T]",
                    handlers=[RichHandler(console=console,
                                          markup=True,
                                          rich_tracebacks=True,
                                          tracebacks_show_locals=True,
                                          locals_max_string=console.width - 20, )])
log = logging.getLogger("termwiki")
