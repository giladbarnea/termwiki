from __future__ import annotations
from collections.abc import Callable
from pathlib import Path


class Page:
    def __call__(self, *args, **kwargs) -> str:
        ...


class FunctionPage(Page):

    def __init__(self, function: Callable[..., str]) -> None:
        super().__init__()
        self.function = function

    def __call__(self, *args, **kwargs) -> str:
        return self.function(*args, **kwargs)


class FilePage(Page):

    def __init__(self, filename: str | Path) -> None:
        super().__init__()
        self.filename = filename

    def __call__(self, *args, **kwargs) -> str:
        with open(self.filename) as f:
            file_content = f.read()
        return file_content
