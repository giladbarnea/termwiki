from termwiki.consts import COLOR_RE
from termwiki.page import FunctionPage, PythonFilePage
from termwiki import page_tree
from test.util import cleanse_str


class TestDirectory:
    class TestEponymousFile:
        class TestFunctionPage:
            def test_adhd(self):
                """
                pages/
                      pages.py
                         adhd() -> str
                """
                pages_page: PythonFilePage = page_tree['pages']
                adhd_page: FunctionPage = pages_page['adhd']
                adhd_text = adhd_page.read()
                adhd_text_lines = adhd_text.splitlines()
                if '┌' in adhd_text_lines[0]:
                    title_index = 1
                else:
                    title_index = 0
                title = cleanse_str(adhd_text_lines[title_index])
                assert title.lower() == 'adhd'
