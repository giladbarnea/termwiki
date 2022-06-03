from termwiki.page import FunctionPage, PythonFilePage, DirectoryPage
from test.data import mock_pages_root
from test.util import clean_str

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
        assert title.lower() == 'no_return'

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
        assert title.lower() == 'no_return'

        # root['no_return']
        no_return_page: FunctionPage = mock_page_tree.search('no_return')
        no_return_text = no_return_page.read()
        no_return_text_lines = no_return_text.splitlines()
        if '┌' in no_return_text_lines[0]:
            title_index = 1
        else:
            title_index = 0
        title = clean_str(no_return_text_lines[title_index])
        assert title.lower() == 'no_return'


class TestFunction:
    def test_function_variable(self):
        no_return_path, no_return_page = mock_page_tree.deep_search('no_return')
        diet_page: FunctionPage = no_return_page.search('diet')
        diet_text = diet_page.read()
        diet_text_lines = diet_text.splitlines()
        title = clean_str(diet_text_lines[0])
        assert title.lower() == 'diet'
        assert diet_text_lines[1].strip() == 'Bad: sugary foods'


class TestNestedDirectory:
    def test_self_named_python_file(self):
        ugly_dirname_text = mock_page_tree.search('ugly dirname').read()
        assert ugly_dirname_text == "ugly dirname"


class TestPythonFile:
    def test_self_named_variable(self):
        """
        root/
            readable/
                 readable.py
                    readable: str = "readable variable in readable/readable.py"
        """
        readable_directory: DirectoryPage
        readable_directory_paths, readable_directory = mock_page_tree.deep_search('readable')
        readable_python_file: PythonFilePage = readable_directory.search('readable')
        readable_variable: FunctionPage = readable_python_file.search('readable')
        readable_text = readable_variable.read()
        assert readable_text == "readable variable in readable/readable.py"

        assert mock_page_tree.search('readable').read() == readable_text
