import functools
import inspect
import logging
import sys

from rich.console import Console as RichConsole
from rich.logging import RichHandler
from rich.theme import Theme

from termwiki import consts


def _format_args(func):
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
            pretty_signature = f"{prefix}{str(bound_args)[16:-1]}"
            # self.debug(f"➡️️ [b white]Entered[/b white] {func_name}({comma_sep_args + (', ' if args and kwargs else '') + comma_sep_kwargs})")
            log.debug(f"➡️️ [i]Entered[/i] {pretty_signature}", stacklevel=2)
            ret = func(*args, **kwargs)
            log.debug(f"⬅️️️ Exiting {prefix}() -> {ret!r}", stacklevel=2)
            return ret

        return wrapper

    if func_or_nothing:
        # We're called e.g as @log_in_out
        return decorator(func_or_nothing)
    # We're called e.g as @log_in_out()
    return decorator


class Console(RichConsole):
    _theme = {
        "debug": "dim",
        "warn": "yellow",
        "warning": "yellow",
        "error": "red",
        "fatal": "bright_red",
        "success": "green",
        "prompt": "b bright_cyan",
        "title": "b bright_white",
    }

    def __init__(self, **kwargs):
        theme = kwargs.pop(
            "theme", Theme({**self._theme, **{k.upper(): v for k, v in self._theme.items()}})
        )
        super().__init__(
            color_system="truecolor",
            # force_terminal=True,
            width=kwargs.pop("width", None if sys.stdin.isatty() else consts.NON_INTERACTIVE_WIDTH),
            file=kwargs.pop("file", sys.stdout if consts.PYCHARM_HOSTED else sys.stderr),
            tab_size=kwargs.pop("tab_size", 2),
            log_time=kwargs.pop("log_time", False),
            # log_time_format='[%d.%m.%Y][%T]',
            log_path=kwargs.pop("log_path", True),
            theme=theme,
            **kwargs,
            # safe_box=False,
            # soft_wrap=True,
        )
        self.width -= 2

    if consts.DEBUG:

        @_format_args
        def debug(self, *args, **kwargs):
            return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    else:

        def debug(self, *args, **kwargs):
            pass

        print(f" ! Console.debug() disabled\n")

    @_format_args
    def info(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @_format_args
    def warning(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @_format_args
    def error(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @_format_args
    def fatal(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @_format_args
    def success(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @_format_args
    def prompt(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)

    @_format_args
    def title(self, *args, **kwargs):
        return self.log(*args, _stack_offset=kwargs.pop("_stack_offset", 3), **kwargs)


class MyRichHandler(RichHandler):
    def emit(self, record: logging.LogRecord) -> None:
        record_pathname = getattr(record, "pathname", None)
        if record_pathname:
            record_pathname = record_pathname.removeprefix(consts.PROJECT_ROOT_PATH)
            if "site-packages/" in record_pathname:
                *venv_path, record_pathname = record_pathname.partition("site-packages/")
            record.pathname = record_pathname
        super().emit(record)


console = Console()

rich_handler = MyRichHandler(
    console=console,
    level=logging.DEBUG if consts.DEBUG else logging.INFO,
    markup=True,
    omit_repeated_times=False,
    enable_link_path=False,
    rich_tracebacks=True,
    tracebacks_show_locals=True,
    locals_max_string=max(console.width, consts.NON_INTERACTIVE_WIDTH) - 20,
)

logging.basicConfig(
    level=logging.DEBUG if consts.DEBUG else logging.INFO,
    format="%(pathname)s %(funcName)s() %(message)s",
    datefmt="[%T]",
    force=True,
    handlers=[rich_handler],
)

log = logging.getLogger("root")
