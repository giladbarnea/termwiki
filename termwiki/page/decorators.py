import functools
import sys
from typing import Callable

from termwiki.common.types import PageFunction


def style(default_style: str | None = None, **language_styles):
    """
    Allows a page_function to be styled with a string or a dict of styles.

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
        if not hasattr(page_function, "styles"):
            page_function.styles = {}
        page_function.styles.update(language_styles)
        return page_function

    return decorator


def alias(*aliases) -> Callable[[PageFunction], PageFunction]:
    @functools.wraps(aliases)
    def decorator(page_function: PageFunction) -> PageFunction:
        if not hasattr(page_function, "aliases"):
            page_function.aliases = []
        page_function.aliases.extend(aliases)
        # should unwrap first?
        for al in aliases:
            page_function.__globals__[al] = page_function
            sys.modules[page_function.__module__].__dict__[al] = page_function
        return page_function

    return decorator


def title(_title) -> Callable[[PageFunction], PageFunction]:
    @functools.wraps(_title)
    def decorator(page_function: PageFunction) -> PageFunction:
        if not hasattr(page_function, "title"):
            page_function.title = _title
        return page_function

    return decorator


def tag(*tags) -> Callable[[PageFunction], PageFunction]:
    @functools.wraps(tags)
    def decorator(page_function: PageFunction) -> PageFunction:
        if not hasattr(page_function, "tags"):
            page_function.tags = []
        page_function.tags.extend(tags)
        return page_function

    return decorator


def related(page_name) -> Callable[[PageFunction], PageFunction]:
    @functools.wraps(page_name)
    def decorator(page_function: PageFunction) -> PageFunction:
        page_function.related = page_name
        return page_function

    return decorator
