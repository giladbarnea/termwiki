from abc import abstractmethod
from collections.abc import Generator, Sequence, Iterable
from typing import ParamSpec, NoReturn, Any, Callable, TypeVar, Self, ForwardRef

from termwiki.log import log
from termwiki.util import cached_property
from . import ast_utils

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[[Self, ...], Any])
ParamSpec = ParamSpec('ParamSpec')


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
            if merged_sub_pages.pages == self.pages:
                return [], self
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
