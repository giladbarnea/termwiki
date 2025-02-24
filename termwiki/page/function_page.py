import ast
import inspect
from collections.abc import Generator
from typing import Callable, ParamSpec

from . import ast_utils
from .page import Traversable
from .variable_page import VariablePage

ParamSpec = ParamSpec("ParamSpec")


class FunctionPage(Traversable):
    def __init__(self, function: Callable[ParamSpec, str | None]) -> None:
        super().__init__()
        self.function = function
        self._python_module_ast = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(function={self.function.__qualname__})"

    def python_module_ast(self) -> ast.Module:
        if self._python_module_ast:
            return self._python_module_ast
        self._python_module_ast: ast.Module = ast.parse(inspect.getsource(self.function))
        return self._python_module_ast

    def name(self):
        return self.function.__name__

    def read(self, *args, **kwargs) -> str:
        text = self.function(*args, **kwargs)
        if text is not None:
            return text
        # If a function doesn't return:
        #  search for self-named variable
        #  if not found, return its joined variables values
        # todo: super doesn't skip variables pointing to the same object
        return super().read(*args, **kwargs)
        # noinspection PyUnreachableCode
        variable_texts = []
        seen_variable_pages = set()
        for _var_name, var_page in self.traverse():
            if var_page.value in seen_variable_pages:
                continue
            seen_variable_pages.add(var_page.value)
            variable_text = var_page.read()
            variable_texts.append(variable_text)
        return "\n".join(variable_texts)

    __call__ = read

    def traverse(self, *args, cache_ok=True, **kwargs) -> Generator[tuple[str, VariablePage]]:
        self.__traverse_exhaused__ and breakpoint()
        python_module_ast = self.python_module_ast()
        yield from ast_utils.traverse_function(self.function, python_module_ast)
