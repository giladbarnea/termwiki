from typing import Protocol, Literal

Style = Literal[
    "algol_nu",
    "default",
    "dracula",
    "friendly",
    "fruity",
    "inkpot",
    "monokai",
    "native",
    "solarized-dark",
]
Language = Literal[
    "ahk",
    "bash",
    "css",
    "docker",
    "html",
    "ini",
    "ipython",
    "js",
    "json",
    "md",
    "mysql",
    "python",
    "rst",
    "sass",
    "toml",
    "ts",
]


class PageFunction(Protocol):
    # sub_pages: set[str]
    # alias: str

    def __call__(self) -> str:
        ...


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
