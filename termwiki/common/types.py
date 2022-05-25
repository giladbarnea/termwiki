from typing import Protocol, Literal

Style = Literal['algol_nu', 'default', 'dracula', 'friendly', 'fruity', 'inkpot', 'monokai', 'native', 'solarized-dark']
Language = Literal['ahk', 'bash', 'css', 'docker', 'ini', 'ipython', 'js', 'json', 'md', 'mysql', 'python', 'rst', 'sass', 'toml', 'ts']

class Page(Protocol):
    sub_pages: set[str]
    alias: str
    
    def __call__(self, subject: str = None) -> str: ...

# Representing subject=None with Optional[str] doesn't work.
# Page = Union[Callable[[str], str], Callable[[], str]]
# from typing import runtime_checkable


# @runtime_checkable
# class Page(Callable[[str], str]):
# class Page(Callable,FunctionType):
#     sub_pages: List[str]
#     alias: str

# __slots__ = ('sub_pages',)

# Page = Callable[[Union[str, ...]], str]
