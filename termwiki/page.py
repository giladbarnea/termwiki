from __future__ import annotations

import ast
import inspect
from collections.abc import Callable, Generator
from importlib import import_module
from pathlib import Path
from types import ModuleType, FunctionType

import termwiki

PROJECT_ROOT = Path(termwiki.__path__[0]).parent


def pformat_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    return ast.dump(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent).replace(r'\n', '\n... ')


def pprint_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    print(pformat_node(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent))


def paginate_function(function: Callable[..., str]):
    python_module_ast: ast.Module = ast.parse(inspect.getsource(function))
    for node in python_module_ast.body[0].body:
        if isinstance(node, ast.Assign):
            target: ast.Name
            for target in node.targets:
                value = node.value.value
                yield target.id, value
            continue
        breakpoint()


def paginate_module(module: ModuleType):
    python_module_ast: ast.Module = ast.parse(inspect.getsource(module))
    exclude_names = getattr(module, '__exclude__', {})
    for node in python_module_ast.body:
        if hasattr(node, 'name'):
            if node.name in exclude_names:
                continue
            if isinstance(node, ast.FunctionDef):
                function = getattr(module, node.name)
                yield node.name, FunctionPage(function)
            else:
                print(f'paginate_module({module}): {node.__class__.__name__} has "name" but is not a FunctionDef')
                breakpoint()
            continue
        if hasattr(node, 'names'):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            print(f'paginate_module({module}): {node.__class__.__name__} has "names" but is not an Import or ImportFrom')
            breakpoint()
            for alias in node.names:
                if alias.name not in exclude_names:
                    yield alias.name, getattr(module, alias.name)
            continue
        if isinstance(node, ast.Assign):
            target: ast.Name
            for target in node.targets:
                if target.id not in exclude_names:
                    variable = getattr(module, target.id)
                    yield target.id, variable
            continue
        breakpoint()


class Page:
    def __call__(self, *args, **kwargs) -> str:
        ...

    def __getitem__(self, item: str) -> Page | None:
        for page_name, page in self.traverse():
            if page_name == item:
                return page
        return None

    def read(self, *args, **kwargs) -> str:
        ...

    def traverse(self, *args, **kwargs) -> Generator[Page]:
        ...


class FunctionPage(Page):
    def __init__(self, function: Callable[..., str]) -> None:
        super().__init__()
        self.function = function

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(function={self.function.__qualname__})'

    def read(self, *args, **kwargs) -> str:
        return self.function(*args, **kwargs)

    __call__ = read

    def traverse(self, *args, **kwargs) -> Generator[Page]:
        yield from paginate_function(self.function)


class FilePage(Page):
    def __init__(self, filename: str | Path) -> None:
        super().__init__()
        self.filename = filename

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(filename={self.filename!r})'

    def read(self, *args, **kwargs) -> str:
        with open(self.filename) as f:
            file_content = f.read()
        return file_content

    __call__ = read


class PythonFilePage(Page):
    """A Python module representing a file (not a package)"""

    def __init__(self, python_module: ModuleType | Path, parent: ModuleType = None) -> None:
        super().__init__()
        self._python_module = python_module
        self.parent = parent

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(python_module={self._python_module!r}, parent={self.parent!r})'

    # @property
    def python_module(self) -> ModuleType:
        if isinstance(self._python_module, ModuleType):
            return self._python_module
        if isinstance(self._python_module, Path):
            if hasattr(self.parent, self._python_module.stem):
                self._python_module = getattr(self.parent, self._python_module.stem)
            else:
                python_module_path = Path(self._python_module)
                if python_module_path.is_relative_to(PROJECT_ROOT):
                    python_module_relative_path = python_module_path.relative_to(PROJECT_ROOT)
                else:
                    python_module_relative_path = python_module_path
                python_module_name = str(python_module_relative_path.with_suffix('')).replace('/', '.')
                self._python_module = import_module(python_module_name)
            return self._python_module

    def read(self, *args, **kwargs) -> str:
        python_module = self.python_module()
        module_name = Path(python_module.__file__).stem
        if hasattr(python_module, module_name):
            return getattr(python_module, module_name)()
        # for page in self.traverse():
        # if isinstance(page, ast.FunctionDef):
        #     if module_name == page.name:
        #     return page.body[0].value.s
        return NotImplemented(module_name)

    def traverse(self, *args, **kwargs) -> Generator[tuple[str, ast.AST]]:
        python_module: ModuleType = self.python_module()
        # exclude_names = getattr(python_module, '__exclude__', {})
        # python_module_ast: ast.Module = ast.parse(inspect.getsource(python_module))
        yield from paginate_module(python_module)
        # for node in python_module_ast.body:
        #     if hasattr(node, 'name'):
        #         if node.name in exclude_names:
        #             continue
        #         if isinstance(node, ast.FunctionDef):
        #             function = getattr(python_module, node.name)
        #             yield node.name, FunctionPage(function)
        #         else:
        #             print(f'{self.__class__.__name__}.traverse(): {node.__class__.__name__} has "name" but is not a FunctionDef')
        #             breakpoint()
        #         continue
        #     if hasattr(node, 'names'):
        #         if isinstance(node, (ast.Import, ast.ImportFrom)):
        #             continue
        #         print(f'{self.__class__.__name__}.traverse(): {node.__class__.__name__} has "names" but is not an Import or ImportFrom')
        #         breakpoint()
        #         for alias in node.names:
        #             if alias.name not in exclude_names:
        #                 yield alias.name, getattr(python_module, alias.name)
        #         continue
        #     if isinstance(node, ast.Assign):
        #         target: ast.Name
        #         for target in node.targets:
        #             if target.id not in exclude_names:
        #                 variable = getattr(python_module, target.id)
        #                 yield target.id, variable
        #         continue
        #     breakpoint()


class DirectoryPage(Page):
    """A directory / package / namespace."""

    def __init__(self, package: ModuleType | Path) -> None:
        super().__init__()
        self._package = package

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(package={self._package!r})'

    # @property
    def package(self) -> ModuleType:
        if isinstance(self._package, ModuleType):
            return self._package
        package_relative_path = self._package.relative_to(PROJECT_ROOT)
        import_path = '.'.join(package_relative_path.parts)
        imported_package = import_module(import_path)
        self._package = imported_package
        return imported_package

    # @property
    def path(self) -> Path:
        if hasattr(self, '_path'):
            return self._path
        package = self.package()
        # Namespaces __file__ attribute is None
        if package.__file__:
            self._path = Path(package.__file__).parent
        else:
            # Also works: self.package.__spec__.submodule_search_locations[0]
            self._path = Path(package.__package__.replace('.', '/'))
        return self._path

    def traverse(self, *, target=None) -> Generator[tuple[str, Page]]:
        path = self.path()
        for path in path.iterdir():
            if path.name.startswith('.') or path.name.startswith('_'):
                continue
            if path.is_dir():
                yield path.name, DirectoryPage(path)
                continue
            if path.suffix != ".py":
                yield path.stem, FilePage(path)
                continue
            if path.name != '__init__.py':
                package = self.package()
                yield path.stem, PythonFilePage(path, package)
                continue

        pages_python_file = self.path() / 'pages.py'
        if pages_python_file.exists():
            package = self.package()
            python_file_page = PythonFilePage(pages_python_file, package)
            for name, page in python_file_page.traverse():
                yield name, page
