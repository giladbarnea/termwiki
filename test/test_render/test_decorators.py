from termwiki.page import DirectoryPage
from test.data import mock_pages_root

mock_page_tree = DirectoryPage(mock_pages_root)


class TestAliasDecorator:
    """Tests @alias decorator, and fn.aliases = ..."""


class TestStyleDecorator:
    def test_sanity(self):
        pages = mock_page_tree['pages']
        function_page_with_style_decorator = pages['with_style_friendly_decorator']
        assert function_page_with_style_decorator
        function_page_with_style_decorator_text = function_page_with_style_decorator.read()
        assert function_page_with_style_decorator_text == "with @style('friendly') decorator"

    def test_language_style(self):
        pages = mock_page_tree['pages']
        function_page_with_style_python_friendly_decorator = pages['with_style_python_friendly_decorator']
        assert function_page_with_style_python_friendly_decorator
        function_page_with_style_python_friendly_decorator_text = function_page_with_style_python_friendly_decorator.read()
        assert function_page_with_style_python_friendly_decorator_text == "with @style(python='friendly') decorator"
