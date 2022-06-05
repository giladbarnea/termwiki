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


def import_module_by_path(path: Path) -> ModuleType:
    if path.is_relative_to(PROJECT_ROOT):
        python_module_relative_path = path.relative_to(PROJECT_ROOT)
    else:
        python_module_relative_path = path
    python_module_name = '.'.join(python_module_relative_path.with_suffix('').parts)
    imported_module = import_module(python_module_name)
    return imported_module


def pformat_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    return ast.dump(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent).replace(r'\n', '\n... ')


def pprint_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    print(pformat_node(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent))


def get_local_var_names_inside_joined_str(joined_str: ast.JoinedStr) -> list[str]:
    var_names = []
    for formatted_value in joined_str.values:
        if isinstance(formatted_value, ast.FormattedValue) and isinstance(formatted_value.value, ast.Name):
            var_names.append(formatted_value.value.id)
    return var_names


def get_local_variables(joined_str: ast.JoinedStr,
                        parent: Callable[..., str],
                        globals_: dict,
                        ) -> dict:
    isinstance(joined_str, ast.JoinedStr) or breakpoint()
    local_var_names_in_fstring = get_local_var_names_inside_joined_str(joined_str)
    # In terms of reuse, FunctionPage.python_module_ast() also does this
    function_def = ast.parse(inspect.getsource(parent)).body[0]
    isinstance(function_def, ast.FunctionDef) or breakpoint()
    local_variables = dict.fromkeys(local_var_names_in_fstring)
    for assign in function_def.body:
        if not isinstance(assign, ast.Assign):
            continue
        for target in assign.targets:
            if target.id in local_var_names_in_fstring:
                var_value = eval(ast.unparse(assign.value), globals_)
                local_variables[target.id] = var_value
    return local_variables


def traverse_immutable_when_unparsed(node, parent, target_id):
    """JoinedStr, Constant, Name, FormattedValue, or sometimes even a simple Expr,
    when ast.unparse(node) returns a string that can be evaluated and used as-is."""
    if hasattr(parent, '__globals__'):
        assert callable(parent) and not isinstance(parent, ModuleType), f'{parent} is not a function'
        globals_ = parent.__globals__
    elif hasattr(parent, '__builtins__'):
        assert not callable(parent) and isinstance(parent, ModuleType), f'{parent} is not a module'
        globals_ = parent.__builtins__
    else:
        raise AttributeError(f'traverse_immutable_when_unparsed({node=}, {parent=}, {target_id=}): parent has neither __globals__ nor __builtins__. {type(parent) = }')
    unparsed_value = ast.unparse(node.value)
    try:
        rendered: str = eval(unparsed_value, globals_)
    except NameError as e:
        # This happens when the value is composed of other local variables
        #  within the same function. E.g the value is "f'{x}'", and x is a local variable.
        #  'x' isn't in the globals, so it's a NameError.
        #  We're resolving the values of the composing local variables.

        locals_ = get_local_variables(node.value, parent, globals_)
        rendered = eval(unparsed_value, globals_, locals_)
    yield target_id, VariablePage(rendered, target_id)


def traverse_assign_node(node: ast.Assign, parent: Callable[..., str] | ModuleType) -> Generator[tuple[str, VariablePage]]:
    parent = inspect.unwrap(parent)  # parent isn't necessarily a function, but that's ok
    target: ast.Name
    for target in node.targets:
        target_id = normalize_page_name(target.id)
        if isinstance(node.value, ast.Constant):
            yield target_id, VariablePage(node.value.value, target_id)
        else:
            yield from traverse_immutable_when_unparsed(node, parent, target_id)


def traverse_function(function: Callable[..., str], python_module_ast: ast.Module) -> Generator[tuple[str, VariablePage]]:
    # noinspection PyTypeChecker
    function_def_ast: ast.FunctionDef = python_module_ast.body[0]
    for node in function_def_ast.body:
        if isinstance(node, ast.Assign):
            yield from traverse_assign_node(node, function)
        else:
            assert hasattr(node, 'value'), f'{node} has no value attribute' or breakpoint()
            yield from traverse_immutable_when_unparsed(node, function, function_def_ast.name)


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
    __pages__ = {}

    def _cache_page(self, normalized_page_name: str, page: Page) -> Page:
        if normalized_page_name in self.__pages__:
            cached_page = self.__pages__[normalized_page_name]
            if isinstance(cached_page, MergedPage):
                cached_page.extend(page)
            else:
                self.__pages__[normalized_page_name] = MergedPage(cached_page, page)
        self.__pages__[normalized_page_name] = page
        return page

    def isearch(self, name: str) -> Generator[Page]:
        """Yields all pages that match 'name'.
        Multiple pages can match if e.g. a file and directory have the same name.
        Lowest level of the search-related methods."""
        name = normalize_page_name(name)
        # if not hasattr(self, '_page_generator'):
        #     self._page_generator = self.traverse()
        #     self._page_generator.exhausted = False
        # while True:
        #     try:
        #         page_name, page = next(self._page_generator)
        #     except StopIteration:
        #         self._page_generator.exhausted = True
        #         break
        #     else:
        #         if page_name == name:
        #             yield page
        for page_name, page in self.traverse():
            if page_name == name:
                yield page

    def search_all(self, name: str) -> list[Page]:
        """Returns a list of all pages that match 'name'."""
        return list(self.isearch(name))

    def search(self, name: str) -> Page | None:
        """Returns the first page that matches 'name'.
        Same as 'page["name"]'.
        mock_page_tree.search('BAD') took 0.5ms.
        mock_page_tree.search('bash') took ~0.1ms (first thing isearch yields).
        """
        for page in self.isearch(name):
            # if page is None:
            #     log.warning(self, f'.search({name!r}): {page} is None')
            #     continue
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
        """Searches a possibly nested page by it's full path."""
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
        variable_texts = [f'# {self.function.__qualname__}']
        seen_variable_pages = set()
        for var_name, var_page in self.traverse():
            if var_page.value in seen_variable_pages:
                continue
            seen_variable_pages.add(var_page.value)
            variable_text = var_page.read()
            variable_texts.append(variable_text)
        return '\n'.join(variable_texts)

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


class MarkdownFilePage(FilePage):  # maybe subclassing Page is better
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
        if hasattr(self.parent, self._python_module.stem):
            self._python_module = getattr(self.parent, self._python_module.stem)
            return self._python_module
        self._python_module = import_module_by_path(self._python_module)
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
        self._package = import_module_by_path(self._package)
        return self._package

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

    def stem(self) -> str:
        return self.path().stem

    def read(self, *args, **kwargs) -> str:
        """Reads any self-named page in the directory"""
        self_stem = self.stem()
        page = self.search(self_stem)
        text = page.read()
        return text

    def traverse(self) -> Generator[tuple[str, Page]]:
        """Traverse the directory and yield (name, page) pairs.
        Pages with the same name are both yielded (e.g. a sub-directory
        and a file with the same name)."""
        self_directory_path = self.path()
        pages_with_same_name_as_us = []
        # sorted(bla.iterdir()), sorted(bla.glob('*')) and glob.glob(bla) are all about 20 µs
        for path in sorted(self_directory_path.iterdir()):  # given e.g name/ and name.md, name/ comes first
            if path.name.startswith('.') or path.name.startswith('_'):
                continue
            path_stem = normalize_page_name(path.stem)
            path_name = normalize_page_name(path.name)
            if path.is_dir():
                directory_page = DirectoryPage(path)
                self._cache_page(path_name, directory_page)
                yield path_name, directory_page
            else:
                if path.suffix == '.py':
                    package = self.package()
                    python_file_page = PythonFilePage(path, package)
                    self._cache_page(path_stem, python_file_page)
                    yield path_stem, python_file_page
                elif path.suffix == '.md':
                    markdown_file_page = MarkdownFilePage(path)
                    self._cache_page(path_stem, markdown_file_page)
                    yield path_stem, markdown_file_page
                else:
                    file_page = FilePage(path)
                    self._cache_page(path_stem, file_page)
                    yield path_stem, file_page

        # Should not only hard code pages.py, but also self-named
        #  files (not only python) and subdirs etc
        pages_python_file = self_directory_path / 'pages.py'
        if pages_python_file.exists():
            package = self.package()
            python_file_page = PythonFilePage(pages_python_file, package)
            for name, page in python_file_page.traverse():
                self._cache_page(name, page)
                yield name, page

        self_directory_name = self_directory_path.stem
        if self_directory_name == 'pages':
            return  # Already traversed

        # for subpath_with_same_name in self_directory_path.glob(f'{self_directory_name}*'):
        #     yield from self.search(subpath_with_same_name.name).traverse()


class MergedPage(Page):
    """A page that is the merge of several pages"""

    def __init__(self, *pages: Page) -> None:
        super().__init__()
        self.pages = list(pages)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(pages={self.pages!r})'

    def read(self, *args, **kwargs) -> str:
        return '\n\n-----------\n'.join(page.read() for page in self.pages)

    def extend(self, *pages: Page) -> None:
        self.pages.extend(pages)
