from termwiki.page import DirectoryPage
from test.data import mock_pages_root

mock_page_tree = DirectoryPage(mock_pages_root)


def test_same_name_same_level_not_all_readable():
    """bash/ dir exists as well as pages.py bash() function.
    bash/ dir has only an unreadable file.
    So we expect 'read', which skips unreadable Pages,
    to return only the contents of bash() function."""
    bash = mock_page_tree.search('bash')
    assert bash is not None
    bash_text = bash['foo'].read()
    assert bash_text == "pages.py bash() function"