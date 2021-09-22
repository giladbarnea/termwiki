from typing import Protocol, overload


class ManFn(Protocol):
    sub_topics: set[str]
    alias: str
    
    def __call__(self, subject: str = None) -> str: ...

# Representing subject=None with Optional[str] doesn't work.
# ManFn = Union[Callable[[str], str], Callable[[], str]]
# from typing import runtime_checkable


# @runtime_checkable
# class ManFn(Callable[[str], str]):
# class ManFn(Callable,FunctionType):
#     sub_topics: List[str]
#     alias: str

# __slots__ = ('sub_topics',)

# ManFn = Callable[[Union[str, ...]], str]
