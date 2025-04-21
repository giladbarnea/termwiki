from typing import Literal, Protocol

from termwiki import consts

Style = Literal[*consts.STYLES]

Language = Literal[*consts.LANGUAGES]


class PageFunction(Protocol):
    # sub_pages: set[str]
    title: str
    aliases: list[str]
    related: list[str]
    tags: list[str]
    styles: dict[Language, Style]
    default_style: Style

    def __call__(self) -> str: ...


# Representing subject=None with Optional[str] doesn't work.
# PageFunction = Union[Callable[[str], str], Callable[[], str]]
# from typing import runtime_checkable


# @runtime_checkable
# class PageFunction(Callable[[str], str]):
# class PageFunction(Callable,FunctionType):
#     sub_pages: List[str]
#     alias: str

# __slots__ = ('sub_pages',)

# PageFunction = Callable[[Union[str, ...]], str]
