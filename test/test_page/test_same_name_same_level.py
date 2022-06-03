import pytest

from termwiki.log import log
from termwiki.page import DirectoryPage, MarkdownFilePage
from test.data import mock_pages_root

mock_page_tree = DirectoryPage(mock_pages_root)


@pytest.mark.skip
def test_bash():
    """bash/ dir exists as well as pages.py bash() function.
    bash/ dir has only an irrelevant file, but it's detected first by DirectoryPage.
    So we expect 'search', which filters falsy Pages, to return only the FunctionPage('bash')"""
    orig_search = mock_page_tree.__class__.search
    mock_page_tree.__class__.search = log.log_in_out(orig_search)
    bash = mock_page_tree.search('bash')
    assert bash
    bash_text = bash.read()
    assert bash_text == "pages.py bash() function"
    mock_page_tree.__class__.search = orig_search


def test_readable():
    """readable/readable.py with 'readable' var exists,
    as well as plain readable.md file."""
    readables = mock_page_tree.search_all('readable')
    assert len(readables) == 2
    # Not sure about Path.iterdir() order
    readable_directory = next((p for p in readables if isinstance(p, DirectoryPage)))

    readable_directory_text = readable_directory.read()
    assert readable_directory_text == "readable variable in readable/readable.py"
    assert readable_directory.search('readable')
    assert readable_directory.search('readable').read() == readable_directory_text

    readable_md_file = next((p for p in readables if isinstance(p, MarkdownFilePage)))
    readable_md_file_text = readable_md_file.read()
    assert readable_md_file_text == "readable.md content"
