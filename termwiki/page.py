from __future__ import annotations

import ast
import inspect
from collections.abc import Generator, Sequence
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Callable

import termwiki

PROJECT_ROOT = Path(termwiki.__path__[0]).parent


def pformat_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    return ast.dump(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent).replace(r'\n', '\n... ')


def pprint_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    print(pformat_node(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent))


def paginate_function(function: Callable[..., str], python_module_ast: ast.Module) -> Generator[tuple[str, VariablePage]]:
    wrapped_function = None
    for node in python_module_ast.body[0].body:
        if isinstance(node, ast.Assign):
            target: ast.Name
            for target in node.targets:
                if isinstance(node.value, ast.Constant):
                    yield target.id, VariablePage(node.value.value, target.id)
                # elif isinstance(node.value, ast.JoinedStr):
                #     values = node.value.values
                # breakpoint()
                # for value in node.value.values:
                #     if isinstance(value, ast.FormattedValue):
                #         wrapped_function = getattr(function, '__wrapped__', function)
                #         if not hasattr(value.value, 'func'):
                #             # value.value is Name, so a variable in an fstring. __LOGGING_HANDLER
                #             breakpoint()
                #         formatting_function = wrapped_function.__globals__[value.value.func.id]
                #         formatting_function_args = []
                #         for arg in value.value.args:
                #             if isinstance(arg, ast.JoinedStr):
                #                 formatting_function_args.append(''.join([v.value for v in arg.values]))
                #             else:
                #                 formatting_function_args.append(arg.s)
                #         try:
                #             s = formatting_function(*formatting_function_args)
                #         except AttributeError as e:
                #             from pdbpp import post_mortem;
                #             post_mortem()
                #         yield target.id, VariablePage(s, target.id)
                #         # breakpoint()
                #     else:
                #         yield target.id, VariablePage(value.s, target.id)
                else:
                    # print(f'paginate_function({function}): {node.value=} is not a Constant')
                    wrapped_function = wrapped_function or getattr(function, '__wrapped__', function)
                    unparsed_value = ast.unparse(node.value)
                    rendered: str = eval(unparsed_value, wrapped_function.__globals__)
                    yield target.id, VariablePage(rendered, target.id)
        else:
            print(f'paginate_function({function}): {node} is not an Assign')
            breakpoint()


def paginate_module(module: ModuleType, python_module_ast: ast.Module):
    exclude_names = getattr(module, '__exclude__', {})
    for node in python_module_ast.body:
        if hasattr(node, 'name'):
            if node.name in exclude_names:
                continue
            if isinstance(node, ast.FunctionDef):
                function = getattr(module, node.name)
                yield node.name, FunctionPage(function)
            else:
                print(f'paginate_module({module}): {node} has "name" but is not a FunctionDef')
                breakpoint()
            continue
        if hasattr(node, 'names'):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            print(f'paginate_module({module}): {node} has "names" but is not an Import or ImportFrom')
            breakpoint()
            for alias in node.names:
                if alias.name not in exclude_names:
                    yield alias.name, getattr(module, alias.name)
            continue
        if isinstance(node, ast.Assign):
            # print(f'paginate_module({module}): {node} is an Assign ({[n.id for n in node.targets]})')
            continue
        breakpoint()


def deep_search(page: Page, page_path: Sequence[str]) -> tuple[list[str], Page]:
    if not page_path:
        return [], page
    sub_path, *page_path = page_path
    sub_page = page[sub_path]
    if not sub_page:
        return [], page
    found_paths, found_page = deep_search(sub_page, page_path)
    return [sub_path] + found_paths, found_page


class Page:

    def __init__(self, initial_depth: int = 1) -> None:
        self.initial_depth = initial_depth

    def __getitem__(self, item: str) -> Page | None:
        for page_name, page in self.traverse():
            if page_name == item:
                return page
        return None

    def read(self, *args, **kwargs) -> str:
        ...

    def traverse(self, *args, **kwargs) -> Generator[tuple[str, Page]]:
        ...


class VariablePage(Page):

    def __init__(self, value: str, name: str = None) -> None:
        super().__init__()
        self.value = value
        self.name = name

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(value={self.value!r}, name={self.name!r})'

    def read(self, *args, **kwargs) -> str:
        return str(self.value)


class FunctionPage(Page):
    def __init__(self, function: Callable[..., str], initial_depth: int = 1) -> None:
        super().__init__(initial_depth=initial_depth)
        self.function = function
        self._python_module_ast: ast.Module = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(function={self.function.__qualname__})'

    def python_module_ast(self) -> ast.Module:
        if self._python_module_ast:
            return self._python_module_ast
        self._python_module_ast: ast.Module = ast.parse(inspect.getsource(self.function))
        return self._python_module_ast

    def read(self, *args, **kwargs) -> str:
        text = self.function(*args, **kwargs)
        if text is not None:
            return text
        # If a function doesn't return, return its joined variables
        values = ['#' * self.initial_depth + f' {self.function.__qualname__}']
        seen_pages = set()
        for var_name, var_page in self.traverse():
            if var_page.value in seen_pages:
                continue
            seen_pages.add(var_page.value)
            text = var_page.read()
            values.append(text)
        return '\n'.join(values)

    __call__ = read

    def traverse(self, *args, **kwargs) -> Generator[tuple[str, VariablePage]]:
        python_module_ast = self.python_module_ast()
        yield from paginate_function(self.function, python_module_ast)


class FilePage(Page):
    def __init__(self, filename: str | Path, initial_depth: int = 1) -> None:
        super().__init__(initial_depth=initial_depth)
        self.filename = filename

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(filename={self.filename!r})'

    def read(self, *args, **kwargs) -> str:
        with open(self.filename) as f:
            file_content = f.read()
        return file_content


class PythonFilePage(Page):
    """A Python module representing a file (not a package)"""

    def __init__(self, python_module: ModuleType | Path, parent: ModuleType = None, initial_depth: int = 1) -> None:
        super().__init__(initial_depth=initial_depth)
        self._python_module = python_module
        self._python_module_ast = None
        self.parent = parent

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(python_module={self._python_module!r}, parent={self.parent!r})'

    def python_module_ast(self) -> ast.Module:
        if self._python_module_ast:
            return self._python_module_ast
        self._python_module_ast: ast.Module = ast.parse(inspect.getsource(self.python_module()))
        return self._python_module_ast

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
            # Should handle the case where it's a var
            return getattr(python_module, module_name)()
        # for page in self.traverse():
        # if isinstance(page, ast.FunctionDef):
        #     if module_name == page.name:
        #     return page.body[0].value.s
        return NotImplemented(module_name)

    def traverse(self, *args, **kwargs) -> Generator[tuple[str, Page]]:
        python_module: ModuleType = self.python_module()
        python_module_ast: ast.Module = self.python_module_ast()
        yield from paginate_module(python_module, python_module_ast)


class DirectoryPage(Page):
    """A directory / package / namespace."""

    def __init__(self, package: ModuleType | Path, initial_depth: int = 1) -> None:
        super().__init__(initial_depth=initial_depth)
        self._package = package

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(package={self._package!r})'

    def package(self) -> ModuleType:
        if isinstance(self._package, ModuleType):
            return self._package
        package_relative_path = self._package.relative_to(PROJECT_ROOT)
        import_path = '.'.join(package_relative_path.parts)
        imported_package = import_module(import_path)
        self._package = imported_package
        return imported_package

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
            elif path.suffix != ".py":
                yield path.stem, FilePage(path)
            elif path.name != '__init__.py':
                package = self.package()
                yield path.stem, PythonFilePage(path, package)

        # Should not hard code pages.py, but self-named
        #  files (not only python) and subdirs etc
        pages_python_file = self.path() / 'pages.py'
        if pages_python_file.exists():
            package = self.package()
            python_file_page = PythonFilePage(pages_python_file, package)
            for name, page in python_file_page.traverse():
                yield name, page
