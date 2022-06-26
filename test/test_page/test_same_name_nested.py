from textwrap import shorten
from termwiki.page import FunctionPage, PythonFilePage, DirectoryPage, MergedPage, VariablePage
from test.data import mock_pages_root
from termwiki.util import clean_str

mock_page_tree = DirectoryPage(mock_pages_root)


class TestDirectory:
    def test_pages_default_python_file(self):
        """
        mock_pages_root/
                       pages.py
                           no_return()
        """
        # root.deep_search('pages')['no_return']
        pages_page: PythonFilePage
        paths, pages_page = mock_page_tree.deep_search('pages')
        no_return_page: FunctionPage = pages_page.search('no_return')
        no_return_text = no_return_page.read()
        no_return_text_lines = no_return_text.splitlines()
        if '┌' in no_return_text_lines[0]:
            title_index = 1
        else:
            title_index = 0
        title = clean_str(no_return_text_lines[title_index])
        assert title.lower() == 'diet'

        # root['pages']['no_return']
        pages_page = mock_page_tree.search('pages')
        no_return_page: FunctionPage = pages_page.search('no_return')
        no_return_text = no_return_page.read()
        no_return_text_lines = no_return_text.splitlines()
        if '┌' in no_return_text_lines[0]:
            title_index = 1
        else:
            title_index = 0
        title = clean_str(no_return_text_lines[title_index])
        assert title.lower() == 'diet'

        # root['no_return']
        no_return_page: FunctionPage = mock_page_tree.search('no_return')
        no_return_text = no_return_page.read()
        no_return_text_lines = no_return_text.splitlines()
        if '┌' in no_return_text_lines[0]:
            title_index = 1
        else:
            title_index = 0
        title = clean_str(no_return_text_lines[title_index])
        assert title.lower() == 'diet'

    def test_traverse_flattens_nested_pages_with_same_name(self):
        only_down_directory = mock_page_tree['only_down']
        assert isinstance(only_down_directory, DirectoryPage)
        only_down_directory_text = only_down_directory.read()
        assert only_down_directory_text == 'only_down'


class TestFunction:
    def test_search_variable(self):
        no_return_path, no_return_page = mock_page_tree.deep_search('no_return')
        diet_page: FunctionPage = no_return_page.search('diet')
        diet_text = diet_page.read()
        diet_text_lines = diet_text.splitlines()
        title = clean_str(diet_text_lines[0])
        assert title.lower() == 'diet'
        assert diet_text_lines[1].strip() == 'Bad: sugary foods'

    def test_self_named_variable(self):
        pass

class TestNestedDirectory:
    def test_self_named_python_file(self):
        ugly_dirname_text = mock_page_tree.search('ugly dirname').read()
        assert ugly_dirname_text == "ugly dirname"


class TestPythonFile:
    def test_self_named_variable(self):
        pass

    def test_self_named_function(self):
        """
        root/
           readable.md
           readable/
              readable.py
                  def readable() -> str
                      readable = "readable variable in readable/readable.py"

        Should return page(s) which have a 'readable' subpage:
        merged_readable_markdown_and_directory.search('readable').
        Since readable.md doesn't, and readable/ dir does, it should return
        readable/readable.py.
        """
        # todo: this is almost identical to test_same_name_same_level.test_same_name_same_level_all_readable
        # * First, manually search one by one until 'readable' var
        merged_readable_markdown_and_directory: MergedPage = mock_page_tree.search('readable')
        assert len(merged_readable_markdown_and_directory.pages) == 2
        readable_python_file: PythonFilePage = merged_readable_markdown_and_directory.search('readable')
        assert isinstance(readable_python_file, PythonFilePage), readable_python_file
        readable_function: FunctionPage = readable_python_file.search('readable')
        assert isinstance(readable_function, FunctionPage), readable_function
        readable_variable: VariablePage = readable_function.search('readable')
        assert isinstance(readable_variable, VariablePage), readable_variable
        readable_text = readable_variable.read()
        assert readable_text == "readable variable in readable/readable.py readable()", shorten(readable_text, 55)

        # * Second, test that read() does deep search if needed
        readable_directory: DirectoryPage = merged_readable_markdown_and_directory.pages[0]
        assert isinstance(readable_directory, DirectoryPage), readable_directory
        assert readable_directory.read() == readable_text
        assert readable_directory.search('readable').read() == readable_text
        assert readable_python_file.read() == readable_text
        assert readable_python_file.search('readable').read() == readable_text
        assert readable_function.read() == readable_text
        assert readable_function.search('readable').read() == readable_text
