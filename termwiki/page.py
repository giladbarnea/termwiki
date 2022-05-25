from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator, Generator
from importlib import import_module
from pathlib import Path
from types import ModuleType
import ast

class Page:
    def __call__(self, *args, **kwargs) -> str:
        ...

    def __getitem__(self, item):
        ...

    def read(self, *args, **kwargs) -> str:
        ...

    def traverse(self, *args, **kwargs) -> Iterator[Page]:
        ...


class FunctionPage(Page):

    def __init__(self, function: Callable[..., str]) -> None:
        super().__init__()
        self.function = function

    def read(self, *args, **kwargs) -> str:
        return self.function(*args, **kwargs)

    __call__ = read


class FilePage(Page):

    def __init__(self, filename: str | Path) -> None:
        super().__init__()
        self.filename = filename

    def read(self, *args, **kwargs) -> str:
        with open(self.filename) as f:
            file_content = f.read()
        return file_content

    __call__ = read


class ModulePage(Page):
    """A Python file."""

    def __init__(self, python_module: ModuleType | Path, parent: ModuleType = None) -> None:
        super().__init__()
        self._python_module = python_module
        self.parent = parent

    @property
    def python_module(self) -> ModuleType:
        if isinstance(self._python_module, ModuleType):
            return self._python_module
        if isinstance(self._python_module, Path):
            if hasattr(self.parent, self._python_module.stem):
                self._python_module = getattr(self.parent, self._python_module.stem)
            else:
                self._python_module = import_module(str(self._python_module.with_suffix('')).replace('/','.'))
            return self._python_module

    def read(self, *args, **kwargs) -> str:
        module_name = Path(self.python_module.__file__).stem
        if hasattr(self.python_module, module_name):
            return getattr(self.python_module, module_name)()
        # for page in self.traverse():
            # if isinstance(page, ast.FunctionDef):
            #     if module_name == page.name:
            #     return page.body[0].value.s
        return NotImplemented(module_name)

    def traverse(self, *args, **kwargs):
        python_module = self.python_module
        parsed = ast.parse(inspect.getsource(python_module))
        yield from ast.walk(parsed)

class PackagePage(Page):
    """A directory / package / namespace."""

    def __init__(self, package: ModuleType | Path) -> None:
        super().__init__()
        self._package = package

    def __getitem__(self, item: str) -> Page | None:
        for page_name, page in self.traverse():
            if page_name == item:
                return page
        return None

    @property
    def package(self) -> ModuleType:
        if isinstance(self._package, ModuleType):
            return self._package
        import_path = '.'.join(self._package.relative_to('/Users/gilad/dev/termwiki').parts)
        imported_package = import_module(import_path)
        return imported_package

    @property
    def path(self) -> Path:
        if self.package.__file__:
            return Path(self.package.__file__).parent
        # Namespaces __file__ attribute is None
        # Also works: self.package.__spec__.submodule_search_locations[0]
        return Path(self.package.__package__.replace('.', '/'))

    def traverse(self, *args, **kwargs) -> Generator[tuple[str, Page]]:
        for page in self.path.iterdir():
            if page.name.startswith('.') or page.name.startswith('_'):
                continue
            if page.is_dir():
                yield page.name, PackagePage(page)
            elif page.suffix != ".py":
                yield page.stem, FilePage(page)
            elif page.name != '__init__.py':
                yield page.stem, ModulePage(page, self.package)
