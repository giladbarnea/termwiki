from __future__ import annotations

import ast
import inspect
import sys
from functools import wraps
from typing import Callable

from termwiki.common.types import PageFunction

def style(default_style: str = None, **language_styles):
    """Allows a page_function to be styled with a string or a dict of styles.

    Example::

        @style("monokai")
        def django():
            return "Django"

        @style(python="monokai", bash="dracula")
        def django():
            return "Django"

    """

    # should unwrap first?
    def decorator(page_function):
        page_function.default_style = default_style
        if not hasattr(page_function, 'styles'):
            page_function.styles = {}
        page_function.styles.update(language_styles)
        return page_function
    return decorator

def alias(*aliases) -> Callable[[PageFunction], PageFunction]:
    def decorator(page_function: PageFunction) -> PageFunction:
        if not hasattr(page_function, 'aliases'):
            page_function.aliases = []
        page_function.aliases.extend(aliases)
        # should unwrap first?
        for al in aliases:
            page_function.__globals__[al] = page_function
            sys.modules[page_function.__module__].__dict__[al] = page_function
        return page_function

    return decorator

def optional_subject(page: PageFunction):
    """Allows page to be called with or without a subject,
    and does the 'return local subject var if specified else the whole page' thing automatically.

    Example::

        @optional_subject
        def django():
            _ADMIN = "django admin"
            return f"Django
                {_ADMIN}"
    """

    @wraps(page)
    def decorate(subject=None):
        if not subject:
            return page()
        fnsrc = inspect.getsource(page)
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

        return page()

    return decorate


