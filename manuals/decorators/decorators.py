from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from functools import wraps

from manuals.common.types import ManFn

console = None


# *** Decorators

def alias(_alias: str) -> Callable[[ManFn], ManFn]:
    """Sets `fn.alias = _alias` to decorated function.
    Used when populating MAIN_TOPICS as an additional key to function."""

    def wrap(fn: ManFn) -> ManFn:
        fn.alias = _alias
        return fn

    return wrap


def rich(manual: ManFn):
    @wraps(manual)
    def wrap(subject=None):
        global console
        string = manual(subject)
        from rich.markdown import Markdown
        if console is None:
            from rich.console import Console
            import io
            console = Console(file=io.StringIO(), force_terminal=True)
        # Todo - Problem: inline code is detected by indentation by builtin commonmark
        #  should build custom parser?
        md = Markdown(string, justify="left")
        console.print(md)
        marked_down = console.file.getvalue()
        return marked_down

    return wrap


def optional_subject(manual: ManFn):
    """Allows manual to be called with or without a subject,
    and does the 'return local subject var if specified else the whole manual' thing automatically.

    Example::

        @optional_subject
        def django():
            _ADMIN = "django admin"
            return f"Django
                {_ADMIN}"
    """

    @wraps(manual)
    def decorate(subject=None):
        if not subject:
            return manual()
        fnsrc = inspect.getsource(manual)
        parsed: ast.Module = ast.parse(fnsrc)
        # noinspection PyTypeChecker
        fndef: ast.FunctionDef = parsed.body[0]
        nod: ast.Assign
        varnames: list[ast.Name]
        for nod in fndef.body:
            if not isinstance(nod, ast.Assign):
                continue
            # noinspection PyTypeChecker
            varnames = nod.targets
            for varname in varnames:
                if varname.id == subject:
                    return eval(ast.unparse(nod.value))

        return manual()

    return decorate
