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
            pages_page: PythonFilePage = page_tree.get('pages')[0]
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
            adhd_page: FunctionPage = page_tree.get('adhd')[0]
            adhd_text = adhd_page.read()
            adhd_text_lines = adhd_text.splitlines()
            if '┌' in adhd_text_lines[0]:
                title_index = 1
            else:
                title_index = 0
            title = cleanse_str(adhd_text_lines[title_index])
            assert title.lower() == 'adhd'

    class TestNestedDirectory:
        class TestPythonFile:
            class TestEponymousFunction:
                def test_pecan_product_product(self):
                    """
                    private_pages/
                          pecan/
                               product.py
                                  product() -> str
                    """
                    pecan_page: DirectoryPage = page_tree.get('pecan')[0]
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
                    pecan_page: DirectoryPage = page_tree.get('pecan')[0]
                    product_page: PythonFilePage = pecan_page['product']
                    product_text = product_page.read()
                    product_text_lines = product_text.splitlines()
                    if '┌' in product_text_lines[0]:
                        title_index = 1
                    else:
                        title_index = 0
                    title = cleanse_str(product_text_lines[title_index])
                    assert title.lower() == 'product'
