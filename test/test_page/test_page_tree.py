from termwiki import page_tree
from termwiki.page import FunctionPage, PythonFilePage, DirectoryPage
from test.util import cleanse_str


class TestDirectory:
    class TestFunctionPage:
        def test_pages_adhd(self):
            """
            pages/
                  pages.py
                     adhd() -> str
            """
            pages_page: PythonFilePage
            paths, pages_page = page_tree.get('pages')
            adhd_page: FunctionPage = pages_page['adhd']
            adhd_text = adhd_page.read()
            adhd_text_lines = adhd_text.splitlines()
            if '┌' in adhd_text_lines[0]:
                title_index = 1
            else:
                title_index = 0
            title = cleanse_str(adhd_text_lines[title_index])
            assert title.lower() == 'adhd'

        def test_implicit_pages_at_directory_root(self):
            adhd_page: FunctionPage
            adhd_path, adhd_page = page_tree.get('adhd')
            adhd_text = adhd_page.read()
            adhd_text_lines = adhd_text.splitlines()
            if '┌' in adhd_text_lines[0]:
                title_index = 1
            else:
                title_index = 0
            title = cleanse_str(adhd_text_lines[title_index])
            assert title.lower() == 'adhd'

        def test_function_variable(self):
            adhd_path, adhd_page = page_tree.get('adhd')
            diet_page: FunctionPage = adhd_page['diet']
            diet_text = diet_page.read()
            diet_text_lines = diet_text.splitlines()
            title = cleanse_str(diet_text_lines[0])
            assert title.lower() == 'diet'
            assert diet_text_lines[1].strip() == 'Bad: sugary foods'

    class TestNestedDirectory:
        def test_self_named_python_file(self):
            from test.data import mock_pages_root

            mock_page_tree = DirectoryPage(mock_pages_root)
            ugly_dirname_text = mock_page_tree['ugly dirname'].read()
            assert ugly_dirname_text == "ugly dirname"

        class TestPythonFile:
            class TestEponymousFunction:
                def test_pecan_product_product(self):
                    """
                    private_pages/
                          pecan/
                               product.py
                                  product() -> str
                    """
                    pecan_page: DirectoryPage
                    pecan_page_paths, pecan_page = page_tree.get('pecan')
                    product_page: PythonFilePage = pecan_page['product']
                    product_function_page: FunctionPage = product_page['product']
                    product_text = product_function_page.read()
                    product_text_lines = product_text.splitlines()
                    if '┌' in product_text_lines[0]:
                        title_index = 1
                    else:
                        title_index = 0
                    title = cleanse_str(product_text_lines[title_index])
                    assert title.lower() == 'product'

                def test_pecan_product(self):
                    """
                    private_pages/
                          pecan/
                               product.py
                                  <.read()>
                                  product() -> str
                    """
                    pecan_page: DirectoryPage
                    pecan_page_paths, pecan_page = page_tree.get('pecan')
                    product_page: PythonFilePage = pecan_page['product']
                    product_text = product_page.read()
                    product_text_lines = product_text.splitlines()
                    if '┌' in product_text_lines[0]:
                        title_index = 1
                    else:
                        title_index = 0
                    title = cleanse_str(product_text_lines[title_index])
                    assert title.lower() == 'product'
