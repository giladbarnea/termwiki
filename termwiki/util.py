import importlib
import re
from typing import Sized, Generic, Callable, Type, TypeVar

from termwiki.consts import COLOR_RE

ReturnType = TypeVar("ReturnType")
T = TypeVar("T")


def short_repr(obj: Sized) -> str:
    if type(obj) is str:
        obj: str
        lines = obj.splitlines()
        if len(lines) > 2:
            return repr("\n".join([lines[0], "…", lines[-1]]))
        if len(obj) > 75:
            return obj[:40] + "…" + obj[-40:]
        return obj

    if hasattr(obj, "short_repr"):
        return obj.short_repr()

    if len(obj) > 2:
        empty_sequence_repr = repr(type(obj)())
        match = re.match(r"\w+", empty_sequence_repr)
        if match:
            type_name = match.group()
            parens = empty_sequence_repr[match.end() :]
            left_parens, right_parens = parens[: len(parens)], parens[len(parens) :]
        else:
            type_name = ""
            left_parens, right_parens = empty_sequence_repr
        return f"{type_name}{left_parens}{obj[0]!r}, ..., {obj[-1]!r}{right_parens}"
    return repr(obj)


def decolor(text):
    return COLOR_RE.sub("", text)


def clean_str(s: str) -> str:
    """Removes colors and all non-alphanumeric characters from a string,
    except leading and trailing underscores.
    Strips and returns."""
    decolored = decolor(s).strip()
    cleaned = []
    for i, char in enumerate(decolored):
        if char.isalnum():
            cleaned.append(char)
        elif i > 0 and cleaned and char == "_":
            cleaned.append(char)

    # cleansed = ''.join(filter(str.isalpha, decolored)).strip()
    # return cleansed
    return "".join(cleaned)


def lazy_import(importer_name: str, to_import):
    """Return the importing module and a callable for lazy importing.

    The module named by importer_name represents the module performing the
    import to help facilitate resolving relative imports.

    to_import is an iterable of the modules to be potentially imported (absolute
    or relative). The `as` form of importing is also supported,
    e.g. `pkg.mod as spam`.

    This function returns a tuple of two items. The first is the importer
    module for easy reference within itself. The second item is a callable to be
    set to `__getattr__`.
    """
    module = importlib.import_module(importer_name)
    import_mapping = {}
    for name in to_import:
        importing, _, binding = name.partition(" as ")
        if not binding:
            _, _, binding = importing.rpartition(".")
        import_mapping[binding] = importing

    def __getattr__(name):
        if name not in import_mapping:
            message = f"module {importer_name!r} has no attribute {name!r}"
            raise AttributeError(message)
        importing = import_mapping[name]
        # imortlib.import_module() implicitly sets submodules on this module as
        # appropriate for direct imports.
        imported = importlib.import_module(importing, module.__spec__.parent)
        setattr(module, name, imported)
        return imported

    return module, __getattr__


class cached_property(Generic[T]):
    instance: T

    # method: Callable[[T, ParamSpec], ReturnType]

    def __init__(self, method: Callable[..., ReturnType]):
        self.method = method

    def __get__(self, instance: T, cls: Type[T]) -> ReturnType:
        if instance is None:
            return self
        value = instance.__dict__[self.method.__name__] = self.method(instance)
        return value
