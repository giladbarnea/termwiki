# from .ast_utils import normalize_page_name, import_module_by_path, traverse_function, traverse_module
# from termwiki.util import lazy_import
# ast_utilz = mod.ast_utils
from .page import Page, Traversable, VariablePage, FunctionPage, FilePage, MarkdownFilePage, PythonFilePage, DirectoryPage
from .merged_page import MergedPage
# mod, __getattr__ = lazy_import('termwiki.page', {'ast_utils'})
# from .ast_utils import normalize_page_name, traverse_function
from .page_tree import page_tree
from .errors import *
