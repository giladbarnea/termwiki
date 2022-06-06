from termwiki.page import DirectoryPage
from test.data import mock_pages_root

mock_page_tree = DirectoryPage(mock_pages_root)


def test_sanity():
    pages = mock_page_tree.search('pages')
    function_page_with_no_return = pages.search('no_return')
    for page_name in ('diet', 'behavior', 'cognitive', 'mental'):
        assert function_page_with_no_return.search(page_name)
        assert function_page_with_no_return.search(page_name).read()
    assert function_page_with_no_return.search('cognitive').read() == function_page_with_no_return.search('mental').read()

def test_name_collision():
    """If a normalized name already exists, something should happen (de-normalize? error?)"""

def test_fuzzy_variable_names():
    function_page_with_no_return = mock_page_tree['pages']['no_return']
    with_underscore = function_page_with_no_return['with_underscore']
    assert with_underscore
    with_underscore_text = with_underscore.read()
    assert with_underscore_text
    assert with_underscore_text == "with underscore"
    assert function_page_with_no_return['withunderscore'].read() == with_underscore_text

    _leading_underscore = function_page_with_no_return['_leading_underscore']
    assert _leading_underscore
    _leading_underscore_text = _leading_underscore.read()
    assert _leading_underscore_text == "leading underscore"
    assert function_page_with_no_return['leading_underscore'].read() == _leading_underscore_text
    assert function_page_with_no_return['leading-underscore'].read() == _leading_underscore_text
    assert function_page_with_no_return['leadingunderscore'].read() == _leading_underscore_text

    _with_uppercase = function_page_with_no_return['_WITH_UPPERCASE']
    assert _with_uppercase
    _with_uppercase_text = _with_uppercase.read()
    assert _with_uppercase_text == "with uppercase"
    assert function_page_with_no_return['with_uppercase'].read() == _with_uppercase_text
    assert function_page_with_no_return['with-uppercase'].read() == _with_uppercase_text
    assert function_page_with_no_return['withuppercase'].read() == _with_uppercase_text

def test_fuzzy_function_names():
    pages = mock_page_tree['pages']
    _with_uppercase_function = pages['_WITH_UPPERCASE_FUNCTION']
    assert _with_uppercase_function
    _with_uppercase_function_text = _with_uppercase_function.read()
    assert _with_uppercase_function_text == "with uppercase function"
    assert pages['with_uppercase_function'].read() == _with_uppercase_function_text
    assert pages['with-uppercase-function'].read() == _with_uppercase_function_text
    assert pages['withuppercasefunction'].read() == _with_uppercase_function_text

def test_fuzzy_file_names():
    with_whitespace = mock_page_tree['with whitespace']
    assert with_whitespace

    with_whitespace_text = with_whitespace.read()
    assert with_whitespace_text == "with whitespace"

    withwhitespace = mock_page_tree['withwhitespace']
    withwhitespace_text = withwhitespace.read()
    assert withwhitespace_text == with_whitespace_text

    assert with_whitespace['_WITH_WHITESPACE'].read() == with_whitespace_text
    assert with_whitespace['with_whitespace'].read() == with_whitespace_text

    assert withwhitespace['_WITH_WHITESPACE'].read() == with_whitespace_text
    assert withwhitespace['withwhitespace'].read() == with_whitespace_text

    assert with_whitespace['_UGLY_FUNCTION'].read() == "ugly function"
    assert with_whitespace['uglyfunction'].read() == "ugly function"

    assert withwhitespace['_UGLY_FUNCTION'].read() == "ugly function"
    assert withwhitespace['ugly-function'].read() == "ugly function"

def test_fuzzy_directory_names():
    ugly_names = ('ugly dirname_', 'ugly_dirname', 'ugly dirname', 'UGLY_DIRNAME', 'uglydirname')
    for ugly_name in ugly_names:
        ugly_dirname_directory = mock_page_tree[ugly_name]
        assert ugly_dirname_directory
        for ugly_name_2 in ugly_names:
            ugly_dirname_pyfile = ugly_dirname_directory[ugly_name_2]
            assert ugly_dirname_pyfile
            for ugly_name_3 in ugly_names:
                ugly_dirname_variable = ugly_dirname_pyfile[ugly_name_3]
                assert ugly_dirname_variable
                ugly_dirname_variable_text = ugly_dirname_variable.read()
                assert ugly_dirname_variable_text == "ugly dirname"
