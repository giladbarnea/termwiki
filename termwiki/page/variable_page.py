from termwiki.util import short_repr, clean_str
from .page import Page


class VariablePage(Page):
    """Variables within functions, or variables at module level"""

    def __init__(self, value: str, name: str = None) -> None:
        super().__init__()
        self.value = value
        self.name = name

    def __repr__(self) -> str:
        # todo: when it's IndentationMarkdown, decoloring value should be less hacky
        return f"{self.__class__.__name__}(name={self.name!r}, value={short_repr(clean_str(self.value))})"

    def read(self, *args, **kwargs) -> str:
        return str(self.value)
