import ast
import inspect
from abc import abstractmethod
from collections.abc import Generator, Sequence, Iterable
from pathlib import Path
from types import ModuleType
from typing import Generic, Type, ParamSpec, NoReturn, Any, Callable, TypeVar, Self, ForwardRef

from termwiki.log import log
from termwiki.util import short_repr, clean_str
from . import ast_utils

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[[Self, ...], Any])
T = TypeVar('T')
I = TypeVar('I')
R = TypeVar('R')
P = ParamSpec('P')

# class CachingGenerator(Generic[T]):
#     # todo: i'm considering caching much simpler, like cached_property
#     instance: T
#     generator: Callable[[T, ...], Iterable[I]]
#     _cacher: Callable[[T, I], ...]
#     _cache_getter: Callable[[T], Iterator[I]]
#
#     def __init__(self, generator: Callable[[T, ...], Iterable[I]]):
#         self.generator = generator
#         self.instance: T = None
#         self._cacher = None
#         self._cache_getter = None
#
#     def __repr__(self):
#         repred = f'{self.__class__.__name__}({self.generator})'
#         if self.instance:
#             repred += f' (instance={repr(self.instance)[:40]}...)'
#         return repred
#
#     def __get__(self, instance: T, owner: Type[T]):
#         if instance is not None:
#             # if self.instance:
#             #     assert self.instance is instance, f'{self} is not bound to {instance}'
#             self.instance = instance
#         return self
#
#     def __call__(self, *args, **kwargs):
#         if self.instance is None:
#             raise AttributeError(f'{self.__class__.__name__} is not bound to an instance')
#
#         if getattr(self.instance, f'__traverse_exhausted__', False):
#             # log.warning(f'{self.instance.__class__.__qualname__}.{self.generator.__name__} is exhausted')
#             yield from self._cache_getter(self.instance)
#             return
#
#         for page in self.generator(self.instance, *args, **kwargs):
#             self._cacher(self.instance, page)
#             yield page
#
#         setattr(self.instance, f'__traverse_exhausted__', True)
#
#     def set_cacher(self, cacher: Callable[[T, I], ...]):
#         self._cacher = cacher
#
#     def set_cache_getter(self, cache_getter: Callable[[T], Iterator[I]]):
#         self._cache_getter = cache_getter


class cached_property(Generic[T]):
    instance: T
    # method: Callable[[T, P], R]

    def __init__(self, method: Callable[P, R]):
        self.method = method

    def __get__(self, instance: T, cls: Type[T]) -> R:
        if instance is None:
            return self
        value = instance.__dict__[self.method.__name__] = self.method(instance)
        return value


def create_caching_traverse(traverse_fn: DecoratedCallable) -> DecoratedCallable:
    def caching_traverse(self: Self, *args, cache_ok=True, **kwargs) -> Generator[tuple[str, Page]]:
        if self.__traverse_exhaused__ and cache_ok:
            pages_iterable = self._pages.items()
        else:
            pages_iterable = traverse_fn(self, *args, **kwargs)

        for name, page in pages_iterable:
            self._pages[name] = page
            yield name, page

        self.__traverse_exhaused__ = True

    return caching_traverse

class Page:
    # def __init__(self):
    #     # self.pages = {}
    #     # self.__traverse_exhaused__ = False
    #     self.__aliases__ = {}

    @abstractmethod
    def read(self, *args, **kwargs) -> str:
        ...

    @cached_property
    def readable(self) -> bool:
        try:
            self.read()
            return True
        except Exception as e:
            log.warning(f'{self!r}.readable | {e!r}')
            return False


class Traversable(Page):
    pages: dict[str, Page]

    def __init__(self):
        self._pages = {}
        """Cache of visited (traversed) pages. Populated and used by 'traverse' method."""
        self.__traverse_exhaused__ = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        # if isinstance(cls.traverse, CachingGenerator):
        #     log.warning(f'{cls}.traverse is already a CachingGenerator')
        #     return
        # traverse = CachingGenerator(cls.traverse)
        # traverse.set_cacher(lambda self, page: self._cache_page(page))
        # traverse.set_cache_getter(lambda self: self.pages.items())
        cls.traverse = create_caching_traverse(cls.traverse)

    @abstractmethod
    def name(self) -> str:
        ...

    # def _cache_page(self, page_tuple: tuple[str, Page]) -> Page:
    #     normalized_page_name, page = page_tuple
    #     if normalized_page_name in self.pages:
    #         cached_page = self.pages[normalized_page_name]
    #         if isinstance(cached_page, MergedPage):
    #             cached_page.extend(page)
    #         else:
    #             self.pages[normalized_page_name] = MergedPage(cached_page, page)
    #     else:
    #         self.pages[normalized_page_name] = page
    #     return self.pages[normalized_page_name]

    @abstractmethod
    # @CachingGenerator
    def traverse(self, *args, cache_ok=True, **kwargs) -> Generator[tuple[str, Page]]:
        ...

    def _ensure_pages_are_populated(self) -> NoReturn:
        if self.__traverse_exhaused__:
            return
        list(self.traverse())

    @property
    def pages(self) -> dict[str, Page]:
        self._ensure_pages_are_populated()
        return self._pages

    @pages.setter
    def pages(self, pages: dict[str, Page]):
        self._pages = pages
        self.__traverse_exhaused__ = True

    # traverse.set_cacher(lambda self, page: self._cache_page(page))

    # traverse._cacher = lambda self, page: self._cache_page(page)

    def search(self,
               name: str,
               *,
               on_not_found: Callable[[Iterable[str], str], str | None] = None) -> Page | None:
        """Search a Page among immediate children of this Traversable.
        If not found, and 'on_not_found' is given, it will be called with
        the names of the immediate children. Otherwise None is returned."""
        normalized_page_name = ast_utils.normalize_page_name(name)
        if normalized_page_name in self.pages:
            return self.pages[normalized_page_name]
        if on_not_found is None:
            return None
        page_name = on_not_found(self.pages.keys(), normalized_page_name)
        if page_name is None:
            return None
        return self.pages[page_name]

    __getitem__ = search

    # @log.log_in_out
    def deep_search(self,
                    page_path: Sequence[str] | str,
                    *,
                    on_not_found: Callable[[Iterable[str], str], str | None] = None,
                    recursive: bool = False,
                    ) -> tuple[list[str], Page]:
        """Searches a possibly nested page by it's full path.
        The main justifications for this method over 'search' are:
        - its return tuple, with the first item being the path taken from here to the page (including up to the page),
        - its ability to search recursively.

        Note: when searching recursively, the tree is traversed all the way down,
        and unless there's only one matching page in the tree, a MergedPage
        is returned containing a flat list of all the matching pages.
        """
        if not page_path:
            return [], self
        # if isinstance(self, MergedPage) and not self.pages:
        #     breakpoint()
        if isinstance(page_path, str):
            page_path = page_path.split(' ')
        first_page_path, *second_and_on_page_paths = page_path
        first_page: Page | Traversable = self.search(first_page_path, on_not_found=on_not_found)
        if not first_page:
            if not recursive:
                return [], self
            merged_sub_pages = self.merge_sub_pages()
            found_paths, found_page = merged_sub_pages.deep_search(page_path,
                                                                   on_not_found=on_not_found,
                                                                   recursive=True)
            return found_paths, found_page

        if not second_and_on_page_paths \
                or not hasattr(first_page, 'deep_search'):
            return [first_page_path], first_page

        first_page: Traversable

        found_paths, found_page = first_page.deep_search(second_and_on_page_paths,
                                                         on_not_found=on_not_found,
                                                         recursive=recursive)
        return [first_page_path] + found_paths, found_page
        # if not found_paths and recursive:
        #     merged_sub_pages = found_page.merge_pages()
        #     return merged_sub_pages.deep_search(second_and_on_page_paths,
        #                                         on_not_found=on_not_found,
        #                                         recursive=True)
        # return [first_page_path] + found_paths, found_page

    def merge_sub_pages(self) -> ForwardRef("MergedPage"):
        from .merged_page import MergedPage
        merged_sub_pages = MergedPage(self.pages)
        return merged_sub_pages

    def read(self, *args, **kwargs) -> str:
        """Searches for self.name() within immediate sub-pages.
        If found, reads the self-named sub-page and returns.
        If not found, the sub-pages are merged and the merged page is read.

        Subclasses that have an inherent way to return their own content
        should override this method, and call super().read() in case of failure.
        """
        # todo: if deep_search had a depth parameter, this would be equivalent to
        #  self.deep_search(self.name(), recursive=True, depth=2)
        name = self.name()
        page = self.search(name)
        if page:
            return page.read()
        # log.warning(f'No self-page found in {self} for {name!r}')
        merged_sub_pages = self.merge_sub_pages()
        merged_sub_pages_text = merged_sub_pages.read()
        return merged_sub_pages_text


class VariablePage(Page):
    """Variables within functions, or variables at module level"""

    def __init__(self, value: str, name: str = None) -> None:
        super().__init__()
        self.value = value
        self.name = name

    def __repr__(self) -> str:
        # todo: when it's IndentationMarkdown, decoloring value should be less hacky
        return f'{self.__class__.__name__}(name={self.name!r}, value={short_repr(clean_str(self.value))})'

    def read(self, *args, **kwargs) -> str:
        return str(self.value)


class FunctionPage(Traversable):
    def __init__(self, function: Callable[P, str | None]) -> None:
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
        for var_name, var_page in self.traverse():
            if var_page.value in seen_variable_pages:
                continue
            seen_variable_pages.add(var_page.value)
            variable_text = var_page.read()
            variable_texts.append(variable_text)
        return '\n'.join(variable_texts)

    __call__ = read

    def traverse(self, *args, cache_ok=True, **kwargs) -> Generator[tuple[str, VariablePage]]:
        self.__traverse_exhaused__ and breakpoint()
        python_module_ast = self.python_module_ast()
        yield from ast_utils.traverse_function(self.function, python_module_ast)


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


class DirectoryPage(Traversable):
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
        self._package = ast_utils.import_module_by_path(self._package)
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
            # self._path = Path(package.__package__.replace('.', '/'))
            self._path = Path(package.__path__[0])
        return self._path

    def stem(self) -> str:
        return self.path().stem

    name = stem

    def traverse(self, *args, cache_ok=True, **kwargs) -> Generator[tuple[str, Page]]:
        """Traverse the directory and yield (name, page) pairs.
        Pages with the same name are both yielded (e.g. a sub-directory
        and a file with the same name)."""
        self.__traverse_exhaused__ and breakpoint()
        self_directory_path = self.path()
        pages_with_same_name_as_us = []
        # sorted(bla.iterdir()), sorted(bla.glob('*')) and glob.glob(bla) are all about 20 µs
        for path in sorted(self_directory_path.iterdir()):  # given e.g name/ and name.md, name/ comes first
            if path.name.startswith('.') or path.name.startswith('_'):
                continue
            path_stem = ast_utils.normalize_page_name(path.stem)
            path_name = ast_utils.normalize_page_name(path.name)
            if path.is_dir():
                directory_page = DirectoryPage(path)
                # self._cache_page(path_name, directory_page)
                yield path_name, directory_page
            else:
                if path.suffix == '.py':
                    package = self.package()
                    python_file_page = PythonFilePage(path, package)
                    # self._cache_page(path_stem, python_file_page)
                    yield path_stem, python_file_page
                elif path.suffix == '.md':
                    markdown_file_page = MarkdownFilePage(path)
                    # self._cache_page(path_stem, markdown_file_page)
                    yield path_stem, markdown_file_page
                else:
                    file_page = FilePage(path)
                    # self._cache_page(path_stem, file_page)
                    yield path_stem, file_page

        # todo: not sure this belongs here. read() also does something similar (inherently lazier)
        pages_python_file = self_directory_path / 'pages.py'
        if pages_python_file.exists():
            package = self.package()
            python_file_page = PythonFilePage(pages_python_file, package)
            for name, page in python_file_page.traverse():
                # self._cache_page(name, page)
                yield name, page

        # self_directory_name = self_directory_path.stem
        # if self_directory_name == 'pages':
        #     return  # Already traversed

        # for subpath_with_same_name in self_directory_path.glob(f'{self_directory_name}*'):
        #     yield from self.search(subpath_with_same_name.name).traverse()


