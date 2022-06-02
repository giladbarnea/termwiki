from termwiki.page import DirectoryPage
from test.data import mock_pages_root

mock_page_tree = DirectoryPage(mock_pages_root)


class TestFuzzyPageNames:
    def test_sanity(self):
        adhd_page = mock_page_tree['pages']['adhd']
        for page_name in ('diet', 'behavior', 'cognitive', 'mental'):
            assert adhd_page[page_name]
            assert adhd_page[page_name].read()
        assert adhd_page['cognitive'].read() == adhd_page['mental'].read()

    def test_fuzzy_variable_names(self):
        adhd_page = mock_page_tree['pages']['adhd']
        with_underscore = adhd_page['with_underscore']
        assert with_underscore
        with_underscore_text = with_underscore.read()
        assert with_underscore_text
        assert with_underscore_text == "with underscore"
        assert adhd_page['withunderscore'].read() == with_underscore_text

        _leading_underscore = adhd_page['_leading_underscore']
        assert _leading_underscore
        _leading_underscore_text = _leading_underscore.read()
        assert _leading_underscore_text == "leading underscore"
        assert adhd_page['leading_underscore'].read() == _leading_underscore_text
        assert adhd_page['leading-underscore'].read() == _leading_underscore_text
        assert adhd_page['leadingunderscore'].read() == _leading_underscore_text

        _with_uppercase = adhd_page['_WITH_UPPERCASE']
        assert _with_uppercase
        _with_uppercase_text = _with_uppercase.read()
        assert _with_uppercase_text == "with uppercase"
        assert adhd_page['with_uppercase'].read() == _with_uppercase_text
        assert adhd_page['with-uppercase'].read() == _with_uppercase_text
        assert adhd_page['withuppercase'].read() == _with_uppercase_text

    def test_fuzzy_function_names(self):
        pages = mock_page_tree['pages']
        _with_uppercase_function = pages['_WITH_UPPERCASE_FUNCTION']
        assert _with_uppercase_function
        _with_uppercase_function_text = _with_uppercase_function.read()
        assert _with_uppercase_function_text == "with uppercase function"
        assert pages['with_uppercase_function'].read() == _with_uppercase_function_text
        assert pages['with-uppercase-function'].read() == _with_uppercase_function_text
        assert pages['withuppercasefunction'].read() == _with_uppercase_function_text
