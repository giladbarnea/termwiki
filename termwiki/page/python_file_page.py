import ast
import inspect
from collections.abc import Generator
from pathlib import Path
from types import ModuleType

from . import ast_utils
from .page import Traversable, Page


class PythonFilePage(Traversable):
    """A Python module representing a file (not a package)"""

    def __init__(self, python_module: ModuleType | Path, parent: ModuleType = None) -> None:
        super().__init__()
        self._python_module = python_module
        self._python_module_ast = None
        self.parent = parent

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(python_module={self._python_module!r})'

    def python_module_ast(self) -> ast.Module:
        if self._python_module_ast:
            return self._python_module_ast
        self._python_module_ast: ast.Module = ast.parse(inspect.getsource(self.python_module()))
        return self._python_module_ast

    def python_module(self) -> ModuleType:
        if isinstance(self._python_module, ModuleType):
            return self._python_module
        if hasattr(self.parent, self._python_module.stem):
            self._python_module = getattr(self.parent, self._python_module.stem)
            return self._python_module
        self._python_module = ast_utils.import_module_by_path(self._python_module)
        return self._python_module

    def name(self):
        python_module = self.python_module()
        module_name = Path(python_module.__file__).stem
        return module_name

    def traverse(self, *args, cache_ok=True, **kwargs) -> Generator[tuple[str, Page]]:
        self.__traverse_exhaused__ and breakpoint()
        python_module: ModuleType = self.python_module()
        python_module_ast: ast.Module = self.python_module_ast()
        yield from ast_utils.traverse_module(python_module, python_module_ast)
