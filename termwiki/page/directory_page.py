from collections.abc import Generator
from pathlib import Path
from types import ModuleType

from . import ast_utils
from .file_page import FilePage
from .markdown_file_page import MarkdownFilePage
from .page import Traversable, Page
from .python_file_page import PythonFilePage


class DirectoryPage(Traversable):
    """A directory / package / namespace."""

    def __init__(self, package: ModuleType | Path) -> None:
        super().__init__()
        self._package = package
        self._path = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(package={self._package!r})"

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
        for path in sorted(
            self_directory_path.iterdir()
        ):  # given e.g name/ and name.md, name/ comes first
            if path.name.startswith(".") or path.name.startswith("_"):
                continue
            path_stem = ast_utils.normalize_page_name(path.stem)
            path_name = ast_utils.normalize_page_name(path.name)
            if path.is_dir():
                directory_page = DirectoryPage(path)
                # self._cache_page(path_name, directory_page)
                yield path_name, directory_page
            else:
                if path.suffix == ".py":
                    package = self.package()
                    python_file_page = PythonFilePage(path, package)
                    # self._cache_page(path_stem, python_file_page)
                    yield path_stem, python_file_page
                elif path.suffix == ".md":
                    markdown_file_page = MarkdownFilePage(path)
                    # self._cache_page(path_stem, markdown_file_page)
                    yield path_stem, markdown_file_page
                else:
                    file_page = FilePage(path)
                    # self._cache_page(path_stem, file_page)
                    yield path_stem, file_page

        # todo: not sure this belongs here. read() also does something similar (inherently lazier)
        pages_python_file = self_directory_path / "pages.py"
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
