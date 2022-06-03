from __future__ import annotations

import ast
import inspect
from abc import abstractmethod
from collections.abc import Generator, Sequence
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Callable

import termwiki
from termwiki.consts import NON_LETTER_RE
from termwiki.log import log

PROJECT_ROOT = Path(termwiki.__path__[0]).parent


def normalize_page_name(page_name: str) -> str:
    return NON_LETTER_RE.sub('', page_name).lower()


def pformat_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    return ast.dump(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent).replace(r'\n', '\n... ')


def pprint_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    print(pformat_node(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent))


def traverse_assign_node(node: ast.Assign, parent: Callable[..., str] | ModuleType) -> Generator[tuple[str, VariablePage]]:
    parent = inspect.unwrap(parent)  # parent isn't necessarily a function, but that's ok
    target: ast.Name
    for target in node.targets:
        target_id = normalize_page_name(target.id)
        if isinstance(node.value, ast.Constant):
            yield target_id, VariablePage(node.value.value, target_id)
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
            # noinspection PyTypeChecker
            unparsed_value = ast.unparse(node.value)
            globs = {}
            if hasattr(parent, '__globals__'):
                globs = parent.__globals__
            elif hasattr(parent, '__builtins__'):
                globs = parent.__builtins__
            else:
                raise AttributeError(f'traverse_assign_node({parent}): {parent} has neither __globals__ nor __builtins__')
            rendered: str = eval(unparsed_value, globs)
            yield target_id, VariablePage(rendered, target_id)


def traverse_function(function: Callable[..., str], python_module_ast: ast.Module) -> Generator[tuple[str, VariablePage]]:
    # noinspection PyUnresolvedReferences
    for node in python_module_ast.body[0].body:
        if isinstance(node, ast.Assign):
            yield from traverse_assign_node(node, function)
        else:
            log.warning(f'traverse_function({function}): {node} is not an Assign')
            breakpoint()


def traverse_module(module: ModuleType, python_module_ast: ast.Module):
    exclude_names = getattr(module, '__exclude__', {})
    for node in python_module_ast.body:
        if hasattr(node, 'name'):
            node_name = normalize_page_name(node.name)
            if node.name in exclude_names or node_name in exclude_names:
                continue
            if isinstance(node, ast.FunctionDef):
                function = getattr(module, node.name)
                yield node_name, FunctionPage(function)

                # this will be replaced with import hook
                if hasattr(function, 'aliases'):
                    for alias in function.aliases:
                        yield normalize_page_name(alias), FunctionPage(function)
            else:
                log.warning(f'traverse_module({module}): {node} has "name" but is not a FunctionDef')
                breakpoint()
            continue
        if hasattr(node, 'names'):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            log.warning(f'traverse_module({module}): {node} has "names" but is not an Import or ImportFrom')
            breakpoint()
            for alias in node.names:
                if alias.name not in exclude_names:
                    yield alias.name, getattr(module, alias.name)
            continue
        if isinstance(node, ast.Assign):
            yield from traverse_assign_node(node, module)
            continue
        log.warning(f"traverse_module({module}): {node} doesn't have 'name' nor 'names' and is not an Assign")
        breakpoint()


class Page:
    def isearch(self, name: str) -> Generator[Page]:
        """Yields all pages that match 'name'.
        Multiple pages can match if e.g. a file and directory have the same name.
        Lowest level of the search-related methods."""
        name = normalize_page_name(name)
        for page_name, page in self.traverse():
            if page_name == name:
                yield page

    def search_all(self, name: str) -> list[Page]:
        """Returns a list of all pages that match 'name'."""
        return list(self.isearch(name))

    def search(self, name: str) -> Page | None:
        """Returns the first truthy page that matches 'name'.
        Same as 'page["name"]'."""
        for page in self.isearch(name):
            if page is None:
                log.warning(self, f'.search({name!r}): {page} is None')
                continue
            return page
        log.warning(self, f'.search({name!r}): nothing found')
        return None

    __getitem__ = search

    def ideep_search(self, page_path: Sequence[str] | str) -> Generator[tuple[list[str], Page]]:
        if not page_path:
            yield [], self
            return
        if isinstance(page_path, str):
            page_path = page_path.split(' ')
        sub_path, *sub_page_path = page_path
        any_sub_page = False
        for sub_page in self.isearch(sub_path):
            any_sub_page = True
            for found_paths, found_page in sub_page.ideep_search(sub_page_path):
                yield [sub_path] + found_paths, found_page
        if not any_sub_page:
            log.warning(self, f'.ideep_search({page_path!r}): nothing found')
            breakpoint()
            yield [], self

    def deep_search(self, page_path: Sequence[str] | str) -> tuple[list[str], Page]:
        if not page_path:
            return [], self
        if isinstance(page_path, str):
            page_path = page_path.split(' ')
        sub_path, *sub_page_path = page_path
        sub_page = self.search(sub_path)
        if not sub_page:
            return [], self
        found_paths, found_page = sub_page.deep_search(sub_page_path)
        return [sub_path] + found_paths, found_page

    @abstractmethod
    def read(self, *args, **kwargs) -> str:
        ...

    def traverse(self, *args, **kwargs) -> Generator[tuple[str, Page]]:
        return NotImplemented


class VariablePage(Page):
    """Variables within functions, or variables at module level"""

    def __init__(self, value: str, name: str = None) -> None:
        super().__init__()
        self.value = value
        self.name = name

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(value={self.value!r}, name={self.name!r})'

    def read(self, *args, **kwargs) -> str:
        return str(self.value)


class FunctionPage(Page):
    def __init__(self, function: Callable[..., str]) -> None:
        super().__init__()
        self.function = function
        self._python_module_ast = None

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
        values = [f'# {self.function.__qualname__}']
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
        yield from traverse_function(self.function, python_module_ast)


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


class MarkdownFilePage(FilePage): # maybe subclassing Page is better
    """Traverses headings"""


class PythonFilePage(Page):
    """A Python module representing a file (not a package)"""

    def __init__(self, python_module: ModuleType | Path, parent: ModuleType = None) -> None:
        super().__init__()
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
                return self._python_module
            python_module_path = Path(self._python_module)
            if python_module_path.is_relative_to(PROJECT_ROOT):
                python_module_relative_path = python_module_path.relative_to(PROJECT_ROOT)
            else:
                python_module_relative_path = python_module_path
            python_module_name = str(python_module_relative_path.with_suffix('')).replace('/', '.')
            self._python_module = import_module(python_module_name)
            return self._python_module

    def read(self, *args, **kwargs) -> str:
        """Read the function with the same name as the module"""
        python_module = self.python_module()
        module_name = Path(python_module.__file__).stem
        return self[module_name].read()

    def traverse(self, *args, **kwargs) -> Generator[tuple[str, Page]]:
        python_module: ModuleType = self.python_module()
        python_module_ast: ast.Module = self.python_module_ast()
        yield from traverse_module(python_module, python_module_ast)


class DirectoryPage(Page):
    """A directory / package / namespace."""

    def __init__(self, package: ModuleType | Path) -> None:
        super().__init__()
        self._package = package
        self._path = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(package={self._package!r})'

    def package(self) -> ModuleType:
        if isinstance(self._package, ModuleType):
            return self._package
        if self._package.is_relative_to(PROJECT_ROOT):
            package_relative_path = self._package.relative_to(PROJECT_ROOT)
        else:
            package_relative_path = self._package
        import_path = '.'.join(package_relative_path.parts)
        imported_package = import_module(import_path)
        self._package = imported_package
        return imported_package

    def path(self) -> Path:
        if self._path is not None:
            return self._path
        package = self.package()
        # Namespaces __file__ attribute is None
        if package.__file__:
            self._path = Path(package.__file__).parent
        else:
            # Also works: self.package.__spec__.submodule_search_locations[0]
            self._path = Path(package.__package__.replace('.', '/'))
        return self._path

    def read(self, *args, **kwargs) -> str:
        path = self.path()
        path_stem = path.stem
        page = self.search(path_stem)
        text = page.read()
        return text

    def traverse(self) -> Generator[tuple[str, Page]]:
        """Traverse the directory and yield (name, page) pairs.
        Pages with the same name are both yielded (e.g. a sub-directory
        and a file with the same name)."""
        for path in self.path().iterdir():
            if path.name.startswith('.') or path.name.startswith('_'):
                continue
            path_stem = normalize_page_name(path.stem)
            path_name = normalize_page_name(path.name)
            if path.is_dir():
                yield path_name, DirectoryPage(path)
            else:
                if path.suffix == '.py':
                    package = self.package()
                    yield path_stem, PythonFilePage(path, package)
                elif path.suffix == '.md':
                    yield path_stem, MarkdownFilePage(path)
                else:
                    yield path_stem, FilePage(path)

        # Should not hard code pages.py, but self-named
        #  files (not only python) and subdirs etc
        pages_python_file = self.path() / 'pages.py'
        if pages_python_file.exists():
            package = self.package()
            python_file_page = PythonFilePage(pages_python_file, package)
            for name, page in python_file_page.traverse():
                yield name, page
