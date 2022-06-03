from time import perf_counter_ns

start = perf_counter_ns()
import functools
import os
import sys

from rich.console import Console
from rich.theme import Theme

after_imports = perf_counter_ns()


def format_args(func):
    @functools.wraps(func)
    def log_method(*args, **kwargs):
        self, *args = args
        log_level_tag = f"[{func.__name__}]"
        formatted_args = log_level_tag + "\n· ".join(map(str,args))
        return func(self, formatted_args, **kwargs)

    return log_method


class Logger(Console):
    _theme = {
        "debug": "dim", "warn": "yellow", "warning": "yellow", "error": "red", "fatal": "bright_red", "success": "green", "prompt": "b bright_cyan", "title": "b bright_white",
        }

    def __init__(self, **kwargs):
        PYCHARM_HOSTED = os.getenv("PYCHARM_HOSTED")
        theme = kwargs.pop("theme", Theme({**self._theme, **{k.upper(): v for k, v in self._theme.items()}}), )
        super().__init__(# force_terminal=True,
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


    def log_in_out(self, func_or_nothing=None, watch=()):
        """A decorator that logs the entry and exit of a function."""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                comma_sep_args = ", ".join(map(repr, args))
                comma_sep_kwargs = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
                self.debug(f"➡️️ [b white]Entered[/b white] {func.__name__}({comma_sep_args + comma_sep_kwargs})")
                ret = func(*args, **kwargs)
                self.debug(f"⬅️️️ Exiting {func.__name__}(...) -> {ret!r}")
                return ret

            return wrapper

        if func_or_nothing:
            # We're called e.g as @log_in_out
            return decorator(func_or_nothing)
        # We're called e.g as @log_in_out()
        return decorator

    if os.getenv("TERMWIKI_DEBUG", "true").lower() in ("1", "true"):
        @format_args
        def debug(self, *args, **kwargs):
            return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)
    else:
        def debug(self, *args, **kwargs):
            pass

        print(" ! Logger.debug() disabled\n")

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


after_definitions = perf_counter_ns()
log = Logger()
after_instantiation = perf_counter_ns()
log.info(f'{after_imports - start:,.0f}ns after imports',
         f'{after_definitions - after_imports:,.0f}ns after definitions',
         f'{after_instantiation - after_definitions:,.0f}ns after instantiation',
         f'{after_instantiation - start:,.0f}ns total')
