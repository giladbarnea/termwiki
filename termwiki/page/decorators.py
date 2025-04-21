import sys
from typing import Callable, TypeVar

from termwiki.common.types import PageFunction

TPageFunction = TypeVar("TPageFunction", bound=PageFunction)


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

    # Should unwrap first?
    def decorator[TPageFunction](page_function: TPageFunction) -> TPageFunction:
        page_function.default_style = default_style
        _setdefault(page_function, "styles", {})
        page_function.styles.update(language_styles)
        return page_function

    return decorator


def alias(*aliases) -> Callable[[PageFunction], PageFunction]:
    def decorator(page_function: PageFunction) -> PageFunction:
        _setdefault(page_function, "aliases", [])
        page_function.aliases.extend(aliases)
        # Should unwrap first?
        for alias in aliases:
            page_function.__globals__[alias] = page_function
            sys.modules[page_function.__module__].__dict__[alias] = page_function
        return page_function

    return decorator


def title(_title) -> Callable[[PageFunction], PageFunction]:
    def decorator(page_function: PageFunction) -> PageFunction:
        _setdefault(page_function, "title", _title)
        return page_function

    return decorator


def tag(*tags) -> Callable[[PageFunction], PageFunction]:
    def decorator(page_function: PageFunction) -> PageFunction:
        _setdefault(page_function, "tags", [])
        page_function.tags.extend(tags)
        return page_function

    return decorator


def related(*page_names) -> Callable[[PageFunction], PageFunction]:
    def decorator(page_function: PageFunction) -> PageFunction:
        _setdefault(page_function, "related", [])
        page_function.related.extend(page_names)
        return page_function

    return decorator


def _setdefault(obj, attr, value) -> None:
    if not hasattr(obj, attr):
        setattr(obj, attr, value)
    return None
