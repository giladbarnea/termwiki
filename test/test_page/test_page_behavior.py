"""
Tests for specific Page behaviors, not file structure scenarios.

on_not_found,
deep_search(recursive=True),
exact name match is deeper than fzf ~match,
self-named pages as default,
read() merges sub-pages if no self-named sub-page was found,
functions without return values,
"""

from termwiki.page import FunctionPage, DirectoryPage, VariablePage, PythonFilePage, MarkdownFilePage, MergedPage
from termwiki.util import clean_str
from test.data import mock_pages_root
from test.data.mock_pages_root import page_behavior

mock_page_tree = DirectoryPage(mock_pages_root)
page_behavior_data_dir = DirectoryPage(page_behavior)


class TestDirectory:
    def test_traverse_yields_from_pages_py(self):
        """
        mock_pages_root/
           pages.py
               no_return()
        We expect mock_page_tree.search('no_return') to return the FunctionPage(no_return).
        This also tests functions without return values
        """
        # * First, manually verify one by one until 'no_return' function
        # root['pages']['no_return']
        pages_page: PythonFilePage = mock_page_tree.search('pages')
        no_return_page: FunctionPage = pages_page.search('no_return')
        no_return_text = no_return_page.read()
        no_return_text_lines = no_return_text.splitlines()
        if '┌' in no_return_text_lines[0]:
            title_index = 1
        else:
            title_index = 0
        title = clean_str(no_return_text_lines[title_index])
        assert title.lower() == 'diet'

        # * Second, test that search() yields from pages.py
        # root['no_return']
        no_return_page: FunctionPage = mock_page_tree.search('no_return')
        assert isinstance(no_return_page, FunctionPage)
        no_return_text = no_return_page.read()
        no_return_text_lines = no_return_text.splitlines()
        if '┌' in no_return_text_lines[0]:
            title_index = 1
        else:
            title_index = 0
        title = clean_str(no_return_text_lines[title_index])
        assert title.lower() == 'diet'

    def test_read_flattens_nested_pages_with_same_name_all_the_way_down(self):
        """
        only_down/
            only_down.py
                def only_down():
                    _only_down = 'only_down'

        Expect only_down_directory.read() to return 'only_down'
        """
        only_down_directory: DirectoryPage = page_behavior_data_dir['only_down']
        assert isinstance(only_down_directory, DirectoryPage)
        only_down_directory_text = only_down_directory.read()
        assert only_down_directory_text == 'only_down'

        only_down_python_file: PythonFilePage = only_down_directory.search('only_down')
        assert isinstance(only_down_python_file, PythonFilePage)
        assert only_down_python_file.read() == 'only_down'

        only_down_function: FunctionPage = only_down_python_file.search('only_down')
        assert isinstance(only_down_function, FunctionPage)
        assert only_down_function.read() == 'only_down'

        only_down_variable: VariablePage = only_down_function.search('only_down')
        assert isinstance(only_down_variable, VariablePage)
        assert only_down_variable.read() == 'only_down'


class TestFunction:
    def test_search_variable(self):
        no_return_page: FunctionPage = mock_page_tree['pages']['no_return']
        diet_page: VariablePage = no_return_page.search('diet')
        diet_text = diet_page.read()
        diet_text_lines = diet_text.splitlines()
        title = clean_str(diet_text_lines[0])
        assert title.lower() == 'diet'
        assert diet_text_lines[1].strip() == 'Bad: sugary foods'

    def test_self_named_variable(self):
        pass


class TestPythonFile:
    def test_self_named_variable(self):
        pass


class TestNestedDirectory:
    def test_read_searches_self_named_python_file(self):
        """
        same_name_nested/
            ugly dirname_/
                ugly_dirname.py
                    UGLY_DIRNAME = 'ugly dirname'
        """
        ugly_dirname_text = mock_page_tree.search('ugly dirname').read()
        assert ugly_dirname_text == "ugly dirname"


class TestMergedPage:
    def test_search(self):
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
        # * First, manually search one by one until 'readable' var
        merged_readable_markdown_and_directory: MergedPage = page_behavior_data_dir.search('readable')
        assert len(merged_readable_markdown_and_directory.pages) == 2
        readable_python_file: PythonFilePage = merged_readable_markdown_and_directory.search('readable')
        assert isinstance(readable_python_file, PythonFilePage), readable_python_file
        readable_function: FunctionPage = readable_python_file.search('readable')
        assert isinstance(readable_function, FunctionPage), readable_function
        readable_variable: VariablePage = readable_function.search('readable')
        assert isinstance(readable_variable, VariablePage), readable_variable
        readable_variable_content = readable_variable.read()
        assert readable_variable_content == "readable variable in readable/readable.py readable()", readable_variable_content

        readable_directory: DirectoryPage
        readable_markdown: MarkdownFilePage
        readable_directory, readable_markdown = merged_readable_markdown_and_directory.pages

        # * Second, test that DirectoryPage.read() merges all sub-pages recursively and gets to the 'readable' var
        assert isinstance(readable_directory, DirectoryPage), readable_directory
        assert readable_directory.read() == readable_variable_content
        assert readable_directory.search('readable').read() == readable_variable_content
        assert readable_python_file.read() == readable_variable_content
        assert readable_python_file.search('readable').read() == readable_variable_content
        assert readable_function.read() == readable_variable_content
        assert readable_function.search('readable').read() == readable_variable_content

        # * Third, MarkdownFilePage.read()
        assert isinstance(readable_markdown, MarkdownFilePage), readable_markdown
        assert readable_markdown.read() == 'readable.md content'

    def test_read_flattens_nested_pages_with_same_name_all_the_way_down(self):
        merged_readable_markdown_and_directory: MergedPage = page_behavior_data_dir.search('readable')
        merged_content = merged_readable_markdown_and_directory.read()
        # contains and not equals because I'm not sure about merged formatting
        assert "readable variable in readable/readable.py readable()" in merged_content
        assert "readable.md content" in merged_content
